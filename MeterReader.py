
import logging

logger = logging.getLogger("meter_reader")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("meter_reader_log.log")
fh.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

from enum import Enum
import cv2
import tensorflow as tf
import numpy as np
import json
import codecs
import time

from MqttHandler import MqttHandler

class ReaderHealthState(Enum):
    OK = 0
    VIDEO_ERROR = 1
    MQTT_ERROR = 2
    READ_ERROR = 4
    SETTING_ERROR = 8
    CNN_ERROR = 16
    PLAU_ERROR = 32
    CONF_SAVE_ERROR = 64
    CONF_ERROR = 128
    INF_LOW_PROB = 256


class MeterReader():
    def __init__(self):
        
        # Initalize class variables
        self.meterConf = {}
        self.readerHealth = ReaderHealthState.OK.value
        self.errorStreak = 0

        self.delta = 0
        self.lastValue = 0

        self.setUpMeter()

    def setError(self, errorType, msg=""):  
        self.readerHealth |= errorType.value
        logger.warning(f"{str(errorType)} - {msg}")

    def delError(self, errorType):
        # First check if error was set before, because delError is called periodically, nit just at errors
        if self.readerHealth & errorType.value:
            self.readerHealth &= ~errorType.value
            logger.info(f"{str(errorType)} has been healed.")


    def checkError(self):
        return self.readerHealth == ReaderHealthState.OK.value
    
    def checkErrStreak(self):

        if not self.checkError():
            self.errorStreak += 1
        else:
            self.errorStreak = 0
            
        if self.meterConf["meterReaderDesc"]["errStreakResetThresh"] < self.errorStreak:
            self.setUpMeter(isRestart=True)
            self.errorStreak = 0
            self.readerHealth = ReaderHealthState.OK.value

    def onMqttConnect(self, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            self.mqttClient.subscribeTotopic(self.meterConf["mqttDesc"]["topics"]["currValResp"], self.receiveValueFromHa)
            self.delError(ReaderHealthState.MQTT_ERROR)
        else:
            msg = f"Failed to connect, return code: {rc}.\n"
            print(msg)
            self.setError(ReaderHealthState.MQTT_ERROR, msg)
            
    def onMqttDisConnect(self):
        print("Unexpected MQTT Broker disconnection! Trying to reconnect...")

    def receiveValueFromHa(self, value):
        if value is not None:
            print("Received gas value from Home Assisstant:", str(value), ". From type:", type(value))

    def readMeter(self):
        isSuccess = True # Variable to follow read success throughout a cycle

        topic = self.meterConf["mqttDesc"]["topics"]["flashOn"]
        msg = json.dumps({"bright":self.meterConf["meterReaderDesc"]["flashBright"]/100})

        resSucc, resMsg  = self.mqttClient.publish2opic(topic, msg)
        print(resMsg)
        
        if not resSucc:
            self.setError(ReaderHealthState.MQTT_ERROR, resMsg)
            isSuccess = False
        else:
            self.delError(ReaderHealthState.MQTT_ERROR)
        
        time.sleep(self.meterConf["meterReaderDesc"]["flashTime"])

        if isSuccess:
            try:
                video = cv2.VideoCapture(self.meterConf["cameraDesc"]["camUrl"])
                check, frame = video.read()
                video.release()
                h, w = frame.shape[:2] 
                rotM = cv2.getRotationMatrix2D(center=(w/2, h/2), 
                                                angle=self.meterConf["meterReaderDesc"]["imgRot"], 
                                                scale=1) 
                frame = cv2.warpAffine( src=frame, M=rotM, dsize=(w, h))


                if type(frame) == type(None):
                    self.setError(ReaderHealthState.VIDEO_ERROR, "empty frame")
                else:
                    self.delError(ReaderHealthState.VIDEO_ERROR)
            except:
                isSuccess = False
                msg = "ERROR: could not connect to camera!"
                print(msg)
                self.setError(ReaderHealthState.VIDEO_ERROR, msg)

        if not self.meterConf["imgMaskDesc"]["digMasks"]:
            self.setError(ReaderHealthState.SETTING_ERROR, "Image masks haven't been set")
            isSuccess = False
        else:
            self.delError(ReaderHealthState.SETTING_ERROR)
            

        if  isSuccess:
            sensor = 0
            for i, (powa, rect) in enumerate(self.meterConf["imgMaskDesc"]["digMasks"].items()):

                maskImg = frame[rect[0][1]:rect[1][1], rect[0][0]:rect[1][0]]
                maskImg = cv2.resize(maskImg, (20,32))
                maskImg = maskImg.astype(np.float32)

                try:
                    self.cnnInterpreter.set_tensor(self.modelInputDict[0]['index'], [maskImg])

                    self.cnnInterpreter.invoke()

                    output_data = self.cnnInterpreter.get_tensor(self.modelOutputDict[0]['index'])
                    
                    prob = np.max(output_data)
                    if prob < self.meterConf["meterReaderDesc"]["minInferenceProb"]:
                        self.setError(ReaderHealthState.INF_LOW_PROB, f"Low probability of digit detection: {prob}, digit: {i}.")
                        sensor = self.lastValue
                        break
                    else:
                        self.delError(ReaderHealthState.INF_LOW_PROB)

                    res = np.argmax(output_data)
        
                    sensor += res * pow(10,int(powa))
                    sensor = round(sensor, 3)
                    self.delError(ReaderHealthState.CNN_ERROR)
                except:
                    sensor = self.lastValue
                    self.setError(ReaderHealthState.CNN_ERROR, "Error with getting tensor!")
     
            rangeTh = self.meterConf["meterReaderDesc"]["singleStepThresh"]

            # Verify sensor value
            if sensor < self.lastValue: 
                msg = f"Sensor value must be decreasing. Value:({sensor}), using last stored instead: {self.lastValue}"
                self.setError(ReaderHealthState.PLAU_ERROR, msg)
                print(msg)
            elif (self.lastValue+rangeTh) < sensor and not self.firstRound:
                msg = f"Value read ({sensor}) is not plausible as change is larger than the limit: ({rangeTh}) , using last stored instead: {self.lastValue}"
                self.setError(ReaderHealthState.PLAU_ERROR, msg)
                print(msg)
            else:
                self.delError(ReaderHealthState.PLAU_ERROR)
                self.delta = sensor - self.lastValue
                self.lastValue = sensor
                self.firstRound = False
                self.meterConf["meterReaderDesc"]["initMeterVal"] = self.lastValue
                try:
                    with open("MeterToolConf.json", 'w') as f:
                        json.dump(self.meterConf, f, indent=4)

                except:
                    self.setError(ReaderHealthState.CONF_SAVE_ERROR)

        print("Gas usage: ", self.lastValue, "m3")
        print("Health state: ", self.readerHealth)

        topic = self.meterConf["mqttDesc"]["topics"]["meterReport"]
        msg = json.dumps({"sensorValue":self.lastValue, "delta": self.delta, "sensorHealth": self.readerHealth})
        resSucc, resMsg  = self.mqttClient.publish2opic(topic, msg)
        self.delError(ReaderHealthState.CONF_SAVE_ERROR)
        print(resMsg)
        if not resSucc:
            self.setError(ReaderHealthState.MQTT_ERROR, resMsg)
        else:
            self.delError(ReaderHealthState.MQTT_ERROR)

        topic = self.meterConf["mqttDesc"]["topics"]["flashOff"]
        msg = json.dumps({"bright":"0%"})
        resSucc, resMsg  = self.mqttClient.publish2opic(topic, msg)
        print(resMsg)
        if not resSucc:
            self.setError(ReaderHealthState.MQTT_ERROR, resMsg)
        else:
            self.delError(ReaderHealthState.MQTT_ERROR)


    def setUpMeter(self, isRestart=False):
        
        logger.info("----------------------Starting script----------------------")
        if isRestart:
            logger.warning(f"Meter reader has been restarted after an error streak. Last health state was: {self.readerHealth}.")
            
        try:
            with codecs.open("MeterToolConf.json", 'r', 'utf-8') as jsf:
                self.meterConf = json.load(jsf)
        except:
            msg = "Could not open configuration file!"
            self.setError(ReaderHealthState.CONF_ERROR, msg)
            print(msg)

        self.lastValue = self.meterConf["meterReaderDesc"]["initMeterVal"]
        self.firstRound = self.meterConf["meterReaderDesc"]["ignoreFirstRoundPlauErr"]

        self.mqttClient = MqttHandler(self.meterConf["mqttDesc"],
                                "gas_meter_reader",
                                self.onMqttConnect,
                                self.onMqttDisConnect)


        topic = self.meterConf["mqttDesc"]["topics"]["currValReq"]
        msg = json.dumps({})

        resSucc, resMsg  = self.mqttClient.publish2opic(topic, msg)
        print(resMsg)
        
        if not resSucc:
            self.setError(ReaderHealthState.MQTT_ERROR, resMsg)
            return False
        else:
            self.delError(ReaderHealthState.MQTT_ERROR)


        # Load TFLite model and allocate tensors.
        try:
            self.cnnInterpreter = tf.lite.Interpreter(model_path="DigitNumberModel.tflite")
                    
            # Get input and output tensors.
            self.modelInputDict = self.cnnInterpreter.get_input_details()
            self.modelOutputDict = self.cnnInterpreter.get_output_details()
                    
            self.cnnInterpreter.allocate_tensors()
        except:
            msg = "Could not set up CNN interpreter!"
            self.setError(ReaderHealthState.CNN_ERROR, msg)
            print(msg)

    

#-------------------------------------------------------------------
# Start of script
#-------------------------------------------------------------------


mr = MeterReader()

while True:
    mr.checkErrStreak()
    mr.readMeter()
    time.sleep(mr.meterConf["meterReaderDesc"]["timeBtwRounds"])
    



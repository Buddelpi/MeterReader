
import sys
import cv2
import tensorflow as tf
import numpy as np
import random
from paho.mqtt import client as mqtt_client
import json
import codecs
from pathlib import Path
import time
from enum import Enum

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
    

def setError(errorType):
    global readerHealth
    readerHealth |= errorType.value

def delError(errorType):
    global readerHealth
    readerHealth &= ~errorType.value

def checkError():
    return readerHealth == ReaderHealthState.OK.value

def onMqttConnect(rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        delError(ReaderHealthState.MQTT_ERROR)
    else:
        print("Failed to connect, return code %d\n", rc)
        delError(ReaderHealthState.MQTT_ERROR)
        
def onMqttDisConnect():
    print("Unexpected MQTT Broker disconnection! Trying to reconnect...")

def readMeter():
    global lastValue, firstRound

    topic = meterConf["mqttDesc"]["topics"]["flashOn"]
    msg = json.dumps({"bright":meterConf["meterReaderDesc"]["flashBright"]/100})

    resSucc, resMsg  = mqttClient.publish2opic(topic, msg)
    print(resMsg)
    
    if not resSucc:
        setError(ReaderHealthState.MQTT_ERROR)
        return False
    else:
        delError(ReaderHealthState.MQTT_ERROR)
    
    time.sleep(meterConf["meterReaderDesc"]["flashTime"])

    try:
        video = cv2.VideoCapture(meterConf["cameraDesc"]["camUrl"])
        check, frame = video.read()
        video.release()
        if type(frame) == type(None):
            setError(ReaderHealthState.VIDEO_ERROR)
        else:
            delError(ReaderHealthState.VIDEO_ERROR)
    except:
        print("ERROR: could not connect to camera!")
        setError(ReaderHealthState.VIDEO_ERROR)

    if not meterConf["imgMaskDesc"]["digMasks"]:
        setError(ReaderHealthState.SETTING_ERROR)
    else:
        delError(ReaderHealthState.SETTING_ERROR)

    sensor = 0
    if  checkError():
        for i, (powa, rect) in enumerate(meterConf["imgMaskDesc"]["digMasks"].items()):

            maskImg = frame[rect[0][1]:rect[1][1], rect[0][0]:rect[1][0]]
            maskImg = cv2.resize(maskImg, (20,32))
            maskImg = maskImg.astype(np.float32)

            try:
                cnnInterpreter.set_tensor(modelInputDict[0]['index'], [maskImg])

                cnnInterpreter.invoke()

                output_data = cnnInterpreter.get_tensor(modelOutputDict[0]['index'])
                res = np.argmax(output_data)
    
                sensor += res * pow(10,int(powa))
                sensor = round(sensor, 3)
                delError(ReaderHealthState.CNN_ERROR)
            except:
                sensor = lastValue
                setError(ReaderHealthState.CNN_ERROR)
    else:
        sensor = lastValue      

    rangeTh = meterConf["meterReaderDesc"]["singleStepThresh"]

    if (sensor < lastValue or (lastValue+rangeTh) < sensor) and not firstRound:
        setError(ReaderHealthState.PLAU_ERROR)
        print(f"Wrong value read ({sensor}), using last stored instead: {lastValue}")
        sensor = lastValue
        
    else:
        delError(ReaderHealthState.PLAU_ERROR)
        lastValue = sensor
        firstRound = False
        meterConf["meterReaderDesc"]["initMeterVal"] = lastValue
        try:
            with open("MeterToolConf.json", 'w') as f:
                json.dump(meterConf, f, indent=4)

        except:
            setError(ReaderHealthState.CONF_SAVE_ERROR)

    print("Gas usage: ", sensor, "m3")
    print("Health state: ", readerHealth)

    topic = meterConf["mqttDesc"]["topics"]["meterReport"]
    msg = json.dumps({"sensorValue":sensor, "sensorHealth": readerHealth})
    resSucc, resMsg  = mqttClient.publish2opic(topic, msg)
    delError(ReaderHealthState.CONF_SAVE_ERROR)
    print(resMsg)
    if not resSucc:
        setError(ReaderHealthState.MQTT_ERROR)
    else:
        delError(ReaderHealthState.MQTT_ERROR)

    topic = meterConf["mqttDesc"]["topics"]["flashOff"]
    msg = json.dumps({"bright":"0%"})
    resSucc, resMsg  = mqttClient.publish2opic(topic, msg)
    print(resMsg)
    if not resSucc:
        setError(ReaderHealthState.MQTT_ERROR)
    else:
        delError(ReaderHealthState.MQTT_ERROR)


meterConf = {}
try:
    with codecs.open("MeterToolConf.json", 'r', 'utf-8') as jsf:
        meterConf = json.load(jsf)
except:
    raise BaseException("Cannot open configuration file!")

mqttClient = MqttHandler(meterConf["mqttDesc"],
                        "gas_meter_reader",
                        onMqttConnect,
                        onMqttDisConnect)


# Load TFLite model and allocate tensors.
cnnInterpreter = tf.lite.Interpreter(model_path="dig-cont_0600_s3.tflite")
        
# Get input and output tensors.
modelInputDict = cnnInterpreter.get_input_details()
modelOutputDict = cnnInterpreter.get_output_details()
        
cnnInterpreter.allocate_tensors()

lastValue = meterConf["meterReaderDesc"]["initMeterVal"]
firstRound = True
readerHealth = ReaderHealthState.OK.value

while True:
    readMeter()
    time.sleep(meterConf["meterReaderDesc"]["timeBtwRounds"])
    



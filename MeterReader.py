
import logging

logger = logging.getLogger("meter_reader")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("meter_reader_log.log")
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

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
    CONF_ERROR = 128
    

def setError(errorType, msg=""):
    global readerHealth
    readerHealth |= errorType.value
    logger.warning(f"{str(errorType)} - {msg}")

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
        setError(ReaderHealthState.MQTT_ERROR, resMsg)
        return False
    else:
        delError(ReaderHealthState.MQTT_ERROR)
    
    time.sleep(meterConf["meterReaderDesc"]["flashTime"])

    try:
        video = cv2.VideoCapture(meterConf["cameraDesc"]["camUrl"])
        check, frame = video.read()
        video.release()
        if type(frame) == type(None):
            setError(ReaderHealthState.VIDEO_ERROR, "empty frame")
        else:
            delError(ReaderHealthState.VIDEO_ERROR)
    except:
        msg = "ERROR: could not connect to camera!"
        print(msg)
        setError(ReaderHealthState.VIDEO_ERROR, msg)

    if not meterConf["imgMaskDesc"]["digMasks"]:
        setError(ReaderHealthState.SETTING_ERROR, "Image masks haven't been set")
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
                setError(ReaderHealthState.CNN_ERROR, "Error with getting tensor!")
    else:
        sensor = lastValue      

    rangeTh = meterConf["meterReaderDesc"]["singleStepThresh"]

    if (sensor < lastValue or (lastValue+rangeTh) < sensor) and not firstRound:
        msg = f"Wrong value read ({sensor}), using last stored instead: {lastValue}"
        setError(ReaderHealthState.PLAU_ERROR, msg)
        print(msg)
        sensor = lastValue
        delta = 0
        
    else:
        delError(ReaderHealthState.PLAU_ERROR)
        delta = sensor - lastValue
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
    msg = json.dumps({"sensorValue":sensor, "delta": delta, "sensorHealth": readerHealth})
    resSucc, resMsg  = mqttClient.publish2opic(topic, msg)
    delError(ReaderHealthState.CONF_SAVE_ERROR)
    print(resMsg)
    if not resSucc:
        setError(ReaderHealthState.MQTT_ERROR, resMsg)
    else:
        delError(ReaderHealthState.MQTT_ERROR)

    topic = meterConf["mqttDesc"]["topics"]["flashOff"]
    msg = json.dumps({"bright":"0%"})
    resSucc, resMsg  = mqttClient.publish2opic(topic, msg)
    print(resMsg)
    if not resSucc:
        setError(ReaderHealthState.MQTT_ERROR, resMsg)
    else:
        delError(ReaderHealthState.MQTT_ERROR)


meterConf = {}
try:
    with codecs.open("MeterToolConf.json", 'r', 'utf-8') as jsf:
        meterConf = json.load(jsf)
except:
    msg = "Could not open configuration file!"
    setError(ReaderHealthState.CONF_ERROR, msg)
    print(msg)

mqttClient = MqttHandler(meterConf["mqttDesc"],
                        "gas_meter_reader",
                        onMqttConnect,
                        onMqttDisConnect)


# Load TFLite model and allocate tensors.
try:
    cnnInterpreter = tf.lite.Interpreter(model_path="dig-cont_0600_s3.tflite")
            
    # Get input and output tensors.
    modelInputDict = cnnInterpreter.get_input_details()
    modelOutputDict = cnnInterpreter.get_output_details()
            
    cnnInterpreter.allocate_tensors()
except:
    msg = "Could not set up CNN interpreter!"
    setError(ReaderHealthState.CNN_ERROR, msg)
    print(msg)

lastValue = meterConf["meterReaderDesc"]["initMeterVal"]
firstRound = True
readerHealth = ReaderHealthState.OK.value

while True:
    readMeter()
    time.sleep(meterConf["meterReaderDesc"]["timeBtwRounds"])
    



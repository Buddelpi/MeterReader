
import sys
import cv2
import tensorflow as tf
import numpy as np
import random
from paho.mqtt import client as mqtt_client
import json
import yaml
import codecs
from pathlib import Path

from ImageManLabel import ImageManLabel
from ImageMaskPicker import MaskDigitItem

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QPushButton, QWidget, QVBoxLayout, QApplication,  \
                    QToolBar, QStatusBar, QPushButton, QSlider




class MeterConfGUI(QMainWindow):
    def __init__(self):
        super().__init__(parent=None)
        
        try:
            with codecs.open("MeterToolConf.json", 'r', 'utf-8') as jsf:
                self.meterConf = json.load(jsf)
        except:
            raise BaseException("Cannot open configuration file!")
        
        self.currMaskItem = None
        
        self.displyWidth = 640
        self.displayHeight = 480
        
        self.mainWidget = QWidget()

        
        self.setWindowTitle("Meter Tool Configurator")
        self._createMainArea()
        self._createMenu()
        #self._createToolBar()
        self._createStatusBar()
        
        self._setUpCnn()
        
        self.mqttClient = self._connectMqtt()
        
    def _connectMqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.statBar.showMessage("Connected to MQTT Broker!", 5000)
            else:
                self.statBar.showMessage("Failed to connect, return code %d\n", rc)
        
        def on_disconnect(client, userdata, rc):
            if rc != 0:
                self.statBar.showMessage("Unexpected MQTT Broker disconnection! Trying to reconnect...", 5000)
                self.mqttClient = self._connectMqtt()
                
        client = mqtt_client.Client(f"meter_tool_mqtt_client{random.randint(1000,9999)}")
        client.username_pw_set(self.meterConf["mqttDesc"]["user"], self.meterConf["mqttDesc"]["pass"])
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.connect(self.meterConf["mqttDesc"]["brokerUrl"], self.meterConf["mqttDesc"]["brokerTcpPort"])
        return client
    
    def _publishFLashMqtt(self):
        
        lampState = self.flashLigthBut.isChecked()

        if lampState:
            topic="gasmeter/flashlight/on"
            msg = json.dumps({"bright":self.flashBrightSli.value()/100})
            self.flashLigthBut.setStyleSheet("background-color : yellow")      
        else:
            topic="gasmeter/flashlight/off"
            self.flashLigthBut.setStyleSheet("background-color : lightgrey")
            msg = json.dumps({"bright":"0%"})
        
        result = self.mqttClient.publish(topic, msg)
        status = result[0]
        if status == 0:
            self.statBar.showMessage(f"Sent topic `{topic}`", 5000)
        else:
            self.statBar.showMessage(f"Failed to send message to topic {topic}", 5000)

    def _createMainArea(self):
        
        mainLay = QVBoxLayout()
        configLay = QHBoxLayout()
        
        controlLay = QVBoxLayout()
        
        maskLay = QVBoxLayout()
        wholesMaskLay = QHBoxLayout()
        fractMaskLay = QHBoxLayout() 
        
        
        self.imageLabel = ImageManLabel(self.onRectReceived)
        self.imageLabel.setInhibit(True)
        self.cropLabel = ImageManLabel()
        
        captureBut = QPushButton("Capture image")
        captureBut.clicked.connect(self.captureImage)
        captureBut.setStyleSheet("background-color : lightgrey")
        
        self.flashLigthBut = QPushButton("Flashlight")
        self.flashLigthBut.setCheckable(True)
        self.flashLigthBut.setStyleSheet("background-color : lightgrey")
        self.flashLigthBut.clicked.connect(self._publishFLashMqtt) 
        
        self.flashBrightSli = QSlider(Qt.Horizontal)
        self.flashBrightSli.setMinimum(0)
        self.flashBrightSli.setMaximum(100)
        self.flashBrightSli.setSingleStep(1)
        self.flashBrightSli.setValue(self.meterConf["flashBright"])
        self.flashLigthBut.setText(f"Flashlight ({self.flashBrightSli.value()}%)")
        self.flashBrightSli.sliderReleased.connect(self.handleFlashBrightSLi)
        
        controlLay.addWidget(captureBut)
        controlLay.addWidget(self.flashLigthBut)
        controlLay.addWidget(self.flashBrightSli)
        controlLay.addStretch()
        
        cntWhoDig = self.meterConf["imgMaskDesc"]["digitSize"][0]
        cntFracDig = self.meterConf["imgMaskDesc"]["digitSize"][1]
        
        self.maskItemDict = {}
        
        wholesMaskLay.addStretch()
        fractMaskLay.addStretch()
        
        for num in range(cntWhoDig-1, -1, -1):
            self.maskItemDict[num] = MaskDigitItem(num, self.handleMaskItemEvent)
            wholesMaskLay.addWidget(self.maskItemDict[num])
        for num in range(-1, (-1*cntFracDig)-1, -1):
            self.maskItemDict[num] = MaskDigitItem(num, self.handleMaskItemEvent)
            fractMaskLay.addWidget(self.maskItemDict[num])
        
        maskLay.addLayout(wholesMaskLay)
        maskLay.addLayout(fractMaskLay)
        
        configLay.addLayout(controlLay)
        configLay.addLayout(maskLay)
            
        mainLay.addWidget(self.imageLabel)
        mainLay.addLayout(configLay)
        
        self.mainWidget.setLayout(mainLay)
        
        self.setCentralWidget(self.mainWidget)
    
    def handleMaskItemEvent(self, itemPower, atSave=False):
        for key in self.maskItemDict.keys():
            if key != itemPower:
                self.maskItemDict[key].dislightItem()
            else:
                if atSave:
                    self.currMaskItem = None
                    self.imageLabel.setInhibit(True)
                else:
                    self.currMaskItem = itemPower
                    self.imageLabel.setInhibit(False)
     
    
    def handleFlashBrightSLi(self):
        self.flashLigthBut.setText(f"Flashlight ({self.flashBrightSli.value()}%)")
        self._publishFLashMqtt()
        
    
    def onRectReceived(self, imgPart, tl, br):    
        self.cropLabel.setImage(imgPart)


        img3 = cv2.resize(imgPart, (20,32))
        img4 = img3.astype(np.float32)
        
        self.cnnInterpreter.set_tensor(self.modelInputDict[0]['index'], [img4])

        self.cnnInterpreter.invoke()

        output_data = self.cnnInterpreter.get_tensor(self.modelOutputDict[0]['index'])
        
        res = np.argmax(output_data)
        
        resNum = "NaN" if res==10 else str(res)
        perc = round(100*output_data[0][res],2)
        
        showPic = cv2.imwrite(f"validNum_{resNum}.jpg",img4)
        
        self.statBar.showMessage(f"{resNum} ({perc}%)")
        
        if self.currMaskItem != None:
            self.maskItemDict[self.currMaskItem].setMaskImg(imgPart)
            self.maskItemDict[self.currMaskItem].setMaskCoord(tl,br)
            self.maskItemDict[self.currMaskItem].setPredict(resNum,perc)
            self.maskItemDict[self.currMaskItem].setItemIsSet()
            self.meterConf[self.currMaskItem] = (tl,br)
        
    
    def saveConfig(self):
        
        allSet = True
        for i,item in enumerate(self.maskItemDict.values()):
            if not item.getItemIsSet():
                allSet = False
        
        if allSet:
            try:
                with open("MeterToolConf.json", 'w') as f:
                    json.dump(self.meterConf, f, indent=4)
                self.statBar.showMessage("Configuration successfully saved!", 5000)
            except:
                self.statBar.showMessage("There was an error saving the configuration file!")
        else:
            self.statBar.showMessage("Configuration could not be saved as not all the digit masks are configured!")
            
    def captureImage(self):
        try:
            self.video = cv2.VideoCapture(self.meterConf["camUrl"])
            check, frame = self.video.read()
            self.video.release()
            self.imageLabel.setImage(frame)
        except:
            self.statBar.showMessage("ERROR: could not connect to camera!")
    
    def _createMenu(self):
        menu = self.menuBar()#.addAction("&Exit", self.close)
        #menu.addAction("&Exit", self.close)
        menu.addAction("&Save config", self.saveConfig)
        #menu.addAction("&Read current state", self.close)

    def _createToolBar(self):
        tools = QToolBar()
        tools.addAction("Exit", self.close)
        self.addToolBar(tools)

    def _createStatusBar(self):
        self.statBar = QStatusBar()
        self.statBar.showMessage("Ready to go", 5000)
        self.setStatusBar(self.statBar)
    
    
    def _setUpCnn(self):
        # Load TFLite model and allocate tensors.
        self.cnnInterpreter = tf.lite.Interpreter(model_path="dig-cont_0600_s3.tflite")
        
        # Get input and output tensors.
        self.modelInputDict = self.cnnInterpreter.get_input_details()
        self.modelOutputDict = self.cnnInterpreter.get_output_details()
        
        self.cnnInterpreter.allocate_tensors()


def except_hook(cls, exception, traceback):
    """Needed for more useful debugging messages"""
    sys.__excepthook__(cls, exception, traceback)





if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(Path('style.css').read_text())
    sys.excepthook = except_hook
    window = MeterConfGUI()
    window.show()
    sys.exit(app.exec())
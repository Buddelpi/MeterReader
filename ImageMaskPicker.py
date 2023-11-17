
import numpy as np
from ImageManLabel import ImageManLabel

from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QLabel, QGroupBox                    
                    
class MaskDigitItem(QGroupBox):
    def __init__(self, power, disLightAllOthersFunc):
        super().__init__()
        
        self.power = power
        self.disLightAllOthersFunc = disLightAllOthersFunc
        
        self.setObjectName("maskItem")
        
        self.itemisSet = False
        self.maskTopLeft = (0,0)
        self.maskBotRight = (0,0)
        
        mainLay = QVBoxLayout()
        
        self.setTitle(f"10^{power}")
        
        self.blankImg = np.zeros((32,20,3), dtype=np.uint8)
        self.maskImgLbl = ImageManLabel()
        self.maskImgLbl.setImage(self.blankImg)
        self.tlLbl = QLabel("TL coord: (0,0)")
        self.brLbl = QLabel("Br coord: (0,0)")
        self.predLbl = QLabel("Prediction: NaN (100%)")
        
        self.saveBut = QPushButton("Change")
        self.saveBut.clicked.connect(self.handleSaveBut)
        self.saveBut.setCheckable(True)
        
        mainLay.addWidget(self.maskImgLbl)
        mainLay.addWidget(self.tlLbl)
        mainLay.addWidget(self.brLbl)
        mainLay.addWidget(self.predLbl)
        mainLay.addWidget(self.saveBut)
        
        self.setLayout(mainLay)
        
        
    
    def highlightItem(self):
        self.saveBut.setText("Save")
        self.setStyleSheet("QGroupBox{border: 6px solid green}")
        self.disLightAllOthersFunc(self.power)
        
    def dislightItem(self):
        self.saveBut.setText("Change")
        self.saveBut.setChecked(False)
        if self.itemisSet:
            self.setStyleSheet("QGroupBox{border: 2px solid green}")
        else:
            self.setStyleSheet("QGroupBox{border: 2px solid red}")
            
    def handleSaveBut(self):
        saveButState = self.saveBut.isChecked()
        
        if saveButState:
            self.highlightItem()
            self.resetItem()
        else:
            self.dislightItem()
            self.disLightAllOthersFunc(self.power, True)
    
    def setMaskImg(self, img):
        self.maskImgLbl.setImage(img)
    
    def setMaskCoord(self, tl, br):
        self.itemisSet = True
        self.maskTopLeft = tl
        self.maskBotRight = br
        self.tlLbl.setText(f"TL coord: {tl}")
        self.brLbl.setText(f"Br coord: {br}")
    
    def setPredict(self, num, perc):
        self.predLbl.setText(f"Prediction: {num} ({perc}%)")
        
    def resetItem(self):
        self.itemisSet = False
        self.maskTopLeft = (0,0)
        self.maskBotRight = (0,0)
        self.tlLbl.setText("TL coord: (0,0)")
        self.brLbl.setText("Br coord: (0,0)")
        self.predLbl.setText("Prediction: NaN (100%)")
        self.blankImg = np.zeros((32,20,3), dtype=np.uint8)
        
    def setItemIsSet(self):
        self.itemisSet = True
        
    def getItemIsSet(self):
        return self.itemisSet
    
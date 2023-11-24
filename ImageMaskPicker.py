
import numpy as np
from ImageManLabel import ImageManLabel

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox                    
                    
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
        maskSetLay = QHBoxLayout()
        textLay = QVBoxLayout()
        
        self.setTitle(f"10^{power}")
        
        self.blankImg = np.zeros((32,20,3), dtype=np.uint8)
        self.maskImgLbl = ImageManLabel()
        self.maskImgLbl.setImage(self.blankImg)
        self.blLbl = QLabel("BL(000,000)")
        self.blLbl.setObjectName("tlblLbl")
        self.blLbl.resize(100, 20) 
        self.tlLbl = QLabel("TL(000,000)")
        self.tlLbl.setObjectName("tlblLbl")
        self.tlLbl.resize(100, 20) 
        self.predLbl = QLabel("NaN (100%)")
        self.predLbl.setObjectName("predLbl")
        self.predLbl.resize(100, 20) 
        
        self.saveBut = QPushButton("Change")
        self.saveBut.clicked.connect(self.handleSaveBut)
        self.saveBut.setCheckable(True)
        self.saveBut.setObjectName("saveBut")
        
        textLay.addWidget(self.tlLbl)
        textLay.addWidget(self.blLbl)
        textLay.addWidget(self.predLbl)

        maskSetLay.addWidget(self.maskImgLbl)
        maskSetLay.addLayout(textLay)

        mainLay.addLayout(maskSetLay)
        mainLay.addWidget(self.saveBut)
        
        self.setLayout(mainLay)
        
        
    
    def highlightItem(self):
        self.saveBut.setText("Save")
        self.setStyleSheet("QGroupBox{border: 2px solid yellow}")
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
        self.tlLbl.setText(f"TL{tl}")
        self.blLbl.setText(f"BL{br}")
    
    def setPredict(self, num, perc):
        self.predLbl.setText(f"{num} ({perc}%)")
        
    def resetItem(self):
        self.itemisSet = False
        self.maskTopLeft = (0,0)
        self.maskBotRight = (0,0)
        self.tlLbl.setText("TL(000,000)")
        self.blLbl.setText("BL(000,000)")
        self.predLbl.setText("NaN (100%)")
        self.blankImg = np.zeros((32,20,3), dtype=np.uint8)
        
    def setItemIsSet(self):
        self.itemisSet = True
        
    def getItemIsSet(self):
        return self.itemisSet
    
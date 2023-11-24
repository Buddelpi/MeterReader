
from copy import deepcopy
import cv2

from PyQt5.QtWidgets import QLabel

from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import  Qt, QEvent
from types import NoneType

class ImageManLabel(QLabel):
    def __init__(self, onRectCb=None):
        super().__init__()
        if type(onRectCb) != NoneType:
            self.installEventFilter(self)
        self.currImage = None
        self.savedImage = None
        self.origImage = None
        self.onRectCb = onRectCb
        
        self.recTopLeft = (0,0)
        self.recBotRight = (0,0)
        
        self.inhibitDraw = False
    
    def convert_cv_qt(self, cv_img, keepOrigSize=True):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        if not keepOrigSize:
            convert_to_Qt_format = convert_to_Qt_format.scaled(self.displyWidth, self.displayHeight, Qt.KeepAspectRatio)
        return QPixmap.fromImage(convert_to_Qt_format)
    
    
    def setImage(self, frame=None):
        if type(frame) == NoneType:
            frame = deepcopy(self.currImage)
        else:
            self.currImage = deepcopy(frame)
            self.savedImage = deepcopy(frame)
            self.origImage = deepcopy(frame)
        qt_img = self.convert_cv_qt(frame)
        self.setPixmap(qt_img)
    
    def drawRect(self, tl, br):
        self.currImage = deepcopy(self.savedImage)
        cv2.rectangle(self.currImage,tl,br,(0,255,0),2)
        self.setImage()
    
    def saveImage(self):
        self.savedImage = deepcopy(self.currImage)
     
    def eventFilter(self, obj, event):
        if not self.inhibitDraw:
            if event.type() == QEvent.MouseMove:
                x = event.x()
                y = event.y()
                self.recBotRight = (x,y)
                self.drawRect(self.recTopLeft, self.recBotRight)
            elif event.type() == QEvent.MouseButtonPress:
                x = event.x()
                y = event.y()
                if event.button() == Qt.LeftButton:
                    self.recTopLeft = (x,y)
            elif event.type() == QEvent.MouseButtonRelease:
                x = event.x()
                y = event.y()
                if event.button() == Qt.LeftButton:
                    self.recBotRight = (x,y)
                    self.drawRect(self.recTopLeft, self.recBotRight)
                    
                    rat = 1/3
                    colShift = int(abs(self.recTopLeft[0]-self.recBotRight[0])*rat)
                    rowShift = int(abs(self.recTopLeft[1]-self.recBotRight[1])*rat)  
                    
                    bigRecTl = (self.recTopLeft[0]-colShift, self.recTopLeft[1]-rowShift)
                    bigRectBr = (self.recBotRight[0]+colShift, self.recBotRight[1]+rowShift)
                    
                    self.drawRect(bigRecTl, bigRectBr)
                    self.onRectCb(self.origImage[bigRecTl[1]:bigRectBr[1], bigRecTl[0]:bigRectBr[0]], bigRecTl, bigRectBr)
                    
        return super().eventFilter(obj, event)
    
    def setInhibit(self, inh):
        self.inhibitDraw = inh
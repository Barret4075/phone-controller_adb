import sys
import cv2
import numpy as np
from copy import deepcopy
import time


class cut_img:
    def __init__(self,  img_file:np.ndarray,scale=0.34,):
        """imgfile:单通道灰度值图像\n
        scale:比例
        """
        self.scale = scale
        self.img = img_file
        # self.img =cv2.cvtColor(self.img,cv2.COLOR_BGR2GRAY)
        self.resized_img = cv2.resize(self.img, dsize=None, fx=scale, fy=scale)
        self.show_marked_img = False
        self.sub_img = None
        self.notdone=True
        # 坐标标记
        self.start_x, self.start_y, self.end_x, self.end_y = 0, 0, 0, 0
        # 在缩略图上的坐标标记
        self.ori_x, self.ori_y = 0, 0
        # 放大镜
        self.magnifier_range = 60
        self.magnifier_scale = 4

    def save_img(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.notdone=False
            return

    def draw(self, event, x, y, flags, params):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.ori_x, self.ori_y = x, y
            self.start_x, self.start_y = round(x / self.scale), round(y / self.scale)
            self.show_marked_img = True
        if event == cv2.EVENT_LBUTTONUP:
            self.end_x = round(x / self.scale)
            self.end_y = round(y / self.scale)
            self.sub_img = self.img[
                min(self.start_y, self.end_y) : max(self.start_y, self.end_y),
                min(self.start_x, self.end_x) : max(self.start_x, self.end_x),
            ]
            global target_img
            target_img=self.sub_img
            cv2.imshow("image", self.resized_img)
            cv2.imshow("click to save", self.sub_img)
            self.show_marked_img = False
            cv2.setMouseCallback("click to save", self.save_img)
        if event == cv2.EVENT_MOUSEMOVE:
            if self.show_marked_img:
                marked_img = deepcopy(self.resized_img)
                cv2.rectangle(marked_img, (self.ori_x, self.ori_y), (x, y), (0, 0, 160), 1)
                cv2.imshow("image", marked_img)
            # magnifier
            round_x, round_y = round(x / self.scale), round(y / self.scale)
            size_img = self.img.shape
            bordered_img = np.zeros((
                    size_img[0] + 2 * self.magnifier_range,
                    size_img[1] + 2 * self.magnifier_range,
                    ),dtype=np.uint8,)
            bordered_img[
                self.magnifier_range : self.magnifier_range + size_img[0],
                self.magnifier_range : self.magnifier_range + size_img[1]
            ] = self.img
            o_img = bordered_img[
                round_y : round_y + 2*self.magnifier_range,
                round_x : round_x + 2*self.magnifier_range,]
            magnifier_img = cv2.resize(
                o_img,
                dsize=None,
                fx=self.magnifier_scale,
                fy=self.magnifier_scale,)
            cv2.line(magnifier_img,(0,self.magnifier_range*self.magnifier_scale),(2*self.magnifier_range*self.magnifier_scale,self.magnifier_range*self.magnifier_scale),(120,10,120),1)
            cv2.line(magnifier_img,(self.magnifier_range*self.magnifier_scale,0),(self.magnifier_range*self.magnifier_scale,2*self.magnifier_range*self.magnifier_scale),(120,10,120),1)
            cv2.putText(magnifier_img,f"ori_x={x},ori_y={y}",[10,30],cv2.FONT_HERSHEY_SIMPLEX,1,(120,120,30),2)
            cv2.putText(magnifier_img,f"x={round(x/self.scale)},y={round(y/self.scale)}",[10,70],cv2.FONT_HERSHEY_SIMPLEX,1.4,(120,120,100),2)
            cv2.imshow("magnifier", magnifier_img)

    def cut_img(self):
        cv2.imshow("image", self.resized_img)
        cv2.setMouseCallback("image", self.draw)
        while self.notdone:
            cv2.waitKey(1)
        cv2.destroyAllWindows()
        return self.sub_img

def cut(img):
    sub_img=cut_img(img)
    return sub_img.cut_img()

if __name__== "__main__":
    img=cv2.cvtColor(np.array(cv2.imread('screen.png')),cv2.COLOR_RGB2GRAY)
    img=cut(img)
    cv2.imshow('img',img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

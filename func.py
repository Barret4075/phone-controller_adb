import random
import time
import cv2
from cut_img import cut
import numpy as np

from enum_classes import actionType, swipedirection

def capscreen(device):
    return cv2.cvtColor(np.array(device.screenshot()), cv2.COLOR_BGR2GRAY)


def capbutton(device=None,img=None):
    if img is None:
        img=capscreen(device)
    sub_img,*_=cut(img)
    return sub_img


def clickbutton(adb_device, img,offset=None,max_retry=3):
    """img为图像,offset包括了坐标偏移个区域大小"""
    for i in range(max_retry):
        _, maxVal, _, (startX, startY) = cv2.minMaxLoc(
            cv2.matchTemplate(capscreen(adb_device), img, cv2.TM_CCOEFF_NORMED)
        )
        if maxVal > 0.7:
            break
        time.sleep(2*i)
    if offset is None:
        endX, endY = startX + img.shape[1], startY + img.shape[0]
    else:
        (offset_X,offset_Y),(len_X,len_Y)=offset
        startX,startY=startX+offset_X,startY+offset_Y
        endX,endY=startX+len_X,startY+len_Y
    adb_device.click(random.randint(startX, endX),random.randint(startY, endY))
def swipe(device, direction, img=None,coordinates=False):
    screen = capscreen(device)
    shapeY, shapeX = screen.shape[:2]
    if coordinates:
        startY,startX=random.randint(*img[0]),random.randint(*img[1])
    else:
        _, maxVal, _, (startX,startY,) = cv2.minMaxLoc(
            cv2.matchTemplate(screen, img, cv2.TM_CCOEFF_NORMED))
        startX += random.randint(0, img.shape[1])
        startY += random.randint(0, img.shape[0])
    match direction:
        case swipedirection.up:
            end_X = startX + random.randint(-30, 30)
            end_Y = max(startY - random.randint(400, 600), 0)
        case swipedirection.down:
            end_X = startX + random.randint(-30, 30)
            end_Y = min(startY + random.randint(400, 600), shapeY)
        case swipedirection.left:
            end_X = max(startX - random.randint(400, 600), 0)
            end_Y = startY + random.randint(-30, 30)
        case swipedirection.right:
            end_X = min(startX + random.randint(400, 600), shapeX)
            end_Y = startY + random.randint(-30, 30)
    device.swipe(startX, startY, end_X, end_Y, random.uniform(0.2, 0.7))
def perform(device, params, act):
    match act:
        case actionType.click:
            clickbutton(device, params)
        case actionType.common_swipe:
            swipe(device,*params,coordinates=True)
        case actionType.keyevent:
            device.keyevent(params)
        case actionType.delay:
            time.sleep(params)
        case actionType.begin:
            device.keyevent("HOME")
            time.sleep(0.2)
            device.keyevent("HOME")
            for _ in range(5):
                time.sleep(random.uniform(0.8, 1.2))
                device.swipe(500, 500, 100, 500, 0.1)
        case actionType.click_possibly:
            time.sleep(3)
            clickbutton(device,params)
        case actionType.click_offset:
            pat,*offset_shape=params
            clickbutton(device,pat,offset_shape)
        case actionType.swipe_offset:
            swipe(device,*params)
def get_enum_value(enum_class, value):
    return next((member for member in enum_class if member.value == value), None)
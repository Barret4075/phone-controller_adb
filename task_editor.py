import os
import time
from cut_img import cut,draw_coordinate
import random
from enum import Enum
from copy import deepcopy
import pickle
import cv2
from adbutils import adb
import numpy as np

d = adb.device()


def capscreen(d):
    return cv2.cvtColor(np.array(d.screenshot()), cv2.COLOR_BGR2GRAY)


def capbutton(device=None,img=None):
    if img is not None:
        return cut(img)
    return cut(capscreen(device))


def clickbutton(d, img,target=None):
    """确认是否加入"""
    for _ in range(4):
        _, maxVal, _, (startX, startY) = cv2.minMaxLoc(
            cv2.matchTemplate(capscreen(d), img, cv2.TM_CCOEFF_NORMED)
        )
        if maxVal <0.8:
            time.sleep(2)
        else:
            break

    if target==None:
        endX, endY = startX + img.shape[1], startY + img.shape[0]
    else:
        (offset_X,offset_Y),(len_X,len_Y)=target
        startX,startY=startX+offset_X,startY+offset_Y
        endX,endY=startX+len_X,startY+len_Y
    d.click(random.randint(startX, endX),random.randint(startY, endY))


class actionType(Enum):
    click = 'click'
    common_swipe = 'swipe'
    keyevent = 'keyevent'
    delay = 'delay'
    begin = 'start_of'
    click_possibly ='possible_button'
    click_offset ='offset_click'
    swipe_offset='offset_swipe'

class swipedirection(Enum):
    up="up"
    down="down"
    right="right"
    left="left"


def swipe(d, direction, img=None,coordinates=False):
    screen = capscreen(d)
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
    d.swipe(startX, startY, end_X, end_Y, random.uniform(0.2, 0.7))
    print(f"swipe success from X:{startX} Y:{startY} to X:{end_X} Y:{end_Y}")

def action(d, para, act):
    match act:
        case actionType.click:
            clickbutton(d, para)
        case actionType.common_swipe:
            swipe(d,*para,coordinates=True)
        case actionType.keyevent:
            d.keyevent(para)
        case actionType.delay:
            time.sleep(para)
        case actionType.begin:
            d.keyevent("HOME")
            time.sleep(0.2)
            d.keyevent("HOME")
            for _ in range(5):
                time.sleep(random.uniform(0.8, 1.2))
                d.swipe(500, 500, 100, 500, 0.1)
        case actionType.click_possibly:
            time.sleep(3)
            clickbutton(d,para)
        case actionType.click_offset:
            pat,*offset_shape=para
            clickbutton(d,pat,offset_shape)
        case actionType.swipe_offset:
            swipe(d,*para)


def createTask():
    process = []
    actionlist=list(enumerate(actionType,start=1))
    while True:
        r = input(
            '\n'.join([f'{ind}.{i.value}' for ind,i in actionlist]+['请选择'])
        )
        if r.isalnum() and int(r)-1 in range(len(actionType)):
            r=actionlist[int(r)-1][1]
        else:
            with open(f'{r}.task', "wb") as f:
                pickle.dump(process,f)
            break
        match r:
            # Home/返回键
            case actionType.keyevent:
                act = {"1": "HOME", "2": "BACK"}[input("1.HOME\n2.BACK")]
                action(d, act, actionType.keyevent)
                process.append([act, actionType.keyevent])
            # 单击
            case actionType.click:
                button = capbutton(d)
                action(d, button, actionType.click)
                process.append([deepcopy(button), actionType.click])
            #偏移点击
            case actionType.click_offset:
                screen=capscreen(d)
                button_basic = capbutton(d,screen)
                button_target = capbutton(d,screen)
                _, _, _, (startX_b, startY_b) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_basic, cv2.TM_CCOEFF_NORMED))
                _, _, _, (startX_t, startY_t) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_target, cv2.TM_CCOEFF_NORMED))
                
                process.append([[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],actionType.click_offset])
                action(d,[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],actionType.click_offset)
            #延迟
            case actionType.delay:
                second = int(input("请输入秒数"))
                process.append(([second, actionType.delay]))
            #点击（可能存在）
            case actionType.click_possibly:
                button = capbutton(d)
                action(d, button,actionType.click_possibly)
                process.append([button,actionType.click_possibly])
            #自由滑动
            case actionType.common_swipe:
                swipe_range=draw_coordinate(capscreen(d))
                directions=list(enumerate(swipedirection,start=1))
                c = input('\n'.join([f'{ind}.{i.value}' for ind,i in directions]+['请选择']))
                if c not in map(str,range(1,5)):
                    raise ValueError("输入不合法!")
                direction=directions[int(c)-1][1]

                action(d, para=(direction,swipe_range),act=actionType.common_swipe)
                process.append([actionType.common_swipe,(direction,swipe_range,)])
            #划至桌面最右（脚本开始）
            case actionType.begin:
                action(d, None, actionType.begin)
                process.append([None, actionType.begin])
            case actionType.swipe_offset:
                img=capscreen(d)
                button=capbutton(img=img)
                directions=list(enumerate(swipedirection,start=1))
                c = input(
                    '\n'.join([f'{ind}.{i.value}' for ind,i in directions]+['请选择'])
                )
                if c not in map(str,range(1,5)):
                    raise ValueError("输入不合法!")
                direction=directions[int(c)-1][1]
                process.append([[direction,button],actionType.swipe_offset])
                action(d,[direction,button],actionType.swipe_offset)

        process.append([random.uniform(2,4),actionType.delay])


def testTask():
    tasks = [i for i in os.listdir() if os.path.isfile(i) and i.endswith(".task")]
    if tasks == []:
        raise FileExistsError("当前目录没有task文件")
    with open(tasks[int(input("\n".join([f"{ind}.{i}" for ind, i in enumerate(tasks, start=1)]+ ["请输入序号"])))- 1],'rb') as f:
        task=pickle.load(f)
    for target, act in task:
        action(d, target, act)

if __name__=="__main__":
    createTask()

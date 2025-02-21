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
import dill

adb_device = adb.device()


def capscreen(d):
    return cv2.cvtColor(np.array(d.screenshot()), cv2.COLOR_BGR2GRAY)


def capbutton(device=None,img=None):
    if img is not None:
        return cut(img)
    return cut(capscreen(device))


def clickbutton(adb_device, img,offset=None,max_retry=3):
    """img为图像,offset包括了坐标偏移个区域大小"""
    for _ in range(max_retry):
        _, maxVal, _, (startX, startY) = cv2.minMaxLoc(
            cv2.matchTemplate(capscreen(adb_device), img, cv2.TM_CCOEFF_NORMED)
        )
        if maxVal <0.7:
            time.sleep(2)
        else:
            break

    if offset==None:
        endX, endY = startX + img.shape[1], startY + img.shape[0]
    else:
        (offset_X,offset_Y),(len_X,len_Y)=offset
        startX,startY=startX+offset_X,startY+offset_Y
        endX,endY=startX+len_X,startY+len_Y
    adb_device.click(random.randint(startX, endX),random.randint(startY, endY))


class actionType(Enum):
    keyevent = '实体按键'
    click = '点击'
    click_offset ='偏移点击'
    click_possibly ='尝试点击'
    common_swipe = '屏幕滑动'
    swipe_offset='图片滑动'
    delay = '延迟'
    begin = '回到桌面最右'

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
                action(adb_device, act, actionType.keyevent)
                process.append([act, actionType.keyevent])
            # 单击
            case actionType.click:
                button = capbutton(adb_device)
                action(adb_device, button, actionType.click)
                process.append([deepcopy(button), actionType.click])
            #偏移点击
            case actionType.click_offset:
                screen=capscreen(adb_device)
                button_basic = capbutton(adb_device,screen)
                button_target = capbutton(adb_device,screen)
                _, _, _, (startX_b, startY_b) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_basic, cv2.TM_CCOEFF_NORMED))
                _, _, _, (startX_t, startY_t) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_target, cv2.TM_CCOEFF_NORMED))
                
                process.append([[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],actionType.click_offset])
                action(adb_device,[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],actionType.click_offset)
            #延迟
            case actionType.delay:
                second = int(input("请输入秒数"))
                process.append(([second, actionType.delay]))
            #点击（可能存在）
            case actionType.click_possibly:
                button = capbutton(adb_device)
                action(adb_device, button,actionType.click_possibly)
                process.append([button,actionType.click_possibly])
            #自由滑动
            case actionType.common_swipe:
                swipe_range=draw_coordinate(capscreen(adb_device))
                directions=list(enumerate(swipedirection,start=1))
                c = input('\n'.join([f'{ind}.{i.value}' for ind,i in directions]+['请选择']))
                if c not in map(str,range(1,5)):
                    raise ValueError("输入不合法!")
                direction=directions[int(c)-1][1]

                action(adb_device, para=[direction,swipe_range],act=actionType.common_swipe)
                process.append([actionType.common_swipe,(direction,swipe_range,)])
            #划至桌面最右（脚本开始）
            case actionType.begin:
                action(adb_device, None, actionType.begin)
                process.append([None, actionType.begin])
            case actionType.swipe_offset:
                img=capscreen(adb_device)
                button=capbutton(img=img)
                directions=list(enumerate(swipedirection,start=1))
                c = input(
                    '\n'.join([f'{ind}.{i.value}' for ind,i in directions]+['请选择'])
                )
                if c not in map(str,range(1,5)):
                    raise ValueError("输入不合法!")
                direction=directions[int(c)-1][1]
                process.append([[direction,button],actionType.swipe_offset])
                action(adb_device,[direction,button],actionType.swipe_offset)

        process.append([random.uniform(2,4),actionType.delay])


def testTask():
    tasks = [i for i in os.listdir() if os.path.isfile(i) and i.endswith(".task")]
    if tasks == []:
        raise FileExistsError("当前目录没有task文件")
    with open(tasks[int(input("\n".join([f"{ind}.{i}" for ind, i in enumerate(tasks, start=1)]+ ["请输入序号"])))- 1],'rb') as f:
        task=pickle.load(f)
    for target, act in task:
        action(adb_device, target, act)

def get_ki_by_val(enum_class, value):
    for member in enum_class:
        if member.value == value:
            return member
    return None
    
def testdillTask():
    tasks = [i for i in os.listdir() if os.path.isfile(i) and i.endswith(".dill")]
    if tasks == []:
        raise FileExistsError("当前目录没有task文件")
    with open(tasks[int(input("\n".join([f"{ind}.{i}" for ind, i in enumerate(tasks, start=1)]+ ["请输入序号"])))- 1],'rb') as f:
        task=dill.load(f)
    for target, act in task:
        if act==actionType.common_swipe.value or act==actionType.swipe_offset.value:
            target[0]=get_ki_by_val(target[0])
        action(adb_device, target, get_ki_by_val(act))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QListWidget, QPushButton,
    QVBoxLayout, QWidget, QInputDialog, QMessageBox,QMenu
)
from PyQt6.QtCore import Qt
import sys

class TaskCreatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("自动化任务创建工具")
        self.setGeometry(100, 100, 600, 400)

        # 操作列表
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # 按钮区域
        self.btn_add = QPushButton("添加操作")
        self.btn_save = QPushButton("保存任务")
        self.btn_clear = QPushButton("清空列表")

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_clear)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 绑定事件
        self.btn_add.clicked.connect(self.add_action)
        self.btn_save.clicked.connect(self.save_task)
        self.btn_clear.clicked.connect(self.clear_list)

        self.actionList=list(actionType)
        self.directions=list(swipedirection)
    
    def show_context_menu(self,pos):
        menu = QMenu()
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(self.delete_select)
        menu.exec(self.list_widget.viewport().mapToGlobal(pos))

    def add_action(self):

        act, ok = QInputDialog.getItem(
            self, "选择操作", "请选择要添加的操作类型:", [item.value for item in self.actionList], editable=False
        )
        act=get_ki_by_val(actionType,act)
        if ok and act:
            match act:
                # Home/返回键
                case actionType.keyevent:
                    key,ok=QInputDialog.getItem(self,"选择按键","选择按键",["HOME","BACK"],editable=False)
                    if ok :
                        action(adb_device, key, act)
                        self.process.append([key, act.value])
                        self.list_widget.addItem(f"实体键{key}")
                # 单击
                case actionType.click:
                    button = capbutton(adb_device)
                    action(adb_device, button, act)
                    self.process.append([deepcopy(button), act.value])
                    self.list_widget.addItem(f"点击图像")
                #偏移点击
                case actionType.click_offset:
                    screen=capscreen(adb_device)
                    button_basic = capbutton(adb_device,screen)
                    button_target = capbutton(adb_device,screen)
                    _, _, _, (startX_b, startY_b) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_basic, cv2.TM_CCOEFF_NORMED))
                    _, _, _, (startX_t, startY_t) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_target, cv2.TM_CCOEFF_NORMED))
                    
                    self.process.append([[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],act.value])
                    action(adb_device,[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],act)
                    self.list_widget.addItem(f"偏移点击")
                #延迟
                case actionType.delay:
                    second,ok =QInputDialog.getInt(self,"延迟时间","秒数")
                    if ok:
                        self.process.append(([second, act.value]))
                        self.list_widget.addItem(f"延迟{second}秒")
                #点击（可能存在）
                case actionType.click_possibly:
                    button = capbutton(adb_device)
                    action(adb_device, button,act)
                    self.process.append([button,act.value])
                    self.list_widget.addItem(f"尝试点击可能存在的图像")
                #自由滑动
                case actionType.common_swipe:
                    swipe_range=draw_coordinate(capscreen(adb_device))
                    direction_str,ok= QInputDialog.getItem(self,"选择方向","选择方向",[i.value for i in self.directions],editable=False)
                    if ok:
                        direction=get_ki_by_val(swipedirection,direction_str)
                        action(adb_device, para=(direction,swipe_range),act=act)
                        self.process.append([act.value,(direction_str,swipe_range,)])
                        self.list_widget.addItem(f"滑动屏幕区域，方向{direction_str} ; X from {swipe_range[1][0]} to {swipe_range[1][1]},Y from {swipe_range[0][0]} to {swipe_range[0][1]}")

                case actionType.begin:
                    action(adb_device, None, act)
                    self.process.append([None, act.value])
                    self.list_widget.addItem("回到桌面最右")

                case actionType.swipe_offset:
                    img=capscreen(adb_device)
                    button=capbutton(img=img)
                    direction_str,ok= QInputDialog.getItem(self,"选择方向","选择方向",[d.value for d in self.directions],editable=False)
                    direction=get_ki_by_val(swipedirection,direction_str)
                    action(adb_device,[direction,button],act)

                    self.process.append([[direction_str,button],act.value])
                    self.list_widget.addItem(f"滑动图像,方向{direction.value}")

    def save_task(self):
        if not self.process:
            QMessageBox.warning(self, "错误", "任务列表为空！")
            return
        
        filename, _ = QInputDialog.getText(
            self, "保存任务", "输入任务文件名（无需后缀）:"
        )
        if filename:
            with open(f"{filename}.dill", "wb") as f:
                dill.dump(self.process, f)
            QMessageBox.information(self, "成功", f"任务已保存为 {filename}.dill")

    def clear_list(self):
        self.process.clear()
        self.list_widget.clear()
    def delete_select(self, widget):
        """删除列表中的选定项"""
        # 获取当前选中的行索引
        selected_row = self.list_widget.currentRow()
        
        if selected_row == -1:  # 未选中任何项
            QMessageBox.warning(self, "错误", "请先选择要删除的操作项！")
            return
        
        # 同步删除数据和列表项
        del self.process[selected_row]
        self.list_widget.takeItem(selected_row)
def TaskCreator():
    app = QApplication(sys.argv)
    window = TaskCreatorGUI()
    window.show()
    sys.exit(app.exec())

if __name__=="__main__":
    TaskCreator()

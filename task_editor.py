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


def capscreen(device):
    return cv2.cvtColor(np.array(device.screenshot()), cv2.COLOR_BGR2GRAY)


def capbutton(device=None,img=None):
    if img is None:
        img=capscreen(device)
    sub_img,*_=cut(img)
    return sub_img


def clickbutton(adb_device, img,offset=None,max_retry=3):
    """img为图像,offset包括了坐标偏移个区域大小"""
    for _ in range(max_retry):
        _, maxVal, _, (startX, startY) = cv2.minMaxLoc(
            cv2.matchTemplate(capscreen(adb_device), img, cv2.TM_CCOEFF_NORMED)
        )
        if maxVal > 0.7:
            break
        time.sleep(2)
    if offset is None:
        endX, endY = startX + img.shape[1], startY + img.shape[0]
    else:
        (offset_X,offset_Y),(len_X,len_Y)=offset
        startX,startY=startX+offset_X,startY+offset_Y
        endX,endY=startX+len_X,startY+len_Y
    adb_device.click(random.randint(startX, endX),random.randint(startY, endY))


class actionType(Enum):
    click = '点击'
    click_offset ='偏移点击'
    click_possibly ='尝试点击'
    keyevent = '实体按键'
    common_swipe = '屏幕滑动'
    swipe_offset='图片滑动'
    delay = '延迟'
    begin = '回到桌面最右'

class swipedirection(Enum):
    up="上"
    down="下"
    right="右"
    left="左"


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


def testTask():
    tasks = [i for i in os.listdir() if os.path.isfile(i) and i.endswith(".task")]
    if tasks == []:
        raise FileExistsError("当前目录没有task文件")
    with open(tasks[int(input("\n".join([f"{ind}.{i}" for ind, i in enumerate(tasks, start=1)]+ ["请输入序号"])))- 1],'rb') as f:
        task=pickle.load(f)
    for target, act in task:
        perform(adb_device, target, act)

def get_enum_value(enum_class, value):
    return next((member for member in enum_class if member.value == value), None)
    
def testdillTask():
    tasks = [i for i in os.listdir() if os.path.isfile(i) and i.endswith(".dill")]
    if tasks == []:
        raise FileExistsError("当前目录没有dill文件")
    with open(tasks[int(input("\n".join([f"{ind}.{i}" for ind, i in enumerate(tasks, start=1)]+ ["请输入序号"])))- 1],'rb') as f:
        task=dill.load(f)
    for target, act,*_ in task:
        if act==actionType.common_swipe.value or act==actionType.swipe_offset.value:
            target[0]=get_enum_value(target[0])
        perform(adb_device, target, get_enum_value(actionType,act))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QListWidget, QPushButton,QFrame,QLabel,
    QVBoxLayout, QWidget, QInputDialog, QMessageBox,QMenu,QHBoxLayout
)
from PyQt6.QtCore import Qt,QDateTime,QTimer
import sys

class TaskCreatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.operate_list = []
        self.tasks_list=[]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.init_ui()
        self.updateTaskMenu()

        self.actionList=list(actionType)
        self.directions=list(swipedirection)

    def init_ui(self):
        self.setWindowTitle("自动化任务创建工具")
        self.setGeometry(100, 100, 800, 400)

        # 创建主水平布局容器
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # ================= 左侧面板 =================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 时间显示模块
        time_frame = QFrame()
        time_frame.setFrameShape(QFrame.Shape.Box)
        time_layout = QVBoxLayout(time_frame)
        
        self.time_label = QLabel("当前时间：")
        self.time_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.time_display = QLabel()
        self.time_display.setStyleSheet("font-size: 16px; color: #2c3e50;")
        self.time_display.setMinimumWidth(200)
        
        self.update_time()
        self.timer.start(1000)  # 每秒更新一次
        
        #任务显示模块
        self.tasks_list_widge=QListWidget()
        self.tasks_list_widge.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tasks_list_widge.customContextMenuRequested.connect(self.show_task_menu)

        self.refresh_button = QPushButton("刷新")

        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.time_display)
        left_layout.addWidget(time_frame)
        left_layout.addWidget(self.tasks_list_widge)
        left_layout.addWidget(self.refresh_button)

        self.refresh_button.clicked.connect(self.updateTaskMenu)

    
        # ================= 右侧原有界面 =================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 操作列表
        self.operate_list_widget = QListWidget()
        self.operate_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.operate_list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # 按钮区域
        self.btn_add = QPushButton("添加操作")
        self.btn_save = QPushButton("保存任务")
        self.btn_clear = QPushButton("清空列表")

        # 布局
        right_layout.addWidget(self.operate_list_widget)
        right_layout.addWidget(self.btn_add)
        right_layout.addWidget(self.btn_save)
        right_layout.addWidget(self.btn_clear)

        # 绑定事件
        self.btn_add.clicked.connect(self.add_action)
        self.btn_save.clicked.connect(self.save_task)
        self.btn_clear.clicked.connect(self.clear_list)



        # =====将左右面板加入主布局=====
        main_layout.addWidget(left_panel, stretch=1)   # 左侧占1份空间
        main_layout.addWidget(right_panel, stretch=3)  # 右侧占3份空间
        
        self.setCentralWidget(main_widget)

    def update_time(self):
        """更新时间显示"""
        current_time = QDateTime.currentDateTime()
        formatted_time = current_time.toString("yyyy-MM-dd HH:mm")
        self.time_display.setText(formatted_time)

    def updateTaskMenu(self):
        self.tasks_list_widge.clear()
        self.tasks_list = [i for i in os.listdir() if os.path.isfile(i) and i.endswith(".dill")]
        for task in self.tasks_list:
            self.tasks_list_widge.addItem(task.rstrip('.dill'))

    def show_context_menu(self,pos):
        menu = QMenu()
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(self.delete_select)
        menu.exec(self.operate_list_widget.viewport().mapToGlobal(pos))

    def show_task_menu(self,pos):
        menu = QMenu()
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(self.delete_task)
        load_action=menu.addAction("加载")
        load_action.triggered.connect(self.loadAction)
        menu.exec(self.tasks_list_widge.viewport().mapToGlobal(pos))

    def loadAction(self):
        selected=self.tasks_list[self.tasks_list_widge.currentRow()]
        self.clear_list()
        with open(selected ,'rb') as file:
            self.operate_list=dill.load(file)
            for item in self.operate_list:
                self.operate_list_widget.addItem(item[2])

    def delete_task(self):
        """删除选定任务"""
        selected_row = self.tasks_list_widge.currentRow()
        os.remove(self.tasks_list[selected_row])
        del self.tasks_list[selected_row]
        self.tasks_list_widge.takeItem(selected_row)
        
    def delete_select(self):
        """删除列表中的选定项"""
        selected_row = self.operate_list_widget.currentRow()
        
        if selected_row == -1:
            QMessageBox.warning(self, "错误", "请先选择要删除的操作项！")
            return
        
        del self.operate_list[selected_row]
        self.operate_list_widget.takeItem(selected_row)


    def add_action(self):

        operate, ok = QInputDialog.getItem(
            self, "选择操作", "请选择要添加的操作类型:", [item.value for item in self.actionList], editable=False
        )
        operate=get_enum_value(actionType,operate)
        if ok and operate:
            match operate:
                # Home/返回键
                case actionType.keyevent:
                    key,ok=QInputDialog.getItem(self,"选择按键","选择按键",["HOME","BACK"],editable=False)
                    if ok :
                        perform(adb_device, key, operate)
                        self.operate_list.append([key, operate.value,f"实体键{key}"])
                        self.operate_list_widget.addItem(f"实体键{key}")
                # 单击
                case actionType.click:
                    button = capbutton(device=adb_device)
                    perform(adb_device, button, operate)
                    self.operate_list.append([deepcopy(button), operate.value,"点击图像"])
                    self.operate_list_widget.addItem("点击图像")
                #偏移点击
                case actionType.click_offset:
                    screen=capscreen(device=adb_device)
                    button_basic = capbutton(img=screen)
                    button_target = capbutton(img=screen)
                    
                    _, _, _, (startX_b, startY_b) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_basic, cv2.TM_CCOEFF_NORMED))
                    _, _, _, (startX_t, startY_t) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_target, cv2.TM_CCOEFF_NORMED))
                    
                    self.operate_list.append([[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],operate.value,"偏移点击"])
                    perform(adb_device,[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],operate)
                    self.operate_list_widget.addItem("偏移点击")
                #延迟
                case actionType.delay:
                    second,ok =QInputDialog.getInt(self,"延迟时间","秒数")
                    if ok:
                        self.operate_list.append(([second, operate.value,f"延迟{second}秒"]))
                        self.operate_list_widget.addItem(f"延迟{second}秒")
                #点击（可能存在）
                case actionType.click_possibly:
                    button = capbutton(adb_device)
                    perform(adb_device, button,operate)
                    self.operate_list.append([button,operate.value,"尝试点击可能存在的图像"])
                    self.operate_list_widget.addItem(f"尝试点击可能存在的图像")
                #自由滑动
                case actionType.common_swipe:
                    _,_,*swipe_range=cut(capscreen(adb_device),return_start_pos=True,return_end_pos=True)
                    transpose=lambda x:list(map(list,zip(*x)))
                    swipe_range=transpose(swipe_range)
                    direction_str,ok= QInputDialog.getItem(self,"选择方向","选择方向",[i.value for i in self.directions],editable=False)
                    if ok:
                        direction=get_enum_value(swipedirection,direction_str)
                        perform(adb_device, params=(direction,swipe_range),act=operate)
                        self.operate_list.append([operate.value,direction_str,swipe_range,f"滑动屏幕区域，方向{direction_str} ;区域 X from {swipe_range[1][0]} to {swipe_range[1][1]},Y from {swipe_range[0][0]} to {swipe_range[0][1]}"])
                        self.operate_list_widget.addItem(f"滑动屏幕区域，方向{direction_str} ;区域 X from {swipe_range[1][0]} to {swipe_range[1][1]},Y from {swipe_range[0][0]} to {swipe_range[0][1]}")

                case actionType.begin:
                    perform(adb_device, None, operate)
                    self.operate_list.append([None, operate.value,"回到桌面最右"])
                    self.operate_list_widget.addItem("回到桌面最右")

                case actionType.swipe_offset:
                    img=capscreen(adb_device)
                    button=capbutton(img=img)
                    direction_str,ok= QInputDialog.getItem(self,"选择方向","选择方向",[d.value for d in self.directions],editable=False)
                    direction=get_enum_value(swipedirection,direction_str)
                    perform(adb_device,[direction,button],operate)

                    self.operate_list.append([[direction_str,button],operate.value,f"滑动图像,方向{direction.value}"])
                    self.operate_list_widget.addItem(f"滑动图像,方向{direction.value}")

    def save_task(self):
        if not self.operate_list:
            QMessageBox.warning(self, "错误", "任务列表为空！")
            return
        
        filename, _ = QInputDialog.getText(
            self, "保存任务", "输入任务文件名（无需后缀）:"
        )
        if filename:
            with open(f"{filename}.dill", "wb") as f:
                dill.dump(self.operate_list, f)
            QMessageBox.information(self, "成功", f"任务已保存为 {filename}.dill")

    def clear_list(self):
        self.operate_list.clear()
        self.operate_list_widget.clear()


def TaskCreator():
    app = QApplication(sys.argv)
    window = TaskCreatorGUI()
    window.show()
    sys.exit(app.exec())

if __name__=="__main__":
    TaskCreator()

from copy import deepcopy
import os
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QPushButton,QFrame,QLabel,
    QVBoxLayout, QWidget, QInputDialog, QMessageBox,QMenu,QHBoxLayout
)
from PyQt6.QtCore import Qt,QDateTime,QTimer,QThread, pyqtSignal

import cv2
import dill

from cut_img import cut
from enum_classes import actionType, swipedirection
from func import capbutton, capscreen, get_enum_value, perform

class TaskManagerGUI(QMainWindow):
    def __init__(self,device):
        super().__init__()
        self.adb_divice=device
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

    
        # ================= 中间界面 =================
        operater_panel = QWidget()
        operater_layout = QVBoxLayout(operater_panel)

        # 操作列表
        self.operate_list_widget = QListWidget()
        self.operate_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.operate_list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # 按钮区域
        self.btn_add = QPushButton("添加操作")
        self.btn_clear = QPushButton("清空列表")

        # 布局
        operater_layout.addWidget(self.operate_list_widget)
        operater_layout.addWidget(self.btn_add)
        operater_layout.addWidget(self.btn_clear)

        # 绑定事件
        self.btn_add.clicked.connect(self.add_action)
        self.btn_clear.clicked.connect(self.clear_list)

        # ================= 编辑控制界面 =================
        editor_and_test_panel=QWidget()
        editor_and_test_layout=QVBoxLayout(editor_and_test_panel)
        editor_and_test_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.btn_save = QPushButton("保存任务")
        self.test=QPushButton("测试任务")
        editor_and_test_layout.addWidget(self.btn_save)
        editor_and_test_layout.addWidget(self.test)
        self.btn_save.clicked.connect(self.save_task)
        self.test.clicked.connect(self.start_test_task)

        # =====将面板加入主布局=====
        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(operater_panel, stretch=2)
        main_layout.addWidget(editor_and_test_panel,stretch=1)
        
        self.setCentralWidget(main_widget)

    def start_test_task(self):
        self.test_thread = TestTaskThread(self.operate_list, self.adb_divice,self)
        self.test_thread.start()
    def set_operate_index(self, index:int):
        self.operate_list_widget.setCurrentRow(index)

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
                        perform(self.adb_divice, key, operate)
                        self.operate_list.append([key, operate.value,f"实体键{key}"])
                        self.operate_list_widget.addItem(f"实体键{key}")
                # 单击
                case actionType.click:
                    button = capbutton(device=self.adb_divice)
                    perform(self.adb_divice, button, operate)
                    self.operate_list.append([deepcopy(button), operate.value,"点击图像"])
                    self.operate_list_widget.addItem("点击图像")
                #偏移点击
                case actionType.click_offset:
                    screen=capscreen(device=self.adb_divice)
                    button_basic = capbutton(img=screen)
                    button_target = capbutton(img=screen)
                    
                    _, _, _, (startX_b, startY_b) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_basic, cv2.TM_CCOEFF_NORMED))
                    _, _, _, (startX_t, startY_t) = cv2.minMaxLoc(cv2.matchTemplate(screen, button_target, cv2.TM_CCOEFF_NORMED))
                    
                    self.operate_list.append([[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],operate.value,"偏移点击"])
                    perform(self.adb_divice,[button_basic,(startX_t-startX_b,startY_t-startY_b),button_target.shape],operate)
                    self.operate_list_widget.addItem("偏移点击")
                #延迟
                case actionType.delay:
                    second,ok =QInputDialog.getInt(self,"延迟时间","秒数")
                    if ok:
                        self.operate_list.append(([second, operate.value,f"延迟{second}秒"]))
                        self.operate_list_widget.addItem(f"延迟{second}秒")
                #点击（可能存在）
                case actionType.click_possibly:
                    button = capbutton(self.adb_divice)
                    perform(self.adb_divice, button,operate)
                    self.operate_list.append([button,operate.value,"尝试点击可能存在的图像"])
                    self.operate_list_widget.addItem(f"尝试点击可能存在的图像")
                #自由滑动
                case actionType.common_swipe:
                    _,_,*swipe_range=cut(capscreen(self.adb_divice),return_start_pos=True,return_end_pos=True)
                    transpose=lambda x:list(map(list,zip(*x)))
                    swipe_range=transpose(swipe_range)
                    direction_str,ok= QInputDialog.getItem(self,"选择方向","选择方向",[i.value for i in self.directions],editable=False)
                    if ok:
                        direction=get_enum_value(swipedirection,direction_str)
                        perform(self.adb_divice, params=(direction,swipe_range),act=operate)
                        self.operate_list.append([[direction_str,swipe_range],operate.value,f"滑动屏幕区域，方向{direction_str} ;区域 X from {swipe_range[1][0]} to {swipe_range[1][1]},Y from {swipe_range[0][0]} to {swipe_range[0][1]}"])
                        self.operate_list_widget.addItem(f"滑动屏幕区域，方向{direction_str} ;区域 X from {swipe_range[1][0]} to {swipe_range[1][1]},Y from {swipe_range[0][0]} to {swipe_range[0][1]}")

                case actionType.begin:
                    perform(self.adb_divice, None, operate)
                    self.operate_list.append([None, operate.value,"回到桌面最右"])
                    self.operate_list_widget.addItem("回到桌面最右")

                case actionType.swipe_offset:
                    img=capscreen(self.adb_divice)
                    button=capbutton(img=img)
                    direction_str,ok= QInputDialog.getItem(self,"选择方向","选择方向",[d.value for d in self.directions],editable=False)
                    direction=get_enum_value(swipedirection,direction_str)
                    perform(self.adb_divice,[direction,button],operate)

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

class TestTaskThread(QThread):
    def __init__(self, operate_list, adb_device,manager=None):
        super().__init__()
        self.operate_list = operate_list
        self.adb_device = adb_device
        self.manager =manager

    def run(self):
        for index, (target, act, *_) in enumerate(self.operate_list):
            if act == actionType.common_swipe.value or act == actionType.swipe_offset.value:
                target[0] = get_enum_value(swipedirection, target[0])
            perform(self.adb_device, target, get_enum_value(actionType, act))
            if self.manager:
                self.manager.set_operate_index(index)
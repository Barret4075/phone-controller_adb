from enum import Enum
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

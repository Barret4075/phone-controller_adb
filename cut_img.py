import cv2
import numpy as np
from copy import deepcopy


class cut_img:
    def __init__(
        self,
        img_file: np.ndarray,
        scale=0.34,
        draw=False,
    ):
        """imgfile:单通道灰度值图像\n
        scale:比例
        """
        self.scale = scale
        self.img = img_file
        if len(self.img.shape) > 2:
            self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        self.resized_img = cv2.resize(self.img, dsize=None, fx=scale, fy=scale)
        self.sub_img = None

        self.show_marked_img = False

        self.notdone = True
        # 原图标记
        self.draw_on_ori = draw
        # 坐标标记
        self.start_x, self.start_y, self.end_x, self.end_y = 0, 0, 0, 0
        # 在缩略图上的坐标标记
        self.ori_x, self.ori_y = 0, 0
        # 放大镜
        self.magnifier_range = 60
        self.magnifier_scale = 4

    def save_img(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.notdone = False
            return

    def draw(self, event, x, y, flags, params):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.ori_x, self.ori_y = x, y
            self.start_x, self.start_y = round(x / self.scale), round(y / self.scale)
            self.show_marked_img = True
        if event == cv2.EVENT_LBUTTONUP:
            if x == self.ori_x or y == self.ori_y:
                return
            self.end_x, self.end_y = round(x / self.scale), round(y / self.scale)
            self.sub_img = self.img[
                min(self.start_y, self.end_y) : max(self.start_y, self.end_y),
                min(self.start_x, self.end_x) : max(self.start_x, self.end_x),
            ]
            self.show_marked_img = False
            if self.draw_on_ori:
                marked = deepcopy(self.resized_img)
                cv2.rectangle(marked, (self.ori_x, self.ori_y), (x, y), (0, 0, 160), 1)
                cv2.imshow("image", marked)
            else:
                cv2.imshow("image", self.resized_img)

            cv2.imshow("click to save", self.sub_img)
            cv2.setMouseCallback("click to save", self.save_img)
        if event == cv2.EVENT_MOUSEMOVE:
            if self.show_marked_img:
                marked_img = deepcopy(self.resized_img)
                cv2.rectangle(
                    marked_img, (self.ori_x, self.ori_y), (x, y), (0, 0, 160), 1
                )
                cv2.imshow("image", marked_img)
            # magnifier
            round_x, round_y = round(x / self.scale), round(y / self.scale)
            size_img = self.img.shape
            bordered_img = np.zeros(
                (
                    size_img[0] + 2 * self.magnifier_range,
                    size_img[1] + 2 * self.magnifier_range,
                ),
                dtype=np.uint8,
            )
            bordered_img[
                self.magnifier_range : self.magnifier_range + size_img[0],
                self.magnifier_range : self.magnifier_range + size_img[1],
            ] = self.img
            o_img = bordered_img[
                round_y : round_y + 2 * self.magnifier_range,
                round_x : round_x + 2 * self.magnifier_range,
            ]
            magnifier_img = cv2.resize(
                o_img,
                dsize=None,
                fx=self.magnifier_scale,
                fy=self.magnifier_scale,
            )
            cv2.line(
                magnifier_img,
                (0, self.magnifier_range * self.magnifier_scale),
                (
                    2 * self.magnifier_range * self.magnifier_scale,
                    self.magnifier_range * self.magnifier_scale,
                ),
                (120, 10, 120),
                1,
            )
            cv2.line(
                magnifier_img,
                (self.magnifier_range * self.magnifier_scale, 0),
                (
                    self.magnifier_range * self.magnifier_scale,
                    2 * self.magnifier_range * self.magnifier_scale,
                ),
                (120, 10, 120),
                1,
            )
            cv2.putText(
                magnifier_img,
                f"ori_x={x},ori_y={y}",
                [10, 30],
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (120, 120, 30),
                2,
            )
            cv2.putText(
                magnifier_img,
                f"x={round(x/self.scale)},y={round(y/self.scale)}",
                [10, 70],
                cv2.FONT_HERSHEY_SIMPLEX,
                1.4,
                (120, 120, 100),
                2,
            )
            cv2.imshow("magnifier", magnifier_img)

    def cut_img(self, return_start_pos=False, return_end_pos=False):
        """return img(np.ndarray) shape(tuple) [(start_y,start_x)] [(end_y,end_x)]"""
        cv2.imshow("image", self.resized_img)
        cv2.setMouseCallback("image", self.draw)
        while self.notdone:
            cv2.waitKey(1)
        cv2.destroyAllWindows()
        yield self.sub_img
        yield self.sub_img.shape
        if return_start_pos:
            yield (min(self.start_y, self.end_y), min(self.start_x, self.end_x))
        if return_end_pos:
            yield (max(self.start_y, self.end_y), max(self.start_x, self.end_x))

    def draw_coordinate_shape(self) -> tuple:
        cv2.imshow("image", self.resized_img)
        cv2.setMouseCallback("image", self.draw)
        while self.notdone:
            cv2.waitKey(100)
        cv2.destroyAllWindows()
        return


def cut(img, *args, **kwargs):
    """
    :param img: 原图 np.ndarray
    :param return_start_pos: 是否返回起始坐标(左上角)boolen
    :param return_end_pos: 是否返回结束坐标(右下角)boolen

    :return img: 子图 np.ndarray
    :return shape: 子图shape tuple
    :return start_pos: (start_y,start_x)
    :return end_pos: (end_y,end_x)
    """
    sub_img = cut_img(img, draw=True)
    return sub_img.cut_img(*args, **kwargs)


if __name__ == "__main__":
    img = cv2.cvtColor(np.array(cv2.imread("screen.png")), cv2.COLOR_RGB2GRAY)
    print(img.shape)
    img, shape, (sx, sy), (ex, ey) = cut(
        img, return_start_pos=True, return_end_pos=True
    )
    print(shape, sx, sy, ex, ey)

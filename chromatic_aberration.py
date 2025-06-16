import cv2
import numpy as np
from PIL import Image, ImageGrab, ImageTk
import tkinter as tk
from tkinter import ttk


def is_pil_image(obj):
    return isinstance(obj, Image.Image)


def apply_chromatic_aberration(img_array, shift_amount):
    # 拆分通道
    b, g, r = cv2.split(img_array)

    # 创建偏移后的红色和蓝色通道
    rows, cols = img_array.shape[:2]

    # 向右下方偏移红色通道
    r_shifted = np.roll(r, shift=shift_amount, axis=(0, 1))

    # 向左上方偏移蓝色通道
    b_shifted = np.roll(b, shift=-shift_amount, axis=(0, 1))

    # 重新合并图像
    aberrated_img = cv2.merge([b_shifted, g, r_shifted])
    aberrated_img = cv2.cvtColor(aberrated_img, cv2.COLOR_BGR2RGB)
    result_image = Image.fromarray(aberrated_img)

    return result_image

def apply_chromatic_aberration_v2(img_array, shift_amount):
    b, g, r = cv2.split(img_array)
    rows, cols = img_array.shape[:2]

    def shift(ch, dx, dy):
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(ch, M, (cols, rows), borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    r_shifted = shift(r, shift_amount, shift_amount)
    b_shifted = shift(b, -shift_amount, -shift_amount)

    merged = cv2.merge([b_shifted, g, r_shifted])
    return Image.fromarray(cv2.cvtColor(merged, cv2.COLOR_BGR2RGB))

import random

def apply_chromatic_aberration_v5(img_array, base_shift=3):
    b, g, r = cv2.split(img_array)
    rows, cols = img_array.shape[:2]

    def shift(ch, dx, dy):
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(ch, M, (cols, rows), borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    # 随机偏移
    r_dx, r_dy = random.randint(base_shift-1, base_shift+1), random.randint(base_shift-1, base_shift+1)
    b_dx, b_dy = random.randint(-base_shift-1, -base_shift+1), random.randint(-base_shift-1, -base_shift+1)

    r_shifted = shift(r, r_dx, r_dy)
    b_shifted = shift(b, b_dx, b_dy)

    merged = cv2.merge([b_shifted, g, r_shifted])
    return Image.fromarray(cv2.cvtColor(merged, cv2.COLOR_BGR2RGB))

class ChromaticApp:
    def __init__(self, root):
        self.root = root
        self.original_img = self.load_from_clipboard()
        if self.original_img is None:
            root.destroy()
            return

        # 转为 OpenCV 数组供处理用
        self.cv_img = np.array(self.original_img.convert('RGB'))
        self.cv_img = self.cv_img[:, :, ::-1]  # RGB -> BGR

        # 设置GUI
        self.root.title("Chromatic Aberration Viewer")

        self.panel = tk.Label(root)
        self.panel.pack()

        # 滑块控件
        self.shift_var = tk.IntVar(value=5)
        self.slider = ttk.Scale(
            root,
            from_=0,
            to=20,
            orient='horizontal',
            variable=self.shift_var,
            command=self.update_image
        )
        self.slider.pack(fill='x', padx=10, pady=10)

        self.label = tk.Label(root, text="Shift Amount: 5")
        self.label.pack()

        # 初始显示
        self.update_image(None)

    def load_from_clipboard(self):
        clipboard_image = ImageGrab.grabclipboard()
        if clipboard_image is None:
            print("剪贴板中没有图像。")
            return None
        elif is_pil_image(clipboard_image):
            return clipboard_image
        elif isinstance(clipboard_image, list) and len(clipboard_image) == 1:
            try:
                return Image.open(clipboard_image[0])
            except Exception as e:
                print(e)
                return None
        return None

    def update_image(self, event=None):
        shift_amount = self.shift_var.get()
        self.label.config(text=f"Shift Amount: {shift_amount}")

        result_image = apply_chromatic_aberration_v5(self.cv_img, shift_amount)

        # 缩放图像以便显示（如果太大）
        w, h = result_image.size
        max_size = 800
        scale = min(max_size / w, max_size / h, 1)
        resized_img = result_image.resize((int(w * scale), int(h * scale)))

        # 显示图像
        self.tk_image = ImageTk.PhotoImage(resized_img)
        self.panel.config(image=self.tk_image)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChromaticApp(root)
    root.mainloop()
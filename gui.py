import tkinter as tk
from PIL import Image, ImageTk, ImageGrab
import app

# 创建 Tkinter 窗口
window = tk.Tk()
window.title("图片显示窗口")

# 创建多行文本输入框
text_input = tk.Text(window)
text_input.pack()

# 创建显示图片的控件
image_label = tk.Label(window)
image_label.pack()

# 定义处理粘贴事件的函数
def handle_paste(event):
    # 获取剪贴板内容
    clipboard_image = ImageGrab.grabclipboard()
    text_input.delete('1.0', tk.END)

    if clipboard_image is None:
        text_input.insert(tk.END, "Not Image")
    else:
        result = app.image_to_wd14_tags(clipboard_image, 'wd14-convnext', 0.35, False, True, False, True)
        text_input.insert(tk.END, result)

# 绑定 Ctrl + V 快捷键和处理函数
window.bind('<Control-v>', handle_paste)

# 运行主循环
window.mainloop()

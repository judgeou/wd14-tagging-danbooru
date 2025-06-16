from PIL import Image, ImageChops, ImageGrab
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk

class ChromaticAberrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("色差效果调节器")
        
        # 保存当前图片
        self.current_image = None
        self.photo = None
        
        # 创建界面元素
        self.create_widgets()
        
        # 添加键盘绑定
        self.root.bind('<Control-v>', self.paste_image)
    
    def create_widgets(self):
        # 创建滑动条框架
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10)
        
        # 创建强度滑动条
        ttk.Label(control_frame, text="色差强度:").pack(side=tk.LEFT)
        self.strength_var = tk.DoubleVar(value=3.0)
        self.strength_slider = ttk.Scale(
            control_frame,
            from_=0,
            to=10,
            variable=self.strength_var,
            orient=tk.HORIZONTAL,
            length=200,
            command=self.update_image
        )
        self.strength_slider.pack(side=tk.LEFT, padx=5)
        
        # 创建按钮框架
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=5)
        
        # 添加保存按钮
        self.save_button = ttk.Button(button_frame, text="保存图片", command=self.save_image)
        self.save_button.pack(pady=5)
        
        # 创建图片显示区域
        self.image_label = ttk.Label(self.root)
        self.image_label.pack(pady=10)
        
        # 创建提示标签
        self.status_label = ttk.Label(self.root, text="请复制图片到剪贴板")
        self.status_label.pack(pady=5)
    
    def chromatic_aberration(self, image, strength):
        # 分离颜色通道
        r, g, b = image.split()
        
        # 根据滑动条值设置位移量
        shift_x = int(strength)
        
        # 对红色和蓝色通道进行反向位移
        r_shifted = ImageChops.offset(r, shift_x, 0)
        g_shifted = g  # 保持绿色通道不变
        b_shifted = ImageChops.offset(b, -shift_x, 0)
        
        # 处理边界
        r_shifted.paste(0, (0, 0, shift_x, r_shifted.height))
        b_shifted.paste(0, (b_shifted.width - shift_x, 0, b_shifted.width, b_shifted.height))
        
        # 合并颜色通道
        result = Image.merge('RGB', (r_shifted, g_shifted, b_shifted))
        
        return result
    
    def update_image(self, *args):
        if self.current_image:
            # 应用色差效果
            result = self.chromatic_aberration(self.current_image, self.strength_var.get())
            
            # 调整图片大小以适应显示
            display_size = (800, 600)  # 可以根据需要调整
            result.thumbnail(display_size, Image.Resampling.LANCZOS)
            
            # 更新显示
            self.photo = ImageTk.PhotoImage(result)
            self.image_label.configure(image=self.photo)
    
    def paste_image(self, event=None):
        """处理粘贴事件"""
        clipboard_image = ImageGrab.grabclipboard()
        if clipboard_image is not None:
            if is_pil_image(clipboard_image):
                self.current_image = clipboard_image
            elif len(clipboard_image) == 1:
                self.current_image = Image.open(clipboard_image[0])
            
            if self.current_image:
                self.status_label.configure(text="图片已加载")
                self.update_image()
    
    def save_image(self):
        """保存当前图片"""
        if self.current_image and hasattr(self, 'photo'):
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG 文件", "*.png"),
                    ("JPEG 文件", "*.jpg"),
                    ("所有文件", "*.*")
                ]
            )
            if file_path:
                # 获取当前效果的图片
                result = self.chromatic_aberration(self.current_image, self.strength_var.get())
                result.save(file_path)
                self.status_label.configure(text="图片已保存")

def is_pil_image(obj):
    return isinstance(obj, Image.Image)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChromaticAberrationApp(root)
    root.mainloop()
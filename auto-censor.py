from PIL import Image, ImageGrab
import numpy as np
from app import image_to_wd14_tags
import cv2
import io
import win32clipboard
from io import BytesIO

def is_pil_image(obj):
    return isinstance(obj, Image.Image)

def detect_skin_regions(image_cv):
    # 将图像转换为HSV颜色空间
    hsv = cv2.cvtColor(image_cv, cv2.COLOR_BGR2HSV)
    
    # 定义肤色范围
    lower_skin = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    
    # 创建肤色掩码
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
    
    # 使用形态学操作去除噪声
    kernel = np.ones((5,5), np.uint8)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    
    # 找到轮廓
    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 过滤掉太小的区域
    min_area = 1000
    valid_regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            valid_regions.append((x, y, w, h))
    
    return valid_regions

def censor_image(image, tags):
    # 定义需要打码的NSFW标签
    nsfw_tags = ['nipples', 'pussy', 'monochrome', 'female_pubic_hair', 'penis']
    
    # 检查是否有NSFW标签
    has_nsfw = any(tag in tags for tag in nsfw_tags)
    
    if has_nsfw:
        # 将PIL图像转换为OpenCV格式
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 检测肤色区域
        regions = detect_skin_regions(image_cv)
        
        # 对检测到的区域进行打码
        for (x, y, w, h) in regions:
            # 创建打码区域
            mask = Image.new('RGBA', (w, h), (0, 0, 0, 128))
            # 将打码区域粘贴到原图上
            image.paste(mask, (x, y), mask)
    
    return image

def image_to_clipboard(image):
    output = BytesIO()
    image.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # 去掉BMP文件头
    output.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

while True:
    clipboard_image = ImageGrab.grabclipboard()
    if clipboard_image is None:
        print("Not Image")
    else:
        if is_pil_image(clipboard_image):
            image = clipboard_image
        elif len(clipboard_image) == 1:
            image = Image.open(clipboard_image[0])
        
        # 检测NSFW内容
        tags, _ = image_to_wd14_tags(image, 'wd14-convnext', 0.35, False, True, False, True)
        # 对NSFW内容进行打码
        censored_image = censor_image(image, tags)
        # 将打码后的图片复制到剪贴板
        image_to_clipboard(censored_image)
        
    input('wait your image')
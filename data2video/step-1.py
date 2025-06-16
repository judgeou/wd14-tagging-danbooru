import numpy as np
from PIL import Image
import math
import hashlib

def file_to_png_with_numpy(file_path, image_path):
    with open(file_path, "rb") as file:
        hash = hashlib.sha256(file.read())
    # 读取文件数据
    with open(file_path, "rb") as file:
        data = np.frombuffer(file.read(), dtype=np.uint8)

    data_len = len(data)
    len_info = np.array([data_len >> 24, (data_len >> 16) & 0xFF, (data_len >> 8) & 0xFF, data_len & 0xFF], dtype=np.uint8)
    data = np.concatenate([len_info, data])

    # 计算最佳图像尺寸
    width = math.ceil(math.sqrt(len(data) / 3))
    height = math.ceil(len(data) / (3 * width))
    padded_length = width * height * 3

    # 数据填充
    padded_data = np.zeros(padded_length, dtype=np.uint8)
    padded_data[:len(data)] = data

    # 转换数据格式
    image_data = padded_data.reshape((height, width, 3))

    # 创建并保存图像
    image = Image.fromarray(image_data, 'RGB')
    image.save(image_path, 'PNG')

    return hash

def png_to_file(image_path, file_path):
    # 读取图像
    image = Image.open(image_path)
    data = np.array(image)

    # 提取像素数据并转换为一维数组
    binary_data = data.flatten()

    # 读取原始数据长度信息（前4个字节）
    data_len = (binary_data[0] << 24) + (binary_data[1] << 16) + (binary_data[2] << 8) + binary_data[3]

    # 提取实际数据
    actual_data = binary_data[4:4 + data_len]

    # 写入文件
    with open(file_path, "wb") as file:
        file.write(actual_data.tobytes())

    return hashlib.sha256(actual_data.tobytes())

# 使用示例
hash1 = file_to_png_with_numpy('data2video/1100085.jpg', 'output.png')
hash2 = png_to_file("output.png", "decode.jpg")

print(hash1.hexdigest())
print(hash2.hexdigest())

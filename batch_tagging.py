import os
import sys
from PIL import Image
import app_cpu

# 排除不需要的tag，从 exclude.txt 读取需要排除的tag
def excludeTags(str):
    try:
        f = open('exclude.txt', 'r', encoding='utf-8')
        for line in f.readlines():
            str = str.replace(line.strip(), '')
        f.close()
    except FileNotFoundError:
        pass  # 如果文件不存在，跳过排除步骤
    return str

def replaceTags(str):
    try:
        f = open('replace.txt', 'r', encoding='utf-8')
        for line in f.readlines():
            pair = line.split()
            if len(pair) >= 2:
                str = str.replace(pair[0], pair[1])
        f.close()
    except FileNotFoundError:
        pass  # 如果文件不存在，跳过替换步骤
    return str

def is_image_file(filename):
    """检查文件是否为支持的图片格式"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    return os.path.splitext(filename.lower())[1] in image_extensions

def process_directory(directory_path):
    """处理指定目录中的所有图片文件"""
    if not os.path.exists(directory_path):
        print(f"错误：目录 {directory_path} 不存在")
        return
    
    # 获取目录中的所有文件
    files = os.listdir(directory_path)
    image_files = [f for f in files if is_image_file(f)]
    
    if not image_files:
        print(f"在目录 {directory_path} 中没有找到图片文件")
        return
    
    print(f"找到 {len(image_files)} 个图片文件，开始处理...")
    
    for i, filename in enumerate(image_files, 1):
        file_path = os.path.join(directory_path, filename)
        print(f"处理 ({i}/{len(image_files)}): {filename}")
        
        try:
            # 打开图片
            image = Image.open(file_path)
            
            # 调用标签识别函数
            result = app_cpu.image_to_wd14_tags(image, 'wd-eva02-large-tagger-v3', 0.35, True, True, False, True)
            
            # 应用排除和替换规则
            result = excludeTags(result)
            result = replaceTags(result)
            
            # 生成txt文件名（与图片同名但扩展名为.txt）
            name_without_ext = os.path.splitext(filename)[0]
            txt_filename = name_without_ext + '.txt'
            txt_path = os.path.join(directory_path, txt_filename)
            
            # 保存结果到txt文件
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"  -> 已保存到: {txt_filename}")
            
        except Exception as e:
            print(f"  -> 错误：处理 {filename} 时出现问题: {str(e)}")
    
    print("批量处理完成！")

def main():
    if len(sys.argv) > 1:
        directory_path = sys.argv[1]
    else:
        directory_path = input("请输入要处理的目录路径: ").strip()
    
    # 处理相对路径和绝对路径
    if not os.path.isabs(directory_path):
        directory_path = os.path.abspath(directory_path)
    
    process_directory(directory_path)

if __name__ == "__main__":
    main() 
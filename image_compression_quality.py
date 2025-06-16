import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

def calculate_compression_quality(original_path, compressed_path):
    """
    计算压缩图片的质量损失
    
    Args:
        original_path: 原始图片路径
        compressed_path: 压缩后图片路径
        
    Returns:
        dict: 包含各种质量指标的字典
    """
    # 读取图片
    original = cv2.imread(original_path)
    compressed = cv2.imread(compressed_path)
    
    if original is None or compressed is None:
        raise ValueError("无法读取图片，请检查文件路径")
    
    # 确保两张图片尺寸相同
    if original.shape != compressed.shape:
        compressed = cv2.resize(compressed, (original.shape[1], original.shape[0]))
    
    # 计算MSE
    mse = np.mean((original - compressed) ** 2)
    
    # 计算PSNR
    psnr_value = psnr(original, compressed)
    
    # 计算SSIM，设置合适的窗口大小
    min_dim = min(original.shape[0], original.shape[1])
    win_size = min(7, min_dim)  # 确保窗口大小不超过图片尺寸
    if win_size % 2 == 0:  # 确保窗口大小为奇数
        win_size -= 1
    
    # 将BGR转换为RGB
    original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
    compressed_rgb = cv2.cvtColor(compressed, cv2.COLOR_BGR2RGB)
    
    # 计算SSIM
    ssim_value = ssim(original_rgb, compressed_rgb, 
                     win_size=win_size,
                     channel_axis=2,
                     data_range=255)
    
    return {
        "MSE": mse,
        "PSNR": psnr_value,
        "SSIM": ssim_value
    }

def print_quality_metrics(metrics):
    """
    打印质量指标
    
    Args:
        metrics: 质量指标字典
    """
    print("\n图片压缩质量评估结果：")
    print(f"MSE (均方误差): {metrics['MSE']:.2f}")
    print(f"PSNR (峰值信噪比): {metrics['PSNR']:.2f} dB")
    print(f"SSIM (结构相似性): {metrics['SSIM']:.4f}")
    
    # 提供简单的质量评估
    if metrics['SSIM'] > 0.95:
        print("\n质量评估：极好")
    elif metrics['SSIM'] > 0.9:
        print("\n质量评估：很好")
    elif metrics['SSIM'] > 0.8:
        print("\n质量评估：良好")
    elif metrics['SSIM'] > 0.7:
        print("\n质量评估：一般")
    else:
        print("\n质量评估：较差")

if __name__ == "__main__":
    # 示例用法
    original_image = "original.jpg"  # 替换为您的原始图片路径
    compressed_image = "compressed.jpg"  # 替换为您的压缩后图片路径
    
    try:
        metrics = calculate_compression_quality(original_image, compressed_image)
        print_quality_metrics(metrics)
    except Exception as e:
        print(f"发生错误: {str(e)}") 
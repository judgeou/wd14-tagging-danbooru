import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
import subprocess
import os
import tempfile

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
    
    # 计算SSIM
    ssim_value = ssim(original, compressed, multichannel=True, win_size=7, channel_axis=2)
    
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
    # if metrics['SSIM'] > 0.95:
    #     print("\n质量评估：极好")
    # elif metrics['SSIM'] > 0.9:
    #     print("\n质量评估：很好")
    # elif metrics['SSIM'] > 0.8:
    #     print("\n质量评估：良好")
    # elif metrics['SSIM'] > 0.7:
    #     print("\n质量评估：一般")
    # else:
    #     print("\n质量评估：较差")

def extract_frame_from_video(video_path, time_point, output_path):
    """
    使用ffmpeg从视频中提取指定时间点的帧
    
    Args:
        video_path: 视频文件路径
        time_point: 时间点（秒）
        output_path: 输出图片路径
    """
    command = [
        'ffmpeg',
        '-y',
        '-ss', str(time_point),
        '-i', video_path,
        '-frames:v', '1',
        '-vsync', '0',
        output_path
    ]
    
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"提取视频帧失败: {str(e)}")

def compare_video_frames(original_video, compressed_video, time_point):
    """
    比较两个视频在指定时间点的帧质量
    
    Args:
        original_video: 原始视频路径
        compressed_video: 压缩后视频路径
        time_point: 要比较的时间点（秒）
        
    Returns:
        dict: 包含各种质量指标的字典
    """
    # 创建临时文件来存储提取的帧
    original_frame_path = "1.png"
    compressed_frame_path = "2.png"
    
    
    # 提取帧
    extract_frame_from_video(original_video, time_point, original_frame_path)
    extract_frame_from_video(compressed_video, time_point, compressed_frame_path)
    
    # 比较帧质量
    metrics = calculate_compression_quality(original_frame_path, compressed_frame_path)
    
    return metrics


if __name__ == "__main__":
    # 示例用法
    original_video = r"g:\h\DeliriumBear\Marin+-+02+(Extra+13).mp4"  # 替换为您的原始视频路径
    compressed_video = r"f:\Download\Marin+-+02+(Extra+13)(1).mkv"  # 替换为您的压缩后视频路径
    time_point = '00:00:30'  # 要比较的时间点（秒）
    
    try:
        metrics = compare_video_frames(original_video, compressed_video, time_point)
        print(f"\n视频第 {time_point} 秒帧的质量评估结果：")
        print_quality_metrics(metrics)
    except Exception as e:
        print(f"发生错误: {str(e)}") 
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def put_chinese_text(img, text, position, font_size=30, color=(0, 0, 255)):
    """
    在图片上绘制中文文本
    
    参数:
        img: OpenCV格式的图像
        text: 要绘制的文本
        position: 文本位置，元组(x, y)
        font_size: 字体大小
        color: 文本颜色，BGR格式
        
    返回:
        添加文本后的图像
    """
    # 将OpenCV图像转换为PIL图像
    if len(img.shape) == 3:
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    else:
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_GRAY2RGB))
    
    # 创建绘图对象
    draw = ImageDraw.Draw(pil_img)
    
    # 尝试加载系统字体
    try:
        # 尝试加载微软雅黑字体
        font = ImageFont.truetype("msyh.ttc", font_size)
    except IOError:
        try:
            # 尝试加载宋体
            font = ImageFont.truetype("simsun.ttc", font_size)
        except IOError:
            try:
                # 尝试加载黑体
                font = ImageFont.truetype("simhei.ttf", font_size)
            except IOError:
                # 如果都失败，使用默认字体
                font = ImageFont.load_default()
    
    # 绘制文本，注意PIL使用RGB而OpenCV使用BGR
    draw.text(position, text, font=font, fill=(color[2], color[1], color[0]))
    
    # 将PIL图像转换回OpenCV格式
    result_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    return result_img
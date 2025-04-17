import cv2
import numpy as np
import matplotlib.pyplot as plt
from text_utils import put_chinese_text

# 圆形标定函数
def calibrate_circle(image, actual_radius):
    """
    对圆形进行标定
    
    参数:
        image: 输入图像
        actual_radius: 实际半径(mm)
        
    返回:
        success: 是否成功
        result_image: 标定结果图像
        pixels_per_mm: 像素/毫米比例
    """
    # 转换为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()
    
    # 高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)  # 增加高斯核大小
    
    # 尝试多种二值化方法
    # 自适应二值化
    thresh1 = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 2)  # 增加块大小
    
    # 形态学操作改善轮廓
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    thresh = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
    
    # 查找轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 根据矩形度筛选轮廓
    valid_contours = []
    min_area = 1000  # 增加最小面积阈值，避免小噪点
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        # 计算轮廓的周长
        perimeter = cv2.arcLength(cnt, True)
        # 对轮廓进行多边形近似
        epsilon = 0.04 * perimeter  # 增加近似精度参数，更宽松的多边形近似
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        # 判断是否为矩形（四边形）
        if len(approx) >= 4 and len(approx) <= 6:  # 允许4-6个顶点，更宽松的四边形判断
            # 计算最小外接矩形的面积
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box_area = cv2.contourArea(box)
            # 计算轮廓面积与其最小外接矩形面积的比值
            if box_area > 0:
                rect_ratio = area / box_area
                # 如果比值接近1，说明轮廓更接近矩形，降低阈值使检测更宽松
                if rect_ratio > 0.7:
                    valid_contours.append(cnt)
    
    if not valid_contours:
        return False, image, 0
    
    # 找到最合适的轮廓（假设是圆形）
    max_contour = max(valid_contours, key=cv2.contourArea)
    
    # 计算最小外接圆
    (x, y), radius = cv2.minEnclosingCircle(max_contour)
    center = (int(x), int(y))
    radius = int(radius)
    
    # 计算像素/毫米比例
    pixels_per_mm = radius / actual_radius
    
    # 创建结果图像
    result_image = image.copy() if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    cv2.circle(result_image, center, radius, (0, 255, 0), 2)
    
    # 使用支持中文的文本绘制函数
    result_image = put_chinese_text(result_image, f"半径: {radius} pixels = {actual_radius} mm", 
                (center[0] - 100, center[1] + radius + 30), 30, (0, 0, 255))
    result_image = put_chinese_text(result_image, f"比例: {pixels_per_mm:.4f} pixels/mm", 
                (center[0] - 100, center[1] + radius + 60), 30, (0, 0, 255))
    
    return True, result_image, pixels_per_mm

# 矩形标定函数
def calibrate_rectangle(image, actual_width, actual_height):
    """
    对矩形进行标定
    
    参数:
        image: 输入图像
        actual_width: 实际宽度(mm)
        actual_height: 实际高度(mm)
        
    返回:
        success: 是否成功
        result_image: 标定结果图像
        pixels_per_mm_width: 宽度方向像素/毫米比例
        pixels_per_mm_height: 高度方向像素/毫米比例
    """
    # 保存原始图像用于结果显示
    original_image = image.copy()
    
    # 转换为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()
    
    # 高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 尝试多种边缘检测和二值化方法
    methods = []
    
    # 方法1: 自适应二值化
    thresh1 = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh1 = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
    methods.append(thresh1)
    
    # 方法2: Otsu二值化
    _, thresh2 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thresh2 = cv2.morphologyEx(thresh2, cv2.MORPH_CLOSE, kernel)
    methods.append(thresh2)
    
    # 方法3: Canny边缘检测
    edges = cv2.Canny(blurred, 30, 150)
    dilated_edges = cv2.dilate(edges, kernel, iterations=1)
    methods.append(dilated_edges)
    
    # 方法4: 使用更大的结构元素进行形态学操作
    kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    thresh3 = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel_large)
    methods.append(thresh3)
    
    # 颜色过滤 - 如果是彩色图像，尝试过滤掉红色区域（如国徽）
    if len(image.shape) == 3:
        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # 定义红色范围
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        
        # 创建红色掩码
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # 反转掩码，保留非红色区域
        non_red_mask = cv2.bitwise_not(red_mask)
        
        # 应用掩码到灰度图
        filtered_gray = cv2.bitwise_and(gray, gray, mask=non_red_mask)
        
        # 对过滤后的图像进行二值化
        _, thresh_filtered = cv2.threshold(filtered_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        thresh_filtered = cv2.morphologyEx(thresh_filtered, cv2.MORPH_CLOSE, kernel)
        methods.append(thresh_filtered)
    
    # 尝试所有方法找到最佳轮廓
    best_contour = None
    max_area = 0
    min_area_threshold = 1000  # 最小面积阈值，避免小噪点
    
    for method_img in methods:
        # 查找轮廓
        contours, _ = cv2.findContours(method_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 根据矩形度筛选轮廓
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # 过滤掉太小的轮廓
            if area < min_area_threshold:
                continue
            
            # 计算轮廓的周长
            perimeter = cv2.arcLength(cnt, True)
            
            # 对轮廓进行多边形近似
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            # 判断是否为矩形（四边形）
            if len(approx) >= 4 and len(approx) <= 10:  # 放宽顶点数量限制
                # 计算最小外接矩形
                rect = cv2.minAreaRect(cnt)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                box_area = cv2.contourArea(box)
                
                # 计算轮廓面积与其最小外接矩形面积的比值
                if box_area > 0:
                    rect_ratio = area / box_area
                    
                    # 获取矩形的宽度和高度
                    width = max(rect[1][0], rect[1][1])
                    height = min(rect[1][0], rect[1][1])
                    
                    # 计算宽高比，身份证和信用卡的宽高比约为1.6
                    aspect_ratio = width / height if height > 0 else 0
                    
                    # 检查宽高比是否接近预期值（允许一定误差）
                    expected_ratio = actual_width / actual_height
                    ratio_diff = abs(aspect_ratio - expected_ratio) / expected_ratio
                    
                    # 综合考虑面积、矩形度和宽高比
                    if rect_ratio > 0.5 and ratio_diff < 0.3 and area > max_area:
                        max_area = area
                        best_contour = cnt
    
    if best_contour is None:
        return False, image, 0, 0
    
    # 计算最小外接矩形
    rect = cv2.minAreaRect(best_contour)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    
    # 获取矩形的宽度和高度（像素）
    width = rect[1][0]
    height = rect[1][1]
    
    # 确保宽度大于高度
    if width < height:
        width, height = height, width
    
    # 计算像素/毫米比例
    pixels_per_mm_width = width / actual_width
    pixels_per_mm_height = height / actual_height
    
    # 创建结果图像
    result_image = image.copy() if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(result_image, [box], 0, (0, 255, 0), 2)
    
    # 计算矩形中心点
    center_x = int(rect[0][0])
    center_y = int(rect[0][1])
    
    # 添加标注，使用支持中文的文本绘制函数
    result_image = put_chinese_text(result_image, f"长度: {width:.1f} pixels = {actual_width} mm", 
                (center_x - 100, center_y + int(height/2) + 30), 30, (0, 0, 255))
    result_image = put_chinese_text(result_image, f"宽度: {height:.1f} pixels = {actual_height} mm", 
                (center_x - 100, center_y + int(height/2) + 60), 30, (0, 0, 255))
    result_image = put_chinese_text(result_image, f"比例 宽: {pixels_per_mm_width:.4f} px/mm, 高: {pixels_per_mm_height:.4f} px/mm", 
                (center_x - 100, center_y + int(height/2) + 90), 30, (0, 0, 255))
    
    return True, result_image, pixels_per_mm_width, pixels_per_mm_height

# 圆形测量函数
def measure_circle(image, pixels_per_mm):
    """
    测量圆形
    
    参数:
        image: 输入图像
        pixels_per_mm: 像素/毫米比例
        
    返回:
        success: 是否成功
        result_image: 测量结果图像
        measured_radius: 测量半径(mm)
    """
    # 转换为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()
    
    # 高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)  # 增加高斯核大小
    
    # 尝试多种二值化方法
    # 自适应二值化
    thresh1 = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 2)  # 增加块大小
    
    # 形态学操作改善轮廓
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    thresh = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
    
    # 查找轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 根据矩形度筛选轮廓
    valid_contours = []
    min_area = 1000  # 增加最小面积阈值，避免小噪点
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        # 计算轮廓的周长
        perimeter = cv2.arcLength(cnt, True)
        # 对轮廓进行多边形近似
        epsilon = 0.04 * perimeter  # 增加近似精度参数，更宽松的多边形近似
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        # 判断是否为矩形（四边形）
        if len(approx) >= 4 and len(approx) <= 6:  # 允许4-6个顶点，更宽松的四边形判断
            # 计算最小外接矩形的面积
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box_area = cv2.contourArea(box)
            # 计算轮廓面积与其最小外接矩形面积的比值
            if box_area > 0:
                rect_ratio = area / box_area
                # 如果比值接近1，说明轮廓更接近矩形，降低阈值使检测更宽松
                if rect_ratio > 0.7:
                    valid_contours.append(cnt)
    
    if not valid_contours:
        return False, image, 0
    
    # 找到最合适的轮廓（假设是圆形）
    max_contour = max(valid_contours, key=cv2.contourArea)
    
    # 计算最小外接圆
    (x, y), radius = cv2.minEnclosingCircle(max_contour)
    center = (int(x), int(y))
    radius = int(radius)
    
    # 计算实际半径(mm)
    measured_radius = radius / pixels_per_mm
    
    # 创建结果图像
    result_image = image.copy() if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    cv2.circle(result_image, center, radius, (0, 255, 0), 2)
    # 使用支持中文的文本绘制函数
    result_image = put_chinese_text(result_image, f"半径: {radius} pixels = {measured_radius:.2f} mm", 
                (center[0] - 100, center[1] + radius + 30), 30, (0, 0, 255))
    
    return True, result_image, measured_radius

# 矩形测量函数
def measure_rectangle(image, pixels_per_mm_width, pixels_per_mm_height):
    """
    测量矩形
    
    参数:
        image: 输入图像
        pixels_per_mm_width: 宽度方向像素/毫米比例
        pixels_per_mm_height: 高度方向像素/毫米比例
        
    返回:
        success: 是否成功
        result_image: 测量结果图像
        measured_width: 测量宽度(mm)
        measured_height: 测量高度(mm)
    """
    # 保存原始图像用于结果显示
    original_image = image.copy()
    
    # 转换为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()
    
    # 高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 尝试多种边缘检测和二值化方法
    methods = []
    
    # 方法1: 自适应二值化
    thresh1 = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh1 = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
    methods.append(thresh1)
    
    # 方法2: Otsu二值化
    _, thresh2 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thresh2 = cv2.morphologyEx(thresh2, cv2.MORPH_CLOSE, kernel)
    methods.append(thresh2)
    
    # 方法3: Canny边缘检测
    edges = cv2.Canny(blurred, 30, 150)
    dilated_edges = cv2.dilate(edges, kernel, iterations=1)
    methods.append(dilated_edges)
    
    # 方法4: 使用更大的结构元素进行形态学操作
    kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    thresh3 = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel_large)
    methods.append(thresh3)
    
    # 颜色过滤 - 如果是彩色图像，尝试过滤掉红色区域（如国徽）
    if len(image.shape) == 3:
        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # 定义红色范围
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        
        # 创建红色掩码
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # 反转掩码，保留非红色区域
        non_red_mask = cv2.bitwise_not(red_mask)
        
        # 应用掩码到灰度图
        filtered_gray = cv2.bitwise_and(gray, gray, mask=non_red_mask)
        
        # 对过滤后的图像进行二值化
        _, thresh_filtered = cv2.threshold(filtered_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        thresh_filtered = cv2.morphologyEx(thresh_filtered, cv2.MORPH_CLOSE, kernel)
        methods.append(thresh_filtered)
    
    # 尝试所有方法找到最佳轮廓
    best_contour = None
    max_area = 0
    min_area_threshold = 1000  # 最小面积阈值，避免小噪点
    
    for method_img in methods:
        # 查找轮廓
        contours, _ = cv2.findContours(method_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 根据矩形度筛选轮廓
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # 过滤掉太小的轮廓
            if area < min_area_threshold:
                continue
            
            # 计算轮廓的周长
            perimeter = cv2.arcLength(cnt, True)
            
            # 对轮廓进行多边形近似
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            # 判断是否为矩形（四边形）
            if len(approx) >= 4 and len(approx) <= 10:  # 放宽顶点数量限制
                # 计算最小外接矩形
                rect = cv2.minAreaRect(cnt)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                box_area = cv2.contourArea(box)
                
                # 计算轮廓面积与其最小外接矩形面积的比值
                if box_area > 0:
                    rect_ratio = area / box_area
                    
                    # 获取矩形的宽度和高度
                    width = max(rect[1][0], rect[1][1])
                    height = min(rect[1][0], rect[1][1])
                    
                    # 如果面积更大且矩形度合理，则更新最佳轮廓
                    if rect_ratio > 0.5 and area > max_area:
                        max_area = area
                        best_contour = cnt
    
    if best_contour is None:
        return False, image, 0, 0
    
    # 计算最小外接矩形
    rect = cv2.minAreaRect(best_contour)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    
    # 获取矩形的宽度和高度（像素）
    width = rect[1][0]
    height = rect[1][1]
    
    # 确保宽度大于高度
    if width < height:
        width, height = height, width
    
    # 计算实际尺寸(mm)
    measured_width = width / pixels_per_mm_width
    measured_height = height / pixels_per_mm_height
    
    # 创建结果图像
    result_image = image.copy() if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(result_image, [box], 0, (0, 255, 0), 2)
    
    # 计算矩形中心点
    center_x = int(rect[0][0])
    center_y = int(rect[0][1])
    
    # 添加标注，使用支持中文的文本绘制函数
    result_image = put_chinese_text(result_image, f"长度: {width:.1f} pixels = {measured_width:.2f} mm", 
                (center_x - 100, center_y + int(height/2) + 30), 30, (0, 0, 255))
    result_image = put_chinese_text(result_image, f"宽度: {height:.1f} pixels = {measured_height:.2f} mm", 
                (center_x - 100, center_y + int(height/2) + 60), 30, (0, 0, 255))
    
    return True, result_image, measured_width, measured_height
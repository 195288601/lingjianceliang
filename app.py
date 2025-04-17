import streamlit as st
import cv2
import numpy as np
import os
import json
from datetime import datetime
from PIL import Image
# 导入图像处理模块
from image_processing import calibrate_circle, calibrate_rectangle, measure_circle, measure_rectangle
# 导入首页模块
from home_page import home_page
# 导入认证模块
from auth import is_authenticated, require_login
# 导入摄像头工具模块
from camera_utils import init_camera, stop_camera, camera_stream_placeholder, display_camera_stream, capture_frame

# 设置页面配置
st.set_page_config(page_title="机器视觉零件测量系统", layout="wide")

# 获取当前脚本的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 创建保存结果的目录（使用绝对路径）
results_dir = os.path.join(current_dir, 'results')
if not os.path.exists(results_dir):
    os.makedirs(results_dir)

# 创建标定数据的目录（使用绝对路径）
calibration_dir = os.path.join(current_dir, 'calibration')
if not os.path.exists(calibration_dir):
    os.makedirs(calibration_dir)

# 初始化标定数据文件（使用绝对路径）
CALIBRATION_FILE = os.path.join(calibration_dir, 'calibration_data.json')
if not os.path.exists(CALIBRATION_FILE):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump({
            'circle': {'radius': 0, 'pixels_per_mm': 0},
            'rectangle': {'width': 0, 'height': 0, 'pixels_per_mm_width': 0, 'pixels_per_mm_height': 0},
            'custom': []
        }, f)

# 加载标定数据
def load_calibration_data():
    try:
        with open(CALIBRATION_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            'circle': {'radius': 0, 'pixels_per_mm': 0},
            'rectangle': {'width': 0, 'height': 0, 'pixels_per_mm_width': 0, 'pixels_per_mm_height': 0},
            'custom': []
        }

# 保存标定数据
def save_calibration_data(data):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f)

# 主应用
def main():
    st.title("机器视觉零件测量系统")
    
    # 初始化session_state
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = "首页"
    if 'login_status' not in st.session_state:
        st.session_state.login_status = False
    
    # 侧边栏选择功能
    st.sidebar.title("功能选择")
    
    # 显示登录状态
    if is_authenticated():
        st.sidebar.success(f"已登录为: {st.session_state.username}")
        if st.sidebar.button("退出登录", key="logout_button_sidebar"):
            st.session_state.login_status = False
            if 'username' in st.session_state:
                del st.session_state.username
            st.session_state.app_mode = "首页"
            st.experimental_rerun()
    
    # 根据登录状态决定可选模式
    if is_authenticated():
        app_mode = st.sidebar.selectbox("选择模式", ["首页", "标定", "测量"], index=["首页", "标定", "测量"].index(st.session_state.app_mode))
    else:
        app_mode = "首页"
        st.sidebar.info("请先登录系统才能使用标定和测量功能")
    
    # 更新session_state
    st.session_state.app_mode = app_mode
    
    if app_mode == "首页":
        home_page()
    elif app_mode == "标定":
        calibration_page()
    else:
        measurement_page()

# 标定页面
def calibration_page():
    # 检查用户是否已登录
    if not is_authenticated():
        st.warning("请先登录系统！")
        st.session_state.app_mode = "首页"
        st.experimental_rerun()
        return
        
    st.header("标定模式")
    
    # 选择标定类型
    calibration_type = st.radio("选择标定类型", ["圆形标定", "矩形标定", "自定义标定"])
    
    # 常用标定物体预设
    if calibration_type == "圆形标定":
        preset_object = st.selectbox("选择常用标定物体", [
            "自定义尺寸",
            "1元硬币 (直径25.0mm)",
            "5角硬币 (直径20.5mm)",
            "1角硬币 (直径19.0mm)"
        ])
    elif calibration_type == "矩形标定":
        # 选择常用标定物体预设
        preset_object = st.selectbox("选择常用标定物体", [
            "自定义尺寸",
            "标准信用卡 (85.6mm × 54.0mm)",
            "A4纸 (297mm × 210mm)",
            "身份证 (85.6mm × 54.0mm)"
        ])
        
        if preset_object == "标准信用卡 (85.6mm × 54.0mm)" or preset_object == "身份证 (85.6mm × 54.0mm)":
            actual_width = 85.6
            actual_height = 54.0
        elif preset_object == "A4纸 (297mm × 210mm)":
            actual_width = 297.0
            actual_height = 210.0
        else:  # 自定义尺寸
            actual_width = st.number_input("输入标定矩形的实际宽度 (mm)", min_value=0.1, value=50.0, step=0.1)
            actual_height = st.number_input("输入标定矩形的实际高度 (mm)", min_value=0.1, value=30.0, step=0.1)
    
    # 选择输入源
    source_type = st.radio("选择输入源", ["上传图片", "使用摄像头"])
    
    if source_type == "上传图片":
        uploaded_file = st.file_uploader("上传白色背景的标定图片", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            img_array = np.array(image)
            process_calibration(img_array, calibration_type)
    else:
        # 初始化摄像头
        if init_camera():
            # 创建摄像头流占位符
            camera_placeholder = camera_stream_placeholder()
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 显示摄像头流
                current_frame = display_camera_stream(camera_placeholder)
            
            with col2:
                st.markdown("### 摄像头控制")
                st.markdown("将标定物体放在白色背景上，确保光线充足")
                
                # 捕获按钮
                if st.button("捕获图像", key="capture_calibration"):
                    captured_frame = capture_frame()
                    if captured_frame is not None:
                        st.session_state.captured_frame = captured_frame
                        st.success("图像已捕获!")
                        # 处理捕获的图像
                        process_calibration(captured_frame, calibration_type)
                    else:
                        st.error("捕获图像失败，请检查摄像头连接")
                
                # 停止摄像头按钮
                if st.button("停止摄像头", key="stop_camera_calibration"):
                    stop_camera()
                    st.experimental_rerun()

# 测量页面
def measurement_page():
    # 检查用户是否已登录
    if not is_authenticated():
        st.warning("请先登录系统！")
        st.session_state.app_mode = "首页"
        st.experimental_rerun()
        return
        
    st.header("测量模式")
    
    # 选择测量类型
    measurement_type = st.radio("选择测量类型", ["圆形测量", "矩形测量"])
    
    # 选择输入源
    source_type = st.radio("选择输入源", ["上传图片", "使用摄像头"])
    
    # 加载标定数据
    calibration_data = load_calibration_data()
    
    # 检查是否已标定
    if measurement_type == "圆形测量" and calibration_data['circle']['pixels_per_mm'] == 0:
        st.error("请先进行圆形标定！")
        return
    elif measurement_type == "矩形测量" and calibration_data['rectangle']['pixels_per_mm_width'] == 0:
        st.error("请先进行矩形标定！")
        return
    
    # 输入期望尺寸
    if measurement_type == "圆形测量":
        expected_radius = st.number_input("输入期望半径 (mm)", min_value=0.1, value=10.0, step=0.1)
    else:  # 矩形测量
        expected_width = st.number_input("输入期望长度 (mm)", min_value=0.1, value=50.0, step=0.1)
        expected_height = st.number_input("输入期望宽度 (mm)", min_value=0.1, value=30.0, step=0.1)
    
    if source_type == "上传图片":
        uploaded_file = st.file_uploader("上传白色背景的测量图片", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            img_array = np.array(image)
            
            if measurement_type == "圆形测量":
                process_circle_measurement(img_array, expected_radius, calibration_data)
            else:  # 矩形测量
                process_rectangle_measurement(img_array, expected_width, expected_height, calibration_data)
    else:
        # 初始化摄像头
        if init_camera():
            # 创建摄像头流占位符
            camera_placeholder = camera_stream_placeholder()
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 显示摄像头流
                current_frame = display_camera_stream(camera_placeholder)
            
            with col2:
                st.markdown("### 摄像头控制")
                st.markdown("将测量物体放在白色背景上，确保光线充足")
                
                # 捕获按钮
                if st.button("捕获图像", key="capture_measurement"):
                    captured_frame = capture_frame()
                    if captured_frame is not None:
                        st.session_state.captured_frame = captured_frame
                        st.success("图像已捕获!")
                        # 处理捕获的图像
                        if measurement_type == "圆形测量":
                            process_circle_measurement(captured_frame, expected_radius, calibration_data)
                        else:  # 矩形测量
                            process_rectangle_measurement(captured_frame, expected_width, expected_height, calibration_data)
                    else:
                        st.error("捕获图像失败，请检查摄像头连接")
                
                # 停止摄像头按钮
                if st.button("停止摄像头", key="stop_camera_measurement"):
                    stop_camera()
                    st.experimental_rerun()

# 处理标定
def process_calibration(image, calibration_type):
    st.image(image, caption="上传的标定图片", use_column_width=True)
    
    # 显示标定参数输入
    if calibration_type == "圆形标定":
        # 选择常用标定物体预设
        preset_object = st.selectbox("选择常用标定物体", [
            "自定义尺寸",
            "1元硬币 (直径25.0mm)",
            "5角硬币 (直径20.5mm)",
            "1角硬币 (直径19.0mm)"
        ])
        
        if preset_object == "1元硬币 (直径25.0mm)":
            actual_radius = 12.5  # 直径的一半
        elif preset_object == "5角硬币 (直径20.5mm)":
            actual_radius = 10.25
        elif preset_object == "1角硬币 (直径19.0mm)":
            actual_radius = 9.5
        else:  # 自定义尺寸
            actual_radius = st.number_input("输入标定圆的实际半径 (mm)", min_value=0.1, value=10.0, step=0.1)
        if st.button("开始圆形标定"):
            # 这里将调用圆形标定函数
            st.info("正在进行圆形标定...")
            # 调用圆形标定函数
            success, result_image, pixels_per_mm = calibrate_circle(image, actual_radius)
            if success:
                st.success(f"圆形标定成功! 像素/毫米比例: {pixels_per_mm:.4f}")
                st.image(result_image, caption="标定结果", use_column_width=True)
                
                # 保存标定数据
                calibration_data = load_calibration_data()
                calibration_data['circle']['radius'] = actual_radius
                calibration_data['circle']['pixels_per_mm'] = pixels_per_mm
                save_calibration_data(calibration_data)
            else:
                st.error("标定失败，未能检测到圆形")
    
    elif calibration_type == "矩形标定":
        # 选择常用标定物体预设
        preset_object = st.selectbox("选择常用标定物体", [
            "自定义尺寸",
            "标准信用卡 (85.6mm × 54.0mm)",
            "身份证 (85.6mm × 54.0mm)",
            "A4纸 (297mm × 210mm)"
        ])
        
        if preset_object == "标准信用卡 (85.6mm × 54.0mm)" or preset_object == "身份证 (85.6mm × 54.0mm)":
            actual_width = 85.6
            actual_height = 54.0
        elif preset_object == "A4纸 (297mm × 210mm)":
            actual_width = 297.0
            actual_height = 210.0
        else:  # 自定义尺寸
            actual_width = st.number_input("输入标定矩形的实际宽度 (mm)", min_value=0.1, value=50.0, step=0.1)
            actual_height = st.number_input("输入标定矩形的实际高度 (mm)", min_value=0.1, value=30.0, step=0.1)
        if st.button("开始矩形标定"):
            # 这里将调用矩形标定函数
            st.info("正在进行矩形标定...")
            # 调用矩形标定函数
            success, result_image, pixels_per_mm_width, pixels_per_mm_height = calibrate_rectangle(image, actual_width, actual_height)
            if success:
                st.success(f"矩形标定成功! 宽度像素/毫米: {pixels_per_mm_width:.4f}, 高度像素/毫米: {pixels_per_mm_height:.4f}")
                st.image(result_image, caption="标定结果", use_column_width=True)
                
                # 保存标定数据
                calibration_data = load_calibration_data()
                calibration_data['rectangle']['width'] = actual_width
                calibration_data['rectangle']['height'] = actual_height
                calibration_data['rectangle']['pixels_per_mm_width'] = pixels_per_mm_width
                calibration_data['rectangle']['pixels_per_mm_height'] = pixels_per_mm_height
                save_calibration_data(calibration_data)
            else:
                st.error("标定失败，未能检测到矩形")
    
    else:  # 自定义标定
        st.subheader("自定义标定")
        custom_name = st.text_input("输入自定义标定对象名称")
        custom_dimension = st.number_input("输入标定对象的特征尺寸 (mm)", min_value=0.1, value=10.0, step=0.1)
        if st.button("开始自定义标定"):
            st.info("正在进行自定义标定...")
            # 这里将来添加自定义标定代码
            st.warning("自定义标定功能正在开发中...")

# 圆形测量处理
def process_circle_measurement(image, expected_radius, calibration_data):
    st.image(image, caption="上传的测量图片", use_column_width=True)
    
    if st.button("开始圆形测量"):
        st.info("正在进行圆形测量...")
        # 调用圆形测量函数
        success, result_image, measured_radius = measure_circle(image, calibration_data['circle']['pixels_per_mm'])
        
        if success:
            st.success(f"测量成功!")
            st.image(result_image, caption="测量结果", use_column_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("期望半径 (mm)", f"{expected_radius:.2f}")
            with col2:
                st.metric("实际半径 (mm)", f"{measured_radius:.2f}")
            with col3:
                error = ((measured_radius - expected_radius) / expected_radius) * 100
                st.metric("误差 (%)", f"{error:.2f}")
            
            # 保存结果选项
            if st.button("保存测量结果", key="save_circle_result"):
                save_success = save_measurement_result("circle", {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "expected_radius": expected_radius,
                    "measured_radius": measured_radius,
                    "error_percentage": error
                }, result_image)
                if save_success:
                    st.success("测量结果已保存!")
                else:
                    st.error("保存测量结果失败，请检查文件权限或磁盘空间。")
        else:
            st.error("测量失败，未能检测到圆形")

# 矩形测量处理
def process_rectangle_measurement(image, expected_width, expected_height, calibration_data):
    st.image(image, caption="上传的测量图片", use_column_width=True)
    
    if st.button("开始矩形测量"):
        st.info("正在进行矩形测量...")
        # 调用矩形测量函数
        success, result_image, measured_width, measured_height = measure_rectangle(
            image, 
            calibration_data['rectangle']['pixels_per_mm_width'],
            calibration_data['rectangle']['pixels_per_mm_height']
        )
        
        if success:
            st.success(f"测量成功!")
            st.image(result_image, caption="测量结果", use_column_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("长度 x 宽度 (mm)", f"{expected_width:.2f} x {expected_height:.2f}")
            with col2:
                st.metric("实际长度 x 宽度 (mm)", f"{measured_width:.2f} x {measured_height:.2f}")
            with col3:
                width_error = ((measured_width - expected_width) / expected_width) * 100
                height_error = ((measured_height - expected_height) / expected_height) * 100
                st.metric("误差 (%)", f"长: {width_error:.2f}, 宽: {height_error:.2f}")
            
            # 保存结果选项
            if st.button("保存测量结果", key="save_rectangle_result"):
                save_success = save_measurement_result("rectangle", {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "expected_width": expected_width,
                    "expected_height": expected_height,
                    "measured_width": measured_width,
                    "measured_height": measured_height,
                    "width_error_percentage": width_error,
                    "height_error_percentage": height_error
                }, result_image)
                if save_success:
                    st.success("测量结果已保存!")
                else:
                    st.error("保存测量结果失败，请检查文件权限或磁盘空间。")
        else:
            st.error("测量失败，未能检测到矩形")

# 保存测量结果
def save_measurement_result(measurement_type, data, image):
    try:
        # 导入csv模块
        import csv
        
        # 获取当前脚本的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 确保结果目录存在（使用绝对路径）
        results_dir = os.path.join(current_dir, 'results')
        
        # 检查目录是否存在，如果不存在则创建
        if not os.path.exists(results_dir):
            try:
                os.makedirs(results_dir, exist_ok=True)
            except Exception as e:
                st.error(f"创建结果目录失败: {str(e)}")
                return False
        
        # 创建唯一的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir_name = f"{measurement_type}_{timestamp}"
        result_dir = os.path.join(results_dir, result_dir_name)
        
        # 创建结果子目录
        try:
            os.makedirs(result_dir, exist_ok=True)
        except Exception as e:
            st.error(f"创建测量结果目录失败: {str(e)}")
            return False
        
        # 保存数据为JSON
        data_file = os.path.join(result_dir, 'data.json')
        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            st.error(f"保存JSON数据文件失败: {str(e)}")
            return False
        
        # 保存数据为CSV
        csv_file = os.path.join(result_dir, 'data.csv')
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                csv_writer = csv.writer(f)
                # 写入表头和数据
                if measurement_type == 'circle':
                    csv_writer.writerow(['时间戳', '期望半径(mm)', '实际半径(mm)', '误差(%)'])
                    csv_writer.writerow([
                        data['timestamp'],
                        data['expected_radius'],
                        data['measured_radius'],
                        data['error_percentage']
                    ])
                elif measurement_type == 'rectangle':
                    csv_writer.writerow(['时间戳', '期望长度(mm)', '期望宽度(mm)', '实际长度(mm)', '实际宽度(mm)', '长度误差(%)', '宽度误差(%)'])
                    csv_writer.writerow([
                        data['timestamp'],
                        data['expected_width'],
                        data['expected_height'],
                        data['measured_width'],
                        data['measured_height'],
                        data['width_error_percentage'],
                        data['height_error_percentage']
                    ])
        except Exception as e:
            st.error(f"保存CSV数据文件失败: {str(e)}")
            # CSV保存失败不影响整体结果，继续执行
        
        # 保存图像
        image_file = os.path.join(result_dir, 'result_image.jpg')
        
        # 检查图像通道，确保正确转换
        if isinstance(image, np.ndarray):
            try:
                # 确保图像数据类型正确
                if image.dtype != np.uint8:
                    image = image.astype(np.uint8)
                
                # 使用PIL保存图像
                if len(image.shape) == 3 and image.shape[2] == 3:
                    # 对于彩色图像
                    pil_image = Image.fromarray(image)
                    pil_image.save(image_file, format='JPEG')
                    st.info(f"保存彩色图像到: {image_file}")
                elif len(image.shape) == 2 or (len(image.shape) == 3 and image.shape[2] == 1):
                    # 对于灰度图
                    if len(image.shape) == 3:
                        image = image[:,:,0]  # 取第一个通道
                    pil_image = Image.fromarray(image, mode='L')
                    pil_image.save(image_file, format='JPEG')
                    st.info(f"保存灰度图像到: {image_file}")
                else:
                    # 处理其他情况
                    st.warning(f"未知图像格式: shape={image.shape}, 尝试转换为RGB")
                    # 尝试转换为RGB
                    try:
                        if len(image.shape) == 3 and image.shape[2] == 4:  # RGBA图像
                            rgb_image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
                            pil_image = Image.fromarray(rgb_image)
                        else:
                            # 其他格式尝试直接转换
                            pil_image = Image.fromarray(image)
                        pil_image.save(image_file, format='JPEG')
                        st.info(f"成功转换并保存图像到: {image_file}")
                    except Exception as e:
                        st.error(f"图像格式转换失败: {str(e)}")
                        return False
            except Exception as e:
                st.error(f"保存图像失败: {str(e)}")
                # 尝试使用OpenCV保存
                try:
                    st.warning("尝试使用OpenCV保存图像...")
                    if len(image.shape) == 3 and image.shape[2] == 3:
                        # BGR转RGB (OpenCV使用BGR格式)
                        cv_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    else:
                        cv_image = image
                    cv2.imwrite(image_file, cv_image)
                    st.info(f"使用OpenCV成功保存图像到: {image_file}")
                except Exception as cv_error:
                    st.error(f"OpenCV保存图像也失败: {str(cv_error)}")
                    return False
        else:
            st.error(f"无效的图像数据类型: {type(image)}")
            # 尝试直接保存PIL图像
            try:
                if isinstance(image, Image.Image):
                    st.warning("检测到PIL图像对象，直接保存...")
                    image.save(image_file, format='JPEG')
                    st.info(f"成功保存PIL图像到: {image_file}")
                else:
                    return False
            except Exception as e:
                st.error(f"保存PIL图像失败: {str(e)}")
                return False
        
        # 验证文件是否成功创建
        if os.path.exists(data_file) and os.path.exists(image_file):
            st.success(f"测量结果已成功保存到: {result_dir}")
            return True
        else:
            st.error("文件保存验证失败")
            return False
    except Exception as e:
        st.error(f"保存测量结果时发生错误: {str(e)}")
        return False

# 运行应用
if __name__ == "__main__":
    main()
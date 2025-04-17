import cv2
import numpy as np
import streamlit as st
import time
from threading import Thread
from PIL import Image

class CameraCapture:
    """摄像头捕获类，用于管理摄像头视频流"""
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.is_running = False
        self.cap = None
        self.frame = None
        self.last_frame_time = 0
        self.fps = 0
    
    def start(self):
        """启动摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                st.error(f"无法打开摄像头 ID: {self.camera_id}")
                return False
            
            # 设置分辨率
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.is_running = True
            # 启动捕获线程
            self.thread = Thread(target=self._capture_loop)
            self.thread.daemon = True
            self.thread.start()
            return True
        except Exception as e:
            st.error(f"启动摄像头时出错: {str(e)}")
            return False
    
    def _capture_loop(self):
        """捕获循环，在单独的线程中运行"""
        prev_time = time.time()
        frame_count = 0
        
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                # 转换BGR到RGB
                self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 计算FPS
                frame_count += 1
                curr_time = time.time()
                if curr_time - prev_time >= 1.0:
                    self.fps = frame_count
                    frame_count = 0
                    prev_time = curr_time
                
                self.last_frame_time = time.time()
            time.sleep(0.01)  # 减少CPU使用率
    
    def get_frame(self):
        """获取当前帧"""
        if self.frame is not None:
            return self.frame.copy(), self.fps
        return None, 0
    
    def stop(self):
        """停止摄像头"""
        self.is_running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()

def camera_stream_placeholder():
    """创建摄像头流占位符"""
    return st.empty()

def init_camera(camera_id=0):
    """初始化摄像头"""
    if 'camera' not in st.session_state:
        st.session_state.camera = CameraCapture(camera_id)
    
    if not st.session_state.camera.is_running:
        if st.session_state.camera.start():
            st.success("摄像头已成功启动")
            return True
        else:
            st.error("摄像头启动失败")
            return False
    return True

def stop_camera():
    """停止摄像头"""
    if 'camera' in st.session_state and st.session_state.camera.is_running:
        st.session_state.camera.stop()
        st.info("摄像头已停止")

def get_camera_frame():
    """获取摄像头当前帧"""
    if 'camera' in st.session_state and st.session_state.camera.is_running:
        return st.session_state.camera.get_frame()
    return None, 0

def display_camera_stream(placeholder, processing_func=None, params=None):
    """显示摄像头流
    
    参数:
        placeholder: streamlit占位符
        processing_func: 图像处理函数 (可选)
        params: 传递给处理函数的参数 (可选)
    """
    frame, fps = get_camera_frame()
    if frame is not None:
        # 应用图像处理函数
        if processing_func is not None:
            if params is not None:
                processed_frame = processing_func(frame, **params)
            else:
                processed_frame = processing_func(frame)
            display_frame = processed_frame
        else:
            display_frame = frame
        
        # 显示FPS
        cv2.putText(display_frame, f"FPS: {fps}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 显示图像
        placeholder.image(display_frame, channels="RGB", use_column_width=True)
        return display_frame
    return None

def capture_frame():
    """捕获当前帧"""
    frame, _ = get_camera_frame()
    return frame
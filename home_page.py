import streamlit as st
import os
from PIL import Image
from auth import login_page, is_authenticated, require_login

def home_page():
    st.header("欢迎使用机器视觉零件测量系统")
    
    # 系统概述
    st.subheader("系统概述")
    st.write("""
    这是一个基于机器视觉的零件测量系统，可以对圆形和矩形零件进行标定和测量。
    系统使用白色A4纸作为背景，支持图片和摄像头两种输入方式。
    通过简单的操作，您可以快速完成零件的尺寸测量工作。
    """)
    
    # 主要功能介绍
    st.subheader("主要功能")
    
    # 标定功能
    with st.expander("标定功能", expanded=True):
        st.markdown("""
        - **圆形标定**：使用已知半径的圆形物体进行标定
            - 支持1元硬币、5角硬币、1角硬币等常用标定物
            - 支持自定义尺寸的圆形物体
        - **矩形标定**：使用已知尺寸的矩形物体进行标定
            - 支持标准信用卡、身份证、A4纸等常用标定物
            - 支持自定义尺寸的矩形物体
        - **自定义标定**：支持自定义物体标定（开发中）
        """)
    
    # 测量功能
    with st.expander("测量功能", expanded=True):
        st.markdown("""
        - **圆形测量**：测量圆形零件的半径
        - **矩形测量**：测量矩形零件的长度和宽度
        - **支持与期望尺寸比较**：计算测量值与期望值的误差
        - **支持保存测量结果**：将测量结果保存为文件
        """)
    
    # 输入方式
    with st.expander("输入方式", expanded=True):
        st.markdown("""
        - **图片输入**：上传图片进行标定或测量
        - **摄像头输入**：使用摄像头实时捕获图像并进行处理
        """)
    
    # 使用流程指南
    st.subheader("使用流程指南")
    
    # 创建三列布局
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 第一步：标定")
        st.markdown("""
        1. 在侧边栏选择"标定"模式
        2. 选择标定类型（圆形/矩形）
        3. 选择标定物体或输入自定义尺寸
        4. 上传标定图片
        5. 点击"开始标定"按钮
        6. 查看标定结果
        """)
    
    with col2:
        st.markdown("### 第二步：测量")
        st.markdown("""
        1. 在侧边栏选择"测量"模式
        2. 选择测量类型（圆形/矩形）
        3. 输入期望尺寸（可选）
        4. 上传测量图片
        5. 查看测量结果
        """)
    
    with col3:
        st.markdown("### 第三步：保存结果")
        st.markdown("""
        1. 查看测量结果和误差
        2. 点击"保存结果"按钮
        3. 结果将保存在results目录中
        """)
    
    # 注意事项
    st.subheader("注意事项")
    st.warning("""
    - 拍摄图片时，请确保使用白色A4纸作为背景
    - 物体应与背景有明显的对比度
    - 拍摄时避免阴影和反光
    - 标定和测量使用的相机应保持一致，以确保准确性
    - 首次使用系统时，必须先进行标定，然后才能进行测量
    """)
    
    # 开始使用按钮
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("开始使用系统", use_container_width=True):
            # 显示登录界面
            if 'show_login' not in st.session_state:
                st.session_state.show_login = True
                st.experimental_rerun()
    
    # 显示登录界面
    if st.session_state.get('show_login', False):
        with st.container():
            st.markdown("""<style>
                .login-container {
                    background-color: #f0f2f6;
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    margin: 20px 0;
                }
            </style>""", unsafe_allow_html=True)
            
            with st.container():
                st.markdown('<div class="login-container">', unsafe_allow_html=True)
                login_result = login_page()
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 如果登录成功，跳转到标定页面
                if is_authenticated():
                    st.session_state.app_mode = "标定"
                    st.session_state.show_login = False
                    st.experimental_rerun()
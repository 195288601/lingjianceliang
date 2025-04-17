import streamlit as st
import json
import os
import hashlib

# 获取当前脚本的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 创建用户数据目录
users_dir = os.path.join(current_dir, 'users')
if not os.path.exists(users_dir):
    os.makedirs(users_dir)

# 用户数据文件路径
USERS_FILE = os.path.join(users_dir, 'users.json')

# 初始化用户数据文件
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        # 创建默认管理员账户 (用户名: admin, 密码: admin123)
        default_password = hashlib.sha256('admin123'.encode()).hexdigest()
        json.dump({
            'admin': {
                'password': default_password,
                'role': 'admin'
            }
        }, f, ensure_ascii=False)

# 加载用户数据
def load_users():
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # 如果文件不存在或损坏，创建新的用户数据
        default_password = hashlib.sha256('admin123'.encode()).hexdigest()
        return {
            'admin': {
                'password': default_password,
                'role': 'admin'
            }
        }

# 保存用户数据
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False)

# 验证用户
def verify_user(username, password):
    users = load_users()
    if username in users:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if users[username]['password'] == hashed_password:
            return True
    return False

# 添加用户
def add_user(username, password, role='user'):
    users = load_users()
    if username not in users:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        users[username] = {
            'password': hashed_password,
            'role': role
        }
        save_users(users)
        return True
    return False

# 登录界面
def login_page():
    st.subheader("用户登录")
    
    # 初始化session_state
    if 'login_status' not in st.session_state:
        st.session_state.login_status = False
    
    if not st.session_state.login_status:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submit_button = st.form_submit_button("登录")
            
            if submit_button:
                if verify_user(username, password):
                    st.session_state.login_status = True
                    st.session_state.username = username
                    st.success(f"欢迎, {username}!")
                    st.experimental_rerun()
                else:
                    st.error("用户名或密码错误!")
        
        st.info("默认管理员账号: admin, 密码: admin123")
    else:
        st.success(f"已登录为: {st.session_state.username}")
        if st.button("退出登录", key="logout_button_login"):
            st.session_state.login_status = False
            if 'username' in st.session_state:
                del st.session_state.username
            st.experimental_rerun()

# 检查用户是否已登录
def is_authenticated():
    return st.session_state.get('login_status', False)

# 要求用户登录
def require_login():
    if not is_authenticated():
        login_page()
        return False
    return True
import streamlit as st
import sqlite3
import pandas as pd
import base64
from datetime import datetime
from streamlit_quill import st_quill
from io import BytesIO
from PIL import Image

# --- 数据库初始化 ---
def init_db():
    conn = sqlite3.connect('news_plus_data.db', check_same_thread=False)
    c = conn.cursor()
    # 增加 image 字段用于存储图片的 Base64 字符串
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_base64 TEXT,
            author TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# --- 图片处理工具 ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        # 打开图片并压缩，防止数据库过大
        img = Image.open(uploaded_file)
        img.thumbnail((800, 800))  # 限制最大尺寸
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# --- 数据库操作 ---
def add_article(title, content, image_b64, author):
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('INSERT INTO articles (title, content, image_base64, author, date) VALUES (?,?,?,?,?)', 
              (title, content, image_b64, author, date))
    conn.commit()

def update_article(id, title, content, image_b64):
    c = conn.cursor()
    if image_b64:
        c.execute('UPDATE articles SET title=?, content=?, image_base64=? WHERE id=?', (title, content, image_b64, id))
    else:
        c.execute('UPDATE articles SET title=?, content=? WHERE id=?', (title, content, id))
    conn.commit()

# --- 页面配置 ---
st.set_page_config(page_title="信息发布门户", layout="centered")

# --- 侧边栏：登录逻辑 ---
ADMIN_USER = "admin"
ADMIN_PASSWORD = "123"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("🛡️ 管理信息")
    if not st.session_state.logged_in:
        user = st.text_input("用户名")
        pwd = st.text_input("密码", type="password")
        if st.button("进入管理模式"):
            if user == ADMIN_USER and pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("验证失败")
    else:
        st.success("管理员在线")
        if st.button("退出登录"):
            st.session_state.logged_in = False
            st.rerun()

# --- 主界面 ---
st.title("🎨 信息资讯")

# 1. 管理员发布区
if st.session_state.logged_in:
    with st.expander("📝 编辑新文章", expanded=False):
        new_title = st.text_input("文章标题")
        
        st.write("正文编辑 (支持字体加粗、颜色、列表等):")
        # 富文本编辑器
        new_content = st_quill(placeholder="撰写内容...", key="main_editor")
        
        new_image = st.file_uploader("上传封面图片", type=["jpg", "png", "jpeg"])
        
        if st.button("发布文章"):
            if new_title and new_content:
                img_b64 = image_to_base64(new_image)
                add_article(new_title, new_content, img_b64, "系统管理员")
                st.success("发布成功！")
                st.rerun()
            else:
                st.warning("标题和内容不能为空")

# 2. 信息展示区
articles = pd.read_sql('SELECT * FROM articles ORDER BY id DESC', conn)

for _, row in articles.iterrows():
    with st.container():
        st.markdown("---")
        # 标题
        st.header(row['title'])
        # 元数据
        st.caption(f"📅 {row['date']}  |  👤 {row['author']}")
        
        # 显示图片
        if row['image_base64']:
            st.image(base64.b64decode(row['image_base64']), use_container_width=True)
        
        # 显示富文本内容 (注意：st.markdown 需要开启 unsafe_allow_html)
        st.markdown(row['content'], unsafe_allow_html=True)
        
        # 管理员操作
        if st.session_state.logged_in:
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("删除", key=f"del_{row['id']}"):
                    c = conn.cursor()
                    c.execute('DELETE FROM articles WHERE id=?', (row['id'],))
                    conn.commit()
                    st.rerun()
            with col2:
                if st.button("修改", key=f"edit_btn_{row['id']}"):
                    st.session_state[f"editing_{row['id']}"] = True

            # 修改表单
            if st.session_state.get(f"editing_{row['id']}", False):
                with st.form(f"form_{row['id']}"):
                    edit_title = st.text_input("标题", value=row['title'])
                    edit_content = st_quill(value=row['content'], key=f"editor_{row['id']}")
                    edit_img = st.file_uploader("更换图片 (留空保留原图)", type=["jpg", "png"])
                    
                    if st.form_submit_button("保存"):
                        img_b64 = image_to_base64(edit_img)
                        update_article(row['id'], edit_title, edit_content, img_b64)
                        st.session_state[f"editing_{row['id']}"] = False
                        st.rerun()
                    if st.form_submit_button("取消"):
                        st.session_state[f"editing_{row['id']}"] = False
                        st.rerun()

import streamlit as st
import sqlite3
import pandas as pd
import base64
from datetime import datetime
from streamlit_quill import st_quill
from io import BytesIO
from PIL import Image

# --- 数据库初始化 (保持不变) ---
def init_db():
    conn = sqlite3.connect('news_plus_data.db', check_same_thread=False)
    c = conn.cursor()
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

# --- 图片处理工具 (保持不变) ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        img.thumbnail((800, 800))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# --- 页面配置 ---
st.set_page_config(page_title="信息发布门户", layout="centered")

# ⭐ 核心修复：注入 Quill 的 CSS 样式表 ⭐
# 只有引入了这个 CSS，HTML 中的 ql-color-xxx 等类名才会生效
st.markdown("""
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <style>
        /* 这里的样式是为了让显示区域看起来更像文章 */
        .published-content {
            line-height: 1.6;
        }
        .ql-editor {
            padding: 0 !important; /* 移除编辑器默认内边距 */
            height: auto !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 侧边栏登录 (保持不变) ---
ADMIN_USER = "admin"
ADMIN_PASSWORD = "123"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("🛡️ 管理后台")
    if not st.session_state.logged_in:
        user = st.text_input("用户名")
        pwd = st.text_input("密码", type="password")
        if st.button("登录"):
            if user == ADMIN_USER and pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("失败")
    else:
        st.success("管理员已登录")
        if st.button("注销"):
            st.session_state.logged_in = False
            st.rerun()

# --- 主界面 ---
st.title("📢 信息资讯")

# 1. 发布功能
if st.session_state.logged_in:
    with st.expander("📝 编辑新文章", expanded=False):
        new_title = st.text_input("文章标题")
        st.write("正文编辑:")
        # 使用工具栏更全的配置
        new_content = st_quill(placeholder="撰写内容...", key="main_editor")
        new_image = st.file_uploader("上传图片", type=["jpg", "png", "jpeg"])
        
        if st.button("发布"):
            if new_title and new_content:
                img_b64 = image_to_base64(new_image)
                c = conn.cursor()
                c.execute('INSERT INTO articles (title, content, image_base64, author, date) VALUES (?,?,?,?,?)', 
                          (new_title, new_content, img_b64, "系统管理员", datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                st.success("发布成功！")
                st.rerun()

# 2. 展示功能
articles = pd.read_sql('SELECT * FROM articles ORDER BY id DESC', conn)

for _, row in articles.iterrows():
    with st.container():
        st.markdown("---")
        st.header(row['title'])
        st.caption(f"📅 {row['date']}  |  👤 {row['author']}")
        
        if row['image_base64']:
            st.image(base64.b64decode(row['image_base64']), use_container_width=True)
        
        # ⭐ 核心修复：渲染带样式的 HTML ⭐
        # 必须包裹在 class="ql-snow" 和 class="ql-editor" 内部
        full_html = f"""
        <div class="ql-snow">
            <div class="ql-editor published-content">
                {row['content']}
            </div>
        </div>
        """
        st.markdown(full_html, unsafe_allow_html=True)
        
        # 管理操作 (删除/修改)
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

            if st.session_state.get(f"editing_{row['id']}", False):
                with st.form(f"form_{row['id']}"):
                    edit_title = st.text_input("标题", value=row['title'])
                    # 修改时的编辑器
                    edit_content = st_quill(value=row['content'], key=f"editor_{row['id']}")
                    if st.form_submit_button("保存"):
                        c = conn.cursor()
                        c.execute('UPDATE articles SET title=?, content=? WHERE id=?', (edit_title, edit_content, row['id']))
                        conn.commit()
                        st.session_state[f"editing_{row['id']}"] = False
                        st.rerun()

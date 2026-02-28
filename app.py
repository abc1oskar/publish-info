import streamlit as st
import sqlite3
import pandas as pd
import base64
from datetime import datetime
from streamlit_quill import st_quill
from io import BytesIO
from PIL import Image

# --- 1. 数据库初始化 ---
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

# --- 2. 图片处理工具 ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        img.thumbnail((800, 800))  
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# --- 3. 页面配置与 CSS 样式注入 (解决间隙与颜色问题) ---
st.set_page_config(page_title="信息发布门户", layout="centered")

st.markdown("""
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <style>
        /* A. 压缩间距：主标题与内容区 */
        h1 { margin-bottom: -1.5rem !important; padding-bottom: 0rem; }
        
        /* B. 压缩间距：分隔线上下 */
        hr { margin-top: 0.5rem !important; margin-bottom: 0.8rem !important; }
        
        /* C. 压缩间距：文章标题与元数据 */
        h2 { margin-top: -1rem !important; margin-bottom: 0rem !important; }
        .stCaption { margin-top: -0.8rem !important; margin-bottom: 0.5rem !important; }

        /* D. 修复富文本样式：确保颜色和排版生效 */
        .ql-snow .ql-editor {
            padding: 0 !important;
            height: auto !important;
            line-height: 1.6;
            font-size: 16px;
        }
        /* 避免 Markdown 引擎解析干扰导致的 div 泄露 */
        .stMarkdown div { line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

# --- 4. 侧边栏：登录逻辑 ---
ADMIN_USER = "admin"
ADMIN_PASSWORD = "123"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("🛡️ 管理后台")
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

# --- 5. 主界面渲染 ---
st.title("📢 信息资讯")

# 1) 管理员发布入口
if st.session_state.logged_in:
    with st.expander("📝 发布新文章"):
        new_title = st.text_input("文章标题")
        st.write("正文编辑:")
        new_content = st_quill(placeholder="撰写内容...", key="main_editor")
        new_image = st.file_uploader("上传封面图片", type=["jpg", "png", "jpeg"])
        
        if st.button("立即发布"):
            if new_title and new_content:
                img_b64 = image_to_base64(new_image)
                c = conn.cursor()
                c.execute('INSERT INTO articles (title, content, image_base64, author, date) VALUES (?,?,?,?,?)', 
                          (new_title, new_content, img_b64, "系统管理员", datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                st.success("发布成功！")
                st.rerun()

# 2) 信息展示区
articles = pd.read_sql('SELECT * FROM articles ORDER BY id DESC', conn)

for _, row in articles.iterrows():
    with st.container():
        st.markdown("---")
        # 文章标题
        st.header(row['title'])
        # 时间与作者
        st.caption(f"📅 {row['date']}  |  👤 {row['author']}")
        
        # 显示图片
        if row['image_base64']:
            st.image(base64.b64decode(row['image_base64']), use_container_width=True)
        
        # 核心：显示富文本内容 (解决颜色失效与标签泄露)
        # 移除换行符防止 Markdown 引擎误读标签
        clean_content = row['content'].replace('\n', '')
        formatted_html = f'<div class="ql-snow"><div class="ql-editor">{clean_content}</div></div>'
        st.markdown(formatted_html, unsafe_allow_html=True)
        
        # 管理员操作按钮
        if st.session_state.logged_in:
            c1, c2 = st.columns([1, 5])
            with c1:
                if st.button("删除", key=f"del_{row['id']}"):
                    conn.cursor().execute('DELETE FROM articles WHERE id=?', (row['id'],))
                    conn.commit()
                    st.rerun()
            with c2:
                if st.button("修改", key=f"edit_btn_{row['id']}"):
                    st.session_state[f"editing_{row['id']}"] = True

            # 修改表单
            if st.session_state.get(f"editing_{row['id']}", False):
                with st.form(f"form_{row['id']}"):
                    edit_title = st.text_input("修改标题", value=row['title'])
                    edit_content = st_quill(value=row['content'], key=f"editor_{row['id']}")
                    edit_img = st.file_uploader("更换图片 (不选则保留原图)", type=["jpg", "png"])
                    
                    if st.form_submit_button("保存修改"):
                        img_b64 = image_to_base64(edit_img)
                        if img_b64:
                            conn.cursor().execute('UPDATE articles SET title=?, content=?, image_base64=? WHERE id=?', (edit_title, edit_content, img_b64, row['id']))
                        else:
                            conn.cursor().execute('UPDATE articles SET title=?, content=? WHERE id=?', (edit_title, edit_content, row['id']))
                        conn.commit()
                        st.session_state[f"editing_{row['id']}"] = False
                        st.rerun()
                    if st.form_submit_button("取消"):
                        st.session_state[f"editing_{row['id']}"] = False
                        st.rerun()

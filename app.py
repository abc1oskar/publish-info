import streamlit as st
import sqlite3
import pandas as pd
import base64
from datetime import datetime
from streamlit_quill import st_quill
from io import BytesIO
from PIL import Image

# --- 1. 数据库逻辑 (保持不变) ---
def init_db():
    conn = sqlite3.connect('news_pro_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, 
                  image_base64 TEXT, author TEXT, date TEXT)''')
    conn.commit()
    return conn

conn = init_db()

def image_to_base64(uploaded_file):
    if uploaded_file:
        img = Image.open(uploaded_file)
        img.thumbnail((800, 800))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# --- 2. 页面配置与 CSS 注入 ---
st.set_page_config(page_title="图文发布系统", layout="centered")

# 注入 Quill 样式，并强制去除 Markdown 干扰
st.markdown("""
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <style>
        /* 修复字体颜色和样式 */
        .ql-snow .ql-editor {
            padding: 0px !important;
            font-size: 1.1rem;
            line-height: 1.6;
            color: inherit;
        }
        /* 解决可能的空白边距问题 */
        .stMarkdown div {
            line-height: 1.6;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. 登录逻辑 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("⚙️ 管理面板")
    if not st.session_state.logged_in:
        user = st.text_input("账号")
        pwd = st.text_input("密码", type="password")
        if st.button("登录"):
            if user == "admin" and pwd == "123":
                st.session_state.logged_in = True
                st.rerun()
    else:
        st.write("✅ 已登录")
        if st.button("退出"):
            st.session_state.logged_in = False
            st.rerun()

# --- 4. 发布功能 ---
st.title("📢 校园信息发布")

if st.session_state.logged_in:
    with st.expander("➕ 发布新文章", expanded=False):
        t = st.text_input("文章标题")
        # 增加工具栏选项，确保颜色选择器出现
        c_text = st_quill(
            placeholder="写点什么...",
            toolbar_options=[
                ['bold', 'italic', 'underline'],
                [{'color': []}, {'background': []}], # 颜色和背景色
                [{'header': [1, 2, 3, False]}],
                ['link', 'image'],
                ['clean']
            ],
            key="editor_new"
        )
        img_file = st.file_uploader("配图", type=['jpg','png'])
        if st.button("确认发布"):
            if t and c_text:
                img_b64 = image_to_base64(img_file)
                cur = conn.cursor()
                cur.execute('INSERT INTO articles (title, content, image_base64, author, date) VALUES (?,?,?,?,?)',
                          (t, c_text, img_b64, "管理员", datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                st.success("发布成功")
                st.rerun()

# --- 5. 内容展示 (核心修正点) ---
articles = pd.read_sql('SELECT * FROM articles ORDER BY id DESC', conn)

for _, row in articles.iterrows():
    with st.container():
        st.markdown("---")
        st.header(row['title'])
        st.caption(f"🗓️ {row['date']}")
        
        if row['image_base64']:
            st.image(base64.b64decode(row['image_base64']))
        
        # --- 重点：修正 </div> 出现的问题 ---
        # 1. 确保内容中没有导致 Markdown 解析混乱的换行
        clean_content = row['content'].replace('\n', '')
        
        # 2. 使用组合字符串，确保 div 标签紧贴内容
        # 这样可以防止 Streamlit 将其中的 HTML 识别为普通的 Markdown
        html_display = (
            f'<div class="ql-snow">'
            f'<div class="ql-editor">'
            f'{clean_content}'
            f'</div></div>'
        )
        
        # 3. 渲染
        st.markdown(html_display, unsafe_allow_html=True)
        
        # 管理操作
        if st.session_state.logged_in:
            if st.button(f"🗑️ 删除", key=f"del_{row['id']}"):
                conn.cursor().execute('DELETE FROM articles WHERE id=?', (row['id'],))
                conn.commit()
                st.rerun()

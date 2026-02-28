import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 数据库初始化 ---
def init_db():
    conn = sqlite3.connect('news_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# --- 辅助函数 ---
def get_all_articles():
    return pd.read_sql('SELECT * FROM articles ORDER BY id DESC', conn)

def add_article(title, content, author):
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO articles (title, content, author, date) VALUES (?,?,?,?)', 
              (title, content, author, date))
    conn.commit()

def update_article(id, title, content):
    c = conn.cursor()
    c.execute('UPDATE articles SET title = ?, content = ? WHERE id = ?', (title, content, id))
    conn.commit()

def delete_article(id):
    c = conn.cursor()
    c.execute('DELETE FROM articles WHERE id = ?', (id,))
    conn.commit()

# --- 页面配置 ---
st.set_page_config(page_title="信息发布门户", layout="wide")

# --- 侧边栏：登录逻辑 ---
# 提示：实际生产中请使用加密存储密码，这里仅作演示
ADMIN_USER = "admin"
ADMIN_PASSWORD = "password123"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("🛡️ 权限管理")
    if not st.session_state.logged_in:
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        if st.button("登录"):
            if username == ADMIN_USER and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.success("管理员已登录")
                st.rerun()
            else:
                st.error("用户名或密码错误")
    else:
        st.write(f"当前身份: **管理员 ({ADMIN_USER})**")
        if st.button("注销"):
            st.session_state.logged_in = False
            st.rerun()

# --- 主界面 ---
st.title("📢 校园信息发布平台")

# 如果是管理员，显示发布入口
if st.session_state.logged_in:
    with st.expander("➕ 发布新信息"):
        with st.form("add_form", clear_on_submit=True):
            new_title = st.text_input("标题")
            new_author = st.text_input("发布者", value="系统管理员")
            new_content = st.text_area("内容")
            submit = st.form_submit_button("立即发布")
            if submit and new_title and new_content:
                add_article(new_title, new_content, new_author)
                st.success("信息发布成功！")
                st.rerun()

# --- 信息列表展示 ---
articles_df = get_all_articles()

if articles_df.empty:
    st.info("暂无发布的信息。")
else:
    for index, row in articles_df.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([0.8, 0.2])
            
            with col1:
                st.subheader(row['title'])
                st.caption(f"发布于: {row['date']} | 发布者: {row['author']}")
                st.write(row['content'])
            
            # 只有管理员可见修改和删除按钮
            if st.session_state.logged_in:
                with col2:
                    st.write("🛠️ 管理操作")
                    # 编辑功能
                    if st.button("修改", key=f"edit_{row['id']}"):
                        st.session_state.edit_id = row['id']
                    
                    # 删除功能
                    if st.button("删除", key=f"del_{row['id']}", type="primary"):
                        delete_article(row['id'])
                        st.warning("信息已删除")
                        st.rerun()

        # 处理编辑弹窗逻辑（通过 session_state 控制）
        if 'edit_id' in st.session_state and st.session_state.edit_id == row['id']:
            with st.form(f"edit_form_{row['id']}"):
                edit_title = st.text_input("修改标题", value=row['title'])
                edit_content = st.text_area("修改内容", value=row['content'])
                if st.form_submit_button("保存修改"):
                    update_article(row['id'], edit_title, edit_content)
                    del st.session_state.edit_id
                    st.success("修改成功！")
                    st.rerun()
                if st.form_submit_button("取消"):
                    del st.session_state.edit_id
                    st.rerun()

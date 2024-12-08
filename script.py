import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
import sqlite3
import json

# Streamlit Secrets から取得
CLIENT_ID = st.secrets["client_secret"]["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]["client_secret"]
REDIRECT_URI = st.secrets["client_secret"]["redirect_uri"]
AUTHORIZATION_URL = st.secrets["client_secret"]["auth_uri"]
TOKEN_URL = st.secrets["client_secret"]["token_uri"]
USER_INFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"


# データベース初期化
def init_db():
    conn = sqlite3.connect("user_data.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            favorite_item TEXT
        )
    """)
    return conn

# ユーザーの選択を保存
def save_user_preference(conn, user_id, favorite_item):
    conn.execute(
        "INSERT OR REPLACE INTO user_preferences (user_id, favorite_item) VALUES (?, ?)",
        (user_id, favorite_item),
    )
    conn.commit()

# ユーザーの選択を取得
def get_user_preference(conn, user_id):
    cursor = conn.execute("SELECT favorite_item FROM user_preferences WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

# 初期化
if "token" not in st.session_state:
    st.session_state.token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Streamlitアプリ
st.title("Google OAuth2 Login Example")

# OAuth認証フロー
oauth = OAuth2Session(CLIENT_ID, CLIENT_SECRET, redirect_uri=REDIRECT_URI)
auth_url, state = oauth.create_authorization_url(
    AUTHORIZATION_URL,
    response_type="code",
    scope="https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
)

code = st.query_params.get("code")

if not st.session_state.logged_in:
    if not code and not st.session_state.token:
        st.write(f"[Login with Google]({auth_url})")
    elif not st.session_state.token:
        try:
            # トークンを取得
            token = oauth.fetch_token(
                TOKEN_URL,
                code=code,
                redirect_uri=REDIRECT_URI,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET
            )
            st.session_state.token = token

            # ユーザー情報を取得
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            response = oauth.get(USER_INFO_URL, headers=headers)
            user_info = response.json()
            st.session_state.user_info = user_info
            st.session_state.logged_in = True
        except Exception as e:
            st.error(f"Token retrieval failed: {str(e)}")
            st.write(f"Authorization code: {code}")
    else:
        st.session_state.logged_in = True

if st.session_state.logged_in and st.session_state.user_info:
    user_info = st.session_state.user_info
    user_email = user_info.get("email")
    user_name = user_info.get("name")

    if user_email:
        st.success(f"Logged in as: {user_name} ({user_email})")

        # データベース
        conn = init_db()

        # 前回の選択を取得
        previous_favorite = get_user_preference(conn, user_email)
        if previous_favorite:
            st.write(f"Your previous favorite: {previous_favorite}")

        # 好きなものを選択
        favorite_item = st.selectbox("Choose your favorite item:", ["Apple", "Banana", "Cherry"], index=0)

        if st.button("Save"):
            save_user_preference(conn, user_email, favorite_item)
            st.success(f"Saved your favorite item: {favorite_item}")

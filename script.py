import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
from google.cloud import firestore
import json
import os
import atexit

# Streamlit Secrets から取得
CLIENT_ID = st.secrets["client_secret"]["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]["client_secret"]
REDIRECT_URI = st.secrets["client_secret"]["redirect_uris"]
AUTHORIZATION_URL = st.secrets["client_secret"]["auth_uri"]
TOKEN_URL = st.secrets["client_secret"]["token_uri"]
USER_INFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"


# Firestoreクライアントの初期化
def init_firestore():
    service_account_info = json.loads(st.secrets["firestore"]["service_account_json"])
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firestore_key.json"
    with open("firestore_key.json", "w") as f:
        json.dump(service_account_info, f)
    return firestore.Client()

# Firestoreにユーザーデータを保存
def save_user_preference_firestore(db, user_id, favorite_item):
    doc_ref = db.collection("user_preferences").document(user_id)
    doc_ref.set({"favorite_item": favorite_item})

# Firestoreからユーザーデータを取得
def get_user_preference_firestore(db, user_id):
    doc_ref = db.collection("user_preferences").document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("favorite_item")
    return None

# Firestoreキーのクリーンアップ
def cleanup_firestore_key():
    if os.path.exists("firestore_key.json"):
        os.remove("firestore_key.json")

atexit.register(cleanup_firestore_key)

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
        db = init_firestore()

        # 前回の選択を取得
        previous_favorite = get_user_preference_firestore(db, user_email)
        if previous_favorite:
            st.write(f"Your previous favorite: {previous_favorite}")

        # 好きなものを選択
        favorite_item = st.selectbox("Choose your favorite item:", ["Apple", "Banana", "Cherry"], index=0)

        if st.button("Save"):
            save_user_preference_firestore(db, user_email, favorite_item)
            st.success(f"Saved your favorite item: {favorite_item}")

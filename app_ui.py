import os
import json
import uuid
import datetime
import requests
import streamlit as st

APP_NAME = "Community AI"
MODELS = ["gemini 2.5 flash"]
SUGGESTIONS = [
    "Phân tích Technical Debt trong codebase",
    "Viết lại đoạn code này cho tối ưu",
    "Giải thích thuật toán từng bước (Socratic)",
    "Tóm tắt nội dung file đính kèm",
]

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversation_store.json")

st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")


def load_store():
    if os.path.exists(STORE_PATH):
        try:
            with open(STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_store():
    data = {
        "conversations": st.session_state.conversations,
        "current_conv_id": st.session_state.current_conv_id,
        "settings": {
            "theme": st.session_state.theme,
            "model": st.session_state.model,
            "username": st.session_state.username,
            "hint_level": st.session_state.hint_level,
        },
    }
    try:
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_state() -> None:
    defaults = {
        "theme": "dark",
        "model": MODELS[0],
        "username": "Nguoi dung",
        "composer_seq": 0,
        "show_attach": False,
        "hint_level": 1,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    if "conversations" not in st.session_state:
        store = load_store()
        if store and store.get("conversations"):
            st.session_state.conversations = store["conversations"]
            st.session_state.current_conv_id = store.get("current_conv_id") or next(iter(store["conversations"]))
            settings = store.get("settings", {})
            st.session_state.theme = settings.get("theme", st.session_state.theme)
            st.session_state.model = settings.get("model", st.session_state.model)
            st.session_state.username = settings.get("username", st.session_state.username)
            st.session_state.hint_level = settings.get("hint_level", st.session_state.hint_level)
        else:
            first_id = str(uuid.uuid4())
            st.session_state.conversations = {first_id: {"title": "Cuộc trò chuyện mới", "messages": [], "pinned": False}}
            st.session_state.current_conv_id = first_id
            save_store()


def current_conv() -> dict:
    return st.session_state.conversations[st.session_state.current_conv_id]


def new_conversation() -> None:
    cid = str(uuid.uuid4())
    st.session_state.conversations[cid] = {"title": "Cuộc trò chuyện mới", "messages": [], "pinned": False}
    st.session_state.current_conv_id = cid


def append_message(role: str, content: str, file_name: str = None) -> None:
    conv = current_conv()
    conv["messages"].append(
        {
            "role": role,
            "content": content,
            "file_name": file_name,
            "time": datetime.datetime.now().strftime("%H:%M"),
            "feedback": None,
        }
    )
    if role == "user" and conv["title"] == "Cuộc trò chuyện mới":
        conv["title"] = content.strip()[:36] + ("..." if len(content.strip()) > 36 else "")


def upload_file_to_backend(uploaded_file) -> bool:
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        response = requests.post(f"{BASE_URL}/api/v1/upload", files=files, timeout=120)
        return response.status_code == 200
    except Exception:
        return False


def call_model(user_text: str) -> str:
    payload = {
        "user_id": st.session_state.username,
        "question": user_text,
        "hint_level": st.session_state.hint_level,
    }
    try:
        response = requests.post(f"{BASE_URL}/api/v1/socratic", json=payload, timeout=120)
        if response.status_code == 200:
            return response.json().get("response", "Không nhận được phản hồi từ AI.")
        return f"Lỗi Backend ({response.status_code}): {response.text}"
    except Exception as e:
        return f"Lỗi kết nối Backend: {str(e)}"


def handle_send(text: str, uploaded_file=None) -> None:
    final_text = text.strip()
    file_name = None

    if uploaded_file is not None:
        file_name = uploaded_file.name
        with st.spinner(f"Đang nạp file '{file_name}' vào hệ thống RAG..."):
            upload_file_to_backend(uploaded_file)

    if not final_text and not file_name:
        st.toast("Vui lòng nhập nội dung hoặc đính kèm file.")
        return

    append_message("user", final_text if final_text else f"Đã gửi file: {file_name}", file_name=file_name)
    
    query_text = final_text
    if file_name:
        query_text = f"[Tài liệu đính kèm: {file_name}]\n{final_text}"

    with st.spinner("AI đang suy nghĩ..."):
        reply = call_model(query_text)

    append_message("assistant", reply)
    st.session_state.composer_seq += 1
    st.session_state.show_attach = False


init_state()


def build_css(theme: str) -> str:
    if theme == "dark":
        bg, surface, surface_alt = "#0E1117", "#161A23", "#1D222D"
        border, text, text_muted = "#2A2F3A", "#E6E8EC", "#8A919E"
        bubble_user, bubble_user_text, bubble_ai, accent = "#2563EB", "#FFFFFF", "#181E29", "#3B82F6"
    else:
        bg, surface, surface_alt = "#FFFFFF", "#F8F9FA", "#F1F3F5"
        border, text, text_muted = "#E9ECEF", "#212529", "#6C757D"
        bubble_user, bubble_user_text, bubble_ai, accent = "#2563EB", "#FFFFFF", "#F8F9FA", "#2563EB"

    return f"""
    <style>
    html, body, [class*="css"] {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important; }}
    .stApp {{ background-color: {bg} !important; color: {text} !important; }}
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {{ background-color: {surface} !important; border-right: 1px solid {border}; }}
    section[data-testid="stSidebar"] * {{ color: {text} !important; }}
    
    /* Form & Input inputs */
    textarea, input, div[data-baseweb="select"] > div {{ background-color: {surface_alt} !important; color: {text} !important; border: 1px solid {border} !important; border-radius: 8px !important; }}
    
    /* Buttons */
    div[data-testid="stButton"] > button {{ background-color: {surface_alt} !important; color: {text} !important; border: 1px solid {border} !important; border-radius: 8px !important; transition: all 0.2s; }}
    div[data-testid="stButton"] > button:hover {{ border-color: {accent} !important; color: {accent} !important; }}
    button[kind="primary"] {{ background-color: {accent} !important; color: #FFFFFF !important; border: none !important; font-weight: 600; }}
    
    /* Header Topbar */
    .app-topbar {{ display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid {border}; margin-bottom: 20px; }}
    .app-topbar .title {{ font-size: 16px; font-weight: 600; }}
    .app-topbar .meta {{ font-size: 12px; color: {text_muted}; display: flex; align-items: center; gap: 8px; }}
    .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background-color: #10B981; display: inline-block; }}
    
    /* Chat layout */
    .chat-wrapper {{ max-width: 850px; margin: 0 auto; padding: 0 10px; }}
    .row-user {{ display: flex; justify-content: flex-end; margin: 12px 0; }}
    .row-ai {{ display: flex; justify-content: flex-start; margin: 12px 0; }}
    
    .bubble-user {{ background-color: {bubble_user}; color: {bubble_user_text}; padding: 12px 16px; border-radius: 16px 16px 4px 16px; max-width: 78%; font-size: 14.5px; line-height: 1.5; }}
    .bubble-ai {{ background-color: {bubble_ai}; color: {text}; padding: 14px 18px; border-radius: 16px 16px 16px 4px; max-width: 82%; border: 1px solid {border}; font-size: 14.5px; line-height: 1.6; }}
    
    .file-badge {{ display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 6px; font-size: 12px; margin-bottom: 8px; border: 1px solid rgba(255,255,255,0.2); }}
    .msg-time {{ font-size: 11px; color: {text_muted}; margin-top: 4px; }}
    
    /* Action toolbar beneath messages */
    .action-bar {{ display: flex; gap: 4px; margin-top: 4px; opacity: 0.8; }}
    .action-bar div[data-testid="stButton"] > button {{ border: none !important; background: transparent !important; padding: 2px 6px !important; font-size: 13px !important; color: {text_muted} !important; }}
    .action-bar div[data-testid="stButton"] > button:hover {{ color: {accent} !important; background: {surface_alt} !important; }}
    </style>
    """


st.markdown(build_css(st.session_state.theme), unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### **{APP_NAME}**")
    st.caption("Trợ lý AI Trợ giúp Lập trình")

    if st.button("➕  Cuộc trò chuyện mới", use_container_width=True):
        new_conversation()
        st.rerun()

    st.divider()
    st.caption("LỊCH SỬ CHAT")

    # Sắp xếp các cuộc trò chuyện đã ghim lên đầu
    sorted_cids = sorted(
        st.session_state.conversations.keys(),
        key=lambda k: st.session_state.conversations[k].get("pinned", False),
        reverse=True
    )

    for cid in sorted_cids:
        conv = st.session_state.conversations[cid]
        is_active = cid == st.session_state.current_conv_id
        
        col_title, col_action = st.columns([0.82, 0.18])
        
        with col_title:
            prefix = "📌 " if conv.get("pinned") else ("💬 " if is_active else "  ")
            if st.button(f"{prefix}{conv['title']}", key=f"hist_{cid}", use_container_width=True):
                st.session_state.current_conv_id = cid
                st.rerun()
                
        with col_action:
            with st.popover("⋮", use_container_width=True):
                if st.button("Ghim / Bỏ ghim", key=f"pin_{cid}", use_container_width=True):
                    conv["pinned"] = not conv.get("pinned", False)
                    save_store()
                    st.rerun()
                
                new_title = st.text_input("Đổi tên", value=conv["title"], key=f"rn_inp_{cid}", label_visibility="collapsed")
                if st.button("Lưu tên", key=f"sv_{cid}", use_container_width=True):
                    conv["title"] = new_title
                    save_store()
                    st.rerun()
                
                if st.button("🗑️ Xóa", key=f"del_{cid}", use_container_width=True):
                    del st.session_state.conversations[cid]
                    if is_active and len(st.session_state.conversations) > 0:
                        st.session_state.current_conv_id = next(iter(st.session_state.conversations))
                    elif len(st.session_state.conversations) == 0:
                        new_conversation()
                    save_store()
                    st.rerun()

    st.divider()
    st.caption("CẤU HÌNH AI")
    current_idx = MODELS.index(st.session_state.model) if st.session_state.model in MODELS else 0
    st.session_state.model = st.selectbox("Model", MODELS, index=current_idx)
    st.session_state.hint_level = st.slider("Mức gợi ý Socratic", min_value=1, max_value=3, value=st.session_state.hint_level)

    st.divider()
    st.caption("TÀI KHOẢN & GIAO DIỆN")
    st.session_state.username = st.text_input("Tên hiển thị", st.session_state.username)
    theme_choice = st.radio("Giao diện", ["dark", "light"], index=0 if st.session_state.theme == "dark" else 1, horizontal=True)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

# --- MAIN CHAT UI ---
conv = current_conv()
st.markdown(
    f"""
    <div class="app-topbar">
        <div class="title">💬 {conv['title']}</div>
        <div class="meta"><span class="status-dot"></span>{st.session_state.model} | {st.session_state.username}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

if not conv["messages"]:
    st.info("👋 Xin chào! Hãy gửi tin nhắn hoặc đính kèm tài liệu để bắt đầu.")

for idx, msg in enumerate(conv["messages"]):
    if msg["role"] == "user":
        file_html = f'<div class="file-badge">📄 {msg["file_name"]}</div><br/>' if msg.get("file_name") else ""
        st.markdown(
            f'<div class="row-user"><div>'
            f'<div class="bubble-user">{file_html}{msg["content"]}</div>'
            f'<div class="msg-time" style="text-align:right;">{msg["time"]}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="row-ai"><div>'
            f'<div class="bubble-ai">{msg["content"]}</div>'
            f'<div class="msg-time">{msg["time"]}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="action-bar">', unsafe_allow_html=True)
        ac1, ac2, ac3, _ = st.columns([0.8, 0.8, 0.8, 9.6])
        with ac1:
            if st.button("📋", key=f"cp_{idx}", help="Sao chép"):
                st.toast("Đã sao chép nội dung!")
        with ac2:
            if st.button("👍", key=f"up_{idx}", help="Hữu ích"):
                st.toast("Cảm ơn đánh giá của bạn!")
        with ac3:
            if st.button("👎", key=f"dn_{idx}", help="Chưa tốt"):
                st.toast("Đã ghi nhận phản hồi!")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("<br/>", unsafe_allow_html=True)

# --- COMPOSER INPUT ---
composer_key = f"composer_{st.session_state.composer_seq}"

st.caption("Gợi ý câu hỏi:")
sug_cols = st.columns(len(SUGGESTIONS))
for i, s in enumerate(SUGGESTIONS):
    with sug_cols[i]:
        if st.button(s, key=f"sugg_{i}", use_container_width=True):
            st.session_state[composer_key] = s

st.text_area(
    "Message",
    key=composer_key,
    placeholder="Nhập câu hỏi hoặc dán mã lỗi vào đây...",
    label_visibility="collapsed",
    height=90,
)

tool_col1, _, send_col = st.columns([2, 7, 2])
with tool_col1:
    if st.button("Đính kèm file", use_container_width=True):
        st.session_state.show_attach = not st.session_state.show_attach
with send_col:
    send_clicked = st.button("Gửi 🚀", use_container_width=True, type="primary")

uploaded_file = None
if st.session_state.show_attach:
    uploaded_file = st.file_uploader("Upload file", type=["pdf", "txt", "py", "js", "docx", "png", "jpg"], label_visibility="collapsed")

if send_clicked:
    text = st.session_state.get(composer_key, "")
    handle_send(text, uploaded_file=uploaded_file)
    st.rerun()

save_store()
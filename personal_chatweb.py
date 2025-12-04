import streamlit as st
import requests
import json
import uuid
import os

# ==========================================
# [사용자 설정] 비밀번호 및 파일 설정
# ==========================================
ACCESS_PASSWORD = "15369" 
HISTORY_FILE = "chat_history.json"

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="Gemini Workspace",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# --- 2. 스타일링 (UI 레이아웃 고정) ---
st.markdown("""
<style>
    /* 1. 전체 레이아웃 & 색상 */
    .stApp { background-color: #ffffff; color: #1e293b; }
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    
    /* 2. 상단 탭바 고정 (Sticky) */
    .stTabs [data-baseweb="tab-list"] { 
        position: sticky;
        top: 2.5rem; /* 헤더 높이만큼 띄움 */
        z-index: 999;
        background-color: #ffffff;
        padding-top: 5px;
        padding-bottom: 5px;
        margin-bottom: 0px;
        border-bottom: 1px solid #f1f5f9;
    }

    /* 3. Expander (이름 변경) 고정 (Sticky) */
    /* 탭 바로 아래에 붙도록 설정 */
    .streamlit-expanderHeader {
        position: sticky;
        top: 6rem; /* 탭바 아래 위치 */
        z-index: 998;
        background-color: #ffffff !important;
        border-bottom: 1px solid #f0f0f0;
    }
    .streamlit-expanderContent {
        background-color: #ffffff;
        border-bottom: 1px solid #f0f0f0;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #f8fafc;
        border-radius: 6px 6px 0px 0px;
        color: #64748b;
        font-weight: 600;
        font-size: 0.9em;
        padding: 0 16px;
        border: 1px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #2563eb !important;
        border: 1px solid #e2e8f0;
        border-bottom: 1px solid #ffffff;
    }

    /* 채팅 메시지 스타일 */
    [data-testid="stChatMessage"] { 
        padding: 1rem; 
        border-radius: 12px; 
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #eff6ff; border: 1px solid #dbeafe; } /* User */
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #e2e8f0; } /* AI */
    
    /* 입력창 스타일 */
    .stTextInput > div > div > input { border-radius: 8px; border: 1px solid #cbd5e1; }
    
    /* 상단 헤더 영역 최소화 (여백 줄임) */
    .block-container { 
        padding-top: 1.5rem; 
        padding-bottom: 5rem; /* 입력창 가림 방지 */
    }
    
    /* 출처 박스 */
    .source-box {
        font-size: 0.75em; color: #64748b; background-color: #f8fafc;
        padding: 8px 12px; border-radius: 6px; margin-top: 8px; border: 1px solid #e2e8f0;
    }
    .source-box a { color: #3b82f6; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- 3. 로직 함수 ---

def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.info("🔒 Gemini Workspace")
            pwd = st.text_input("Password", type="password")
            if st.button("Login", use_container_width=True):
                if pwd == ACCESS_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Access Denied")
        st.stop() 

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return [{"id": str(uuid.uuid4()), "title": "Chat 1", "messages": []}]

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.sessions, f, ensure_ascii=False, indent=2)

# === 실행 ===
check_password()

if "sessions" not in st.session_state: st.session_state.sessions = load_history()
if "api_key" not in st.session_state: st.session_state.api_key = ""

# --- 4. 모델 데이터 ---
MODEL_OPTIONS = {
    "Nano Banana (Image Spec)": {
        "gemini-3-pro-image-preview": "Nano Banana Pro (ID: gemini-3-pro-image-preview)",
        "gemini-2.5-flash-image-preview": "Nano Banana (ID: gemini-2.5-flash-image-preview)",
        "gemini-2.5-flash-image": "Nano Banana (ID: gemini-2.5-flash-image)",
    },
    "Gemini 3.0 Series": {
        "gemini-3-pro-preview": "Gemini 3 Pro Preview",
    },
    "Gemini 2.5 Series": {
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite",
        "gemini-2.5-computer-use-preview-10-2025": "Gemini 2.5 Computer Use Preview",
    },
    "Gemini 2.0 Series": {
        "gemini-2.0-pro-exp-02-05": "Gemini 2.0 Pro Experimental 02-05",
        "gemini-2.0-pro-exp": "Gemini 2.0 Pro Experimental",
        "gemini-2.0-flash": "Gemini 2.0 Flash",
        "gemini-2.0-flash-lite": "Gemini 2.0 Flash-Lite",
        "gemini-2.0-flash-exp": "Gemini 2.0 Flash Experimental",
    },
    "Specialized & Latest": {
        "gemini-robotics-er-1.5-preview": "Gemini Robotics-ER 1.5 Preview",
        "gemini-exp-1206": "Gemini Experimental 1206",
        "gemini-pro-latest": "Gemini Pro Latest",
        "gemini-flash-latest": "Gemini Flash Latest",
    }
}

# --- 5. 사이드바 ---
with st.sidebar:
    st.header("Settings")
    with st.expander("🔑 API Key", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("Key", value=st.session_state.api_key, type="password")
        if not st.session_state.api_key: st.warning("Required")

    st.subheader("Neural Engine")
    cat = st.selectbox("Category", options=MODEL_OPTIONS.keys(), label_visibility="collapsed")
    model_map = MODEL_OPTIONS[cat]
    selected_model_name = st.selectbox("Model", options=model_map.values(), label_visibility="collapsed")
    selected_model_id = [k for k, v in model_map.items() if v == selected_model_name][0]
    st.caption(f"ID: {selected_model_id}")

    st.markdown("---")
    use_google_search = st.toggle("🌐 Search", value=False)
    st.markdown("---")

    with st.expander("Parameters"):
        temperature = st.slider("Temp", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("Persona", height=100)

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("➕ Tab", use_container_width=True):
        if len(st.session_state.sessions) < 10:
            st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Chat {len(st.session_state.sessions)+1}", "messages": []})
            save_history()
            st.rerun()
    if c2.button("🗑️ Reset", use_container_width=True):
        if len(st.session_state.sessions) > 1: st.session_state.sessions.pop()
        else: 
            st.session_state.sessions[0]["messages"] = []
            st.session_state.sessions[0]["title"] = "Chat 1"
        save_history()
        st.rerun()
    
    st.markdown("---")
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 6. 메인 화면 ---
c1, c2 = st.columns([1, 1])
with c1: st.markdown("### ❄️ Gemini Desktop")
with c2: st.markdown(f"<div style='text-align:right; color:#94a3b8; font-size:0.8em; padding-top:10px;'>{selected_model_name}</div>", unsafe_allow_html=True)

# 탭바
tabs = st.tabs([s["title"] for s in st.session_state.sessions])

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        
        # [고정] 이름 변경 (Sticky CSS 적용됨)
        with st.expander("Edit Tab Name", expanded=False):
            new_title = st.text_input("Title", value=session["title"], key=f"title_{session['id']}")
            if new_title != session["title"]:
                session["title"] = new_title
                save_history()
                st.rerun()

        # [스크롤] 채팅 영역 (높이 고정 550px)
        # 이 높이를 넘어가면 박스 안에 스크롤이 생깁니다.
        chat_container = st.container(height=550, border=False)
        
        with chat_container:
            if not session["messages"]: st.info("새로운 대화가 시작되었습니다.")
            
            for msg in session["messages"]:
                avatar = "🧑‍💻" if msg["role"] == "user" else "❄️"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])
                    if "sources" in msg and msg["sources"]:
                        source_html = "<div class='source-box'>📚 <b>Source:</b><br>"
                        for src in msg["sources"]:
                            source_html += f"• <a href='{src.get('uri','#')}' target='_blank'>{src.get('title','Link')}</a><br>"
                        source_html += "</div>"
                        st.markdown(source_html, unsafe_allow_html=True)

        # [고정] 입력창 (Streamlit Default Fixed Footer)
        if prompt := st.chat_input("Message...", key=f"input_{session['id']}"):
            if not st.session_state.api_key: st.stop()

            session["messages"].append({"role": "user", "content": prompt})
            save_history()
            
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"): st.markdown(prompt)

            with chat_container:
                with st.chat_message("assistant", avatar="❄️"):
                    ph = st.empty()
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                        
                        api_contents = []
                        for m in session["messages"][-20:-1]:
                            role = "user" if m["role"] == "user" else "model"
                            api_contents.append({"role": role, "parts": [{"text": m["content"]}]})
                        api_contents.append({"role": "user", "parts": [{"text": prompt}]})

                        payload = {
                            "contents": api_contents,
                            "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
                            "safetySettings": [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                            ]
                        }

                        if use_google_search: payload["tools"] = [{"google_search": {}}]
                        if system_prompt.strip(): payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

                        res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                        
                        if res.status_code == 200:
                            data = res.json()
                            if "candidates" in data and data["candidates"]:
                                cand = data["candidates"][0]
                                bot_text = cand["content"]["parts"][0]["text"]
                                
                                sources = []
                                md = cand.get("groundingMetadata", {})
                                if "groundingChunks" in md:
                                    for c in md["groundingChunks"]:
                                        if "web" in c: sources.append(c["web"])

                                ph.markdown(bot_text)
                                if sources:
                                    html = "<div class='source-box'>📚 <b>Source:</b><br>"
                                    for s in sources: html += f"• <a href='{s.get('uri','#')}' target='_blank'>{s.get('title','Link')}</a><br>"
                                    html += "</div>"
                                    st.markdown(html, unsafe_allow_html=True)

                                session["messages"].append({"role": "assistant", "content": bot_text, "sources": sources})
                                save_history()
                            else: ph.warning("No Response")
                        else: ph.error(f"Error {res.status_code}: {res.text}")
                    except Exception as e: ph.error(str(e))

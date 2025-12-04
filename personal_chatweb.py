import streamlit as st
import requests
import json
import uuid
import os

# ==========================================
# [사용자 설정] 여기에 원하는 비밀번호를 입력하세요
# ==========================================
ACCESS_PASSWORD = "1234" 
HISTORY_FILE = "chat_history.json"  # 대화 내용이 저장될 파일명

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="Gemini Workspace",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# --- 2. 스타일링 ---
st.markdown("""
<style>
    /* 전체 배경 화이트 */
    .stApp { background-color: #ffffff; color: #1e293b; }
    
    /* 사이드바 배경 */
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    
    /* 탭바 고정 (Sticky) - 스크롤해도 탭은 상단에 남음 */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px;
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: #ffffff;
        padding-top: 10px;
        padding-bottom: 5px;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #f1f5f9; border-radius: 8px 8px 0px 0px;
        color: #64748b; font-weight: 600; padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important; color: #3b82f6 !important;
        border-top: 2px solid #3b82f6; border-bottom: 0px solid transparent;
    }

    /* 채팅 메시지 스타일 */
    [data-testid="stChatMessage"] { padding: 1rem; border-radius: 12px; margin-bottom: 10px; }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #eff6ff; border: 1px solid #dbeafe; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #e2e8f0; }
    .stTextInput > div > div > input { border-radius: 10px; border: 1px solid #cbd5e1; }
    
    /* 출처 박스 */
    .source-box {
        font-size: 0.8em; color: #64748b; background-color: #f1f5f9;
        padding: 8px; border-radius: 6px; margin-top: 8px; border: 1px solid #e2e8f0;
    }
    .source-box a { color: #3b82f6; text-decoration: none; }
    
    /* [수정] 상단 여백 확보 (잘림 방지) */
    .block-container { 
        padding-top: 3.5rem; 
        padding-bottom: 0rem; 
    }
    
    /* 로그인 화면 중앙 정렬용 */
    .login-container {
        display: flex; justify-content: center; align-items: center; height: 100vh;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. [기능] 로그인 및 데이터 저장 로직 ---

def check_password():
    """비밀번호 확인 함수"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("<br><br>", unsafe_allow_html=True) # 상단 여백 추가
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("🔒 접근 제어 시스템")
            pwd = st.text_input("비밀번호를 입력하세요", type="password")
            if st.button("로그인", use_container_width=True):
                if pwd == ACCESS_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
        st.stop() 

def load_history():
    """파일에서 대화 기록 불러오기"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return [{"id": str(uuid.uuid4()), "title": "Chat 1", "messages": []}]
    return [{"id": str(uuid.uuid4()), "title": "Chat 1", "messages": []}]

def save_history():
    """파일에 대화 기록 저장하기"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.sessions, f, ensure_ascii=False, indent=2)

# === 로그인 체크 ===
check_password()

# --- 4. 초기화 ---
if "sessions" not in st.session_state:
    st.session_state.sessions = load_history()

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 5. 모델 데이터베이스 ---
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

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    with st.expander("🔑 API Key", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("Google AI Key", value=st.session_state.api_key, type="password")
        if not st.session_state.api_key: st.warning("⚠️ API Key 필요")

    st.subheader("Neural Engine")
    cat = st.selectbox("Series", options=MODEL_OPTIONS.keys(), label_visibility="collapsed")
    model_map = MODEL_OPTIONS[cat]
    selected_model_name = st.selectbox("Model", options=model_map.values(), label_visibility="collapsed")
    selected_model_id = [k for k, v in model_map.items() if v == selected_model_name][0]
    st.caption(f"ID: {selected_model_id}")

    st.markdown("---")
    use_google_search = st.toggle("🌐 Google Search", value=False)
    st.markdown("---")

    with st.expander("🎛️ Parameters"):
        temperature = st.slider("Creativity", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("System Persona", height=100)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("➕ New Tab", use_container_width=True):
            if len(st.session_state.sessions) < 10:
                st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Chat {len(st.session_state.sessions) + 1}", "messages": []})
                save_history()
                st.rerun()
            else: st.error("Max 10 tabs.")
    with col_b:
        if st.button("🗑️ Reset", use_container_width=True):
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

# --- 7. 메인 화면 ---
col1, col2 = st.columns([2, 3])
with col1: st.markdown("### ❄️ Gemini Desktop")
with col2: st.markdown(f"<div style='text-align:right; color:#64748b; font-size:0.8em; padding-top:10px;'>Active: {selected_model_name} {'(🔍Search On)' if use_google_search else ''}</div>", unsafe_allow_html=True)

# 탭 생성
tabs = st.tabs([s["title"] for s in st.session_state.sessions])

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        
        # 탭 이름 수정 기능 (이 부분이 스크롤되어 사라지지 않도록 Sticky 처리하기 어려움 -> 대신 컨테이너 사용으로 해결)
        # st.container(height=...)를 사용하면 내부만 스크롤되므로 
        # 이 상단 영역(Edit Tab Name)은 화면에 고정된 것처럼 보입니다.
        
        with st.expander("Edit Tab Name", expanded=False):
            new_title = st.text_input("Title", value=session["title"], key=f"title_{session['id']}")
            if new_title != session["title"]:
                session["title"] = new_title
                save_history()
                st.rerun()

        # [고정 높이 컨테이너] 
        # 화면에 꽉 차게 보이되, 메인 스크롤바가 생기지 않도록 높이 설정 (약 600px ~ 650px)
        chat_container = st.container(height=600, border=False)
        
        with chat_container:
            if not session["messages"]: st.info("대화를 시작하세요.")
            
            for msg in session["messages"]:
                avatar = "🧑‍💻" if msg["role"] == "user" else "❄️"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])
                    if "sources" in msg and msg["sources"]:
                        source_html = "<div class='source-box'>📚 <b>검색 출처:</b><br>"
                        for src in msg["sources"]:
                            title = src.get('title', 'Link')
                            uri = src.get('uri', '#')
                            source_html += f"• <a href='{uri}' target='_blank'>{title}</a><br>"
                        source_html += "</div>"
                        st.markdown(source_html, unsafe_allow_html=True)

        if prompt := st.chat_input("Message...", key=f"input_{session['id']}"):
            if not st.session_state.api_key: st.stop()

            session["messages"].append({"role": "user", "content": prompt})
            save_history()
            
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"): st.markdown(prompt)

            with chat_container:
                with st.chat_message("assistant", avatar="❄️"):
                    msg_ph = st.empty()
                    
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                        
                        api_contents = []
                        for m in session["messages"][-20:-1]:
                            role = "user" if m["role"] == "user" else "model"
                            api_contents.append({"role": role, "parts": [{"text": m["content"]}]})
                        api_contents.append({"role": "user", "parts": [{"text": prompt}]})

                        payload = {
                            "contents": api_contents,
                            "generationConfig": {
                                "temperature": temperature,
                                "maxOutputTokens": 8192,
                            },
                             "safetySettings": [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                            ]
                        }

                        if use_google_search: payload["tools"] = [{"google_search": {}}]
                        if system_prompt.strip(): payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

                        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                        
                        if response.status_code == 200:
                            data = response.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                candidate = candidates[0]
                                bot_text = candidate["content"]["parts"][0]["text"]
                                
                                grounding_sources = []
                                grounding_metadata = candidate.get("groundingMetadata", {})
                                if "groundingChunks" in grounding_metadata:
                                    for chunk in grounding_metadata["groundingChunks"]:
                                        if "web" in chunk: grounding_sources.append(chunk["web"])

                                msg_ph.markdown(bot_text)
                                if grounding_sources:
                                    source_html = "<div class='source-box'>📚 <b>검색 출처:</b><br>"
                                    for src in grounding_sources:
                                        title = src.get('title', '참고 링크')
                                        uri = src.get('uri', '#')
                                        source_html += f"• <a href='{uri}' target='_blank'>{title}</a><br>"
                                    source_html += "</div>"
                                    st.markdown(source_html, unsafe_allow_html=True)

                                session["messages"].append({
                                    "role": "assistant", 
                                    "content": bot_text,
                                    "sources": grounding_sources
                                })
                                save_history()
                            else:
                                msg_ph.warning("응답 없음.")
                        else:
                            msg_ph.error(f"Error {response.status_code}: {response.text}")
                            
                    except Exception as e:
                        msg_ph.error(str(e))



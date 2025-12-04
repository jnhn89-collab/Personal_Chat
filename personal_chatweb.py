import streamlit as st
import requests
import json
import uuid

# --- 1. 페이지 설정 (수정됨: 사이드바 기본 열림) ---
st.set_page_config(
    page_title="Gemini Workspace",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# --- 2. 세션 상태 초기화 ---
if "sessions" not in st.session_state:
    st.session_state.sessions = [{"id": str(uuid.uuid4()), "title": "Chat 1", "messages": []}]
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 3. UI 스타일링 (헤더 숨김 코드 삭제됨) ---
st.markdown("""
<style>
    /* 전체 배경 화이트 */
    .stApp {
        background-color: #ffffff;
        color: #1e293b;
    }
    
    /* 사이드바 배경 */
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        color: #64748b;
        font-weight: 600;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #3b82f6 !important;
        border-top: 2px solid #3b82f6;
        border-bottom: 0px solid transparent;
    }

    /* 채팅 메시지 스타일 */
    [data-testid="stChatMessage"] {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 10px;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #eff6ff; /* User: Light Blue */
        border: 1px solid #dbeafe;
    }
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #ffffff; /* AI: White */
        border: 1px solid #e2e8f0;
    }
    
    /* 입력창 디자인 */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 1px solid #cbd5e1;
    }
    
    /* 상단 여백 줄이기 */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. 모델 데이터베이스 ---
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

# --- 5. 사이드바 (설정) ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key 입력
    with st.expander("🔑 API Key", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input(
            "Google AI Key", 
            value=st.session_state.api_key, 
            type="password",
            placeholder="AIzaSy..."
        )
        if not st.session_state.api_key:
            st.warning("⚠️ 키를 입력해야 대화가 가능합니다.")

    st.subheader("Neural Engine")
    
    # 카테고리 선택
    cat = st.selectbox("Series", options=MODEL_OPTIONS.keys(), label_visibility="collapsed")
    model_map = MODEL_OPTIONS[cat]
    
    # 모델 선택
    selected_model_name = st.selectbox("Model", options=model_map.values(), label_visibility="collapsed")
    selected_model_id = [k for k, v in model_map.items() if v == selected_model_name][0]
    
    st.caption(f"ID: {selected_model_id}")

    # 파라미터
    with st.expander("🎛️ Parameters"):
        temperature = st.slider("Creativity", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("System Persona", height=100)

    st.divider()
    
    # 탭 관리 버튼
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("➕ New Tab", use_container_width=True):
            if len(st.session_state.sessions) < 10:
                st.session_state.sessions.append({
                    "id": str(uuid.uuid4()), 
                    "title": f"Chat {len(st.session_state.sessions) + 1}", 
                    "messages": []
                })
                st.rerun()
            else:
                st.error("탭은 최대 10개까지입니다.")
    with col_b:
        if st.button("🗑️ Reset", use_container_width=True):
             if len(st.session_state.sessions) > 1:
                st.session_state.sessions.pop()
             else:
                st.session_state.sessions[0]["messages"] = []
                st.session_state.sessions[0]["title"] = "Chat 1"
             st.rerun()

# --- 6. 메인 화면 ---
col1, col2 = st.columns([2, 3])
with col1:
    st.markdown("### ❄️ Gemini Desktop")
with col2:
    st.markdown(f"<div style='text-align:right; color:#64748b; font-size:0.8em; padding-top:10px;'>Active: {selected_model_name}</div>", unsafe_allow_html=True)

# 탭 생성
tabs = st.tabs([s["title"] for s in st.session_state.sessions])

# 각 탭별 로직
for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        
        # 탭 이름 수정 기능
        with st.expander("Edit Tab Name", expanded=False):
            new_title = st.text_input("Tab Title", value=session["title"], key=f"title_{session['id']}")
            if new_title != session["title"]:
                session["title"] = new_title
                st.rerun()

        # 채팅 표시 영역
        chat_container = st.container()
        with chat_container:
            if not session["messages"]:
                st.info("대화를 시작하세요. (설정은 왼쪽 사이드바 👈)")
            
            for msg in session["messages"]:
                avatar = "🧑‍💻" if msg["role"] == "user" else "❄️"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # 입력창
        if prompt := st.chat_input("Message Gemini...", key=f"input_{session['id']}"):
            if not st.session_state.api_key:
                st.error("왼쪽 사이드바에서 API Key를 먼저 입력해주세요.")
                st.stop()

            # 유저 메시지 추가
            session["messages"].append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(prompt)

            # API 호출
            with chat_container:
                with st.chat_message("assistant", avatar="❄️"):
                    message_placeholder = st.empty()
                    
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                        
                        # 히스토리 구성 (최근 20개)
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

                        if system_prompt.strip():
                            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

                        # 요청
                        headers = {'Content-Type': 'application/json'}
                        response = requests.post(url, headers=headers, data=json.dumps(payload))
                        
                        if response.status_code == 200:
                            data = response.json()
                            if "candidates" in data and data["candidates"]:
                                bot_text = data["candidates"][0]["content"]["parts"][0]["text"]
                                message_placeholder.markdown(bot_text)
                                session["messages"].append({"role": "assistant", "content": bot_text})
                            else:
                                message_placeholder.warning("모델이 응답하지 않았습니다. (내용 없음)")
                        else:
                            message_placeholder.error(f"API Error {response.status_code}: {response.text}")
                            
                    except Exception as e:
                        message_placeholder.error(f"System Error: {str(e)}")


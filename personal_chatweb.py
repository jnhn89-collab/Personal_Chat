import streamlit as st
import requests
import json
import uuid

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Gemini Workspace",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 세션 초기화 ---
if "sessions" not in st.session_state:
    st.session_state.sessions = [{"id": str(uuid.uuid4()), "title": "New Chat", "messages": []}]
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 스타일링 (Clean White) ---
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #1e293b; }
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #f1f5f9; border-radius: 8px 8px 0px 0px;
        color: #64748b; font-weight: 600; padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important; color: #3b82f6 !important;
        border-top: 2px solid #3b82f6;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #eff6ff; border: 1px solid #dbeafe; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #e2e8f0; }
    .stTextInput > div > div > input { border-radius: 10px; border: 1px solid #cbd5e1; }
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 모델 데이터베이스 (리스트 원문 100% 반영) ---
MODEL_OPTIONS = {
    "Nano Banana (Code Name)": {
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
        "gemini-2.5-pro-preview-tts": "Gemini 2.5 Pro TTS (Audio Only - 주의)",
        "gemini-2.5-flash-preview-tts": "Gemini 2.5 Flash TTS (Audio Only - 주의)",
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

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ Settings")
    with st.expander("🔑 API Key", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("Google AI Key", value=st.session_state.api_key, type="password")

    st.subheader("Select Model")
    cat = st.selectbox("Category", options=MODEL_OPTIONS.keys(), label_visibility="collapsed")
    model_map = MODEL_OPTIONS[cat]
    selected_model_name = st.selectbox("Model ID", options=model_map.values(), label_visibility="collapsed")
    # 이름에서 ID 역추적
    selected_model_id = [k for k, v in model_map.items() if v == selected_model_name][0]
    
    # 선택된 모델 정보 표시
    st.info(f"Target ID: {selected_model_id}")

    with st.expander("🎛️ Parameters"):
        temperature = st.slider("Creativity", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("System Persona", height=100)

    st.divider()
    if st.button("➕ New Chat Tab", use_container_width=True):
        if len(st.session_state.sessions) < 10:
            st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Chat {len(st.session_state.sessions) + 1}", "messages": []})
            st.rerun()
    
    if len(st.session_state.sessions) > 0:
         if st.button("🗑️ Reset/Delete Tab", use_container_width=True):
            if len(st.session_state.sessions) > 1:
                st.session_state.sessions.pop()
            else:
                st.session_state.sessions[0]["messages"] = []
                st.session_state.sessions[0]["title"] = "New Chat"
            st.rerun()

# --- 메인 ---
col1, col2 = st.columns([1, 4])
with col1: st.markdown("### ❄️ Gemini Desktop")
with col2: st.markdown(f"<div style='text-align:right; color:#64748b; font-size:0.8em; padding-top:10px;'>Active: {selected_model_name}</div>", unsafe_allow_html=True)

tabs = st.tabs([s["title"] for s in st.session_state.sessions])

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        
        # 탭 이름 변경
        with st.expander("Edit Tab Name"):
            new_title = st.text_input("Name", value=session["title"], key=f"title_{session['id']}")
            if new_title != session["title"]:
                session["title"] = new_title
                st.rerun()

        # 채팅 영역
        chat_container = st.container()
        with chat_container:
            if not session["messages"]:
                st.caption("Ready to connect.")
            for msg in session["messages"]:
                avatar = "🧑‍💻" if msg["role"] == "user" else "❄️"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # 입력 영역
        if prompt := st.chat_input("Message...", key=f"in_{session['id']}"):
            if not st.session_state.api_key:
                st.error("API Key Required")
                st.stop()

            session["messages"].append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"): st.markdown(prompt)

            with chat_container:
                with st.chat_message("assistant", avatar="❄️"):
                    msg_ph = st.empty()
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                        
                        api_msgs = []
                        for m in session["messages"][-20:-1]:
                            role = "user" if m["role"] == "user" else "model"
                            api_msgs.append({"role": role, "parts": [{"text": m["content"]}]})
                        api_msgs.append({"role": "user", "parts": [{"text": prompt}]})

                        payload = {
                            "contents": api_msgs,
                            "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
                            "safetySettings": [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                            ]
                        }
                        if system_prompt.strip(): payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

                        resp = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            if "candidates" in data and data["candidates"]:
                                bot_text = data["candidates"][0]["content"]["parts"][0]["text"]
                                msg_ph.markdown(bot_text)
                                session["messages"].append({"role": "assistant", "content": bot_text})
                            else:
                                msg_ph.error("No content generated.")
                        else:
                            msg_ph.error(f"Error {resp.status_code}: {resp.text}")
                    except Exception as e:
                        msg_ph.error(str(e))

    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 모델 데이터베이스 (리스트 원문 100% 반영) ---
MODEL_OPTIONS = {
    "Nano Banana (Code Name)": {
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
        "gemini-2.5-pro-preview-tts": "Gemini 2.5 Pro TTS (Audio Only - 주의)",
        "gemini-2.5-flash-preview-tts": "Gemini 2.5 Flash TTS (Audio Only - 주의)",
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

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ Settings")
    with st.expander("🔑 API Key", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("Google AI Key", value=st.session_state.api_key, type="password")

    st.subheader("Select Model")
    cat = st.selectbox("Category", options=MODEL_OPTIONS.keys(), label_visibility="collapsed")
    model_map = MODEL_OPTIONS[cat]
    selected_model_name = st.selectbox("Model ID", options=model_map.values(), label_visibility="collapsed")
    # 이름에서 ID 역추적
    selected_model_id = [k for k, v in model_map.items() if v == selected_model_name][0]
    
    # 선택된 모델 정보 표시
    st.info(f"Target ID: {selected_model_id}")

    with st.expander("🎛️ Parameters"):
        temperature = st.slider("Creativity", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("System Persona", height=100)

    st.divider()
    if st.button("➕ New Chat Tab", use_container_width=True):
        if len(st.session_state.sessions) < 10:
            st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Chat {len(st.session_state.sessions) + 1}", "messages": []})
            st.rerun()
    
    if len(st.session_state.sessions) > 0:
         if st.button("🗑️ Reset/Delete Tab", use_container_width=True):
            if len(st.session_state.sessions) > 1:
                st.session_state.sessions.pop()
            else:
                st.session_state.sessions[0]["messages"] = []
                st.session_state.sessions[0]["title"] = "New Chat"
            st.rerun()

# --- 메인 ---
col1, col2 = st.columns([1, 4])
with col1: st.markdown("### ❄️ Gemini Desktop")
with col2: st.markdown(f"<div style='text-align:right; color:#64748b; font-size:0.8em; padding-top:10px;'>Active: {selected_model_name}</div>", unsafe_allow_html=True)

tabs = st.tabs([s["title"] for s in st.session_state.sessions])

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        
        # 탭 이름 변경
        with st.expander("Edit Tab Name"):
            new_title = st.text_input("Name", value=session["title"], key=f"title_{session['id']}")
            if new_title != session["title"]:
                session["title"] = new_title
                st.rerun()

        # 채팅 영역
        chat_container = st.container()
        with chat_container:
            if not session["messages"]:
                st.caption("Ready to connect.")
            for msg in session["messages"]:
                avatar = "🧑‍💻" if msg["role"] == "user" else "❄️"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # 입력 영역
        if prompt := st.chat_input("Message...", key=f"in_{session['id']}"):
            if not st.session_state.api_key:
                st.error("API Key Required")
                st.stop()

            session["messages"].append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"): st.markdown(prompt)

            with chat_container:
                with st.chat_message("assistant", avatar="❄️"):
                    msg_ph = st.empty()
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                        
                        api_msgs = []
                        for m in session["messages"][-20:-1]:
                            role = "user" if m["role"] == "user" else "model"
                            api_msgs.append({"role": role, "parts": [{"text": m["content"]}]})
                        api_msgs.append({"role": "user", "parts": [{"text": prompt}]})

                        payload = {
                            "contents": api_msgs,
                            "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
                            "safetySettings": [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                            ]
                        }
                        if system_prompt.strip(): payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

                        resp = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            if "candidates" in data and data["candidates"]:
                                bot_text = data["candidates"][0]["content"]["parts"][0]["text"]
                                msg_ph.markdown(bot_text)
                                session["messages"].append({"role": "assistant", "content": bot_text})
                            else:
                                msg_ph.error("No content generated.")
                        else:
                            msg_ph.error(f"Error {resp.status_code}: {resp.text}")
                    except Exception as e:
                        msg_ph.error(str(e))

        border-right: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# --- 모델 데이터베이스 (2025.12.04 기준) ---
MODEL_OPTIONS = {
    "NEXT GEN (Gemini 3.0)": {
        "gemini-3-pro-preview": "Gemini 3 Pro Preview (Flagship)",
        "gemini-3-pro-image-preview": "Nano Banana Pro (3.0 Multimodal)",
    },
    "Gemini 2.5 Series (Nano Banana)": {
        "gemini-2.5-pro": "Gemini 2.5 Pro (Standard)",
        "gemini-2.5-flash": "Gemini 2.5 Flash (Nano Banana)",
        "gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite (Lightweight)",
        "gemini-2.5-computer-use-preview-10-2025": "Gemini 2.5 Computer Use (Agent)",
    },
    "Gemini 2.0 Series (Stable)": {
        "gemini-2.0-pro-exp-02-05": "Gemini 2.0 Pro Experimental",
        "gemini-2.0-flash": "Gemini 2.0 Flash (Fast)",
        "gemini-2.0-flash-lite": "Gemini 2.0 Flash-Lite (Ultra Fast)",
    },
    "Experimental & Legacy": {
        "gemini-exp-1206": "Gemini Exp 1206 (Latest Exp)",
        "gemini-robotics-er-1.5-preview": "Gemini Robotics 1.5",
        "gemini-pro-latest": "Gemini 1.5 Pro Latest",
    }
}

# --- 세션 상태 초기화 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 사이드바 설정 ---
with st.sidebar:
    st.title("🧬 GENESIS CORE")
    st.caption("v2025.12.04 | Command Center")
    
    # API Key 입력
    api_key_input = st.text_input(
        "API Protocol Key", 
        type="password", 
        value=st.session_state.api_key,
        placeholder="Paste Google AI Key here...",
        help="Google AI Studio에서 발급받은 키를 입력하세요."
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.markdown("---")
    
    # 모델 선택 로직
    selected_category = st.selectbox("Model Series", options=MODEL_OPTIONS.keys())
    model_map = MODEL_OPTIONS[selected_category]
    selected_model_display = st.selectbox("Neural Engine", options=model_map.values())
    
    # 선택된 모델의 실제 ID 찾기
    selected_model_id = [k for k, v in model_map.items() if v == selected_model_display][0]
    
    st.info(f"ID: {selected_model_id}")

    st.markdown("---")

    # 파라미터 설정
    temperature = st.slider("Entropy (Temperature)", 0.0, 2.0, 0.7, 0.1)
    system_instruction = st.text_area("System Override (Persona)", placeholder="Ex: You are a senior Python engineer...", height=100)
    
    # 대화 초기화 버튼
    if st.button("Flush Memory (Clear Chat)", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- 메인 채팅 인터페이스 ---
st.title("Gemini Ultimate Commander")

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("Enter command..."):
    # 사용자 메시지 표시 및 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # API 키 확인
    if not st.session_state.api_key:
        st.error("⚠️ API Key가 설정되지 않았습니다. 사이드바에서 키를 입력해주세요.")
        st.stop()

    # 모델 응답 요청
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner(f"Accessing {selected_model_id}..."):
            try:
                # API 엔드포인트
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                
                # 히스토리 변환 (최근 15개)
                contents = []
                for msg in st.session_state.messages[-15:-1]: # 현재 메시지 제외한 히스토리
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": msg["content"]}]})
                
                # 현재 메시지 추가
                contents.append({"role": "user", "parts": [{"text": prompt}]})

                # 페이로드 구성
                payload = {
                    "contents": contents,
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

                # 시스템 프롬프트 추가 (지원 모델만)
                if system_instruction.strip():
                    payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

                # 요청 전송
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                
                # 응답 처리
                if response.status_code == 200:
                    data = response.json()
                    if "candidates" in data and data["candidates"]:
                        full_response = data["candidates"][0]["content"]["parts"][0]["text"]
                        message_placeholder.markdown(full_response)
                        
                        # 응답 저장
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    else:
                        st.error("모델이 응답하지 않았습니다. (Safety Filter 또는 빈 응답)")
                        st.json(data)
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"System Error: {str(e)}")


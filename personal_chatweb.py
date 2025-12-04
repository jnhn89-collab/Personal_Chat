import streamlit as st
import requests
import json

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Gemini Ultimate Commander",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 커스텀 스타일 (다크모드 강제 및 터미널 느낌) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #c9d1d9;
    }
    .stTextInput > div > div > input {
        background-color: #0d1117;
        color: #58a6ff;
        border-color: #30363d;
    }
    .stSelectbox > div > div > div {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .stChatMessage {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
    }
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #010409;
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


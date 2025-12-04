import streamlit as st
import requests
import json
import uuid
import os
import base64
import html

# ==========================================
# [사용자 설정] 
# ==========================================
ACCESS_PASSWORD = "153692525" 
HISTORY_FILE = "system_log.dat" # 보안을 위해 확장자 위장

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="System Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# --- 2. 암호화/복호화 (XOR) ---
def encrypt_data(data_str, key):
    enc = []
    for i, c in enumerate(data_str):
        key_c = key[i % len(key)]
        enc_c = chr(ord(c) ^ ord(key_c))
        enc.append(enc_c)
    return base64.b64encode("".join(enc).encode()).decode()

def decrypt_data(enc_str, key):
    try:
        dec = []
        enc_str = base64.b64decode(enc_str).decode()
        for i, c in enumerate(enc_str):
            key_c = key[i % len(key)]
            dec_c = chr(ord(c) ^ ord(key_c))
            dec.append(dec_c)
        return "".join(dec)
    except:
        return ""

# --- 3. 스타일링 & 자바스크립트 (핵심 수정됨) ---
st.markdown("""
<script>
    function copyContent(elementId, btnId, mode) {
        // 1. 숨겨진 div에서 원본 텍스트 가져오기
        const hiddenElement = document.getElementById(elementId);
        if (!hiddenElement) {
            console.error('Text element not found');
            return;
        }
        
        // textContent는 HTML 태그가 해석되지 않은 원본 텍스트를 가져옴
        let textToCopy = hiddenElement.textContent;

        // 2. TXT 모드일 경우 마크다운 제거 (Regex)
        if (mode === 'txt') {
            textToCopy = textToCopy
                .replace(/^#+\s+/gm, '')           // Headers
                .replace(/\*\*(.*?)\*\*/g, '$1')   // Bold
                .replace(/__(.*?)__/g, '$1')       // Bold
                .replace(/\*(.*?)\*/g, '$1')       // Italic
                .replace(/_(.*?)_/g, '$1')         // Italic
                .replace(/`([^`]+)`/g, '$1')       // Inline Code
                .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // Links [text](url) -> text
                .replace(/```[\s\S]*?```/g, '[CODE BLOCK]') // Code blocks
                .replace(/>\s?/g, '');             // Blockquotes
        }

        // 3. 클립보드 복사
        navigator.clipboard.writeText(textToCopy).then(function() {
            const btn = document.getElementById(btnId);
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅';
            btn.style.color = 'green';
            setTimeout(() => { 
                btn.innerHTML = originalText; 
                btn.style.color = '#475569';
            }, 1500);
        }, function(err) {
            console.error('Async: Could not copy text: ', err);
        });
    }
</script>
<style>
    /* 전체 테마 */
    .stApp { background-color: #ffffff; color: #1e293b; }
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    
    /* 탭바 Sticky */
    .stTabs [data-baseweb="tab-list"] { 
        position: sticky; top: 2.5rem; z-index: 999; background-color: #ffffff;
        padding: 5px 0; border-bottom: 1px solid #f1f5f9;
    }
    .stTabs [data-baseweb="tab"] { height: 45px; }
    .stTabs [aria-selected="true"] { border-top: 2px solid #3b82f6; }

    /* 채팅 스타일 */
    [data-testid="stChatMessage"] { padding: 1rem; border-radius: 12px; margin-bottom: 12px; position: relative;}
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #eff6ff; border: 1px solid #dbeafe; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #e2e8f0; }

    /* 복사 버튼 컨테이너 */
    .copy-btn-wrapper {
        display: flex;
        justify-content: flex-end;
        gap: 5px;
        margin-bottom: 5px;
        opacity: 0.2; /* 평소엔 흐릿 */
        transition: opacity 0.2s;
    }
    .copy-btn-wrapper:hover { opacity: 1; }

    .custom-copy-btn {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        font-size: 10px;
        color: #475569;
        cursor: pointer;
        padding: 2px 6px;
        font-family: monospace;
    }
    .custom-copy-btn:hover { background-color: #e2e8f0; color: #0f172a; }

    .block-container { padding-top: 1.5rem; padding-bottom: 5rem; }
    .source-box { font-size: 0.75em; color: #64748b; background-color: #f8fafc; padding: 8px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# --- 4. 로직 ---
def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.info("🔒 Authorized Access Only")
            pwd = st.text_input("Access Code", type="password")
            if st.button("Verify", use_container_width=True):
                if pwd == ACCESS_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Access Denied")
        st.stop() 

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.loads(decrypt_data(f.read(), ACCESS_PASSWORD))
        except: pass
    return [{"id": str(uuid.uuid4()), "title": "Session 1", "messages": []}]

def save_history():
    data = encrypt_data(json.dumps(st.session_state.sessions, ensure_ascii=False), ACCESS_PASSWORD)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: f.write(data)

check_password()
if "sessions" not in st.session_state: st.session_state.sessions = load_history()
if "api_key" not in st.session_state: st.session_state.api_key = ""

# --- 5. 모델 리스트 ---
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

# --- 6. UI ---
with st.sidebar:
    st.header("Config")
    with st.expander("API Token", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("Key", value=st.session_state.api_key, type="password")

    st.subheader("Engine")
    cat = st.selectbox("Type", options=MODEL_OPTIONS.keys(), label_visibility="collapsed")
    model_map = MODEL_OPTIONS[cat]
    selected_model_name = st.selectbox("Ver", options=model_map.values(), label_visibility="collapsed")
    selected_model_id = [k for k, v in model_map.items() if v == selected_model_name][0]

    st.markdown("---")
    use_google_search = st.toggle("Net Search", value=False)
    st.markdown("---")
    
    with st.expander("Adv. Params"):
        temperature = st.slider("Entropy", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("SysPrompt", height=100)

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("➕ New", use_container_width=True):
        if len(st.session_state.sessions) < 10:
            st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Session {len(st.session_state.sessions)+1}", "messages": []})
            save_history()
            st.rerun()
    if c2.button("🗑️ Clear", use_container_width=True):
        if len(st.session_state.sessions) > 1: st.session_state.sessions.pop()
        else: 
            st.session_state.sessions[0]["messages"] = []
            st.session_state.sessions[0]["title"] = "Session 1"
        save_history()
        st.rerun()
    st.markdown("---")
    if st.button("🔒 Lock", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

c1, c2 = st.columns([1, 1])
with c1: st.markdown("### 📊 System Dashboard")
with c2: st.markdown(f"<div style='text-align:right; color:#94a3b8; font-size:0.8em; padding-top:10px;'>Status: Online | {selected_model_name}</div>", unsafe_allow_html=True)

tabs = st.tabs([s["title"] for s in st.session_state.sessions])

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        
        with st.expander("Session Name", expanded=False):
            new_title = st.text_input("Name", value=session["title"], key=f"title_{session['id']}")
            if new_title != session["title"]:
                session["title"] = new_title
                save_history()
                st.rerun()

        chat_container = st.container(height=550, border=False)
        
        with chat_container:
            if not session["messages"]: st.caption("System Ready.")
            
            for idx, msg in enumerate(session["messages"]):
                avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
                with st.chat_message(msg["role"], avatar=avatar):
                    
                    # AI 메시지일 경우에만 복사 기능 활성화
                    if msg["role"] == "assistant":
                        # 1. 고유 ID 생성
                        content_id = f"content_{session['id']}_{idx}"
                        btn_md_id = f"btn_md_{session['id']}_{idx}"
                        btn_txt_id = f"btn_txt_{session['id']}_{idx}"
                        
                        # 2. 숨겨진 Div에 원본 텍스트 저장 (HTML Escape 처리)
                        # display: none으로 화면엔 안 보이지만 DOM에는 존재함
                        safe_content = html.escape(msg["content"])
                        
                        html_code = f"""
                        <div class="copy-btn-wrapper">
                            <button id="{btn_md_id}" class="custom-copy-btn" onclick="copyContent('{content_id}', '{btn_md_id}', 'md')">📋 MD</button>
                            <button id="{btn_txt_id}" class="custom-copy-btn" onclick="copyContent('{content_id}', '{btn_txt_id}', 'txt')">📝 TXT</button>
                        </div>
                        <div id="{content_id}" style="display:none;">{safe_content}</div>
                        """
                        st.markdown(html_code, unsafe_allow_html=True)
                        st.markdown(msg["content"])
                    else:
                        st.markdown(msg["content"])

                    if "sources" in msg and msg["sources"]:
                        source_html = "<div class='source-box'>📚 <b>Ref:</b><br>"
                        for src in msg["sources"]:
                            source_html += f"• <a href='{src.get('uri','#')}' target='_blank'>{src.get('title','Link')}</a><br>"
                        source_html += "</div>"
                        st.markdown(source_html, unsafe_allow_html=True)

        if prompt := st.chat_input("Command Input...", key=f"input_{session['id']}"):
            if not st.session_state.api_key: st.stop()

            session["messages"].append({"role": "user", "content": prompt})
            save_history()
            
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"): st.markdown(prompt)

            with chat_container:
                with st.chat_message("assistant", avatar="🤖"):
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

                                # 실시간 렌더링 시에도 버튼 로직 적용
                                unique_id = str(uuid.uuid4())
                                content_id = f"temp_content_{unique_id}"
                                btn_md_id = f"temp_btn_md_{unique_id}"
                                btn_txt_id = f"temp_btn_txt_{unique_id}"
                                safe_content = html.escape(bot_text)

                                html_code = f"""
                                <div class="copy-btn-wrapper">
                                    <button id="{btn_md_id}" class="custom-copy-btn" onclick="copyContent('{content_id}', '{btn_md_id}', 'md')">📋 MD</button>
                                    <button id="{btn_txt_id}" class="custom-copy-btn" onclick="copyContent('{content_id}', '{btn_txt_id}', 'txt')">📝 TXT</button>
                                </div>
                                <div id="{content_id}" style="display:none;">{safe_content}</div>
                                """
                                ph.markdown(html_code + bot_text, unsafe_allow_html=True)
                                
                                if sources:
                                    html_src = "<div class='source-box'>📚 <b>Ref:</b><br>"
                                    for s in sources: html_src += f"• <a href='{s.get('uri','#')}' target='_blank'>{s.get('title','Link')}</a><br>"
                                    html_src += "</div>"
                                    st.markdown(html_src, unsafe_allow_html=True)

                                session["messages"].append({"role": "assistant", "content": bot_text, "sources": sources})
                                save_history()
                            else: ph.warning("No Data")
                        else: ph.error(f"Err {res.status_code}")
                    except Exception as e: ph.error(str(e))


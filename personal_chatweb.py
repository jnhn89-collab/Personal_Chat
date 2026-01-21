import streamlit as st
import requests
import json
import uuid
import os
import base64
import re

# ==========================================
# [사용자 설정] 
# ==========================================
ACCESS_PASSWORD = "1111" 
HISTORY_FILE = "system_log.dat"

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="System Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# --- 2. 유틸리티 함수 ---
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

def fetch_available_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            models_data = res.json().get("models", [])
            filtered_models = [m for m in models_data if "generateContent" in m.get("supportedGenerationMethods", [])]
            
            categories = {
                "Gemini 2.0 Series": [],
                "Gemini 1.5 Series": [],
                "Experimental/Special": [],
                "Legacy/Other": []
            }

            for m in filtered_models:
                m_id = m["name"].split("/")[-1]
                m_disp = m.get("displayName", m_id)
                
                if "2.0" in m_id: categories["Gemini 2.0 Series"].append((m_id, m_disp))
                elif "1.5" in m_id: categories["Gemini 1.5 Series"].append((m_id, m_disp))
                elif "exp" in m_id or "preview" in m_id: categories["Experimental/Special"].append((m_id, m_disp))
                else: categories["Legacy/Other"].append((m_id, m_disp))
            
            return {k: v for k, v in categories.items() if v}
        return None
    except:
        return None

# --- 3. 핵심: Base64 클립보드 복사 스크립트 (안정화 버전) ---
st.markdown("""
<script>
    async function copyBase64(b64text, btnId, mode) {
        try {
            // Base64 디코딩
            const binaryString = atob(b64text);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            const decoder = new TextDecoder('utf-8');
            let text = decoder.decode(bytes);

            // 텍스트 모드일 경우 마크다운 제거
            if (mode === 'txt') {
                text = text
                    .replace(/^#+\s+/gm, '')           
                    .replace(/\*\*(.*?)\*\*/g, '$1')   
                    .replace(/__(.*?)__/g, '$1')       
                    .replace(/\*(.*?)\*/g, '$1')       
                    .replace(/`([^`]+)`/g, '$1')       
                    .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') 
                    .replace(/```[\s\S]*?```/g, '')    
                    .replace(/>\s?/g, '');             
            }

            // 클립보드 복사
            await navigator.clipboard.writeText(text);

            // 버튼 UI 피드백
            const btn = document.getElementById(btnId) || window.parent.document.getElementById(btnId);
            if(btn){
                const originalHtml = btn.innerHTML;
                btn.innerHTML = '✅ Copied!';
                btn.style.color = '#10b981';
                setTimeout(() => { 
                    btn.innerHTML = originalHtml; 
                    btn.style.color = '#475569';
                }, 2000);
            }
        } catch (err) {
            console.error('Copy failed:', err);
        }
    }
</script>
<style>
    .stApp { background-color: #ffffff; color: #1e293b; }
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    .stTabs [data-baseweb="tab-list"] { 
        position: sticky; top: 2.5rem; z-index: 999; background-color: #ffffff;
        padding: 5px 0; border-bottom: 1px solid #f1f5f9;
    }
    [data-testid="stChatMessage"] { padding: 1rem; border-radius: 12px; margin-bottom: 12px; position: relative;}
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #eff6ff; border: 1px solid #dbeafe; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #e2e8f0; }
    .copy-btn-wrapper { display: flex; justify-content: flex-end; gap: 5px; margin-bottom: 5px; opacity: 0.5; }
    .copy-btn-wrapper:hover { opacity: 1; }
    .custom-copy-btn { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 11px; color: #475569; cursor: pointer; padding: 3px 8px; }
    .source-box { font-size: 0.75em; color: #64748b; background-color: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 4. 세션 관리 및 보안 ---
def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
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
if "model_options" not in st.session_state: st.session_state.model_options = None

# --- 5. 사이드바 UI ---
with st.sidebar:
    st.header("Config")
    st.session_state.api_key = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password")
    
    if st.button("🔄 Refresh Model List", use_container_width=True):
        if st.session_state.api_key:
            st.session_state.model_options = fetch_available_models(st.session_state.api_key)
            st.success("Updated!")
        else: st.warning("Enter API Key")

    if st.session_state.model_options:
        cat = st.selectbox("Category", options=st.session_state.model_options.keys())
        model_list = st.session_state.model_options[cat]
        selected_model_display = st.selectbox("Version", options=[m[1] for m in model_list])
        selected_model_id = [m[0] for m in model_list if m[1] == selected_model_display][0]
    else:
        selected_model_id = "gemini-1.5-flash"

    st.markdown("---")
    use_google_search = st.toggle("Net Search (Google)", value=False)
    
    with st.expander("Parameters"):
        chat_window_height = st.slider("Height", 400, 1600, 800)
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("System Instruction", height=100)

    st.divider()
    if st.button("➕ New Session", use_container_width=True):
        st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Session {len(st.session_state.sessions)+1}", "messages": []})
        save_history(); st.rerun()
    
    if st.button("🔒 Lock Dashboard", use_container_width=True):
        st.session_state.authenticated = False; st.rerun()

# --- 6. 메인 UI ---
st.markdown(f"### 📊 Dashboard <small style='color:#94a3b8;'>Model: {selected_model_id}</small>", unsafe_allow_html=True)

active_tab_names = [s["title"] for s in st.session_state.sessions]
tabs = st.tabs(active_tab_names)

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        
        # 채팅창 영역
        chat_container = st.container(height=chat_window_height, border=False)
        with chat_container:
            for idx, msg in enumerate(session["messages"]):
                with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
                    if msg["role"] == "assistant":
                        # 안전한 Base64 인코딩 (JS 전달용)
                        b64_content = base64.b64encode(msg["content"].encode('utf-8')).decode('utf-8')
                        btn_md_id, btn_txt_id = f"btn_m_{i}_{idx}", f"btn_t_{i}_{idx}"
                        st.markdown(f"""<div class="copy-btn-wrapper">
                            <button id="{btn_md_id}" class="custom-copy-btn" onclick="copyBase64('{b64_content}', '{btn_md_id}', 'md')">📋 MD</button>
                            <button id="{btn_txt_id}" class="custom-copy-btn" onclick="copyBase64('{b64_content}', '{btn_txt_id}', 'txt')">📝 TXT</button>
                        </div>""", unsafe_allow_html=True)
                    
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        src_html = "<div class='source-box'>📚 <b>Sources:</b><br>" + "".join([f"• <a href='{s['uri']}' target='_blank'>{s.get('title','Link')}</a><br>" for s in msg["sources"]]) + "</div>"
                        st.markdown(src_html, unsafe_allow_html=True)

        # 입력 영역
        if prompt := st.chat_input("Enter command...", key=f"input_{session['id']}"):
            if not st.session_state.api_key:
                st.error("API Key is required!")
            else:
                session["messages"].append({"role": "user", "content": prompt})
                
                # 어시스턴트 응답 생성
                with chat_container:
                    with st.chat_message("assistant", avatar="🤖"):
                        ph = st.empty()
                        ph.markdown("Thinking...")
                        
                        try:
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                            
                            contents = []
                            for m in session["messages"][-15:]:
                                contents.append({"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]})
                            
                            payload = {
                                "contents": contents,
                                "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
                            }
                            if system_prompt.strip():
                                payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
                            if use_google_search:
                                payload["tools"] = [{"google_search": {}}]

                            res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                            
                            # [핵심] 응답 검증: HTML이 오면 SyntaxError 발생의 원인이 됨
                            if res.status_code == 200 and "application/json" in res.headers.get("Content-Type", ""):
                                result = res.json()
                                if "candidates" in result:
                                    cand = result["candidates"][0]
                                    bot_text = cand["content"]["parts"][0]["text"]
                                    
                                    # 출처 처리
                                    sources = []
                                    g_meta = cand.get("groundingMetadata", {})
                                    if "groundingChunks" in g_meta:
                                        for chunk in g_meta["groundingChunks"]:
                                            if "web" in chunk: sources.append(chunk["web"])
                                    
                                    ph.markdown(bot_text)
                                    session["messages"].append({"role": "assistant", "content": bot_text, "sources": sources})
                                    save_history()
                                    st.rerun()
                                else:
                                    ph.error("No candidates found in response.")
                            else:
                                error_msg = res.json().get("error", {}).get("message", "Unknown API error") if "json" in res.headers.get("Content-Type", "") else "Server returned Non-JSON response (HTML)."
                                ph.error(f"Error {res.status_code}: {error_msg}")
                        
                        except Exception as e:
                            ph.error(f"System Error: {str(e)}")

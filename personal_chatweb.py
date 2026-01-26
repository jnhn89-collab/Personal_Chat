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

# --- 2. 유틸리티 함수 (암호화 및 모델 관리) ---
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
    """API로부터 사용 가능한 모델 목록을 가져와 카테고리화합니다."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            models_data = res.json().get("models", [])
            # generateContent를 지원하는 모델만 필터링
            filtered_models = [m for m in models_data if "generateContent" in m.get("supportedGenerationMethods", [])]
            
            categories = {
                "Gemini 3.0 Series": [],
                "Gemini 2.5 Series": [],
                "Gemini 2.0 Series": [],
                "Experimental/Special": [],
                "Legacy/Other": []
            }

            for m in filtered_models:
                m_id = m["name"].split("/")[-1]
                m_disp = m.get("displayName", m_id)
                
                if "3.0" in m_id: categories["Gemini 3.0 Series"].append((m_id, m_disp))
                elif "2.5" in m_id: categories["Gemini 2.5 Series"].append((m_id, m_disp))
                elif "2.0" in m_id: categories["Gemini 2.0 Series"].append((m_id, m_disp))
                elif "exp" in m_id or "preview" in m_id: categories["Experimental/Special"].append((m_id, m_disp))
                else: categories["Legacy/Other"].append((m_id, m_disp))
            
            # 빈 카테고리 제거
            return {k: v for k, v in categories.items() if v}
        else:
            st.error(f"Failed to fetch models: {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Model fetch error: {str(e)}")
        return None
        
# --- 3. 핵심: Base64 클립보드 복사 스크립트 ---
st.markdown("""
<script>
    // 함수가 중복 정의되는 것을 방지
    if (typeof window.copyBase64 === 'undefined') {
        window.copyBase64 = async function(b64text, btnId, mode) {
            try {
                const binaryString = atob(b64text);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }
                const decoder = new TextDecoder('utf-8');
                let text = decoder.decode(bytes);

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

                await navigator.clipboard.writeText(text);

                // Streamlit의 iframe 구조 때문에 window.parent.document를 확인해야 함
                const btn = window.parent.document.getElementById(btnId) || document.getElementById(btnId);
                if(btn){
                    const originalHtml = btn.innerHTML;
                    btn.innerHTML = '✅ Copied!';
                    btn.style.color = '#10b981';
                    btn.style.borderColor = '#10b981';
                    setTimeout(() => { 
                        btn.innerHTML = originalHtml; 
                        btn.style.color = '#475569';
                        btn.style.borderColor = '#cbd5e1';
                    }, 2000);
                }
            } catch (err) {
                console.error('Copy failed:', err);
            }
        };
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
    .copy-btn-wrapper { display: flex; justify-content: flex-end; gap: 5px; margin-bottom: 5px; opacity: 0.4; transition: opacity 0.2s; }
    .copy-btn-wrapper:hover { opacity: 1; }
    .custom-copy-btn { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 11px; color: #475569; cursor: pointer; padding: 3px 8px; font-family: monospace; font-weight: bold; }
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
    with st.expander("API Token", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("Key", value=st.session_state.api_key, type="password")
    
    # 모델 갱신 버튼
    if st.button("🔄 Refresh Model List", use_container_width=True):
        if st.session_state.api_key:
            st.session_state.model_options = fetch_available_models(st.session_state.api_key)
            st.success("Models updated!")
        else:
            st.warning("Enter API Key first.")

    st.subheader("Engine")
    if st.session_state.model_options:
        cat = st.selectbox("Type", options=st.session_state.model_options.keys())
        model_list = st.session_state.model_options[cat]
        selected_model_display = st.selectbox("Ver", options=[m[1] for m in model_list])
        selected_model_id = [m[0] for m in model_list if m[1] == selected_model_display][0]
    else:
        st.caption("Click Refresh to load models.")
        selected_model_id = "gemini-1.5-flash" # Default fallback

    st.markdown("---")
    use_google_search = st.toggle("Net Search (Google Search)", value=False)
    st.markdown("---")
    
    with st.expander("Adv. Params", expanded=True):
        chat_window_height = st.slider("Chat Window Height", 400, 2000, 850, step=50)
        temperature = st.slider("Entropy", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("SysPrompt", height=100)

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("➕ New", use_container_width=True):
        st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Session {len(st.session_state.sessions)+1}", "messages": []})
        save_history(); st.rerun()
    if c2.button("🗑️ Clear", use_container_width=True):
        if len(st.session_state.sessions) > 1: st.session_state.sessions.pop()
        else: st.session_state.sessions[0].update({"messages": [], "title": "Session 1"})
        save_history(); st.rerun()
    
    if st.button("🔒 Lock", use_container_width=True):
        st.session_state.authenticated = False; st.rerun()

# --- 6. 메인 UI ---
st.markdown(f"### 📊 System Dashboard <small style='float:right; color:#94a3b8;'>Model: {selected_model_id}</small>", unsafe_allow_html=True)

tabs = st.tabs([s["title"] for s in st.session_state.sessions])

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        with st.expander("Session Name", expanded=False):
            new_title = st.text_input("Name", value=session["title"], key=f"title_{session['id']}")
            if new_title != session["title"]:
                session["title"] = new_title; save_history(); st.rerun()

        chat_container = st.container(height=chat_window_height, border=False)
        
        with chat_container:
            for idx, msg in enumerate(session["messages"]):
                avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
                with st.chat_message(msg["role"], avatar=avatar):
                    if msg["role"] == "assistant":
                        b64_content = base64.b64encode(msg["content"].encode('utf-8')).decode('utf-8')
                        btn_md_id, btn_txt_id = f"b_m_{idx}_{i}", f"b_t_{idx}_{i}"
                        st.markdown(f"""<div class="copy-btn-wrapper">
                            <button id="{btn_md_id}" class="custom-copy-btn" onclick="copyBase64('{b64_content}', '{btn_md_id}', 'md')">📋 MD</button>
                            <button id="{btn_txt_id}" class="custom-copy-btn" onclick="copyBase64('{b64_content}', '{btn_txt_id}', 'txt')">📝 TXT</button>
                        </div>""", unsafe_allow_html=True)
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        src_html = "<div class='source-box'>📚 <b>Ref:</b><br>" + "".join([f"• <a href='{s['uri']}' target='_blank'>{s.get('title','Link')}</a><br>" for s in msg["sources"]]) + "</div>"
                        st.markdown(src_html, unsafe_allow_html=True)

        if prompt := st.chat_input("Command Input...", key=f"input_{session['id']}"):
            if not st.session_state.api_key: st.error("API Key missing!"); st.stop()
            session["messages"].append({"role": "user", "content": prompt})
            save_history()
            st.rerun()

# --- 7. 대화 로직 ---
if st.session_state.sessions and st.session_state.sessions[tabs.index(tab) if 'tab' in locals() else 0]["messages"] and st.session_state.sessions[tabs.index(tab) if 'tab' in locals() else 0]["messages"][-1]["role"] == "user":
    current_session = st.session_state.sessions[tabs.index(tab)]
    user_msg = current_session["messages"][-1]["content"]
    
    with chat_container:
        with st.chat_message("assistant", avatar="🤖"):
            ph = st.empty()
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                
                # 페이로드 구성
                contents = []
                for m in current_session["messages"][-15:]:
                    contents.append({"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]})
                
                payload = {
                    "contents": contents,
                    "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
                }

                if system_prompt.strip():
                    payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

                # Net Search (Google Search Retrieval) 에러 방지 대책
                # 400 에러의 원인은 주로 잘못된 'tools' 구조나 지원하지 않는 모델에서의 호출입니다.
                if use_google_search:
                    # Google Search Retrieval의 올바른 v1beta 구조
                    payload["tools"] = [{"google_search": {}}]

                res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                
                if res.status_code == 200:
                    result = res.json()
                    if "candidates" in result:
                        cand = result["candidates"][0]
                        bot_text = cand["content"]["parts"][0]["text"]
                        
                        # 출처(Grounding) 처리
                        sources = []
                        g_meta = cand.get("groundingMetadata", {})
                        if "groundingChunks" in g_meta:
                            for chunk in g_meta["groundingChunks"]:
                                if "web" in chunk: sources.append(chunk["web"])
                        
                        ph.markdown(bot_text)
                        current_session["messages"].append({"role": "assistant", "content": bot_text, "sources": sources})
                        save_history()
                        st.rerun()
                else:
                    # 상세 에러 메시지 출력으로 원인 파악 용이하게 개선
                    error_details = res.json().get("error", {}).get("message", "Unknown Error")
                    ph.error(f"Error {res.status_code}: {error_details}")
            except Exception as e:
                ph.error(f"Exception: {str(e)}")

import streamlit as st
import requests
import json
import uuid
import os
import base64

# ==========================================
# [사용자 설정] 
# ==========================================
ACCESS_PASSWORD = "1111" 
HISTORY_FILE = "system_log.dat"

# --- 1. 페이지 기본 설정 (가장 먼저 호출) ---
st.set_page_config(page_title="System Dashboard", page_icon="📊", layout="wide")

# --- 2. 보안 기능 ---
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
    except: return ""

# --- 3. 로그인 체크 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.write("### 🔒 System Login")
        pwd = st.text_input("Access Code", type="password")
        if st.button("Login", use_container_width=True):
            if pwd == ACCESS_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Invalid Code")
    st.stop()

# --- 4. 데이터 관리 ---
if "sessions" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                dec = decrypt_data(f.read(), ACCESS_PASSWORD)
                st.session_state.sessions = json.loads(dec)
        except:
            st.session_state.sessions = [{"id": str(uuid.uuid4()), "title": "Session 1", "messages": []}]
    else:
        st.session_state.sessions = [{"id": str(uuid.uuid4()), "title": "Session 1", "messages": []}]

def save_history():
    data = encrypt_data(json.dumps(st.session_state.sessions, ensure_ascii=False), ACCESS_PASSWORD)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: f.write(data)

# --- 5. 스타일 (JS 제거) ---
st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    [data-testid="stChatMessage"] { border-radius: 10px; border: 1px solid #f1f5f9; }
    .source-box { font-size: 0.8em; color: #64748b; background: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 6. 사이드바 ---
with st.sidebar:
    st.title("📊 Config")
    api_key = st.text_input("API Key", type="password")
    model_id = st.selectbox("Model", ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"])
    use_search = st.toggle("Google Search", value=False)
    
    st.divider()
    if st.button("➕ New Session", use_container_width=True):
        st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Session {len(st.session_state.sessions)+1}", "messages": []})
        save_history(); st.rerun()
    if st.button("🗑️ Reset All", use_container_width=True):
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
        st.session_state.clear(); st.rerun()

# --- 7. 메인 화면 ---
tab_list = [s["title"] for s in st.session_state.sessions]
tabs = st.tabs(tab_list)

for i, tab in enumerate(tabs):
    with tab:
        session = st.session_state.sessions[i]
        chat_box = st.container(height=650)
        
        with chat_box:
            for msg in session["messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    # 복사를 위해 st.code 활용 (JS 오류 원천 차단)
                    if msg["role"] == "assistant":
                        with st.expander("Copy Content"):
                            st.code(msg["content"], language="markdown")
                    if msg.get("sources"):
                        st.markdown("<div class='source-box'><b>Ref:</b><br>" + 
                                    "".join([f"• <a href='{s['uri']}'>{s.get('title','Link')}</a><br>" for s in msg["sources"]]) + "</div>", unsafe_allow_html=True)

        if prompt := st.chat_input("Input...", key=f"input_{session['id']}"):
            if not api_key: st.error("Key missing"); st.stop()
            
            session["messages"].append({"role": "user", "content": prompt})
            save_history()
            
            with chat_box:
                with st.chat_message("assistant"):
                    ph = st.empty()
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
                        payload = {
                            "contents": [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in session["messages"][-10:]]
                        }
                        if use_search: payload["tools"] = [{"google_search": {}}]
                        
                        res = requests.post(url, json=payload, timeout=30)
                        if res.status_code == 200:
                            data = res.json()
                            ans = data['candidates'][0]['content']['parts'][0]['text']
                            ph.markdown(ans)
                            
                            sources = []
                            g_meta = data['candidates'][0].get('groundingMetadata', {})
                            if "groundingChunks" in g_meta:
                                for chunk in g_meta["groundingChunks"]:
                                    if "web" in chunk: sources.append(chunk["web"])
                                    
                            session["messages"].append({"role": "assistant", "content": ans, "sources": sources})
                            save_history()
                            st.rerun()
                        else: st.error(f"Error: {res.status_code}")
                    except Exception as e: st.error(str(e))

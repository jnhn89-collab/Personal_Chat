import streamlit as st
import requests
import json
import uuid
import os
import base64
import asyncio
import threading
import time
from datetime import datetime

# ==========================================
# [사용자 설정] 
# ==========================================
ACCESS_PASSWORD = "1111"  # TODO: st.secrets 또는 환경변수로 이동 권장
HISTORY_FILE = "system_log.dat"
TELEGRAM_HISTORY_FILE = "telegram_log.dat"

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
        enc.append(chr(ord(c) ^ ord(key_c)))
    return base64.b64encode("".join(enc).encode()).decode()

def decrypt_data(enc_str, key):
    try:
        dec = []
        enc_str = base64.b64decode(enc_str).decode()
        for i, c in enumerate(enc_str):
            key_c = key[i % len(key)]
            dec.append(chr(ord(c) ^ ord(key_c)))
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
                "Gemini 3.0 Series": [], "Gemini 2.5 Series": [],
                "Gemini 2.0 Series": [], "Experimental/Special": [], "Legacy/Other": []
            }
            for m in filtered_models:
                m_id = m["name"].split("/")[-1]
                m_disp = m.get("displayName", m_id)
                if "3.0" in m_id: categories["Gemini 3.0 Series"].append((m_id, m_disp))
                elif "2.5" in m_id: categories["Gemini 2.5 Series"].append((m_id, m_disp))
                elif "2.0" in m_id: categories["Gemini 2.0 Series"].append((m_id, m_disp))
                elif "exp" in m_id or "preview" in m_id: categories["Experimental/Special"].append((m_id, m_disp))
                else: categories["Legacy/Other"].append((m_id, m_disp))
            return {k: v for k, v in categories.items() if v}
        return None
    except:
        return None

# --- Telegram Async 유틸리티 ---
def _run_async(coro):
    result = [None]
    exception = [None]
    def runner():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result[0] = loop.run_until_complete(coro)
            loop.close()
        except Exception as e:
            exception[0] = e
    t = threading.Thread(target=runner)
    t.start()
    t.join(timeout=30)
    if exception[0]:
        raise exception[0]
    return result[0]

def _get_session_name(phone):
    return f"session_{phone.replace('+','').replace(' ','')}"

def tg_authenticate(api_id, api_hash, phone):
    try:
        from telethon import TelegramClient
        async def _auth():
            client = TelegramClient(_get_session_name(phone), int(api_id), api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                sent = await client.send_code_request(phone)
                await client.disconnect()
                return ("CODE_NEEDED", sent.phone_code_hash)
            await client.disconnect()
            return ("AUTHORIZED", None)
        return _run_async(_auth())
    except Exception as e:
        return (f"ERROR: {str(e)}", None)

def tg_verify_code(api_id, api_hash, phone, code, phone_code_hash):
    try:
        from telethon import TelegramClient
        async def _verify():
            client = TelegramClient(_get_session_name(phone), int(api_id), api_hash)
            await client.connect()
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            authorized = await client.is_user_authorized()
            await client.disconnect()
            return "AUTHORIZED" if authorized else "FAILED"
        return _run_async(_verify())
    except Exception as e:
        return f"ERROR: {str(e)}"

def tg_send_via_user_api(api_id, api_hash, phone, bot_username, message):
    try:
        from telethon import TelegramClient
        async def _send():
            client = TelegramClient(_get_session_name(phone), int(api_id), api_hash)
            await client.connect()
            await client.send_message(bot_username, message)
            await client.disconnect()
            return True
        return _run_async(_send())
    except Exception as e:
        return str(e)

def tg_get_bot_replies(api_id, api_hash, phone, bot_username, limit=50):
    try:
        from telethon import TelegramClient
        async def _get():
            client = TelegramClient(_get_session_name(phone), int(api_id), api_hash)
            await client.connect()
            messages = []
            async for msg in client.iter_messages(bot_username, limit=limit):
                messages.append({
                    "id": msg.id, "text": msg.text or "",
                    "from_me": msg.out,
                    "date": msg.date.strftime("%H:%M") if msg.date else "",
                    "date_full": msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else ""
                })
            await client.disconnect()
            messages.reverse()
            return messages
        return _run_async(_get())
    except Exception as e:
        return str(e)

def tg_fetch_messages():
    """공통: Telegram 메시지 갱신"""
    result = tg_get_bot_replies(
        st.session_state.tg_api_id, st.session_state.tg_api_hash,
        st.session_state.tg_phone, st.session_state.tg_bot_username, limit=100
    )
    if isinstance(result, list):
        st.session_state.tg_messages = result
        save_tg_history()
        return True
    return False

# --- 3. 전역 CSS + JS ---
st.markdown("""
<style>
    /* 전체 */
    .stApp { background-color: #f0f2f5; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e5e7eb; }
    .block-container { padding-top: 1rem; padding-bottom: 0; }
    header[data-testid="stHeader"] { background: rgba(255,255,255,0.97); backdrop-filter: blur(10px); border-bottom: 1px solid #f3f4f6; }
    
    /* 탭 */
    .stTabs [data-baseweb="tab-list"] { 
        position: sticky; top: 0; z-index: 999; 
        background: #ffffff; padding: 6px 0; border-bottom: 2px solid #e5e7eb;
    }
    .stTabs [data-baseweb="tab"] { padding: 8px 20px; font-weight: 600; font-size: 13px; }
    
    /* Gemini 메시지 — ChatGPT 스타일 */
    [data-testid="stChatMessage"] { 
        padding: 16px 20px; border-radius: 0; margin-bottom: 0;
        border-bottom: 1px solid #f3f4f6;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) { background: #ffffff; border: none; border-bottom: 1px solid #f3f4f6; }
    div[data-testid="stChatMessage"]:nth-child(even) { background: #f7f7f8; border: none; border-bottom: 1px solid #f3f4f6; }

    /* 복사 버튼 */
    .copy-btn-wrapper { display: flex; justify-content: flex-end; gap: 5px; margin-bottom: 4px; opacity: 0; transition: opacity 0.2s; }
    [data-testid="stChatMessage"]:hover .copy-btn-wrapper { opacity: 1; }
    .custom-copy-btn { 
        background: #fff; border: 1px solid #d1d5db; border-radius: 6px; 
        font-size: 11px; color: #6b7280; cursor: pointer; padding: 4px 10px; 
        font-family: system-ui; transition: all 0.15s;
    }
    .custom-copy-btn:hover { background: #f3f4f6; color: #111827; }
    .source-box { font-size: 12px; color: #6b7280; background: #f9fafb; padding: 8px 12px; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 8px; }
    
    /* === Telegram 메신저 스타일 === */
    .tg-header {
        background: #ffffff; padding: 12px 20px; border-bottom: 1px solid #e5e7eb;
        display: flex; align-items: center; gap: 12px; border-radius: 12px 12px 0 0;
        margin-bottom: 4px;
    }
    .tg-avatar { 
        width: 42px; height: 42px; border-radius: 50%; 
        background: linear-gradient(135deg, #8b5cf6, #6366f1);
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 20px;
    }
    .tg-bot-info .name { font-size: 15px; font-weight: 600; color: #111827; }
    .tg-bot-info .status { font-size: 11px; color: #10b981; }
    
    .tg-chat-area { display: flex; flex-direction: column; gap: 3px; padding: 12px 16px; }
    .tg-row { display: flex; margin: 1px 0; }
    .tg-row.me { justify-content: flex-end; }
    .tg-row.bot { justify-content: flex-start; }
    .tg-bubble {
        max-width: 72%; padding: 9px 14px; border-radius: 18px;
        font-size: 14px; line-height: 1.55; word-wrap: break-word; white-space: pre-wrap;
    }
    .tg-bubble.me {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: #fff; border-bottom-right-radius: 4px;
    }
    .tg-bubble.bot {
        background: #ffffff; color: #1f2937;
        border: 1px solid #e5e7eb; border-bottom-left-radius: 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .tg-ts { font-size: 10px; color: #b0b0b0; margin-top: 1px; padding: 0 6px; }
    .tg-ts.me { text-align: right; }
    .tg-ts.bot { text-align: left; }
    
    /* 빈 상태 */
    .empty-state { text-align:center; padding:80px 20px; color:#9ca3af; }
    .empty-state .icon { font-size:48px; margin-bottom:12px; }
    .empty-state .title { font-size:17px; font-weight:600; color:#6b7280; }
    .empty-state .sub { font-size:13px; margin-top:6px; }
</style>

<script>
    // 복사 기능
    if (typeof window.copyBase64 === 'undefined') {
        window.copyBase64 = async function(b64text, btnId, mode) {
            try {
                const bytes = new Uint8Array(atob(b64text).split('').map(c=>c.charCodeAt(0)));
                let text = new TextDecoder('utf-8').decode(bytes);
                if (mode === 'txt') {
                    text = text.replace(/^#+\\s+/gm,'').replace(/\\*\\*(.*?)\\*\\*/g,'$1')
                        .replace(/__(.*?)__/g,'$1').replace(/\\*(.*?)\\*/g,'$1')
                        .replace(/`([^`]+)`/g,'$1').replace(/\\[([^\\]]+)\\]\\([^\\)]+\\)/g,'$1')
                        .replace(/```[\\s\\S]*?```/g,'').replace(/>\\s?/g,'');
                }
                await navigator.clipboard.writeText(text);
                const btn = window.parent.document.getElementById(btnId) || document.getElementById(btnId);
                if(btn){ 
                    const orig = btn.innerHTML;
                    btn.innerHTML='✅'; btn.style.color='#10b981';
                    setTimeout(()=>{ btn.innerHTML=orig; btn.style.color='#6b7280'; },1500);
                }
            } catch(e){ console.error(e); }
        };
    }
    
    // 자동 스크롤: 스크롤 가능 컨테이너를 맨 아래로
    (function(){
        function scrollAll(){
            const els = window.parent.document.querySelectorAll('[data-testid="stScrollableBlockContainer"]');
            els.forEach(el => { el.scrollTop = el.scrollHeight + 9999; });
        }
        // 여러 타이밍에 시도 (Streamlit 렌더링 대기)
        [100, 300, 600, 1200].forEach(ms => setTimeout(scrollAll, ms));
        
        // DOM 변경 감지 시에도 스크롤
        const obs = new MutationObserver(() => setTimeout(scrollAll, 80));
        setTimeout(() => {
            const t = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
            if(t) obs.observe(t, {childList:true, subtree:true});
        }, 500);
    })();
</script>
""", unsafe_allow_html=True)


# --- 4. 인증 ---
def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<div style='padding-top:80px;'></div>", unsafe_allow_html=True)
            st.markdown("### 🔒 System Dashboard")
            st.caption("Authorized Access Only")
            pwd = st.text_input("Access Code", type="password", label_visibility="collapsed", placeholder="Enter access code...")
            if st.button("Verify", use_container_width=True, type="primary"):
                if pwd == ACCESS_PASSWORD:
                    st.session_state.authenticated = True; st.rerun()
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

def load_tg_history():
    if os.path.exists(TELEGRAM_HISTORY_FILE):
        try:
            with open(TELEGRAM_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.loads(decrypt_data(f.read(), ACCESS_PASSWORD))
        except: pass
    return []

def save_tg_history():
    data = encrypt_data(json.dumps(st.session_state.tg_messages, ensure_ascii=False), ACCESS_PASSWORD)
    with open(TELEGRAM_HISTORY_FILE, "w", encoding="utf-8") as f: f.write(data)

check_password()

# --- 세션 초기화 ---
defaults = {
    "sessions": load_history(), "api_key": "", "model_options": None,
    "tg_api_id": "", "tg_api_hash": "", "tg_phone": "", "tg_bot_username": "",
    "tg_auth_status": "NOT_STARTED", "tg_code_hash": "",
    "tg_messages": load_tg_history(), "tg_pending_refresh": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# --- 5. 사이드바 ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    with st.expander("🤖 Gemini", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("API Key", value=st.session_state.api_key, type="password", label_visibility="collapsed", placeholder="Gemini API Key")
    
    if st.button("🔄 Refresh Models", use_container_width=True):
        if st.session_state.api_key:
            with st.spinner("Loading..."):
                st.session_state.model_options = fetch_available_models(st.session_state.api_key)
            if st.session_state.model_options: st.success("✅ Loaded")
            else: st.error("Failed")
        else: st.warning("Enter API Key")

    if st.session_state.model_options:
        cat = st.selectbox("Series", options=st.session_state.model_options.keys())
        model_list = st.session_state.model_options[cat]
        sel_disp = st.selectbox("Model", options=[m[1] for m in model_list])
        selected_model_id = [m[0] for m in model_list if m[1] == sel_disp][0]
    else:
        st.caption("Click Refresh to load")
        selected_model_id = "gemini-1.5-flash"

    use_google_search = st.toggle("🌐 Google Search", value=False)
    
    with st.expander("⚙️ Parameters"):
        chat_window_height = st.slider("Chat Height", 400, 2000, 850, step=50)
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("System Prompt", height=80, placeholder="Optional...")

    st.markdown("---")
    
    with st.expander("📱 Telegram", expanded=False):
        st.session_state.tg_api_id = st.text_input("API ID", value=st.session_state.tg_api_id, type="password", key="sb_tid")
        st.session_state.tg_api_hash = st.text_input("API Hash", value=st.session_state.tg_api_hash, type="password", key="sb_thash")
        st.session_state.tg_phone = st.text_input("Phone", value=st.session_state.tg_phone, placeholder="+821012345678", key="sb_tphone")
        st.session_state.tg_bot_username = st.text_input("Bot", value=st.session_state.tg_bot_username, placeholder="@my_bot", key="sb_tbot")
        
        if st.session_state.tg_auth_status == "AUTHORIZED":
            st.success("✅ Connected")
        elif st.session_state.tg_auth_status == "CODE_NEEDED":
            st.warning("⏳ Code needed")
        
        tg_ready = all([st.session_state.tg_api_id, st.session_state.tg_api_hash, 
                        st.session_state.tg_phone, st.session_state.tg_bot_username])
        
        if st.button("🔗 Connect", use_container_width=True, disabled=not tg_ready, key="sb_tconnect"):
            try:
                with st.spinner("Connecting..."):
                    result, code_hash = tg_authenticate(
                        st.session_state.tg_api_id, st.session_state.tg_api_hash, st.session_state.tg_phone
                    )
                    st.session_state.tg_auth_status = result
                    if code_hash: st.session_state.tg_code_hash = code_hash
                st.rerun()
            except Exception as e:
                st.error(f"❌ {str(e)}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("➕ New", use_container_width=True):
        st.session_state.sessions.append({"id": str(uuid.uuid4()), "title": f"Session {len(st.session_state.sessions)+1}", "messages": []})
        save_history(); st.rerun()
    if c2.button("🗑️ Del", use_container_width=True):
        if len(st.session_state.sessions) > 1: st.session_state.sessions.pop()
        else: st.session_state.sessions[0].update({"messages": [], "title": "Session 1"})
        save_history(); st.rerun()
    if st.button("🔒 Lock", use_container_width=True):
        st.session_state.authenticated = False; st.rerun()


# --- 6. 메인 ---
tab_names = [s["title"] for s in st.session_state.sessions] + ["📱 Telegram"]
tabs = st.tabs(tab_names)

# === Gemini 탭 ===
for i in range(len(st.session_state.sessions)):
    with tabs[i]:
        session = st.session_state.sessions[i]
        with st.expander("✏️ Rename", expanded=False):
            new_title = st.text_input("", value=session["title"], key=f"title_{session['id']}", label_visibility="collapsed")
            if new_title != session["title"]:
                session["title"] = new_title; save_history(); st.rerun()

        st.caption(f"🤖 {selected_model_id}")
        chat_container = st.container(height=chat_window_height, border=False)
        
        with chat_container:
            if not session["messages"]:
                st.markdown('<div class="empty-state"><div class="icon">🤖</div><div class="title">Start a conversation</div><div class="sub">Type a message below</div></div>', unsafe_allow_html=True)
            for idx, msg in enumerate(session["messages"]):
                with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"]=="user" else "🤖"):
                    if msg["role"] == "assistant":
                        b64 = base64.b64encode(msg["content"].encode('utf-8')).decode('utf-8')
                        bm, bt = f"c_m_{idx}_{i}", f"c_t_{idx}_{i}"
                        st.markdown(f'<div class="copy-btn-wrapper"><button id="{bm}" class="custom-copy-btn" onclick="copyBase64(\'{b64}\',\'{bm}\',\'md\')">📋 MD</button><button id="{bt}" class="custom-copy-btn" onclick="copyBase64(\'{b64}\',\'{bt}\',\'txt\')">📝 TXT</button></div>', unsafe_allow_html=True)
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        st.markdown("<div class='source-box'>📚 <b>Sources:</b><br>" + "".join([f"• <a href='{s['uri']}' target='_blank'>{s.get('title','Link')}</a><br>" for s in msg["sources"]]) + "</div>", unsafe_allow_html=True)

        if prompt := st.chat_input("Message...", key=f"input_{session['id']}"):
            if not st.session_state.api_key:
                st.error("⚠️ API Key required"); st.stop()
            session["messages"].append({"role": "user", "content": prompt})
            save_history()
            with chat_container:
                with st.chat_message("assistant", avatar="🤖"):
                    ph = st.empty()
                    ph.markdown("⏳ *Thinking...*")
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model_id}:generateContent?key={st.session_state.api_key}"
                        contents = [{"role": "user" if m["role"]=="user" else "model", "parts": [{"text": m["content"]}]} for m in session["messages"][-15:]]
                        payload = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192}}
                        if system_prompt.strip(): payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
                        if use_google_search: payload["tools"] = [{"google_search": {}}]
                        res = requests.post(url, headers={'Content-Type':'application/json'}, data=json.dumps(payload))
                        if res.status_code == 200:
                            result = res.json()
                            if "candidates" in result:
                                cand = result["candidates"][0]
                                bot_text = cand["content"]["parts"][0]["text"]
                                sources = []
                                g_meta = cand.get("groundingMetadata", {})
                                if "groundingChunks" in g_meta:
                                    for chunk in g_meta["groundingChunks"]:
                                        if "web" in chunk: sources.append(chunk["web"])
                                session["messages"].append({"role": "assistant", "content": bot_text, "sources": sources})
                                save_history(); st.rerun()
                            else: ph.error("No response")
                        else:
                            err = res.json().get("error",{}).get("message","Unknown")
                            ph.error(f"Error {res.status_code}: {err}")
                    except Exception as e:
                        ph.error(f"Exception: {str(e)}")


# === Telegram 탭 ===
with tabs[-1]:
    tg_ok = all([st.session_state.tg_api_id, st.session_state.tg_api_hash,
                 st.session_state.tg_phone, st.session_state.tg_bot_username])
    
    if not tg_ok:
        st.markdown("""<div class="empty-state"><div class="icon">📱</div>
            <div class="title">Telegram Setup Required</div>
            <div class="sub">Configure credentials in sidebar → 📱 Telegram</div>
            <div style="margin-top:16px;font-size:12px;color:#d1d5db;">
                Get API credentials at <a href="https://my.telegram.org" target="_blank">my.telegram.org</a>
            </div></div>""", unsafe_allow_html=True)
    
    elif st.session_state.tg_auth_status == "CODE_NEEDED":
        st.markdown("""<div class="empty-state"><div class="icon">🔐</div>
            <div class="title">Enter Verification Code</div>
            <div class="sub">Check your Telegram app</div></div>""", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            tg_code = st.text_input("Code", placeholder="12345", key="tg_auth_code", label_visibility="collapsed")
        with col2:
            if st.button("✅ Verify", use_container_width=True, type="primary"):
                if tg_code:
                    with st.spinner("Verifying..."):
                        result = tg_verify_code(
                            st.session_state.tg_api_id, st.session_state.tg_api_hash,
                            st.session_state.tg_phone, tg_code, st.session_state.tg_code_hash
                        )
                    if result == "AUTHORIZED":
                        st.session_state.tg_auth_status = "AUTHORIZED"; st.rerun()
                    else: st.error(f"Failed: {result}")
    
    elif st.session_state.tg_auth_status != "AUTHORIZED":
        st.markdown("""<div class="empty-state"><div class="icon">🔗</div>
            <div class="title">Click "Connect" in Sidebar</div></div>""", unsafe_allow_html=True)
    
    else:
        # === Telegram 채팅 UI ===
        bot_name = st.session_state.tg_bot_username
        
        # 헤더
        st.markdown(f"""<div class="tg-header">
            <div class="tg-avatar">🤖</div>
            <div class="tg-bot-info">
                <div class="name">{bot_name}</div>
                <div class="status">● online</div>
            </div>
        </div>""", unsafe_allow_html=True)
        
        # 툴바
        tc1, tc2, tc3, tc4 = st.columns([1, 1, 1.5, 4])
        with tc1:
            do_refresh = st.button("🔄 Refresh", use_container_width=True, key="tg_ref")
        with tc2:
            do_clear = st.button("🗑️ Clear", use_container_width=True, key="tg_clr")
        with tc3:
            auto_on = st.toggle("Auto 60s", value=False, key="tg_auto")
        
        if do_refresh:
            with st.spinner("⏳"):
                if tg_fetch_messages(): st.rerun()
                else: st.error("Fetch failed")
        
        if do_clear:
            st.session_state.tg_messages = []; save_tg_history(); st.rerun()
        
        # 자동 갱신 (60초)
        if auto_on:
            try:
                from streamlit_autorefresh import st_autorefresh
                count = st_autorefresh(interval=60000, limit=None, key="tg_ar")
                if count > 0:
                    tg_fetch_messages()
            except ImportError:
                # fallback
                st.markdown("""<script>
                    if(!window._ar){window._ar=setInterval(()=>{
                        const b=window.parent.document.querySelectorAll('button');
                        b.forEach(x=>{if(x.innerText.includes('Refresh'))x.click();});
                    },60000);}
                </script>""", unsafe_allow_html=True)
        
        # 채팅 영역
        tg_chat = st.container(height=chat_window_height, border=False)
        
        with tg_chat:
            if not st.session_state.tg_messages:
                st.markdown('<div class="empty-state"><div class="icon">💬</div><div class="sub">No messages yet</div></div>', unsafe_allow_html=True)
            else:
                html = '<div class="tg-chat-area">'
                for msg in st.session_state.tg_messages:
                    text = (msg.get('text','')
                            .replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                            .replace('\n','<br>'))
                    t = msg.get('date','')
                    cls = "me" if msg.get("from_me") else "bot"
                    html += f'<div class="tg-row {cls}"><div><div class="tg-bubble {cls}">{text}</div><div class="tg-ts {cls}">{t}</div></div></div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)
        
        # 입력
        if tg_input := st.chat_input("Message...", key="tg_input"):
            with st.spinner("Sending..."):
                result = tg_send_via_user_api(
                    st.session_state.tg_api_id, st.session_state.tg_api_hash,
                    st.session_state.tg_phone, st.session_state.tg_bot_username, tg_input
                )
                if result is True:
                    time.sleep(5)  # 1차 갱신: 5초 대기
                    tg_fetch_messages()
                    st.session_state.tg_pending_refresh = True
                    st.rerun()
                else:
                    st.error(f"Failed: {result}")
        
        # 2차 갱신 (30초 후)
        if st.session_state.get("tg_pending_refresh", False):
            st.session_state.tg_pending_refresh = False
            st.markdown("""<script>
                if(!window._dr){window._dr=true;
                setTimeout(()=>{window._dr=false;
                    const b=window.parent.document.querySelectorAll('button');
                    b.forEach(x=>{if(x.innerText.includes('Refresh'))x.click();});
                },30000);}
            </script>""", unsafe_allow_html=True)

import streamlit as st
import requests
import json
import uuid
import os
import base64
import re
import asyncio
import threading
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
            
            return {k: v for k, v in categories.items() if v}
        else:
            st.error(f"Failed to fetch models: {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Model fetch error: {str(e)}")
        return None

# --- Telegram 유틸리티 함수 ---
def _run_async(coro):
    """Streamlit 환경에서 안전하게 async 함수를 실행합니다.
    Streamlit은 이미 이벤트 루프가 돌고 있을 수 있어서,
    새 루프를 별도 스레드에서 실행합니다."""
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
    t.join(timeout=30)  # 최대 30초 대기
    
    if exception[0]:
        raise exception[0]
    return result[0]

def _get_session_name(phone):
    return f"session_{phone.replace('+','').replace(' ','')}"

def tg_authenticate(api_id, api_hash, phone):
    """Telethon 세션 인증을 시작합니다."""
    try:
        from telethon import TelegramClient
        
        async def _auth():
            session_name = _get_session_name(phone)
            client = TelegramClient(session_name, int(api_id), api_hash)
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
    """인증 코드로 로그인을 완료합니다."""
    try:
        from telethon import TelegramClient
        
        async def _verify():
            session_name = _get_session_name(phone)
            client = TelegramClient(session_name, int(api_id), api_hash)
            await client.connect()
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            authorized = await client.is_user_authorized()
            await client.disconnect()
            return "AUTHORIZED" if authorized else "FAILED"
        
        return _run_async(_verify())
    except Exception as e:
        return f"ERROR: {str(e)}"

def tg_send_via_user_api(api_id, api_hash, phone, bot_username, message):
    """내 계정으로 Bot에게 메시지를 보냅니다."""
    try:
        from telethon import TelegramClient
        
        async def _send():
            session_name = _get_session_name(phone)
            client = TelegramClient(session_name, int(api_id), api_hash)
            await client.connect()
            await client.send_message(bot_username, message)
            await client.disconnect()
            return True
        
        return _run_async(_send())
    except Exception as e:
        return str(e)

def tg_get_bot_replies(api_id, api_hash, phone, bot_username, limit=50):
    """Bot과의 대화 내역을 가져옵니다."""
    try:
        from telethon import TelegramClient
        
        async def _get_messages():
            session_name = _get_session_name(phone)
            client = TelegramClient(session_name, int(api_id), api_hash)
            await client.connect()
            
            messages = []
            async for msg in client.iter_messages(bot_username, limit=limit):
                messages.append({
                    "id": msg.id,
                    "text": msg.text or "",
                    "from_me": msg.out,
                    "date": msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else ""
                })
            
            await client.disconnect()
            messages.reverse()
            return messages
        
        return _run_async(_get_messages())
    except Exception as e:
        return str(e)


# --- 3. 핵심: Base64 클립보드 복사 스크립트 ---
st.markdown("""
<script>
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
                        .replace(/^#+\\s+/gm, '')           
                        .replace(/\\*\\*(.*?)\\*\\*/g, '$1')   
                        .replace(/__(.*?)__/g, '$1')       
                        .replace(/\\*(.*?)\\*/g, '$1')       
                        .replace(/`([^`]+)`/g, '$1')       
                        .replace(/\\[([^\\]]+)\\]\\([^\\)]+\\)/g, '$1') 
                        .replace(/```[\\s\\S]*?```/g, '')    
                        .replace(/>\\s?/g, '');             
                }

                await navigator.clipboard.writeText(text);

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
    
    /* Telegram 전용 스타일 */
    .tg-msg-user { background: linear-gradient(135deg, #dbeafe, #eff6ff); border: 1px solid #93c5fd; border-radius: 12px 12px 4px 12px; padding: 10px 14px; margin: 6px 0; margin-left: 20%; }
    .tg-msg-bot { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px 12px 12px 4px; padding: 10px 14px; margin: 6px 0; margin-right: 20%; }
    .tg-msg-time { font-size: 10px; color: #94a3b8; margin-top: 4px; }
    .tg-msg-text { font-size: 14px; color: #1e293b; line-height: 1.5; white-space: pre-wrap; }
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

def load_tg_history():
    """Telegram 대화 내역 로드"""
    if os.path.exists(TELEGRAM_HISTORY_FILE):
        try:
            with open(TELEGRAM_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.loads(decrypt_data(f.read(), ACCESS_PASSWORD))
        except: pass
    return []

def save_tg_history():
    """Telegram 대화 내역 저장"""
    data = encrypt_data(json.dumps(st.session_state.tg_messages, ensure_ascii=False), ACCESS_PASSWORD)
    with open(TELEGRAM_HISTORY_FILE, "w", encoding="utf-8") as f: f.write(data)

check_password()

# --- 세션 상태 초기화 ---
if "sessions" not in st.session_state: st.session_state.sessions = load_history()
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "model_options" not in st.session_state: st.session_state.model_options = None

# Telegram 관련 세션 상태
if "tg_api_id" not in st.session_state: st.session_state.tg_api_id = ""
if "tg_api_hash" not in st.session_state: st.session_state.tg_api_hash = ""
if "tg_phone" not in st.session_state: st.session_state.tg_phone = ""
if "tg_bot_username" not in st.session_state: st.session_state.tg_bot_username = ""
if "tg_auth_status" not in st.session_state: st.session_state.tg_auth_status = "NOT_STARTED"
if "tg_code_hash" not in st.session_state: st.session_state.tg_code_hash = ""
if "tg_messages" not in st.session_state: st.session_state.tg_messages = load_tg_history()
if "tg_last_update_id" not in st.session_state: st.session_state.tg_last_update_id = 0


# --- 5. 사이드바 UI ---
with st.sidebar:
    st.header("⚙️ Config")
    
    # === Gemini 설정 ===
    with st.expander("🤖 Gemini API", expanded=not bool(st.session_state.api_key)):
        st.session_state.api_key = st.text_input("API Key", value=st.session_state.api_key, type="password")
    
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
        selected_model_id = "gemini-1.5-flash"

    st.markdown("---")
    use_google_search = st.toggle("Net Search (Google Search)", value=False)
    st.markdown("---")
    
    with st.expander("Adv. Params", expanded=True):
        chat_window_height = st.slider("Chat Window Height", 400, 2000, 850, step=50)
        temperature = st.slider("Entropy", 0.0, 2.0, 0.7)
        system_prompt = st.text_area("SysPrompt", height=100)

    st.divider()
    
    # === Telegram 설정 ===
    with st.expander("📱 Telegram Config", expanded=False):
        st.session_state.tg_api_id = st.text_input("API ID", value=st.session_state.tg_api_id, type="password", key="tg_id_input")
        st.session_state.tg_api_hash = st.text_input("API Hash", value=st.session_state.tg_api_hash, type="password", key="tg_hash_input")
        st.session_state.tg_phone = st.text_input("Phone (+국가코드)", value=st.session_state.tg_phone, placeholder="+821012345678", key="tg_phone_input")
        st.session_state.tg_bot_username = st.text_input("Bot Username", value=st.session_state.tg_bot_username, placeholder="@my_bot", key="tg_bot_input")
        
        # 인증 상태 표시
        if st.session_state.tg_auth_status == "AUTHORIZED":
            st.success("✅ Telegram 인증 완료")
        elif st.session_state.tg_auth_status == "CODE_NEEDED":
            st.warning("⏳ 인증 코드 입력 대기중")
        else:
            st.info("🔑 인증 필요")
        
        # 연결 버튼
        tg_ready = all([st.session_state.tg_api_id, st.session_state.tg_api_hash, 
                        st.session_state.tg_phone, st.session_state.tg_bot_username])
        
        if st.button("🔗 Connect Telegram", use_container_width=True, disabled=not tg_ready):
            try:
                with st.spinner("Connecting to Telegram..."):
                    result, code_hash = tg_authenticate(
                        st.session_state.tg_api_id,
                        st.session_state.tg_api_hash,
                        st.session_state.tg_phone
                    )
                    st.session_state.tg_auth_status = result
                    if code_hash:
                        st.session_state.tg_code_hash = code_hash
                    if result == "AUTHORIZED":
                        st.success("✅ Connected!")
                    elif result == "CODE_NEEDED":
                        st.info("📲 Telegram 앱에서 인증 코드를 확인하세요.")
                    else:
                        st.error(f"❌ {result}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")

    st.divider()
    
    # === 세션 관리 버튼 ===
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


# --- 6. 메인 UI (탭 구성) ---
st.markdown(f"### 📊 System Dashboard <small style='float:right; color:#94a3b8;'>Model: {selected_model_id}</small>", unsafe_allow_html=True)

# Gemini 세션 탭들 + Telegram 탭
tab_names = [s["title"] for s in st.session_state.sessions] + ["📱 Telegram"]
tabs = st.tabs(tab_names)

# === Gemini 탭들 ===
for i in range(len(st.session_state.sessions)):
    with tabs[i]:
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
            
            # --- Gemini API 호출 (즉시 처리) ---
            with chat_container:
                with st.chat_message("assistant", avatar="🤖"):
                    ph = st.empty()
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
                                
                                ph.markdown(bot_text)
                                session["messages"].append({"role": "assistant", "content": bot_text, "sources": sources})
                                save_history()
                                st.rerun()
                        else:
                            error_details = res.json().get("error", {}).get("message", "Unknown Error")
                            ph.error(f"Error {res.status_code}: {error_details}")
                    except Exception as e:
                        ph.error(f"Exception: {str(e)}")


# === Telegram 탭 ===
with tabs[-1]:
    tg_configured = all([st.session_state.tg_api_id, st.session_state.tg_api_hash, 
                         st.session_state.tg_phone, st.session_state.tg_bot_username])
    
    if not tg_configured:
        st.warning("📱 사이드바에서 Telegram 설정을 먼저 입력하세요.")
        st.markdown("""
        **필요한 정보:**
        1. **API ID** & **API Hash** → [my.telegram.org](https://my.telegram.org) 에서 발급
        2. **Phone** → 본인 전화번호 (국가코드 포함, 예: +821012345678)
        3. **Bot Username** → 대화할 Bot (예: @my_bot)
        """)
    
    elif st.session_state.tg_auth_status == "CODE_NEEDED":
        # 인증 코드 입력 UI
        st.info("📲 Telegram 앱에 전송된 인증 코드를 입력하세요.")
        col1, col2 = st.columns([3, 1])
        with col1:
            tg_code = st.text_input("인증 코드", placeholder="12345", key="tg_auth_code")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ 인증", use_container_width=True):
                if tg_code:
                    result = tg_verify_code(
                        st.session_state.tg_api_id,
                        st.session_state.tg_api_hash,
                        st.session_state.tg_phone,
                        tg_code,
                        st.session_state.tg_code_hash
                    )
                    if result == "AUTHORIZED":
                        st.session_state.tg_auth_status = "AUTHORIZED"
                        st.success("인증 완료!")
                        st.rerun()
                    else:
                        st.error(f"인증 실패: {result}")
    
    elif st.session_state.tg_auth_status != "AUTHORIZED":
        st.info("🔗 사이드바에서 'Connect Telegram' 버튼을 눌러 인증을 시작하세요.")
    
    else:
        # === 인증 완료 — Telegram 채팅 UI ===
        bot_name = st.session_state.tg_bot_username
        st.markdown(f"#### 📱 Telegram — `{bot_name}`")
        
        # 새로고침 + 대화 삭제 버튼
        tc1, tc2, tc3 = st.columns([1, 1, 4])
        with tc1:
            if st.button("🔄 새로고침", use_container_width=True, key="tg_refresh"):
                with st.spinner("불러오는 중..."):
                    result = tg_get_bot_replies(
                        st.session_state.tg_api_id,
                        st.session_state.tg_api_hash,
                        st.session_state.tg_phone,
                        st.session_state.tg_bot_username,
                        limit=100
                    )
                    if isinstance(result, list):
                        st.session_state.tg_messages = result
                        save_tg_history()
                        st.rerun()
                    else:
                        st.error(f"Error: {result}")
        with tc2:
            if st.button("🗑️ 로그 삭제", use_container_width=True, key="tg_clear"):
                st.session_state.tg_messages = []
                save_tg_history()
                st.rerun()
        
        # 자동 새로고침 (60초 간격 — 안전)
        with tc3:
            auto_refresh = st.toggle("⚡ 자동 새로고침 (60초)", value=False, key="tg_auto_refresh")
        
        if auto_refresh:
            st.markdown("""
            <script>
                if (!window._tgAutoRefresh) {
                    window._tgAutoRefresh = true;
                    setTimeout(() => {
                        window._tgAutoRefresh = false;
                        window.parent.document.querySelectorAll('button').forEach(btn => {
                            if (btn.innerText.includes('새로고침')) btn.click();
                        });
                    }, 60000);
                }
            </script>
            """, unsafe_allow_html=True)

        # 채팅 표시 영역
        tg_chat_container = st.container(height=chat_window_height, border=False)
        
        with tg_chat_container:
            if not st.session_state.tg_messages:
                st.caption("대화가 없습니다. 아래에 메시지를 입력하거나 🔄 새로고침을 눌러주세요.")
            else:
                for msg in st.session_state.tg_messages:
                    if msg.get("from_me"):
                        # 내가 보낸 메시지 (오른쪽)
                        st.markdown(f"""
                        <div class="tg-msg-user">
                            <div class="tg-msg-text">{msg.get('text', '')}</div>
                            <div class="tg-msg-time" style="text-align:right;">🧑‍💻 {msg.get('date', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Bot 응답 (왼쪽)
                        st.markdown(f"""
                        <div class="tg-msg-bot">
                            <div class="tg-msg-text">{msg.get('text', '')}</div>
                            <div class="tg-msg-time">🤖 {bot_name} · {msg.get('date', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # 메시지 입력
        if tg_input := st.chat_input("Telegram 메시지 입력...", key="tg_chat_input"):
            with st.spinner("전송 중..."):
                result = tg_send_via_user_api(
                    st.session_state.tg_api_id,
                    st.session_state.tg_api_hash,
                    st.session_state.tg_phone,
                    st.session_state.tg_bot_username,
                    tg_input
                )
                if result is True:
                    # 1차 갱신: 5초 대기 후
                    import time
                    time.sleep(5)
                    
                    updated = tg_get_bot_replies(
                        st.session_state.tg_api_id,
                        st.session_state.tg_api_hash,
                        st.session_state.tg_phone,
                        st.session_state.tg_bot_username,
                        limit=100
                    )
                    if isinstance(updated, list):
                        st.session_state.tg_messages = updated
                        save_tg_history()
                    
                    # 2차 갱신 예약: 30초 후 자동 새로고침 트리거
                    st.session_state.tg_pending_refresh = True
                    st.rerun()
                else:
                    st.error(f"전송 실패: {result}")
        
        # 2차 지연 갱신 (30초 후) — 메시지 전송 직후에만 작동
        if st.session_state.get("tg_pending_refresh", False):
            st.session_state.tg_pending_refresh = False
            st.markdown("""
            <script>
                if (!window._tgDelayedRefresh) {
                    window._tgDelayedRefresh = true;
                    setTimeout(() => {
                        window._tgDelayedRefresh = false;
                        window.parent.document.querySelectorAll('button').forEach(btn => {
                            if (btn.innerText.includes('새로고침')) btn.click();
                        });
                    }, 30000);
                }
            </script>
            """, unsafe_allow_html=True)

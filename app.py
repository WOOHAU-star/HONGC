import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pytz
import json
import os
import requests
import uuid
import time

# ==========================================
# 0. 중복 접속 차단 (Session Lock) 글로벌 레지스트리
# ==========================================
@st.cache_resource
def get_active_users():
    # 구조: {"닉네임": {"sid": "랜덤세션ID", "last_seen": 타임스탬프}}
    return {}

active_users = get_active_users()
TIMEOUT_SECONDS = 90  # 90초 이상 생존신고(새로고침) 없으면 로그아웃 간주

# ==========================================
# 1. 영구 저장소 (Cloud JSONBin)
# ==========================================
DB_FILE = "apex_database.json"

def get_secrets():
    try:
        if "JSONBIN_KEY" in st.secrets and "JSONBIN_ID" in st.secrets:
            return st.secrets["JSONBIN_KEY"], st.secrets["JSONBIN_ID"]
    except: pass
    return None, None

def load_db():
    key, bin_id = get_secrets()
    db_data = {}
    if key and bin_id:
        try:
            url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
            headers = {"X-Master-Key": key}
            req = requests.get(url, headers=headers)
            if req.status_code == 200:
                db_data = req.json().get("record", {})
        except: pass
    
    if not db_data and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db_data = json.load(f)
        except: pass

    if "users" not in db_data:
        old_data = db_data.copy()
        db_data = {"users": {"Admin": {"favorites": old_data.get("favorites", []), "paper_trades": old_data.get("paper_trades", []), "settings": old_data.get("settings", {"total_capital": 100000, "max_stocks": 5, "weight_pct": 100.0, "fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0, "gap_limit_pct": 2.0})}}}
    return db_data

def save_db(full_db):
    key, bin_id = get_secrets()
    if key and bin_id:
        try:
            # 동시성 덮어쓰기 방어막 (Fetch-and-Merge)
            url_get = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
            headers = {"X-Master-Key": key}
            req = requests.get(url_get, headers=headers)
            if req.status_code == 200:
                latest_db = req.json().get("record", {"users": {}})
                current_u = st.session_state.current_user
                if "users" not in latest_db: latest_db["users"] = {}
                latest_db["users"][current_u] = full_db["users"][current_u]
                full_db = latest_db
            
            url_put = f"https://api.jsonbin.io/v3/b/{bin_id}"
            headers_put = {"Content-Type": "application/json", "X-Master-Key": key}
            requests.put(url_put, json=full_db, headers=headers_put)
        except: pass

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(full_db, f, ensure_ascii=False, indent=4)

# ==========================================
# 2. 테마 및 페이지 세팅
# ==========================================
st.set_page_config(page_title="APEX V49.0 - Secure Quant", layout="wide", page_icon="⚖️")

if 'full_db' not in st.session_state:
    st.session_state.full_db = load_db()

if 'theme' not in st.session_state: st.session_state.theme = "Night (Dark)"
bg_color = "#0f172a" if st.session_state.theme == "Night (Dark)" else "#f8fafc"
text_color = "#f8fafc" if st.session_state.theme == "Night (Dark)" else "#1e293b"
card_bg = "rgba(30, 41, 59, 0.8)" if st.session_state.theme == "Night (Dark)" else "#ffffff"
border_color = "rgba(148, 163, 184, 0.2)" if st.session_state.theme == "Night (Dark)" else "rgba(0, 0, 0, 0.1)"
accent_text = "#60a5fa" if st.session_state.theme == "Night (Dark)" else "#2563eb"
muted_text = "#94a3b8" if st.session_state.theme == "Night (Dark)" else "#64748b"

st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  {{ font-family: 'Pretendard', sans-serif !important; }}
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .rank-box {{ padding: 15px; margin-bottom: 15px; border-radius: 8px; border: 1px solid {border_color}; background: {card_bg}; color: {text_color}; }}
    .rank-1 {{ border-top: 4px solid #3b82f6; }}
    .rank-2 {{ border-top: 4px solid #64748b; }}
    .rank-3 {{ border-top: 4px solid #94a3b8; }}
    @keyframes blinker {{ 50% {{ opacity: 0; }} }}
    .blink-red {{ color: #ef5350; font-weight: 900; animation: blinker 1s linear infinite; }}
    .blink-blue {{ color: #42a5f5; font-weight: 900; animation: blinker 1s linear infinite; }}
    @keyframes neon {{ 0% {{ text-shadow: 0 0 5px #fff, 0 0 10px #00e676, 0 0 20px #00e676; color: #fff; border-color: #00e676; }} 100% {{ text-shadow: 0 0 2px #fff, 0 0 5px #00e676, 0 0 10px #00e676; color: #b9fbc0; border-color: #b9fbc0; }} }}
    .neon-box {{ padding: 15px; border-radius: 8px; background: rgba(0,0,0,0.6); border: 2px solid #00e676; text-align: center; animation: neon 1.5s infinite alternate; font-size: 18px; font-weight: 800; margin-bottom: 20px; }}
    div[role="radiogroup"] {{ justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; background: transparent; border: none; }}
    @keyframes ticker {{ 0% {{ transform: translateX(50%); }} 100% {{ transform: translateX(-150%); }} }}
    .ticker-wrap {{ width: 100%; overflow: hidden; background: transparent; padding: 5px 0; margin-top: 5px; margin-bottom: 15px; border: none; }}
    .ticker-move {{ display: inline-block; white-space: nowrap; animation: ticker 160s linear infinite; font-size: 14px; font-weight: 700; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 로그인 및 중복접속 차단 파티션 로직
# ==========================================
url_params = st.query_params
url_u = url_params.get('u')
url_sid = url_params.get('sid')
current_time = time.time()

# [신규] 자동 로그인 및 새로고침 검증 로직
if url_u and url_sid and 'current_user' not in st.session_state:
    record = active_users.get(url_u)
    if record:
        if record['sid'] == url_sid:
            # 내 세션이 맞음 (새로고침 통과)
            st.session_state.current_user = url_u
            st.session_state.session_id = url_sid
        else:
            # 다른 기기에서 접근 시도
            if current_time - record['last_seen'] < TIMEOUT_SECONDS:
                st.error(f"⚠️ '{url_u}' 님은 이미 다른 기기(또는 브라우저)에서 접속 중입니다.")
                st.info("비정상 종료 시 90초 후에 다시 시도해 주십시오.")
                st.stop()
            else:
                # 90초 지났으면 죽은 세션으로 간주, 탈취 허용
                st.session_state.current_user = url_u
                st.session_state.session_id = url_sid
    else:
        # 최초 자동 로그인
        st.session_state.current_user = url_u
        st.session_state.session_id = url_sid

# --- 로그인 화면 (세션이 없을 때만 표시) ---
if 'current_user' not in st.session_state:
    st.markdown("<br><br><h1 style='text-align:center;'>🚀 APEX QUANT 관제탑</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:{muted_text};'>자신만의 트레이더 닉네임(1~8자)을 입력하여 개인 관제탑을 엽니다.<br>비밀번호는 없으나 중복 접속은 차단됩니다.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<div style='background:{card_bg}; padding:30px; border-radius:15px; border:1px solid {border_color};'>", unsafe_allow_html=True)
        login_name = st.text_input("트레이더 닉네임", max_chars=8, placeholder="예: 무적단타")
        
        if st.button("관제탑 입장하기", type="primary", use_container_width=True):
            if 1 <= len(login_name) <= 8:
                rec = active_users.get(login_name)
                # 누군가 이미 이 닉네임으로 90초 이내에 활동했다면 차단!
                if rec and (current_time - rec['last_seen'] < TIMEOUT_SECONDS):
                    st.error(f"⚠️ '{login_name}' 님은 이미 다른 기기에서 접속 중입니다. (비정상 종료 시 90초 후 재시도)")
                else:
                    new_sid = str(uuid.uuid4())[:8] # 나만의 고유 입장권 발급
                    if login_name not in st.session_state.full_db["users"]:
                        st.session_state.full_db["users"][login_name] = {
                            "favorites": [], "paper_trades": [], 
                            "settings": {"total_capital": 100000, "max_stocks": 5, "weight_pct": 100.0, "fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0, "gap_limit_pct": 2.0}
                        }
                        save_db(st.session_state.full_db)
                    
                    # 브라우저에 쿠키(LocalStorage) 저장 후 리다이렉트
                    js_code = f"""
                    <script>
                        localStorage.setItem('apex_user', '{login_name}');
                        localStorage.setItem('apex_sid', '{new_sid}');
                        window.parent.location.href = window.parent.location.pathname + '?u={login_name}&sid={new_sid}';
                    </script>
                    """
                    components.html(js_code, height=0)
            else:
                st.error("닉네임은 1자에서 8자 사이로 입력해주세요.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    auto_login_js = """
    <script>
        const user = localStorage.getItem('apex_user');
        const sid = localStorage.getItem('apex_sid');
        const urlParams = new URLSearchParams(window.parent.location.search);
        if (user && sid && (!urlParams.has('u') || !urlParams.has('sid'))) {
            window.parent.location.href = window.parent.location.pathname + "?u=" + encodeURIComponent(user) + "&sid=" + encodeURIComponent(sid);
        }
    </script>
    """
    components.html(auto_login_js, height=0)
    st.stop()

# ==========================================
# 4. 메인 앱 실행 (로그인 통과 시 하트비트 작동)
# ==========================================
current_u = st.session_state.current_user
current_sid = st.session_state.session_id

# 생존 신고 (Heartbeat) - 새로고침할 때마다 현재 시간을 갱신하여 방을 잠금 유지
active_users[current_u] = {"sid": current_sid, "last_seen": time.time()}

u_data = st.session_state.full_db["users"][current_u]
u_favs = u_data["favorites"]
u_trades = u_data["paper_trades"]
u_set = u_data["settings"]

def sync_and_save():
    st.session_state.full_db["users"][current_u]["favorites"] = u_favs
    st.session_state.full_db["users"][current_u]["paper_trades"] = u_trades
    st.session_state.full_db["users"][current_u]["settings"] = u_set
    save_db(st.session_state.full_db)

# ==========================================
# 5. 사이드바 제어 (유저 정보 표시)
# ==========================================
with st.sidebar:
    st.markdown(f"""
        <div style='background:{card_bg}; padding:15px; border-radius:10px; border:2px solid #00e676; text-align:center; margin-bottom:20px;'>
            <h3 style='margin:0; color:{text_color};'>👤 <span style='color:#00e676;'>{current_u}</span> 님</h3>
            <p style='margin:0; font-size:12px; color:{muted_text};'>🟢 관제탑 접속 중 (보안 잠금)</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 안전하게 로그아웃", use_container_width=True):
        if current_u in active_users: del active_users[current_u] # 명시적 로그아웃 시 즉시 방 개방
        logout_js = """<script>localStorage.removeItem('apex_user'); localStorage.removeItem('apex_sid'); window.parent.location.href = window.parent.location.pathname;</script>"""
        components.html(logout_js, height=0)
        st.stop()
    
    st.divider()
    st.header("⭐ 관심종목 관리")
    st.subheader("🌐 종목 직접 검색 (US Market)")
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        new_search_ticker = st.text_input("티커 (예: PLTR)", label_visibility="collapsed").upper()
    with col_btn:
        search_submit = st.button("추가", use_container_width=True)
        
    if search_submit and new_search_ticker:
        if "." in new_search_ticker: st.error("미장 종목만 가능")
        elif new_search_ticker in u_favs: st.warning("이미 등록됨")
        else:
             with st.spinner("검증 중..."):
                 try:
                     test_df = yf.Ticker(new_search_ticker).history(period="1d")
                     if not test_df.empty:
                         u_favs.append(new_search_ticker)
                         sync_and_save()
                         st.success(f"{new_search_ticker} 추가!")
                         st.rerun()
                     else: st.error("없는 티커입니다.")
                 except: st.error("검증 실패.")
    
    SECTORS = {
        "🌟 Big Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE", "CRM"],
        "💻 AI/반도체": ["AMD", "TSM", "ASML", "ARM", "SMCI", "KLAC", "SNPS", "CDNS", "NXPI", "MCHP"],
        "⚡ 전기차/에너지": ["RIVN", "LCID", "F", "GM", "NIO", "XPEV", "LI", "ALB", "PLUG", "ENPH", "XOM"],
        "🧬 바이오/헬스": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "AMGN", "GILD", "BMY", "CVS"],
        "🏦 금융/핀테크": ["JPM", "BAC", "V", "MA", "PYPL", "SQ", "HOOD", "COIN", "GS", "MS"],
        "🛡️ 보안/클라우드": ["CRWD", "PANW", "FTNT", "NOW", "SNOW", "PLTR", "DDOG", "NET", "ZS", "OKTA"]
    }
    TICKER_DICT = {"AAPL": "애플", "MSFT": "마이크로소프트", "GOOGL": "구글", "AMZN": "아마존", "META": "메타", "TSLA": "테슬라", "NVDA": "엔비디아"}
    
    all_tickers_flat = [t for v in SECTORS.values() for t in v]
    combined_options = list(set(all_tickers_flat + u_favs))
    new_favs = st.multiselect("등록된 관심종목 삭제", options=combined_options, default=u_favs, format_func=lambda x: f"{x}")
    if new_favs != u_favs:
        u_data["favorites"] = new_favs; u_favs = new_favs; sync_and_save()
        
    st.header("💰 자산 통제")
    new_cap = st.number_input("가용 자산 (USD)", min_value=1000, value=int(u_set.get("total_capital", 100000)), step=5000)
    new_max = st.number_input("분산 종목 수", min_value=1, max_value=20, value=int(u_set.get("max_stocks", 5)))
    new_wgt = st.slider("투입 비중 (%)", 10.0, 100.0, float(u_set.get("weight_pct", 100.0)), 5.0)
    allocated_per_stock = (new_cap / new_max) * (new_wgt / 100)
    
    st.divider()
    st.header("⚙️ 딥 필터")
    new_k = st.slider("K-값", 0.3, 0.8, float(u_set.get("fixed_k", 0.5)), 0.05)
    new_sl = st.slider("칼손절 (%)", 1.0, 10.0, float(u_set.get("stop_loss_pct", 4.0)), 0.5)
    new_rr = st.slider("목표 손익비", 1.0, 5.0, float(u_set.get("base_rr_ratio", 2.0)), 0.5)
    new_gap = st.slider("갭 허용 (%)", 0.5, 5.0, float(u_set.get("gap_limit_pct", 2.0)), 0.1)

    if (new_cap != u_set["total_capital"] or new_max != u_set["max_stocks"] or new_wgt != u_set["weight_pct"] or 
        new_k != u_set["fixed_k"] or new_sl != u_set["stop_loss_pct"] or new_rr != u_set["base_rr_ratio"] or new_gap != u_set["gap_limit_pct"]):
        u_set.update({"total_capital": new_cap, "max_stocks": new_max, "weight_pct": new_wgt, "fixed_k": new_k, "stop_loss_pct": new_sl, "base_rr_ratio": new_rr, "gap_limit_pct": new_gap})
        sync_and_save()

# ==========================================
# 6. 매크로 및 엔진 모듈
# ==========================================
@st.cache_data(ttl=60)
def get_macro_indices():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "NASDAQ 100": "^NDX"}
    data = {}
    for name, ticker in tickers.items():
        try:
            df = yf.Ticker(ticker).history(period="2d")
            curr, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
            data[name] = {"price": curr, "pct": ((curr - prev) / prev) * 100}
        except: data[name] = {"price": 0, "pct": 0}
    return data

def get_market_time():
    now_est = datetime.now(pytz.timezone('Asia/Seoul')).astimezone(pytz.timezone('US/Eastern'))
    m_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    m_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    if now_est.weekday() >= 5 or (now_est.weekday() == 4 and now_est >= m_close):
        days_ahead = 7 - now_est.weekday() if now_est.weekday() < 6 else 1
        if now_est.weekday() == 4: days_ahead = 3
        next_open = m_open + timedelta(days=days_ahead)
        diff = next_open - now_est
        status, timer = "🔴 휴장", f"{diff.days}일 {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    elif now_est < m_open:
        diff = m_open - now_est
        status, timer = "🟡 프리", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m"
    elif m_open <= now_est <= m_close:
        diff = m_close - now_est
        status, timer = "🟢 LIVE", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m"
    else:
        next_open = m_open + timedelta(days=1)
        diff = next_open - now_est
        status, timer = "🔵 마감", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m"
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S'), status, timer

@st.cache_data(ttl=60) 
def get_ranking_data(tickers, k, allocated_budget, gap_limit, sl_pct, base_rr):
    results = []
    now = datetime.now()
    today_weekday = datetime.now(pytz.timezone('US/Eastern')).weekday() 
    default_columns = ["티커", "종목명", "상태", "접근율", "현재가", "등락률", "매수타점", "권장수량", "추천점수", "엔진판단", "현재가_수치", "상승여부"]
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d")
            if df.empty or len(df) < 25: continue
            
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            atr_14 = df[['H-L', 'H-PC', 'L-PC']].max(axis=1).rolling(14).mean().iloc[-1]
            
            denom = df['High'].rolling(14).max() - df['Low'].rolling(14).min()
            df['%R'] = np.where(denom == 0, -50, -100 * (df['High'].rolling(14).max() - df['Close']) / denom)
            df['Highest_22'] = df['Close'].rolling(22).max()
            df['VIX_Fix'] = np.where(df['Highest_22'] == 0, 0, (df['Highest_22'] - df['Low']) / df['Highest_22'] * 100)
            
            yest2 = df.iloc[-3]; yest = df.iloc[-2]; today = df.iloc[-1]
            current = today['Close']; yest_close = yest['Close']
            
            change_pct = ((current - yest_close) / yest_close) * 100 if yest_close > 0 else 0
            is_up = change_pct > 0
            if change_pct > 0: pct_str = f"🔺 +{change_pct:.2f}%"
            elif change_pct < 0: pct_str = f"🔵 {change_pct:.2f}%"
            else: pct_str = "➖ 0.00%"
            
            ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
            p_range = yest['High'] - yest['Low']
            target = today['Open'] + (p_range * k)
            
            atr_pct = (atr_14 / current) * 100 if current > 0 else 0
            dynamic_rr = base_rr * 1.5 if atr_pct >= 4.0 else (base_rr * 0.8 if atr_pct <= 2.0 else base_rr)
            
            stop_loss = target * (1 - (sl_pct / 100)); take_profit = target + ((target - stop_loss) * dynamic_rr); bailout_price = target + 0.01 
            gap_pct = ((today['Open'] - yest_close) / yest_close) * 100 if yest_close > 0 else 0
            
            is_gap_danger = gap_pct >= gap_limit
            is_bull = today['Open'] > ma5
            is_hit = current >= target
            is_chasing = current > (target * 1.015) 
            
            is_earnings_danger = False
            if is_bull and (is_hit or ((target - current) / current * 100 < 3.0)):
                try:
                    cal = stock.calendar
                    if isinstance(cal, dict) and 'Earnings Date' in cal and len(cal['Earnings Date']) > 0:
                        e_date = cal['Earnings Date'][0]
                        if isinstance(e_date, datetime) and 0 <= (e_date.date() - now.date()).days <= 7: is_earnings_danger = True
                except: pass
            
            dist_pct_str = f"{((target - current) / current) * 100:.1f}%"
            if not is_bull or is_gap_danger or is_earnings_danger: status_lamp = "🔴 불가"; dist_pct_str = "-"
            elif is_chasing: status_lamp = "🚀 초과"; dist_pct_str = "-"
            elif is_hit: status_lamp = "🟢 진입"; dist_pct_str = "완료"
            else: status_lamp = "🟡 대기"

            is_nr4 = (yest['High'] - yest['Low']) <= (df['High'].iloc[-5:-1] - df['Low'].iloc[-5:-1]).min()
            is_oops = (today['Open'] < yest['Low']) and (current > yest['Low'])
            is_will_hook = (yest2['%R'] <= -80) and (yest['%R'] > yest2['%R'])

            score = 0; reasons = []
            if today_weekday in [1, 2]: score += 15; reasons.append("화/수")
            
            if is_earnings_danger: score -= 200; reasons.append("⚠️실적임박")
            elif is_gap_danger: score -= 100; reasons.append("🚫갭상승")
            elif not is_bull: score -= 50; reasons.append("📉역배열")
            elif is_chasing: score -= 30; reasons.append("⛔추격금지") 
            else:
                score += 10; reasons.append("✅5MA↑")
                if is_hit: score += 50; reasons.append("🔥타점도달")
                if is_nr4: score += 20; reasons.append("⚡NR4")
                if is_oops: score += 25; reasons.append("🔄OOPS")
                if is_will_hook: score += 15; reasons.append("🎣%R반전")
                if df['VIX_Fix'].iloc[-1] >= 12.0: score += 30; reasons.append("🥶VIX바닥")

            results.append({
                "티커": ticker, "종목명": TICKER_DICT.get(ticker, ticker),
                "상태": status_lamp, "접근율": dist_pct_str, 
                "현재가": current, "등락률": pct_str, "현재가_수치": current, "상승여부": is_up, 
                "매수타점": target, "적용R/R": dynamic_rr, "익절가격": take_profit, "손절가격": stop_loss, "Bailout": bailout_price,
                "권장수량": int(allocated_budget / target) if status_lamp in ["🟢 진입", "🟡 대기"] else 0,
                "추천점수": score, "엔진판단": " ".join(reasons)
            })
        except: continue
        
    if not results: return pd.DataFrame(columns=default_columns), []
    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values(by="추천점수", ascending=False).reset_index(drop=True)
    return df_res, [row for _, row in df_res.iterrows() if row['추천점수'] > 0][:3]

def draw_chart(row_info):
    df_chart = yf.Ticker(row_info['티커']).history(period="1mo")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
    up_col, dn_col = '#ef5350', '#42a5f5'
    
    fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="Price", increasing_line_color=up_col, increasing_fillcolor=up_col, decreasing_line_color=dn_col, decreasing_fillcolor=dn_col), row=1, col=1)
    df_chart['MA5'] = df_chart['Close'].rolling(window=5).mean()
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA5'], mode='lines', name='5MA', line=dict(color='#ce93d8', width=1.5)), row=1, col=1)
    
    prices, volumes = df_chart['Close'], df_chart['Volume']
    bins = np.linspace(df_chart['Low'].min(), df_chart['High'].max(), 24) 
    hist, bin_edges = np.histogram(prices, bins=bins, weights=volumes)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    fig.add_trace(go.Bar(x=hist, y=bin_centers, orientation='h', xaxis='x3', yaxis='y', marker=dict(color='rgba(148, 163, 184, 0.15)', line=dict(width=0)), showlegend=False, hoverinfo='none'))
    
    tp_val, tg_val, sl_val = row_info['익절가격'], row_info['매수타점'], row_info['손절가격']
    bo_val = row_info['Bailout']
    fig.add_hline(y=tp_val, line_dash="solid", line_color="#3b82f6", line_width=1.5, annotation_text=f"TP: ${tp_val:.2f}", annotation_position="top right", row=1, col=1)
    fig.add_hline(y=tg_val, line_dash="dash", line_color="#4ade80", line_width=1.5, annotation_text=f"Target: ${tg_val:.2f}", annotation_position="top right", row=1, col=1)
    fig.add_hline(y=bo_val, line_dash="dot", line_color="#eab308", line_width=1.0, annotation_text=f"Bailout: ${bo_val:.2f}", annotation_position="bottom right", row=1, col=1)
    fig.add_hline(y=sl_val, line_dash="solid", line_color="#ef5350", line_width=1.5, annotation_text=f"SL: ${sl_val:.2f}", annotation_position="bottom right", row=1, col=1)
    
    v_colors = [up_col if r['Close'] >= r['Open'] else dn_col for i, r in df_chart.iterrows()]
    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=v_colors, name="Volume"), row=2, col=1)
    
    fig.update_xaxes(rangeslider_visible=False, fixedrange=True); fig.update_yaxes(fixedrange=True)
    t_style = "plotly_dark" if st.session_state.theme == "Night (Dark)" else "plotly_white"
    fig.update_layout(xaxis3=dict(overlaying='x', side='top', showticklabels=False, range=[0, max(hist)*3]), template=t_style, height=450, margin=dict(l=0,r=40,t=20,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, dragmode=False)
    return fig

# ==========================================
# 7. 메인 UI (티커 & 탭)
# ==========================================
k_time, m_status, m_timer = get_market_time()
indices = get_macro_indices()

ticker_items = []
ticker_items.append(f"<span style='color:{muted_text};'>KOR</span> <b style='color:{accent_text};'>{k_time}</b>")
ticker_items.append(f"<b style='color:{text_color};'>{m_status}</b> <span style='color:{muted_text};'>({m_timer})</span>")

for name, data in indices.items():
    color = "#ef5350" if data['pct'] >= 0 else "#42a5f5"
    sign = "+" if data['pct'] >= 0 else ""
    ticker_items.append(f"<span style='color:{muted_text};'>{name}</span> <b style='color:{text_color};'>{data['price']:,.0f}</b> <span style='color:{color};'>({sign}{data['pct']:.2f}%)</span>")
single_ticker_str = "&nbsp;&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp;".join(ticker_items)
full_ticker_str = f"{single_ticker_str} &nbsp;&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp; " * 8 

st.markdown(f"""<div class="ticker-wrap"><div class="ticker-move">{full_ticker_str}</div></div>""", unsafe_allow_html=True)

selected_sector = st.radio("🔭 섹터", list(SECTORS.keys()), horizontal=True, label_visibility="collapsed")
tab1, tab2, tab3 = st.tabs(["📊 관제탑", "⭐ 내 관심종목", "🏆 명예의 전당"])

# ----------------- TAB 1: 관제탑 -----------------
with tab1:
    if selected_sector:
        with st.spinner("스캔 중..."):
            df_all, top_picks = get_ranking_data(SECTORS[selected_sector], new_k, allocated_per_stock, new_gap, new_sl, new_rr)
        
        st.subheader("💡 Top 3 Pick")
        if top_picks:
            cols = st.columns(3)
            for i, row in enumerate(top_picks):
                with cols[i]: st.markdown(f"""<div class="rank-box rank-{i+1}"><div style="font-size:15px; font-weight:800;">{row['종목명']}</div><div style="font-size:13px; line-height:1.6;">🎯 진입: <b>${row['매수타점']:.2f}</b><br/>💰 목표: ${row['익절가격']:.2f}<br/>🔍 근거: <span style="color:#eab308; font-weight:bold;">{row['엔진판단']}</span></div></div>""", unsafe_allow_html=True)
        else: st.info("조건을 완벽히 충족하는 종목이 없습니다.")

        reached = [p for p in top_picks if "🟢 진입" in p['상태']]
        for r in reached: st.markdown(f"""<div class="neon-box">📌 타점 도달: {r['종목명']} (진입가: ${r['현재가_수치']:.2f})</div>""", unsafe_allow_html=True)
        st.divider()
        
        if df_all.empty: st.warning("⚠️ 통신 지연입니다.")
        else:
            df_disp = df_all[['티커', '종목명', '상태', '접근율', '현재가', '등락률', '매수타점', '권장수량', '추천점수', '엔진판단']]
            sel = st.dataframe(df_disp, on_select="rerun", selection_mode="single-row", use_container_width=True, hide_index=True, height=300)
            idx = sel.selection.rows[0] if sel and sel.selection.rows else 0
            row = df_all.iloc[idx]; focus = row['티커']; is_f = focus in u_favs
            st.divider()
            
            if "🔴 불가" in row['상태']: st.warning("⚠️ 역배열, 갭상승 등의 위험으로 매수 금지.")
            elif "🚀 초과" in row['상태']: st.warning("⚠️ 이미 타점 초과. 추격매수 금지.")
                
            c_t, c_b1, c_b2, c_g = st.columns([3, 1, 1, 4])
            blink_class = "blink-red" if row['상승여부'] else "blink-blue"
            with c_t: st.markdown(f"<h3 style='margin:0;'>🔍 {row['종목명']} <span class='{blink_class}' style='font-size:20px; margin-left:10px;'>${row['현재가_수치']:.2f} ({row['등락률']})</span></h3>", unsafe_allow_html=True)
            with c_b1: 
                if st.button("⭐ 관심" if not is_f else "❌ 해제", key=f"b1_{focus}"):
                    if is_f: u_favs.remove(focus)
                    else: u_favs.append(focus)
                    sync_and_save(); st.rerun()
            with c_b2:
                if st.button("🎮 가상 매수", type="primary", key=f"b2_{focus}"):
                    if row['권장수량'] > 0: 
                        u_trades.append({"티커":focus, "종목명":row['종목명'], "진입가":row['현재가_수치'], "수량":row['권장수량'], "목표가":row['익절가격'], "손절가":row['손절가격'], "Bailout":row['Bailout'], "진입시간":datetime.now(pytz.timezone('Asia/Seoul')).strftime("%m-%d %H:%M")})
                        sync_and_save(); st.success("체결됨!")
                    else: st.error("금지 구간")
            st.plotly_chart(draw_chart(row), use_container_width=True, key=f"c1_{focus}", config={'displayModeBar': False})

# ----------------- TAB 2: 내 관심종목 -----------------
with tab2:
    if u_favs:
        with st.spinner("관심종목 스캔 중..."):
            df_f, _ = get_ranking_data(u_favs, new_k, allocated_per_stock, new_gap, new_sl, new_rr)
        if not df_f.empty:
            f_sel = st.dataframe(df_f[['티커', '종목명', '상태', '접근율', '현재가', '등락률', '매수타점', '권장수량', '추천점수', '엔진판단']], on_select="rerun", selection_mode="single-row", use_container_width=True, hide_index=True, height=300)
            f_idx = f_sel.selection.rows[0] if f_sel and f_sel.selection.rows else 0
            f_row = df_f.iloc[f_idx]; f_foc = f_row['티커']
            st.divider()
            
            c_ft, c_fb1, c_fb2, c_fg = st.columns([3, 1, 1, 4])
            blink_class = "blink-red" if f_row['상승여부'] else "blink-blue"
            with c_ft: st.markdown(f"<h3 style='margin:0;'>🔍 {f_row['종목명']} <span class='{blink_class}' style='font-size:20px; margin-left:10px;'>${f_row['현재가_수치']:.2f} ({f_row['등락률']})</span></h3>", unsafe_allow_html=True)
            with c_fb1:
                if st.button("❌ 관심 해제", key=f"fb1_{f_foc}"): u_favs.remove(f_foc); sync_and_save(); st.rerun()
            with c_fb2:
                if st.button("🎮 가상 매수", key=f"fb2_{f_foc}", type="primary"):
                    if f_row['권장수량'] > 0: 
                        u_trades.append({"티커":f_foc, "종목명":f_row['종목명'], "진입가":f_row['현재가_수치'], "수량":f_row['권장수량'], "목표가":f_row['익절가격'], "손절가":f_row['손절가격'], "Bailout":f_row['Bailout'], "진입시간":datetime.now().strftime("%m-%d %H:%M")})
                        sync_and_save(); st.success("체결됨!")
                    else: st.error("조건 미달")
            st.plotly_chart(draw_chart(f_row), use_container_width=True, key=f"c2_{f_foc}", config={'displayModeBar': False})
    else: st.info("사이드바에서 종목을 추가하십시오.")

# ----------------- TAB 3: 모의투자 & 명예의 전당 -----------------
with tab3:
    st.subheader("🎮 내 모의투자 계좌")
    if u_trades:
        pdf = pd.DataFrame(u_trades)
        for t in pdf['티커'].unique():
            try: pdf.loc[pdf['티커']==t, '현재'] = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
            except: pdf.loc[pdf['티커']==t, '현재'] = 0
        pdf['수익($)'] = (pdf['현재'] - pdf['진입가']) * pdf['수량']
        pdf['수익률(%)'] = ((pdf['현재'] - pdf['진입가']) / pdf['진입가']) * 100
        pnl = pdf['수익($)'].sum()
        my_total_invested = (pdf['진입가']*pdf['수량']).sum()
        my_total_pct = (pnl/my_total_invested)*100 if my_total_invested > 0 else 0
        pnl_c = "#ef5350" if pnl >= 0 else "#42a5f5"
        
        st.markdown(f"<div style='background:{card_bg}; padding:15px; border-radius:10px; text-align:center;'><div style='font-size:24px; font-weight:900; color:{pnl_c};'>내 총 수익: ${pnl:,.2f} ({my_total_pct:.2f}%)</div></div>", unsafe_allow_html=True)
        st.dataframe(pdf, column_config={"수익률(%)":st.column_config.ProgressColumn("수익률", format="%.2f%%", min_value=-10, max_value=10)}, use_container_width=True, hide_index=True)
        if st.button("🗑️ 전체 리셋 (내 계좌만)"): u_trades.clear(); sync_and_save(); st.rerun()
    else: st.info("보유 중인 모의투자 종목이 없습니다.")

    st.divider()
    
    st.subheader("🏆 퀀트 리그 (명예의 전당)")
    all_users = st.session_state.full_db.get("users", {})
    leaderboard = []
    
    for uname, udata in all_users.items():
        trds = udata.get("paper_trades", [])
        if not trds: continue
        
        u_pnl = 0
        u_invested = 0
        for trd in trds:
            try:
                curr_price = yf.Ticker(trd["티커"]).history(period="1d")['Close'].iloc[-1]
                u_pnl += (curr_price - trd["진입가"]) * trd["수량"]
                u_invested += trd["진입가"] * trd["수량"]
            except: pass
            
        u_pct = (u_pnl / u_invested) * 100 if u_invested > 0 else 0
        leaderboard.append({"트레이더": uname, "총 수익금": u_pnl, "수익률": u_pct})

    if leaderboard:
        # [수정] 지난 버전의 KeyError 버그 완벽 해결
        ldf = pd.DataFrame(leaderboard).sort_values(by="총 수익금", ascending=False).reset_index(drop=True)
        ldf.index = ldf.index + 1
        st.dataframe(ldf, column_config={"총 수익금": st.column_config.NumberColumn("수익금($)", format="$%.2f"), "수익률": st.column_config.NumberColumn("수익률(%)", format="%.2f%%")}, use_container_width=True)
    else:
        st.info("아직 투자 기록이 등록된 트레이더가 없습니다.")

st.divider()

# 스무스 싱크용 히든 버튼 & 60초 생존 신고(하트비트) 발송
st.button("refresh", key="auto_refresh", help="hidden_refresh")
st.markdown("""<style>div[data-testid="stButton"]:has(button[title="hidden_refresh"]) { display: none !important; }</style>""", unsafe_allow_html=True)
timer_js = f"""<script>let t = 60; setInterval(() => {{ t--; if(t<=0) {{ t=60; const btn = window.parent.document.querySelector('button[title="hidden_refresh"]'); if(btn) btn.click(); }} }}, 1000);</script>"""
components.html(timer_js, height=0)

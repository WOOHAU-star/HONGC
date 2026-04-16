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

# ==========================================
# 1. 영구 저장소 (Local JSON Database) 세팅
# ==========================================
DB_FILE = "apex_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"favorites": [], "paper_trades": []}

def save_db():
    data = {
        "favorites": st.session_state.favorites,
        "paper_trades": st.session_state.paper_trades
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 2. 테마 및 UI 스타일 세팅
# ==========================================
st.set_page_config(page_title="APEX V41.0 - Crash Proof", layout="wide", page_icon="⚖️")

if 'db_loaded' not in st.session_state:
    db_data = load_db()
    st.session_state.favorites = db_data.get("favorites", [])
    st.session_state.paper_trades = db_data.get("paper_trades", [])
    st.session_state.db_loaded = True
if 'theme' not in st.session_state: st.session_state.theme = "Night (Dark)"

with st.sidebar:
    st.header("🎨 환경 설정")
    theme_choice = st.radio("배경 모드", ["Night (Dark)", "Light (White)"], index=0 if st.session_state.theme == "Night (Dark)" else 1)
    st.session_state.theme = theme_choice
    st.divider()

bg_color = "#0f172a" if theme_choice == "Night (Dark)" else "#f8fafc"
text_color = "#f8fafc" if theme_choice == "Night (Dark)" else "#1e293b"
card_bg = "rgba(30, 41, 59, 0.8)" if theme_choice == "Night (Dark)" else "#ffffff"
border_color = "rgba(148, 163, 184, 0.2)" if theme_choice == "Night (Dark)" else "rgba(0, 0, 0, 0.1)"
accent_text = "#60a5fa" if theme_choice == "Night (Dark)" else "#2563eb"
muted_text = "#94a3b8" if theme_choice == "Night (Dark)" else "#64748b"

st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  {{ font-family: 'Pretendard', sans-serif !important; }}
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .rank-box {{ padding: 15px; margin-bottom: 15px; border-radius: 8px; border: 1px solid {border_color}; background: {card_bg}; color: {text_color}; }}
    .rank-1 {{ border-top: 4px solid #3b82f6; }}
    .rank-2 {{ border-top: 4px solid #64748b; }}
    .rank-3 {{ border-top: 4px solid #94a3b8; }}
    @keyframes neon {{
        0% {{ text-shadow: 0 0 5px #fff, 0 0 10px #00e676, 0 0 20px #00e676; color: #fff; border-color: #00e676; }}
        100% {{ text-shadow: 0 0 2px #fff, 0 0 5px #00e676, 0 0 10px #00e676; color: #b9fbc0; border-color: #b9fbc0; }}
    }}
    .neon-box {{ padding: 15px; border-radius: 8px; background: rgba(0,0,0,0.6); border: 2px solid #00e676; text-align: center; animation: neon 1.5s infinite alternate; font-size: 18px; font-weight: 800; margin-bottom: 20px; }}
    
    div[role="radiogroup"] {{ justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; background: transparent; border: none; }}
    @keyframes ticker {{ 0% {{ transform: translateX(50%); }} 100% {{ transform: translateX(-150%); }} }}
    .ticker-wrap {{ width: 100%; overflow: hidden; background: transparent; padding: 5px 0; margin-top: 5px; margin-bottom: 15px; border: none; }}
    .ticker-move {{ display: inline-block; white-space: nowrap; animation: ticker 80s linear infinite; font-size: 14px; font-weight: 700; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 기초 데이터 엔진
# ==========================================
TICKER_DICT = {
    "AAPL": "애플", "MSFT": "마이크로소프트", "GOOGL": "구글", "AMZN": "아마존", "META": "메타", "TSLA": "테슬라", "NVDA": "엔비디아", "NFLX": "넷플릭스", "ADBE": "어도비", "CRM": "세일즈포스",
    "AMD": "AMD", "TSM": "TSMC", "ASML": "ASML", "ARM": "ARM", "SMCI": "슈퍼마이크로", "KLAC": "KLA", "SNPS": "시놉시스", "CDNS": "케이던스", "NXPI": "NXP", "MCHP": "마이크로칩",
    "RIVN": "리비안", "LCID": "루시드", "F": "포드", "GM": "GM", "NIO": "니오", "XPEV": "샤오펑", "LI": "리오토", "ALB": "앨버말", "PLUG": "플러그파워", "ENPH": "엔페이즈", "XOM": "엑슨모빌",
    "LLY": "일라이릴리", "UNH": "유나이티드헬스", "JNJ": "존슨앤존슨", "MRK": "머크", "ABBV": "애브비", "PFE": "화이자", "AMGN": "암젠", "GILD": "길리어드", "BMY": "BMS", "CVS": "CVS헬스",
    "JPM": "JP모건", "BAC": "뱅크오브아메리카", "V": "비자", "MA": "마스터카드", "PYPL": "페이팔", "SQ": "블록", "HOOD": "로빈후드", "COIN": "코인베이스", "GS": "골드만삭스", "MS": "모건스탠리",
    "CRWD": "크라우드스트라이크", "PANW": "팔로알토", "FTNT": "포티넷", "NOW": "서비스나우", "SNOW": "스노우플레이크", "PLTR": "팔란티어", "DDOG": "데이터독", "NET": "클라우드플레어", "ZS": "지스케일러", "OKTA": "옥타"
}

SECTORS = {
    "🌟 Big Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE", "CRM"],
    "💻 AI/반도체": ["AMD", "TSM", "ASML", "ARM", "SMCI", "KLAC", "SNPS", "CDNS", "NXPI", "MCHP"],
    "⚡ 전기차/에너지": ["RIVN", "LCID", "F", "GM", "NIO", "XPEV", "LI", "ALB", "PLUG", "ENPH", "XOM"],
    "🧬 바이오/헬스": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "AMGN", "GILD", "BMY", "CVS"],
    "🏦 금융/핀테크": ["JPM", "BAC", "V", "MA", "PYPL", "SQ", "HOOD", "COIN", "GS", "MS"],
    "🛡️ 보안/클라우드": ["CRWD", "PANW", "FTNT", "NOW", "SNOW", "PLTR", "DDOG", "NET", "ZS", "OKTA"]
}

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
        status, timer = "🔴 주말 휴장", f"{diff.days}일 {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    elif now_est < m_open:
        diff = m_open - now_est
        status, timer = "🟡 프리마켓", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m 남음"
    elif m_open <= now_est <= m_close:
        diff = m_close - now_est
        status, timer = "🟢 LIVE", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m 남음"
    else:
        next_open = m_open + timedelta(days=1)
        diff = next_open - now_est
        status, timer = "🔵 장 마감", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m 남음"
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S'), status, timer

# ==========================================
# 4. 사이드바 및 DB 제어
# ==========================================
with st.sidebar:
    st.header("⭐ 관심종목 관리")
    all_tickers_flat = [t for v in SECTORS.values() for t in v]
    new_favs = st.multiselect("종목 추가/제거", options=all_tickers_flat, default=st.session_state.favorites, format_func=lambda x: f"{x} ({TICKER_DICT.get(x, '')})")
    if new_favs != st.session_state.favorites:
        st.session_state.favorites = new_favs
        save_db()
    st.header("💰 자산 통제")
    total_capital = st.number_input("가용 자산 (USD)", min_value=1000, value=100000, step=5000)
    max_stocks = st.number_input("분산 종목 수", min_value=1, max_value=20, value=5)
    weight_pct = st.slider("투입 비중 (%)", 10.0, 100.0, 100.0, 5.0)
    allocated_per_stock = (total_capital / max_stocks) * (weight_pct / 100)
    st.divider()
    st.header("⚙️ 딥 필터")
    fixed_k = st.slider("K-값", 0.3, 0.8, 0.5, 0.05)
    stop_loss_pct = st.slider("칼손절 (%)", 1.0, 10.0, 4.0, 0.5)
    base_rr_ratio = st.slider("목표 손익비", 1.0, 5.0, 2.0, 0.5)
    gap_limit_pct = st.slider("갭 허용 (%)", 0.5, 5.0, 2.0, 0.1)

def toggle_favorite(ticker):
    if ticker in st.session_state.favorites: st.session_state.favorites.remove(ticker)
    else: st.session_state.favorites.append(ticker)
    save_db()

def execute_paper_trade(trade_info):
    st.session_state.paper_trades.append(trade_info)
    save_db()
    st.success("모의투자 체결!")

def reset_paper_trades():
    st.session_state.paper_trades = []
    save_db()
    st.rerun()

# ==========================================
# 5. 순수 래리 윌리엄스 엔진 (에러 완벽 차단)
# ==========================================
@st.cache_data(ttl=60) 
def get_ranking_data(tickers, k, allocated_budget, gap_limit, sl_pct, base_rr):
    results = []
    now = datetime.now()
    today_weekday = datetime.now(pytz.timezone('US/Eastern')).weekday() 
    
    # [방어막 1] 빈 깡통 생성기 (에러 방지용 기본 컬럼 세팅)
    default_columns = ["티커", "종목명", "현재가", "매수타점", "접근율", "적용R/R", "익절가격", "손절가격", "Bailout", "권장수량", "추천점수", "엔진판단"]
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d")
            if df.empty or len(df) < 25: continue
            
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            atr_14 = df[['H-L', 'H-PC', 'L-PC']].max(axis=1).rolling(14).mean().iloc[-1]
            df['Highest_22'] = df['Close'].rolling(22).max()
            df['VIX_Fix'] = (df['Highest_22'] - df['Low']) / df['Highest_22'].replace(0,1) * 100
            
            yest, today = df.iloc[-2], df.iloc[-1]
            current = today['Close']
            ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
            
            p_range = yest['High'] - yest['Low']
            target = today['Open'] + (p_range * k)
            
            atr_pct = (atr_14 / current) * 100
            dynamic_rr = base_rr * 1.5 if atr_pct >= 4.0 else (base_rr * 0.8 if atr_pct <= 2.0 else base_rr)
            
            stop_loss = target * (1 - (sl_pct / 100))
            take_profit = target + ((target - stop_loss) * dynamic_rr)
            gap_pct = ((today['Open'] - yest['Close']) / yest['Close']) * 100
            
            is_gap_danger = gap_pct >= gap_limit
            is_bull = today['Open'] > ma5
            is_hit = current >= target
            is_chasing = current > (target * 1.015) # 추격매수 금지
            
            if is_bull and not is_hit and not is_gap_danger: dist_str = f"{((target - current) / current) * 100:.1f}%"
            elif is_hit and not is_chasing and not is_gap_danger: dist_str = "✔️진입가능"
            elif is_chasing: dist_str = "🚀초과(관망)"
            else: dist_str = "-"

            is_nr4 = yest['High'] - yest['Low'] <= (df['High'].iloc[-5:-1] - df['Low'].iloc[-5:-1]).min()
            is_oops = (today['Open'] < yest['Low']) and (current > yest['Low'])
            is_will_hook = (df.iloc[-3]['%R'] <= -80) and (-100 * (df['High'].rolling(14).max().iloc[-2] - df['Close'].iloc

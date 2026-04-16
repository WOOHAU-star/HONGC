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
st.set_page_config(page_title="APEX V33.0 - Ticker Tape", layout="wide", page_icon="⚖️")

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
    div[role="radiogroup"] {{ justify-content: center; flex-wrap: wrap; gap: 10px; background: {card_bg}; padding: 10px; border-radius: 12px; border: 1px solid {border_color}; margin-bottom: 15px; }}
    
    /* 가로 스크롤 전광판 (Ticker Tape) 애니메이션 */
    @keyframes ticker {{
        0% {{ transform: translate3d(0, 0, 0); }}
        100% {{ transform: translate3d(-100%, 0, 0); }}
    }}
    .ticker-wrap {{
        width: 100%; overflow: hidden; box-sizing: border-box;
        margin-top: 8px; padding-top: 8px; border-top: 1px solid {border_color};
    }}
    .ticker-move {{
        display: inline-block; white-space: nowrap; padding-left: 100%;
        animation: ticker 15s linear infinite;
    }}
    </style>
""", unsafe_allow_html=True)

# 45초 실질 자동 새로고침 타이머
timer_html = f"""
<div id="countdown-timer" style="font-family: 'Pretendard', sans-serif; font-size:13px; font-weight:600; color:#4ade80; text-align:right;">45초 후 갱신 ⏳</div>
<script>
    let timeLeft = 45;
    setInterval(function() {{
        timeLeft -= 1;
        if(timeLeft <= 0) {{
            timeLeft = 45;
            window.parent.location.reload(); // 0초 시 브라우저 강제 새로고침
        }}
        let el = document.getElementById("countdown-timer");
        if(el) {{ el.innerHTML = timeLeft + "초 후 갱신 ⏳"; }}
    }}, 1000);
</script>
"""

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

@st.cache_data(ttl=45)
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
        status, timer = "🔴 주말 휴장", f"월요일 오픈까지 {diff.days}일 {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    elif now_est < m_open:
        diff = m_open - now_est
        status, timer = "🟡 프리마켓", f"오픈까지 {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    elif m_open <= now_est <= m_close:
        diff = m_close - now_est
        status, timer = "🟢 정규장 (LIVE)", f"마감까지 {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    else:
        next_open = m_open + timedelta(days=1)
        diff = next_open - now_est
        status, timer = "🔵 장 마감", f"내일 오픈까지 {diff.seconds//3600}h {(diff.seconds//60)%60}m"
        
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'), status, timer

# ==========================================
# 4. 사이드바 세팅 및 DB 동기화
# ==========================================
with st.sidebar:
    st.header("⭐ 내 관심종목 관리")
    all_tickers_flat = [t for v in SECTORS.values() for t in v]
    
    new_favs = st.multiselect(
        "관심종목 핀셋 추가/제거", 
        options=all_tickers_flat, 
        default=st.session_state.favorites,
        format_func=lambda x: f"{x} ({TICKER_DICT.get(x, '')})"
    )
    if new_favs != st.session_state.favorites:
        st.session_state.favorites = new_favs
        save_db()

    st.header("💰 자산 통제 (Risk)")
    total_capital = st.number_input("가용 자산 (USD)", min_value=1000, value=100000, step=5000)
    max_stocks = st.number_input("분산 종목 수", min_value=1, max_value=20, value=5)
    weight_pct = st.slider("투입 비중 (%)", 10.0, 100.0, 100.0, 5.0)
    allocated_per_stock = (total_capital / max_stocks) * (weight_pct / 100)
    
    st.divider()
    st.header("⚙️ 래리 윌리엄스 딥 필터")
    fixed_k = st.slider("K-값 (변동성 돌파)", 0.3, 0.8, 0.5, 0.05)
    stop_loss_pct = st.slider("칼손절 폭 (%)", 1.0, 10.0, 4.0, 0.5)
    base_rr_ratio = st.slider("목표 손익비 (R/R)", 1.0, 5.0, 2.0, 0.5)
    gap_limit_pct = st.slider("프리마켓 갭 허용 (%)", 0.5, 5.0, 2.0, 0.1)

def toggle_favorite(ticker):
    if ticker in st.session_state.favorites: st.session_state.favorites.remove(ticker)
    else: st.session_state.favorites.append(ticker)
    save_db()

def execute_paper_trade(trade_info):
    st.session_state.paper_trades.append(trade_info)
    save_db()
    st.success("모의투자 체결 완료! (DB 저장됨)")

def reset_paper_trades():
    st.session_state.paper_trades = []
    save_db()
    st.rerun()

# ==========================================
# 5. 순수 래리 윌리엄스 엔진
# ==========================================
@st.cache_data(ttl=45) 
def get_ranking_data(tickers, k, allocated_budget, gap_limit, sl_pct, base_rr):
    results = []
    now = datetime.now()
    today_weekday = datetime.now(pytz.timezone('US/Eastern')).weekday() 
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d")
            if df.empty or len(df) < 25: continue
            
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            atr_14 = df[['H-L', 'H-PC', 'L-PC']].max(axis=1).rolling(14).mean().iloc[-1]
            
            df['High_14'] = df['High'].rolling(14).max()
            df['Low_14'] = df['Low'].rolling(14).min()
            df['%R'] = -100 * (df['High_14'] - df['Close']) / (df['High_14'] - df['Low_14']).replace(0, 1)
            
            df['Highest_22'] = df['Close'].rolling(22).max()
            df['VIX_Fix'] = (df['Highest_22'] - df['Low']) / df['Highest_22'].replace(0,1) * 100
            
            yest2 = df.iloc[-3]
            yest, today = df.iloc[-2], df.iloc[-1]
            current = today['Close']
            ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
            
            p_range = yest['High'] - yest['Low']
            target = today['Open'] + (p_range * k)
            
            atr_pct = (atr_14 / current) * 100
            dynamic_rr = base_rr * 1.5 if atr_pct >= 4.0 else (base_rr * 0.8 if atr_pct <= 2.0 else base_rr)
            
            stop_loss = target * (1 - (sl_pct / 100))
            take_profit = target + ((target - stop_loss) * dynamic_rr)
            bailout_price = target + 0.01 
            
            gap_pct = ((today['Open'] - yest['Close']) / yest['Close']) * 100
            is_gap_danger = gap_pct >= gap_limit
            is_bull = today['Open'] > ma5
            is_hit = current >= target
            
            if is_bull and not is_hit and not is_gap_danger: dist_str = f"{((target - current) / current) * 100:.1f}%"
            elif is_hit and not is_gap_danger: dist_str = "✔️돌파"
            else: dist_str = "-"

            is_nr4 = yest['High'] - yest['Low'] <= (df['High'].iloc[-5:-1] - df['Low'].iloc[-5:-1]).min()
            is_oops = (today['Open'] < yest['Low']) and (current > yest['Low'])
            is_will_hook = (yest2['%R'] <= -80) and (yest['%R'] > yest2['%R'])
            is_vix_fix_bottom = df['VIX_Fix'].iloc[-1] >= 12.0 

            is_earnings_danger = False
            if is_bull and (is_hit or ((target - current) / current * 100 < 3.0)):
                try:
                    cal = stock.calendar
                    if isinstance(cal, dict) and 'Earnings Date' in cal and len(cal['Earnings Date']) > 0:
                        e_date = cal['Earnings Date'][0]
                        if isinstance(e_date, datetime) and 0 <= (e_date.date() - now.date()).days <= 7:
                            is_earnings_danger = True
                except: pass

            score = 0; reasons = []
            
            if today_weekday in [1, 2]: score += 15; reasons.append("화/수")
            elif today_weekday == 4: score -= 10; reasons.append("금요")
            
            if is_earnings_danger: score -= 200; reasons.append("⚠️실적")
            elif is_gap_danger: score -= 100; reasons.append("🚫갭")
            elif not is_bull: score -= 50; reasons.append("📉역배열")
            else:
                score += 10; reasons.append("✅5MA")
                if is_hit: score += 50; reasons.append("🔥돌파")
                if is_nr4: score += 20; reasons.append("⚡NR4")
                if is_oops: score += 25; reasons.append("🔄OOPS")
                if is_will_hook: score += 15; reasons.append("🎣%R")
                if is_vix_fix_bottom: score += 30; reasons.append("🥶VIX")

            kor_name = TICKER_DICT.get(ticker, "")
            display_name = f"{ticker} ({kor_name})" if kor_name else ticker

            results.append({
                "티커": ticker, "종목명": display_name, "현재가": current, "매수타점": target,
                "접근율": dist_str, "적용R/R": dynamic_rr, "익절가격": take_profit, "손절가격": stop_loss, "Bailout": bailout_price,
                "권장수량": int(allocated_budget / target) if is_bull and not is_gap_danger and not is_earnings_danger else 0,
                "추천점수": score, "엔진판단": " ".join(reasons)
            })
        except: continue
        
    df_res = pd.DataFrame(results)
    if df_res.empty: return df_res, []

    df_res = df_res.sort_values(by="추천점수", ascending=False).reset_index(drop=True)
    top_picks = [row for _, row in df_res.iterrows() if row['추천점수'] > 0][:3]
            
    return df_res, top_picks

def draw_chart(row_info):
    ticker = row_info['티커']
    df_chart = yf.Ticker(ticker).history(period="1mo")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
    fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="Price"), row=1, col=1)
    
    tp_val, tg_val, sl_val = row_info['익절가격'], row_info['매수타점'], row_info['손절가격']
    bo_val = row_info['Bailout']
    
    fig.add_hline(y=tp_val, line_dash="solid", line_color="#3b82f6", line_width=1.5, annotation_text=f"TP: ${tp_val:.2f}", annotation_position="top right", row=1, col=1)
    fig.add_hline(y=tg_val, line_dash="dash", line_color="#4ade80", line_width=1.5, annotation_text=f"Target: ${tg_val:.2f}", annotation_position="top right", row=1, col=1)
    fig.add_hline(y=bo_val, line_dash="dot", line_color="#eab308", line_width=1.0, annotation_text=f"Bailout: ${bo_val:.2f}", annotation_position="bottom right", row=1, col=1)
    fig.add_hline(y=sl_val, line_dash="solid", line_color="#f87171", line_width=1.5, annotation_text=f"SL: ${sl_val:.2f}", annotation_position="bottom right", row=1, col=1)
    
    colors = ['#4ade80' if r['Close'] >= r['Open'] else '#f87171' for i, r in df_chart.iterrows()]
    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=colors, name="Volume"), row=2, col=1)
    
    fig.update_xaxes(rangeslider_visible=False, fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    
    t_style = "plotly_dark" if st.session_state.theme == "Night (Dark)" else "plotly_white"
    fig.update_layout(
        template=t_style, height=450, margin=dict(l=0,r=40,t=20,b=0), 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
        dragmode=False 
    )
    return fig

# ==========================================
# 6. UI 렌더링 (전광판 Ticker Tape 변환)
# ==========================================
kor_time, m_status, m_timer = get_market_time()
indices = get_macro_indices()

# Ticker Tape (가로 스크롤링) HTML 생성
ticker_items = []
for name, data in indices.items():
    c_color = "#4ade80" if data['pct'] >= 0 else "#f87171"
    sign = "+" if data['pct'] >= 0 else ""
    ticker_items.append(f"<span style='font-size:14px; color:{muted_text}; margin-left:40px;'>{name}</span> <span style='font-size:16px; font-weight:800; color:{text_color};'>{data['price']:,.1f}</span> <span style='font-size:14px; font-weight:700; color:{c_color};'>({sign}{data['pct']:.2f}%)</span>")
ticker_html = "".join(ticker_items)

# 초미니멀 상단 헤더 패널
st.markdown(f"""
<div style='display:flex; flex-direction:column; background:{card_bg}; padding:10px 12px; border-radius:8px; border:1px solid {border_color}; margin-bottom:15px;'>
    <div style='display:flex; justify-content:space-between; align-items:center;'>
        <div style='font-size:13px; font-weight:600; color:{text_color};'>KOR: <span style='color:{accent_text};'>{kor_time.split(' ')[1]}</span></div>
        <div style='font-size:13px; font-weight:600; color:{text_color};'>{m_status} <span style='color:{muted_text}; font-size:11px;'>({m_timer})</span></div>
        <div style='font-size:12px; font-weight:600; color:#4ade80;'>{timer_html}</div>
    </div>
    <div class="ticker-wrap">
        <div class="ticker-move">
            {ticker_html}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

selected_sector = st.radio("🔭 스캔 섹터", list(SECTORS.keys()), horizontal=True, label_visibility="collapsed")
final_tickers = SECTORS[selected_sector]

tab1, tab2, tab3 = st.tabs(["📊 섹터 전체 스캔", "⭐ 내 관심종목 컬렉션", "🎮 모의투자 랩실"])

# ----------------- TAB 1: 관제탑 -----------------
with tab1:
    if final_tickers:
        with st.spinner(f"[{selected_sector}] 래리 윌리엄스 딥 필터 작동 중..."):
            df_all, top_picks = get_ranking_data(final_tickers, fixed_k, allocated_per_stock, gap_limit_pct, stop_loss_pct, base_rr_ratio)
        
        st.subheader("💡 결단 보조 지표 (Top 3 Pick)")
        if top_picks:
            cols = st.columns(3)
            for i, row in enumerate(top_picks):
                with cols[i]:
                    st.markdown(f"""
                        <div class="rank-box rank-{i+1}">
                            <div style="font-size:16px; font-weight:800; margin-bottom:8px; color:{text_color};">
                                {row['종목명']} <span style="font-size:13px; color:{muted_text}; font-weight:500;">(점수: {row['추천점수']})</span>
                            </div>
                            <div style="font-size:14px; line-height:1.7; color:{text_color};">
                                🎯 진입: <b>${row['매수타점']:.2f}</b> (현재 ${row['현재가']:.2f})<br/>
                                💰 목표: ${row['익절가격']:.2f} <span style="font-size:12px; color:{accent_text};">(R/R 1:{row['적용R/R']:.1f})</span><br/>
                                ⏱️ 시간청산: ${row['Bailout']:.2f} <span style="font-size:12px; color:#eab308;">(미결판시)</span><br/>
                                🔪 손절: ${row['손절가격']:.2f}<br/>
                                🛒 수량: {row['권장수량']}주<br/>
                                🔍 근거: <span style="color:#eab308; font-weight:bold;">{row['엔진판단']}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else: st.info("상승장 및 타점 조건을 완벽히 충족하는 종목이 없습니다.")

        reached_targets = [p for p in top_picks if "🔥" in p['엔진판단']]
        if reached_targets:
            for row in reached_targets:
                st.markdown(f"""<div class="neon-box">📌 타점 도달: {row['종목명']} 종목이 타점을 돌파했습니다. (진입가: ${row['현재가']:.2f})</div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("📋 전체 스캔 리포트 (클릭 시 하단 차트 연동)")
        
        df_display = df_all[['티커', '종목명', '접근율', '현재가', '매수타점', '권장수량', '추천점수', '엔진판단']].copy()
        
        selection_event = st.dataframe(
            df_display,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "티커": None, 
                "종목명": st.column_config.TextColumn("종목(Name)", width="small"),
                "접근율": st.column_config.TextColumn("접근율", width="small"),
                "현재가": st.column_config.NumberColumn("현재가", format="$%.2f", width="small"),
                "매수타점": st.column_config.NumberColumn("타점", format="$%.2f", width="small"),
                "권장수량": st.column_config.NumberColumn("수량", format="%d주", width="small"),
                "추천점수": st.column_config.NumberColumn("점수", width="small"),
                "엔진판단": st.column_config.TextColumn("엔진근거", width="large")
            },
            use_container_width=True, hide_index=True, height=350
        )

        selected_idx = selection_event.selection.rows[0] if selection_event and len(selection_event.selection.rows) > 0 else 0
        
        if not df_all.empty:
            row_info = df_all.iloc[selected_idx]
            focus_ticker = row_info['티커']
            is_fav = focus_ticker in st.session_state.favorites
            
            st.divider()
            c_title, c_btn1, c_btn2, c_gap = st.columns([3, 1, 1, 4])
            with c_title: st.subheader(f"🔍 정밀 차트 및 작전 제어: {row_info['종목명']}")
            with c_btn1:
                if st.button("⭐ 관심 해제" if is_fav else "☆ 관심 추가", use_container_width=True, key=f"btn_fav_1_{focus_ticker}"):
                    toggle_favorite(focus_ticker)
                    st.rerun()
            with c_btn2:
                if st.button("🎮 가상 매수", type="primary", use_container_width=True, key=f"btn_buy_1_{focus_ticker}"):
                    if row_info['권장수량'] > 0:
                        execute_paper_trade({
                            "티커": row_info['티커'], "종목명": row_info['종목명'], "진입가": row_info['현재가'],
                            "수량": row_info['권장수량'], "목표가": row_info['익절가격'], "손절가": row_info['손절가격'], "Bailout": row_info['Bailout'],
                            "진입시간": datetime.now(pytz.timezone('Asia/Seoul')).strftime("%m-%d %H:%M")
                        })
                    else: st.error("매수 조건 미달.")
            
            st.plotly_chart(draw_chart(row_info), use_container_width=True, key=f"main_chart_{focus_ticker}", config={'scrollZoom': False, 'displayModeBar': False})

# ----------------- TAB 2: 내 관심종목 -----------------
with tab2:
    if st.session_state.favorites:
        with st.spinner("관심종목 딥 스캔 중..."):
            df_fav, fav_top_picks = get_ranking_data(st.session_state.favorites, fixed_k, allocated_per_stock, gap_limit_pct, stop_loss_pct, base_rr_ratio)
        
        st.subheader("⭐ 관심종목 스캔 리포트")
        df_fav_display = df_fav[['티커', '종목명', '접근율', '현재가', '매수타점', '권장수량', '추천점수', '엔진판단']].copy()
        
        fav_selection = st.dataframe(
            df_fav_display,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "티커": None,
                "종목명": st.column_config.TextColumn("종목(Name)", width="small"),
                "접근율": st.column_config.TextColumn("접근율", width="small"),
                "현재가": st.column_config.NumberColumn("현재가", format="$%.2f", width="small"),
                "매수타점": st.column_config.NumberColumn("타점", format="$%.2f", width="small"),
                "권장수량": st.column_config.NumberColumn("수량", format="%d주", width="small"),
                "추천점수": st.column_config.NumberColumn("점수", width="small"),
                "엔진판단": st.column_config.TextColumn("엔진근거", width="large")
            }, use_container_width=True, hide_index=True, height=300
        )

        st.divider()

        fav_idx = fav_selection.selection.rows[0] if fav_selection and len(fav_selection.selection.rows) > 0 else 0
        
        if not df_fav.empty:
            fav_info = df_fav.iloc[fav_idx]
            fav_ticker = fav_info['티커']
            
            c_title, c_btn1, c_btn2, c_gap = st.columns([3, 1, 1, 4])
            with c_title: st.subheader(f"🔍 관심종목 정밀 차트: {fav_info['종목명']}")
            with c_btn1:
                if st.button("❌ 관심 해제", use_container_width=True, key=f"btn_fav_2_{fav_ticker}"):
                    toggle_favorite(fav_ticker)
                    st.rerun()
            with c_btn2:
                if st.button("🎮 가상 매수", type="primary", use_container_width=True, key=f"btn_buy_2_{fav_ticker}"):
                    if fav_info['권장수량'] > 0:
                        execute_paper_trade({
                            "티커": fav_info['티커'], "종목명": fav_info['종목명'], "진입가": fav_info['현재가'],
                            "수량": fav_info['권장수량'], "목표가": fav_info['익절가격'], "손절가": fav_info['손절가격'], "Bailout": fav_info['Bailout'],
                            "진입시간": datetime.now(pytz.timezone('Asia/Seoul')).strftime("%m-%d %H:%M")
                        })
                    else: st.error("매수 조건 미달.")
            
            st.plotly_chart(draw_chart(fav_info), use_container_width=True, key=f"fav_chart_{fav_ticker}", config={'scrollZoom': False, 'displayModeBar': False})
    else:
        st.info("⭐ 스캔 리포트에서 차트 위 '☆ 관심 추가' 버튼을 눌러주십시오.")

# ----------------- TAB 3: 모의투자 -----------------
with tab3:
    st.subheader("🎮 껄무새 방지소 (Paper Trading Lab)")
    
    if st.session_state.paper_trades:
        paper_df = pd.DataFrame(st.session_state.paper_trades)
        
        with st.spinner("실시간 수익률 계산 중..."):
            live_prices = {}
            for t in paper_df['티커'].unique():
                try:
                    df_live = yf.Ticker(t).history(period="1d")
                    live_prices[t] = df_live['Close'].iloc[-1]
                except: live_prices[t] = 0
                
        paper_df['현재가'] = paper_df['티커'].map(live_prices)
        paper_df['수익금($)'] = (paper_df['현재가'] - paper_df['진입가']) * paper_df['수량']
        paper_df['수익률(%)'] = ((paper_df['현재가'] - paper_df['진입가']) / paper_df['진입가']) * 100
        
        total_pnl = paper_df['수익금($)'].sum()
        total_invested = (paper_df['진입가'] * paper_df['수량']).sum()
        total_yield = (total_pnl / total_invested) * 100 if total_invested > 0 else 0
        
        pnl_color = "#4ade80" if total_pnl >= 0 else "#f87171"
        st.markdown(f"""
            <div style="background-color:{card_bg}; padding:15px; border-radius:10px; border:1px solid {border_color}; margin-bottom:20px; text-align:center;">
                <div style="font-size:14px; color:{muted_text}; font-weight:bold;">총 가상 수익금</div>
                <div style="font-size:28px; font-weight:900; color:{pnl_color};">${total_pnl:,.2f} ({total_yield:,.2f}%)</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.dataframe(
            paper_df,
            column_config={
                "진입시간": st.column_config.TextColumn("시간", width="small"),
                "종목명": st.column_config.TextColumn("종목", width="small"),
                "진입가": st.column_config.NumberColumn("진입", format="$%.2f", width="small"),
                "현재가": st.column_config.NumberColumn("현재", format="$%.2f", width="small"),
                "수량": st.column_config.NumberColumn("수량", format="%d주", width="small"),
                "수익금($)": st.column_config.NumberColumn("수익금", format="$%.2f", width="small"),
                "수익률(%)": st.column_config.ProgressColumn("수익률(%)", format="%.2f%%", min_value=-10, max_value=10, width="medium")
            }, use_container_width=True, hide_index=True
        )
        
        if st.button("🗑️ 모의투자 리셋"):
            reset_paper_trades()
    else: st.info("비어 있습니다. 관제탑에서 [🎮 가상 매수] 버튼을 누르십시오.")

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
st.set_page_config(page_title="APEX V38.0 - X-Ray Chart", layout="wide", page_icon="⚖️")

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
        0% {{ text-shadow: 0 0 5px #fff, 0 0 10px #ef5350, 0 0 20px #ef5350; color: #fff; border-color: #ef5350; }}
        100% {{ text-shadow: 0 0 2px #fff, 0 0 5px #ef5350, 0 0 10px #ef5350; color: #ffcdd2; border-color: #ffcdd2; }}
    }}
    .neon-box {{ padding: 15px; border-radius: 8px; background: rgba(0,0,0,0.6); border: 2px solid #ef5350; text-align: center; animation: neon 1.5s infinite alternate; font-size: 18px; font-weight: 800; margin-bottom: 20px; }}
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
        status, timer = "🟡 프리마켓", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m"
    elif m_open <= now_est <= m_close:
        diff = m_close - now_est
        status, timer = "🟢 LIVE", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m"
    else:
        next_open = m_open + timedelta(days=1)
        diff = next_open - now_est
        status, timer = "🔵 장 마감", f"{(diff.seconds//3600)}h {(diff.seconds//60)%60}m"
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
# 5. 순수 래리 윌리엄스 엔진
# ==========================================
@st.cache_data(ttl=60) 
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
            df['Highest_22'] = df['Close'].rolling(22).max()
            df['VIX_Fix'] = (df['Highest_22'] - df['Low']) / df['Highest_22'].replace(0,1) * 100
            yest, today = df.iloc[-2], df.iloc[-1]
            current = today['Close']
            ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
            p_range = yest['High'] - yest['Low']
            target = today['Open'] + (p_range * k)
            dynamic_rr = base_rr * 1.5 if (atr_14/current)*100 >= 4.0 else (base_rr * 0.8 if (atr_14/current)*100 <= 2.0 else base_rr)
            stop_loss = target * (1 - (sl_pct / 100))
            take_profit = target + ((target - stop_loss) * dynamic_rr)
            gap_pct = ((today['Open'] - yest['Close']) / yest['Close']) * 100
            is_gap_danger = gap_pct >= gap_limit
            is_bull = today['Open'] > ma5
            is_hit = current >= target
            dist_str = f"{((target - current) / current) * 100:.1f}%" if is_bull and not is_hit and not is_gap_danger else ("✔️돌파" if is_hit and not is_gap_danger else "-")
            score = 0; reasons = []
            if today_weekday in [1, 2]: score += 15; reasons.append("화/수")
            if is_gap_danger: score -= 100; reasons.append("🚫갭")
            elif not is_bull: score -= 50; reasons.append("📉역배")
            else:
                score += 10; reasons.append("✅5MA")
                if is_hit: score += 50; reasons.append("🔥돌파")
                if df['VIX_Fix'].iloc[-1] >= 12.0: score += 30; reasons.append("🥶VIX")
            results.append({
                "티커": ticker, "종목명": f"{ticker} ({TICKER_DICT.get(ticker, '')})", "현재가": current, "매수타점": target,
                "접근율": dist_str, "적용R/R": dynamic_rr, "익절가격": take_profit, "손절가격": stop_loss, "Bailout": target + 0.01,
                "권장수량": int(allocated_budget / target) if is_bull and not is_gap_danger else 0,
                "추천점수": score, "엔진판단": " ".join(reasons)
            })
        except: continue
    df_res = pd.DataFrame(results)
    if df_res.empty: return df_res, []
    df_res = df_res.sort_values(by="추천점수", ascending=False).reset_index(drop=True)
    return df_res, [row for _, row in df_res.iterrows() if row['추천점수'] > 0][:3]

def draw_chart(row_info):
    df_chart = yf.Ticker(row_info['티커']).history(period="1mo")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
    
    # [수정] 1. 한국형 색상 코드 (상승=빨강 #ef5350, 하락=파랑 #42a5f5)
    up_col = '#ef5350'
    dn_col = '#42a5f5'
    
    fig.add_trace(go.Candlestick(
        x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], 
        name="Price",
        increasing_line_color=up_col, increasing_fillcolor=up_col,
        decreasing_line_color=dn_col, decreasing_fillcolor=dn_col
    ), row=1, col=1)
    
    # [수정] 2. 매물대 투시경 (Volume Profile) - 배경에 옅게 오버레이
    prices = df_chart['Close']
    volumes = df_chart['Volume']
    bins = np.linspace(df_chart['Low'].min(), df_chart['High'].max(), 24) 
    hist, bin_edges = np.histogram(prices, bins=bins, weights=volumes)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    fig.add_trace(go.Bar(
        x=hist, y=bin_centers, orientation='h', xaxis='x3', yaxis='y',
        marker=dict(color='rgba(148, 163, 184, 0.15)', line=dict(width=0)),
        showlegend=False, hoverinfo='none'
    ))
    
    # 3. 래리 윌리엄스 4대 라인
    tp_val, tg_val, sl_val = row_info['익절가격'], row_info['매수타점'], row_info['손절가격']
    bo_val = row_info['Bailout']
    
    fig.add_hline(y=tp_val, line_dash="solid", line_color="#3b82f6", line_width=1.5, annotation_text=f"TP: ${tp_val:.2f}", annotation_position="top right", row=1, col=1)
    fig.add_hline(y=tg_val, line_dash="dash", line_color="#4ade80", line_width=1.5, annotation_text=f"Target: ${tg_val:.2f}", annotation_position="top right", row=1, col=1)
    fig.add_hline(y=bo_val, line_dash="dot", line_color="#eab308", line_width=1.0, annotation_text=f"Bailout: ${bo_val:.2f}", annotation_position="bottom right", row=1, col=1)
    fig.add_hline(y=sl_val, line_dash="solid", line_color="#ef5350", line_width=1.5, annotation_text=f"SL: ${sl_val:.2f}", annotation_position="bottom right", row=1, col=1)
    
    # [수정] 4. 거래량 막대 색상 한국화
    v_colors = [up_col if r['Close'] >= r['Open'] else dn_col for i, r in df_chart.iterrows()]
    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=v_colors, name="Volume"), row=2, col=1)
    
    fig.update_xaxes(rangeslider_visible=False, fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    
    # 매물대(xaxis3)를 차트의 1/3 지점까지만 오도록 Range 설정
    t_style = "plotly_dark" if st.session_state.theme == "Night (Dark)" else "plotly_white"
    fig.update_layout(
        xaxis3=dict(overlaying='x', side='top', showticklabels=False, range=[0, max(hist)*3]),
        template=t_style, height=450, margin=dict(l=0,r=40,t=20,b=0), 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, dragmode=False
    )
    return fig

# ==========================================
# 6. UI 렌더링
# ==========================================
k_time, m_status, m_timer = get_market_time()
indices = get_macro_indices()

col_time, col_stat = st.columns(2)
with col_time:
    st.markdown(f"<div style='padding:5px; font-weight:600; color:{text_color}; font-size:15px;'>KOR: <span style='color:{accent_text};'>{k_time}</span></div>", unsafe_allow_html=True)
with col_stat:
    st.markdown(f"<div style='padding:5px; font-weight:600; color:{text_color}; font-size:15px; text-align:right;'>{m_status} <span style='color:{muted_text}; font-size:12px;'>({m_timer})</span></div>", unsafe_allow_html=True)

ticker_items = []
for name, data in indices.items():
    color = "#ef5350" if data['pct'] >= 0 else "#42a5f5" # 한국형 컬러
    ticker_items.append(f"<span style='color:{muted_text};'>{name}</span> <b style='color:{text_color};'>{data['price']:,.0f}</b> <span style='color:{color};'>({data['pct']:+.2f}%)</span>")
single_ticker_str = "&nbsp;&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp;".join(ticker_items)
full_ticker_str = f"{single_ticker_str} &nbsp;&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp; " * 8 

st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-move">{full_ticker_str}</div>
</div>
""", unsafe_allow_html=True)

selected_sector = st.radio("🔭 섹터", list(SECTORS.keys()), horizontal=True, label_visibility="collapsed")
tab1, tab2, tab3 = st.tabs(["📊 관제탑", "⭐ 관심종목", "🎮 모의투자"])

with tab1:
    if selected_sector:
        df_all, top_picks = get_ranking_data(SECTORS[selected_sector], fixed_k, allocated_per_stock, gap_limit_pct, stop_loss_pct, base_rr_ratio)
        st.subheader("💡 Top 3 Pick")
        if top_picks:
            cols = st.columns(3)
            for i, row in enumerate(top_picks):
                with cols[i]:
                    st.markdown(f"""<div class="rank-box rank-{i+1}"><div style="font-size:15px; font-weight:800;">{row['종목명']}</div><div style="font-size:13px; line-height:1.6;">🎯 진입: <b>${row['매수타점']:.2f}</b><br/>💰 목표: ${row['익절가격']:.2f}<br/>🔍 근거: <span style="color:#eab308; font-weight:bold;">{row['엔진판단']}</span></div></div>""", unsafe_allow_html=True)
        
        reached = [p for p in top_picks if "🔥" in p['엔진판단']]
        for r in reached: st.markdown(f"""<div class="neon-box">📌 타점 도달: {r['종목명']} (진입: ${r['현재가']:.2f})</div>""", unsafe_allow_html=True)

        st.divider()
        df_disp = df_all[['티커', '종목명', '접근율', '현재가', '매수타점', '권장수량', '추천점수', '엔진판단']]
        sel = st.dataframe(df_disp, on_select="rerun", selection_mode="single-row", column_config={"티커":None, "종목명":st.column_config.TextColumn("종목", width="small"), "접근율":st.column_config.TextColumn("접근", width="small"), "현재가":st.column_config.NumberColumn("현재", format="$%.2f", width="small"), "매수타점":st.column_config.NumberColumn("타점", format="$%.2f", width="small"), "권장수량":st.column_config.NumberColumn("수량", format="%d주", width="small"), "추천점수":st.column_config.NumberColumn("점수", width="small"), "엔진판단":st.column_config.TextColumn("근거", width="medium")}, use_container_width=True, hide_index=True, height=300)
        
        idx = sel.selection.rows[0] if sel and sel.selection.rows else 0
        if not df_all.empty:
            row = df_all.iloc[idx]; focus = row['티커']; is_f = focus in st.session_state.favorites
            st.divider()
            c_t, c_b1, c_b2, c_g = st.columns([3, 1, 1, 4])
            with c_t: st.subheader(f"🔍 {row['종목명']}")
            with c_b1: 
                if st.button("⭐ 관심 해제" if is_f else "☆ 관심 추가", key=f"b1_{focus}"): toggle_favorite(focus); st.rerun()
            with c_b2:
                if st.button("🎮 가상 매수", type="primary", key=f"b2_{focus}"):
                    if row['권장수량'] > 0: execute_paper_trade({"티커":focus, "종목명":row['종목명'], "진입가":row['현재가'], "수량":row['권장수량'], "목표가":row['익절가격'], "손절가":row['손절가격'], "Bailout":row['Bailout'], "진입시간":datetime.now(pytz.timezone('Asia/Seoul')).strftime("%m-%d %H:%M")})
                    else: st.error("조건 미달")
            st.plotly_chart(draw_chart(row), use_container_width=True, key=f"c1_{focus}", config={'displayModeBar': False})

with tab2:
    if st.session_state.favorites:
        df_f, f_top = get_ranking_data(st.session_state.favorites, fixed_k, allocated_per_stock, gap_limit_pct, stop_loss_pct, base_rr_ratio)
        f_sel = st.dataframe(df_f[['티커', '종목명', '접근율', '현재가', '매수타점', '권장수량', '추천점수', '엔진판단']], on_select="rerun", selection_mode="single-row", column_config={"티커":None, "종목명":st.column_config.TextColumn("종목", width="small"), "접근율":st.column_config.TextColumn("접근", width="small"), "현재가":st.column_config.NumberColumn("현재", format="$%.2f", width="small"), "매수타점":st.column_config.NumberColumn("타점", format="$%.2f", width="small"), "권장수량":st.column_config.NumberColumn("수량", format="%d주", width="small"), "추천점수":st.column_config.NumberColumn("점수", width="small"), "엔진판단":st.column_config.TextColumn("근거", width="medium")}, use_container_width=True, hide_index=True, height=300)
        f_idx = f_sel.selection.rows[0] if f_sel and f_sel.selection.rows else 0
        if not df_f.empty:
            f_row = df_f.iloc[f_idx]; f_foc = f_row['티커']
            st.divider(); c_ft, c_fb1, c_fb2, c_fg = st.columns([3, 1, 1, 4])
            with c_ft: st.subheader(f"🔍 {f_row['종목명']}")
            with c_fb1:
                if st.button("❌ 관심 해제", key=f"fb1_{f_foc}"): st.session_state.favorites.remove(f_foc); save_db(); st.rerun()
            with c_fb2:
                if st.button("🎮 가상 매수", key=f"fb2_{f_foc}", type="primary"):
                    execute_paper_trade({"티커":f_foc, "종목명":f_row['종목명'], "진입가":f_row['현재가'], "수량":f_row['권장수량'], "목표가":f_row['익절가격'], "손절가":f_row['손절가격'], "Bailout":f_row['Bailout'], "진입시간":datetime.now().strftime("%m-%d %H:%M")})
            st.plotly_chart(draw_chart(f_row), use_container_width=True, key=f"c2_{f_foc}", config={'displayModeBar': False})
    else: st.info("관제탑에서 종목을 추가하십시오.")

with tab3:
    st.subheader("🎮 모의투자 현황 (DB 보존)")
    if st.session_state.paper_trades:
        pdf = pd.DataFrame(st.session_state.paper_trades)
        for t in pdf['티커'].unique():
            try: pdf.loc[pdf['티커']==t, '현재'] = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
            except: pdf.loc[pdf['티커']==t, '현재'] = 0
        pdf['수익($)'] = (pdf['현재'] - pdf['진입가']) * pdf['수량']
        pdf['수익률(%)'] = ((pdf['현재'] - pdf['진입가']) / pdf['진입가']) * 100
        pnl = pdf['수익($)'].sum(); pnl_c = "#ef5350" if pnl >= 0 else "#42a5f5" # 한국형 컬러
        st.markdown(f"<div style='background:{card_bg}; padding:15px; border-radius:10px; text-align:center;'><div style='font-size:24px; font-weight:900; color:{pnl_c};'>총 수익: ${pnl:,.2f} ({ (pnl/((pdf['진입가']*pdf['수량']).sum()))*100 :.2f}%)</div></div>", unsafe_allow_html=True)
        st.dataframe(pdf, column_config={"진입시간":st.column_config.TextColumn("시간", width="small"), "수익률(%)":st.column_config.ProgressColumn("수익률", format="%.2f%%", min_value=-10, max_value=10)}, use_container_width=True, hide_index=True)
        if st.button("🗑️ 리셋"): reset_paper_trades()
    else: st.info("체결된 종목이 없습니다.")

st.divider()

import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import requests
import uuid
import time

# ==========================================
# [중요] 1. 환경 설정 및 키 입력
# ==========================================
DB_FILE = "apex_database.json"

# 여기에 매니저님의 실제 키를 직접 입력하십시오 (따옴표 유지)
MY_JSONBIN_KEY = "$2a$10$sSBmd1/tjehUf48si5qOiufUBN7Ybf.r0jEwIbUukg4kh41uoUGfq"
MY_JSONBIN_ID = "69e184b9aaba88219709aa95"

# ==========================================
# 2. 딥러닝급 무결점 데이터 세탁기
# ==========================================
class TacticalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

def load_db():
    key, bin_id = MY_JSONBIN_KEY, MY_JSONBIN_ID
    db = {"users": {"Admin": {"favorites": [], "settings": {"fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0}}}}
    if key and bin_id and "입력" not in key:
        try:
            req = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}/latest", headers={"X-Master-Key": key}, timeout=5)
            if req.status_code == 200: db = req.json().get("record", db)
        except: pass
    if not db.get("users") and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: db = json.load(f)
        except: pass
    return db

def save_db(full_db):
    key, bin_id = MY_JSONBIN_KEY, MY_JSONBIN_ID
    current_u = st.session_state.get("current_user")
    if key and bin_id and current_u and "입력" not in key:
        try:
            req_get = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}/latest", headers={"X-Master-Key": key}, timeout=5)
            if req_get.status_code == 200:
                latest = req_get.json().get("record", {"users": {}})
                latest["users"][current_u] = full_db["users"][current_u]
                requests.put(f"https://api.jsonbin.io/v3/b/{bin_id}", 
                             data=json.dumps(latest, cls=TacticalEncoder), 
                             headers={"Content-Type": "application/json", "X-Master-Key": key}, timeout=5)
        except: pass
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(full_db, f, indent=4, cls=TacticalEncoder)

# ==========================================
# 3. UI 및 모바일 반응형 CSS (Mobile Responsive)
# ==========================================
st.set_page_config(page_title="APEX V61.0", layout="wide")
if 'full_db' not in st.session_state: st.session_state.full_db = load_db()

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; background-color: #0b0e14; color: #e2e8f0; }
    .stApp { background-color: #0b0e14; }
    
    /* 네온 경고창 */
    .neon-alert { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; text-align: center; color: #fca5a5; font-weight: 800; margin-bottom: 15px; font-size: 14px; }
    
    /* 모바일 반응형 정보창 (스마트폰에서 세로로 예쁘게 정렬됨) */
    .vip-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; background: #151921; padding: 15px; border-radius: 12px; border: 1px solid #232e4a; margin-top: 10px; margin-bottom: 10px; }
    .vip-title { font-size: 24px; font-weight: 900; color: #3b82f6; margin: 0; min-width: 100px; }
    .vip-data-group { display: flex; flex-wrap: wrap; gap: 15px; }
    .vip-data { text-align: center; }
    .vip-label { font-size: 11px; color: #64748b; letter-spacing: 0.5px; }
    .vip-value { font-size: 18px; font-weight: 800; }
    
    @media (max-width: 600px) {
        .vip-header { flex-direction: column; align-items: flex-start; gap: 15px; }
        .vip-data-group { justify-content: space-between; width: 100%; }
    }
    
    .ticker-wrap { width: 100%; overflow: hidden; background: #070a12; padding: 5px 0; margin-bottom: 10px; }
    div[data-testid="stButton"] button[kind="primary"] { background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; font-weight: 900; border: none; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 로그인 로직
# ==========================================
if 'current_user' not in st.session_state:
    st.markdown("<br><br><h1 style='text-align:center;'>APEX <span style='color:#3b82f6;'>RADAR</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#64748b; font-size:14px;'>MOBILE SYNC ENABLED</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        uid = st.text_input("ENTER CALLSIGN", max_chars=8)
        if st.button("SYSTEM START", use_container_width=True, type="primary"):
            if uid:
                if uid not in st.session_state.full_db["users"]:
                    st.session_state.full_db["users"][uid] = {"favorites": [], "settings": {"fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0}}
                    save_db(st.session_state.full_db)
                st.session_state.current_user = uid
                st.rerun()
    st.stop()

u_name = st.session_state.current_user
u_data = st.session_state.full_db["users"][u_name]

# ==========================================
# 5. 10개 테마 200개 종목 데이터 복구
# ==========================================
SECTORS = {
    "⭐ 내 관심종목 (Favorites)": u_data['favorites'],
    "🌟 1. 빅테크 & IT (Big Tech)": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "QCOM", "TXN", "AVGO", "AMAT", "MU", "AMD"],
    "💻 2. AI & 반도체 (AI/Semi)": ["TSM", "ASML", "ARM", "SMCI", "KLAC", "SNPS", "CDNS", "NXPI", "MCHP", "LRCX", "MRVL", "MPWR", "ON", "SWKS", "TER", "WDC", "STM", "GFS", "ENTG", "QRVO"],
    "⚡ 3. 전기차 & 모빌리티 (EV)": ["RIVN", "LCID", "F", "GM", "NIO", "XPEV", "LI", "ALB", "PLUG", "ENPH", "MBLY", "LAZR", "QS", "CHPT", "RUN", "BLDP", "FSR", "NKLA", "PTRA", "ARVL"],
    "🧬 4. 바이오 & 헬스케어 (Bio)": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "AMGN", "GILD", "BMY", "CVS", "TMO", "MDT", "DHR", "ABT", "ISRG", "SYK", "VRTX", "ZTS", "REGN", "BSX"],
    "🏦 5. 금융 & 핀테크 (Fintech)": ["JPM", "BAC", "V", "MA", "PYPL", "SQ", "HOOD", "COIN", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "MCO", "SPGI", "CME", "ICE", "CB"],
    "🛡️ 6. 사이버 보안 (Security)": ["CRWD", "PANW", "FTNT", "NOW", "SNOW", "PLTR", "DDOG", "NET", "ZS", "OKTA", "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "RPD", "S", "MNDT", "FEYE", "NLOK"],
    "☁️ 7. 클라우드 & SW (Cloud)": ["SHOP", "UBER", "MNDY", "TEAM", "NET", "DOCN", "CFLT", "MDB", "PATH", "ESTC", "DT", "HCP", "FIVN", "SMAR", "AYX", "BOX", "PD", "ZEN", "DBX", "WK"],
    "🚀 8. 우주항공 & 방산 (Defense)": ["LMT", "RTX", "NOC", "GD", "BA", "TDG", "HEI", "HII", "TXT", "LHX", "KTOS", "CUB", "KAMN", "AJRD", "AVAV", "MOG-A", "ATRO", "SPCE", "RKLB", "ASTS"],
    "🛒 9. 소비재 & 이커머스 (Retail)": ["WMT", "HD", "PG", "COST", "TGT", "KO", "PEP", "MCD", "NKE", "SBUX", "MELI", "SE", "CPNG", "EBAY", "ETSY", "WAY", "CHWY", "PINS", "FTCH", "W"],
    "🛢️ 10. 에너지 & 인프라 (Energy)": ["XOM", "CVX", "SHEL", "COP", "TTE", "BP", "EQNR", "OXY", "EOG", "FSLR", "SEDG", "DQ", "SPWR", "NEP", "BEP", "CWEN", "HASI", "AY", "PEGI", "HAL"]
}

# ==========================================
# 6. 프로급 차트 엔진
# ==========================================
def draw_pure_chart(ticker, target, tp, sl):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        if df.empty: return None
        df.index = df.index.strftime('%m-%d')
        
        y_min = float(df['Low'].min() * 0.96)
        y_max = float(df['High'].max() * 1.04)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])

        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            increasing_line_color='#ef4444', decreasing_line_color='#3b82f6', 
            increasing_fillcolor='#ef4444', decreasing_fillcolor='#3b82f6', name="Price"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(5).mean(), line=dict(color='#eab308', width=1.5), name='5MA'), row=1, col=1)

        v_cols = ['#ef4444' if c >= o else '#3b82f6' for o, c in zip(df['Open'], df['Close'])]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=v_cols, opacity=0.8, name="Volume"), row=2, col=1)

        fig.add_hline(y=float(target), line_dash="dash", line_color="#10b981", annotation_text=f"ENTRY", row=1, col=1)
        fig.add_hline(y=float(sl), line_dash="solid", line_color="#ef4444", annotation_text=f"SL", row=1, col=1)
        fig.add_hline(y=float(tp), line_dash="dot", line_color="#3b82f6", annotation_text=f"TP", row=1, col=1)

        fig.update_xaxes(type='category', rangeslider_visible=False, fixedrange=True, showgrid=True, gridcolor='#1e293b')
        fig.update_yaxes(fixedrange=True, gridcolor='#1e293b', row=1, col=1, range=[y_min, y_max])
        fig.update_yaxes(fixedrange=True, showgrid=False, row=2, col=1)
        
        fig.update_layout(
            template="plotly_dark", height=450, margin=dict(l=0, r=40, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', dragmode=False, showlegend=False
        )
        return fig
    except Exception as e: return None

# ==========================================
# 7. 스캐닝 로직
# ==========================================
@st.cache_data(ttl=60)
def scan_engine(tickers, k, sl_p):
    res = []
    for t in tickers:
        try:
            s = yf.Ticker(t); df = s.history(period="40d")
            if len(df) < 20: continue
            yest, today = df.iloc[-2], df.iloc[-1]
            curr, op = float(today['Close']), float(today['Open'])
            ma5 = float(df['Close'].rolling(5).mean().iloc[-1])
            target = op + ((float(yest['High'] - yest['Low'])) * k)
            sl = target * (1 - sl_p/100)
            tp = target + (target - sl) * 2.0
            sig = "🎯 BUY" if curr >= target and op > ma5 else "👀 WATCH"
            if op <= ma5: sig = "❄️ WAIT"
            res.append({"Ticker": t, "Price": curr, "Chg": ((curr-df['Close'].iloc[-2])/df['Close'].iloc[-2])*100, "Signal": sig, "Target": target, "TP": tp, "SL": sl})
        except: continue
    return pd.DataFrame(res)

# ==========================================
# 8. 메인 렌더링
# ==========================================
sel_sec = st.selectbox("📂 10개 테마 스캐너 (200종목)", list(SECTORS.keys()), label_visibility="collapsed")

if not SECTORS[sel_sec]:
    st.info("사이드바에서 관심 종목을 추가하십시오.")
else:
    with st.spinner("스캐닝 중... (최대 20개 종목)"):
        df_res = scan_engine(SECTORS[sel_sec], float(u_data['settings']['fixed_k']), float(u_data['settings']['stop_loss_pct']))
    
    if not df_res.empty:
        hits = df_res[df_res['Signal'] == '🎯 BUY']['Ticker'].tolist()
        if hits: st.markdown(f"<div class='neon-alert'>🚨 타점 도달 경고: {', '.join(hits)}</div>", unsafe_allow_html=True)
        
        sel = st.dataframe(df_res[['Ticker', 'Price', 'Chg', 'Signal']], on_select="rerun", selection_mode="single-row",
                           column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Chg": st.column_config.NumberColumn(format="%.2f%%")},
                           use_container_width=True, hide_index=True, height=200)
        
        idx = sel.selection.rows[0] if sel.selection.rows else 0
        row = df_res.iloc[idx]
        
        # 모바일 반응형 전광판 (Responsive VIP Header)
        st.markdown(f"""
            <div class="vip-header">
                <div class="vip-title">{row['Ticker']}</div>
                <div class="vip-data-group">
                    <div class="vip-data"><div class="vip-label">ENTRY</div><div class="vip-value" style="color:#10b981;">${row['Target']:.2f}</div></div>
                    <div class="vip-data"><div class="vip-label">TARGET</div><div class="vip-value" style="color:#3b82f6;">${row['TP']:.2f}</div></div>
                    <div class="vip-data"><div class="vip-label">STOP LOSS</div><div class="vip-value" style="color:#ef4444;">${row['SL']:.2f}</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        fig = draw_pure_chart(row['Ticker'], row['Target'], row['TP'], row['SL'])
        if fig: st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# 사이드바
with st.sidebar:
    st.markdown(f"<h3 style='color:#3b82f6;'>👤 {u_name}</h3>", unsafe_allow_html=True)
    st.divider()
    st.markdown("#### ⚙️ ENGINE SETTINGS")
    u_data['settings']['fixed_k'] = st.slider("K-Value", 0.3, 0.8, float(u_data['settings']['fixed_k']), 0.05)
    u_data['settings']['stop_loss_pct'] = st.slider("Stop Loss (%)", 1.0, 10.0, float(u_data['settings']['stop_loss_pct']), 0.5)
    if st.button("SAVE", use_container_width=True): save_db(st.session_state.full_db); st.success("Saved.")
    
    st.divider()
    st.markdown("#### ⭐ WATCHLIST")
    new_t = st.text_input("Add Ticker").upper()
    if st.button("ADD TICKER"):
        if new_t and new_t not in u_data['favorites']:
            u_data['favorites'].append(new_t); save_db(st.session_state.full_db); st.rerun()

components.html("<script>setTimeout(function(){window.parent.location.reload();}, 60000);</script>", height=0)
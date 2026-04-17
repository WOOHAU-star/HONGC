import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz
import json
import os
import requests
import uuid
import time

# ==========================================
# 0. 보안 및 세션 관리
# ==========================================
@st.cache_resource
def get_active_users(): return {}
active_users = get_active_users()
TIMEOUT_SECONDS = 90

def cleanup_active_users():
    current_time = time.time()
    for u in list(active_users.keys()):
        if current_time - active_users[u]['last_seen'] > TIMEOUT_SECONDS: del active_users[u]

# ==========================================
# 1. 영구 저장소 및 데이터 세탁기 (Casting)
# ==========================================
DB_FILE = "apex_database.json"

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def load_db():
    key, bin_id = (st.secrets.get("JSONBIN_KEY"), st.secrets.get("JSONBIN_ID"))
    db_data = {}
    if key and bin_id:
        try:
            req = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}/latest", headers={"X-Master-Key": key})
            if req.status_code == 200: db_data = req.json().get("record", {})
        except: pass
    if not db_data and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: db_data = json.load(f)
        except: pass
    if "users" not in db_data: db_data = {"users": {"Admin": {"favorites": [], "settings": {"fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0}}}}
    return db_data

def save_db(full_db):
    key, bin_id = (st.secrets.get("JSONBIN_KEY"), st.secrets.get("JSONBIN_ID"))
    current_u = st.session_state.get("current_user")
    if key and bin_id and current_u:
        try:
            req_get = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}/latest", headers={"X-Master-Key": key})
            if req_get.status_code == 200:
                latest_db = req_get.json().get("record", {"users": {}})
                latest_db["users"][current_u] = full_db["users"][current_u]
                full_db = latest_db
            requests.put(f"https://api.jsonbin.io/v3/b/{bin_id}", data=json.dumps(full_db, cls=NumpyEncoder), headers={"Content-Type": "application/json", "X-Master-Key": key})
        except: pass
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(full_db, f, indent=4, cls=NumpyEncoder)

# ==========================================
# 2. UI 및 로그인 로직
# ==========================================
st.set_page_config(page_title="APEX QUANT SCANNER", layout="wide")
if 'full_db' not in st.session_state: st.session_state.full_db = load_db()

bg_color, text_color, card_bg, border_color, muted_text = "#0d1321", "#f1f5f9", "#172033", "#232e4a", "#8193b2"

st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {{ font-family: 'Pretendard', sans-serif !important; background-color: {bg_color}; color: {text_color}; }}
    .stApp {{ background-color: {bg_color}; }}
    .metric-card {{ background: {card_bg}; border: 1px solid {border_color}; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 10px; }}
    @keyframes neon {{ 0% {{ box-shadow: 0 0 5px rgba(239, 68, 68, 0.4); border-color: #ef4444; }} 100% {{ box-shadow: 0 0 15px rgba(239, 68, 68, 0.8); border-color: #fca5a5; }} }}
    .neon-alert {{ background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; border-radius: 8px; padding: 10px; text-align: center; color: #fca5a5; font-weight: 900; animation: neon 1.5s infinite alternate; font-size: 14px; margin-bottom: 10px; }}
    div[data-testid="stButton"] button[kind="primary"] {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-weight: 800; }}
    </style>
""", unsafe_allow_html=True)

url_u, url_sid = st.query_params.get('u'), st.query_params.get('sid')
cleanup_active_users()

if url_u and url_sid and 'current_user' not in st.session_state:
    rec = active_users.get(url_u)
    if rec and rec['sid'] != url_sid: st.error("이미 다른 기기에서 접속 중입니다."); st.stop()
    st.session_state.current_user, st.session_state.session_id = url_u, url_sid

if 'current_user' not in st.session_state:
    st.markdown("<br><h1 style='text-align:center; font-weight:900;'>APEX <span style='color:#667eea;'>SCANNER</span></h1>", unsafe_allow_html=True)
    login_name = st.text_input("Callsign", max_chars=8, placeholder="닉네임 입력", label_visibility="collapsed")
    if st.button("CONNECT", type="primary", use_container_width=True):
        if 1 <= len(login_name) <= 8:
            new_sid = str(uuid.uuid4())[:8]
            if login_name not in st.session_state.full_db["users"]:
                st.session_state.full_db["users"][login_name] = {"favorites": [], "settings": {"fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0}}
                save_db(st.session_state.full_db)
            st.session_state.current_user, st.session_state.session_id = login_name, new_sid
            st.query_params.update(u=login_name, sid=new_sid); st.rerun()
    st.stop()

current_u, current_sid = st.session_state.current_user, st.session_state.session_id
active_users[current_u] = {"sid": current_sid, "last_seen": time.time()}
u_data = st.session_state.full_db["users"][current_u]
u_favs, u_set = u_data.get("favorites", []), u_data.get("settings", {})

# ==========================================
# 3. 데이터 엔진
# ==========================================
@st.cache_data(ttl=60)
def get_macro():
    res = {}
    for n, t in {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "VIX": "^VIX"}.items():
        try:
            d = yf.Ticker(t).history(period="2d")
            c, p = d['Close'].iloc[-1], d['Close'].iloc[-2]
            res[n] = {"p": c, "ch": ((c-p)/p)*100}
        except: res[n] = {"p": 0, "ch": 0}
    return res

@st.cache_data(ttl=60)
def scan_engine(tickers, k, sl_pct, base_rr):
    results = []
    for t in tickers:
        try:
            s = yf.Ticker(t); df = s.history(period="60d")
            if df.empty or len(df) < 20: continue
            yest, today = df.iloc[-2], df.iloc[-1]
            curr, prev_c = float(today['Close']), float(yest['Close'])
            ma5 = float(df['Close'].rolling(5).mean().iloc[-1])
            target = float(today['Open'] + ((yest['High'] - yest['Low']) * k))
            atr = float(abs(df['High'] - df['Low']).rolling(14).mean().iloc[-1])
            dyn_rr = float(base_rr * 1.5 if (atr/curr)*100 >= 4.0 else base_rr)
            sl = float(target * (1 - (sl_pct / 100)))
            tp = float(target + ((target - sl) * dyn_rr))
            
            sig = "🎯 BUY" if curr >= target and today['Open'] > ma5 else ("🚀 OVER" if curr > target * 1.015 else "👀 WATCH")
            if today['Open'] <= ma5: sig = "❄️ WAIT"
            
            results.append({"Ticker": t, "Price": curr, "Chg": ((curr-prev_c)/prev_c)*100, "Signal": sig, "Target": target, "TP": tp, "SL": sl})
        except: continue
    return pd.DataFrame(results).sort_values(by="Signal")

# ==========================================
# 4. 업그레이드 차트 엔진 (신뢰의 비율)
# ==========================================
def draw_professional_chart(ticker, target, tp, sl):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        if df.empty: return go.Figure()

        # X축 날짜 클린업
        df.index = df.index.strftime('%m-%d')
        
        # [수술] Y축 범위 자동 최적화 (캔들 중심)
        y_min, y_max = df['Low'].min() * 0.98, df['High'].max() * 1.02
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

        # 1. 한국형 캔들 & 이평선
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     increasing_line_color='#ef4444', decreasing_line_color='#3b82f6', name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(5).mean(), line=dict(color='#eab308', width=1), name="5MA"), row=1, col=1)

        # 2. 정밀 매물대 (최근 데이터 기준)
        try:
            counts, bins = np.histogram(df['Close'], bins=20, weights=df['Volume'])
            bin_centers = (bins[:-1] + bins[1:]) / 2
            fig.add_trace(go.Bar(x=counts, y=bin_centers, orientation='h', xaxis='x3', yaxis='y',
                                 marker=dict(color='rgba(129, 147, 178, 0.15)'), showlegend=False, hoverinfo='none'), row=1, col=1)
        except: pass

        # 3. 깔끔한 거래량 (X축 숫자 제거)
        v_cols = ['#ef4444' if c >= o else '#3b82f6' for o, c in zip(df['Open'], df['Close'])]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=v_cols, name="Vol"), row=2, col=1)

        # 4. 전술 라인 (비율에 따라 텍스트 위치 자동 조정)
        fig.add_hline(y=target, line_dash="dash", line_color="#10b981", annotation_text=f"ENTRY {target:.2f}", row=1, col=1)
        fig.add_hline(y=sl, line_dash="solid", line_color="#ef4444", annotation_text=f"SL {sl:.2f}", row=1, col=1)
        
        # TP가 너무 멀면 선만 긋고 축은 캔들에 고정
        fig.add_hline(y=tp, line_dash="solid", line_color="#3b82f6", annotation_text=f"TP {tp:.2f}", row=1, col=1)

        # [핵심] 줌 잠금 및 X축 텍스트 정리
        fig.update_xaxes(type='category', rangeslider_visible=False, fixedrange=True, showgrid=False)
        fig.update_yaxes(fixedrange=True, range=[y_min, y_max], showgrid=True, gridcolor='#1e293b')
        
        fig.update_layout(
            xaxis3=dict(overlaying='x', side='top', showticklabels=False, range=[0, max(counts)*4 if 'counts' in locals() else 1]),
            template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', dragmode=False, showlegend=False
        )
        return fig
    except: return go.Figure()

# ==========================================
# 5. 메인 레이아웃
# ==========================================
m = get_macro()
t_tape = " &nbsp;&nbsp;&nbsp; ".join([f"<span style='color:#8193b2;'>{k}</span> <b style='color:#fff;'>{v['p']:.1f}</b> <span style='color:{'#ef4444' if v['ch']>=0 else '#3b82f6'};'>({v['ch']:.1f}%)</span>" for k, v in m.items()])
st.markdown(f"<div class='ticker-wrap'><div class='ticker-move'>{t_tape * 5}</div></div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"<div class='metric-card'><b>{current_u}</b> OPERATING</div>", unsafe_allow_html=True)
    if st.button("DISCONNECT"):
        if current_u in active_users: del active_users[current_u]
        st.query_params.clear(); st.rerun()
    st.divider()
    new_k = st.slider("K", 0.3, 0.8, float(u_set.get("fixed_k", 0.5)), 0.05)
    new_sl = st.slider("SL%", 1.0, 10.0, float(u_set.get("stop_loss_pct", 4.0)), 0.5)
    if (new_k != u_set.get("fixed_k") or new_sl != u_set.get("stop_loss_pct")):
        u_set.update({"fixed_k": new_k, "stop_loss_pct": new_sl}); save_db(st.session_state.full_db)

SECTORS = {"⭐ FAVORITES": u_favs, "🌟 BIG TECH": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX"], "💻 SEMI": ["TSM", "ASML", "ARM", "AMD", "MU"]}
sel_sec = st.selectbox("📂 SECTOR", list(SECTORS.keys()), label_visibility="collapsed")

if not SECTORS[sel_sec]: st.info("관심 종목을 추가하세요.")
else:
    df = scan_engine(SECTORS[sel_sec], new_k, new_sl, float(u_set.get("base_rr_ratio", 2.0)))
    if not df.empty:
        hits = df[df['Signal'] == '🎯 BUY']['Ticker'].tolist()
        if hits: st.markdown(f"<div class='neon-alert'>🔥 HIT: {', '.join(hits)}</div>", unsafe_allow_html=True)
        
        sel = st.dataframe(df[['Ticker', 'Price', 'Chg', 'Signal']], on_select="rerun", selection_mode="single-row",
                           column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Chg": st.column_config.NumberColumn(format="%.1f%%")},
                           use_container_width=True, hide_index=True, height=180)
        
        idx = sel.selection.rows[0] if sel.selection.rows else 0
        row = df.iloc[idx]
        
        st.markdown(f"""
            <div style="display:flex; justify-content:space-around; background:#172033; padding:8px; border-radius:10px; border:1px solid #232e4a; margin:5px 0;">
                <b style="color:#667eea;">{row['Ticker']}</b>
                <span><small style='color:#8193b2'>ENTRY</small> <b>{row['Target']:.2f}</b></span>
                <span><small style='color:#8193b2'>TP</small> <b style="color:#3b82f6;">{row['TP']:.2f}</b></span>
                <span><small style='color:#8193b2'>SL</small> <b style="color:#ef4444;">{row['SL']:.2f}</b></span>
            </div>
        """, unsafe_allow_html=True)
        
        st.plotly_chart(draw_professional_chart(row['Ticker'], row['Target'], row['TP'], row['SL']), use_container_width=True, config={'displayModeBar': False})

components.html("<script>setTimeout(function(){window.parent.location.reload();}, 60000);</script>", height=0)

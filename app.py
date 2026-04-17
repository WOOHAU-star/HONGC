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
# 0. 중복 접속 차단 & 실시간 레이더
# ==========================================
@st.cache_resource
def get_active_users():
    return {}

active_users = get_active_users()
TIMEOUT_SECONDS = 90

def cleanup_active_users():
    current_time = time.time()
    for u in list(active_users.keys()):
        if current_time - active_users[u]['last_seen'] > TIMEOUT_SECONDS:
            del active_users[u]

# ==========================================
# 1. 영구 저장소 (Cloud JSONBin) - 모의투자 제거
# ==========================================
DB_FILE = "apex_database.json"

def get_secrets():
    try:
        if "JSONBIN_KEY" in st.secrets and "JSONBIN_ID" in st.secrets:
            return st.secrets["JSONBIN_KEY"], st.secrets["JSONBIN_ID"]
    except Exception: pass
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
        except Exception: pass
    
    if not db_data and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db_data = json.load(f)
        except Exception: pass

    if "users" not in db_data:
        old_data = db_data.copy()
        db_data = {"users": {"Admin": {"favorites": [], "settings": {"total_capital": 100000, "max_stocks": 5, "weight_pct": 100.0, "fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0, "gap_limit_pct": 2.0}}}}
    return db_data

def save_db(full_db):
    key, bin_id = get_secrets()
    if key and bin_id:
        try:
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
        except Exception: pass

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(full_db, f, ensure_ascii=False, indent=4)

# ==========================================
# 2. 테마 및 페이지 세팅
# ==========================================
st.set_page_config(page_title="APEX QUANT", layout="wide", page_icon="🚀")

if 'full_db' not in st.session_state: st.session_state.full_db = load_db()

bg_color = "#0d1321" 
text_color = "#f1f5f9"
card_bg = "#172033"
border_color = "#232e4a"
muted_text = "#8193b2"

st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  {{ font-family: 'Pretendard', sans-serif !important; background-color: {bg_color}; color: {text_color}; }}
    .stApp {{ background-color: {bg_color}; }}
    
    .metric-card {{ background: {card_bg}; border: 1px solid {border_color}; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 10px; }}
    .metric-title {{ font-size: 12px; color: {muted_text}; font-weight: 700; margin-bottom: 5px; }}
    
    /* 타점 도달 네온사인 */
    @keyframes neon {{
        0% {{ text-shadow: 0 0 5px #fff, 0 0 10px #ef4444, 0 0 20px #ef4444; border-color: #ef4444; box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); }}
        100% {{ text-shadow: 0 0 2px #fff, 0 0 5px #ef4444, 0 0 10px #ef4444; border-color: #fca5a5; box-shadow: 0 0 20px rgba(239, 68, 68, 0.6); }}
    }}
    .neon-alert {{ background: rgba(239, 68, 68, 0.1); border: 2px solid #ef4444; border-radius: 10px; padding: 10px; text-align: center; color: #fff; font-weight: 900; animation: neon 1.5s infinite alternate; margin-bottom: 15px; font-size: 15px; letter-spacing: 1px; }}

    div[data-testid="stButton"] button[kind="primary"] {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 900; border: none; border-radius: 15px; }}
    div[data-baseweb="input"] > div {{ border-radius: 10px; background-color: {card_bg}; border-color: {border_color}; }}
    div[data-baseweb="select"] > div {{ border-radius: 10px; background-color: {card_bg}; border-color: {border_color}; }}
    
    .ticker-wrap {{ width: 100%; overflow: hidden; background: #070a12; padding: 6px 0; border-bottom: 1px solid {border_color}; margin-bottom: 10px; }}
    .ticker-move {{ display: inline-block; white-space: nowrap; animation: ticker 120s linear infinite; font-size: 13px; font-weight: 700; }}
    @keyframes ticker {{ 0% {{ transform: translateX(100%); }} 100% {{ transform: translateX(-150%); }} }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 로그인
# ==========================================
url_params = st.query_params
url_u = url_params.get('u')
url_sid = url_params.get('sid')
current_time = time.time()
cleanup_active_users()

if url_u and url_sid and 'current_user' not in st.session_state:
    record = active_users.get(url_u)
    if record and record['sid'] == url_sid:
        st.session_state.current_user = url_u; st.session_state.session_id = url_sid
    elif record and current_time - record['last_seen'] < TIMEOUT_SECONDS:
        st.error(f"⚠️ '{url_u}' 님은 이미 다른 기기에서 접속 중입니다."); st.stop()
    else:
        st.session_state.current_user = url_u; st.session_state.session_id = url_sid

if 'current_user' not in st.session_state:
    st.markdown("<br><br><br><h1 style='text-align:center; font-weight:900; font-size:36px; letter-spacing:1px;'>APEX <span style='color:#667eea;'>SCANNER</span></h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:{muted_text};'>TACTICAL RADAR ON</p><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        login_name = st.text_input("트레이더 닉네임", max_chars=8, placeholder="Callsign 입력", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("CONNECT 🚀", type="primary", use_container_width=True):
            if 1 <= len(login_name) <= 8:
                rec = active_users.get(login_name)
                if rec and (current_time - rec['last_seen'] < TIMEOUT_SECONDS):
                    st.error(f"⚠️ 접속 충돌. 90초 후 재시도 바랍니다.")
                else:
                    new_sid = str(uuid.uuid4())[:8]
                    if login_name not in st.session_state.full_db["users"]:
                        st.session_state.full_db["users"][login_name] = {"favorites": [], "settings": {"total_capital": 100000, "max_stocks": 5, "weight_pct": 100.0, "fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0, "gap_limit_pct": 2.0}}
                        save_db(st.session_state.full_db)
                    st.session_state.current_user = login_name; st.session_state.session_id = new_sid
                    st.query_params["u"] = login_name; st.query_params["sid"] = new_sid
                    st.rerun()
            else: st.error("1~8자 입력 요망.")
    st.stop()

current_u = st.session_state.current_user
current_sid = st.session_state.session_id
active_users[current_u] = {"sid": current_sid, "last_seen": time.time()}

u_data = st.session_state.full_db["users"][current_u]
u_favs, u_set = u_data.get("favorites", []), u_data.get("settings", {})

def sync_and_save():
    st.session_state.full_db["users"][current_u]["favorites"] = u_favs
    st.session_state.full_db["users"][current_u]["settings"] = u_set
    save_db(st.session_state.full_db)

# ==========================================
# 4. 섹터 티커 딕셔너리
# ==========================================
SECTORS = {
    "🌟 Big Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "QCOM", "TXN", "AVGO", "AMAT", "MU", "AMD"],
    "💻 AI & 반도체": ["TSM", "ASML", "ARM", "SMCI", "KLAC", "SNPS", "CDNS", "NXPI", "MCHP", "LRCX", "MRVL", "MPWR", "ON", "SWKS", "TER", "WDC", "STM", "GFS", "ENTG", "QRVO"],
    "⚡ 전기차 & 자율주행": ["RIVN", "LCID", "F", "GM", "NIO", "XPEV", "LI", "ALB", "PLUG", "ENPH", "MBLY", "LAZR", "QS", "CHPT", "RUN", "BLDP", "FSR", "NKLA", "PTRA", "ARVL"],
    "🧬 바이오 & 헬스케어": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "AMGN", "GILD", "BMY", "CVS", "TMO", "MDT", "DHR", "ABT", "ISRG", "SYK", "VRTX", "ZTS", "REGN", "BSX"],
    "🏦 금융 & 핀테크": ["JPM", "BAC", "V", "MA", "PYPL", "SQ", "HOOD", "COIN", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "MCO", "SPGI", "CME", "ICE", "CB"],
    "🛡️ 사이버 보안": ["CRWD", "PANW", "FTNT", "NOW", "SNOW", "PLTR", "DDOG", "NET", "ZS", "OKTA", "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "RPD", "S", "MNDT", "FEYE", "NLOK"],
    "☁️ 클라우드 & SW": ["SHOP", "UBER", "MNDY", "TEAM", "NET", "DOCN", "CFLT", "MDB", "PATH", "ESTC", "DT", "HCP", "FIVN", "SMAR", "AYX", "BOX", "PD", "ZEN", "DBX", "WK"],
    "🚀 우주항공 & 방산": ["LMT", "RTX", "NOC", "GD", "BA", "TDG", "HEI", "HII", "TXT", "LHX", "KTOS", "CUB", "KAMN", "AJRD", "AVAV", "MOG-A", "ATRO", "SPCE", "RKLB", "ASTS"],
    "🛒 이커머스 & 소비재": ["WMT", "HD", "PG", "COST", "TGT", "KO", "PEP", "MCD", "NKE", "SBUX", "MELI", "SE", "CPNG", "EBAY", "ETSY", "WAY", "CHWY", "PINS", "FTCH", "W"],
    "⚡ 에너지 & 친환경": ["XOM", "CVX", "CVX", "SHEL", "COP", "TTE", "BP", "EQNR", "OXY", "EOG", "FSLR", "SEDG", "DQ", "SPWR", "NEP", "BEP", "CWEN", "HASI", "AY", "PEGI"]
}

# ==========================================
# 5. 사이드바 통제
# ==========================================
with st.sidebar:
    st.markdown(f"<div class='metric-card'><h3 style='margin:0; color:#fff;'>👤 {current_u}</h3><p style='margin:0; font-size:12px; color:#10b981;'>● SECURE CONNECTION</p></div>", unsafe_allow_html=True)
    if st.button("LOGOUT", use_container_width=True):
        if current_u in active_users: del active_users[current_u]
        del st.session_state.current_user; del st.session_state.session_id; st.query_params.clear(); st.rerun()
    
    st.divider()
    st.markdown("<div class='metric-title'>종목 검색 (ADD)</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1: new_search = st.text_input("Ticker", label_visibility="collapsed").upper()
    with c2: 
        if st.button("➕", use_container_width=True) and new_search:
            if "." not in new_search and new_search not in u_favs:
                try:
                    if not yf.Ticker(new_search).history(period="1d").empty:
                        u_favs.append(str(new_search)); sync_and_save(); st.rerun()
                except Exception: pass
    
    all_tickers_flat = list(set([t for v in SECTORS.values() for t in v] + u_favs))
    st.markdown("<br><div class='metric-title'>관심종목 관리 (REMOVE)</div>", unsafe_allow_html=True)
    new_favs = st.multiselect("Edit Watchlist", options=all_tickers_flat, default=u_favs, label_visibility="collapsed")
    if new_favs != u_favs: u_data["favorites"] = new_favs; u_favs = new_favs; sync_and_save()
        
    st.divider()
    st.markdown("<div class='metric-title'>스캔 필터 설정 (FILTER)</div>", unsafe_allow_html=True)
    new_k = st.slider("K-Value", 0.3, 0.8, float(u_set.get("fixed_k", 0.5)), 0.05)
    new_sl = st.slider("Stop Loss (%)", 1.0, 10.0, float(u_set.get("stop_loss_pct", 4.0)), 0.5)
    new_rr = st.slider("Target R/R", 1.0, 5.0, float(u_set.get("base_rr_ratio", 2.0)), 0.5)
    
    if (new_k != u_set.get("fixed_k") or new_sl != u_set.get("stop_loss_pct") or new_rr != u_set.get("base_rr_ratio")):
        u_set.update({"fixed_k": new_k, "stop_loss_pct": new_sl, "base_rr_ratio": new_rr})
        sync_and_save()

    st.divider()
    st.markdown("<div class='metric-title'>🟢 LIVE OPERATORS</div>", unsafe_allow_html=True)
    for u in list(active_users.keys()):
        st.markdown(f"<span style='color:{'#10b981' if u==current_u else muted_text}; font-size:14px;'>● {u}</span>", unsafe_allow_html=True)

# ==========================================
# 6. 스캔 엔진 및 차트 (줌 락, 거래량, 매물대)
# ==========================================
@st.cache_data(ttl=60)
def get_macro_indices():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "VIX": "^VIX"}
    data = {}
    for name, t in tickers.items():
        try:
            df = yf.Ticker(t).history(period="2d")
            curr, prev = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
            data[name] = {"price": curr, "pct": ((curr - prev) / prev) * 100}
        except Exception: data[name] = {"price": 0.0, "pct": 0.0}
    return data

@st.cache_data(ttl=60) 
def get_ranking_data(tickers, k, sl_pct, base_rr):
    results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d")
            if df.empty or len(df) < 25: continue
            
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            atr_14 = float(df[['H-L', 'H-PC', 'L-PC']].max(axis=1).rolling(14).mean().iloc[-1])
            
            yest = df.iloc[-2]; today = df.iloc[-1]
            current = float(today['Close']); yest_close = float(yest['Close'])
            change_pct = ((current - yest_close) / yest_close) * 100 if yest_close > 0 else 0
            
            ma5 = float(df['Close'].rolling(window=5).mean().iloc[-1])
            target = float(today['Open'] + (float(yest['High'] - yest['Low']) * k))
            
            dynamic_rr = float(base_rr * 1.5 if (atr_14/current)*100 >= 4.0 else base_rr)
            stop_loss = float(target * (1 - (sl_pct / 100)))
            take_profit = float(target + ((target - stop_loss) * dynamic_rr))
            
            is_bull = float(today['Open']) > ma5
            is_hit = current >= target
            is_chasing = current > (target * 1.015) 
            
            if not is_bull: signal = "❄️ WAIT"
            elif is_chasing: signal = "🚀 OVER"
            elif is_hit: signal = "🎯 BUY"
            else: signal = "👀 WATCH"

            score = 10 if is_bull else 0
            if is_hit: score += 50
            if signal == "🎯 BUY": score += 20

            results.append({
                "Ticker": str(ticker), "Price": current, "Change": change_pct, 
                "Signal": signal, "Score": score,
                "Target": target, "TP": take_profit, "SL": stop_loss
            })
        except Exception: continue
        
    df_res = pd.DataFrame(results) if results else pd.DataFrame(columns=["Ticker", "Price", "Change", "Signal", "Score", "Target", "TP", "SL"])
    if not df_res.empty: df_res = df_res.sort_values(by="Score", ascending=False).reset_index(drop=True)
    return df_res

def draw_tactical_chart(ticker, target, tp, sl):
    df = yf.Ticker(ticker).history(period="1mo")
    
    # 볼륨 서브플롯 추가
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    
    # 메인 차트 (캔들 + 5MA)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#667eea', decreasing_line_color='#ef4444', showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(5).mean(), line=dict(color='#764ba2', width=1.5), name='5MA', showlegend=False), row=1, col=1)
    
    # 매물대 (Volume Profile) 투명하게 깔기
    bins = np.linspace(df['Low'].min(), df['High'].max(), 24) 
    hist, bin_edges = np.histogram(df['Close'], bins=bins, weights=df['Volume'])
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    fig.add_trace(go.Bar(x=hist, y=bin_centers, orientation='h', xaxis='x3', yaxis='y', marker=dict(color='rgba(100, 116, 139, 0.2)', line=dict(width=0)), showlegend=False, hoverinfo='none'), row=1, col=1)
    
    # 볼륨 바 차트 하단 추가
    v_colors = ['#667eea' if r['Close'] >= r['Open'] else '#ef4444' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=v_colors, showlegend=False), row=2, col=1)
    
    # 타점 라인
    fig.add_hline(y=tp, line_dash="solid", line_color="#3b82f6", annotation_text=f"TP {tp:.2f}", row=1, col=1)
    fig.add_hline(y=target, line_dash="dash", line_color="#10b981", annotation_text=f"ENTRY {target:.2f}", row=1, col=1)
    fig.add_hline(y=sl, line_dash="solid", line_color="#ef4444", annotation_text=f"SL {sl:.2f}", row=1, col=1)
    
    # [수정] 줌 인/아웃 잠금 (fixedrange=True) 및 레이아웃 최적화
    fig.update_xaxes(rangeslider_visible=False, fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        xaxis3=dict(overlaying='x', side='top', showticklabels=False, range=[0, max(hist)*3]), 
        template="plotly_dark", height=400, margin=dict(l=0,r=40,t=10,b=0), 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', dragmode=False
    )
    return fig

# ==========================================
# 7. 메인 UI (초경량 스캐너 뷰)
# ==========================================
indices = get_macro_indices()
t_str = " &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; ".join([f"<span style='color:{muted_text};'>{k}</span> <span style='color:#fff; font-weight:bold;'>{v['price']:.2f}</span> <span style='color:{'#10b981' if v['pct']>=0 else '#ef4444'};'>({'+' if v['pct']>=0 else ''}{v['pct']:.2f}%)</span>" for k, v in indices.items()])
st.markdown(f"<div class='ticker-wrap'><div class='ticker-move'>{t_str * 5}</div></div>", unsafe_allow_html=True)

# 탭을 아예 없애고 바로 스캐너 뷰 노출
selected_sector = st.selectbox("📂 섹터 선택 (스캔)", ["⭐ 내 관심종목 스캔"] + list(SECTORS.keys()))

scan_list = u_favs if selected_sector == "⭐ 내 관심종목 스캔" else SECTORS[selected_sector]

if not scan_list:
    st.info("선택된 리스트에 종목이 없습니다. 사이드바에서 추가해주세요.")
else:
    with st.spinner("스캐닝 중..."):
        df_all = get_ranking_data(scan_list, new_k, new_sl, new_rr)
    
    if not df_all.empty:
        # [신규] 네온사인 알림창 복구 (타점 도달 시)
        hits = df_all[df_all['Signal'] == '🎯 BUY']['Ticker'].tolist()
        if hits:
            hit_str = ", ".join(hits)
            st.markdown(f"<div class='neon-alert'>🔥 타점 도달 경고: {hit_str} 진입 구간!</div>", unsafe_allow_html=True)

        disp_df = df_all[['Ticker', 'Price', 'Change', 'Signal']].copy()
        
        sel = st.dataframe(disp_df, on_select="rerun", selection_mode="single-row", 
                           column_config={
                               "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                               "Change": st.column_config.NumberColumn("Chg", format="%.2f%%"),
                               "Signal": st.column_config.TextColumn("Signal")
                           }, use_container_width=True, hide_index=True, height=200)
        
        idx = sel.selection.rows[0] if sel and sel.selection.rows else 0
        row = df_all.iloc[idx]; focus = str(row['Ticker'])
        
        # [신규] 초압축 인라인 정보창 (컴팩트 UI)
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; background:{card_bg}; padding:15px; border-radius:10px; border:1px solid {border_color}; margin-top:10px; margin-bottom:15px;">
            <div style="font-size:20px; font-weight:900; color:#667eea; width:20%;">{focus}</div>
            <div style="text-align:center; width:25%;"><span style="font-size:11px; color:{muted_text};">ENTRY</span><br><b style="color:#10b981; font-size:16px;">${row['Target']:.2f}</b></div>
            <div style="text-align:center; width:25%;"><span style="font-size:11px; color:{muted_text};">TP</span><br><b style="color:#3b82f6; font-size:16px;">${row['TP']:.2f}</b></div>
            <div style="text-align:center; width:25%;"><span style="font-size:11px; color:{muted_text};">SL</span><br><b style="color:#ef4444; font-size:16px;">${row['SL']:.2f}</b></div>
        </div>
        """, unsafe_allow_html=True)
        
        # 차트 출력 (No-Zoom Lock, 볼륨 렌더링 포함)
        st.plotly_chart(draw_tactical_chart(focus, row['Target'], row['TP'], row['SL']), use_container_width=True, config={'displayModeBar': False})
        
    else: st.info("스캔 결과가 없거나 통신 지연입니다.")

st.button("refresh", key="auto_refresh", help="hidden_refresh")
st.markdown("""<style>div[data-testid="stButton"]:has(button[title="hidden_refresh"]) { display: none !important; }</style>""", unsafe_allow_html=True)
components.html("""<script>let t = 60; setInterval(() => { t--; if(t<=0) { t=60; const btn = window.parent.document.querySelector('button[title="hidden_refresh"]'); if(btn) btn.click(); } }, 1000);</script>""", height=0)

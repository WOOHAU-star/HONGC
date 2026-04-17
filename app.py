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
# 1. 영구 저장소 (Cloud JSONBin)
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
        db_data = {"users": {"Admin": {"favorites": [], "paper_trades": [], "settings": {"total_capital": 100000, "max_stocks": 5, "weight_pct": 100.0, "fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0, "gap_limit_pct": 2.0}}}}
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
# 2. 테마 및 페이지 세팅 (하이엔드 핀테크 UI)
# ==========================================
st.set_page_config(page_title="APEX QUANT", layout="wide", page_icon="🚀")

if 'full_db' not in st.session_state: st.session_state.full_db = load_db()

# 레퍼런스 이미지 기반 색상 추출
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
    
    /* 레퍼런스 스타일 카드 */
    .metric-card {{ background: {card_bg}; border: 1px solid {border_color}; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 10px 20px -5px rgba(0,0,0,0.3); margin-bottom: 15px; }}
    .metric-title {{ font-size: 13px; color: {muted_text}; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; margin-bottom: 8px; }}
    .metric-value {{ font-size: 26px; font-weight: 900; color: #fff; margin-bottom: 5px; }}
    
    /* 레퍼런스 스타일 네온/그레이디언트 버튼 */
    div[data-testid="stButton"] button[kind="primary"] {{ 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
        color: white; font-weight: 900; border: none; border-radius: 25px; 
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.4); padding: 10px 0; transition: all 0.3s;
    }}
    div[data-testid="stButton"] button[kind="primary"]:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(118, 75, 162, 0.6); }}
    
    /* 입력창 모서리 둥글게 */
    div[data-baseweb="input"] > div {{ border-radius: 15px; background-color: {card_bg}; border-color: {border_color}; }}
    div[data-baseweb="select"] > div {{ border-radius: 15px; background-color: {card_bg}; border-color: {border_color}; }}
    
    /* Ticker Tape */
    .ticker-wrap {{ width: 100%; overflow: hidden; background: #070a12; padding: 8px 0; border-bottom: 1px solid {border_color}; margin-bottom: 20px; }}
    .ticker-move {{ display: inline-block; white-space: nowrap; animation: ticker 120s linear infinite; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; }}
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
    # 이미지 레퍼런스를 반영한 둥글고 세련된 로그인 UI
    st.markdown("<br><br><br><h1 style='text-align:center; font-weight:900; font-size:40px; letter-spacing:2px;'>APEX</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:{muted_text};'>Create your tactical account</p><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown(f"<div style='font-size:13px; color:{muted_text}; margin-bottom:5px; margin-left:10px;'>Your Callsign</div>", unsafe_allow_html=True)
        login_name = st.text_input("트레이더 닉네임", max_chars=8, placeholder="Monic Fox", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("GET STARTED", type="primary", use_container_width=True):
            if 1 <= len(login_name) <= 8:
                rec = active_users.get(login_name)
                if rec and (current_time - rec['last_seen'] < TIMEOUT_SECONDS):
                    st.error(f"⚠️ 접속 충돌. 90초 후 재시도 바랍니다.")
                else:
                    new_sid = str(uuid.uuid4())[:8]
                    if login_name not in st.session_state.full_db["users"]:
                        st.session_state.full_db["users"][login_name] = {"favorites": [], "paper_trades": [], "settings": {"total_capital": 100000, "max_stocks": 5, "weight_pct": 100.0, "fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0, "gap_limit_pct": 2.0}}
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
u_favs, u_trades, u_set = u_data["favorites"], u_data["paper_trades"], u_data["settings"]

def sync_and_save():
    st.session_state.full_db["users"][current_u]["favorites"] = u_favs
    st.session_state.full_db["users"][current_u]["paper_trades"] = u_trades
    st.session_state.full_db["users"][current_u]["settings"] = u_set
    save_db(st.session_state.full_db)

# ==========================================
# 4. 10개 테마 200개 종목 데이터베이스 복구
# ==========================================
SECTORS = {
    "🌟 Big Tech (빅테크)": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "QCOM", "TXN", "AVGO", "AMAT", "MU", "AMD"],
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
    st.markdown(f"<div class='metric-card'><h3 style='margin:0; color:#fff;'>👤 {current_u}</h3><p style='margin:0; font-size:12px; color:#667eea;'>SECURE CONNECTION</p></div>", unsafe_allow_html=True)
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
    st.markdown("<div class='metric-title'>자산 통제 (CAPITAL)</div>", unsafe_allow_html=True)
    new_cap = st.number_input("Capital ($)", min_value=1000, value=int(u_set.get("total_capital", 100000)), step=5000)
    new_max = st.number_input("Max Stocks", min_value=1, max_value=20, value=int(u_set.get("max_stocks", 5)))
    new_wgt = st.slider("Weight (%)", 10.0, 100.0, float(u_set.get("weight_pct", 100.0)), 5.0)
    allocated_per_stock = float(new_cap / new_max) * float(new_wgt / 100)
    
    st.markdown("<br><div class='metric-title'>딥 필터 (FILTER)</div>", unsafe_allow_html=True)
    new_k = st.slider("K-Value", 0.3, 0.8, float(u_set.get("fixed_k", 0.5)), 0.05)
    new_sl = st.slider("Stop Loss (%)", 1.0, 10.0, float(u_set.get("stop_loss_pct", 4.0)), 0.5)
    new_rr = st.slider("Target R/R", 1.0, 5.0, float(u_set.get("base_rr_ratio", 2.0)), 0.5)
    
    if (new_cap != u_set["total_capital"] or new_max != u_set["max_stocks"] or new_wgt != u_set["weight_pct"] or new_k != u_set["fixed_k"] or new_sl != u_set["stop_loss_pct"] or new_rr != u_set["base_rr_ratio"]):
        u_set.update({"total_capital": new_cap, "max_stocks": new_max, "weight_pct": new_wgt, "fixed_k": new_k, "stop_loss_pct": new_sl, "base_rr_ratio": new_rr})
        sync_and_save()

# ==========================================
# 6. 매크로 및 엔진 모듈
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
def get_ranking_data(tickers, k, allocated_budget, sl_pct, base_rr):
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
                "Ticker": str(ticker), 
                "Price": current, "Change": change_pct, 
                "Signal": signal, "Score": score,
                "Target": target, "TP": take_profit, "SL": stop_loss,
                "Qty": int(allocated_budget / target) if signal in ["🎯 BUY", "👀 WATCH"] else 0
            })
        except Exception: continue
        
    df_res = pd.DataFrame(results) if results else pd.DataFrame(columns=["Ticker", "Price", "Change", "Signal", "Score", "Target", "TP", "SL", "Qty"])
    if not df_res.empty: df_res = df_res.sort_values(by="Score", ascending=False).reset_index(drop=True)
    return df_res

def draw_tactical_chart(ticker, target, tp, sl):
    df = yf.Ticker(ticker).history(period="1mo")
    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#667eea', decreasing_line_color='#ef4444'))
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(5).mean(), line=dict(color='#764ba2', width=1.5), name='5MA'))
    fig.add_hline(y=tp, line_dash="solid", line_color="#3b82f6", annotation_text=f"TP ${tp:.2f}")
    fig.add_hline(y=target, line_dash="dash", line_color="#667eea", annotation_text=f"ENTRY ${target:.2f}")
    fig.add_hline(y=sl, line_dash="solid", line_color="#ef4444", annotation_text=f"SL ${sl:.2f}")
    fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=40,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

# ==========================================
# 7. 메인 UI (모바일 공간 확보 및 레퍼런스 적용)
# ==========================================
indices = get_macro_indices()
t_str = " &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; ".join([f"<span style='color:{muted_text};'>{k}</span> <span style='color:#fff; font-weight:bold;'>{v['price']:.2f}</span> <span style='color:{'#667eea' if v['pct']>=0 else '#ef4444'};'>({'+' if v['pct']>=0 else ''}{v['pct']:.2f}%)</span>" for k, v in indices.items()])
st.markdown(f"<div class='ticker-wrap'><div class='ticker-move'>{t_str * 5}</div></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🎯 SCANNER", "💼 WALLET", "🏆 RANKING"])

# --- TAB 1: SCANNER ---
with tab1:
    # [모바일 공간 확보] 방대한 10개 테마를 콤팩트한 드롭다운으로 변경
    selected_sector = st.selectbox("📂 Select Sector (200 Tickers)", list(SECTORS.keys()))
    
    if selected_sector:
        with st.spinner("Scanning 20 targets..."):
            df_all = get_ranking_data(SECTORS[selected_sector], new_k, allocated_per_stock, new_sl, new_rr)
        
        if not df_all.empty:
            disp_df = df_all[['Ticker', 'Price', 'Change', 'Signal']].copy()
            sel = st.dataframe(disp_df, on_select="rerun", selection_mode="single-row", 
                               column_config={
                                   "Price": st.column_config.NumberColumn("현재가", format="$%.2f"),
                                   "Change": st.column_config.NumberColumn("등락", format="%.2f%%"),
                                   "Signal": st.column_config.TextColumn("상태")
                               }, use_container_width=True, hide_index=True, height=200)
            
            idx = sel.selection.rows[0] if sel and sel.selection.rows else 0
            row = df_all.iloc[idx]; focus = str(row['Ticker'])
            
            st.divider()
            # 선택 종목 전술 뷰
            st.markdown(f"<div class='metric-card' style='text-align:left;'><div class='metric-title'>Selected Asset</div><div class='metric-value' style='color:#667eea;'>{focus}</div></div>", unsafe_allow_html=True)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("🎯 ENTRY", f"${row['Target']:.2f}")
            m2.metric("🔵 TP", f"${row['TP']:.2f}")
            m3.metric("🔴 SL", f"${row['SL']:.2f}")
            
            st.plotly_chart(draw_tactical_chart(focus, row['Target'], row['TP'], row['SL']), use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("CONFIRM GAMESBUY", type="primary", use_container_width=True):
                if int(row['Qty']) > 0 and row['Signal'] in ["🎯 BUY", "👀 WATCH"]:
                    u_trades.append({"티커":focus, "종목명":focus, "진입가":float(row['Price']), "수량":int(row['Qty'])})
                    sync_and_save(); st.success("Transaction Confirmed!")
                else: st.error("Invalid Entry conditions.")
        else: st.info("데이터 통신 지연. 다시 선택해주세요.")

# --- TAB 2: WALLET ---
with tab2:
    if u_trades:
        pdf = pd.DataFrame(u_trades)
        for t in pdf['티커'].unique():
            try: pdf.loc[pdf['티커']==t, '현재'] = float(yf.Ticker(t).history(period="1d")['Close'].iloc[-1])
            except Exception: pdf.loc[pdf['티커']==t, '현재'] = 0.0
        pdf['Profit'] = (pdf['현재'] - pdf['진입가']) * pdf['수량']
        pnl = float(pdf['Profit'].sum())
        invested = float((pdf['진입가']*pdf['수량']).sum())
        pct = float((pnl/invested)*100) if invested > 0 else 0.0
        
        st.markdown(f"<div class='metric-card'><div class='metric-title'>Available Balance</div><div class='metric-value'>${pnl:,.2f}</div><div class='metric-sub' style='color:{'#667eea' if pct>=0 else '#ef4444'};'>{pct:.2f}% ROI</div></div>", unsafe_allow_html=True)
        st.dataframe(pdf[['티커', '진입가', '현재', '수량', 'Profit']], column_config={"진입가": st.column_config.NumberColumn(format="$%.2f"), "현재": st.column_config.NumberColumn(format="$%.2f"), "Profit": st.column_config.NumberColumn("수익", format="$%.2f")}, use_container_width=True, hide_index=True)
        if st.button("RESET WALLET", use_container_width=True): u_trades.clear(); sync_and_save(); st.rerun()
    else: st.info("No Active Assets.")

# --- TAB 3: RANKING ---
with tab3:
    st.markdown("<div class='metric-title'>SPENDINGS CATEGORIES</div>", unsafe_allow_html=True)
    all_users = st.session_state.full_db.get("users", {})
    l_data = []
    for uname, udata in all_users.items():
        trds = udata.get("paper_trades", [])
        if not trds: continue
        u_pnl = 0.0; u_inv = 0.0
        for trd in trds:
            try:
                cp = float(yf.Ticker(trd["티커"]).history(period="1d")['Close'].iloc[-1])
                u_pnl += (cp - float(trd["진입가"])) * int(trd["수량"]); u_inv += float(trd["진입가"]) * int(trd["수량"])
            except: pass
        u_pct = float((u_pnl / u_inv) * 100) if u_inv > 0 else 0.0
        l_data.append({"Trader": str(uname), "Profit": u_pnl, "ROI": u_pct})

    if l_data:
        ldf = pd.DataFrame(l_data).sort_values(by="ROI", ascending=False)
        colors = ['#667eea' if r > 0 else '#ef4444' for r in ldf['ROI']]
        fig = go.Figure(data=[go.Bar(x=ldf['Trader'], y=ldf['ROI'], marker_color=colors, text=[f"{r:.1f}%" for r in ldf['ROI']], textposition='auto')])
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else: st.info("No Ranking Data.")

st.button("refresh", key="auto_refresh", help="hidden_refresh")
st.markdown("""<style>div[data-testid="stButton"]:has(button[title="hidden_refresh"]) { display: none !important; }</style>""", unsafe_allow_html=True)
components.html("""<script>let t = 60; setInterval(() => { t--; if(t<=0) { t=60; const btn = window.parent.document.querySelector('button[title="hidden_refresh"]'); if(btn) btn.click(); } }, 1000);</script>""", height=0)

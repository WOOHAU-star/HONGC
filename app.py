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
# 1. 환경 설정 및 키 입력
# ==========================================
DB_FILE = "apex_database.json"
MY_JSONBIN_KEY = st.secrets.get("JSONBIN_KEY")
MY_JSONBIN_ID = st.secrets.get("JSONBIN_ID")

TICKER_INFO = {
    "AAPL": ("애플", "빅테크"), "MSFT": ("마이크로소프트", "빅테크"), "GOOGL": ("구글", "빅테크"), "AMZN": ("아마존", "빅테크"),
    "META": ("메타", "빅테크"), "TSLA": ("테슬라", "빅테크"), "NVDA": ("엔비디아", "빅테크"), "NFLX": ("넷플릭스", "빅테크"),
    "ADBE": ("어도비", "빅테크"), "CRM": ("세일즈포스", "빅테크"), "ORCL": ("오라클", "빅테크"), "CSCO": ("시스코", "빅테크"),
    "IBM": ("IBM", "빅테크"), "INTC": ("인텔", "빅테크"), "QCOM": ("퀄컴", "빅테크"), "TXN": ("텍사스인스트루먼트", "빅테크"),
    "AVGO": ("브로드컴", "빅테크"), "AMAT": ("어플라이드머티", "빅테크"), "MU": ("마이크론", "빅테크"), "AMD": ("AMD", "빅테크"),
    "TSM": ("TSMC", "반도체"), "ASML": ("ASML", "반도체"), "ARM": ("ARM", "반도체"), "SMCI": ("슈퍼마이크로", "반도체"),
    "KLAC": ("KLA", "반도체"), "SNPS": ("시놉시스", "반도체"), "CDNS": ("케이던스", "반도체"), "NXPI": ("NXP", "반도체"),
    "MCHP": ("마이크로칩", "반도체"), "LRCX": ("램리서치", "반도체"), "MRVL": ("마벨", "반도체"), "MPWR": ("모놀리식", "반도체"),
    "ON": ("온세미", "반도체"), "SWKS": ("스카이웍스", "반도체"), "TER": ("테라다인", "반도체"), "WDC": ("웨스턴디지털", "반도체"),
    "STM": ("ST마이크로", "반도체"), "GFS": ("글로벌파운드리", "반도체"), "ENTG": ("인테그리스", "반도체"), "QRVO": ("코보", "반도체"),
    "RIVN": ("리비안", "전기차"), "LCID": ("루시드", "전기차"), "F": ("포드", "전기차"), "GM": ("GM", "전기차"),
    "NIO": ("니오", "전기차"), "XPEV": ("샤오펑", "전기차"), "LI": ("리오토", "전기차"), "ALB": ("앨범말", "전기차"),
    "PLUG": ("플러그파워", "에너지"), "ENPH": ("엔페이즈", "에너지"), "MBLY": ("모빌아이", "자율주행"), "LAZR": ("루미나", "자율주행"),
    "QS": ("퀀텀스케이프", "배터리"), "CHPT": ("차지포인트", "충전"), "RUN": ("선런", "에너지"), "BLDP": ("발라드", "에너지"),
    "FSR": ("피스커", "전기차"), "NKLA": ("니콜라", "전기차"), "PTRA": ("프로테라", "전기차"), "ARVL": ("어라이벌", "전기차"),
    "LLY": ("일라이릴리", "바이오"), "UNH": ("유나이티드헬스", "헬스케어"), "JNJ": ("존슨앤존슨", "헬스케어"), "MRK": ("머크", "바이오"),
    "ABBV": ("애브비", "바이오"), "PFE": ("화이자", "바이오"), "AMGN": ("암젠", "바이오"), "GILD": ("길리어드", "바이오"),
    "BMY": ("브리스톨마이어", "바이오"), "CVS": ("CVS헬스", "유통"), "TMO": ("써모피셔", "의료장비"), "MDT": ("메드트로닉", "의료장비"),
    "DHR": ("다나허", "의료장비"), "ABT": ("애보트", "의료장비"), "ISRG": ("인튜이티브", "의료장비"), "SYK": ("스트라이커", "의료장비"),
    "VRTX": ("버텍스", "바이오"), "ZTS": ("조에티스", "동물헬스"), "REGN": ("리제네론", "바이오"), "BSX": ("보스턴사이언", "의료장비"),
    "JPM": ("JP모건", "금융"), "BAC": ("뱅크오브아메리카", "금융"), "V": ("비자", "결제"), "MA": ("마스터카드", "결제"),
    "PYPL": ("페이팔", "핀테크"), "SQ": ("블록", "핀테크"), "HOOD": ("로빈후드", "핀테크"), "COIN": ("코인베이스", "코인"),
    "GS": ("골드만삭스", "금융"), "MS": ("모건스탠리", "금융"), "WFC": ("웰스파고", "금융"), "C": ("씨티그룹", "금융"),
    "AXP": ("아멕스", "결제"), "BLK": ("블랙록", "금융"), "SCHW": ("찰스슈왑", "금융"), "MCO": ("무디스", "금융"),
    "SPGI": ("S&P글로벌", "금융"), "CME": ("CME그룹", "거래소"), "ICE": ("ICE", "거래소"), "CB": ("첩", "보험"),
    "CRWD": ("크라우드스트라이크", "보안"), "PANW": ("팔로알토", "보안"), "FTNT": ("포티넷", "보안"), "PLTR": ("팔란티어", "보안"),
    "SHOP": ("쇼피파이", "클라우드"), "UBER": ("우버", "모빌리티"), "TEAM": ("아틀라시안", "소프트웨어"), "SNOW": ("스노우플레이크", "클라우드"),
    "LMT": ("록히드마틴", "방산"), "RTX": ("RTX", "방산"), "BA": ("보잉", "우주항공"), "NOC": ("노스롭그루먼", "방산"),
    "CPNG": ("쿠팡", "이커머스"), "WMT": ("월마트", "유통"), "HD": ("홈디포", "유통"), "PG": ("P&G", "소비재"),
    "COST": ("코스트코", "유통"), "TGT": ("타겟", "유통"), "KO": ("코카콜라", "소비재"), "PEP": ("펩시", "소비재"),
    "MCD": ("맥도날드", "소비재"), "NKE": ("나이키", "소비재"), "SBUX": ("스타벅스", "소비재"),
    "XOM": ("엑슨모빌", "에너지"), "CVX": ("셰브론", "에너지"), "SHEL": ("쉘", "에너지"), "COP": ("코노코필립스", "에너지")
}

class TacticalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

def load_db():
    key, bin_id = MY_JSONBIN_KEY, MY_JSONBIN_ID
    db = {"users": {"Admin": {"favorites": [], "settings": {"fixed_k": 0.5, "stop_loss_pct": 4.0, "base_rr_ratio": 2.0}}}}
    if key and bin_id:
        try:
            req = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}/latest", headers={"X-Master-Key": key}, timeout=5)
            if req.status_code == 200: db = req.json().get("record", db)
        except: pass
    return db

def save_db(full_db):
    key, bin_id = MY_JSONBIN_KEY, MY_JSONBIN_ID
    current_u = st.session_state.get("current_user")
    if key and bin_id and current_u:
        try:
            requests.put(f"https://api.jsonbin.io/v3/b/{bin_id}", data=json.dumps(full_db, cls=TacticalEncoder), headers={"Content-Type": "application/json", "X-Master-Key": key}, timeout=5)
        except: pass

# ==========================================
# 2. UI 및 압축 레이아웃 CSS
# ==========================================
st.set_page_config(page_title="APEX V64.0", layout="wide")
if 'full_db' not in st.session_state: st.session_state.full_db = load_db()

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; background-color: #0b0e14; color: #e2e8f0; }
    .stApp { background-color: #0b0e14; }
    
    .vip-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; background: #151921; padding: 10px 15px; border-radius: 8px; border: 1px solid #232e4a; margin: 5px 0; }
    .vip-title { font-size: 20px; font-weight: 900; color: #3b82f6; margin: 0; }
    .vip-sub { font-size: 13px; color: #8193b2; margin-left: 10px; }
    .vip-data { text-align: center; }
    .vip-label { font-size: 10px; color: #64748b; margin-bottom: -3px; }
    .vip-value { font-size: 16px; font-weight: 800; }
    
    .global-hit-banner { background: linear-gradient(90deg, rgba(16,185,129,0.15) 0%, rgba(16,185,129,0) 100%); border-left: 4px solid #10b981; padding: 8px 15px; margin: 10px 0; font-weight: 800; color: #6ee7b7; font-size: 14px; }
    .theme-hit-banner { background: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; border-radius: 6px; padding: 8px 12px; font-weight: 800; color: #93c5fd; font-size: 13px; margin-bottom: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

def get_info(ticker):
    info = TICKER_INFO.get(ticker, (ticker, "기타"))
    return info[0], info[1]

# ==========================================
# 3. 차트 (5MA + 20MA 추가 및 데이터 슬라이싱)
# ==========================================
def draw_chart(ticker, target, tp, sl):
    try:
        # 20일선을 완벽히 구하기 위해 3개월치 데이터 다운로드
        df_full = yf.Ticker(ticker).history(period="3mo")
        if df_full.empty: return None
        
        # 이평선 계산
        df_full['5MA'] = df_full['Close'].rolling(5).mean()
        df_full['20MA'] = df_full['Close'].rolling(20).mean()
        
        # 화면에는 최근 30일(약 1개월)만 깔끔하게 출력
        df = df_full.iloc[-30:].copy()
        df.index = df.index.strftime('%m-%d')
        
        y_min, y_max = float(df['Low'].min() * 0.96), float(df['High'].max() * 1.04)
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
        
        # 캔들
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#ef4444', decreasing_line_color='#3b82f6', increasing_fillcolor='#ef4444', decreasing_fillcolor='#3b82f6', name="Price"), row=1, col=1)
        
        # 5일선 (노랑) & 20일선 (핑크 점선)
        fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#eab308', width=1.5), name='5MA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['20MA'], line=dict(color='#ec4899', width=1.5, dash='dot'), name='20MA'), row=1, col=1)
        
        # 거래량 및 전술 라인
        v_cols = ['#ef4444' if c >= o else '#3b82f6' for o, c in zip(df['Open'], df['Close'])]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=v_cols, opacity=0.8), row=2, col=1)
        fig.add_hline(y=float(target), line_dash="dash", line_color="#10b981", annotation_text="ENTRY", row=1, col=1)
        fig.add_hline(y=float(sl), line_dash="solid", line_color="#ef4444", annotation_text="SL", row=1, col=1)
        fig.add_hline(y=float(tp), line_dash="dot", line_color="#3b82f6", annotation_text="TP", row=1, col=1)
        
        fig.update_xaxes(type='category', rangeslider_visible=False, fixedrange=True, showgrid=True, gridcolor='#1e293b')
        fig.update_yaxes(fixedrange=True, gridcolor='#1e293b', row=1, col=1, range=[y_min, y_max])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=40, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', dragmode=False, showlegend=False)
        return fig
    except: return None

# ==========================================
# 4. 스캔 엔진
# ==========================================
@st.cache_data(ttl=60)
def turbo_scan_engine(tickers, k, sl_p):
    if not tickers: return pd.DataFrame()
    res = []
    try:
        df_all = yf.download(tickers, period="40d", group_by='ticker', threads=True, progress=False)
        for t in tickers:
            try:
                df = df_all[t].dropna() if len(tickers) > 1 else df_all.dropna()
                if len(df) < 20: continue
                yest, today = df.iloc[-2], df.iloc[-1]
                curr, op = float(today['Close']), float(today['Open'])
                ma5 = float(df['Close'].rolling(5).mean().iloc[-1])
                target = op + ((float(yest['High'] - yest['Low'])) * k)
                sl, tp = target * (1 - sl_p/100), target + (target * (1 - sl_p/100) * 2.0)
                sig = "🎯 BUY" if curr >= target and op > ma5 else ("❄️ WAIT" if op <= ma5 else "👀 WATCH")
                name, sector = get_info(t)
                res.append({"Ticker": t, "Name": name, "Sector": sector, "Price": curr, "Chg": ((curr-float(yest['Close']))/float(yest['Close']))*100, "Signal": sig, "Target": target, "TP": tp, "SL": sl})
            except: continue
    except: pass
    return pd.DataFrame(res)

# ==========================================
# 5. 메인 UI
# ==========================================
if 'current_user' not in st.session_state:
    st.markdown("<h1 style='text-align:center;'>APEX <span style='color:#3b82f6;'>RADAR</span></h1>", unsafe_allow_html=True)
    uid = st.text_input("CALLSIGN", max_chars=8)
    if st.button("START"): st.session_state.current_user = uid; st.rerun()
    st.stop()

u_data = st.session_state.full_db["users"][st.session_state.current_user]
SECTORS_LIST = {
    "🌟 1. 빅테크": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "QCOM", "TXN", "AVGO", "AMAT", "MU", "AMD"],
    "💻 2. AI & 반도체": ["TSM", "ASML", "ARM", "SMCI", "KLAC", "SNPS", "CDNS", "NXPI", "MCHP", "LRCX", "MRVL", "MPWR", "ON", "SWKS", "TER", "WDC", "STM", "GFS", "ENTG", "QRVO"],
    "⚡ 3. 전기차": ["RIVN", "LCID", "F", "GM", "NIO", "XPEV", "LI", "ALB", "PLUG", "ENPH", "MBLY", "LAZR", "QS", "CHPT", "RUN", "BLDP", "FSR", "NKLA", "PTRA", "ARVL"],
    "🧬 4. 바이오": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "AMGN", "GILD", "BMY", "CVS", "TMO", "MDT", "DHR", "ABT", "ISRG", "SYK", "VRTX", "ZTS", "REGN", "BSX"],
    "🏦 5. 금융": ["JPM", "BAC", "V", "MA", "PYPL", "SQ", "HOOD", "COIN", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "MCO", "SPGI", "CME", "ICE", "CB"],
    "🛡️ 6. 사이버보안": ["CRWD", "PANW", "FTNT", "NOW", "SNOW", "PLTR", "DDOG", "NET", "ZS", "OKTA", "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "RPD", "S", "MNDT", "FEYE", "NLOK"],
    "☁️ 7. 클라우드": ["SHOP", "UBER", "MNDY", "TEAM", "NET", "DOCN", "CFLT", "MDB", "PATH", "ESTC", "DT", "HCP", "FIVN", "SMAR", "AYX", "BOX", "PD", "ZEN", "DBX", "WK"],
    "🚀 8. 방산": ["LMT", "RTX", "NOC", "GD", "BA", "TDG", "HEI", "HII", "TXT", "LHX", "KTOS", "CUB", "KAMN", "AJRD", "AVAV", "MOG-A", "ATRO", "SPCE", "RKLB", "ASTS"],
    "🛒 9. 소비재": ["CPNG", "WMT", "HD", "PG", "COST", "TGT", "KO", "PEP", "MCD", "NKE", "SBUX", "MELI", "SE", "EBAY", "ETSY", "WAY", "CHWY", "PINS", "FTCH", "W"],
    "🛢️ 10. 에너지": ["XOM", "CVX", "SHEL", "COP", "TTE", "BP", "EQNR", "OXY", "EOG", "FSLR", "SEDG", "DQ", "SPWR", "NEP", "BEP", "CWEN", "HASI", "AY", "PEGI", "HAL"]
}

all_ticks = list(set([t for v in SECTORS_LIST.values() for t in v]))
with st.spinner("⚡ 전체 섹터 정찰 중..."): df_global = turbo_scan_engine(all_ticks, float(u_data['settings']['fixed_k']), float(u_data['settings']['stop_loss_pct']))

st.markdown("<div class='global-hit-banner'>🔥 실시간 전 섹터 타점 도달 브리핑</div>", unsafe_allow_html=True)
hits = df_global[df_global['Signal'] == '🎯 BUY'].copy()

if not hits.empty:
    hits = hits.sort_values(by='Chg', ascending=False)
    sel_hits = st.dataframe(hits[['Ticker', 'Name', 'Sector', 'Price', 'Chg']], on_select="rerun", selection_mode="single-row",
                            column_config={"Ticker": "코드", "Name": "회사명", "Sector": "섹터", "Price": st.column_config.NumberColumn("가", format="$%.2f"), "Chg": st.column_config.NumberColumn("%", format="%.1f%%")}, use_container_width=True, hide_index=True, height=150)
    if sel_hits.selection.rows:
        row = hits.iloc[sel_hits.selection.rows[0]]
        st.markdown(f"<div class='vip-header'><div class='vip-title'>{row['Ticker']} <span class='vip-sub'>{row['Name']} | {row['Sector']}</span></div><div class='vip-data-group'><div class='vip-data'><div class='vip-label'>ENTRY</div><div class='vip-value' style='color:#10b981;'>${row['Target']:.2f}</div></div><div class='vip-data'><div class='vip-label'>TP</div><div class='vip-value' style='color:#3b82f6;'>${row['TP']:.2f}</div></div><div class='vip-data'><div class='vip-label'>SL</div><div class='vip-value' style='color:#ef4444;'>${row['SL']:.2f}</div></div></div></div>", unsafe_allow_html=True)
        fig = draw_chart(row['Ticker'], row['Target'], row['TP'], row['SL'])
        if fig: st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else: st.info("현재 모든 섹터가 관망세입니다.")

st.divider()

# --- 테마별 상세 스캔 (정렬 및 카운트 기능 추가) ---
st.markdown("### 📂 테마별 상세 분석")
sel_sec = st.selectbox("섹터 선택", list(SECTORS_LIST.keys()), label_visibility="collapsed")
df_sec = turbo_scan_engine(SECTORS_LIST[sel_sec], float(u_data['settings']['fixed_k']), float(u_data['settings']['stop_loss_pct']))

if not df_sec.empty:
    # 1. 시그널 기반 자동 정렬 (BUY -> WATCH -> WAIT)
    sort_map = {"🎯 BUY": 0, "👀 WATCH": 1, "❄️ WAIT": 2}
    df_sec['sort_idx'] = df_sec['Signal'].map(sort_map)
    df_sec = df_sec.sort_values(by=['sort_idx', 'Chg'], ascending=[True, False]).drop(columns=['sort_idx'])
    
    # 2. 타점 도달 카운트 배너
    hit_count = len(df_sec[df_sec['Signal'] == '🎯 BUY'])
    if hit_count > 0:
        st.markdown(f"<div class='theme-hit-banner'>🎯 현재 테마 내 진입 가능 종목: {hit_count}개</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='theme-hit-banner' style='color:#8193b2; border-color:#232e4a; background:transparent;'>현재 테마는 모두 관망/대기 상태입니다.</div>", unsafe_allow_html=True)

    sel_sec_df = st.dataframe(df_sec[['Ticker', 'Name', 'Price', 'Signal']], on_select="rerun", selection_mode="single-row",
                              column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Signal": st.column_config.TextColumn("상태")},
                              use_container_width=True, hide_index=True, height=250)
    
    if sel_sec_df.selection.rows:
        row_s = df_sec.iloc[sel_sec_df.selection.rows[0]]
        st.markdown(f"<div class='vip-header'><div class='vip-title'>{row_s['Ticker']} <span class='vip-sub'>{row_s['Name']}</span></div><div class='vip-data-group'><div class='vip-data'><div class='vip-label'>ENTRY</div><div class='vip-value' style='color:#10b981;'>${row_s['Target']:.2f}</div></div><div class='vip-data'><div class='vip-label'>TP</div><div class='vip-value' style='color:#3b82f6;'>${row_s['TP']:.2f}</div></div><div class='vip-data'><div class='vip-label'>SL</div><div class='vip-value' style='color:#ef4444;'>${row_s['SL']:.2f}</div></div></div></div>", unsafe_allow_html=True)
        fig_s = draw_chart(row_s['Ticker'], row_s['Target'], row_s['TP'], row_s['SL'])
        if fig_s: st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

# 사이드바
with st.sidebar:
    st.title(f"👤 {st.session_state.current_user}")
    u_data['settings']['fixed_k'] = st.slider("K", 0.3, 0.8, float(u_data['settings']['fixed_k']), 0.05)
    u_data['settings']['stop_loss_pct'] = st.slider("SL%", 1.0, 10.0, float(u_data['settings']['stop_loss_pct']), 0.5)
    if st.button("SAVE"): save_db(st.session_state.full_db); st.success("Saved.")

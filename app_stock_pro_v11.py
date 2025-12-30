import streamlit as st
import random
import os
import re
import time
import requests
import pandas as pd
import yfinance as yf
from pathlib import Path
from dataclasses import dataclass
import plotly.graph_objects as go

# =====================
# Imports & Config
# =====================
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from streamlit_lottie import st_lottie
except ImportError:
    st_lottie = None

APP_TITLE = "Quantum Tarot | 量化塔羅"
DEFAULT_CARD_DIR = "Cards-jpg"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MODEL_NAME = "models/gemini-2.5-flash"

GEMINI_API_KEY = None
if hasattr(st, "secrets"):
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)
GEMINI_API_KEY = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")

# =====================
# Lottie
# =====================
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=3)
        return r.json() if r.status_code == 200 else None
    except:
        return None

LOTTIE_URLS = {
    "finance": "https://lottie.host/807e3661-002d-44a1-b883-93d39695fa9f/9sQW3qF1y3.json",
    "ai": "https://lottie.host/4e90768b-980e-4424-967a-0639e4466b02/tC6U7tXy8l.json",
    "tarot": "https://lottie.host/64f0f62b-6581-42cb-b40b-7419e61c3371/X100fT4a9H.json"
}

# =====================
# CSS: 午夜藍 + 金色 主題 (含手機版修復)
# =====================
def inject_custom_css():
    st.markdown("""
    <style>
    /* 強制亮色模式樣式，避免手機 Dark Mode 造成字體看不見 */
    [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        color: #262730 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        border-right: 1px solid #DEE2E6;
    }
    
    /* 標題與重點色 */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { 
        color: #1a237e !important; 
        font-family: 'Helvetica Neue', 'Microsoft JhengHei', sans-serif;
        font-weight: 700 !important;
    }
    
    /* 普通文字顏色 */
    p, span, div, li, .stMarkdown, .stText {
        color: #262730;
    }

    /* Hero Section 容器 */
    .hero-container {
        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
        color: white !important;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        margin-bottom: 25px;
        text-align: center;
    }
    .hero-container * {
        color: white !important;
    }
    .hero-title {
        color: #ffd700 !important;
        font-size: 1.8rem;
        margin-bottom: 5px;
    }
    .hero-metric-label {
        font-size: 0.9rem;
        opacity: 0.8;
        color: #e3f2fd;
    }
    .hero-metric-value {
        font-size: 1.5rem;
        font-weight: bold;
    }
    
    /* 卡片與容器 */
    .report-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 12px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); 
        border-top: 5px solid #1a237e; 
        margin-top: 10px; 
    }
    .news-card { 
        background-color: #f8f9fa; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 12px; 
        font-size: 0.95rem; 
        border-left: 3px solid #ffd700;
        transition: all 0.2s ease;
    }
    .news-card:hover {
        transform: translateX(5px);
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* 塔羅牌容器 */
    .tarot-img-container img {
        border-radius: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        transition: transform 0.3s ease;
    }
    .tarot-img-container img:hover {
        transform: translateY(-5px);
    }
    
    /* 針對手機深色模式的修復 (Media Query) */
    @media (prefers-color-scheme: dark) {
        body { background-color: #FFFFFF !important; }
        .stApp { background-color: #FFFFFF !important; }
        p, span, div, li { color: #262730 !important; }
        /* 排除 Hero Section，保持深藍背景 */
        .hero-container {
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%) !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# =====================
# Logic
# =====================
MAJOR_ZH = {"thefool": "愚者", "themagician": "魔術師", "thehighpriestess": "女祭司", "theempress": "皇后", "theemperor": "皇帝", "thehierophant": "教皇", "thelovers": "戀人", "thechariot": "戰車", "strength": "力量", "thehermit": "隱者", "wheeloffortune": "命運之輪", "justice": "正義", "thehangedman": "倒吊人", "death": "死神", "temperance": "節制", "thedevil": "惡魔", "thetower": "高塔", "thestar": "星星", "themoon": "月亮", "thesun": "太陽", "judgement": "審判", "theworld": "世界"}
SUIT_ZH = {"cups": "聖杯", "wands": "權杖", "swords": "寶劍", "pentacles": "錢幣"}
COURT_ZH = {"page": "侍者", "knight": "騎士", "queen": "皇后", "king": "國王"}
RANK_ZH = {"ace": "A", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "10"}

@dataclass
class Card:
    key: str; name: str; path: str

def parse_card_filename(stem: str) -> str:
    s = stem.lower().replace("-", "_").replace(" ", "_")
    s = re.sub(r"_+", "_", s)
    m = re.match(r"^(\d{1,2})_(.+)$", s)
    if m:
        num = m.group(1)
        token = re.sub(r"[^a-z0-9]", "", m.group(2))
        return f"{MAJOR_ZH.get(token, m.group(2).title())}"
    m = re.match(r"^(cups|wands|swords|pentacles)_?(ace|\d{1,2}|page|knight|queen|king)$", s)
    if m:
        suit, rank = m.group(1), m.group(2)
        return f"{SUIT_ZH.get(suit, suit)} {COURT_ZH.get(rank, RANK_ZH.get(rank, rank))}"
    return s.title()

@st.cache_data(show_spinner=False)
def load_cards(card_dir: str):
    p = Path(card_dir)
    if not p.exists(): return []
    files = [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]
    return [Card(key=f.stem.lower(), name=parse_card_filename(f.stem), path=str(f)) for f in sorted(files)]

def get_stock_and_news(symbol: str):
    if not yf: return None, "❌ 系統維護中", []
    if symbol.isdigit() and len(symbol) == 4: symbol = f"{symbol}.TW"
    metrics = {}
    news_list = []
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1mo")
        if hist.empty: return None, "❌ 查無此代號", []
        
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = (current - prev) / prev * 100
        avg_vol = hist['Volume'].mean()
        today_vol = hist['Volume'].iloc[-1]
        vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        metrics = {
            "price": f"{current:.2f}",
            "change": f"{change:+.2f}%",
            "vol_ratio": f"{vol_ratio:.1f}x",
            "rsi": f"{rsi:.1f}",
            "raw_data_str": f"現價{current:.2f}, 漲跌{change:.2f}%, 量能{vol_ratio:.1f}倍, RSI{rsi:.1f}"
        }
        
        try:
            news_data = stock.news
            if news_data:
                for n in news_data[:3]:
                    news_list.append(f"- {n.get('title', '無標題')} ({n.get('publisher', '未知來源')})")
        except:
            news_list.append("⚠️ 暫無相關新聞或抓取失敗")
            
    except Exception as e:
        return None, str(e), []
    return metrics, None, news_list

def _call_gemini(prompt):
    if not genai or not GEMINI_API_KEY: return "⚠️ AI 系統忙碌中"
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        return model.generate_content(prompt).text
    except:
        return "⚠️ AI 連線逾時，請重試"

# =====================
# Gauge Chart
# =====================
def plot_gauge(score, mode="stock"):
    is_stock = mode == "stock"
    
    # 顏色配置
    if is_stock:
        steps = [
            {'range': [0, 30], 'color': '#ef5350'},   # Red
            {'range': [30, 70], 'color': '#ffca28'},  # Amber
            {'range': [70, 100], 'color': '#66bb6a'}  # Green
        ]
        line_color = "#263238"
        bar_color = "rgba(0,0,0,0)" # 透明，只顯示 steps
    else:
        steps = [
            {'range': [0, 30], 'color': '#ab47bc'},   # Purple 300
            {'range': [30, 70], 'color': '#7e57c2'},  # Deep Purple 400
            {'range': [70, 100], 'color': '#512da8'}  # Deep Purple 700
        ]
        line_color = "#311b92"
        bar_color = "rgba(0,0,0,0)"

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        number = {'font': {'size': 40, 'color': '#1a237e'}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "gray"},
            'bar': {'color': bar_color},
            'bgcolor': "white",
            'borderwidth': 0,
            'steps': steps,
            'threshold': {
                'line': {'color': line_color, 'width': 5},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=30, b=30), paper_bgcolor='rgba(0,0,0,0)', font={'family': "Microsoft JhengHei"})
    return fig

# =====================
# UI
# =====================
st.set_page_config(page_title="Quantum Tarot", layout="wide", page_icon="🔮")
inject_custom_css()

# Header
c1, c2 = st.columns([0.85, 0.15])
with c1:
    st.title("Quantum Tarot | 量化塔羅")
    st.caption("融合華爾街量化數據與榮格心理學的決策輔助系統 V12")
with c2:
    if load_lottieurl(LOTTIE_URLS["finance"]): 
        st_lottie(load_lottieurl(LOTTIE_URLS["finance"]), height=60, key="head_anim")

st.divider()

# Sidebar
with st.sidebar:
    st.header("⚙️ 控制面板")
    mode = st.radio("模式選擇", ["股票分析", "一般占卜 (開放式)"], captions=["結合即時數據", "心靈指引"])
    
    st.markdown("---")
    
    if mode == "股票分析":
        symbol = st.text_input("股票代號", placeholder="例如：2330, NVDA").upper()
        style = st.selectbox("操作風格", ["短線當沖 (Day Trading)", "波段操作 (Swing)", "長線價值 (Value)"])
    else:
        question = st.text_area("請輸入您的問題", height=120, placeholder="例如：最近工作運勢如何？\n這個專案該不該接？")
        
    st.markdown("---")
    run_btn = st.button("🚀 開始分析", type="primary", use_container_width=True)
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.caption("v12.0.0 | Powered by Gemini 2.0")

cards = load_cards(DEFAULT_CARD_DIR)
if not cards: st.stop()

if "state" not in st.session_state:
    st.session_state.state = {"data": None, "cards": [], "analysis": None, "news": [], "score": None}

# Execution
if run_btn:
    
    # === 股票模式 ===
    if mode == "股票分析":
        if not symbol: st.toast("⚠️ 請輸入代號"); st.stop()
        
        with st.status("📡 正在連接交易所與宇宙場域...", expanded=True) as status:
            st.write("正在抓取即時報價...")
            data, err, news = get_stock_and_news(symbol)
            if err: status.update(label="❌ 錯誤", state="error"); st.error(err); st.stop()
            
            st.write("正在抽取塔羅牌...")
            drawn = random.sample(cards, k=3)
            time.sleep(0.5)
            
            st.write("AI 正在進行深度解讀...")
            news_str = "\n".join(news)
            prompt = f"""
            你是一位華爾街資深分析師。請用【繁體中文】分析。
            【標的】：{symbol}
            【數據】：{data['raw_data_str']}
            【新聞】：{news_str}
            【塔羅】：{[c.name for c in drawn]}
            【風格】：{style}
            
            請依序輸出：
            1. 【信心分數】：(請只輸出一個數字，0-100)
            2. 詳細分析報告 (Markdown format)
            """
            full_response = _call_gemini(prompt)
            
            score_match = re.search(r"(\d{1,3})", full_response[:50]) 
            score = int(score_match.group(1)) if score_match else 50
            analysis = re.sub(r"【信心分數】.*?\n", "", full_response)
            
            status.update(label="✅ 分析完成！", state="complete", expanded=False)
            
        st.session_state.state = {"data": data, "cards": drawn, "analysis": analysis, "news": news, "score": score, "mode": "stock"}

    # === 一般占卜模式 ===
    else:
        if not question: st.toast("⚠️ 請輸入問題"); st.stop()
        
        with st.status("🔮 正在連結潛意識場域...", expanded=True) as status:
            st.write("正在洗牌...")
            time.sleep(1)
            drawn = random.sample(cards, k=3)
            
            st.write("AI 正在感應能量...")
            # V12 優化：更精確的 Prompt
            prompt = f"""
            你是一位精通榮格心理學與神秘學的資深塔羅導師。
            使用者問了一個關於「{question}」的問題。
            
            你抽到了以下三張牌，請將它們對應到以下位置：
            1. {drawn[0].name} (代表：現狀/核心問題)
            2. {drawn[1].name} (代表：建議/行動方向)
            3. {drawn[2].name} (代表：未來/潛在結果)
            
            請務必針對「{question}」這個問題進行回答，不要給出空泛的解釋。
            用溫暖、有洞見且具體的語氣。
            
            請依序輸出：
            1. 【能量分數】：(請根據牌面好壞給出 0-100 的數字)
            2. 詳細解讀報告 (Markdown format)，包含：
               - 🎴 牌面解析 (請連結牌義與使用者的問題)
               - 🌌 核心訊息 (直指問題核心)
               - 💡 具體建議 (下一步該怎麼做)
            """
            full_response = _call_gemini(prompt)
            
            score_match = re.search(r"(\d{1,3})", full_response[:50]) 
            score = int(score_match.group(1)) if score_match else 50
            analysis = re.sub(r"【能量分數】.*?\n", "", full_response)
            
            status.update(label="✨ 感應完成！", state="complete", expanded=False)
            
        st.session_state.state = {"data": None, "cards": drawn, "analysis": analysis, "news": [], "score": score, "mode": "general"}

# Display Logic
res = st.session_state.state

if res["cards"]:
    
    # === Hero Section (視覺焦點) ===
    is_stock = res.get("mode") == "stock"
    score_title = "AI 多空信心" if is_stock else "能量流動指數"
    
    # 使用 container 包裝 Hero Section
    with st.container():
        c_gauge, c_metrics = st.columns([0.3, 0.7])
        
        with c_gauge:
            fig = plot_gauge(res["score"], res.get("mode"))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown(f"<div style='text-align:center; margin-top:-20px; font-weight:bold; color:#555;'>{score_title}</div>", unsafe_allow_html=True)
            
        with c_metrics:
            if is_stock and res["data"]:
                st.markdown(f"""
                <div class="hero-container">
                    <div class="hero-title">{symbol} 市場概況</div>
                    <div style="display:flex; justify-content:space-around; margin-top:15px;">
                        <div><div class="hero-metric-label">現價</div><div class="hero-metric-value">{res['data']['price']}</div></div>
                        <div><div class="hero-metric-label">漲跌</div><div class="hero-metric-value">{res['data']['change']}</div></div>
                        <div><div class="hero-metric-label">RSI</div><div class="hero-metric-value">{res['data']['rsi']}</div></div>
                        <div><div class="hero-metric-label">量能</div><div class="hero-metric-value">{res['data']['vol_ratio']}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                 st.markdown(f"""
                <div class="hero-container" style="background: linear-gradient(135deg, #4a148c 0%, #7b1fa2 100%);">
                    <div class="hero-title">🔮 潛意識能量場</div>
                    <div style="margin-top:10px; font-size:1.1rem; opacity:0.9;">
                        "{question[:30]}..."
                    </div>
                    <div style="margin-top:15px; font-size:0.9rem; opacity:0.8;">
                        宇宙訊息已下載完成，請參考下方深度解讀。
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # === Tabs 分頁設計 (優化版面) ===
    st.write("")
    tab1, tab2, tab3 = st.tabs(["🎴 牌面與分析", "📰 市場資訊 / 詳情", "⚙️ 原始數據"])
    
    with tab1:
        # 牌面展示
        st.subheader("抽牌結果")
        cols = st.columns(3)
        for i, col in enumerate(cols):
            with col:
                st.markdown('<div class="tarot-img-container">', unsafe_allow_html=True)
                st.image(res["cards"][i].path, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.caption(f"**{res['cards'][i].name}**")
        
        # 深度報告
        st.subheader("深度解讀")
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown(res["analysis"])
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab2:
        if is_stock:
            st.subheader("相關新聞快訊")
            if res["news"]:
                for n in res["news"]:
                    st.markdown(f"<div class='news-card'>{n}</div>", unsafe_allow_html=True)
            else:
                st.info("暫無相關新聞")
        else:
            st.info("此模式無市場新聞數據。")
            st.markdown("### 建議行動")
            st.write("1. 靜心冥想 5 分鐘")
            st.write("2. 記錄下此刻的直覺")
            
    with tab3:
        st.subheader("Debug & Raw Data")
        st.json(res)

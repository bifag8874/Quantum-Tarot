import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd
import random
from datetime import datetime
import time
import os
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 1. 初始設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="量子塔羅 V15.6 - 語法修復版",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 連線設定
# ---------------------------------------------------------
@st.cache_resource
def configure_services():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn, None
    except Exception as e:
        return None, str(e)

conn, err_msg = configure_services()
if err_msg:
    st.error(f"連線失敗: {err_msg}")
    st.stop()

# ---------------------------------------------------------
# 3. 資料庫與工具
# ---------------------------------------------------------
DB_TTL = 0

def get_history(user_id):
    try:
        df = conn.read(ttl=DB_TTL)
        if df.empty or "user_id" not in df.columns: return pd.DataFrame()
        return df[df["user_id"] == user_id].sort_values(by="timestamp", ascending=False)
    except: return pd.DataFrame()

def save_to_history(user_id, q_type, query, cards, summary):
    try:
        df = conn.read(ttl=DB_TTL)
        new_row = pd.DataFrame([{
            "user_id": user_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": q_type,
            "query": str(query).strip(),
            "cards": str(cards).strip(),
            "ai_summary": str(summary).strip()
        }])
        if df.empty: updated_df = new_row
        else: updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        return True
    except: return False

def get_stock_data(symbol):
    try:
        if symbol.isdigit(): symbol = f"{symbol}.TW"
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")
        if hist.empty: return None

        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2] if len(hist) >= 2 else current
        change = current - prev
        pct = (change / prev) * 100

        return {
            "symbol": symbol,
            "price": f"{current:.2f}",
            "change_val": f"{change:.2f}",
            "change_pct": f"{pct:.2f}%",
            "trend": "📈" if change > 0 else "📉" if change < 0 else "➖",
            "volume": f"{hist['Volume'].iloc[-1]:,}"
        }
    except: return None

# ---------------------------------------------------------
# 4. 核心修復：中文牌名 -> 英文檔名 對照表
# ---------------------------------------------------------
TAROT_IMG_MAP = {
    # 大阿爾克那 (00-21)
    "愚者": "00_thefool.jpg", "魔術師": "01_themagician.jpg", "女祭司": "02_thehighpriestess.jpg",
    "皇后": "03_theempress.jpg", "皇帝": "04_theemperor.jpg", "教皇": "05_thehierophant.jpg",
    "戀人": "06_thelovers.jpg", "戰車": "07_thechariot.jpg", "力量": "08_strength.jpg",
    "隱者": "09_thehermit.jpg", "命運之輪": "10_wheeloffortune.jpg", "正義": "11_justice.jpg",
    "吊人": "12_thehangedman.jpg", "死神": "13_death.jpg", "節制": "14_temperance.jpg",
    "惡魔": "15_thedevil.jpg", "塔": "16_thetower.jpg", "星星": "17_thestar.jpg",
    "月亮": "18_themoon.jpg", "太陽": "19_thesun.jpg", "審判": "20_judgement.jpg",
    "世界": "21_theworld.jpg",
    # 權杖 (Wands)
    "權杖一": "wands01.jpg", "權杖二": "wands02.jpg", "權杖三": "wands03.jpg",
    "權杖四": "wands04.jpg", "權杖五": "wands05.jpg", "權杖六": "wands06.jpg",
    "權杖七": "wands07.jpg", "權杖八": "wands08.jpg", "權杖九": "wands09.jpg",
    "權杖十": "wands10.jpg", "權杖侍者": "wands11.jpg", "權杖騎士": "wands12.jpg",
    "權杖王后": "wands13.jpg", "權杖國王": "wands14.jpg",
    # 聖杯 (Cups)
    "聖杯一": "cups01.jpg", "聖杯二": "cups02.jpg", "聖杯三": "cups03.jpg",
    "聖杯四": "cups04.jpg", "聖杯五": "cups05.jpg", "聖杯六": "cups06.jpg",
    "聖杯七": "cups07.jpg", "聖杯八": "cups08.jpg", "聖杯九": "cups09.jpg",
    "聖杯十": "cups10.jpg", "聖杯侍者": "cups11.jpg", "聖杯騎士": "cups12.jpg",
    "聖杯王后": "cups13.jpg", "聖杯國王": "cups14.jpg",
    # 寶劍 (Swords)
    "寶劍一": "swords01.jpg", "寶劍二": "swords02.jpg", "寶劍三": "swords03.jpg",
    "寶劍四": "swords04.jpg", "寶劍五": "swords05.jpg", "寶劍六": "swords06.jpg",
    "寶劍七": "swords07.jpg", "寶劍八": "swords08.jpg", "寶劍九": "swords09.jpg",
    "寶劍十": "swords10.jpg", "寶劍侍者": "swords11.jpg", "寶劍騎士": "swords12.jpg",
    "寶劍王后": "swords13.jpg", "寶劍國王": "swords14.jpg",
    # 錢幣 (Pentacles)
    "錢幣一": "pentacles01.jpg", "錢幣二": "pentacles02.jpg", "錢幣三": "pentacles03.jpg",
    "錢幣四": "pentacles04.jpg", "錢幣五": "pentacles05.jpg", "錢幣六": "pentacles06.jpg",
    "錢幣七": "pentacles07.jpg", "錢幣八": "pentacles08.jpg", "錢幣九": "pentacles09.jpg",
    "錢幣十": "pentacles10.jpg", "錢幣侍者": "pentacles11.jpg", "錢幣騎士": "pentacles12.jpg",
    "錢幣王后": "pentacles13.jpg", "錢幣國王": "pentacles14.jpg"
}

def draw_cards():
    return random.sample(list(TAROT_IMG_MAP.keys()), 3)

# ---------------------------------------------------------
# 5. UI 設定
# ---------------------------------------------------------
with st.sidebar:
    st.title("🎛️ 控制台")
    temp = st.slider("🔮 靈感溫度", 0.0, 1.0, 0.7, 0.1)
    st.divider()
    if "user_id" not in st.session_state: st.session_state.user_id = None
    if st.session_state.user_id:
        st.success(f"Hi, {st.session_state.user_id}")
        if st.button("登出"): 
            st.session_state.user_id = None
            st.rerun()
    else:
        uid = st.text_input("輸入暱稱")
        if st.button("登入") and uid.strip():
            st.session_state.user_id = uid.strip()
            st.rerun()

if not st.session_state.user_id:
    st.info("👈 請先登入")
    st.stop()

history_df = get_history(st.session_state.user_id)
context = ""
if not history_df.empty:
    for _, row in history_df.head(3).iterrows():
        context += f"- {row['timestamp']} | {row['query']} -> {row['cards']}\n"

st.title(f"🔮 V15.6 量子塔羅 - {st.session_state.user_id}")
tab1, tab2, tab3 = st.tabs(["🎴 塔羅", "📈 股票", "📜 紀錄"])

# --- 圖片顯示邏輯 ---
def show_card_images(cards):
    cols = st.columns(3)
    for i, col in enumerate(cols):
        card_name = cards[i]
        filename = TAROT_IMG_MAP.get(card_name, "00_thefool.jpg") # 預設愚者

        # GitHub Raw 路徑 (對應使用者的 Repo 結構)
        github_url = f"https://raw.githubusercontent.com/bifag8874/Quantum-Tarot/main/Cards-jpg/{filename}"

        with col:
            st.image(github_url, caption=card_name, use_container_width=True)

# --- 塔羅 Tab ---
with tab1:
    q = st.text_area("輸入問題...")
    if st.button("抽牌", key="btn_t"):
        if not q: st.warning("請輸入問題")
        else:
            with st.spinner("連結宇宙..."):
                cards = draw_cards()
                cards_str = "、".join(cards)

                show_card_images(cards)

                st.subheader(f"🎴 牌面：{cards_str}")

                # 修正：移除容易造成 SyntaxError 的反斜線
                prompt = f"""你是一位塔羅大師。
{context}
問題：{q}
牌面：{cards_str}

請解析牌義並給出建議。最後一行給【AI 摘要】。
"""
                try:
                    model = genai.GenerativeModel('models/gemini-flash-latest', generation_config=genai.GenerationConfig(temperature=temp))
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    summary = res.text.split("【AI 摘要】")[-1].strip() if "【AI 摘要】" in res.text else "完成"
                    save_to_history(st.session_state.user_id, "塔羅", q, cards_str, summary)
                except Exception as e: st.error(f"AI 錯誤: {e}")

# --- 股票 Tab ---
with tab2:
    s = st.text_input("股票代號 (如 2330)")
    if st.button("分析", key="btn_s"):
        if not s: st.warning("請輸入代號")
        else:
            with st.spinner("分析中..."):
                stock_data = get_stock_data(s)

                if stock_data:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("現價", stock_data['price'], stock_data['change_pct'])
                    c2.metric("漲跌", stock_data['change_val'])
                    c3.metric("趨勢", stock_data['trend'])
                    info_str = f"數據：{stock_data}"
                else:
                    st.warning("⚠️ 無即時數據，進行純預測。")
                    info_str = "無法取得數據"

                cards = draw_cards()

                show_card_images(cards)

                # 修正：移除容易造成 SyntaxError 的反斜線
                prompt = f"""金融占卜師。
{context}
標的：{s}
數據：{info_str}
牌面：{'、'.join(cards)}

請結合數據與牌義分析。最後給【AI 摘要】。
"""
                try:
                    model = genai.GenerativeModel('models/gemini-flash-latest', generation_config=genai.GenerationConfig(temperature=temp))
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                    summary = res.text.split("【AI 摘要】")[-1].strip() if "【AI 摘要】" in res.text else f"分析 {s}"
                    save_to_history(st.session_state.user_id, "股票", s, str(cards), summary)
                except Exception as e: st.error(f"AI 錯誤: {e}")

# --- 紀錄 Tab ---
with tab3:
    if st.button("刷新"): st.rerun()
    if not history_df.empty:
        st.dataframe(history_df[['timestamp', 'query', 'cards', 'ai_summary']], hide_index=True)
    else: st.write("無紀錄")

import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd
import random
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 1. 初始設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="量子塔羅 V15.1 - 視覺增強版",
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
# 3. 資料庫操作
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
    except Exception as e:
        st.warning(f"存檔失敗: {e}")
        return False

# ---------------------------------------------------------
# 4. 工具函數
# ---------------------------------------------------------
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")
        if hist.empty: return None
        current = stock.info.get('currentPrice', hist['Close'].iloc[-1])
        pct = ((current - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        return {"price": f"{current:.2f}", "change": f"{pct:.2f}%", "trend": "漲" if pct>0 else "跌"}
    except: return None

def draw_cards():
    deck = ["愚者", "魔術師", "女祭司", "皇后", "皇帝", "教皇", "戀人", "戰車",
            "力量", "隱者", "命運之輪", "正義", "吊人", "死神", "節制", "惡魔",
            "塔", "星星", "月亮", "太陽", "審判", "世界",
            "權杖一", "權杖國王", "聖杯三", "聖杯王后", "寶劍十", "錢幣騎士"]
    return random.sample(deck, 3)

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

# 準備記憶
history_df = get_history(st.session_state.user_id)
context = ""
if not history_df.empty:
    for _, row in history_df.head(3).iterrows():
        context += f"- {row['timestamp']} | {row['query']} -> {row['cards']}\n"

st.title(f"🔮 V15.1 量子塔羅 - {st.session_state.user_id}")
tab1, tab2, tab3 = st.tabs(["🎴 塔羅", "📈 股票", "📜 紀錄"])

# --- 塔羅 Tab ---
with tab1:
    q = st.text_area("輸入問題...")
    if st.button("抽牌", key="btn_t"):
        if not q: st.warning("請輸入問題")
        else:
            with st.spinner("連結宇宙中..."):
                cards = draw_cards()
                cards_str = "、".join(cards)

                # --- 🖼️ 視覺修復：顯示牌面圖片 ---
                cols = st.columns(3)
                # 這裡暫時用一張通用塔羅圖代表，實際應用可建立 {牌名: URL} 的字典
                img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/RWS_Tarot_00_Fool.jpg/344px-RWS_Tarot_00_Fool.jpg"

                for i, col in enumerate(cols):
                    with col:
                        # 顯示圖片，並在下方標註牌名
                        st.image(img_url, caption=cards[i], use_container_width=True)
                # ----------------------------------

                st.subheader(f"🎴 牌面：{cards_str}")

                prompt = f"""你是一位塔羅大師。
{context}
問題：{q}
牌面：{cards_str}

請提供：
1. 【牌面解析】
2. 【深度建議】
3. 【未來指引】
最後一行請給【AI 摘要】(30字)。
"""
                try:
                    model = genai.GenerativeModel('models/gemini-flash-latest', generation_config=genai.GenerationConfig(temperature=temp))
                    res = model.generate_content(prompt)
                    st.markdown(res.text)

                    summary = res.text.split("【AI 摘要】")[-1].strip() if "【AI 摘要】" in res.text else "完成"
                    save_to_history(st.session_state.user_id, "塔羅", q, cards_str, summary)
                    st.toast("已存檔")
                except Exception as e: st.error(f"AI 錯誤: {e}")

# --- 股票 Tab ---
with tab2:
    s = st.text_input("股票代號")
    if st.button("分析", key="btn_s"):
        if not s: st.warning("請輸入代號")
        else:
            with st.spinner("分析中..."):
                data = get_stock_data(s)
                info = str(data) if data else "無數據"
                cards = draw_cards()

                # --- 🖼️ 視覺修復 ---
                cols = st.columns(3)
                img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/RWS_Tarot_01_Magician.jpg/352px-RWS_Tarot_01_Magician.jpg"
                for i, col in enumerate(cols):
                    with col:
                        st.image(img_url, caption=cards[i], use_container_width=True)
                # -------------------

                if data: st.info(f"📊 {data['price']} | {data['change']}")

                prompt = f"""金融占卜師。
{context}
標的：{s}
數據：{info}
牌面：{'、'.join(cards)}

請分析市場與玄學。最後給【AI 摘要】。
"""
                try:
                    model = genai.GenerativeModel('models/gemini-flash-latest', generation_config=genai.GenerationConfig(temperature=temp))
                    res = model.generate_content(prompt)
                    st.markdown(res.text)

                    summary = res.text.split("【AI 摘要】")[-1].strip() if "【AI 摘要】" in res.text else f"分析 {s}"
                    save_to_history(st.session_state.user_id, "股票", s, str(cards), summary)
                    st.toast("已存檔")
                except Exception as e: st.error(f"AI 錯誤: {e}")

# --- 紀錄 Tab ---
with tab3:
    if st.button("刷新"): st.rerun()
    if not history_df.empty:
        st.dataframe(history_df[['timestamp', 'query', 'cards', 'ai_summary']], hide_index=True)
    else: st.write("無紀錄")

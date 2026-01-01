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
    page_title="量子塔羅 V15.3 - 靈魂完全體",
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
# 4. 工具函數 (整合 V11 本地圖庫 + V15.2 股市修復)
# ---------------------------------------------------------

# 完整 78 張牌名清單 (參考 V11 邏輯)
TAROT_DECK = [
    # 大阿爾克那
    "愚者", "魔術師", "女祭司", "皇后", "皇帝", "教皇", "戀人", "戰車",
    "力量", "隱者", "命運之輪", "正義", "吊人", "死神", "節制", "惡魔",
    "塔", "星星", "月亮", "太陽", "審判", "世界",
    # 權杖
    "權杖一", "權杖二", "權杖三", "權杖四", "權杖五", "權杖六", "權杖七", "權杖八", "權杖九", "權杖十",
    "權杖侍者", "權杖騎士", "權杖王后", "權杖國王",
    # 聖杯
    "聖杯一", "聖杯二", "聖杯三", "聖杯四", "聖杯五", "聖杯六", "聖杯七", "聖杯八", "聖杯九", "聖杯十",
    "聖杯侍者", "聖杯騎士", "聖杯王后", "聖杯國王",
    # 寶劍
    "寶劍一", "寶劍二", "寶劍三", "寶劍四", "寶劍五", "寶劍六", "寶劍七", "寶劍八", "寶劍九", "寶劍十",
    "寶劍侍者", "寶劍騎士", "寶劍王后", "寶劍國王",
    # 錢幣
    "錢幣一", "錢幣二", "錢幣三", "錢幣四", "錢幣五", "錢幣六", "錢幣七", "錢幣八", "錢幣九", "錢幣十",
    "錢幣侍者", "錢幣騎士", "錢幣王后", "錢幣國王"
]

def get_stock_data(symbol):
    try:
        # 自動補全台股代號
        if symbol.isdigit():
            symbol = f"{symbol}.TW"

        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")

        if hist.empty:
            return None 

        current_price = hist['Close'].iloc[-1]

        if len(hist) >= 2:
            prev_price = hist['Close'].iloc[-2]
            change = current_price - prev_price
            pct_change = (change / prev_price) * 100
        else:
            change = 0
            pct_change = 0

        return {
            "symbol": symbol,
            "price": f"{current_price:.2f}",
            "change_val": f"{change:.2f}",
            "change_pct": f"{pct_change:.2f}%",
            "trend": "📈 上漲" if change > 0 else "📉 下跌" if change < 0 else "➖ 持平",
            "volume": f"{hist['Volume'].iloc[-1]:,}"
        }
    except:
        return None

def draw_cards():
    return random.sample(TAROT_DECK, 3)

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

st.title(f"🔮 V15.3 量子塔羅 - {st.session_state.user_id}")
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

                # --- 🖼️ 自動判斷圖片來源 (V15.3 核心) ---
                cols = st.columns(3)
                for i, col in enumerate(cols):
                    card_name = cards[i]
                    # 優先找本地 images/ 資料夾
                    local_img_path = f"images/{card_name}.jpg"

                    with col:
                        if os.path.exists(local_img_path):
                            st.image(local_img_path, caption=card_name, use_container_width=True)
                        else:
                            # 如果本地找不到，顯示牌名文字卡片 (Fallback)
                            st.info(f"🎴 {card_name}")
                # ---------------------------------------

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
    s = st.text_input("股票代號 (台股請直接輸入數字，如 2330)")
    if st.button("分析", key="btn_s"):
        if not s: st.warning("請輸入代號")
        else:
            with st.spinner("分析中..."):
                stock_data = get_stock_data(s)

                if stock_data:
                    info_str = f"標的：{stock_data['symbol']}\n現價：{stock_data['price']}\n漲跌：{stock_data['change_val']} ({stock_data['change_pct']})\n趨勢：{stock_data['trend']}\n成交量：{stock_data['volume']}"
                    c1, c2, c3 = st.columns(3)
                    c1.metric("現價", stock_data['price'], stock_data['change_pct'])
                    c2.metric("漲跌", stock_data['change_val'])
                    c3.metric("趨勢", stock_data['trend'])
                else:
                    info_str = f"標的：{s} (無法取得即時數據，請AI進行純能量分析)"
                    st.warning("⚠️ 查無即時股價，將進行純塔羅分析。")

                cards = draw_cards()

                # --- 🖼️ 圖片顯示邏輯 ---
                cols = st.columns(3)
                for i, col in enumerate(cols):
                    card_name = cards[i]
                    local_img_path = f"images/{card_name}.jpg"
                    with col:
                        if os.path.exists(local_img_path):
                            st.image(local_img_path, caption=card_name, use_container_width=True)
                        else:
                            st.info(f"🎴 {card_name}")
                # ---------------------

                prompt = f"""金融占卜師。
{context}

【市場真實數據】
{info_str}

【抽牌結果】
{'、'.join(cards)}

請結合「真實市場數據」與「塔羅牌義」進行分析。
如果數據顯示上漲，但牌面凶險，請警告風險。
最後給【AI 摘要】。
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

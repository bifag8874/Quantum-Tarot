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
    page_title="量子塔羅 V14 - 全知全能版",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 金鑰與連線
# ---------------------------------------------------------
try:
    GENAI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GENAI_API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"⚠️ 系統初始化失敗: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 歷史紀錄管理
# ---------------------------------------------------------
DB_TTL = 0

def get_history(user_id):
    try:
        df = conn.read(ttl=DB_TTL)
        if df.empty or "user_id" not in df.columns:
            return pd.DataFrame()
        return df[df["user_id"] == user_id].sort_values(by="timestamp", ascending=False)
    except Exception:
        return pd.DataFrame()

def save_to_history(user_id, q_type, query, cards, summary):
    try:
        df = conn.read(ttl=DB_TTL)
        new_row = pd.DataFrame([{
            "user_id": user_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": q_type,
            "query": str(query), # 強制轉字串防錯
            "cards": str(cards),
            "ai_summary": str(summary)
        }])

        if df.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df, new_row], ignore_index=True)

        conn.update(data=updated_df)
        return True
    except Exception as e:
        st.warning(f"⚠️ 存檔暫時失敗 (不影響占卜結果): {e}")
        return False

# ---------------------------------------------------------
# 4. 工具函數
# ---------------------------------------------------------
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1mo")
        if hist.empty: return None
        current_price = stock.info.get('currentPrice', hist['Close'].iloc[-1])
        change = current_price - hist['Close'].iloc[0]
        pct = (change / hist['Close'].iloc[0]) * 100
        return {"price": f"{current_price:.2f}", "change": f"{pct:.2f}%", "trend": "漲" if change>0 else "跌"}
    except:
        return None

def draw_cards():
    deck = ["愚者", "魔術師", "女祭司", "皇后", "皇帝", "教皇", "戀人", "戰車",
            "力量", "隱者", "命運之輪", "正義", "吊人", "死神", "節制", "惡魔",
            "塔", "星星", "月亮", "太陽", "審判", "世界", "權杖一", "聖杯三", "寶劍十", "錢幣王"]
    return random.sample(deck, 3)

# ---------------------------------------------------------
# 5. 主程式
# ---------------------------------------------------------
with st.sidebar:
    st.title("👤 登入系統")
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id:
        st.success(f"Hi, {st.session_state.user_id}")
        if st.button("登出"):
            st.session_state.user_id = None
            st.rerun()
    else:
        uid = st.text_input("輸入暱稱", placeholder="例如: User1")
        if st.button("登入"):
            if uid.strip():
                st.session_state.user_id = uid.strip()
                st.rerun()

if not st.session_state.user_id:
    st.info("👈 請先在左側登入以啟用雲端記憶功能")
    st.stop()

# 準備 Prompt (更安全的寫法)
history_df = get_history(st.session_state.user_id)
history_context = ""
if not history_df.empty:
    recent = history_df.head(3)
    history_context = "【使用者近期紀錄 (僅供參考)】\n"
    for _, row in recent.iterrows():
        history_context += f"- {row['timestamp']}: {row['query']} -> {row['cards']}\n"

st.title(f"🔮 V14 量子塔羅 - {st.session_state.user_id}")
tab1, tab2, tab3 = st.tabs(["🎴 塔羅", "📈 股票", "📜 紀錄"])

with tab1:
    q = st.text_area("輸入問題")
    if st.button("占卜", key="btn_t"):
        if not q:
            st.warning("請輸入問題")
        else:
            with st.spinner("連結宇宙中..."):
                cards = draw_cards()
                cards_str = "、".join(cards)
                st.write(f"🎴 抽牌結果：**{cards_str}**")

                # 安全的 Prompt
                prompt = f"""你是一位塔羅師。
{history_context}

使用者問題：{q}
抽到的牌：{cards_str}

請進行解析，並在最後提供【AI 摘要】(30字內)。
"""
                try:
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    res = model.generate_content(prompt)
                    st.markdown(res.text)

                    # 存檔
                    summary = res.text.split("【AI 摘要】")[-1].strip() if "【AI 摘要】" in res.text else "占卜完成"
                    save_to_history(st.session_state.user_id, "塔羅", q, cards_str, summary)
                    st.toast("已存檔")
                except Exception as e:
                    st.error(f"AI連線錯誤: {e}")

with tab2:
    s = st.text_input("股票代號")
    if st.button("分析", key="btn_s"):
        if not s:
            st.warning("請輸入代號")
        else:
            with st.spinner("分析中..."):
                data = get_stock_data(s)
                market_str = f"數據: {data}" if data else "無即時數據"
                cards = draw_cards()
                st.write(f"🎴 抽牌：{'、'.join(cards)}")

                prompt = f"""你是金融占卜師。
{history_context}

標的：{s}
市場數據：{market_str}
牌面：{'、'.join(cards)}

請解析，並在最後提供【AI 摘要】。
"""
                try:
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    res = model.generate_content(prompt)
                    st.markdown(res.text)

                    summary = res.text.split("【AI 摘要】")[-1].strip() if "【AI 摘要】" in res.text else f"分析 {s}"
                    save_to_history(st.session_state.user_id, "股票", s, str(cards), summary)
                    st.toast("已存檔")
                except Exception as e:
                    st.error(f"AI錯誤: {e}")

with tab3:
    if st.button("重新整理"): st.rerun()
    if not history_df.empty:
        st.dataframe(history_df[['timestamp', 'query', 'ai_summary']], hide_index=True)
    else:
        st.write("尚無紀錄")

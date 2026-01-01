import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd
import random
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 1. 初始設定 (Page Config)
# ---------------------------------------------------------
st.set_page_config(
    page_title="量子塔羅 V15 - 終極全能版",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 金鑰與連線設定
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
    st.error(f"⚠️ 系統連線失敗: {err_msg}")
    st.stop()

# ---------------------------------------------------------
# 3. 資料庫操作 (快取控制)
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
            "query": str(query).strip(),
            "cards": str(cards).strip(),
            "ai_summary": str(summary).strip()
        }])

        if df.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df, new_row], ignore_index=True)

        conn.update(data=updated_df)
        return True
    except Exception as e:
        st.warning(f"⚠️ 存檔失敗: {e}")
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
        start = hist['Close'].iloc[0]
        change = current - start
        pct = (change / start) * 100

        return {
            "price": f"{current:.2f}",
            "change": f"{pct:.2f}%",
            "trend": "上漲" if change > 0 else "下跌"
        }
    except:
        return None

def draw_cards():
    deck = [
        "愚者", "魔術師", "女祭司", "皇后", "皇帝", "教皇", "戀人", "戰車",
        "力量", "隱者", "命運之輪", "正義", "吊人", "死神", "節制", "惡魔",
        "塔", "星星", "月亮", "太陽", "審判", "世界",
        "權杖一", "權杖國王", "聖杯三", "聖杯王后", "寶劍十", "錢幣騎士"
    ]
    return random.sample(deck, 3)

# ---------------------------------------------------------
# 5. UI 與 側邊欄設定
# ---------------------------------------------------------
with st.sidebar:
    st.title("🎛️ 靈魂控制台")

    # 🌡️ 溫度計功能回歸
    creativity = st.slider(
        "🔮 靈感溫度 (Creativity)",
        min_value=0.0, max_value=1.0, value=0.7, step=0.1,
        help="數值越高，AI 回答越奔放創意；數值越低，回答越理性保守。"
    )

    st.divider()

    st.subheader("👤 使用者登入")
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id:
        st.success(f"已登入：{st.session_state.user_id}")
        if st.button("登出"):
            st.session_state.user_id = None
            st.rerun()
    else:
        uid_input = st.text_input("輸入暱稱", placeholder="例如: jowho")
        if st.button("登入"):
            if uid_input.strip():
                st.session_state.user_id = uid_input.strip()
                st.rerun()

if not st.session_state.user_id:
    st.info("👈 請先在左側登入，開啟您的量子旅程。")
    st.stop()

# 準備長期記憶
history_df = get_history(st.session_state.user_id)
recent_context = ""
if not history_df.empty:
    recent = history_df.head(3)
    recent_context = "【使用者近期背景 (請納入考量)】\n"
    for _, row in recent.iterrows():
        recent_context += f"- 時間:{row['timestamp']} | 問:{row['query']} | 牌:{row['cards']}\n"

# ---------------------------------------------------------
# 6. 主介面 Tabs
# ---------------------------------------------------------
st.title(f"🔮 V15 量子塔羅 - {st.session_state.user_id} 的全知空間")

tab1, tab2, tab3 = st.tabs(["🎴 深度占卜", "📈 金融運勢", "📜 靈魂紀錄"])

# --- Tab 1: 塔羅 ---
with tab1:
    q = st.text_area("心中默念你的問題 (越具體越好)...", height=100)
    if st.button("揭開命運", key="btn_tarot"):
        if not q:
            st.warning("請輸入問題")
        else:
            with st.spinner("正在連結宇宙意識 (Gemini Flash Latest)..."):
                cards = draw_cards()
                cards_str = "、".join(cards)
                st.subheader(f"🎴 牌面顯現：{cards_str}")

                # 強化版 Prompt
                prompt = f"""你是一位精通心理學與神祕學的塔羅大師。
{recent_context}

使用者問題：{q}
抽到的牌：{cards_str}

請依照以下架構進行深度解析：
1. **【牌面象徵】**：簡述這三張牌在當下問題中的核心意義。
2. **【深度指引】**：結合使用者的背景，給出具體且有溫度的建議。
3. **【未來展望】**：預測事情可能的發展走向。

最後，請務必提供一行【AI 摘要】(30字內)，用於系統存檔。
"""
                try:
                    # 使用 models/gemini-flash-latest 並帶入溫度參數
                    model = genai.GenerativeModel(
                        'models/gemini-flash-latest',
                        generation_config=genai.GenerationConfig(temperature=creativity)
                    )
                    response = model.generate_content(prompt)

                    st.markdown(response.text)

                    summary = "占卜完成"
                    if "【AI 摘要】" in response.text:
                        summary = response.text.split("【AI 摘要】")[-1].strip()

                    if save_to_history(st.session_state.user_id, "塔羅", q, cards_str, summary):
                        st.toast("✅ 命運紀錄已儲存！", icon="☁️")

                except Exception as e:
                    st.error(f"AI 連線錯誤: {e}")

# --- Tab 2: 股票 ---
with tab2:
    s = st.text_input("輸入代號 (如 AAPL, 2330.TW)")
    if st.button("量化運勢分析", key="btn_stock"):
        if not s:
            st.warning("請輸入代號")
        else:
            with st.spinner(f"正在掃描 {s} 的能量場..."):
                stock_data = get_stock_data(s)
                market_info = f"數據: {stock_data}" if stock_data else "無法取得即時數據"

                cards = draw_cards()
                cards_str = "、".join(cards)
                st.write(f"🎴 能量牌面：{cards_str}")
                if stock_data:
                    st.info(f"📊 市場訊號：現價 {stock_data['price']} | 趨勢 {stock_data['trend']} ({stock_data['change']})")

                # 強化版 Prompt
                prompt = f"""你是結合華爾街經驗與量子玄學的金融顧問。
{recent_context}

標的：{s}
市場數據：{market_info}
抽到的牌：{cards_str}

請依照以下架構分析：
1. **【市場與玄學對沖】**：數據面與牌面是否一致？或是存在矛盾？
2. **【操作建議】**：給出保守與積極兩種策略。
3. **【風險提示】**：這組牌面暗示了什麼潛在風險？

最後請務必提供【AI 摘要】。
"""
                try:
                    model = genai.GenerativeModel(
                        'models/gemini-flash-latest',
                        generation_config=genai.GenerationConfig(temperature=creativity)
                    )
                    response = model.generate_content(prompt)

                    st.markdown(response.text)

                    summary = f"分析 {s}"
                    if "【AI 摘要】" in response.text:
                        summary = response.text.split("【AI 摘要】")[-1].strip()

                    save_to_history(st.session_state.user_id, "股票", s, cards_str, summary)
                    st.toast("✅ 投資筆記已儲存！", icon="📈")

                except Exception as e:
                    st.error(f"AI 分析錯誤: {e}")

# --- Tab 3: 紀錄 ---
with tab3:
    if st.button("🔄 刷新紀錄"):
        st.rerun()

    if history_df.empty:
        st.write("目前尚無紀錄。")
    else:
        st.dataframe(
            history_df[['timestamp', 'type', 'query', 'cards', 'ai_summary']],
            column_config={
                "timestamp": "時間",
                "type": "類別",
                "query": "問題/代號",
                "cards": "牌面",
                "ai_summary": "AI 重點筆記"
            },
            use_container_width=True,
            hide_index=True
        )

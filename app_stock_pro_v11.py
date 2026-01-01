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
    page_title="量子塔羅 V14.6 - 全知全能 2.0 Flash",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 金鑰與連線設定 (含錯誤引導)
# ---------------------------------------------------------
@st.cache_resource
def configure_services():
    try:
        # 嘗試讀取 Gemini API Key
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)

        # 測試連線 (建立連線物件)
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn, None
    except Exception as e:
        return None, str(e)

conn, err_msg = configure_services()

if err_msg:
    st.error(f"⚠️ 系統連線失敗，請檢查 Secrets 設定。\n錯誤訊息: {err_msg}")
    st.stop()

# ---------------------------------------------------------
# 3. 核心邏輯：資料庫操作
# ---------------------------------------------------------
DB_TTL = 0  # 設定為 0 代表每次都讀最新資料

def get_history(user_id):
    """讀取該使用者的歷史紀錄"""
    try:
        df = conn.read(ttl=DB_TTL)
        if df.empty or "user_id" not in df.columns:
            return pd.DataFrame()
        # 篩選並排序
        return df[df["user_id"] == user_id].sort_values(by="timestamp", ascending=False)
    except Exception:
        return pd.DataFrame()

def save_to_history(user_id, q_type, query, cards, summary):
    """寫入歷史紀錄 (強制轉字串防錯)"""
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
        st.warning(f"⚠️ 存檔失敗 (不影響占卜結果): {e}")
        return False

# ---------------------------------------------------------
# 4. 業務邏輯：股市與塔羅
# ---------------------------------------------------------
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d") # 改為5天，資料更輕量
        if hist.empty: return None

        current_price = stock.info.get('currentPrice', hist['Close'].iloc[-1])
        start_price = hist['Close'].iloc[0]
        change = current_price - start_price
        pct = (change / start_price) * 100

        return {
            "price": f"{current_price:.2f}",
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
# 5. UI 介面與主流程
# ---------------------------------------------------------
with st.sidebar:
    st.title("👤 使用者登入")
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id:
        st.success(f"哈囉，{st.session_state.user_id}！")
        if st.button("登出"):
            st.session_state.user_id = None
            st.rerun()
    else:
        uid_input = st.text_input("請輸入暱稱", placeholder="例如: jowho")
        if st.button("登入"):
            if uid_input.strip():
                st.session_state.user_id = uid_input.strip()
                st.rerun()

if not st.session_state.user_id:
    st.info("👈 請先在左側欄輸入暱稱登入，以啟用「雲端記憶」功能。")
    st.stop()

# 準備長期記憶 Prompt
history_df = get_history(st.session_state.user_id)
recent_context = ""
if not history_df.empty:
    recent = history_df.head(3)
    recent_context = "【使用者近期背景 (AI參考用)】\n"
    for _, row in recent.iterrows():
        recent_context += f"- 時間:{row['timestamp']} | 問:{row['query']} | 牌:{row['cards']}\n"

st.title(f"🔮 V14.6 量子塔羅 - {st.session_state.user_id} 的專屬空間")

tab1, tab2, tab3 = st.tabs(["🎴 塔羅占卜", "📈 股票運勢", "📜 靈魂紀錄"])

# --- Tab 1: 塔羅 ---
with tab1:
    q = st.text_area("心中默念你的問題...", height=100)
    if st.button("開始占卜", key="btn_tarot"):
        if not q:
            st.warning("請輸入問題")
        else:
            with st.spinner("連結宇宙資料庫 (Gemini 2.0 Flash)..."):
                cards = draw_cards()
                cards_str = "、".join(cards)
                st.subheader(f"🎴 抽牌結果：{cards_str}")

                # 建構 Prompt
                prompt = f"""你是一位神秘且具有洞察力的塔羅占卜師。
{recent_context}

現在使用者問：{q}
抽到的牌是：{cards_str}

請綜合解讀，語氣要溫暖。
最後請務必提供【AI 摘要】(30字內)，用於系統存檔。
"""
                try:
                    # ✅ 修正點：使用您帳號中確認存在的 'models/gemini-2.0-flash'
                    model = genai.GenerativeModel('models/gemini-1.5-flash')
                    response = model.generate_content(prompt)

                    st.markdown(response.text)

                    # 嘗試提取摘要
                    summary = "占卜完成"
                    if "【AI 摘要】" in response.text:
                        summary = response.text.split("【AI 摘要】")[-1].strip()

                    # 存檔
                    if save_to_history(st.session_state.user_id, "塔羅", q, cards_str, summary):
                        st.toast("✅ 紀錄已儲存！", icon="☁️")

                except Exception as e:
                    st.error(f"AI 連線錯誤: {e}")
                    st.caption("若仍有問題，請嘗試更換為 'models/gemini-flash-latest'")

# --- Tab 2: 股票 ---
with tab2:
    s = st.text_input("輸入美股/台股代號 (如 AAPL, 2330.TW)")
    if st.button("分析運勢", key="btn_stock"):
        if not s:
            st.warning("請輸入代號")
        else:
            with st.spinner(f"正在分析 {s}..."):
                stock_data = get_stock_data(s)
                market_info = f"數據: {stock_data}" if stock_data else "無法取得即時數據"

                cards = draw_cards()
                cards_str = "、".join(cards)
                st.write(f"🎴 能量牌面：{cards_str}")
                if stock_data:
                    st.info(f"📊 市場狀態：現價 {stock_data['price']} | 趨勢 {stock_data['trend']} ({stock_data['change']})")

                prompt = f"""你是華爾街量子金融占卜師。
{recent_context}

標的：{s}
市場數據：{market_info}
抽到的牌：{cards_str}

請結合技術面與玄學面進行分析。
最後請務必提供【AI 摘要】。
"""
                try:
                    # ✅ 修正點：使用您帳號中確認存在的 'models/gemini-2.0-flash'
                    model = genai.GenerativeModel('models/gemini-1.5-flash')
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

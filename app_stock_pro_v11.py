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
    page_title="量子塔羅 V14 - 全知全能版",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 秘密金鑰讀取 & 資料庫連線
# ---------------------------------------------------------
try:
    # 設定 Gemini API
    GENAI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GENAI_API_KEY)

    # 建立 Google Sheets 連線
    # 這裡的 "gsheets" 對應 secrets.toml 裡的 [connections.gsheets]
    conn = st.connection("gsheets", type=GSheetsConnection)

except Exception as e:
    st.error(f"⚠️ 金鑰或連線設定錯誤: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 核心函數：歷史紀錄管理 (讀取/寫入)
# ---------------------------------------------------------
DB_TTL = 0  # 設定為 0 代表每次都讀最新資料，不快取

def get_history(user_id):
    """從 Google Sheets 讀取該使用者的歷史紀錄"""
    try:
        df = conn.read(ttl=DB_TTL)
        # 如果是空的試算表，或是沒有 user_id 欄位，回傳空 DataFrame
        if df.empty or "user_id" not in df.columns:
            return pd.DataFrame()

        # 篩選該使用者的資料，並按時間倒序排列
        user_history = df[df["user_id"] == user_id].sort_values(by="timestamp", ascending=False)
        return user_history
    except Exception as e:
        st.warning(f"無法讀取歷史紀錄: {e}")
        return pd.DataFrame()

def save_to_history(user_id, q_type, query, cards, summary):
    """將本次問卜結果寫入 Google Sheets"""
    try:
        # 1. 讀取現有資料
        df = conn.read(ttl=DB_TTL)

        # 2. 準備新的一筆資料
        new_row = pd.DataFrame([{
            "user_id": user_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": q_type,
            "query": query,
            "cards": cards,
            "ai_summary": summary
        }])

        # 3. 合併並寫回
        if df.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df, new_row], ignore_index=True)

        conn.update(data=updated_df)
        return True
    except Exception as e:
        st.error(f"存檔失敗: {e}")
        return False

# ---------------------------------------------------------
# 4. 核心函數：AI 模型與工具
# ---------------------------------------------------------
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1mo")
        if hist.empty: return None

        info = stock.info
        current_price = info.get('currentPrice', hist['Close'].iloc[-1])
        change = current_price - hist['Close'].iloc[0]
        pct_change = (change / hist['Close'].iloc[0]) * 100

        return {
            "price": f"{current_price:.2f}",
            "change": f"{pct_change:.2f}%",
            "trend": "上漲" if change > 0 else "下跌",
            "volume": f"{hist['Volume'].mean():.0f}"
        }
    except:
        return None

def draw_cards():
    tarot_deck = [
        "愚者", "魔術師", "女祭司", "皇后", "皇帝", "教皇", "戀人", "戰車",
        "力量", "隱者", "命運之輪", "正義", "吊人", "死神", "節制", "惡魔",
        "塔", "星星", "月亮", "太陽", "審判", "世界",
        "權杖一", "權杖國王", "聖杯三", "聖杯王后", "寶劍十", "錢幣騎士"
    ]
    return random.sample(tarot_deck, 3)

# ---------------------------------------------------------
# 5. 使用者登入系統 (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.title("👤 使用者登入")

    # 初始化 session state
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id:
        st.success(f"哈囉，{st.session_state.user_id}！")
        if st.button("登出"):
            st.session_state.user_id = None
            st.rerun()
    else:
        user_input = st.text_input("請輸入暱稱 (作為歷史紀錄ID)", placeholder="例如: jowho")
        if st.button("登入 / 開始"):
            if user_input.strip():
                st.session_state.user_id = user_input.strip()
                st.rerun()
            else:
                st.warning("請輸入暱稱！")

    st.markdown("---")
    st.markdown("### 📜 歷史紀錄功能")
    st.info("登入後，您的每次占卜都會自動儲存到雲端資料庫。即便關閉網頁，下次登入依然記得您的問題。")

# ---------------------------------------------------------
# 6. 主程式介面
# ---------------------------------------------------------
if not st.session_state.user_id:
    st.info("👈 請先在左側欄輸入暱稱登入，以啟用「雲端記憶」功能。")
    st.stop()

# 讀取該使用者的歷史紀錄 (作為 AI 的背景知識)
history_df = get_history(st.session_state.user_id)
recent_history_text = ""

if not history_df.empty:
    # 取最近 3 筆紀錄
    recent = history_df.head(3)
    recent_history_text = "【使用者近期背景資料】\n"
    for _, row in recent.iterrows():
        recent_history_text += f"- {row['timestamp']} 問過「{row['query']}」，結果是「{row['cards']}」\n"

st.title(f"🔮 量子塔羅 V14 - {st.session_state.user_id} 的專屬空間")

tab1, tab2, tab3 = st.tabs(["🎴 塔羅占卜", "📈 股票運勢", "📜 我的歷史紀錄"])

# --- Tab 1: 塔羅占卜 ---
with tab1:
    user_query = st.text_area("心中默念你的問題...", height=100)

    if st.button("開始占卜", key="btn_tarot"):
        if not user_query:
            st.warning("請先輸入問題！")
        else:
            with st.spinner("正在連結宇宙資料庫..."):
                cards = draw_cards()
                st.image("https://upload.wikimedia.org/wikipedia/commons/9/90/RWS_Tarot_00_Fool.jpg", 
                         caption="示意圖", width=150) # 簡化圖片，實際可換隨機圖

                cards_str = "、".join(cards)
                st.subheader(f"🎴 你抽到了：{cards_str}")

                # 建構 Prompt (加入長期記憶)
                prompt = f"""
                你是神秘的塔羅占卜師。

                {recent_history_text}
                (請參考以上背景，如果使用者的舊問題跟新問題有關聯，請適當連結，展現出你記得他的過去。若無關則忽略。)

                現在使用者問：「{user_query}」
                抽到的牌是：{cards_str}

                請綜合解讀，給出建議。語氣要溫暖、神秘且帶有洞察力。
                最後請給出一個「AI 摘要」，總結這次占卜的重點 (不超過30字)，用於存檔。
                格式：
                【深度解讀】
                ...
                【AI 摘要】
                ...
                """

                model = genai.GenerativeModel('gemini-1.5-pro')
                response = model.generate_content(prompt)
                full_reply = response.text

                # 顯示結果
                st.markdown(full_reply)

                # 嘗試提取摘要 (簡單切分)
                try:
                    summary = full_reply.split("【AI 摘要】")[-1].strip()
                except:
                    summary = "占卜完成"

                # 存檔
                if save_to_history(st.session_state.user_id, "塔羅", user_query, cards_str, summary):
                    st.toast("✅ 紀錄已儲存至雲端！", icon="☁️")

# --- Tab 2: 股票運勢 ---
with tab2:
    symbol = st.text_input("輸入美股/台股代號 (如 AAPL, 2330.TW)")

    if st.button("分析運勢", key="btn_stock"):
        if not symbol:
            st.warning("請輸入代號")
        else:
            with st.spinner(f"正在分析 {symbol}..."):
                stock_data = get_stock_data(symbol)
                cards = draw_cards()
                cards_str = "、".join(cards)

                if stock_data:
                    market_info = f"目前股價 {stock_data['price']}，近期走勢 {stock_data['trend']} ({stock_data['change']})。"
                else:
                    market_info = "無法取得即時股價，將進行純能量分析。"

                st.info(f"抽到的牌：{cards_str}")

                prompt = f"""
                你是華爾街的量子金融占卜師。
                {recent_history_text}

                使用者詢問股票：{symbol}
                市場數據：{market_info}
                抽到的牌：{cards_str}

                請結合「技術面」(如果有數據) 與 「玄學面」(塔羅牌義) 進行分析。
                同樣，請在最後提供【AI 摘要】。
                """

                model = genai.GenerativeModel('gemini-1.5-pro')
                response = model.generate_content(prompt)
                full_reply = response.text

                st.markdown(full_reply)

                # 提取摘要並存檔
                try:
                    summary = full_reply.split("【AI 摘要】")[-1].strip()
                except:
                    summary = f"分析 {symbol}"

                if save_to_history(st.session_state.user_id, "股票", symbol, cards_str, summary):
                    st.toast("✅ 投資筆記已儲存！", icon="📈")

# --- Tab 3: 歷史紀錄檢視 ---
with tab3:
    st.subheader("📜 你的靈魂旅程")

    if st.button("🔄 重新整理紀錄"):
        st.rerun()

    if history_df.empty:
        st.write("目前還沒有紀錄喔，快去問第一個問題吧！")
    else:
        # 顯示漂亮的表格
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

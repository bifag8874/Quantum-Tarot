import streamlit as st
import google.generativeai as genai

st.title("🛠️ Gemini API 模型診斷工具")

# 1. 讀取 Key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    st.success("✅ API Key 讀取成功")
except Exception as e:
    st.error(f"❌ Key 讀取失敗: {e}")
    st.stop()

# 2. 列出所有模型
st.write("正在查詢可用模型列表...")

try:
    models = list(genai.list_models())
    
    st.subheader("📋 你的帳號可用的模型清單：")
    
    found_any = False
    for m in models:
        # 只顯示支援 generateContent 的模型
        if 'generateContent' in m.supported_generation_methods:
            st.code(f"model = genai.GenerativeModel('{m.name}')")
            found_any = True
            
    if not found_any:
        st.warning("⚠️ 你的帳號似乎沒有任何支援 generateContent 的模型！")
        st.info("請確認你在 Google Cloud Console 是否已啟用 'Generative Language API'。")
        
except Exception as e:
    st.error(f"❌ 查詢失敗: {e}")

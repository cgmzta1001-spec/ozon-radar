import streamlit as st
import pandas as pd
import random
import requests
from deep_translator import GoogleTranslator

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="Ozon 选品雷达 (终极版)", page_icon="📡", layout="wide")

# --- 2. 隐藏菜单栏 (看起来更像原生 App) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. 🔐 密码保护 & Secrets 读取 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.markdown("### 🔐 内部系统登录")
        password = st.text_input("请输入访问密码", type="password")
        if st.button("登录"):
            # 优先从 Secrets 读取，如果没有则默认 888888
            correct_password = st.secrets.get("MY_PASSWORD", "888888")
            if password == correct_password:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("密码错误")
        st.stop()

check_password()

# ==========================================
# 👇 核心逻辑：数据获取与分析
# ==========================================

class OzonAnalyzer:
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='zh-CN')

    def translate(self, text):
        try:
            return self.translator.translate(text)
        except:
            return text

    # --- 🟢 获取真实数据 ---
    def get_real_data_from_api(self, keyword):
        # 使用 RapidAPI 的通用 Ozon 接口
        url = "https://ozon-scraper-api.p.rapidapi.com/v1/search"
        querystring = {"text": keyword, "page": "1"}

        # 从 Secrets 获取 API Key
        api_key = st.secrets.get("RAPIDAPI_KEY", "")
        
        if not api_key or "YOUR_RAPIDAPI_KEY" in api_key:
            return None # 没配置 Key，直接返回 None

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "ozon-scraper-api.p.rapidapi.com"
        }

        try:
            response = requests.get(url, headers=headers, params=querystring, timeout=10)
            if response.status_code != 200:
                return None
            
            json_data = response.json()
            items = []
            # 解析数据 (适配常见 API 结构)
            raw_items = json_data.get('items', [])
            for item in raw_items:
                try:
                    title = item.get('title', '未知商品')
                    price = item.get('price', {}).get('amount', 0)
                    if price == 0: price = item.get('price_rub', 0)
                    
                    reviews = item.get('rating', {}).get('count', 0)
                    rating = item.get('rating', {}).get('average', 0.0)
                    link = item.get('url', f"https://www.ozon.ru/search/?text={keyword}")

                    items.append({
                        "title_origin": title,
                        "price_rub": float(price),
                        "reviews": int(reviews),
                        "rating": float(rating),
                        "link": link,
                        "is_real": True
                    })
                except:
                    continue
            return items
        except:
            return None

    # --- 🟡 生成模拟数据 ---
    def get_mock_data(self, keyword):
        data = []
        base_price = random.randint(500, 3000)
        nouns = [keyword, f"Premium {keyword}", f"{keyword} Set", f"New {keyword}"]
        
        for i in range(15):
            price = max(100, base_price + random.randint(-200, 500))
            item = {
                "title_origin": f"[模拟] {random.choice(nouns)} #{i+1} (演示数据)",
                "price_rub": price,
                "reviews": random.randint(0, 1500),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "link": f"https://www.ozon.ru/search/?text={keyword}",
                "is_real": False
            }
            data.append(item)
        return data

    # --- 🔵 智能切换 ---
    def get_data(self, keyword):
        # 1. 先尝试真实数据
        real_data = self.get_real_data_from_api(keyword)
        if real_data and len(real_data) > 0:
            st.toast("✅ 已连接 Ozon 实时数据", icon="☁️")
            return real_data
        
        # 2. 失败则使用模拟数据
        st.toast("⚠️ 使用演示数据模式 (API 未配置或耗尽)", icon="💻")
        return self.get_mock_data(keyword)

# --- 4. 爆款评分逻辑 ---
def analyze_potential(row):
    score = 0
    # ROI 权重
    if row['ROI (%)'] >= 50: score += 40

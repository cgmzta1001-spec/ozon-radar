import streamlit as st
import pandas as pd
import random
import requests
from deep_translator import GoogleTranslator
import matplotlib
matplotlib.use('Agg') # 防白屏补丁

# --- 1. 页面配置 ---
st.set_page_config(page_title="Ozon 选品雷达 (Pro)", page_icon="📡", layout="wide")

# --- 2. 隐藏菜单 (美化) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 🔐 密码保护 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.markdown("### 🔐 内部系统登录")
        password = st.text_input("请输入访问密码", type="password")
        if st.button("登录"):
            try:
                correct_password = st.secrets.get("MY_PASSWORD", "888888")
            except FileNotFoundError:
                correct_password = "888888"
            
            if password == correct_password:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("❌ 密码错误")
        st.stop()

check_password()

# ==========================================
# 👇 核心逻辑
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
        url = "https://ozon-scraper-api.p.rapidapi.com/v1/search"
        querystring = {"text": keyword, "page": "1"}

        try:
            api_key = st.secrets.get("RAPIDAPI_KEY", "")
        except:
            api_key = ""
        
        if not api_key or "替换" in api_key:
            return None 

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "ozon-scraper-api.p.rapidapi.com"
        }

        try:
            response = requests.get(url, headers=headers, params=querystring, timeout=15)
            if response.status_code != 200:
                return None
            
            json_data = response.json()
            items = []
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

    def get_data(self, keyword):
        real_data = self.get_real_data_from_api(keyword)
        if real_data and len(real_data) > 0:
            st.toast("✅ 已连接 Ozon 实时数据", icon="☁️")
            return real_data
        
        st.toast("⚠️ 使用演示数据模式", icon="💻")
        return self.get_mock_data(keyword)

# --- 4. 爆款评分逻辑 ---
def analyze_potential(row):
    score = 0
    if row['ROI (%)'] >= 50: score += 40
    elif row['ROI (%)'] >= 30: score += 30
    
    if row['reviews'] > 500: score += 30
    elif row['reviews'] > 50: score += 20
    
    if 4.5 >= row['rating'] >= 3.8: score += 30
    return score

# ==========================================
# 👇 界面 UI
# ==========================================

st.title("🔥 Ozon 选品雷达 (Pro)")

col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("请输入产品关键词 (英文)", "crochet bag")
with col2:
    start_btn = st.button("🚀 开始挖掘", type="primary", use_container_width=True)

with st.sidebar:
    st.header("💰 成本模型")
    exchange = st.number_input("汇率 (CNY/RUB)", value=0.075, format="%.4f")
    cost = st.number_input("采购+运费 (CNY)", value=50.0)
    fee_percent = st.slider("平台费率 (%)", 10, 40, 15) / 100

if start_btn:
    analyzer = OzonAnalyzer()
    
    with st.spinner("正在扫描全网数据..."):
        # 获取数据
        raw_data = analyzer.get_data(keyword)
        df = pd.DataFrame(raw_data)
        
        if df.empty:
            st.error("❌ 未找到数据，请稍后重试。")
            st.stop()

        # 💰 计算利润核心公式
        df['价格 (CNY)'] = df['price_rub'] * exchange
        # 净利润 = 售价(转人民币) * (1-佣金) - 成本
        df['净利润 (CNY)'] = df['价格 (CNY)'] * (1 - fee_percent) - cost
        df['ROI (%)'] = (df['净利润 (CNY)'] / cost) * 100
        
        # 翻译与评分
        df['中文标题'] = df['title_origin'].apply(analyzer.translate)
        df['爆款分'] = df.apply(analyze_potential, axis=1)
        
        # 排序
        df = df.sort_values(by='爆款分', ascending=False)
        
        # 展示结果
        st.divider()
        if df.iloc[0]['is_real']:
            st.success(f"📊 分析完成：找到 {len(df)} 个真实竞品")
        else:
            st.warning(f"⚠️ 分析完成：显示 {len(df)} 个模拟演示商品")

        st.subheader("📋 全量选品矩阵表")

        try:
            st.dataframe(
                df.style.background_gradient(subset=['爆款分', '净利润 (CNY)'], cmap="RdYlGn", vmin=0, vmax=100),
                column_config={
                    "中文标题": st.column_config.TextColumn("商品名称", width="medium"),
                    "price_rub": st.column_config.NumberColumn("卢布价", format="₽%d"),
                    "reviews": st.column_config.NumberColumn("评价数"),
                    "rating": st.column_config.NumberColumn("评分", format="%.1f ⭐"),
                    # 👇 新增：利润列
                    "净利润 (CNY)": st.column_config.NumberColumn("预计利润", format="¥%.1f"),
                    "ROI (%)": st.column_config.NumberColumn("ROI", format="%.0f%%"),
                    "爆款分": st.column_config.ProgressColumn("推荐指数", min_value=0, max_value=100),
                    "link": st.column_config.LinkColumn("链接"),
                },
                use_container_width=True,
                hide_index=True
            )
        except Exception as e:
            st.error(f"矩阵图渲染失败，已切换普通模式: {e}")
            st.dataframe(df)

        st.markdown("---")

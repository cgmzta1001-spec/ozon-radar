import streamlit as st
import pandas as pd
import random
import requests
from deep_translator import GoogleTranslator
# 👇 必须加这一句，防止服务器报错
import matplotlib
matplotlib.use('Agg') 

# --- 1. 页面配置 ---
st.set_page_config(page_title="Ozon 选品雷达 (Pro)", page_icon="📡", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

# --- 2. 🔐 密码与 Secrets ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if not st.session_state.password_correct:
        st.markdown("### 🔐 内部系统登录")
        pwd = st.text_input("密码", type="password")
        if st.button("登录"):
            # 容错处理：如果没有配置 Secrets，默认密码 888888
            correct = st.secrets.get("MY_PASSWORD", "888888")
            if pwd == correct:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("密码错误")
        st.stop()
check_password()

# --- 3. 核心功能类 ---
class OzonAnalyzer:
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='zh-CN')

    def translate(self, text):
        try:
            return self.translator.translate(text)
        except:
            return text

    def get_real_data(self, keyword):
        # 尝试从 Secrets 获取 Key
        api_key = st.secrets.get("RAPIDAPI_KEY", "")
        # 如果 Key 是空的，或者含有默认提示语，直接返回 None (切换模拟数据)
        if not api_key or "替换" in api_key or "YOUR" in api_key:
            return None 

        url = "https://ozon-scraper-api.p.rapidapi.com/v1/search"
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "ozon-scraper-api.p.rapidapi.com"
        }
        try:
            # 联网请求
            response = requests.get(url, headers=headers, params={"text": keyword, "page": "1"}, timeout=15)
            if response.status_code != 200: return None
            
            data = response.json()
            items = []
            for item in data.get('items', []):
                price = item.get('price', {}).get('amount', 0)
                if price == 0: price = item.get('price_rub', 0)
                items.append({
                    "title_origin": item.get('title', '未知'),
                    "price_rub": float(price),
                    "reviews": int(item.get('rating', {}).get('count', 0)),
                    "rating": float(item.get('rating', {}).get('average', 0.0)),
                    "link": item.get('url', f"https://www.ozon.ru/search/?text={keyword}"),
                    "is_real": True
                })
            return items
        except:
            return None

    def get_mock_data(self, keyword):
        # 生成模拟数据
        data = []
        base = random.randint(500, 3000)
        for i in range(10):
            data.append({
                "title_origin": f"[模拟] {keyword} 示例商品 {i+1}",
                "price_rub": base + random.randint(-200, 500),
                "reviews": random.randint(0, 1000),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "link": "https://www.ozon.ru",
                "is_real": False
            })
        return data

# --- 4. 界面逻辑 ---
st.title("🔥 Ozon 选品雷达 (利润热力版)")

col1, col2 = st.columns([3, 1])
keyword = col1.text_input("关键词", "crochet bag")
if col2.button("🚀 开始挖掘", type="primary", use_container_width=True):
    
    with st.spinner("正在分析数据..."):
        # 1. 获取数据
        app = OzonAnalyzer()
        raw = app.get_real_data(keyword)
        
        # 自动降级逻辑
        if not raw:
            raw = app.get_mock_data(keyword)
            st.toast("⚠️ 正在使用演示数据 (未连接 API 或 额度耗尽)", icon="💻")
        else:
            st.toast("✅ 已获取真实实时数据", icon="☁️")
            
        df = pd.DataFrame(raw)

        # 2. 读取侧边栏参数 (放在这里防止重跑)
        with st.sidebar:
            st.header("💰 利润计算器")
            ex_rate = st.number_input("汇率", value=0.075, format="%.4f")
            cost_cny = st.number_input("成本 (¥)", value=40.0)
            fee = st.slider("费率 (%)", 10, 40, 15) / 100

        # 3. 计算指标
        df['价格 (¥)'] = df['price_rub'] * ex_rate
        df['净利润 (¥)'] = df['价格 (¥)'] * (1 - fee) - cost_cny
        df['ROI'] = (df['净利润 (¥)'] / cost_cny) * 100
        
        # 评分
        def get_score(row):
            s = 0
            if row['ROI'] > 30: s += 40
            if row['reviews'] > 50: s += 30
            if row['rating'] > 4.0: s += 30
            return s
        df['爆款分'] = df.apply(get_score, axis=1)
        
        df['中文标题'] = df['title_origin'].apply(app.translate)
        df = df.sort_values(by="爆款分", ascending=False)

        # 4. 显示热力图 (关键部分)
        st.divider()
        st.subheader("📋 利润分析矩阵")
        
        # 如果是真实数据，显示绿色成功提示；模拟数据显示黄色警告
        if df.iloc[0]['is_real']:
            st.success(f"找到 {len(df)} 个真实竞品")
        else:
            st.warning("⚠️ 当前为演示数据模式 (请检查 Secrets 配置以获取真实数据)")

        # 👇 强制渲染热力图
        try:
            st.dataframe(
                df.style.background_gradient(subset=['爆款分', '净利润 (¥)'], cmap="RdYlGn", vmin=None, vmax=None),
                column_config={
                    "中文标题": st.column_config.TextColumn("商品", width="medium"),
                    "price_rub": st.column_config.NumberColumn("卢布价", format="₽%d"),
                    "净利润 (¥)": st.column_config.NumberColumn("净利润", format="¥%.1f"),
                    "ROI": st.column_config.NumberColumn("ROI", format="%.0f%%"),
                    "爆款分": st.column_config.ProgressColumn("推荐度", min_value=0, max_value=100),
                    "link": st.column_config.LinkColumn("链接"),
                },
                use_container_width=True,
                hide_index=True
            )
        except Exception as e:
            # 如果还是失败，这次我们会把错误打印出来，方便找原因
            st.error(f"❌ 热力图加载失败，原因: {e}")
            st.dataframe(df) # 兜底显示普通表格

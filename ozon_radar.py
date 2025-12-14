import streamlit as st
import pandas as pd
import random
import requests
import re
from collections import Counter
from deep_translator import GoogleTranslator
import matplotlib
import matplotlib.pyplot as plt

# 🛠️ 强制后台画图 (防白屏)
matplotlib.use('Agg')

# --- 1. 页面配置 ---
st.set_page_config(page_title="Ozon 选品雷达 (RapidAPI版)", page_icon="⚡", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stMetric {background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心功能类 ---
class OzonAnalyzer:
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='zh-CN')

    def translate(self, text):
        try:
            return self.translator.translate(text)
        except:
            return text

    # 🔥 核心修改：适配 RapidAPI (JSON 模式)
    def get_real_data(self, keyword):
        # 1. 检查 Key
        api_key = st.secrets.get("RAPIDAPI_KEY", "")
        if not api_key or "YOUR" in api_key: return None 

        # 2. 配置 RapidAPI (这里使用通用的 Ozon Scraper)
        url = "https://ozon-scraper-api.p.rapidapi.com/v1/search"
        
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "ozon-scraper-api.p.rapidapi.com"
        }
        
        params = {
            "text": keyword,
            "page": "1"
        }

        try:
            # 发送请求 (JSON 接口通常 1-3 秒就返回)
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                # 如果报错，打印一下方便调试
                print(f"API Error: {response.status_code}")
                return None
            
            data = response.json()
            items = []
            
            # 3. 解析 JSON (比 HTML 简单且精准)
            # 注意：不同的 RapidAPI 服务商返回结构不同，这是最常见的结构
            raw_items = data.get('items', [])
            
            for item in raw_items:
                try:
                    # 价格解析 (有些接口放在 price.amount，有些直接是 price)
                    price = item.get('price', {}).get('amount', 0)
                    if price == 0: price = item.get('price_rub', 0) # 备用字段
                    
                    # 评价数解析
                    reviews = item.get('rating', {}).get('count', 0)
                    rating = float(item.get('rating', {}).get('average', 0.0))
                    
                    # 标题
                    title = item.get('title', '未知商品')
                    
                    items.append({
                        "title_origin": title,
                        "price_rub": float(price),
                        "reviews": int(reviews),
                        "rating": rating,
                        "link": item.get('url', f"https://www.ozon.ru/search/?text={keyword}"),
                        "is_real": True
                    })
                except:
                    continue
                    
            return items
        except Exception as e:
            print(f"Parsing Error: {e}")
            return None

    def get_mock_data(self, keyword):
        data = []
        base = random.randint(500, 3000)
        for i in range(20):
            price = max(100, base + random.randint(-500, 1500))
            data.append({
                "title_origin": f"[模拟] {keyword} 样式{chr(65+i)} Pro Max",
                "price_rub": price,
                "reviews": random.randint(10, 2000),
                "rating": round(random.uniform(3.0, 5.0), 1),
                "link": "https://www.ozon.ru",
                "is_real": False
            })
        return data

# --- 3. 辅助分析函数 ---
def extract_keywords(titles):
    text = " ".join(titles).lower()
    text = re.sub(r'[^\w\s]', '', text)
    words = text.split()
    stop_words = {'the', 'for', 'and', 'with', 'ozon', '模拟', 'pro', 'set', 'new', 'cm', 'pcs'}
    filtered = [w for w in words if w not in stop_words and len(w) > 2]
    return Counter(filtered).most_common(10)

# --- 4. 界面逻辑 ---
st.title("⚡ Ozon 选品雷达 (RapidAPI 极速版)")
st.caption("数据源: RapidAPI (JSON) | 状态: 🚀 高速连接中")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 参数配置")
    keyword = st.text_input("🔍 搜索关键词", "crochet bag")
    st.markdown("---")
    st.header("💰 利润模型")
    ex_rate = st.number_input("汇率 (CNY/RUB)", 0.075, format="%.4f")
    cost_cny = st.number_input("采购成本 (¥)", 40.0)
    fee = st.slider("平台佣金 (%)", 10, 40, 15) / 100

if st.button("🚀 极速挖掘", type="primary", use_container_width=True):
    
    analyzer = OzonAnalyzer()
    
    with st.spinner("⚡ 正在通过 API 获取精准数据..."):
        # 1. 获取数据
        raw = analyzer.get_real_data(keyword)
        if not raw:
            raw = analyzer.get_mock_data(keyword)
            is_mock = True
            st.toast("⚠️ API 连接未成功，已切换演示数据", icon="💻")
        else:
            is_mock = False
            st.toast("✅ 成功获取真实数据！", icon="🎉")
            
        df = pd.DataFrame(raw)

        # 2. 计算
        df['价格 (¥)'] = df['price_rub'] * ex_rate
        df['净利润 (¥)'] = df['价格 (¥)'] * (1 - fee) - cost_cny
        df['ROI (%)'] = (df['净利润 (¥)'] / cost_cny) * 100
        
        # 3. 评分
        df['爆款分'] = 0
        df.loc[df['ROI (%)'] > 30, '爆款分'] += 40
        df.loc[df['reviews'] > 100, '爆款分'] += 30
        
        # 4. 翻译
        df['中文标题'] = df['title_origin'].apply(analyzer.translate)
        df = df.sort_values("爆款分", ascending=False)

    # === 仪表板 ===
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    if not df.empty:
        m1.metric("平均售价", f"₽{int(df['price_rub'].mean())}")
        m2.metric("平均 ROI", f"{int(df['ROI (%)'].mean())}%")
        m3.metric("最高利润", f"¥{int(df['净利润 (¥)'].max())}")
        m4.metric("数据来源", "RapidAPI" if not is_mock else "模拟演示")

    # === 功能 Tabs ===
    tab1, tab2, tab3 = st.tabs(["📋 选品矩阵", "📊 市场图表", "🧠 SEO 分析"])

    with tab1:
        st.subheader("全量商品数据")
        st.dataframe(
            df.style.background_gradient(subset=['净利润 (¥)', 'ROI (%)'], cmap="RdYlGn"),
            column_config={
                "中文标题": st.column_config.TextColumn("商品名称", width="medium"),
                "price_rub": st.column_config.NumberColumn("卢布价", format="₽%d"),
                "净利润 (¥)": st.column_config.NumberColumn("净利", format="¥%.1f"),
                "ROI (%)": st.column_config.NumberColumn("ROI", format="%.0f%%"),
                "link": st.column_config.LinkColumn("链接"),
            },
            use_container_width=True
        )
        # 下载按钮
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出 Excel", data=csv, file_name=f'ozon_{keyword}.csv', mime='text/csv')

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**💰 价格分布**")
            st.bar_chart(df['price_rub'].value_counts(bins=5).sort_index())
        with c2:
            st.markdown("**💎 蓝海寻找 (价格 vs 评价)**")
            st.scatter_chart(df, x='price_rub', y='reviews', color='ROI (%)')

    with tab3:
        st.markdown("**🔑 爆款标题热词**")
        kw_df = pd.DataFrame(extract_keywords(df['title_origin'].tolist()), columns=['词', '频次'])
        st.bar_chart(kw_df.set_index('词'))

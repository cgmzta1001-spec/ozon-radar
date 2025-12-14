import streamlit as st
import pandas as pd
import random
import requests
from collections import Counter
import re
from deep_translator import GoogleTranslator
import matplotlib
import matplotlib.pyplot as plt

# 🛠️ 强制后台画图 (防白屏)
matplotlib.use('Agg')

# --- 1. 页面高级配置 ---
st.set_page_config(page_title="Ozon 选品雷达 (旗舰版)", page_icon="🚀", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
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

    def get_real_data(self, keyword):
        api_key = st.secrets.get("RAPIDAPI_KEY", "")
        if not api_key or "YOUR" in api_key: return None 

        url = "https://ozon-scraper-api.p.rapidapi.com/v1/search"
        headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "ozon-scraper-api.p.rapidapi.com"}
        
        try:
            response = requests.get(url, headers=headers, params={"text": keyword, "page": "1"}, timeout=15)
            if response.status_code != 200: return None
            
            data = response.json()
            items = []
            for item in data.get('items', []):
                price = item.get('price', {}).get('amount', 0)
                if price == 0: price = item.get('price_rub', 0)
                
                title = item.get('title', '未知')
                rating = float(item.get('rating', {}).get('average', 0.0))
                reviews = int(item.get('rating', {}).get('count', 0))
                
                items.append({
                    "title_origin": title,
                    "price_rub": float(price),
                    "reviews": reviews,
                    "rating": rating,
                    "link": item.get('url', f"https://www.ozon.ru/search/?text={keyword}"),
                    "is_real": True
                })
            return items
        except:
            return None

    def get_mock_data(self, keyword):
        data = []
        base = random.randint(500, 3000)
        # 模拟更真实的分布
        for i in range(30):
            price = max(100, base + random.randint(-500, 1500))
            reviews = random.randint(0, 100) if random.random() > 0.2 else random.randint(500, 3000)
            data.append({
                "title_origin": f"[模拟] {keyword} 样式{chr(65+i)} Pro Max",
                "price_rub": price,
                "reviews": reviews,
                "rating": round(random.uniform(3.0, 5.0), 1),
                "link": "https://www.ozon.ru",
                "is_real": False
            })
        return data

# --- 3. 辅助分析函数 ---
def extract_keywords(titles):
    # 简单的分词统计
    text = " ".join(titles).lower()
    # 去掉标点和无意义词
    text = re.sub(r'[^\w\s]', '', text)
    words = text.split()
    stop_words = {'the', 'for', 'and', 'with', 'ozon', '模拟', 'pro', 'max', 'new', 'set', 'of'}
    filtered = [w for w in words if w not in stop_words and len(w) > 2]
    return Counter(filtered).most_common(10)

# --- 4. 界面逻辑 ---
st.title("🚀 Ozon 选品雷达 (旗舰版 V2.0)")

# 侧边栏：参数设置
with st.sidebar:
    st.header("⚙️ 参数配置")
    keyword = st.text_input("🔍 搜索关键词", "crochet bag")
    st.markdown("---")
    st.header("💰 利润模型")
    ex_rate = st.number_input("汇率 (CNY/RUB)", 0.075, format="%.4f")
    cost_cny = st.number_input("采购成本 (¥)", 40.0)
    fee = st.slider("平台佣金 (%)", 10, 40, 15) / 100
    st.markdown("---")
    st.caption("Developed by Gemini AI Partner")

# 主按钮
if st.button("🚀 全网深度挖掘", type="primary", use_container_width=True):
    
    analyzer = OzonAnalyzer()
    
    with st.spinner("🕵️‍♂️ AI 正在爬取数据、清洗噪音、计算利润..."):
        # 1. 获取数据
        raw = analyzer.get_real_data(keyword)
        if not raw:
            raw = analyzer.get_mock_data(keyword)
            is_mock = True
        else:
            is_mock = False
            
        df = pd.DataFrame(raw)

        # 2. 计算核心指标
        df['价格 (¥)'] = df['price_rub'] * ex_rate
        df['净利润 (¥)'] = df['价格 (¥)'] * (1 - fee) - cost_cny
        df['ROI (%)'] = (df['净利润 (¥)'] / cost_cny) * 100
        
        # 3. 智能评分
        df['爆款分'] = 0
        df.loc[df['ROI (%)'] > 30, '爆款分'] += 40
        df.loc[df['reviews'] > 100, '爆款分'] += 30
        df.loc[df['rating'] > 4.2, '爆款分'] += 30

        # 4. 翻译
        df['中文标题'] = df['title_origin'].apply(analyzer.translate)
        df = df.sort_values("爆款分", ascending=False)

    # === 🟢 模块 1: 市场大盘仪表板 ===
    st.divider()
    if is_mock:
        st.warning("⚠️ 当前为演示数据模式 (API 未连接)")
    else:
        st.success(f"✅ 成功抓取 {len(df)} 条真实竞品数据")

    # 4个核心指标卡片
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("平均售价 (卢布)", f"₽{int(df['price_rub'].mean())}")
    m2.metric("市场平均 ROI", f"{int(df['ROI (%)'].mean())}%", delta_color="normal")
    m3.metric("头部竞品最高销", f"{df['reviews'].max()} 条")
    m4.metric("盈利商品占比", f"{len(df[df['净利润 (¥)']>0]) / len(df) * 100:.0f}%")

    # === 🔵 模块 2: 多维度分析 Tabs ===
    tab1, tab2, tab3 = st.tabs(["📋 选品矩阵表", "📊 可视化图表", "🧠 SEO 关键词助手"])

    with tab1:
        st.subheader("全量商品利润分析")
        
        # 过滤器
        c1, c2 = st.columns(2)
        min_roi = c1.slider("过滤 ROI 低于多少的产品?", 0, 100, 0)
        show_df = df[df['ROI (%)'] >= min_roi]
        
        # 渲染热力图
        st.dataframe(
            show_df.style.background_gradient(subset=['爆款分', '净利润 (¥)', 'ROI (%)'], cmap="RdYlGn"),
            column_config={
                "中文标题": st.column_config.TextColumn("商品", width="medium"),
                "price_rub": st.column_config.NumberColumn("卢布价", format="₽%d"),
                "净利润 (¥)": st.column_config.NumberColumn("净利", format="¥%.1f"),
                "ROI (%)": st.column_config.NumberColumn("ROI", format="%.0f%%"),
                "link": st.column_config.LinkColumn("链接"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 📥 下载 Excel 功能
        csv = show_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下载数据到 Excel",
            data=csv,
            file_name=f'ozon_analysis_{keyword}.csv',
            mime='text/csv',
        )

    with tab2:
        st.subheader("市场分布透视")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("**💰 价格区间分布 (哪个价位段产品最多?)**")
            # 价格直方图
            st.bar_chart(df['price_rub'].value_counts(bins=5).sort_index())
            
        with col_chart2:
            st.markdown("**💎 价格 vs 评价数 (寻找价格高且评价少的蓝海)**")
            # 散点图
            st.scatter_chart(df, x='price_rub', y='reviews', color='ROI (%)')

    with tab3:
        st.subheader("🔑 爆款标题高频词 (SEO)")
        st.caption("将这些词加入你的标题，更容易被买家搜索到")
        
        keywords = extract_keywords(df['title_origin'].tolist())
        kw_df = pd.DataFrame(keywords, columns=['单词', '出现次数'])
        
        # 横向柱状图展示关键词
        st.bar_chart(kw_df.set_index('单词'))
        
        with st.expander("查看推荐标题组合"):
            top_words = [k[0] for k in keywords[:5]]
            st.write(f"🤖 **AI 推荐组合**: {keyword} " + " ".join(top_words))

import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from deep_translator import GoogleTranslator

# --- 1. 页面配置 (SaaS 风格) ---
st.set_page_config(page_title="Ozon Seerfar (终极离线版)", page_icon="🦁", layout="wide")

# 自定义 CSS：让界面更紧凑专业
st.markdown("""
    <style>
    .main {background-color: #f4f6f9;}
    .stMetric {background-color: white; padding: 10px; border-radius: 8px; border: 1px solid #e0e0e0;}
    h1, h2, h3 {font-family: 'Sans-serif';}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心解析引擎 (源码分析) ---
class OzonUltimateEngine:
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='zh-CN')

    def translate(self, text):
        try:
            return self.translator.translate(text)
        except:
            return text

    def extract_keywords(self, titles):
        # SEO 关键词提取逻辑
        text = " ".join(titles).lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        stop_words = {'the', 'for', 'and', 'with', 'ozon', 'pro', 'set', 'new', 'pcs', 'cm', 'mm', 'black', 'white'}
        filtered = [w for w in words if w not in stop_words and len(w) > 2 and not w.isdigit()]
        return Counter(filtered).most_common(15)

    def parse_html(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        items = []
        
        # 核心解析逻辑：寻找商品卡片
        links = soup.find_all('a', href=re.compile(r'/product/'))
        seen_urls = set()
        
        for link in links:
            url = link.get('href')
            if not url or 'ozon.ru' in url or url in seen_urls: continue
            
            # 向上找父容器
            card = link.find_parent('div')
            found_data = False
            
            # 向上遍历寻找数据
            for _ in range(6):
                if not card: break
                text_blob = card.get_text(separator=" ")
                
                # 1. 找价格 (123 ₽)
                price_match = re.search(r'([\d\s]+)\s?₽', text_blob)
                if price_match:
                    try:
                        price_str = price_match.group(1).replace(' ', '').replace('\xa0', '').replace('\u2009', '')
                        price = float(price_str)
                        if price < 50: break # 过滤无效价格
                        
                        # 2. 找评价数
                        reviews = 0
                        rev_match = re.search(r'(\d+)\s?(otz|rev|отз)', text_blob, re.IGNORECASE)
                        if rev_match:
                            reviews = int(rev_match.group(1))
                        else:
                            # 备用：括号里的数字
                            sub_match = re.search(r'\(([\d\s]+)\)', text_blob)
                            if sub_match:
                                try: reviews = int(sub_match.group(1).replace(' ', ''))
                                except: pass

                        # 3. 找标题
                        title = "Ozon 商品"
                        img_tag = card.find('img')
                        if img_tag and img_tag.get('alt'):
                            title = img_tag.get('alt')
                        elif len(link.get_text()) > 5:
                            title = link.get_text(strip=True)

                        # 4. Seerfar 销量预估算法 (核心)
                        # 假设：每10-15个销量产生1个评价 (留评率约7%) + 基础权重
                        est_sales = int(reviews * 0.15) + 10
                        if est_sales > 2000: est_sales = 2000 # 封顶
                        est_gmv = est_sales * price

                        full_url = url if url.startswith('http') else f"https://www.ozon.ru{url}"
                        seen_urls.add(url)
                        
                        items.append({
                            "title_origin": title,
                            "price_rub": price,
                            "reviews": reviews,
                            "est_sales": est_sales,
                            "est_gmv": est_gmv,
                            "link": full_url
                        })
                        found_data = True
                        break
                    except: pass
                card = card.parent
                if found_data: break
        return items

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.title("🦁 Seerfar 离线版")
    st.caption("源码解析 | 利润计算 | 趋势分析")
    
    st.markdown("### 💰 利润模型")
    ex_rate = st.number_input("汇率 (CNY/RUB)", 0.075, format="%.4f")
    cost_cny = st.number_input("采购+运费 (¥)", 45.0)
    fee = st.slider("费率+广告 (%)", 10, 50, 20) / 100
    
    st.info("💡 **使用方法**：\n1. 电脑打开 Ozon 搜索关键词\n2. 右键 -> 查看网页源代码\n3. 全选复制 -> 粘贴到右侧")

# --- 4. 主界面逻辑 ---
st.header("1️⃣ 数据导入")
html_input = st.text_area("👇 请粘贴 Ozon 网页源代码 (HTML)", height=100, placeholder="<div ...>")

if st.button("🚀 启动 Seerfar 级分析", type="primary", use_container_width=True):
    if not html_input:
        st.error("请先粘贴源代码！")
        st.stop()
        
    engine = OzonUltimateEngine()
    
    with st.spinner("🕵️ 正在解剖代码、估算销量、挖掘关键词..."):
        raw_data = engine.parse_html(html_input)
        
        if not raw_data:
            st.error("⚠️ 解析失败！请确保您粘贴的是【Ozon 搜索结果页】的完整源代码。")
            st.stop()
            
        df = pd.DataFrame(raw_data)
        
        # --- 全维度计算 ---
        df['价格 (¥)'] = df['price_rub'] * ex_rate
        df['净利润 (¥)'] = df['价格 (¥)'] * (1 - fee) - cost_cny
        df['ROI (%)'] = (df['净利润 (¥)'] / cost_cny) * 100
        
        # 爆款分计算
        df['爆款分'] = 0
        df.loc[df['ROI (%)'] > 30, '爆款分'] += 40
        df.loc[df['est_sales'] > 50, '爆款分'] += 30
        df.loc[df['reviews'] < 50, '爆款分'] += 20 # 新品加权
        
        # 翻译 (只翻译前30个，防止卡顿)
        df['中文标题'] = df['title_origin'].head(30).apply(lambda x: engine.translate(x[:40]))
        # 剩下的用原文填充
        df['中文标题'].fillna(df['title_origin'], inplace=True)
        
        st.success(f"✅ 成功提取 {len(df)} 个商品，分析完成！")

    # === 📊 模块 1: 市场大盘 (Seerfar 风格) ===
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("总盘子 (GMV)", f"₽{int(df['est_gmv'].sum()/1000)}k", help="搜索页预估总销售额")
    m2.metric("平均 ROI", f"{int(df['ROI (%)'].mean())}%", delta_color="normal")
    m3.metric("头部商品销量", f"{int(df['est_sales'].max())} 单")
    m4.metric("盈利商品占比", f"{len(df[df['净利润 (¥)']>0]) / len(df) * 100:.0f}%")

    # === 📈 模块 2: 高级图表 Tabs ===
    tab1, tab2, tab3, tab4 = st.tabs(["💎 蓝海机会图", "🧠 SEO 关键词", "📋 选品矩阵表", "📊 垄断分析"])

    with tab1:
        st.markdown("**Seerfar 核心视图：寻找「低评高销」的蓝海品**")
        fig = px.scatter(
            df,
            x="reviews",
            y="price_rub",
            size="est_sales",     # 气泡大小 = 预估销量
            color="ROI (%)",      # 颜色 = 利润率
            hover_data=["中文标题", "净利润 (¥)"],
            color_continuous_scale="RdYlGn",
            labels={"reviews": "评价数 (越少越好)", "price_rub": "售价 (卢布)", "est_sales": "预估月销"},
            title="气泡越大销量越高，位置越左评价越少 (左上角/左下角为机会区)"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("**🔑 爆款标题 SEO 词频分析**")
        keywords = engine.extract_keywords(df['title_origin'].tolist())
        kw_df = pd.DataFrame(keywords, columns=['单词', '出现频次'])
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.bar_chart(kw_df.set_index('单词'))
        with c2:
            st.write("🔥 **高频热词 Top 10**")
            st.table(kw_df.head(10))

    with tab3:
        st.markdown("**📋 全量选品矩阵 (带热力图)**")
        
        # 过滤器
        min_roi = st.slider("只显示 ROI 大于多少的产品?", 0, 100, 0)
        show_df = df[df['ROI (%)'] >= min_roi].sort_values("爆款分", ascending=False)
        
        # 👇 您要的矩阵图回来了！
        st.dataframe(
            show_df.style.background_gradient(subset=['爆款分', '净利润 (¥)', 'ROI (%)', 'est_sales'], cmap="RdYlGn"),
            column_config={
                "中文标题": st.column_config.TextColumn("商品", width="medium"),
                "price_rub": st.column_config.NumberColumn("卢布价", format="₽%d"),
                "reviews": st.column_config.NumberColumn("评价数"),
                "est_sales": st.column_config.ProgressColumn("预估月销", format="%d", min_value=0, max_value=max(df['est_sales'])),
                "净利润 (¥)": st.column_config.NumberColumn("净利", format="¥%.1f"),
                "ROI (%)": st.column_config.NumberColumn("ROI", format="%.0f%%"),
                "link": st.column_config.LinkColumn("链接"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 👇 导出功能也保留了
        csv = show_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出数据到 Excel", data=csv, file_name='ozon_seerfar_analysis.csv', mime='text/csv')

    with tab4:
        st.markdown("**🍰 市场垄断度分析**")
        col_1, col_2 = st.columns(2)
        with col_1:
            fig_pie = px.pie(df.head(10), values='est_sales', names='中文标题', title="Top 10 商品销量占比")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_2:
            fig_hist = px.histogram(df, x="price_rub", y="est_sales", nbins=10, title="哪个价格段销量最大？")
            st.plotly_chart(fig_hist, use_container_width=True)

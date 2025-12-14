import streamlit as st
import pandas as pd
import time
import random
from collections import Counter
import re
from deep_translator import GoogleTranslator

# --- 1. 页面基础配置 (必须放在第一行) ---
st.set_page_config(
    page_title="Ozon 爆款捕手 (私密版)",
    page_icon="🔐",
    layout="wide"
)

# --- 2. 🔐 密码保护模块 ---
def check_password():
    """如果不输入正确密码，就停止运行下面的代码"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.markdown("### 🔐 内部选品系统 - 访问控制")
        st.info("本工具仅限内部团队使用，请输入访问密码。")
        
        password = st.text_input("请输入密码", type="password")
        
        if st.button("登录系统"):
            # 👇 【在这里修改您的密码】 👇
            if password == "20251225":  
                st.session_state.password_correct = True
                st.success("密码正确，正在进入系统...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("密码错误，请联系管理员获取权限")
        
        st.stop()  # ⛔ 密码不对时，代码到这里就彻底停止，不会加载下面的选品功能

# 运行密码检查
check_password()

# ==========================================
# 👇 只有密码输对后，才会运行下面的选品代码
# ==========================================

# --- 3. 核心逻辑类 (V3.0) ---
class OzonAnalyzer:
    def __init__(self):
        # 初始化翻译器
        self.translator = GoogleTranslator(source='auto', target='zh-CN')

    def translate(self, text):
        try:
            return self.translator.translate(text)
        except:
            return text

    def extract_keywords(self, titles):
        """提取高频热词"""
        all_text = " ".join(titles).lower()
        all_text = re.sub(r'[^\w\s]', '', all_text)
        words = all_text.split()
        stop_words = {'for', 'and', 'the', 'with', 'set', 'ozon', 'global', 'in', 'of', 'pcs', 'new', 'hot', 'kit'}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
        return Counter(filtered_words).most_common(10)

    def generate_real_search_link(self, keyword):
        return f"https://www.ozon.ru/search/?text={keyword.replace(' ', '+')}&from_global=true"

    def get_data(self, keyword):
        """
        生成用于演示的 V3.0 高级模拟数据
        (模拟不同类型的爆款、蓝海品、红海品)
        """
        data = []
        base_price = random.randint(800, 3000)
        
        scenarios = [
            # 1. 爆款模型: 销量大，价格适中
            {"review_range": (500, 2000), "price_mod": (0, 200), "rating": (4.5, 4.9)},
            # 2. 蓝海模型: 销量起步，价格高，评分一般 (机会最大)
            {"review_range": (50, 200), "price_mod": (500, 1000), "rating": (3.5, 4.2)},
            # 3. 滞销模型: 销量低，价格低
            {"review_range": (0, 10), "price_mod": (-300, 0), "rating": (3.0, 5.0)},
            # 4. 红海卷王: 销量巨高，价格极低
            {"review_range": (3000, 5000), "price_mod": (-500, -200), "rating": (4.8, 5.0)}
        ]
        
        # 模拟标题词库
        nouns = [keyword, f"Premium {keyword}", f"{keyword} Gift Set", f"Pro {keyword}", f"Mini {keyword}"]

        for i in range(20): # 模拟20个竞品
            scenario = random.choice(scenarios)
            price_rub = base_price + random.randint(*scenario["price_mod"])
            price_rub = max(100, price_rub)
            
            reviews = random.randint(*scenario["review_range"])
            rating = round(random.uniform(*scenario["rating"]), 1)
            
            item = {
                "id": i,
                "title_origin": f"{random.choice(nouns)} #{i+1}",
                "price_rub": price_rub,
                "reviews": reviews,
                "rating": rating,
                "link": self.generate_real_search_link(keyword)
            }
            data.append(item)
        return data

# --- 4. AI 爆款判定算法 ---
def analyze_potential(row):
    """
    AI打分逻辑：综合 ROI、销量需求、竞争难度(评分)
    """
    score = 0
    reasons = []

    # A. 利润维度 (权重 40)
    roi = row['ROI (%)']
    if roi >= 50: score += 40
    elif roi >= 30: score += 30
    elif roi >= 15: score += 15
    else: score += 0 

    # B. 需求维度 (权重 30)
    rev = row['reviews']
    if rev > 1000: score += 30; reasons.append("🔥需求极高")
    elif rev > 300: score += 20; reasons.append("✅需求稳定")
    elif rev > 50: score += 10; reasons.append("🌱潜力新品")
    else: score += 0

    # C. 竞争机会 (权重 20) - 寻找评分 3.8-4.5 的痛点产品
    rating = row['rating']
    if 3.8 <= rating <= 4.5:
        score += 20
        reasons.append("🎯有痛点可改进")
    elif rating < 3.8:
        score += 10 
    else:
        score += 5 # 竞品太完美，难切入

    # D. 最终定级
    if score >= 80: verdict = "💎 强烈推荐"
    elif score >= 60: verdict = "⭐ 值得尝试"
    elif score >= 40: verdict = "😐 表现平平"
    else: verdict = "❌ 建议避坑"

    return pd.Series([score, verdict, " ".join(reasons)])

# --- 5. 侧边栏：成本设置 ---
st.sidebar.title("💰 成本配置")
st.sidebar.markdown("修改此处参数，右侧数据会自动更新")
exchange_rate = st.sidebar.number_input("汇率 (1卢布=CNY)", 0.075, format="%.3f")
product_cost = st.sidebar.number_input("进货价 (¥)", 20.0)
shipping_cost = st.sidebar.number_input("运费 (¥)", 30.0)
fee_percent = st.sidebar.slider("平台佣金 (%)", 10, 40, 15) / 100

st.sidebar.divider()
st.sidebar.info(f"当前单件总成本: ¥{product_cost + shipping_cost:.2f}")

# --- 6. 主界面 ---
st.title("🔥 Ozon 爆款捕手 V3.0 (团队私享版)")
st.caption("集成 AI 利润计算与爆款潜力评分模型")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("输入关键词 (例如: crochet bag)", "crochet bag")
with col2:
    start_btn = st.button("开始挖掘", type="primary", use_container_width=True)

if start_btn:
    analyzer = OzonAnalyzer()
    
    with st.spinner("正在分析市场数据与利润模型..."):
        time.sleep(1) # 模拟加载体验
        
        # 1. 获取数据
        raw_data = analyzer.get_data(keyword)
        df = pd.DataFrame(raw_data)
        
        # 2. 基础计算
        df['价格 (CNY)'] = df['price_rub'] * exchange_rate
        df['成本 (¥)'] = product_cost + shipping_cost
        df['预估净利 (¥)'] = df['价格 (CNY)'] * (1 - fee_percent) - df['成本 (¥)']
        df['ROI (%)'] = (df['预估净利 (¥)'] / df['成本 (¥)']) * 100
        
        # 3. 翻译标题
        df['中文标题'] = df['title_origin'].apply(analyzer.translate)

        # 4. 🔥 调用爆款判定模块
        df[['爆款分', 'AI建议', '标签']] = df.apply(analyze_potential, axis=1)
        
        # 按分数倒序排列
        df = df.sort_values(by='爆款分', ascending=False)

    # --- 结果展示区 ---

    # 🏆 顶部推荐卡片
    top_product = df.iloc[0]
    st.markdown("### 🏆 AI 严选：当前最具潜力商品")
    
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.info(f"**{top_product['中文标题']}**")
        st.caption(f"原始标题: {top_product['title_origin']}")
        st.write(f"🏷️ **分析标签**: {top_product['标签']}")
    with c2:
        st.metric("爆款评分", f"{top_product['爆款分']} 分", delta=top_product['AI建议'])
    with c3:
        st.metric("预估ROI", f"{top_product['ROI (%)']:.1f}%", 
                  delta_color="normal" if top_product['ROI (%)'] > 30 else "inverse")

    st.divider()

    # 📊 详细数据表
    st.subheader("📋 全量选品分析表")
    
    show_df = df[['中文标题', 'price_rub', 'reviews', 'rating', 'ROI (%)', '爆款分', 'AI建议']]
    
    st.dataframe(
        show_df.style.background_gradient(subset=['爆款分'], cmap="RdYlGn", vmin=0, vmax=100),
        column_config={
            "price_rub": st.column_config.NumberColumn("卢布价", format="₽%d"),
            "reviews": st.column_config.NumberColumn("评价数(热度)"),
            "rating": st.column_config.NumberColumn("评分", format="%.1f ⭐"),
            "ROI (%)": st.column_config.NumberColumn("投资回报率", format="%.0f%%"),
            "爆款分": st.column_config.ProgressColumn("潜力值", min_value=0, max_value=100),
        },
        use_container_width=True
    )

    # 📈 图表分析
    st.subheader
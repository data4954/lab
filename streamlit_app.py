"""
碳酸锂 LC2609 机构持仓分析网页
数据来源：广州期货交易所（GFEX）
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from data_fetcher import (
    fetch_history_data,
    get_latest_data,
    process_for_chart,
    generate_analysis_text,
)

# ============ 页面配置 ============
st.set_page_config(
    page_title="碳酸锂LC2609持仓分析",
    page_icon="📊",
    layout="wide",
)

# ============ 自定义样式 ============
st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        padding: 0.5rem 0;
    }
    .sub-title {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
    }
    .long-color { color: #e74c3c; font-weight: bold; }
    .short-color { color: #27ae60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============ 标题区 ============
st.markdown('<div class="main-title">📊 碳酸锂 LC2609 机构持仓分析</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">数据来源：广州期货交易所（GFEX）| 前5大席位 | 2026年2月至今</div>', unsafe_allow_html=True)

st.divider()

# ============ 侧边栏参数 ============
with st.sidebar:
    st.header("⚙️ 参数设置")

    contract = st.selectbox(
        "合约选择",
        ["lc2609", "lc2606", "lc2607", "lc2611"],
        index=0,
        format_func=lambda x: x.upper()
    )

    top_n = st.slider("显示席位数", min_value=3, max_value=10, value=5)

    st.divider()

    start_date = st.date_input(
        "起始日期",
        value=datetime(2026, 2, 1),
        min_value=datetime(2023, 11, 10),
        max_value=datetime.now(),
    )

    end_date = st.date_input(
        "截止日期",
        value=datetime.now(),
        min_value=datetime(2023, 11, 10),
        max_value=datetime.now(),
    )

    st.divider()
    st.markdown("**关于本工具**")
    st.markdown(
        "本工具自动获取广期所公开的日持仓排名数据，"
        "展示碳酸锂期货主要机构席位的持仓变动趋势，"
        "辅助分析资金动向。"
    )
    st.markdown("⚠️ 仅供参考，不构成投资建议。")


# ============ 数据加载 ============
@st.cache_data(ttl=1800, show_spinner=False)
def load_all_data(start_str, end_str, contract_code, top_num):
    """缓存加载全部历史数据"""
    return fetch_history_data(
        start_date=start_str,
        end_date=end_str,
        contract=contract_code,
        top_n=top_num,
    )


# 转换日期格式
start_str = start_date.strftime("%Y%m%d")
end_str = end_date.strftime("%Y%m%d")

# 加载数据
with st.spinner("正在从广期所获取持仓数据，首次加载可能需要1-2分钟..."):
    history_df = load_all_data(start_str, end_str, contract, top_n)

if history_df.empty:
    st.error("❌ 未能获取到数据，请检查日期范围或稍后重试。")
    st.stop()

# ============ 第一区：最新一日摘要 ============
st.header("📋 最新持仓概况")

# 获取最新日期的数据
latest_date = history_df["date"].max()
latest_df = history_df[history_df["date"] == latest_date]

# 生成分析文字
analysis_text = generate_analysis_text(latest_df, latest_date, top_n)
st.markdown(analysis_text)

st.divider()

# ============ 第二区：多空持仓表格 ============
st.header("📊 当日前5大席位详情")

col_long, col_short = st.columns(2)

with col_long:
    st.subheader("🔴 多头持仓排名")
    long_display = latest_df[["rank", "long_party_name", "long_open_interest", "long_open_interest_chg"]].copy()
    long_display.columns = ["排名", "席位名称", "持仓量(手)", "增减(手)"]
    long_display = long_display.head(top_n).reset_index(drop=True)

    # 样式化显示
    st.dataframe(
        long_display.style.applymap(
            lambda x: "color: red" if isinstance(x, (int, float)) and x > 0 else
                      "color: green" if isinstance(x, (int, float)) and x < 0 else "",
            subset=["增减(手)"]
        ),
        use_container_width=True,
        hide_index=True,
    )

with col_short:
    st.subheader("🟢 空头持仓排名")
    short_display = latest_df[["rank", "short_party_name", "short_open_interest", "short_open_interest_chg"]].copy()
    short_display.columns = ["排名", "席位名称", "持仓量(手)", "增减(手)"]
    short_display = short_display.head(top_n).reset_index(drop=True)

    st.dataframe(
        short_display.style.applymap(
            lambda x: "color: red" if isinstance(x, (int, float)) and x > 0 else
                      "color: green" if isinstance(x, (int, float)) and x < 0 else "",
            subset=["增减(手)"]
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ============ 第三区：历史趋势曲线图 ============
st.header("📈 持仓趋势曲线（2026年2月至今）")

# 处理数据
long_pivot, short_pivot, long_chg_pivot, short_chg_pivot = process_for_chart(history_df, top_n)

if long_pivot is not None and short_pivot is not None:
    # Tab 切换不同视图
    tab1, tab2, tab3, tab4 = st.tabs([
        "多头持仓趋势", "空头持仓趋势", "多头每日增减", "空头每日增减"
    ])

    # 颜色方案
    colors = ['#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#1abc9c',
              '#e67e22', '#2ecc71', '#e91e63', '#00bcd4', '#ff5722']

    with tab1:
        fig_long = go.Figure()
        for i, col in enumerate(long_pivot.columns):
            fig_long.add_trace(go.Scatter(
                x=long_pivot.index,
                y=long_pivot[col],
                mode="lines+markers",
                name=col,
                line=dict(width=2, color=colors[i % len(colors)]),
                marker=dict(size=3),
                hovertemplate=f"{col}<br>日期: %{{x}}<br>持仓: %{{y:,.0f}}手<extra></extra>"
            ))
        fig_long.update_layout(
            title="前5大多头席位持仓量变化",
            xaxis_title="日期",
            yaxis_title="持仓量（手）",
            hovermode="x unified",
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_long, use_container_width=True)

    with tab2:
        fig_short = go.Figure()
        for i, col in enumerate(short_pivot.columns):
            fig_short.add_trace(go.Scatter(
                x=short_pivot.index,
                y=short_pivot[col],
                mode="lines+markers",
                name=col,
                line=dict(width=2, color=colors[i % len(colors)]),
                marker=dict(size=3),
                hovertemplate=f"{col}<br>日期: %{{x}}<br>持仓: %{{y:,.0f}}手<extra></extra>"
            ))
        fig_short.update_layout(
            title="前5大空头席位持仓量变化",
            xaxis_title="日期",
            yaxis_title="持仓量（手）",
            hovermode="x unified",
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_short, use_container_width=True)

    with tab3:
        fig_long_chg = go.Figure()
        for i, col in enumerate(long_chg_pivot.columns):
            fig_long_chg.add_trace(go.Bar(
                x=long_chg_pivot.index,
                y=long_chg_pivot[col],
                name=col,
                marker_color=colors[i % len(colors)],
                hovertemplate=f"{col}<br>日期: %{{x}}<br>增减: %{{y:+,.0f}}手<extra></extra>"
            ))
        fig_long_chg.update_layout(
            title="前5大多头席位每日增减变化",
            xaxis_title="日期",
            yaxis_title="增减量（手）",
            barmode="group",
            hovermode="x unified",
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_long_chg, use_container_width=True)

    with tab4:
        fig_short_chg = go.Figure()
        for i, col in enumerate(short_chg_pivot.columns):
            fig_short_chg.add_trace(go.Bar(
                x=short_chg_pivot.index,
                y=short_chg_pivot[col],
                name=col,
                marker_color=colors[i % len(colors)],
                hovertemplate=f"{col}<br>日期: %{{x}}<br>增减: %{{y:+,.0f}}手<extra></extra>"
            ))
        fig_short_chg.update_layout(
            title="前5大空头席位每日增减变化",
            xaxis_title="日期",
            yaxis_title="增减量（手）",
            barmode="group",
            hovermode="x unified",
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_short_chg, use_container_width=True)

    st.divider()

    # ============ 第四区：多空力量对比曲线 ============
    st.header("⚖️ 多空力量对比")

    # 计算每日前5名多头总持仓 vs 前5名空头总持仓
    daily_long_total = history_df.groupby("date")["long_open_interest"].sum().reset_index()
    daily_short_total = history_df.groupby("date")["short_open_interest"].sum().reset_index()
    daily_comparison = daily_long_total.merge(daily_short_total, on="date")
    daily_comparison["net"] = daily_comparison["long_open_interest"] - daily_comparison["short_open_interest"]

    fig_compare = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            f"前{top_n}名多头/空头合计持仓对比",
            f"净多头持仓（多头 - 空头）"
        ),
        row_heights=[0.6, 0.4],
    )

    # 上图：多空持仓对比
    fig_compare.add_trace(go.Scatter(
        x=daily_comparison["date"],
        y=daily_comparison["long_open_interest"],
        mode="lines",
        name="多头合计",
        line=dict(color="#e74c3c", width=2),
        fill="tonexty" if False else None,
    ), row=1, col=1)

    fig_compare.add_trace(go.Scatter(
        x=daily_comparison["date"],
        y=daily_comparison["short_open_interest"],
        mode="lines",
        name="空头合计",
        line=dict(color="#27ae60", width=2),
    ), row=1, col=1)

    # 下图：净多头（柱状图，正红负绿）
    net_colors = ["#e74c3c" if v >= 0 else "#27ae60" for v in daily_comparison["net"]]
    fig_compare.add_trace(go.Bar(
        x=daily_comparison["date"],
        y=daily_comparison["net"],
        name="净多头",
        marker_color=net_colors,
    ), row=2, col=1)

    fig_compare.update_layout(
        height=650,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_compare.update_yaxes(title_text="持仓量（手）", row=1, col=1)
    fig_compare.update_yaxes(title_text="净持仓（手）", row=2, col=1)
    fig_compare.update_xaxes(title_text="日期", row=2, col=1)

    st.plotly_chart(fig_compare, use_container_width=True)

else:
    st.warning("历史数据不足，无法生成趋势图。")

# ============ 底部信息 ============
st.divider()
st.markdown(
    f"""
    <div style='text-align: center; color: #888; font-size: 0.85rem;'>
        数据更新时间：{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]} |
        数据来源：广州期货交易所（GFEX）公开持仓排名 |
        合约：{contract.upper()} |
        ⚠️ 本页面仅供研究参考，不构成任何投资建议
    </div>
    """,
    unsafe_allow_html=True
)

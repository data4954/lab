"""
碳酸锂 LC2609 持仓数据获取模块
数据来源：广州期货交易所（GFEX）通过 akshare 接口
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st


def get_trading_dates(start_date: str, end_date: str) -> list:
    """
    生成交易日列表（排除周末）
    start_date: '20260201' 格式
    end_date: '20260512' 格式
    """
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    dates = []
    current = start
    while current <= end:
        # 排除周六(5)和周日(6)
        if current.weekday() < 5:
            dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_single_day(date: str, contract: str = "lc2609"):
    """
    获取单日持仓排名数据
    返回 DataFrame 或 None（如果当天无数据）
    """
    try:
        result = ak.futures_gfex_position_rank(date=date, vars_list=["lc"])
        df = result.get(contract)
        if df is not None and not df.empty:
            df = df.copy()
            df["date"] = date
            return df
        return None
    except Exception:
        return None


def fetch_history_data(
    start_date: str = "20260201",
    end_date: str = None,
    contract: str = "lc2609",
    top_n: int = 5,
    progress_callback=None,
):
    """
    获取历史持仓数据（2026年2月至今）
    返回包含所有交易日前N名席位的 DataFrame

    参数:
        start_date: 起始日期
        end_date: 截止日期，默认为今天
        contract: 合约代码
        top_n: 取前N名
        progress_callback: 进度回调函数
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")

    dates = get_trading_dates(start_date, end_date)
    all_data = []

    for i, date in enumerate(dates):
        df = fetch_single_day(date, contract)
        if df is not None:
            # 只取前 top_n 名
            df_top = df.head(top_n).copy()
            all_data.append(df_top)

        if progress_callback:
            progress_callback((i + 1) / len(dates))

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        return combined
    return pd.DataFrame()


def get_latest_data(contract: str = "lc2609"):
    """
    获取最新一个交易日的持仓数据
    会往前尝试最多7天，找到有数据的交易日
    """
    today = datetime.now()
    for i in range(7):
        date = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = fetch_single_day(date, contract)
        if df is not None:
            return df, date
    return None, None


def process_for_chart(df: pd.DataFrame, top_n: int = 5):
    """
    处理数据用于曲线图展示
    返回:
        long_pivot: 多头持仓透视表 (日期 x 席位)
        short_pivot: 空头持仓透视表 (日期 x 席位)
        long_chg_pivot: 多头增减透视表
        short_chg_pivot: 空头增减透视表
    """
    if df.empty:
        return None, None, None, None

    # 多头数据
    long_df = df[["date", "long_party_name", "long_open_interest", "long_open_interest_chg"]].copy()
    long_df = long_df.rename(columns={
        "long_party_name": "席位",
        "long_open_interest": "持仓量",
        "long_open_interest_chg": "增减"
    })

    # 空头数据
    short_df = df[["date", "short_party_name", "short_open_interest", "short_open_interest_chg"]].copy()
    short_df = short_df.rename(columns={
        "short_party_name": "席位",
        "short_open_interest": "持仓量",
        "short_open_interest_chg": "增减"
    })

    # 找出出现频次最高的前 top_n 个席位
    long_top_seats = long_df["席位"].value_counts().head(top_n).index.tolist()
    short_top_seats = short_df["席位"].value_counts().head(top_n).index.tolist()

    # 过滤只保留top席位
    long_df = long_df[long_df["席位"].isin(long_top_seats)]
    short_df = short_df[short_df["席位"].isin(short_top_seats)]

    # 透视
    long_pivot = long_df.pivot_table(index="date", columns="席位", values="持仓量", aggfunc="first")
    short_pivot = short_df.pivot_table(index="date", columns="席位", values="持仓量", aggfunc="first")
    long_chg_pivot = long_df.pivot_table(index="date", columns="席位", values="增减", aggfunc="first")
    short_chg_pivot = short_df.pivot_table(index="date", columns="席位", values="增减", aggfunc="first")

    return long_pivot, short_pivot, long_chg_pivot, short_chg_pivot


def generate_analysis_text(df: pd.DataFrame, date: str, top_n: int = 5) -> str:
    """
    基于持仓数据自动生成中文分析文字
    模仿专业期货研究员的分析风格
    """
    if df is None or df.empty:
        return "暂无数据"

    # 取前 top_n 名
    df_top = df.head(top_n)

    # 多头统计
    long_total = df_top["long_open_interest"].sum()
    long_chg_total = df_top["long_open_interest_chg"].sum()

    # 空头统计
    short_total = df_top["short_open_interest"].sum()
    short_chg_total = df_top["short_open_interest_chg"].sum()

    # 净多头
    net_long = long_total - short_total
    net_chg = long_chg_total - short_chg_total

    # 多头增仓的席位
    long_add = df_top[df_top["long_open_interest_chg"] > 0]
    long_reduce = df_top[df_top["long_open_interest_chg"] < 0]

    # 空头增仓的席位
    short_add = df_top[df_top["short_open_interest_chg"] > 0]
    short_reduce = df_top[df_top["short_open_interest_chg"] < 0]

    # 格式化日期
    date_fmt = f"{date[:4]}年{date[4:6]}月{date[6:8]}日"

    # 构建分析文字
    lines = []
    lines.append(f"**{date_fmt} 碳酸锂LC2609持仓分析**\n")

    # 总体判断
    if long_chg_total > 0 and short_chg_total > 0:
        if long_chg_total > short_chg_total:
            sentiment = "多空双方同时增仓，但多头增仓力度更大，资金面偏多"
        elif short_chg_total > long_chg_total:
            sentiment = "多空双方同时增仓，空头增仓力度更大，资金面偏空"
        else:
            sentiment = "多空双方增仓势均力敌，资金面呈博弈态势"
    elif long_chg_total > 0 and short_chg_total <= 0:
        sentiment = "多头主动增仓，空头离场，资金面明显偏多"
    elif long_chg_total <= 0 and short_chg_total > 0:
        sentiment = "空头主动增仓，多头离场，资金面明显偏空"
    else:
        sentiment = "多空双方均减仓，市场观望情绪浓厚"

    lines.append(f"**总体判断：** {sentiment}\n")

    # 数据摘要
    lines.append(f"- 前{top_n}名多头合计持仓 **{long_total:,}** 手，较前日增减 **{long_chg_total:+,}** 手")
    lines.append(f"- 前{top_n}名空头合计持仓 **{short_total:,}** 手，较前日增减 **{short_chg_total:+,}** 手")
    lines.append(f"- 净多头持仓（多-空）：**{net_long:+,}** 手，净变动 **{net_chg:+,}** 手\n")

    # 多头详情
    lines.append("**多头动向：**")
    if not long_add.empty:
        add_details = "、".join(
            [f"{row['long_party_name']}增{int(row['long_open_interest_chg']):+d}手"
             for _, row in long_add.iterrows()]
        )
        lines.append(f"- 增仓：{add_details}")
    if not long_reduce.empty:
        reduce_details = "、".join(
            [f"{row['long_party_name']}{int(row['long_open_interest_chg']):+d}手"
             for _, row in long_reduce.iterrows()]
        )
        lines.append(f"- 减仓：{reduce_details}")

    lines.append("")

    # 空头详情
    lines.append("**空头动向：**")
    if not short_add.empty:
        add_details = "、".join(
            [f"{row['short_party_name']}增{int(row['short_open_interest_chg']):+d}手"
             for _, row in short_add.iterrows()]
        )
        lines.append(f"- 增仓：{add_details}")
    if not short_reduce.empty:
        reduce_details = "、".join(
            [f"{row['short_party_name']}{int(row['short_open_interest_chg']):+d}手"
             for _, row in short_reduce.iterrows()]
        )
        lines.append(f"- 减仓：{reduce_details}")

    # 风险提示
    lines.append("\n---")
    lines.append("*注：以上数据来源于广州期货交易所公开持仓排名，仅供参考，不构成投资建议。*")

    return "\n".join(lines)

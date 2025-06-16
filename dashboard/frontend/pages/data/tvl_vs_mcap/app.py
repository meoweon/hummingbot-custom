import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from defillama import DefiLlama

from frontend.st_utils import initialize_st_page, t

initialize_st_page(page_title=t("TVL vs Market Cap"), icon="🦉")

# Start content here
MIN_TVL = 1000000.0
MIN_MCAP = 1000000.0


# 常见链名和类别的翻译映射
def get_translated_name(name):
    translation_mapping = {
        "Ethereum": "以太坊",
        "Solana": "索拉纳",
        "Binance": "币安链",
        "Polygon": "Polygon",
        "Avalanche": "雪崩",
        "Multi-Chain": "多链",
        "Liquid Staking": "流动性质押",
        "Bridge": "跨链桥",
        "Yield": "收益",
        "CEX": "中心化交易所",
        "Restaking": "再质押",
        "Lending": "借贷",
        "DEX": "去中心化交易所",
        "Chain": "区块链",
    }
    return t(name) if name in translation_mapping else name


@st.cache_data
def get_tvl_mcap_data():
    llama = DefiLlama()
    df = pd.DataFrame(llama.get_all_protocols())
    tvl_mcap_df = df.loc[(df["tvl"] > 0) & (df["mcap"] > 0), ["name", "tvl", "mcap", "chain", "category", "slug"]].sort_values(
        by=["mcap"], ascending=False
    )
    return tvl_mcap_df[(tvl_mcap_df["tvl"] > MIN_TVL) & (tvl_mcap_df["mcap"] > MIN_MCAP)]


def get_protocols_by_chain_category(protocols: pd.DataFrame, group_by: list, nth: list):
    return protocols.sort_values("tvl", ascending=False).groupby(group_by).nth(nth).reset_index()


with st.spinner(text=t("In progress")):
    tvl_mcap_df = get_tvl_mcap_data()

default_chains = ["Ethereum", "Solana", "Binance", "Polygon", "Multi-Chain", "Avalanche"]

st.write(f"### {t('Chains')} 🔗")
chains = st.multiselect(t("Select the chains to analyze:"), options=tvl_mcap_df["chain"].unique(), default=default_chains)

scatter = px.scatter(
    data_frame=tvl_mcap_df[tvl_mcap_df["chain"].isin(chains)],
    x="tvl",
    y="mcap",
    color="chain",
    trendline="ols",
    log_x=True,
    log_y=True,
    height=800,
    hover_data=["name"],
    template="plotly_dark",
    title=t("TVL vs MCAP"),
    labels={"tvl": t("TVL (USD)"), "mcap": t("Market Cap (USD)"), "chain": t("chain")},
)

st.plotly_chart(scatter, use_container_width=True)

st.write("---")
st.write(f"### {t('SunBurst')} 🌞")
groupby = st.selectbox(t("Group by:"), [["chain", "category"], ["category", "chain"]])
nth = st.slider(t("Top protocols by Category"), min_value=1, max_value=5)

filtered_df = tvl_mcap_df[tvl_mcap_df["chain"].isin(chains)].copy()

# 为旭日图创建翻译版本
for column in ["chain", "category"]:
    if column in filtered_df.columns:
        filtered_df[column] = filtered_df[column].apply(get_translated_name)

proto_agg = get_protocols_by_chain_category(filtered_df, groupby, np.arange(0, nth, 1).tolist())
groupby.append("slug")
sunburst = px.sunburst(
    proto_agg,
    path=groupby,
    values="tvl",
    height=800,
    title=t("SunBurst"),
    template="plotly_dark",
)

st.plotly_chart(sunburst, use_container_width=True)

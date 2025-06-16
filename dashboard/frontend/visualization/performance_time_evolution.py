import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from frontend.visualization.theme import get_color_scheme
from frontend.utils.i18n import t


def create_combined_subplots(executors: pd.DataFrame):
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=[t("Cumulative PnL"), t("Cumulative Volume"), t("Cumulative Positions"), t("Win/Loss Ratio")],
    )

    pnl_trace = get_pnl_traces(executors)
    fig.add_trace(pnl_trace, row=1, col=1)

    volume_trace = get_volume_bar_traces(executors)
    fig.add_trace(volume_trace, row=2, col=1)

    activity_trace = get_total_executions_with_position_bar_traces(executors)
    fig.add_trace(activity_trace, row=3, col=1)

    win_loss_fig = get_win_loss_ratio_fig(executors)
    for trace in win_loss_fig.data:
        fig.add_trace(trace, row=4, col=1)

    fig.update_layout(showlegend=True, yaxis4=dict(type="linear", range=[1, 100], ticksuffix="%"))

    fig.update_layout(
        height=1000,
        width=800,
        title_text=t("Global Aggregated Performance Metrics"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
    )

    fig.update_yaxes(title_text=t("$ Quote"), row=1, col=1)
    fig.update_yaxes(title_text=t("$ Quote"), row=2, col=1)
    fig.update_yaxes(title_text=t("# Executors"), row=3, col=1)

    return fig


def get_pnl_traces(executors: pd.DataFrame):
    color_scheme = get_color_scheme()
    executors.sort_values("close_timestamp", inplace=True)
    executors["net_pnl_quote"] = pd.to_numeric(executors["net_pnl_quote"], errors="coerce").fillna(0.0)
    executors["cum_net_pnl_quote"] = executors["net_pnl_quote"].cumsum()
    scatter_traces = go.Scatter(
        name=t("Cum Realized PnL"),
        x=executors["close_datetime"],
        y=executors["cum_net_pnl_quote"],
        marker_color=executors["cum_net_pnl_quote"].apply(lambda x: color_scheme["buy"] if x > 0 else color_scheme["sell"]),
        showlegend=False,
        line_shape="hv",
        fill="tozeroy",
    )
    return scatter_traces


def get_volume_bar_traces(executors: pd.DataFrame):
    color_scheme = get_color_scheme()
    executors.sort_values("close_timestamp", inplace=True)
    executors["filled_amount_quote"] = pd.to_numeric(executors["filled_amount_quote"], errors="coerce").fillna(0.0)
    executors["cum_filled_amount_quote"] = executors["filled_amount_quote"].cumsum() * 2
    scatter_traces = go.Scatter(
        name=t("Cum Volume"),
        x=executors["close_datetime"],
        y=executors["cum_filled_amount_quote"],
        marker_color=executors["cum_filled_amount_quote"].apply(lambda x: color_scheme["buy"] if x > 0 else color_scheme["sell"]),
        showlegend=False,
        fill="tozeroy",
    )
    return scatter_traces


def get_total_executions_with_position_bar_traces(executors: pd.DataFrame):
    color_scheme = get_color_scheme()
    executors.sort_values("close_timestamp", inplace=True)
    executors["net_pnl_pct"] = pd.to_numeric(executors["net_pnl_pct"], errors="coerce").fillna(0.0)
    executors["cum_n_trades"] = (executors["net_pnl_pct"] != 0).cumsum()
    scatter_traces = go.Scatter(
        name=t("Cum Activity"),
        x=executors["close_datetime"],
        y=executors["cum_n_trades"],
        marker_color=executors["cum_n_trades"].apply(lambda x: color_scheme["buy"] if x > 0 else color_scheme["sell"]),
        showlegend=False,
        line_shape="hv",
        fill="tozeroy",
    )
    return scatter_traces


def get_win_loss_ratio_fig(executors: pd.DataFrame):
    df = executors.copy()
    df.to_csv("executors.csv", index=False)
    df.sort_values("close_timestamp", inplace=True)
    df["net_pnl_pct"] = pd.to_numeric(df["net_pnl_pct"], errors="coerce").fillna(0.0)
    df = df[df["net_pnl_pct"] != 0]
    df["cum_win_signals"] = (df["net_pnl_pct"] > 0).cumsum()
    df["cum_loss_signals"] = (df["net_pnl_pct"] < 0).cumsum()
    df["acc_over_time"] = df["cum_win_signals"] / np.arange(1, len(df) + 1)

    df["total_signals"] = df["cum_win_signals"] + df["cum_loss_signals"]
    df["win_ratio"] = df["cum_win_signals"] / df["total_signals"]
    df["loss_ratio"] = df["cum_loss_signals"] / df["total_signals"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["close_datetime"],
            y=df["win_ratio"],
            mode="lines",
            line=dict(width=0.5, color="rgb(184, 247, 212)"),
            stackgroup="one",
            groupnorm="percent",
            name=t("Win Ratio"),
            line_shape="hv",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["close_datetime"],
            y=df["loss_ratio"],
            mode="lines",
            line=dict(width=0.5, color="rgb(111, 231, 219)"),
            stackgroup="one",
            name=t("Loss Ratio"),
            line_shape="hv",
            showlegend=False,
        )
    )

    fig.update_layout(showlegend=False, yaxis=dict(type="linear", range=[1, 100], ticksuffix="%"))

    return fig

"""
Build matplotlib figures from a pandas DataFrame and user options.

Used by the NL Query Dialog visualization flow (Approach 1: Python/pandas + plotting).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


def build_figure(df: pd.DataFrame, options: dict[str, Any]) -> plt.Figure:
    """
    Build a matplotlib Figure from a DataFrame and options dict.

    Options expected:
        chart_type: str - one of "bar", "line", "scatter", "histogram", "box"
        x_col: str - column name for X axis (or single numeric for histogram)
        y_col: optional str - column name for Y axis (bar/line/scatter)
        series_col: optional str - column for grouping/series (bar/line/scatter)
        title: str
        x_label: str
        y_label: str
        palette: str - seaborn palette name or "default"
        group_by: optional str - column to group by before plotting
        agg: optional str - "sum", "mean", "count" when group_by is set
    """
    chart_type = (options.get("chart_type") or "bar").lower()
    x_col = options.get("x_col")
    y_col = options.get("y_col")
    series_col = options.get("series_col")
    title = options.get("title") or ""
    x_label = options.get("x_label") or (x_col or "")
    y_label = options.get("y_label") or (y_col or "")
    palette_name = options.get("palette") or "default"
    group_by = options.get("group_by")
    agg = (options.get("agg") or "mean").lower()

    if df is None or df.empty:
        raise ValueError("DataFrame is empty")
    if not x_col and chart_type != "box":
        raise ValueError("x_col is required")

    # Optional aggregation
    plot_df = df
    if group_by and group_by in df.columns and y_col and y_col in df.columns:
        try:
            if agg == "sum":
                plot_df = df.groupby(group_by, dropna=False)[y_col].sum().reset_index()
            elif agg == "count":
                plot_df = df.groupby(group_by, dropna=False)[y_col].count().reset_index()
            else:
                plot_df = df.groupby(group_by, dropna=False)[y_col].mean().reset_index()
            # Use group_by as X when we aggregated
            x_col = group_by
        except Exception as e:
            logger.warning(f"Aggregation failed, using raw data: {e}")

    # Numeric columns for type checks
    numeric_cols = list(plot_df.select_dtypes(include=["number"]).columns)

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    palette = None if palette_name == "default" else palette_name
    if palette:
        try:
            sns.set_palette(palette)
        except Exception:
            pass

    if chart_type == "bar":
        if not y_col or y_col not in plot_df.columns:
            # Count by x_col
            counts = plot_df[x_col].value_counts().sort_index()
            x_vals = counts.index.tolist()
            y_vals = counts.values.tolist()
            ax.bar(range(len(x_vals)), y_vals, color=plt.cm.viridis(0.4), edgecolor="gray", linewidth=0.5)
            ax.set_xticks(range(len(x_vals)))
            ax.set_xticklabels([str(v) for v in x_vals], rotation=45, ha="right")
        elif series_col and series_col in plot_df.columns:
            sns.barplot(data=plot_df, x=x_col, y=y_col, hue=series_col, ax=ax, palette=palette)
        else:
            sns.barplot(data=plot_df, x=x_col, y=y_col, ax=ax, palette=palette)
        ax.tick_params(axis="x", rotation=45)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    elif chart_type == "line":
        if not y_col or y_col not in plot_df.columns:
            raise ValueError("y_col is required for line chart")
        if series_col and series_col in plot_df.columns:
            for val in plot_df[series_col].dropna().unique():
                sub = plot_df[plot_df[series_col] == val]
                ax.plot(sub[x_col].astype(str), sub[y_col], marker="o", label=str(val), markersize=4)
            ax.legend()
        else:
            plot_df = plot_df.sort_values(x_col)
            ax.plot(plot_df[x_col].astype(str), plot_df[y_col], marker="o", markersize=4)
        ax.tick_params(axis="x", rotation=45)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    elif chart_type == "scatter":
        if not y_col or y_col not in plot_df.columns:
            raise ValueError("y_col is required for scatter chart")
        x_series = plot_df[x_col]
        y_series = plot_df[y_col]
        if pd.api.types.is_numeric_dtype(x_series) and pd.api.types.is_numeric_dtype(y_series):
            if series_col and series_col in plot_df.columns:
                for val in plot_df[series_col].dropna().unique():
                    sub = plot_df[plot_df[series_col] == val]
                    ax.scatter(sub[x_col], sub[y_col], label=str(val), alpha=0.7)
                ax.legend()
            else:
                ax.scatter(x_series, y_series, alpha=0.7)
        else:
            ax.scatter(range(len(plot_df)), y_series if pd.api.types.is_numeric_dtype(y_series) else range(len(plot_df)), alpha=0.7)
            ax.set_xticks(range(len(plot_df)))
            ax.set_xticklabels([str(x_series.iloc[i]) for i in range(len(plot_df))], rotation=45, ha="right")

    elif chart_type == "histogram":
        col = x_col if x_col in plot_df.columns else (numeric_cols[0] if numeric_cols else None)
        if not col:
            raise ValueError("Need at least one numeric column for histogram")
        series = plot_df[col].dropna()
        if not pd.api.types.is_numeric_dtype(series):
            series = pd.to_numeric(series, errors="coerce").dropna()
        ax.hist(series, bins=min(30, max(10, len(series) // 5)), color=plt.cm.viridis(0.5), edgecolor="gray")

    elif chart_type == "box":
        if y_col and y_col in plot_df.columns:
            if series_col and series_col in plot_df.columns:
                sns.boxplot(data=plot_df, x=series_col, y=y_col, ax=ax, palette=palette)
            else:
                ax.boxplot(plot_df[y_col].dropna(), labels=[y_col])
        elif numeric_cols:
            ax.boxplot([plot_df[c].dropna() for c in numeric_cols], labels=numeric_cols)
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        else:
            raise ValueError("Need at least one numeric column for box plot")

    else:
        raise ValueError(f"Unknown chart_type: {chart_type}")

    if title:
        ax.set_title(title, fontsize=12)
    if x_label:
        ax.set_xlabel(x_label)
    if y_label and chart_type != "histogram":
        ax.set_ylabel(y_label)

    fig.tight_layout()
    return fig

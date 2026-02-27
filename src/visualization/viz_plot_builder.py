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
        chart_type: str - one of "bar", "line", "scatter", "histogram", "box", "pie"
        x_col: str - column name for X axis (or single numeric for histogram)
        y_col: optional str - column name for Y axis (bar/line/scatter)
        y_cols: optional list[str] - multiple value columns for pie (wedges) or grouped bar
        series_col: optional str - column for grouping/series (bar/line/scatter)
        title: str
        x_label: str
        y_label: str
        palette: str - seaborn palette name or "default"
        group_by: optional str - column to group by before plotting
        agg: optional str - "sum", "mean", "count" when group_by is set
        chart_type_fallback_message: optional str - shown when chart type was fallback (ignored by renderer)
    """
    chart_type = (options.get("chart_type") or "bar").lower()
    x_col = options.get("x_col")
    y_col = options.get("y_col")
    y_cols = options.get("y_cols")  # list of column names for multi-metric
    if y_cols is not None and not isinstance(y_cols, list):
        y_cols = None
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
        if y_cols and all(c in plot_df.columns for c in y_cols):
            # Grouped bar: multiple metrics per x
            x_vals = plot_df[x_col].astype(str).tolist()
            x_pos = list(range(len(x_vals)))
            n_series = len(y_cols)
            width = 0.8 / max(1, n_series)
            for i, col in enumerate(y_cols):
                bars_x = [p + (i - 0.5 * (n_series - 1)) * width for p in x_pos]
                vals = plot_df[col].values
                ax.bar(bars_x, vals, width=width * 0.95, label=col)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(x_vals, rotation=45, ha="right")
            ax.legend()
        elif not y_col or y_col not in plot_df.columns:
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

    elif chart_type == "pie":
        if y_cols and all(c in plot_df.columns for c in y_cols):
            # One pie: wedge labels = y_cols, sizes = sum per column (or mean)
            sizes = [plot_df[c].sum() for c in y_cols]
            if sum(sizes) == 0:
                sizes = [plot_df[c].mean() for c in y_cols]
            labels = list(y_cols)
            colors = plt.cm.viridis([i / max(1, len(y_cols)) for i in range(len(y_cols))])
            ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90)
        elif y_col and y_col in plot_df.columns and x_col and x_col in plot_df.columns:
            # One pie: x_col as labels, y_col as sizes
            plot_agg = plot_df.groupby(x_col, dropna=False)[y_col].sum().reset_index()
            labels = plot_agg[x_col].astype(str).tolist()
            sizes = plot_agg[y_col].tolist()
            colors = plt.cm.viridis([i / max(1, len(sizes)) for i in range(len(sizes))])
            ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90)
        else:
            raise ValueError("Pie chart requires y_cols (list) or x_col and y_col")

    else:
        raise ValueError(f"Unknown chart_type: {chart_type}")

    if title:
        ax.set_title(title, fontsize=12)
    if x_label:
        ax.set_xlabel(x_label)
    if y_label and chart_type not in ("histogram", "pie"):
        ax.set_ylabel(y_label)

    fig.tight_layout()
    return fig

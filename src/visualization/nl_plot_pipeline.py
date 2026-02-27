"""
NL → chart config pipeline for NL-plot feature.

Used by nl_sql/api_call.py (POST /nl_to_chart_config) and optionally by the
NL query dialog. Produces an options dict compatible with build_figure() in
viz_plot_builder.py. No code execution.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

# Chart types and palettes must match viz_plot_builder / VizOptionsDialog
CHART_TYPES = ["bar", "line", "scatter", "histogram", "box"]
PALETTES = ["default", "viridis", "Set3", "colorblind", "pastel", "muted", "deep"]


def build_chart_config_prompt(
    description: str,
    column_names: list[str],
    column_dtypes: Optional[dict[str, str]] = None,
) -> str:
    """
    Build a prompt that asks the LLM for a chart config JSON.

    Args:
        description: User's natural-language plot description.
        column_names: List of column names available in the DataFrame.
        column_dtypes: Optional map of column name -> dtype string (e.g. "int64", "object").

    Returns:
        Prompt string for the LLM.
    """
    columns_line = ", ".join(f'"{c}"' for c in column_names)
    if column_dtypes:
        dtype_line = "\n".join(f"  - {k}: {v}" for k, v in column_dtypes.items())
        columns_section = f"Column names and dtypes:\n{dtype_line}\nUse only these columns."
    else:
        columns_section = f"Column names (use only these): {columns_line}"

    return f"""You are a chart config generator. Given a short plot description and the available columns, output a single JSON object with exactly these keys. Use only the column names provided.

{columns_section}

Allowed chart_type values: {", ".join(CHART_TYPES)}
Allowed palette values: {", ".join(PALETTES)}

Required keys:
- chart_type (string, one of the allowed chart types)
- x_col (string, one of the column names; for histogram use a numeric column)
- title (string, optional but recommended)

Optional keys (use null if not needed):
- y_col (string, required for bar/line/scatter when showing a value axis)
- series_col (string, for grouping/series)
- x_label, y_label (strings)
- palette (string, one of the allowed palettes or "default")
- group_by (string, column to aggregate by)
- agg (string: "sum", "mean", "count")

Rules:
- For "bar chart of X by Y" use chart_type "bar", x_col Y, y_col X (or series_col if multiple series).
- For histogram use chart_type "histogram", x_col as the numeric column.
- For line/scatter you need both x_col and y_col.
- Output ONLY the JSON object, no markdown, no explanation, no code block wrapper.

User description: "{description}"

JSON:"""


def _extract_json_from_response(text: str) -> str:
    """Strip markdown code blocks and return the first JSON object found."""
    if not text or not text.strip():
        raise ValueError("Empty LLM response")
    text = text.strip()
    # Remove optional ```json ... ``` or ``` ... ```
    text = re.sub(r"^```\w*\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?\s*```\s*$", "", text)
    text = text.strip()
    # Find first { ... } block
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unbalanced braces in JSON response")


def parse_chart_config(
    llm_response: str,
    valid_columns: list[str],
    valid_chart_types: Optional[list[str]] = None,
    valid_palettes: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Parse and validate chart config from LLM response.

    Args:
        llm_response: Raw string from the LLM (may contain markdown).
        valid_columns: Allowed column names (e.g. list(df.columns)).
        valid_chart_types: Allowed chart_type values; defaults to CHART_TYPES.
        valid_palettes: Allowed palette values; defaults to PALETTES.

    Returns:
        Options dict suitable for build_figure(df, options).

    Raises:
        ValueError: If JSON is invalid or config fails validation.
    """
    valid_chart_types = valid_chart_types or CHART_TYPES
    valid_palettes = valid_palettes or PALETTES
    valid_col_set = set(valid_columns)

    raw = _extract_json_from_response(llm_response)
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e

    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")

    # Normalize keys and validate
    chart_type = (config.get("chart_type") or config.get("chart_type", "bar"))
    if isinstance(chart_type, str):
        chart_type = chart_type.lower().strip()
    if chart_type not in valid_chart_types:
        raise ValueError(f"chart_type must be one of {valid_chart_types}, got {chart_type!r}")

    x_col = config.get("x_col")
    if x_col is not None and isinstance(x_col, str):
        x_col = x_col.strip() or None
    if chart_type != "box" and x_col and x_col not in valid_col_set:
        raise ValueError(f"x_col must be one of {valid_columns}, got {x_col!r}")

    y_col = config.get("y_col")
    if y_col is not None and isinstance(y_col, str):
        y_col = y_col.strip() or None
    if y_col and y_col not in valid_col_set:
        raise ValueError(f"y_col must be one of {valid_columns}, got {y_col!r}")

    series_col = config.get("series_col")
    if series_col is not None and isinstance(series_col, str):
        series_col = series_col.strip() or None
    if series_col and series_col not in valid_col_set:
        raise ValueError(f"series_col must be one of {valid_columns}, got {series_col!r}")

    group_by = config.get("group_by")
    if group_by is not None and isinstance(group_by, str):
        group_by = group_by.strip() or None
    if group_by and group_by not in valid_col_set:
        raise ValueError(f"group_by must be one of {valid_columns}, got {group_by!r}")

    palette = config.get("palette") or "default"
    if isinstance(palette, str):
        palette = palette.strip() or "default"
    if palette not in valid_palettes:
        palette = "default"

    agg = (config.get("agg") or "mean")
    if isinstance(agg, str):
        agg = agg.lower().strip()
    if agg not in ("sum", "mean", "count"):
        agg = "mean"

    options: dict[str, Any] = {
        "chart_type": chart_type,
        "x_col": x_col,
        "y_col": y_col,
        "series_col": series_col,
        "title": (config.get("title") or "").strip() if config.get("title") else "",
        "x_label": (config.get("x_label") or "").strip() if config.get("x_label") else "",
        "y_label": (config.get("y_label") or "").strip() if config.get("y_label") else "",
        "palette": palette,
        "group_by": group_by,
        "agg": agg,
    }
    return options


def nl_to_plot_options(
    description: str,
    df: Any,
    llm_callback: Callable[[str], str],
) -> dict[str, Any]:
    """
    Run the NL → chart config pipeline: prompt, LLM call, parse, validate.

    Args:
        description: Natural-language plot description.
        df: DataFrame with the data (must have .columns and optionally .dtypes).
        llm_callback: Function that takes the prompt string and returns the raw LLM response.

    Returns:
        Options dict for build_figure(df, options).

    Raises:
        ValueError: If df is empty, has no columns, or LLM response is invalid.
    """
    try:
        column_names = list(df.columns)
    except Exception as e:
        raise ValueError("Invalid DataFrame: no .columns") from e
    if not column_names:
        raise ValueError("DataFrame has no columns")

    column_dtypes = None
    try:
        if hasattr(df, "dtypes"):
            column_dtypes = {str(c): str(df.dtypes[c]) for c in column_names}
    except Exception:
        pass

    prompt = build_chart_config_prompt(description, column_names, column_dtypes)
    response = llm_callback(prompt)
    return parse_chart_config(response, column_names)

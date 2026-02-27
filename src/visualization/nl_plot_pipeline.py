"""
NL → chart config pipeline for NL-plot feature.

Used by nl_sql/api_call.py (POST /nl_to_chart_config) and optionally by the
NL query dialog. Produces an options dict compatible with build_figure() in
viz_plot_builder.py. No code execution.

Also provides build_plot_code_prompt and extract_plot_code for the refactor path
(LLM → Python code → MCP runs code → PNG).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

import pandas as pd

# Chart types and palettes must match viz_plot_builder / VizOptionsDialog
CHART_TYPES = ["bar", "line", "scatter", "histogram", "box", "pie"]
PALETTES = ["default", "viridis", "Set3", "colorblind", "pastel", "muted", "deep"]


def compute_data_summary(df: Any, max_sample: int = 3) -> dict[str, dict[str, Any]]:
    """
    Compute a short per-column summary for data-aware prompts (min/max/nunique or sample).

    Args:
        df: DataFrame with .columns and .dtypes.
        max_sample: Max number of sample values to include for non-numeric columns.

    Returns:
        Dict mapping column name -> {dtype, ...stats}. Numeric: min, max, nunique.
        Non-numeric: nunique, sample_values (list).
    """
    summary: dict[str, dict[str, Any]] = {}
    try:
        cols = list(df.columns)
    except Exception:
        return summary
    for c in cols:
        try:
            s = df[c].dropna()
            dtype = str(df.dtypes[c]) if hasattr(df, "dtypes") else "unknown"
            entry: dict[str, Any] = {"dtype": dtype}
            if hasattr(s, "dtype") and (s.dtype.kind in "iufc" or "int" in dtype or "float" in dtype):
                try:
                    num = pd.to_numeric(s, errors="coerce").dropna()
                    if len(num):
                        entry["min"] = float(num.min())
                        entry["max"] = float(num.max())
                    entry["nunique"] = int(s.nunique())
                except Exception:
                    entry["nunique"] = int(s.nunique())
            else:
                entry["nunique"] = int(s.nunique())
                try:
                    samples = s.head(max_sample).astype(str).tolist()
                    entry["sample_values"] = samples
                except Exception:
                    pass
            summary[str(c)] = entry
        except Exception:
            summary[str(c)] = {"dtype": "unknown"}
    return summary


def build_chart_config_prompt(
    description: str,
    column_names: list[str],
    column_dtypes: Optional[dict[str, str]] = None,
    data_summary: Optional[dict[str, dict[str, Any]]] = None,
    chart_types: Optional[list[str]] = None,
    palettes: Optional[list[str]] = None,
) -> str:
    """
    Build a prompt that asks the LLM for a chart config JSON.

    Args:
        description: User's natural-language plot description.
        column_names: List of column names available in the DataFrame.
        column_dtypes: Optional map of column name -> dtype string (e.g. "int64", "object").
        data_summary: Optional per-column summary (min/max/nunique or sample_values) for data-aware prompts.
        chart_types: Allowed chart_type values; defaults to CHART_TYPES.
        palettes: Allowed palette values; defaults to PALETTES.

    Returns:
        Prompt string for the LLM.
    """
    chart_types = chart_types or CHART_TYPES
    palettes = palettes or PALETTES
    columns_line = ", ".join(f'"{c}"' for c in column_names)
    if column_dtypes:
        dtype_line = "\n".join(f"  - {k}: {v}" for k, v in column_dtypes.items())
        columns_section = f"Column names and dtypes:\n{dtype_line}\nUse only these columns."
    else:
        columns_section = f"Column names (use only these): {columns_line}"

    data_summary_section = ""
    if data_summary:
        lines = []
        for col, stats in data_summary.items():
            if col not in column_names:
                continue
            parts = [f"  {col}: dtype={stats.get('dtype', '?')}"]
            if "min" in stats and "max" in stats:
                parts.append(f" range=[{stats['min']},{stats['max']}]")
            if "nunique" in stats:
                parts.append(f" nunique={stats['nunique']}")
            if "sample_values" in stats:
                parts.append(f" sample={stats['sample_values']}")
            lines.append("".join(parts))
        if lines:
            data_summary_section = "Data summary (use to choose sensible axes/bins):\n" + "\n".join(lines) + "\n\n"

    examples_section = """
Examples (output only the JSON object, no markdown):
Example 1 - bar of one metric by category:
{"chart_type": "bar", "x_col": "name", "y_col": "wins", "title": "Wins by Team", "y_cols": null}
Example 2 - multiple metrics as grouped bar:
{"chart_type": "bar", "x_col": "name", "y_cols": ["hit", "so", "bb"], "title": "Hit, SO, BB by Player", "y_col": null}
Example 3 - pie with multiple wedge values:
{"chart_type": "pie", "x_col": "name", "y_cols": ["hit", "so", "bb"], "title": "Hit/SO/BB by Player"}
"""

    return f"""You are a chart config generator. Given a short plot description and the available columns, output a single JSON object. Use only the column names provided.

{columns_section}

{data_summary_section}Allowed chart_type values: {", ".join(chart_types)}
Allowed palette values: {", ".join(palettes)}

Required keys:
- chart_type (string, one of the allowed chart types)
- x_col (string, one of the column names; for histogram use a numeric column)
- title (string, optional but recommended)

Optional keys (use null if not needed):
- y_col (string, single value column for bar/line/scatter)
- y_cols (array of strings, for multiple metrics: pie wedges or grouped/stacked bar; e.g. ["hit", "so", "bb"])
- series_col (string, for grouping/series)
- x_label, y_label (strings)
- palette (string, one of the allowed palettes or "default")
- group_by (string, column to aggregate by)
- agg (string: "sum", "mean", "count")

Rules:
- For "bar chart of X by Y" use chart_type "bar", x_col Y, y_col X (or series_col if multiple series).
- For multiple metrics (e.g. "hit, so, and bb") use y_cols: ["hit", "so", "bb"]; for pie use chart_type "pie" and y_cols for wedge values.
- For "each X show A, B, C" use x_col X and y_cols [A,B,C].
- For histogram use chart_type "histogram", x_col as the numeric column.
- For line/scatter you need both x_col and y_col (or y_cols for multiple lines).
- Output ONLY the JSON object, no markdown, no explanation, no code block wrapper.
{examples_section}
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
        Options dict suitable for build_figure(df, options). May include
        y_cols (list), chart_type_fallback_message (str) if fallback was applied,
        and optional keys passed through (unsupported ones ignored by renderer).
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

    # Normalize chart_type with fallback (e.g. pie -> bar if pie not supported)
    chart_type = (config.get("chart_type") or "bar")
    if isinstance(chart_type, str):
        chart_type = chart_type.lower().strip()
    chart_type_fallback_message: Optional[str] = None
    if chart_type not in valid_chart_types:
        if chart_type == "pie" and "bar" in valid_chart_types:
            chart_type_fallback_message = "Pie not available; showing as bar."
            chart_type = "bar"
        else:
            chart_type = "bar" if "bar" in valid_chart_types else valid_chart_types[0]
            chart_type_fallback_message = f"Chart type not supported; using {chart_type}."

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

    # y_cols: array of column names for multi-metric plots
    y_cols: Optional[list[str]] = None
    if "y_cols" in config and config["y_cols"] is not None:
        if isinstance(config["y_cols"], list):
            y_cols = []
            for v in config["y_cols"]:
                if isinstance(v, str):
                    v = v.strip()
                    if v and v in valid_col_set:
                        y_cols.append(v)
            if not y_cols:
                y_cols = None

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
        "y_cols": y_cols,
        "series_col": series_col,
        "title": (config.get("title") or "").strip() if config.get("title") else "",
        "x_label": (config.get("x_label") or "").strip() if config.get("x_label") else "",
        "y_label": (config.get("y_label") or "").strip() if config.get("y_label") else "",
        "palette": palette,
        "group_by": group_by,
        "agg": agg,
    }
    if chart_type_fallback_message:
        options["chart_type_fallback_message"] = chart_type_fallback_message
    return options


def build_plot_code_prompt(
    description: str,
    column_names: list[str],
    column_dtypes: Optional[dict[str, str]] = None,
    data_summary: Optional[dict[str, dict[str, Any]]] = None,
    data_sample: Optional[list[dict[str, Any]]] = None,
    distinct_values: Optional[dict[str, list[str]]] = None,
    row_count: Optional[int] = None,
) -> str:
    """
    Build a prompt that asks the LLM for Python code that plots the DataFrame.

    The code will run in an environment where `df` is a pandas DataFrame.
    Code must set `plot_png_bytes` to the PNG bytes of the figure (e.g. via io.BytesIO).

    Args:
        description: User's natural-language plot description.
        column_names: List of column names in the DataFrame.
        column_dtypes: Optional map of column name -> dtype string.
        data_summary: Optional per-column summary for context.
        data_sample: Optional list of dict (first N rows) so LLM sees column names and types.
        distinct_values: Optional map column -> list of distinct values (for filtering).
        row_count: Optional number of rows in the full data.

    Returns:
        Prompt string for the LLM.
    """
    columns_line = ", ".join(f'"{c}"' for c in column_names)
    sections = [
        "You are a Python code generator for matplotlib plots.",
        "Given a plot description and the available DataFrame columns, output ONLY Python code (no markdown, no explanation).",
        "",
        "Available columns: " + columns_line + ".",
        "The code will run with a variable `df` (pandas DataFrame) already in scope.",
        "Allowed: pandas (pd), numpy (np), matplotlib.pyplot (plt), io (BytesIO).",
        "Do not use open(), file(), os, subprocess, or network.",
        "",
        "Requirements:",
        "1. If the user specifies particular entities (e.g. player names, team names, or 'players: nick, james', 'teams A and B'), you MUST filter df first: keep only rows where the relevant column is in those values. Use only values from the 'Valid values for filtering' list below. Example: df = df[df['name'].astype(str).str.strip().isin(['nick', 'james'])] then plot the filtered df. If no specific entities are named, plot the full df.",
        "2. Column mapping: when the user says 'players' or 'player names' use the column that holds player names (often 'name'); when they say 'teams' or 'team names' use the column that holds team names (often 'team' or 'name'). Use only column names from the available columns list.",
        "3. Build a matplotlib figure from the (possibly filtered) df (e.g. bar, line, scatter, pie, histogram).",
        "4. Save the figure to a buffer: buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); buf.seek(0)",
        "5. Set the result: plot_png_bytes = buf.getvalue()",
        "6. Use only column names from the list above.",
        "",
        "User description: \"" + description + "\"",
        "",
        "Python code:",
    ]

    if column_dtypes:
        sections.insert(4, "Column dtypes: " + ", ".join(f"{k}={v}" for k, v in column_dtypes.items()) + ".")
    if data_summary:
        lines = []
        for col, stats in data_summary.items():
            if col not in column_names:
                continue
            parts = [f"  {col}: {stats.get('dtype', '?')}"]
            if "nunique" in stats:
                parts.append(f" nunique={stats['nunique']}")
            if "sample_values" in stats:
                parts.append(f" sample={stats['sample_values']}")
            lines.append("".join(parts))
        if lines:
            sections.insert(5, "Data summary:\n" + "\n".join(lines) + "\n")
    if row_count is not None:
        sections.insert(6, f"The DataFrame has {row_count} rows.")
    if distinct_values:
        lines = [
            "Valid values for filtering (use only these). When the user names specific entities, filter df to rows where the column is in these values before plotting:"
        ]
        for col, vals in distinct_values.items():
            if col in column_names and vals:
                lines.append(f"  {col}: {vals[:20]}{'...' if len(vals) > 20 else ''}")
        sections.insert(7, "\n".join(lines) + "\n")
    if data_sample:
        try:
            sample_str = json.dumps(data_sample[:10], default=str)
            if len(sample_str) < 1500:
                sections.insert(8, "Sample rows (first few): " + sample_str + "\n")
        except Exception:
            pass

    return "\n".join(sections)


def build_plot_prompt_generator_prompt(
    description: str,
    column_names: list[str],
    column_dtypes: Optional[dict[str, str]] = None,
    data_sample: Optional[list[dict[str, Any]]] = None,
    data_summary: Optional[dict[str, dict[str, Any]]] = None,
    distinct_values: Optional[dict[str, list[str]]] = None,
    row_count: Optional[int] = None,
    chart_type_suggestion: Optional[str] = None,
) -> str:
    """
    Build the user message for LLM #1 (Plot-Prompt Generator) per nl_plot_data_4.md.

    Inputs: DataFrame schema (columns, dtypes), sample rows, user's natural-language
    request. Optional: data_summary, distinct_values, row_count, chart_type_suggestion.

    Returns the user message content. System message (rules) is fixed in the caller.
    """
    sections = [
        "=== PANDAS DATAFRAME SCHEMA AND SAMPLE ===",
        "Column names: " + ", ".join(f'"{c}"' for c in column_names) + ".",
    ]
    if column_dtypes:
        sections.append("Column dtypes: " + ", ".join(f"{k}={v}" for k, v in column_dtypes.items()) + ".")
    if row_count is not None:
        sections.append(f"Row count: {row_count}.")
    if data_summary:
        lines = []
        for col, stats in data_summary.items():
            if col not in column_names:
                continue
            parts = [f"  {col}: {stats.get('dtype', '?')}"]
            if "nunique" in stats:
                parts.append(f" nunique={stats['nunique']}")
            if "min" in stats and "max" in stats:
                parts.append(f" range=[{stats['min']},{stats['max']}]")
            if "sample_values" in stats:
                parts.append(f" sample={stats['sample_values']}")
            lines.append("".join(parts))
        if lines:
            sections.append("Data summary:\n" + "\n".join(lines))
    if distinct_values:
        sections.append("Valid values for filtering (use only these when user names entities):")
        for col, vals in distinct_values.items():
            if col in column_names and vals:
                sections.append(f"  {col}: {vals[:20]}{'...' if len(vals) > 20 else ''}")
    if data_sample:
        try:
            sample_str = json.dumps(data_sample[:10], default=str)
            if len(sample_str) < 2000:
                sections.append("Sample rows (first rows of the DataFrame):")
                sections.append(sample_str)
            else:
                sections.append("Sample rows (truncated): " + sample_str[:1500] + "...")
        except Exception:
            pass
    sections.append("")
    sections.append("=== NATURAL-LANGUAGE PLOTTING REQUEST ===")
    sections.append(description)
    if chart_type_suggestion and chart_type_suggestion.strip():
        sections.append("")
        sections.append(f"(User suggested chart type, hint only: {chart_type_suggestion.strip()})")
    sections.append("")
    sections.append(
        "Produce a single, complete prompt that instructs another LLM to generate Python plotting code. "
        "Do not generate code yourself. Output only the prompt text, no wrapper or explanation."
    )
    return "\n".join(sections)


def build_plot_brainstorm_prompt(
    description: str,
    column_names: list[str],
    chart_type_suggestion: Optional[str] = None,
    column_dtypes: Optional[dict[str, str]] = None,
    data_summary: Optional[dict[str, dict[str, Any]]] = None,
    distinct_values: Optional[dict[str, list[str]]] = None,
    row_count: Optional[int] = None,
    data_sample: Optional[list[dict[str, Any]]] = None,
) -> str:
    """
    Build a prompt that asks the LLM to propose up to 3 chart ideas (matplotlib or seaborn).
    Data context is placed first so the model brainstorms based on actual columns/dtypes/row count.
    Requires varied chart types (not all bar).
    """
    columns_line = ", ".join(f'"{c}"' for c in column_names)
    # Build data context block first so the model sees actual data shape
    data_context = [
        "=== ACTUAL SQL EXECUTION DATA (use this to choose chart types) ===",
        "Available columns: " + columns_line + ".",
    ]
    if column_dtypes:
        data_context.append("Column dtypes: " + ", ".join(f"{k}={v}" for k, v in column_dtypes.items()) + ".")
    if row_count is not None:
        data_context.append(f"Row count: {row_count}.")
    if data_summary:
        lines = []
        for col, stats in data_summary.items():
            if col not in column_names:
                continue
            parts = [f"  {col}: {stats.get('dtype', '?')}"]
            if "nunique" in stats:
                parts.append(f" nunique={stats['nunique']}")
            if "min" in stats and "max" in stats:
                parts.append(f" range=[{stats['min']},{stats['max']}]")
            if "sample_values" in stats:
                parts.append(f" sample={stats['sample_values']}")
            lines.append("".join(parts))
        if lines:
            data_context.append("Data summary:\n" + "\n".join(lines))
    if distinct_values:
        data_context.append("Valid values for filtering:")
        for col, vals in distinct_values.items():
            if col in column_names and vals:
                data_context.append(f"  {col}: {vals[:15]}{'...' if len(vals) > 15 else ''}")
    if data_sample:
        try:
            sample_str = json.dumps(data_sample[:5], default=str)
            if len(sample_str) < 1000:
                data_context.append("Sample rows: " + sample_str)
        except Exception:
            pass
    data_context.append("")

    # Chart-type diversity and data-driven rules
    rules = [
        "=== RULES ===",
        "1. Propose exactly 3 ideas with DIFFERENT chart types. Do NOT propose three bar charts or the same type twice.",
        "2. Vary chart types using the data context above:",
        "   - Few categories + one numeric column -> bar or pie for one idea.",
        "   - Many rows + numeric column -> line/trend or histogram for another idea.",
        "   - Two numeric columns -> scatter. Many numeric columns -> heatmap or pairplot.",
        "   - Categorical + numeric -> boxplot or violin (e.g. sns.boxplot, sns.violinplot) for another idea.",
        "3. Use ONLY the column names listed above. Do not invent column names (e.g. no HR, RBI, RUNS unless they appear in Available columns).",
        "4. Each idea: (a) label, (b) chart_type (e.g. bar, line, scatter, pie, seaborn_violin, seaborn_heatmap), (c) approach (one line: what to plot and how).",
        "",
        "Output format (JSON array):",
        '[{"label": "...", "chart_type": "...", "approach": "..."}, {"label": "...", "chart_type": "...", "approach": "..."}, {"label": "...", "chart_type": "...", "approach": "..."}]',
        "",
        "User description: \"" + description + "\"",
    ]
    if chart_type_suggestion and chart_type_suggestion.strip():
        rules.insert(-1, f"User suggested chart type (hint only; still propose 3 varied types): {chart_type_suggestion.strip()}.")
        rules.insert(-1, "")
    sections = data_context + rules
    sections.append("")
    sections.append("JSON array of 3 ideas (different chart_type values):")
    return "\n".join(sections)


def parse_brainstorm_ideas(llm_response: str) -> list[dict[str, Any]]:
    """
    Parse LLM response into a list of idea dicts with label, chart_type, approach.
    Returns at most 3 ideas; empty list on parse failure.
    """
    if not llm_response or not llm_response.strip():
        return []
    text = llm_response.strip()
    # Strip markdown code block if present
    if "```" in text:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            text = text[start:end]
        else:
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("["):
                    end = line.rfind("]") + 1
                    if end > 0:
                        text = line[:end]
                    break
    try:
        raw = json.loads(text)
        if not isinstance(raw, list):
            raw = [raw] if isinstance(raw, dict) else []
        ideas = []
        for item in raw[:3]:
            if isinstance(item, dict):
                ideas.append({
                    "label": str(item.get("label", "")).strip() or "Chart",
                    "chart_type": str(item.get("chart_type", "")).strip() or "bar",
                    "approach": str(item.get("approach", "")).strip() or "",
                })
        return ideas
    except (json.JSONDecodeError, TypeError):
        return []


def build_plot_select_prompt(
    description: str,
    ideas: list[dict[str, Any]],
    column_names: list[str],
    chart_type_suggestion: Optional[str] = None,
    column_dtypes: Optional[dict[str, str]] = None,
    data_summary: Optional[dict[str, dict[str, Any]]] = None,
    row_count: Optional[int] = None,
    distinct_values: Optional[dict[str, list[str]]] = None,
) -> str:
    """Build a prompt that asks the LLM to select the single best idea for the user query and data."""
    ideas_text = "\n".join(
        f"{i+1}. {idea.get('label', '')} (chart_type={idea.get('chart_type', '')}): {idea.get('approach', '')}"
        for i, idea in enumerate(ideas)
    )
    sections = [
        "Select the ONE best chart idea from the list below for the user's description and the actual data.",
        "Base your choice on: (1) how well the idea matches the user's intent, and (2) how well the chart_type fits the data (columns, dtypes, row count).",
        "Prefer an idea that matches the user's words (e.g. 'compare' -> bar or line; 'distribution' -> hist/violin/box; 'relationship' -> scatter; 'parts of whole' -> pie).",
        "",
        "Available columns: " + ", ".join(f'"{c}"' for c in column_names) + ".",
        "",
        "Ideas:",
        ideas_text,
        "",
        "User description: \"" + description + "\"",
    ]
    if chart_type_suggestion and chart_type_suggestion.strip():
        sections.append(f"User suggested chart type (consider as hint): {chart_type_suggestion.strip()}.")
    if row_count is not None:
        sections.append(f"Data has {row_count} rows.")
    sections.append("")
    sections.append("Reply with ONLY the number of the chosen idea (1, 2, or 3), then optionally a short reason after a colon. Example: 2: Best fit for comparing categories.")
    return "\n".join(sections)


def parse_selected_idea(llm_response: str, ideas: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """
    Parse LLM response to get the selected idea (1-based index). Returns the idea dict or None.
    """
    if not llm_response or not ideas:
        return ideas[0] if ideas else None
    text = llm_response.strip()
    # Extract leading number
    for i, c in enumerate(text):
        if c in "123":
            num = int(c)
            if 1 <= num <= len(ideas):
                return ideas[num - 1]
            return ideas[0] if ideas else None
        if c.isalpha() or c in ".:":
            break
    return ideas[0] if ideas else None


def build_plot_code_prompt_from_idea(
    selected_idea: dict[str, Any],
    description: str,
    column_names: list[str],
    column_dtypes: Optional[dict[str, str]] = None,
    data_summary: Optional[dict[str, dict[str, Any]]] = None,
    data_sample: Optional[list[dict[str, Any]]] = None,
    distinct_values: Optional[dict[str, list[str]]] = None,
    row_count: Optional[int] = None,
) -> str:
    """
    Build a code-generation prompt from the selected brainstorm idea.
    Instructs: any matplotlib or seaborn; only provided columns; filter by entities when user names them; set plot_png_bytes.
    """
    label = selected_idea.get("label", "Chart")
    chart_type = selected_idea.get("chart_type", "bar")
    approach = selected_idea.get("approach", "")
    columns_line = ", ".join(f'"{c}"' for c in column_names)
    idea_line = f"Selected chart: {label} (type: {chart_type}). Approach: {approach}."
    sections = [
        "You are a Python code generator for plots. Implement EXACTLY the selected chart below using matplotlib (plt) or seaborn (sns).",
        "CRITICAL: You MUST implement the selected chart_type and approach. Do NOT substitute a generic bar chart. If the selected type is line, scatter, violin, heatmap, pie, etc., use that exact visualization.",
        "",
        idea_line,
        "",
        "Available columns: " + columns_line + ".",
        "Use ONLY these column names. Do not use column names not in this list.",
        "The code runs with `df` (pandas DataFrame) in scope. Allowed: pd, np, plt, sns (seaborn), io.",
        "Do not use open(), file(), os, subprocess, or network.",
        "",
        "Requirements:",
        "1. If the user specifies particular entities (e.g. player names, 'players: nick, james'), filter df first to those rows using the 'Valid values for filtering' list below, then plot the filtered df.",
        "2. Use only column names from the Available columns list.",
        "3. Implement the chart_type above: use plt or sns accordingly (e.g. line -> plt.plot or sns.lineplot; violin -> sns.violinplot; heatmap -> sns.heatmap; pie -> plt.pie; scatter -> plt.scatter or sns.scatterplot).",
        "4. Save the figure to a buffer: buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); buf.seek(0); plot_png_bytes = buf.getvalue()",
        "5. If using seaborn, get the figure with plt.gcf() after the seaborn call, then plt.savefig(...) to the buffer. End with plot_png_bytes = buf.getvalue().",
        "",
        "User description: \"" + description + "\"",
        "",
        "Python code:",
    ]
    if column_dtypes:
        sections.insert(6, "Column dtypes: " + ", ".join(f"{k}={v}" for k, v in column_dtypes.items()) + ".")
    if data_summary:
        lines = []
        for col, stats in data_summary.items():
            if col not in column_names:
                continue
            parts = [f"  {col}: {stats.get('dtype', '?')}"]
            if "nunique" in stats:
                parts.append(f" nunique={stats['nunique']}")
            if "sample_values" in stats:
                parts.append(f" sample={stats['sample_values']}")
            lines.append("".join(parts))
        if lines:
            sections.insert(7, "Data summary:\n" + "\n".join(lines) + "\n")
    if row_count is not None:
        sections.insert(8, f"The DataFrame has {row_count} rows.")
    if distinct_values:
        lines = [
            "Valid values for filtering (use only these when user names entities):"
        ]
        for col, vals in distinct_values.items():
            if col in column_names and vals:
                lines.append(f"  {col}: {vals[:20]}{'...' if len(vals) > 20 else ''}")
        sections.insert(9, "\n".join(lines) + "\n")
    if data_sample:
        try:
            sample_str = json.dumps(data_sample[:10], default=str)
            if len(sample_str) < 1500:
                sections.insert(10, "Sample rows: " + sample_str + "\n")
        except Exception:
            pass
    return "\n".join(sections)


def extract_plot_code(llm_response: str) -> str:
    """
    Extract Python code from LLM response, stripping markdown code fences if present.

    Args:
        llm_response: Raw string from the LLM (may contain ```python ... ```).

    Returns:
        Code string ready for execution.
    """
    if not llm_response or not llm_response.strip():
        raise ValueError("Empty LLM response")
    text = llm_response.strip()
    if text.startswith("```"):
        # Remove first line (```python or ```)
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def get_heuristic_config(
    column_names: list[str],
    column_dtypes: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """
    Return a minimal valid chart config when LLM parsing fails (first categorical as x_col, first numeric as y_col).
    """
    x_col = None
    y_col = None
    for c in column_names:
        dtype = (column_dtypes or {}).get(str(c), "")
        if "int" in dtype or "float" in dtype or "number" in dtype:
            if y_col is None:
                y_col = c
        else:
            if x_col is None:
                x_col = c
        if x_col and y_col:
            break
    if not x_col and column_names:
        x_col = column_names[0]
    return {
        "chart_type": "bar",
        "x_col": x_col,
        "y_col": y_col,
        "y_cols": None,
        "series_col": None,
        "title": "Chart (heuristic fallback)",
        "x_label": "",
        "y_label": "",
        "palette": "default",
        "group_by": None,
        "agg": "mean",
        "chart_type_fallback_message": "Using default chart; LLM config could not be parsed.",
    }


def nl_to_plot_options(
    description: str,
    df: Any,
    llm_callback: Callable[[str], str],
    data_summary: Optional[dict[str, dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Run the NL → chart config pipeline: prompt, LLM call, parse, validate.

    Args:
        description: Natural-language plot description.
        df: DataFrame with the data (must have .columns and optionally .dtypes).
        llm_callback: Function that takes the prompt string and returns the raw LLM response.
        data_summary: Optional per-column summary; if None, computed from df via compute_data_summary.

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

    if data_summary is None and hasattr(df, "select_dtypes"):
        data_summary = compute_data_summary(df)

    prompt = build_chart_config_prompt(
        description, column_names, column_dtypes,
        data_summary=data_summary,
    )
    response = llm_callback(prompt)
    return parse_chart_config(response, column_names)

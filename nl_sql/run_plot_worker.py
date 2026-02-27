"""
Worker script for running LLM-generated plot code in a sandbox.

Reads JSON from stdin: {"code": str, "data": list of dict}.
Outputs to stdout: base64-encoded PNG bytes, or on error a line starting with "ERROR:".
Run with: python -m nl_sql.run_plot_worker
"""

from __future__ import annotations

import io
import json
import base64
import sys

# Allowed for plot generation only
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


def strip_code_fences(code: str) -> str:
    """Remove markdown code fences if present."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first line (```python or ```)
        lines = lines[1:]
        # Remove trailing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    return code


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print("ERROR: Invalid JSON input: " + str(e), file=sys.stderr)
        sys.exit(1)

    code = payload.get("code") or ""
    data = payload.get("data")
    if data is None:
        print("ERROR: Missing 'data' in input", file=sys.stderr)
        sys.exit(1)

    code = strip_code_fences(code)
    if not code.strip():
        print("ERROR: Empty code after stripping fences", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.DataFrame(data)
    except Exception as e:
        print("ERROR: Failed to build DataFrame: " + str(e), file=sys.stderr)
        sys.exit(1)

    # Restricted namespace: only these names are available (matplotlib + seaborn per nl_plot_data_3)
    namespace = {
        "df": df,
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "io": io,
        "base64": base64,
    }

    try:
        exec(code, namespace)
    except Exception as e:
        print("ERROR: Code execution failed: " + str(e), file=sys.stderr)
        sys.exit(1)

    plot_png_bytes = namespace.get("plot_png_bytes")
    if plot_png_bytes is None:
        # Fallback: save current pyplot figure to buffer
        try:
            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
            buf.seek(0)
            plot_png_bytes = buf.getvalue()
        except Exception as e:
            print("ERROR: No plot_png_bytes and fallback failed: " + str(e), file=sys.stderr)
            sys.exit(1)

    if not isinstance(plot_png_bytes, bytes):
        print("ERROR: plot_png_bytes is not bytes", file=sys.stderr)
        sys.exit(1)

    # Output base64 to stdout so parent can capture it
    print(base64.b64encode(plot_png_bytes).decode("ascii"))


if __name__ == "__main__":
    main()

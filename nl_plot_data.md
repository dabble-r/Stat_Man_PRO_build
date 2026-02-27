# NL-plot data flow: confirmation that NL-plot uses NL SQL execution data

## Summary

**Confirmed:** The NL-plot path populates the plot from the **same** NL SQL execution data as manual visualization. Both paths use the dialog’s in-memory `query_results_df`; no separate query or data fetch is performed for NL-plot. The backend only returns chart **configuration** (chart type, columns, options); the **data** for the figure always comes from the already-executed query results in the dialog.

---

## Where the data comes from

- **Single source of truth:** `self.query_results_df` on the NL Query Dialog ([nl_query_dialog.py](src/ui/dialogs/nl_query_dialog.py)).
- **When it is set:** After the user runs a query (e.g. Execute SQL or NL → SQL then Execute), `_on_execution_complete` (or the path that handles execution) builds a DataFrame from the result rows and assigns it to `self.query_results_df` (see e.g. `pd.DataFrame(results)`, then `_display_dataframe(self.query_results_df)`).
- **When it is cleared:** When servers are stopped, execution is run without results, or the dialog clears state; then `query_results_df` is set to `None`.

So the data shown in the results table and the data used for **both** manual and NL-plot charts are the same: the last executed query’s result set stored in `query_results_df`.

---

## Manual visualization path

1. User has already run a query → `query_results_df` is populated.
2. User clicks **Visualize** (no plot description).
3. `_handle_visualize` runs:
   - Guard: `if self.query_results_df is None or self.query_results_df.empty` → warn and return.
   - `opts_dialog = VizOptionsDialog(self.query_results_df, parent=self)` — dialog is given the **same** DataFrame (by reference).
   - User picks options in the dialog; `get_options()` returns an options dict.
   - `fig = build_figure(self.query_results_df.copy(), options)` — figure is built from a **copy** of `query_results_df`.
4. **Data used for the plot:** `query_results_df` (the NL SQL execution result).

---

## NL-plot path

1. User has already run a query → `query_results_df` is populated (same as above).
2. User enters a plot description and clicks **Submit**.
3. `_handle_nl_plot_submit` runs:
   - Guard: `if self.query_results_df is None or self.query_results_df.empty` → warn and return.
   - From **current** `query_results_df` it derives:
     - `columns = list(self.query_results_df.columns)`
     - `dtypes` from `self.query_results_df.dtypes`
     - `data_summary = compute_data_summary(self.query_results_df)`
   - It sends to the backend **only** metadata: `description`, `columns`, `dtypes`, `data_summary`. **No row data** is sent.
4. Backend `POST /nl_to_chart_config` ([api_call.py](nl_sql/api_call.py)) receives `ChartConfigRequest`: `description`, `columns`, `dtypes`, `data_summary`. It returns a chart **options** dict (e.g. `chart_type`, `x_col`, `y_col`, `y_cols`, `title`, …). The backend does **not** receive or return result rows.
5. When the request succeeds, `_on_chart_config_finished` runs:
   - Parses the returned options JSON.
   - Opens `VizOptionsDialog(self.query_results_df.copy(), parent=self)` and pre-fills it with `set_initial_options(options)` — again the dialog gets a **copy** of the **same** `query_results_df`.
   - User may adjust and click Plot; `final_options = {**options, **opts_dialog.get_options()}`.
   - `fig = build_figure(self.query_results_df.copy(), final_options)` — figure is built from a **copy** of `query_results_df`.
6. **Data used for the plot:** `query_results_df` (the same NL SQL execution result as manual path).

---

## build_figure and data

- **Renderer:** [viz_plot_builder.py](src/visualization/viz_plot_builder.py) `build_figure(df, options)`.
- **Manual path:** `build_figure(self.query_results_df.copy(), options)`.
- **NL-plot path:** `build_figure(self.query_results_df.copy(), final_options)`.

In both cases the first argument is a copy of the **same** `query_results_df`. The only difference is how the **options** dict is produced (user in dialog vs. backend from description + column metadata). The **data** for the plot is always the in-memory NL SQL execution result.

---

## Conclusion

- NL-plot **does** populate the plot from the same NL SQL execution data as manual visualization.
- That data is `query_results_df` in the dialog, set when the user executes a query (e.g. Execute SQL).
- NL-plot sends only **schema/metadata** (columns, dtypes, data summary) and a **description** to the backend; the backend returns **chart options** only. No result rows are sent or received by the backend.
- Both manual and NL-plot paths call `build_figure(self.query_results_df.copy(), ...)` with the same DataFrame source, so the chart is always drawn from the current query results table data.

---

## Why “plot data from one row” (e.g. one player) shows the same data for all

**Observed:** A query like “bar chart of player: nick, stats: hits, so, bb” produces a chart that looks the same regardless of the player name (e.g. always all players or same structure, not filtered to nick).

**Root cause (workflow/logic):**

1. **Chart config has no row filter**  
   The options returned by the backend and consumed by `build_figure()` only describe **which columns** to use: `chart_type`, `x_col`, `y_col`, `y_cols`, `series_col`, `group_by`, `agg`, labels, palette. There is no key such as `filter_col` / `filter_value` (or `row_filter`) to mean “only include rows where column \(C\) equals value \(V\)”.

2. **Backend cannot express “one row” or “one player”**  
   The backend receives only metadata (column names, dtypes, data summary) and the natural-language description. It can infer “use columns hit, so, bb” and “use name for labels,” but the response schema does not allow it to return “restrict to rows where name == 'nick'.” So even if the LLM interprets “player: nick” correctly, it has no way to output that as chart options.

3. **Renderer never filters the DataFrame**  
   In [viz_plot_builder.py](src/visualization/viz_plot_builder.py), `build_figure(df, options)` starts with `plot_df = df` (or an aggregated view of `df`). It never applies a row filter based on options. So the same full `query_results_df` is always plotted; no “only this row” or “only this player” step exists.

4. **Data sent to the backend has no row identity**  
   The client sends `columns`, `dtypes`, and `data_summary` (e.g. nunique, min/max, sample values). It does **not** send per-row data or a list of distinct values (e.g. player names). So the LLM cannot know “nick” is a valid value for a specific column and cannot return a filter that the client or renderer would apply.

**Summary:** The pipeline is “choose columns and chart type,” not “choose columns and **which rows**.” Because the chart config has no row-filter semantics and the renderer never filters by column value, a request like “player: nick, stats: hits, so, bb” still plots the full result set; the player name in the description does not restrict rows. To support “plot data from one row” or “only player nick,” the workflow would need: (a) optional filter keys in the chart config (e.g. `filter_col`, `filter_value` or a list of filters), (b) the client/renderer applying that filter to `query_results_df` before calling `build_figure`, and (c) the prompt/schema telling the LLM to output those keys when the description mentions a specific entity (e.g. a player name).

---

## Strategy: NL SQL execution–data aware and NL-plot query aware

**Goal:** Make NL-plot accurate for user queries such as “bar chart of player: nick, stats: hits, so, bb” or “line chart for teams A and B, stats wins and losses” by making the system **execution-data aware** (know what rows/values are in the current result) and **query aware** (map “player: nick” / “teams A, B” into chart config that restricts rows and picks the right columns).

### 1. Execution-data awareness (what’s in the result)

- **Current:** The client sends `columns`, `dtypes`, and `data_summary` (nunique, min/max, and a small `sample_values` per column). The backend never sees the full list of distinct values (e.g. all player names or team names) in the current result.
- **Strategy:**
  - **Client:** From `query_results_df`, compute **distinct values** for selected columns (e.g. all string/categorical columns, or columns the app treats as “entities”: `name`, `team`, `manager`, etc.). Cap list length (e.g. 200) and send as `distinct_values: { "name": ["nick", "joe", ...], "team": ["A", "B"], ... }` in the chart-config request. Optionally send **row_count** so the LLM knows “one row” vs “many.”
  - **Backend:** Extend `ChartConfigRequest` with optional `distinct_values: Dict[str, List[str]]` and optional `row_count: int`. Include in the prompt: “Current result set has N rows. Valid values for filtering (use only these): …” so the LLM can output filter values that exist in the data.
  - **MCP (optional):** If you prefer the server to derive distinct values from the DB instead of the client, add an endpoint (e.g. POST `/distinct` with `sql` + `column`) that runs a query and returns distinct values for that column. The NL-plot backend would then need the “last executed SQL” from the client to run such a query. **Simpler and more accurate:** have the client compute distinct values from `query_results_df` so the plot is guaranteed to match the **exactly** executed result (no extra DB round-trip, no schema drift).

### 2. Chart config: row filters and multi-entity

- **Current:** Options only describe columns and chart type; no way to say “only these rows.”
- **Strategy:**
  - **Schema extension:** Add optional keys to the chart config JSON:
    - **Single filter:** `filter_col` (string), `filter_value` (string) → “include only rows where `filter_col == filter_value`.”
    - **Multi-value filter:** `filter_col` (string), `filter_values` (array of strings) → “include only rows where `filter_col` is in `filter_values`” (e.g. “teams A and B”).
    - **Multi-column filter (optional):** `filters` (array of `{ "col": "name", "value": "nick" }`) for “player nick and stat X” style queries.
  - **Prompt:** Tell the LLM to output these keys when the user mentions specific entities (e.g. “player nick”, “for team A”, “players nick and joe”). Rules: use only values from the provided `distinct_values`; if the user names one entity, use `filter_col` + `filter_value`; if several, use `filter_col` + `filter_values`.
  - **Parse/validate:** In `parse_chart_config`, accept and validate `filter_col` (must be in valid_columns), `filter_value` / `filter_values` (optional: check against allowed list if provided). Pass them through in the options dict.

### 3. Client: apply filter before plotting

- **Before** calling `build_figure(query_results_df.copy(), final_options)`:
  - If `final_options` has `filter_col` and `filter_value`: `df = df[df[filter_col].astype(str).str.strip() == str(filter_value).strip()]`.
  - If `final_options` has `filter_col` and `filter_values`: `df = df[df[filter_col].astype(str).str.strip().isin([str(v).strip() for v in filter_values])]`.
  - If `filters` (list of {col, value}) is present: apply each as an equality filter in turn.
  - If the filtered `df` is empty, show a short message (“No rows match filter”) and optionally still open the adjust dialog with the full data so the user can change the filter.
- **Data passed to build_figure:** Always pass the (possibly filtered) DataFrame and the same `final_options`; the renderer does not need to know about filters if the client does the filtering.

### 4. Any chart type, any combination of stats, any combination of teams/players

- **Any chart type:** Already supported (bar, line, scatter, histogram, box, pie) and extensible via `CHART_TYPES` and prompt. Keep documenting allowed types and using fallback (e.g. pie → bar) when a type is unsupported.
- **Any combination of stats:** Already supported via `y_cols` (e.g. hit, so, bb). Ensure the prompt and examples show multi-metric requests and that the LLM returns `y_cols` with the correct column names from the request.
- **Any combination of teams or players:** Add the **row-filter** mechanism above: send `distinct_values` for entity columns (name, team, etc.), extend schema with `filter_col` / `filter_value` / `filter_values`, and have the client filter `query_results_df` before `build_figure`. Then “player: nick”, “teams A and B”, “only these players: …” can be mapped to a filter that restricts to the requested rows.

### 5. End-to-end flow (with strategy applied)

1. User runs NL SQL → Execute → `query_results_df` populated.
2. User enters plot description (e.g. “bar chart of player nick, stats hits so bb”) and clicks Submit.
3. **Client** computes `columns`, `dtypes`, `data_summary` (existing) and **distinct_values** for entity columns (e.g. name, team) from `query_results_df`; optionally `row_count`. Sends all to backend.
4. **Backend** builds prompt with columns, dtypes, data summary, **distinct values**, and rules for when to output `filter_col` / `filter_value` / `filter_values`. LLM returns chart config including optional filter keys.
5. **Parse** validates and passes through filter keys in options.
6. **Client** receives options; if filter keys present, filters `query_results_df` to the subset; then opens “Visualization Options (Adjust)” with the (possibly filtered) data and options; on Apply, merges options and calls `build_figure(filtered_df.copy(), final_options)`.
7. **Renderer** is unchanged: it still gets a DataFrame and options; the DataFrame is already restricted to the requested rows when the user asked for a specific player or set of teams/players.

This keeps the NL-plot pipeline **execution-data aware** (distinct values and row count from the current result), **query aware** (natural language “player: nick” / “teams A, B” → filter in config), and accurate for any chart type, any combination of stats, and any combination of teams or players within the current result set.



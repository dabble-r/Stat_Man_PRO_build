# League.db path consistency

## Canonical database (NL search and Execute SQL)

The app uses a **single canonical League database** for:

- Natural language search and formatted-query execution (NL-to-SQL dialog)
- Add team, Load CSV, and other league data flows
- Clear on startup / on close and schema initialization

**Path:** `data/database/League.db` relative to the application base (project root in development; directory of the executable when frozen). In code this is always resolved via `get_database_path()`.

So when you run a formatted query or search in the NL dialog, results come from this **same** League.db.

---

## Save to a custom folder (SaveDialog)

If you **save** league data to a **custom folder** (e.g. via SaveDialog or “Save to folder X”), the app writes to:

**Path:** `{folder}/DB/League.db`

That file is **not** the same as the canonical database above. So:

- **NL results will not reflect that save** until you load from that location (e.g. Load CSV from that folder, if the app supports it).
- The canonical `data/database/League.db` is what the NL-to-SQL dialog and Execute SQL use; saving to a different folder does not change that.

If you want NL search and Execute SQL to see the data you just saved, use the main app data location (the canonical path) when saving, or load that saved data into the app so it lives in the canonical League.db.

# Tasks 3 and 4

This folder contains the Text2SQL implementation.

## Task 3: Text2SQL API

The API converts a natural language question into SQL, runs it against the PostgreSQL database, and returns the result.

Main files:

- `main.py` - FastAPI entry point.
- `sql_generator.py` - Generates SQL, fixes failed SQL, and creates a short summary.
- `executor.py` - Executes SQL queries.
- `validator.py` - Blocks unsafe SQL commands.
- `db.py` - Database connection setup.

Run the API:

```bash
cd task3and4
.venv/bin/python -m uvicorn main:app --reload
```

## Task 4: Streamlit UI

The Streamlit UI provides a simple text box for asking database questions and shows the generated SQL, result table, and summary.

Run the UI:

```bash
cd task3and4
.venv/bin/python -m streamlit run streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

## Requirements

Make sure the root PostgreSQL container is running:

```bash
docker compose up -d
```

The `.env` file should include `DATABASE_URL` and `GEMINI_API_KEY`.

import csv
import os
from datetime import datetime
from pathlib import Path

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

PROJECT = Path(os.getenv("ASSISTANT_PROJECT_DIR", Path(__file__).resolve().parents[1]))
UV = os.getenv("UV_BIN", "uv")
VERSION = os.getenv("PRODUCTION_VERSION", "v1")
MIN_COMPLETION = 0.7
MIN_REGRESSION_PASS = 0.8


@dag(schedule="@daily", start_date=datetime(2026, 9, 1), catchup=False, tags=["assistant"])
def nightly_eval():
    run_eval = BashOperator(task_id="run_eval", bash_command=f"cd {PROJECT} && {UV} run python experiment.py {VERSION}")

    @task
    def check():
        with open(PROJECT / "reports" / "run_comparison.csv") as f:
            row = next(r for r in csv.DictReader(f) if r["mlflow.runName"] == f"prompt_{VERSION}")
        row = {k: float(v) for k, v in row.items() if k in ("task_completion", "pct_tests_passed")}
        print(f"task_completion={row['task_completion']:.2f} pct_tests_passed={row['pct_tests_passed']:.2f}")
        problems = []
        if row["task_completion"] < MIN_COMPLETION:
            problems.append(f"task completion {row['task_completion']:.2f} < {MIN_COMPLETION}")
        if row["pct_tests_passed"] < MIN_REGRESSION_PASS:
            problems.append(f"regression pass rate {row['pct_tests_passed']:.2f} < {MIN_REGRESSION_PASS}")
        if problems:
            raise RuntimeError("degradation: " + "; ".join(problems))

    run_eval >> check()


nightly_eval()

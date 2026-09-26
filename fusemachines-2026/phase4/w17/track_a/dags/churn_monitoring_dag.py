import json
import os
from datetime import datetime
from pathlib import Path

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

PROJECT = Path(os.getenv("CHURN_PROJECT_DIR", Path(__file__).resolve().parents[1]))
UV = os.getenv("UV_BIN", "uv")


@dag(schedule="@weekly", start_date=datetime(2026, 9, 1), catchup=False, tags=["churn"])
def churn_monitoring():
    drift_check = BashOperator(task_id="drift_check", bash_command=f"cd {PROJECT} && {UV} run python drift.py")
    retrain = BashOperator(task_id="retrain", bash_command=f"cd {PROJECT} && {UV} run python train.py")
    register = BashOperator(task_id="register", bash_command=f"cd {PROJECT} && {UV} run python register.py")

    @task.branch
    def decide():
        summary = json.loads((PROJECT / "reports" / "drift_summary.json").read_text())
        print("reasons:", summary["reasons"])
        return "retrain" if summary["retrain_recommended"] else "no_drift"

    @task
    def no_drift():
        print("no significant drift, keeping the production model")

    drift_check >> decide() >> [retrain, no_drift()]
    retrain >> register


churn_monitoring()

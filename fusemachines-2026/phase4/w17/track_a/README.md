# W17 Track A - churn model MLOps

Dataset: Telco Customer Churn (IBM sample), 7043 rows, in `data/telco_churn.csv`. Target is `Churn`, about 26.5% Yes.

Flow: data -> train.py -> MLflow runs -> register.py (registry) -> mlflow models serve -> drift.py (Evidently) -> retrain if needed (Airflow DAG)

## Run

```
uv sync
uv run python train.py
uv run python register.py
MLFLOW_TRACKING_URI=sqlite:///mlflow.db uv run mlflow models serve -m "models:/churn-model@champion" -p 5001 --env-manager local
curl -X POST localhost:5001/invocations -H 'content-type: application/json' -d @sample_request.json
uv run python drift.py
uv run python drift.py --no-drift
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

mlflow.db and mlartifacts/ are not in the repo because the artifacts are around 280 MB. Running the steps above creates them again. Results I exported are in `reports/`.

## a. Environment (uv)

pyproject.toml and uv.lock, python pinned to 3.12 in .python-version. My system python is 3.14 so uv downloads 3.12 for the project. The lock is useful here because Evidently 0.7 has a completely different API from 0.4 which most examples online use, and MLflow 3 changed log_model and how sklearn models get saved, so an unpinned install would break the scripts. From a clean clone `uv sync` is the only setup step (I deleted .venv and ran it again to check).

## b. Experiment tracking (MLflow)

Each run logs the hyperparameters, accuracy, precision, recall, f1, roc auc, 5 fold cv roc auc, train f1 (to see overfitting), fit time, and the model, confusion matrix and roc curve as artifacts. 80/20 stratified split, threshold 0.5.

I tried different model families and changed the complexity settings:

| run | accuracy | precision | recall | f1 | roc auc | cv roc auc | train f1 |
|---|---|---|---|---|---|---|---|
| logreg_C1_l2 | 0.738 | 0.504 | 0.783 | 0.614 | 0.842 | 0.845 | 0.633 |
| logreg_C0.05_l1 | 0.743 | 0.510 | 0.789 | 0.620 | 0.839 | 0.844 | 0.628 |
| rf_300_depth8 | 0.752 | 0.521 | 0.791 | 0.629 | 0.843 | 0.848 | 0.682 |
| rf_500_unbounded | 0.784 | 0.619 | 0.487 | 0.545 | 0.821 | 0.823 | 0.996 |
| gbm_200_depth3 | 0.805 | 0.669 | 0.524 | 0.588 | 0.844 | 0.847 | 0.640 |

(reports/run_comparison.csv, same as the compare view in the MLflow UI)

I registered rf_300_depth8. It has the best f1 (0.629), recall (0.791) and cv roc auc (0.848). gbm_200_depth3 has the best accuracy (0.805) and test roc auc (0.844) but recall is only 0.524, so it misses about half the people who churn. Since 73.5% of rows are "No", accuracy mostly rewards predicting No. The gbm roc auc is only 0.0015 higher which is less than the cv noise. rf_500_unbounded overfits (train f1 0.996, test 0.545). register.py picks the best f1 among runs with roc auc within 0.01 of the best.

Trade off: precision is 0.52 so about half the customers flagged would not have left. For churn that is cheaper than missing them.

Registry (reports/registry.json): new version goes to Staging (alias staging), then Production (alias champion) and the old version is archived. Stages are deprecated in MLflow 3 so I set both stages and aliases, serving uses @champion. When retraining, the new version only goes to Production if its f1 is not lower than the current one.

## c. Monitoring (Evidently)

- reference: random 70% of the data (4930 rows), used as the training time data
- current: the other 30% with drift added. MonthlyCharges + random 5 to 25 per row, month-to-month contracts oversampled from 55% to 80% of rows, 8% of labels flipped

Reports in reports/ and also logged to MLflow in the drift_check run:
- data_drift_report.html - DataDriftPreset on all 19 features
- target_drift_report.html - drift of Churn and of the model predictions (z test, p < 0.05)
- custom_metrics_report.html - two custom metrics made with the Evidently metric classes in drift.py: mean difference of MonthlyCharges (test <= 5) and change in churn rate for month-to-month customers (test <= 0.05)
- the same files with _baseline are from a split with no drift added

Results (reports/drift_summary.json): 4 of 19 features drifted. MonthlyCharges and Contract are the two I changed. tenure and TotalCharges also drifted, I didn't touch them but month-to-month customers are newer so oversampling them lowers both. So the drift I added was found. Churn rate went from 27.0% to 35.2% and target drift was flagged. Predicted churners went from 40.9% to 55.1%. Mean MonthlyCharges difference is +14.47 so that custom test fails. Month-to-month churn rate only changed by -2.4 points, so the higher churn overall comes from having more month-to-month customers, not from them churning more. On the baseline split nothing drifted and all tests passed.

The default method for the target (Jensen-Shannon distance, threshold 0.1) did not flag the 8 point jump in churn rate so I used a z test for the two binary columns.

What it would mean in production: the model never saw prices this high and it would flag over half the customers, so the retention team gets too many cases and precision goes down. drift.py recommends retraining if more than 25% of features drift, churn rate drifts, mean MonthlyCharges moves more than 5, or month-to-month churn rate moves more than 5 points. Two of these fired here. Retraining should really be done on new labeled data, not the same csv.

## d. Orchestration (Airflow bonus)

dags/churn_monitoring_dag.py, runs weekly:

```
drift_check -> decide -> retrain -> register   (if retrain_recommended)
                      -> no_drift              (otherwise)
```

decide reads reports/drift_summary.json. Tasks run `uv run ...` inside the project so Airflow doesn't need the project packages. Tested with Airflow 3.3 in a separate venv using `airflow dags test churn_monitoring`, it went to retrain and registered version 2 (reports/airflow_dag_test.log).

```
export AIRFLOW__CORE__DAGS_FOLDER=$PWD/dags
airflow dags test churn_monitoring
```

## Files

- common.py - paths, columns, loading data, mlflow setup
- train.py, register.py, drift.py
- dags/churn_monitoring_dag.py
- sample_request.json - example input for the served model
- reports/ - comparison table, plots, registry info, Evidently reports

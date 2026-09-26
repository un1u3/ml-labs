import json

import mlflow
from mlflow import MlflowClient

from common import EXPERIMENT, MODEL_NAME, REPORTS, setup_mlflow

setup_mlflow()
client = MlflowClient()

# best f1 from latest batch (roc auc within 0.01 of best)
runs = mlflow.search_runs(experiment_names=[EXPERIMENT], filter_string="tags.type = 'training'")
runs = runs[runs["tags.batch"] == runs["tags.batch"].max()]
runs = runs[runs["metrics.roc_auc"] >= runs["metrics.roc_auc"].max() - 0.01]
best = runs.sort_values("metrics.f1", ascending=False).iloc[0]
name = best["tags.mlflow.runName"]
print(f"best run: {name} f1={best['metrics.f1']:.4f} roc_auc={best['metrics.roc_auc']:.4f}")

try:
    champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
    champion_f1 = client.get_run(champion.run_id).data.metrics["f1"]
except mlflow.exceptions.MlflowException:
    champion_f1 = 0

mv = mlflow.register_model(f"runs:/{best['run_id']}/model", MODEL_NAME)
client.update_model_version(MODEL_NAME, mv.version, f"{name}: F1={best['metrics.f1']:.4f}, ROC-AUC={best['metrics.roc_auc']:.4f}")

client.transition_model_version_stage(MODEL_NAME, mv.version, "Staging")
client.set_registered_model_alias(MODEL_NAME, "staging", mv.version)
print(f"version {mv.version} -> Staging")

if best["metrics.f1"] >= champion_f1 - 0.005:
    client.transition_model_version_stage(MODEL_NAME, mv.version, "Production", archive_existing_versions=True)
    client.set_registered_model_alias(MODEL_NAME, "champion", mv.version)
    client.delete_registered_model_alias(MODEL_NAME, "staging")
    print(f"version {mv.version} -> Production")
else:
    print(f"version {mv.version} stays in Staging, production F1 is {champion_f1:.4f}")

info = client.get_model_version(MODEL_NAME, mv.version)
REPORTS.mkdir(exist_ok=True)
(REPORTS / "registry.json").write_text(json.dumps(
    {"model": MODEL_NAME, "version": mv.version, "run": name, "run_id": best["run_id"],
     "stage": info.current_stage, "aliases": info.aliases, "description": info.description}, indent=2))

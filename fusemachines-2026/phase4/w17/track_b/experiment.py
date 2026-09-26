# uv run python experiment.py v1 v2 ...
import json
import sys

import mlflow
import pandas as pd

import agent
import config
import eval as harness
import regression


def pick_traces(results):
    ok = [r for r in results if r["passed"]]
    bad = [r for r in results if not r["passed"]]
    picks = ([min(ok, key=lambda r: r["iterations"])] if ok else []) + bad[:1]
    picks.append(max(results, key=lambda r: r["iterations"]))
    return {r["case"]: r for r in picks}


def run_version(version):
    cfg = agent.configure(**config.VERSIONS[version])
    out = config.REPORTS / version
    out.mkdir(parents=True, exist_ok=True)
    with mlflow.start_run(run_name=f"prompt_{version}"):
        mlflow.log_params(cfg)
        mlflow.log_artifact(str(agent.PROMPTS / f"prompt_{version}.txt"), "prompt")

        results = harness.evaluate()
        summary = harness.summarize(results)
        (out / "results.md").write_text(harness.report(results, f"Evaluation results ({version})"))
        (out / "traces.json").write_text(json.dumps(results, indent=2, default=str))
        for name, r in pick_traces(results).items():
            mlflow.log_dict(r, f"traces/representative/{name.replace(' ', '_').replace(':', '')}.json")
        mlflow.log_artifact(str(out / "traces.json"), "traces")
        mlflow.log_artifact(str(out / "results.md"), "harness")

        reg, scored, reg_traces = regression.run(out / "regression_report.html")
        scored.to_csv(out / "regression_results.csv", index=False)
        (out / "regression_traces.json").write_text(json.dumps(reg_traces, indent=2, default=str))
        for p in ["regression_report.html", "regression_results.csv", "regression_traces.json"]:
            mlflow.log_artifact(str(out / p), "regression")

        reg_cost = sum(config.cost(t["input_tokens"], t["output_tokens"], cfg["model"]) for t in reg_traces)
        metrics = {**summary, **{k: v for k, v in reg.items() if k != "promotable"},
                   "regression_cost_usd": reg_cost, "promotable": int(reg["promotable"])}
        mlflow.log_metrics(metrics)
        mlflow.set_tag("promotable", reg["promotable"])
    print(version, json.dumps(metrics, indent=1))
    return {"version": version, **{k: round(v, 4) for k, v in metrics.items()}}


def main():
    mlflow.set_tracking_uri(config.TRACKING_URI)
    if mlflow.get_experiment_by_name(config.EXPERIMENT) is None:
        mlflow.create_experiment(config.EXPERIMENT, artifact_location=config.ARTIFACT_ROOT)
    mlflow.set_experiment(config.EXPERIMENT)
    versions = sys.argv[1:] or list(config.VERSIONS)
    rows = [run_version(v) for v in versions]

    runs = mlflow.search_runs(experiment_names=[config.EXPERIMENT], filter_string="attributes.status = 'FINISHED'")
    runs = runs.sort_values("start_time").drop_duplicates("tags.mlflow.runName", keep="last")
    cols = ["tags.mlflow.runName"] + [c for c in runs.columns if c.startswith("metrics.")]
    table = runs[cols].rename(columns=lambda c: c.split(".", 1)[1]).sort_values("mlflow.runName")
    table.to_csv(config.REPORTS / "run_comparison.csv", index=False)
    print(table.round(4).to_string(index=False))
    return rows


if __name__ == "__main__":
    main()

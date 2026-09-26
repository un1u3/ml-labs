import json
import sys

import mlflow
import numpy as np
import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.core.metric_types import SingleValueCalculation, SingleValueMetric
from evidently.metrics import ValueDrift
from evidently.presets import DataDriftPreset
from evidently.tests import lte

from common import CATEGORICAL, FEATURES, MODEL_NAME, NUMERIC, REPORTS, SEED, TARGET, load_data, setup_mlflow


# custom metric: current mean - reference mean
class MeanDifference(SingleValueMetric):
    column: str


class MeanDifferenceCalculation(SingleValueCalculation[MeanDifference]):
    def calculate(self, context, current_data, reference_data):
        col = self.metric.column
        return self.result(float(current_data.column(col).data.mean() - reference_data.column(col).data.mean()))

    def display_name(self):
        return f"Mean difference of {self.metric.column}"


# custom metric: churn rate change in one contract type
class SegmentChurnShift(SingleValueMetric):
    contract: str


class SegmentChurnShiftCalculation(SingleValueCalculation[SegmentChurnShift]):
    def rate(self, data):
        df = data.as_dataframe()
        return float((df[df["Contract"] == self.metric.contract][TARGET] == "Yes").mean())

    def calculate(self, context, current_data, reference_data):
        return self.result(self.rate(current_data) - self.rate(reference_data))

    def display_name(self):
        return f"Churn rate shift for {self.metric.contract}"


def make_split(df, inject=True):
    reference = df.sample(frac=0.7, random_state=SEED)
    current = df.drop(reference.index).copy()
    if inject:
        rng = np.random.default_rng(SEED)
        current["MonthlyCharges"] += rng.uniform(5, 25, len(current))
        # month-to-month up to 80%
        m2m = current[current["Contract"] == "Month-to-month"]
        other = current[current["Contract"] != "Month-to-month"]
        n_other = int(len(current) * 0.2)
        current = pd.concat([m2m.sample(len(current) - n_other, replace=True, random_state=SEED),
                             other.sample(n_other, random_state=SEED)])
        flip = rng.random(len(current)) < 0.08
        current.loc[flip, TARGET] = np.where(current.loc[flip, TARGET] == "Yes", "No", "Yes")
    return reference.reset_index(drop=True), current.reset_index(drop=True)


def drifted(snapshot):
    failed = {t["metric_config"]["metric_id"] for t in snapshot["tests"] if t["status"] == "FAIL"}
    return sorted(m["config"]["column"] for m in snapshot["metrics"]
                  if m["config"]["type"].endswith("ValueDrift") and m["id"] in failed)


def main():
    inject = "--no-drift" not in sys.argv
    suffix = "" if inject else "_baseline"
    setup_mlflow()
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
    reference, current = make_split(load_data(), inject)
    for df in (reference, current):
        df["prediction"] = np.where(model.predict(df[FEATURES]) == 1, "Yes", "No")

    definition = DataDefinition(numerical_columns=NUMERIC, categorical_columns=CATEGORICAL + [TARGET, "prediction"])
    ref = Dataset.from_pandas(reference, data_definition=definition)
    cur = Dataset.from_pandas(current, data_definition=definition)

    reports = {
        "data_drift": Report([DataDriftPreset(columns=FEATURES)], include_tests=True),
        # z test, default one didnt catch the churn change
        "target_drift": Report([ValueDrift(column=TARGET, method="z", threshold=0.05),
                                ValueDrift(column="prediction", method="z", threshold=0.05)], include_tests=True),
        "custom_metrics": Report([MeanDifference(column="MonthlyCharges", tests=[lte(5)]),
                                  SegmentChurnShift(contract="Month-to-month", tests=[lte(0.05)])], include_tests=True),
    }
    snaps = {}
    for name, report in reports.items():
        snap = report.run(cur, ref)
        snap.save_html(str(REPORTS / f"{name}_report{suffix}.html"))
        snaps[name] = snap.dict()

    drifted_features = drifted(snaps["data_drift"])
    target_drift = drifted(snaps["target_drift"])
    mean_diff, seg_shift = [float(m["value"]) for m in snaps["custom_metrics"]["metrics"]]

    reasons = []
    if len(drifted_features) / len(FEATURES) > 0.25:
        reasons.append(f"{len(drifted_features)} of {len(FEATURES)} features drifted")
    if TARGET in target_drift:
        reasons.append("churn rate drifted")
    if abs(mean_diff) > 5:
        reasons.append(f"mean MonthlyCharges changed by {mean_diff:+.2f}")
    if abs(seg_shift) > 0.05:
        reasons.append(f"month-to-month churn rate changed by {seg_shift:+.3f}")

    summary = {
        "drift_injected": inject,
        "drifted_features": drifted_features,
        "drifted_share": round(len(drifted_features) / len(FEATURES), 3),
        "target_and_prediction_drift": target_drift,
        "churn_rate_reference": round((reference[TARGET] == "Yes").mean(), 4),
        "churn_rate_current": round((current[TARGET] == "Yes").mean(), 4),
        "predicted_churn_rate_reference": round((reference["prediction"] == "Yes").mean(), 4),
        "predicted_churn_rate_current": round((current["prediction"] == "Yes").mean(), 4),
        "mean_monthly_charges_diff": round(mean_diff, 3),
        "m2m_churn_rate_shift": round(seg_shift, 4),
        "retrain_recommended": bool(reasons),
        "reasons": reasons,
    }
    (REPORTS / f"drift_summary{suffix}.json").write_text(json.dumps(summary, indent=2))

    with mlflow.start_run(run_name=f"drift_check{suffix}"):
        mlflow.set_tag("type", "monitoring")
        mlflow.log_param("drift_injected", inject)
        mlflow.log_metrics({k: v for k, v in summary.items() if isinstance(v, float)} |
                           {"retrain_recommended": int(bool(reasons))})
        for name in reports:
            mlflow.log_artifact(REPORTS / f"{name}_report{suffix}.html", "evidently")
        mlflow.log_dict(summary, "evidently/drift_summary.json")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

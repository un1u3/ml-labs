import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import pandas as pd
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, RocCurveDisplay, accuracy_score, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from common import CATEGORICAL, FEATURES, NUMERIC, REPORTS, SEED, load_data, setup_mlflow

MODELS = [
    ("logreg_C1_l2", LogisticRegression, {"C": 1.0, "l1_ratio": 0.0, "class_weight": "balanced", "max_iter": 2000}),
    ("logreg_C0.05_l1", LogisticRegression, {"C": 0.05, "l1_ratio": 1.0, "solver": "saga", "class_weight": "balanced", "max_iter": 5000}),
    ("rf_300_depth8", RandomForestClassifier, {"n_estimators": 300, "max_depth": 8, "min_samples_leaf": 5, "class_weight": "balanced"}),
    ("rf_500_unbounded", RandomForestClassifier, {"n_estimators": 500, "max_depth": None, "min_samples_leaf": 1}),
    ("gbm_200_depth3", GradientBoostingClassifier, {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05}),
]


def build(cls, params):
    pre = ColumnTransformer([("num", StandardScaler(), NUMERIC),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])
    return Pipeline([("pre", pre), ("clf", cls(random_state=SEED, **params))])


def save_plots(model, X, y, name):
    paths = []
    for kind, Display in [("confusion_matrix", ConfusionMatrixDisplay), ("roc_curve", RocCurveDisplay)]:
        Display.from_estimator(model, X, y)
        plt.title(name)
        path = REPORTS / "plots" / f"{name}_{kind}.png"
        plt.savefig(path, bbox_inches="tight")
        plt.close()
        paths.append(path)
    return paths


def main():
    setup_mlflow()
    (REPORTS / "plots").mkdir(parents=True, exist_ok=True)
    df = load_data()
    X, y = df[FEATURES], (df["Churn"] == "Yes").astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    batch = time.strftime("%Y%m%d-%H%M%S")

    rows = []
    for name, cls, params in MODELS:
        with mlflow.start_run(run_name=name) as run:
            model = build(cls, params)
            start = time.time()
            model.fit(X_train, y_train)
            fit_time = time.time() - start
            proba = model.predict_proba(X_test)[:, 1]
            pred = (proba >= 0.5).astype(int)
            metrics = {
                "accuracy": accuracy_score(y_test, pred),
                "precision": precision_score(y_test, pred),
                "recall": recall_score(y_test, pred),
                "f1": f1_score(y_test, pred),
                "roc_auc": roc_auc_score(y_test, proba),
                "cv_roc_auc": cross_val_score(build(cls, params), X_train, y_train, cv=5, scoring="roc_auc").mean(),
                "train_f1": f1_score(y_train, model.predict(X_train)),
                "fit_seconds": fit_time,
            }
            mlflow.log_params({"model_family": cls.__name__, **params})
            mlflow.log_metrics(metrics)
            mlflow.set_tags({"batch": batch, "type": "training"})
            for p in save_plots(model, X_test, y_test, name):
                mlflow.log_artifact(p, "plots")
            mlflow.sklearn.log_model(model, name="model", input_example=X_test.head(3),
                                     signature=infer_signature(X_test, pred),
                                     skops_trusted_types=["sklearn.tree._tree.Tree"])
            rows.append({"run": name, "run_id": run.info.run_id, **{k: round(v, 4) for k, v in metrics.items()}})
            print(name, f"f1={metrics['f1']:.3f} roc_auc={metrics['roc_auc']:.3f} acc={metrics['accuracy']:.3f}")

    pd.DataFrame(rows).to_csv(REPORTS / "run_comparison.csv", index=False)


if __name__ == "__main__":
    main()

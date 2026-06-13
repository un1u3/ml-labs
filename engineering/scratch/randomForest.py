import numpy as np
from decisionTree import DecisionTree

class RandomForest:
    def __init__(self, n_estimators=100, max_depth=5, max_features="sqrt"):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.max_features = max_features

        self.trees = []
        self.feature_indices = []
        self.oob_predictions = None

    def fit(self, X, y):
        n, p = X.shape

        # Number of features per tree
        if self.max_features == "sqrt":
            m = int(np.sqrt(p))
        elif self.max_features == "log2":
            m = int(np.log2(p))
        else:
            m = p // 3

        # OOB storage: [prediction_sum, prediction_count]
        self.oob_predictions = np.zeros((n, 2))

        for _ in range(self.n_estimators):
            self._train_single_tree(X, y, m)

        return self

    def _train_single_tree(self, X, y, m):
        n, p = X.shape

        # Bootstrap sampling
        idx = np.random.choice(n, n, replace=True)

        # Out-of-bag samples
        oob_idx = np.setdiff1d(np.arange(n), idx)

        # Random feature subset
        feat_idx = np.random.choice(p, m, replace=False)

        # Train tree
        tree = DecisionTree(max_depth=self.max_depth)
        tree.fit(X[np.ix_(idx, feat_idx)], y[idx])

        self.trees.append(tree)
        self.feature_indices.append(feat_idx)

        # OOB predictions
        if len(oob_idx) > 0:
            preds = tree.predict(X[np.ix_(oob_idx, feat_idx)])

            self.oob_predictions[oob_idx, 0] += preds
            self.oob_predictions[oob_idx, 1] += 1

    def predict(self, X):
        all_preds = np.array([
            tree.predict(X[:, feat_idx])
            for tree, feat_idx in zip(self.trees, self.feature_indices)
        ])

        # Majority vote (binary classification: 0/1)
        return np.round(np.mean(all_preds, axis=0)).astype(int)

    def oob_score(self, y):
        mask = self.oob_predictions[:, 1] > 0

        if np.sum(mask) == 0:
            return 0.0

        preds = np.round(
            self.oob_predictions[mask, 0] /
            self.oob_predictions[mask, 1]
        ).astype(int)

        return np.mean(preds == y[mask])
    


import numpy as np

# Reproducibility
np.random.seed(42)

# Number of samples
n = 200

# Features
X = np.random.randn(n, 4)

# Non-linear decision boundary
y = (
    (X[:, 0] + X[:, 1] > 0).astype(int) ^
    (X[:, 2] > 0).astype(int)
)

# Split into train/test
split = int(0.8 * n)

X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]


rf = RandomForest(n_estimators=20, max_depth=5, max_features="sqrt")
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)

print("Predictions:", y_pred)
print("Actual:", y_test)
print("Accuracy:", np.mean(y_pred == y_test))
print("OOB Score:", rf.oob_score(y_train))



from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

rf = RandomForest(n_estimators=50, max_depth=5)
rf.fit(X_train, y_train)
print(f"Test Accuracy: {np.mean(rf.predict(X_test) == y_test):.4f}")
print(f"OOB Score: {rf.oob_score(y_train):.4f}")
import numpy as np 

class Node:
    def __init__(self, feature=None, threshold=None, left=None, right=None, value=None):
        self.feature = feature
        self.threshold = threshold
        self.left = left 
        self.right = right
        self.value = value

    def is_leaf(self):
        return self.value is not None 

class DecisionTree:
    def __init__(self, max_depth=5, min_samples_split=2, criterion='gini'):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.criterion = criterion
        self.root = None
        
    def _gini(self, y):
        _, counts = np.unique(y, return_counts=True)
        p = counts / len(y)
        return 1 - np.sum(p**2)
        
    def _entropy(self, y):
        _, count = np.unique(y, return_counts=True)
        p = count / len(y)
        # Use base 2 for standard information entropy calculation
        return -np.sum(p * np.log2(p + 1e-9))
    
    def _impurity(self, y):
        return self._gini(y) if self.criterion == 'gini' else self._entropy(y)

    def _best_split(self, X, y):
        best_gain = -np.inf 
        best_feat = None
        best_thresh = None
        parent_imp = self._impurity(y)
        n = len(y)

        for feat in range(X.shape[1]):
            for thresh in np.unique(X[:, feat]):
                # Use local variables instead of self instance state
                left_y = y[X[:, feat] <= thresh]
                right_y = y[X[:, feat] > thresh]
                
                if len(left_y) == 0 or len(right_y) == 0:
                    continue
                    
                gain = parent_imp - (len(left_y)/n * self._impurity(left_y) + len(right_y)/n * self._impurity(right_y))
                if gain > best_gain:
                    best_gain, best_feat, best_thresh = gain, feat, thresh
        return best_feat, best_thresh
    
    def _build(self, X, y, depth):
        if depth >= self.max_depth or len(y) < self.min_samples_split or len(np.unique(y)) == 1:
            return Node(value=np.bincount(y).argmax())
            
        feat, thresh = self._best_split(X, y)
        if feat is None:
            return Node(value=np.bincount(y).argmax())
            
        mask = X[:, feat] <= thresh
        left = self._build(X[mask], y[mask], depth + 1)
        right = self._build(X[~mask], y[~mask], depth + 1)
        return Node(feature=feat, threshold=thresh, left=left, right=right)

    def fit(self, X, y):
        self.root = self._build(X, y, 0)
        return self
    
    def _predict_one(self, x, node):
        if node.is_leaf():
            return node.value
        if x[node.feature] <= node.threshold:
            return self._predict_one(x, node.left)
        return self._predict_one(x, node.right)

    def predict(self, X):
        return np.array([self._predict_one(x, self.root) for x in X])





from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification



from sklearn.datasets import make_classification

X, y = make_classification(
    n_samples=1000, 
    n_features=20, 
    n_informative=10,
    n_redundant=5,
    random_state=42
)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

for depth in [1, 3, 5, 10, 20]:
    model = DecisionTree(max_depth=depth)
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"max_depth={depth}: {acc:.4f}")


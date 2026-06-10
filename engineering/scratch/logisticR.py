import numpy as np 
class LogisticRegressionScratch:
    def __init__(self, lr=0.1, epochs=500):
        self.lr = lr 
        self.num_iters = epochs
        self.weights = None 
        self.bias = None 



    
    def _sigmoid(self, z):
        return 1 / (1 + np.exp(-z))
    
    def fit(self, X, y):

        # initialization
        num_samples, num_features = X.shape
        self.weights = np.zeros(num_features)
        self.bias = 0.0

        # gradient descent 
        for _ in range(self.num_iters):
            y_pred = X @ self.weights + self.bias
            y_pred_ = self._sigmoid(y_pred)

            # compute gradeints and update 
            dw = (1 / num_samples) * np.dot(X.T, (y_pred_ - y))
            db = (1 / num_samples) * np.sum(y_pred_ - y)

            # update parms 
            self.weights -= self.lr* dw 
            self.bias -= self.lr * db

    def predict_proba(self, X):
        y_pred = X @ self.weights + self.bias 
        return self._sigmoid(y_pred)
    
    
    def predict(self, X, threshold=0.5):
        prob = self.predict_proba(X)
        return np.where(prob >= threshold, 1, 0 )
    



from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

X, y = make_classification(n_samples=500, n_features=5, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LogisticRegressionScratch(lr=0.1, epochs=1000)
model.fit(X_train, y_train)
preds = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, preds):.4f}")
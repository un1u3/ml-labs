import numpy as np
class Ridge:
    def __init__(self, lam=0 ) -> None:
        # if lam is 0 there is no penalty term so its identical to OLS
        self.bias = 0
        self.lam = lam

    def fit(self, X, y):
        X_ = np.c_[np.ones(len(X)), X]
        self.XT = np.transpose(X_)
        I = np.eye(X_.shape[1])
        I[0, 0] = 0 
        self.beta = np.linalg.inv((np.transpose(X_) @ X_) + self.lam * I) @ np.transpose(X_) @ y 

    def predict(self, X):
        X_ = np.c_[np.ones(len(X)), X] 
        return X_ @ self.beta 



    # Simple test — y = 2x + 1
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([3, 5, 7, 9, 11])

model = Ridge()
model.fit(X, y)
print(model.beta)        # should be [1, 2] — intercept=1, slope=2
print(model.predict(X))  # should be [3, 5, 7, 9, 11]
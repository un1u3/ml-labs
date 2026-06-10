import numpy as np
class LassoScratch:
    def __init__(self, lam=2.0, max_iter=1000, tol=1e-4) -> None:
        # if lam is 0 there is no penalty term so its identical to OLS
        self.bias = 0
        self.lam = lam
        self.max_iter = max_iter

    def fit(self, X, y):
        n, p = X.shape  
        self.beta = np.zeros(p)
        
        for _ in range(self.max_iter):            
            for j in range(p):
                r_j = y - X @ self.beta + X[:, j] * self.beta[j]
                rho = X[:, j] @ r_j / n
                if rho > self.lam:
                    self.beta[j] = rho - self.lam
                elif rho < -self.lam:
                    self.beta[j] = rho + self.lam
                else:
                    self.beta[j] = 0.0
    def predict(self, X):
        return X @ self.beta
    

X = np.array([[1], [2], [3], [4], [5]], dtype=float)
X = (X - X.mean()) / X.std()  # normalize
y = np.array([3, 5, 7, 9, 11], dtype=float)

model = LassoScratch(lam=10.0)  # smaller lambda
model.fit(X, y)
print(model.beta)
print(model.predict(X))
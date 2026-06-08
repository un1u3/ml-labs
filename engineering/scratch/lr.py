import numpy as np
class LinearRegression:
    def __init__(self) -> None:
        self.bias = 0
        
        
        

    def fit(self, X, y):
        X_ = np.c_[np.ones(len(X)), X]
        self.XT = np.transpose(X_)
        self.beta = np.linalg.inv(self.XT@X_) @ self.XT @ y 

    def predict(self, X):
         X_ = np.c_[np.ones(len(X)), X] 
         return X_ @ self.beta 



# Simple test — y = 2x + 1
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([3, 5, 7, 9, 11])

model = LinearRegression()
model.fit(X, y)
print(model.beta)        # should be [1, 2] — intercept=1, slope=2
print(model.predict(X))  # should be [3, 5, 7, 9, 11]
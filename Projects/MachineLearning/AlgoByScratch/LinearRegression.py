import numpy as np 
class SimpleLinearRegression:

    def __init__(self,learning_rate,n_iterations):
        self.learning_rate = learning_rate
        self.n_iterations = n_iterations
        self.weights = None 
        self.bias = None 

    def fit(self,X,y):
        m, n_features = X.shape
        self.weights = np.zeros(n_features)
        self.bias = 0 

        for _ in range(self.n_iterations):
            y_pred = X @ self.weights + self.bias 
            dW = (-2/m) * (X.T @ (y - y_pred))
            dB = (-2/m) * np.sum(y- y_pred)

            # updateThe parameter 

            self.weights -= self.learning_rate * dW
            self.bias -= self.learning_rate * dB

    def predict(self,X):
        return X @ self.weights + self.bias


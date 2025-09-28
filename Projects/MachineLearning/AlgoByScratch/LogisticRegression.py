import numpy as np 


class LogisticRegressionGD:

    def __init__(self,learning_rate,n_iterations):
        self.learning_rate = learning_rate
        self.n_iterations = n_iterations
        self.weights = None 
        self.bias = None 

    def _signmod(self,z):
        return 1 / (1 + np.exp(-z))

    def fit(self,X,y):
        m, n_features = X.shape
        self.weights = np.zeros(n_features)
        self.bias = 0 

        for _ in range(self.n_iterations):
            linear_models = X @ self.weights + self.bias 
            y_pred = self._signmod(linear_models)

            dW = (1/m) * (X.T @ (y_pred - y))
            dB = (1/m) * np.sum(y_pred - y)

            # update parameters 
            self.weights -= self.learning_rate * dW 
            self.bias -= self.learning_rate * dB 
    
    def predict_prob(self,X):
        linear_model = X @ self.weights + self.bias 
        return self._signmod(linear_model)

    def predict(self,X, threshold = 0.5):
        return (self.predict_proba(X) >= threshold).astype(int)



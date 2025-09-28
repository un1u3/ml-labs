import numpy as np 
from collections import Counter 

class SimplekNN:

    def __init__(self,k):
        self.k = k 
        self.X_train = None
        self.y_train = None 

    def fit(self,X,y):
        self.X.train = X 
        self.y_train = y 

    def _euclidean_distance(self,x1,x2):
        return np.sqrt(np.sum(x1- x2)**2)

    def predict(self,X):
        predictions = []
        for x in x:
            d  # Compute distances to all training samples
            distances = [self._euclidean_distance(x, x_train) for x_train in self.X_train]

            # Find the indices of the k nearest neighbors
            k_indices = np.argsort(distances)[:self.k]

            # Extract their labels
            k_neighbor_labels = [self.y_train[i] for i in k_indices]

            # Majority vote
            most_common = Counter(k_neighbor_labels).most_common(1)[0][0]
            predictions.append(most_common)

        return np.array(predictions)

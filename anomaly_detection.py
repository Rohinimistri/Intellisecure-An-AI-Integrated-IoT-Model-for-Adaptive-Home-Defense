from sklearn.ensemble import IsolationForest
import numpy as np

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.02)

    def train(self, data):
        self.model.fit(data)

    def predict(self, data):
        return self.model.predict(data)

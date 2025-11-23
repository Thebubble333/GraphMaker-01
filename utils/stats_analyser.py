import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class BoxPlotData:
    label: str
    min_val: float
    q1: float
    median: float
    q3: float
    max_val: float
    outliers: List[float]


@dataclass
class RegressionData:
    slope: float
    intercept: float
    r_squared: float
    predictions: List[float]
    residuals: List[float]


class StatsAnalyser:
    def __init__(self):
        pass

    def get_boxplot_stats(self, data: List[float], label: str = "") -> BoxPlotData:
        if not data:
            return BoxPlotData(label, 0, 0, 0, 0, 0, [])

        arr = np.array(data)
        q1 = np.percentile(arr, 25)
        median = np.percentile(arr, 50)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1

        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr

        # Identify outliers
        outliers = arr[(arr < lower_fence) | (arr > upper_fence)].tolist()

        # Whiskers end at the most extreme data points within fences
        non_outliers = arr[(arr >= lower_fence) & (arr <= upper_fence)]
        min_val = np.min(non_outliers) if len(non_outliers) > 0 else q1
        max_val = np.max(non_outliers) if len(non_outliers) > 0 else q3

        return BoxPlotData(label, min_val, q1, median, q3, max_val, outliers)

    def calculate_regression(self, x: List[float], y: List[float]) -> RegressionData:
        if len(x) != len(y) or len(x) < 2:
            return None

        x_arr = np.array(x)
        y_arr = np.array(y)

        # Linear regression (y = mx + c)
        slope, intercept = np.polyfit(x_arr, y_arr, 1)

        # R-squared
        correlation_matrix = np.corrcoef(x_arr, y_arr)
        correlation_xy = correlation_matrix[0, 1]
        r_squared = correlation_xy ** 2

        # Predictions and Residuals
        predictions = slope * x_arr + intercept
        residuals = y_arr - predictions

        return RegressionData(slope, intercept, r_squared, predictions.tolist(), residuals.tolist())
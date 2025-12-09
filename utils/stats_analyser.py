import numpy as np
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

# --- Data Classes ---
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

@dataclass
class VisualStatNode:
    value: float
    index: float
    type: str 

@dataclass
class VisualQuartileData:
    sorted_data: List[float]
    q1: VisualStatNode
    median: VisualStatNode
    q3: VisualStatNode

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

        outliers = arr[(arr < lower_fence) | (arr > upper_fence)].tolist()
        non_outliers = arr[(arr >= lower_fence) & (arr <= upper_fence)]
        min_val = np.min(non_outliers) if len(non_outliers) > 0 else q1
        max_val = np.max(non_outliers) if len(non_outliers) > 0 else q3

        return BoxPlotData(label, min_val, q1, median, q3, max_val, outliers)

    def calculate_regression(self, x: List[float], y: List[float]) -> Optional[RegressionData]:
        if len(x) != len(y) or len(x) < 2:
            return None

        x_arr = np.array(x)
        y_arr = np.array(y)
        slope, intercept = np.polyfit(x_arr, y_arr, 1)
        
        correlation_matrix = np.corrcoef(x_arr, y_arr)
        correlation_xy = correlation_matrix[0, 1]
        r_squared = correlation_xy ** 2

        predictions = slope * x_arr + intercept
        residuals = y_arr - predictions

        return RegressionData(slope, intercept, r_squared, predictions.tolist(), residuals.tolist())

    def get_visual_quartiles(self, data: List[float]) -> VisualQuartileData:
        sorted_data = sorted(data)
        n = len(sorted_data)

        def get_stat_info(sub_data_len):
            mid_idx = (sub_data_len - 1) / 2
            if sub_data_len % 2 == 1:
                return mid_idx, "exact"
            else:
                return mid_idx, "split"

        med_idx, med_type = get_stat_info(n)
        if med_type == "exact":
            median_val = sorted_data[int(med_idx)]
        else:
            median_val = (sorted_data[int(math.floor(med_idx))] + sorted_data[int(math.ceil(med_idx))]) / 2
        median_node = VisualStatNode(median_val, med_idx, med_type)

        if n % 2 == 1:
            lower_half_len = int(med_idx)
            upper_start_idx = int(med_idx) + 1
        else:
            lower_half_len = int(n / 2)
            upper_start_idx = int(n / 2)

        q1_local_idx, q1_type = get_stat_info(lower_half_len)
        q1_global_idx = q1_local_idx
        if q1_type == "exact":
            q1_val = sorted_data[int(q1_global_idx)]
        else:
            q1_val = (sorted_data[int(math.floor(q1_global_idx))] + sorted_data[int(math.ceil(q1_global_idx))]) / 2
        q1_node = VisualStatNode(q1_val, q1_global_idx, q1_type)

        q3_local_idx, q3_type = get_stat_info(lower_half_len)
        q3_global_idx = upper_start_idx + q3_local_idx
        if q3_type == "exact":
            q3_val = sorted_data[int(q3_global_idx)]
        else:
            q3_val = (sorted_data[int(math.floor(q3_global_idx))] + sorted_data[int(math.ceil(q3_global_idx))]) / 2
        q3_node = VisualStatNode(q3_val, q3_global_idx, q3_type)

        return VisualQuartileData(sorted_data, q1_node, median_node, q3_node)

    def get_stem_leaf_data(self, data: List[float], stem_value=10, split_stems=False):
        """
        Organizes data into a dictionary {stem_key: [sorted_leaves]}.
        """
        if not data:
            return {}, 0, 0

        sorted_data = sorted(data)
        stem_dict = {}
        
        # 1. Populate Dict with Actual Data
        for val in sorted_data:
            val = round(val, 2)
            stem = int(val // stem_value)
            
            # Calculate Leaf
            remainder = val % stem_value
            leaf_unit = stem_value / 10
            leaf = int(remainder // leaf_unit)
            
            # Determine Key
            if split_stems:
                key = float(stem)
                if remainder >= (stem_value / 2):
                    key += 0.5
            else:
                key = int(stem) 
                
            if key in stem_dict:
                stem_dict[key].append(leaf)
            else:
                stem_dict[key] = [leaf]

        # 2. Fill in Empty Stems (The Gaps)
        if not stem_dict:
            return {}, 0, 0

        min_key = min(stem_dict.keys())
        max_key = max(stem_dict.keys())
        
        step = 0.5 if split_stems else 1.0
        current = min_key
        
        while current <= max_key + 0.01:
            if split_stems:
                normalized_key = round(current, 1)
            else:
                normalized_key = int(round(current))
            
            if normalized_key not in stem_dict:
                stem_dict[normalized_key] = []
            
            current += step

        # 3. Final Sanity Check
        final_dict = {}
        for k, v in stem_dict.items():
            final_key = k
            if not split_stems:
                final_key = int(k)
            final_dict[final_key] = sorted(v) # Ensure sorted leaves

        return final_dict, min(final_dict.keys()), max(final_dict.keys())

    # --- NEW HELPER FOR HIGHLIGHTING ---
    def get_stem_leaf_position(self, val: float, stem_value=10, split_stems=False) -> Tuple[float, int]:
        """
        Given a specific value, returns (stem_key, leaf_value) to help find its position.
        """
        val = round(val, 2)
        stem = int(val // stem_value)
        remainder = val % stem_value
        leaf_unit = stem_value / 10
        leaf = int(remainder // leaf_unit)
        
        if split_stems:
            key = float(stem)
            if remainder >= (stem_value / 2):
                key += 0.5
            key = round(key, 1)
        else:
            key = int(stem)
            
        return key, leaf
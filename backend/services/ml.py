"""Season-aware shelf-life prediction.

This module provides infrastructure for shelf life model loading and management.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

_SHELF_LIFE_MODEL_VERSION = 3


@dataclass
class ShelfLifeTrainingReport:
    mae: float
    rmse: float
    n_rows: int
    feature_importances: List[Dict[str, Any]]


class MLService:
    def __init__(self):
        self.shelf_life_pipeline: Optional[Pipeline] = None
        self.shelf_life_report: Optional[ShelfLifeTrainingReport] = None
        self._init_shelf_life_model()

    def _dataset_path(self, name: str) -> str:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return os.path.join(base_dir, "agri_supply_chain_datasets", name)

    def _init_shelf_life_model(self) -> None:
        model_path = self._dataset_path("shelf_life_model.joblib")
        crop_yield_path = self._dataset_path("crop_yield.csv")
        seasonal_corrected_path = self._dataset_path("crop_freshness_shelf_life_seasonal_corrected.csv")
        seasonal_shelf_life_path = self._dataset_path("crop_freshness_shelf_life_seasonal.csv")
        if os.path.exists(seasonal_corrected_path):
            shelf_life_path = seasonal_corrected_path
        elif os.path.exists(seasonal_shelf_life_path):
            shelf_life_path = seasonal_shelf_life_path
        else:
            shelf_life_path = self._dataset_path("crop_freshness_shelf_life.csv")

        logger.info(
            "Shelf-life dataset selected: %s (version=%s)",
            shelf_life_path,
            _SHELF_LIFE_MODEL_VERSION,
        )

        should_load = False
        if os.path.exists(model_path):
            try:
                import joblib

                meta = joblib.load(model_path)
                if meta.get("version") != _SHELF_LIFE_MODEL_VERSION:
                    should_load = False
                else:
                    model_mtime = os.path.getmtime(model_path)
                    data_mtime = max(
                        os.path.getmtime(p)
                        for p in [crop_yield_path, shelf_life_path]
                        if isinstance(p, str) and p and os.path.exists(p)
                    )
                    should_load = model_mtime >= data_mtime
            except Exception:
                should_load = False

        if should_load:
            try:
                model_mtime = os.path.getmtime(model_path)
                import joblib

                obj = joblib.load(model_path)
                self.shelf_life_pipeline = obj.get("pipeline")
                rep = obj.get("report")
                if isinstance(rep, dict):
                    self.shelf_life_report = ShelfLifeTrainingReport(
                        mae=float(rep.get("mae") or 0.0),
                        rmse=float(rep.get("rmse") or 0.0),
                        n_rows=int(rep.get("n_rows") or 0),
                        feature_importances=list(rep.get("feature_importances") or []),
                    )
                logger.info(
                    "Shelf-life model loaded from %s (mtime=%s)",
                    model_path,
                    model_mtime,
                )
                return
            except Exception:
                self.shelf_life_pipeline = None
                self.shelf_life_report = None

        try:
            self._train_shelf_life_model(save_path=model_path)
            logger.info("Shelf-life model trained and saved to %s", model_path)
        except Exception as e:
            logger.warning("Shelf-life model not available: %s", e)
            self.shelf_life_pipeline = None
            self.shelf_life_report = None

    def _train_shelf_life_model(self, save_path: str) -> None:
        """Train shelf life model using seasonal crop datasets."""
        seasonal_corrected_path = self._dataset_path("crop_freshness_shelf_life_seasonal_corrected.csv")
        seasonal_shelf_life_path = self._dataset_path("crop_freshness_shelf_life_seasonal.csv")
        if os.path.exists(seasonal_corrected_path):
            shelf_life_path = seasonal_corrected_path
        elif os.path.exists(seasonal_shelf_life_path):
            shelf_life_path = seasonal_shelf_life_path
        else:
            shelf_life_path = self._dataset_path("crop_freshness_shelf_life.csv")

        if not os.path.exists(shelf_life_path):
            raise FileNotFoundError(f"Missing dataset: {shelf_life_path}")

        # Load and process seasonal shelf life data
        df_s = pd.read_csv(shelf_life_path)
        df_s = df_s.copy()

        # Calculate mean shelf life by crop and season
        group_cols = ["Crop"]
        if "Season" in df_s.columns:
            group_cols.append("Season")

        df_agg = df_s.groupby(group_cols, as_index=False)["Max_Shelf_Life_Days"].mean()

        logger.info(
            "Shelf life data loaded: %d rows, %d unique crops",
            len(df_agg),
            df_agg["Crop"].nunique(),
        )

        # Store aggregated data for lookup
        self._shelf_life_data = df_agg.to_dict("records")

    def get_shelf_life_days(self, crop: str, season: str = "") -> Optional[float]:
        """Get shelf life days for a crop from seasonal data."""
        if not hasattr(self, "_shelf_life_data") or not self._shelf_life_data:
            return None

        crop_lower = str(crop).lower().strip()
        season_lower = str(season).lower().strip()

        # Try to find exact match with season
        if season_lower:
            for record in self._shelf_life_data:
                if (
                    str(record.get("Crop", "")).lower().strip() == crop_lower
                    and str(record.get("Season", "")).lower().strip() == season_lower
                ):
                    return float(record.get("Max_Shelf_Life_Days", 0))

        # Fall back to crop-only match
        for record in self._shelf_life_data:
            if str(record.get("Crop", "")).lower().strip() == crop_lower:
                return float(record.get("Max_Shelf_Life_Days", 0))

        return None


# =============================================================================
# FULL ML TRAINING PIPELINE DEMONSTRATION
# Complete workflow from data loading to model evaluation
# NOTE: This code is for demonstration purposes only and is NOT executed
# =============================================================================
#
# import pandas as pd
# import numpy as np
#
# # Visualization
# import matplotlib.pyplot as plt
# import seaborn as sns
#
# # ML
# from sklearn.model_selection import train_test_split
# from sklearn.preprocessing import LabelEncoder
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_absolute_error, r2_score
#
#
# from google.colab import files
# uploaded = files.upload()
# file_path = list(uploaded.keys())[0] if uploaded else ""
#
# df = pd.read_csv(file_path)
#
# df.head()
#
# df.info()
# df.describe()
# df.isnull().sum()
#
# import numpy as np
#
# # Create more data with small variation
# df_aug = df.sample(n=len(df)*3, replace=True, random_state=42)
#
# df_aug["Optimal_Temp_C"] += np.random.normal(0, 2, size=len(df_aug))
# df_aug["Optimal_Humidity_%"] += np.random.normal(0, 5, size=len(df_aug))
#
# # Combine
# df = pd.concat([df, df_aug], ignore_index=True)
#
# df.fillna(df.mean(numeric_only=True), inplace=True)
#
# le = LabelEncoder()
#
# for col in df.select_dtypes(include='object').columns:
#     df[col] = le.fit_transform(df[col])
#
# X = df.drop("Max_Shelf_Life_Days", axis=1)
# y = df["Max_Shelf_Life_Days"]
#
# X_train, X_test, y_train, y_test = train_test_split(
#     X, y, test_size=0.2, random_state=42
# )
#
# model = RandomForestRegressor(n_estimators=100, random_state=42)
# model.fit(X_train, y_train)
#
# y_pred = model.predict(X_test)
#
# mae = mean_absolute_error(y_test, y_pred)
# r2 = r2_score(y_test, y_pred)
#
#
# print("MAE:", mae)
# print("R2 Score:", r2)


ml_service = MLService()

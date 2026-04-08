from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


_FIXED_WAREHOUSES = {
    "Delhi Warehouse",
    "Chandigarh Warehouse",
    "Bengaluru Warehouse",
    "Hyderabad Warehouse",
    "Kolkata Warehouse",
    "Bhubaneswar Warehouse",
    "Mumbai Warehouse",
    "Ahmedabad Warehouse",
    "Nagpur Central Warehouse",
}


@dataclass(frozen=True)
class CropKnowledge:
    storage_type: str
    max_shelf_life_days: float
    optimal_temp_c: float
    optimal_humidity_pct: float


class WarehouseTwin:
    def __init__(self, datasets_dir: Path):
        self._datasets_dir = datasets_dir
        self._crop_knowledge: Dict[Tuple[str, str], CropKnowledge] = {}
        self._climate_daily_avg: Dict[Tuple[str, date], Tuple[float, float]] = {}
        self._dates_by_warehouse: Dict[str, Tuple[date, date]] = {}
        self._loaded = False

    def _normalize_crop_key(self, crop: str) -> str:
        c = (crop or "").strip().lower()
        if not c:
            return ""
        mapping = {
            "apples": "apple",
            "onions": "onion",
            "tomatoes": "tomato",
            "mangoes": "mango",
            "potatoes": "potato",
            "chilies": "chilli",
            "chillies": "chilli",
        }
        if c in mapping:
            return mapping[c]

        # Since _crop_knowledge is keyed by (crop, storage_type), we check membership by crop.
        crops_present = {k[0] for k in self._crop_knowledge.keys()} if self._crop_knowledge else set()
        if c in crops_present:
            return c
        if c.endswith("es") and c[:-2] in crops_present:
            return c[:-2]
        if c.endswith("s") and c[:-1] in crops_present:
            return c[:-1]
        return c

    def _normalize_storage_key(self, storage_type: str) -> str:
        s = (storage_type or "").strip().lower()
        if not s:
            return ""
        s = " ".join(s.split())
        return s

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._load_crop_knowledge()
        self._load_climate_timeseries_daily_avg()
        self._loaded = True

    def _load_crop_knowledge(self) -> None:
        path = self._datasets_dir / "crop_freshness_shelf_life1.csv"
        if not path.exists():
            path = self._datasets_dir / "crop_freshness_shelf_life.csv"
        if not path.exists():
            candidates = sorted(self._datasets_dir.glob("crop_freshness_shelf_life*.csv"))
            path = candidates[0] if candidates else path
        if not path.exists():
            self._crop_knowledge = {}
            return

        out: Dict[Tuple[str, str], CropKnowledge] = {}
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                crop = (row.get("Crop") or "").strip()
                if not crop:
                    continue
                try:
                    storage_type = (row.get("Storage_Type") or "").strip()
                    max_days = float(row.get("Max_Shelf_Life_Days") or 0)
                    opt_t = float(row.get("Optimal_Temp_C") or 0)
                    opt_h = float(row.get("Optimal_Humidity_%") or row.get("Optimal_Humidity_%") or 0)
                except Exception:
                    continue
                key = (crop.lower(), self._normalize_storage_key(storage_type))
                prev = out.get(key)
                prev_days = float(prev.max_shelf_life_days) if prev else -1.0
                if float(max_days or 0.0) > float(prev_days):
                    out[key] = CropKnowledge(
                        storage_type=storage_type,
                        max_shelf_life_days=max_days if max_days > 0 else 1.0,
                        optimal_temp_c=opt_t,
                        optimal_humidity_pct=opt_h,
                    )

        seasonal_path = self._datasets_dir / "crop_freshness_shelf_life_seasonal_corrected.csv"
        if seasonal_path.exists():
            try:
                with seasonal_path.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        crop = (row.get("Crop") or "").strip()
                        if not crop:
                            continue
                        try:
                            max_days = float(row.get("Max_Shelf_Life_Days") or 0)
                            opt_t = float(row.get("Optimal_Temp_C") or 0)
                            opt_h = float(row.get("Optimal_Humidity_%") or row.get("Optimal_Humidity_%") or 0)
                        except Exception:
                            continue
                        # Keep the same key shape as the primary dataset: (crop, storage_type).
                        # Seasonal dataset may not include storage type; store it under empty storage.
                        key = (crop.lower(), "")
                        prev = out.get(key)
                        prev_days = float(prev.max_shelf_life_days) if prev else -1.0
                        if prev is None and float(max_days or 0.0) > 0.0:
                            out[key] = CropKnowledge(
                                storage_type="",
                                max_shelf_life_days=max_days,
                                optimal_temp_c=opt_t,
                                optimal_humidity_pct=opt_h,
                            )
                        elif prev is not None and float(max_days or 0.0) > float(prev_days):
                            out[key] = CropKnowledge(
                                storage_type=str(prev.storage_type or ""),
                                max_shelf_life_days=max_days,
                                optimal_temp_c=opt_t,
                                optimal_humidity_pct=opt_h,
                            )
            except Exception:
                pass
        self._crop_knowledge = out

    def _load_climate_timeseries_daily_avg(self) -> None:
        path = self._datasets_dir / "warehouse_climate_timeseries.csv"
        if not path.exists():
            candidates = sorted(self._datasets_dir.glob("warehouse_climate_timeseries*.csv"))
            path = candidates[0] if candidates else path
        if not path.exists():
            self._climate_daily_avg = {}
            self._dates_by_warehouse = {}
            return

        sums: Dict[Tuple[str, date], Tuple[float, float, int]] = {}
        minmax: Dict[str, Tuple[date, date]] = {}

        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wh = (row.get("warehouse_name") or "").strip()
                if wh not in _FIXED_WAREHOUSES:
                    continue
                ts_raw = (row.get("timestamp") or "").strip()
                try:
                    ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M")
                except Exception:
                    continue
                d = ts.date()
                try:
                    t = float(row.get("temperature_c") or 0)
                    h = float(row.get("humidity_pct") or 0)
                except Exception:
                    continue

                k = (wh, d)
                if k in sums:
                    st, sh, c = sums[k]
                    sums[k] = (st + t, sh + h, c + 1)
                else:
                    sums[k] = (t, h, 1)

                if wh in minmax:
                    mn, mx = minmax[wh]
                    mn2 = mn if mn <= d else d
                    mx2 = mx if mx >= d else d
                    minmax[wh] = (mn2, mx2)
                else:
                    minmax[wh] = (d, d)

        daily: Dict[Tuple[str, date], Tuple[float, float]] = {}
        for (wh, d), (st, sh, c) in sums.items():
            if c <= 0:
                continue
            daily[(wh, d)] = (st / c, sh / c)

        self._climate_daily_avg = daily
        self._dates_by_warehouse = minmax

    def get_crop_knowledge(self, crop: str, storage_type: Optional[str] = None) -> Optional[CropKnowledge]:
        self.ensure_loaded()
        key = self._normalize_crop_key(crop)
        if not key:
            return None
        sk = self._normalize_storage_key(storage_type or "")
        if sk:
            ck = self._crop_knowledge.get((key, sk))
            if ck is not None:
                return ck

        # Fallback: if no storage type was specified (or no exact match exists),
        # choose the record with the maximum shelf life for that crop.
        best = None
        for (crop_k, _st), ck in self._crop_knowledge.items():
            if crop_k != key:
                continue
            if best is None or float(ck.max_shelf_life_days or 0.0) > float(best.max_shelf_life_days or 0.0):
                best = ck
        return best

    def climate_for(self, warehouse_name: str, on_date: date) -> Optional[Tuple[date, float, float]]:
        self.ensure_loaded()
        wh = (warehouse_name or "").strip()
        if wh not in _FIXED_WAREHOUSES:
            return None

        if (wh, on_date) in self._climate_daily_avg:
            t, h = self._climate_daily_avg[(wh, on_date)]
            return (on_date, t, h)

        mm = self._dates_by_warehouse.get(wh)
        if not mm:
            return None
        mn, mx = mm
        candidate = on_date
        if candidate < mn:
            candidate = mn
        if candidate > mx:
            candidate = mx
        if (wh, candidate) in self._climate_daily_avg:
            t, h = self._climate_daily_avg[(wh, candidate)]
            return (candidate, t, h)
        return None

    def compatibility_status(
        self,
        *,
        crop: str,
        actual_temp_c: Optional[float],
        actual_humidity_pct: Optional[float],
        temp_tight: float = 2.0,
        hum_tight: float = 5.0,
        temp_loose: float = 5.0,
    ) -> str:
        """Classify storage compatibility from dataset-derived conditions.

        Compatible: within tight bounds of crop optimal temp/humidity
        Sub-Optimal: within loose bounds
        Incompatible: outside loose bounds or missing environment data
        """
        self.ensure_loaded()
        ck = self.get_crop_knowledge(crop)
        if not ck:
            return "Incompatible"
        if actual_temp_c is None or actual_humidity_pct is None:
            return "Incompatible"

        dt = abs(float(actual_temp_c) - float(ck.optimal_temp_c))
        dh = abs(float(actual_humidity_pct) - float(ck.optimal_humidity_pct))

        if dt <= temp_tight and dh <= hum_tight:
            return "Compatible"
        if dt <= temp_loose:
            return "Sub-Optimal"
        return "Incompatible"

    def simulate_one_day(
        self,
        crop: str,
        warehouse_name: str,
        sim_date: date,
        freshness: float,
        *,
        alpha: float = 0.002,
        beta: float = 0.001,
    ) -> Tuple[float, Optional[float], Optional[float], Optional[str]]:
        self.ensure_loaded()

        ck = self.get_crop_knowledge(crop)
        climate = self.climate_for(warehouse_name, sim_date)
        if not ck:
            return (max(0.0, min(1.0, freshness)), None, None, None)
        if not climate:
            base_decay = 1.0 / float(ck.max_shelf_life_days or 1.0)
            return (max(0.0, min(1.0, freshness - base_decay)), None, None, ck.storage_type)

        _, actual_t, actual_h = climate
        base_decay = 1.0 / float(ck.max_shelf_life_days or 1.0)
        temp_penalty = abs(actual_t - ck.optimal_temp_c) * alpha
        humidity_penalty = abs(actual_h - ck.optimal_humidity_pct) * beta
        daily_decay = base_decay + temp_penalty + humidity_penalty
        new_f = freshness - daily_decay
        new_f = max(0.0, min(1.0, new_f))
        return (new_f, actual_t, actual_h, ck.storage_type)


_twin_singleton: Optional[WarehouseTwin] = None


def get_warehouse_twin() -> WarehouseTwin:
    global _twin_singleton
    if _twin_singleton is None:
        datasets_dir = Path(__file__).resolve().parents[2] / "agri_supply_chain_datasets"
        _twin_singleton = WarehouseTwin(datasets_dir)
    return _twin_singleton

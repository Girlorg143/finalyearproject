from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt
from ..extensions import db
from ..models import CropBatch, DisasterEvent, Shipment, StorageLog, WarehouseStatus, SalvageBatch, ROLE_WAREHOUSE
from ..utils import roles_required
from ..services.genai import generate_warehouse_recommendation, generate_warehouse_alert_and_recommendation
from ..services.warehouse_twin import get_warehouse_twin
from ..services.coordinates import get_city_coordinates, get_warehouse_coordinates, haversine_distance
from datetime import datetime, timedelta, timezone, date
import math
from typing import List, Optional, Tuple

warehouse_bp = Blueprint("warehouse", __name__)

WAREHOUSE_SUPPORTED_STORAGE = {
    "Delhi Warehouse": {"DRY"},
    "Chandigarh Warehouse": {"COLD"},
    "Bengaluru Warehouse": {"DRY", "COLD"},
    "Hyderabad Warehouse": {"DRY", "COLD"},
    "Kolkata Warehouse": {"DRY", "COLD"},
    "Bhubaneswar Warehouse": {"DRY"},
    "Mumbai Warehouse": {"DRY", "COLD"},
    "Ahmedabad Warehouse": {"DRY"},
    "Nagpur Central Warehouse": {"DRY", "COLD"},
}


def _normalize_storage_type(s: str) -> str:
    v = str(s or "").strip().lower()
    if not v:
        return ""
    if "cold" in v:
        return "COLD"
    if "ambient" in v:
        return "DRY"
    if "dry" in v:
        return "DRY"
    return ""


def _as_date(v, *, default: date) -> date:
    if v is None:
        return default
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return default
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return default
    return default


def _risk_status_from_freshness(f: float) -> str:
    if f > 0.70:
        return "SAFE"
    if f >= 0.40:
        return "RISK"
    return "HIGH"


def _escalate_risk_one_level(risk: str) -> str:
    r = str(risk or "").strip().upper()
    if r == "SAFE":
        return "RISK"
    if r == "RISK":
        return "HIGH"
    return "HIGH"


def _warehouse_risk_status(
    *,
    current_freshness: float,
    predicted_24h: float,
    predicted_48h: Optional[float],
    decay_rate_per_hour: float,
    storage_incompatible: bool,
) -> str:
    """Warehouse spoilage risk interpretation.

    Risk is driven by freshness level and expected decline trend, not by environment deviation
    directly. Environment affects risk only through predicted freshness.
    """

    cur = _clamp01(float(current_freshness))
    p24 = _clamp01(float(predicted_24h))
    p48 = _clamp01(float(predicted_48h)) if predicted_48h is not None else None
    rate = max(0.0, float(decay_rate_per_hour or 0.0))

    if storage_incompatible:
        return "HIGH"

    drop_24 = max(0.0, cur - p24)
    drop_48 = max(0.0, cur - (p48 if p48 is not None else p24))

    # High freshness should be SAFE even if env is outside optimal range.
    # However, if forecasts indicate a large/rapid decline, reflect that.
    if cur >= 0.80:
        if drop_24 < 0.25 and drop_48 < 0.30 and rate <= (0.25 / 24.0):
            return "SAFE"
        # If the model forecasts a sharp fall soon, flag as RISK even though freshness is high.
        if (p48 is not None and p48 < 0.55) or p24 < 0.60:
            return "RISK"

    # Use the worst-case forecast within 48h if available.
    worst = min([v for v in [cur, p24, p48] if v is not None])
    if worst < 0.40:
        return "HIGH"

    # Significant predicted decline or low-ish forecast should be flagged as RISK.
    # For non-high freshness, absolute forecast thresholds matter.
    if cur < 0.80 and ((p48 is not None and p48 < 0.65) or p24 < 0.70):
        return "RISK"
    if drop_24 >= 0.15:
        return "RISK"
    if rate >= (0.15 / 24.0):
        return "RISK"

    return "SAFE"


def _env_out_of_optimal(*, ck, temp_c, hum_pct) -> bool:
    if ck is None:
        return False
    try:
        opt_t = getattr(ck, "optimal_temp_c", None)
        if temp_c is not None and opt_t is not None and abs(float(temp_c) - float(opt_t)) > 4.0:
            return True
    except Exception:
        pass
    try:
        opt_h = getattr(ck, "optimal_humidity_pct", None)
        if hum_pct is not None and opt_h is not None and abs(float(hum_pct) - float(opt_h)) > 15.0:
            return True
    except Exception:
        pass
    return False


def _storage_decay_rate_per_hour(*, ck) -> float:
    # Use shelf-life as decay basis: 1 / (max_days * 24)
    try:
        max_days = float(getattr(ck, "max_shelf_life_days", None) or 0.0)
    except Exception:
        max_days = 0.0
    if max_days <= 0.0:
        max_days = 10.0
    try:
        return max(0.0001, min(0.02, 1.0 / (float(max_days) * 24.0)))
    except Exception:
        return 1.0 / (10.0 * 24.0)


def _storage_profile_for_batch(*, ck, required_storage: str, is_compatible: bool) -> str:
    # Map internal storage normalization to dataset Storage_Type values.
    req_norm = _normalize_storage_type(required_storage)
    if req_norm == "COLD" and is_compatible:
        return "Cold Storage"
    if req_norm == "DRY" and is_compatible:
        return "Dry Storage"
    # Fallback to "Ambient" when incompatible/unknown.
    return "Ambient"


def _predict_warehouse_freshness_24h(
    *,
    entry_freshness: float,
    ck,
    storage_type: str,
    current_temperature: Optional[float],
    current_humidity: Optional[float],
    prediction_window_hours: float = 24.0,
    allowed_temp_range_c: float = 4.0,
    allowed_humidity_range_pct: float = 15.0,
) -> Tuple[float, List[str], bool]:
    
    alerts: List[str] = []

    opt_t = getattr(ck, "optimal_temp_c", None) if ck is not None else None
    opt_h = getattr(ck, "optimal_humidity_pct", None) if ck is not None else None
    required_storage = str(getattr(ck, "storage_type", "") or "") if ck is not None else ""

    temp_dev = None
    hum_dev = None
    try:
        if opt_t is not None and current_temperature is not None:
            temp_dev = abs(float(current_temperature) - float(opt_t))
    except Exception:
        temp_dev = None
    try:
        if opt_h is not None and current_humidity is not None:
            hum_dev = abs(float(current_humidity) - float(opt_h))
    except Exception:
        hum_dev = None

    if temp_dev is not None and float(temp_dev) > float(allowed_temp_range_c):
        alerts.append("Temperature outside optimal range")
    if hum_dev is not None and float(hum_dev) > float(allowed_humidity_range_pct):
        alerts.append("Humidity outside optimal range")

    # Storage mismatch penalty: only when we can compare an actual profile vs required.
    storage_incompatible = False
    try:
        req_n = str(required_storage or "").strip().lower()
        act_n = str(storage_type or "").strip().lower()
        if req_n and act_n and req_n != act_n:
            storage_incompatible = True
    except Exception:
        storage_incompatible = False
    if storage_incompatible:
        alerts.append("Storage incompatible for crop")

    # Deterministic decay model (time-based) + environment stress
    # Base decay per hour comes from crop shelf-life; stress multipliers increase decay.
    base_decay_per_hour = _storage_decay_rate_per_hour(ck=ck)
    try:
        hrs = float(prediction_window_hours or 24.0)
    except Exception:
        hrs = 24.0
    if hrs <= 0:
        hrs = 24.0

    # Stress multipliers: temperature affects decay more strongly than humidity.
    try:
        t_mul = 1.0 + (0.08 * max(0.0, float(temp_dev or 0.0)))
    except Exception:
        t_mul = 1.0
    try:
        h_mul = 1.0 + (0.02 * max(0.0, float(hum_dev or 0.0)))
    except Exception:
        h_mul = 1.0
    stress_mul = float(t_mul) * float(h_mul)

    if storage_incompatible:
        # Storage mismatch accelerates decay additionally (simple explainable multiplier)
        stress_mul *= 1.25

    loss = float(base_decay_per_hour) * float(hrs) * float(stress_mul)
    predicted = _clamp01(float(entry_freshness) - float(loss))
    if float(predicted) < float(entry_freshness) - 1e-9:
        alerts.append("Predicted freshness drop within 24 hours")

    # Deduplicate while keeping stable order
    out = []
    seen = set()
    for a in alerts:
        k = str(a).strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(str(a))

    return (float(predicted), out, bool(storage_incompatible))


def _region_for_warehouse(warehouse_name: str) -> str:
    name = (warehouse_name or "").strip()
    mapping = {
        "Delhi Warehouse": "North",
        "Chandigarh Warehouse": "North",
        "Bengaluru Warehouse": "South",
        "Hyderabad Warehouse": "South",
        "Kolkata Warehouse": "East",
        "Bhubaneswar Warehouse": "East",
        "Mumbai Warehouse": "West",
        "Ahmedabad Warehouse": "West",
        "Nagpur Central Warehouse": "Central",
    }
    return mapping.get(name, "Unknown")


def _extract_city(location: str) -> str:
    loc = (location or "").strip()
    if not loc:
        return ""
    if "," in loc:
        return loc.split(",", 1)[0].strip()
    return loc


def _estimate_travel_hours(batch: CropBatch, user_warehouse: str) -> float:
    try:
        city = _extract_city(getattr(batch, "location", "") or "")
        c = get_city_coordinates(city)
        w = get_warehouse_coordinates(user_warehouse)
        if c and w:
            km = float(haversine_distance(c[0], c[1], w[0], w[1]) or 0.0)
            speed_kmh = 40.0
            h = km / speed_kmh if km > 0.0 else 0.0
            if h > 0.0:
                return h
    except Exception:
        pass

    try:
        shp = Shipment.query.filter_by(batch_id=batch.id).order_by(Shipment.created_at.desc()).first()
        if shp and shp.eta_hours is not None:
            h = float(shp.eta_hours or 0.0)
            if h > 0.0:
                return h
    except Exception:
        pass

    return 6.0


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


@warehouse_bp.post("/accept")
@roles_required(ROLE_WAREHOUSE)
def accept_batch():
    data = request.get_json() or {}
    claims = get_jwt() or {}
    user_warehouse = claims.get("warehouse_location")
    if not user_warehouse:
        return jsonify({"msg": "warehouse location not found in token"}), 400

    try:
        batch_id = int(data.get("batch_id"))
    except Exception:
        return jsonify({"msg": "batch_id is required"}), 400

    force_accept = bool(data.get("force"))
    acknowledge_risk = bool(data.get("acknowledge_risk"))

    b = CropBatch.query.get(batch_id)
    if not b:
        return jsonify({"msg": "batch not found"}), 404

    try:
        shp = Shipment.query.filter_by(batch_id=b.id).order_by(Shipment.created_at.desc()).first()
    except Exception:
        shp = None
    shp_status = str(getattr(shp, "status", "") or "").strip().lower()
    if not shp or shp_status != "delivered":
        return jsonify({"msg": "warehouse receipt blocked: logistics delivery required", "required": "DELIVERED"}), 409

    if (b.warehouse or "").strip() != user_warehouse:
        return jsonify({"msg": "batch is not assigned to this warehouse"}), 403

    farmer_freshness = float(getattr(b, "freshness_score", 0.0) or 0.0)

    # Accept is based on logistics arrival freshness.
    try:
        arrival_fresh = float(getattr(shp, "current_freshness", None) or 0.0)
    except Exception:
        arrival_fresh = 0.0
    arrival_fresh = _clamp01(float(arrival_fresh))

    risk_now = _risk_status_from_freshness(float(arrival_fresh))
    if risk_now in {"RISK", "HIGH"} and not acknowledge_risk:
        return jsonify({"msg": "Accept requires risk acknowledgement.", "risk_status": risk_now}), 409

    delivered_at = getattr(shp, "delivery_time", None)
    today = datetime.now(timezone.utc).date()
    entry_date = delivered_at.date() if isinstance(delivered_at, datetime) else today

    b.current_stage = "WAREHOUSE"
    b.warehouse_name = user_warehouse
    b.storage_start_date = entry_date
    b.warehouse_entry_date = entry_date
    b.farmer_freshness_snapshot = farmer_freshness

    # Warehouse entry freshness is immutable and must come from logistics final freshness.
    try:
        if getattr(b, "warehouse_entry_freshness", None) is None:
            b.warehouse_entry_freshness = round(float(arrival_fresh), 6)
    except Exception:
        pass
    b.warehouse_freshness = round(float(arrival_fresh), 6)
    if getattr(b, "last_simulated_date", None) is None:
        b.last_simulated_date = entry_date
    db.session.add(b)

    try:
        ws = WarehouseStatus(
            batch_id=int(b.id),
            temperature=None,
            humidity=None,
            storage_duration_hours=0,
            status="STORED",
            timestamp=datetime.now(timezone.utc),
            updated_by=int(claims.get("sub")) if claims.get("sub") is not None else None,
            warehouse_location=str(user_warehouse),
        )
        db.session.add(ws)
    except Exception:
        pass

    # Audit: risk acknowledgement (no freshness mutation)
    try:
        if risk_now in {"RISK", "HIGH"} and acknowledge_risk:
            db.session.add(StorageLog(batch_id=int(b.id), condition_status="risk_acknowledged"))
    except Exception:
        pass
    db.session.commit()
    return jsonify({"msg": "accepted", "batch_id": b.id, "warehouse_name": user_warehouse})


@warehouse_bp.get("/dashboard")
@roles_required(ROLE_WAREHOUSE)
def dashboard():
    try:
        claims = get_jwt() or {}
        user_warehouse = claims.get("warehouse_location")
        if not user_warehouse:
            return jsonify({"msg": "warehouse location not found in token"}), 400

        twin = get_warehouse_twin()
        today = datetime.now(timezone.utc).date()

        env_date, env_temp, env_hum = (None, None, None)
        env = twin.climate_for(user_warehouse, today)
        if env:
            env_date, env_temp, env_hum = env

        incoming_all = CropBatch.query.filter_by(warehouse=user_warehouse).all()
        incoming = []
        for b in incoming_all:
            stage = (getattr(b, "current_stage", None) or "").strip() or "FARMER"
            if stage == "WAREHOUSE":
                incoming.append(b)
                continue
            try:
                shp = Shipment.query.filter_by(batch_id=b.id).order_by(Shipment.created_at.desc()).first()
                st = str(getattr(shp, "status", "") or "").strip().lower()
                if st == "delivered":
                    incoming.append(b)
            except Exception:
                continue

        incoming_rows = []
        stored_rows = []
        salvage_pending_rows = []
        salvage_completed_rows = []
        first_crop = None
        for _b in incoming:
            first_crop = _b.crop_type
            if first_crop:
                break
        env_compat = "Incompatible"
        if first_crop:
            env_compat = twin.compatibility_status(crop=first_crop, actual_temp_c=env_temp, actual_humidity_pct=env_hum)

        dirty = False
        for b in incoming:
            stage = (getattr(b, "current_stage", None) or "").strip() or "FARMER"

            if str(getattr(b, "status", "") or "").strip().upper() in {"SALVAGE_PENDING", "SALVAGED", "EMERGENCY_REQUIRED"}:
                continue

            ck = twin.get_crop_knowledge(b.crop_type)

            if stage == "WAREHOUSE":
                entry_raw = getattr(b, "warehouse_entry_date", None) or getattr(b, "storage_start_date", None)
                entry = _as_date(entry_raw, default=today)
                days_in_warehouse = (today - entry).days
                if days_in_warehouse < 1:
                    days_in_warehouse = 1

                # Stored batches: entry freshness is fixed at intake time.
                entry_fresh = getattr(b, "warehouse_entry_freshness", None)
                try:
                    entry_fresh = float(entry_fresh) if entry_fresh is not None else None
                except Exception:
                    entry_fresh = None
                if entry_fresh is None:
                    entry_fresh = float(getattr(b, "freshness_score", 0.0) or 0.0)
                entry_fresh = _clamp01(float(entry_fresh))

                # Required storage must come directly from dataset Storage_Type.
                ck_required = twin.get_crop_knowledge(b.crop_type, storage_type=None) or ck
                required_storage = (ck_required.storage_type if ck_required else "")

                # Actual storage profile: assume required storage if warehouse supports it, else Ambient.
                supported = WAREHOUSE_SUPPORTED_STORAGE.get(user_warehouse, {"DRY"})
                req_norm = _normalize_storage_type(required_storage)
                is_compatible = (not req_norm) or (req_norm in supported)
                actual_storage_profile = str(required_storage or "") if is_compatible else "Ambient"

                # Compute a climate-aware daily decay and update current freshness based on days stored.
                shelf_days = 0.0
                try:
                    sd = getattr(ck_required, "max_shelf_life_days", None) if ck_required is not None else None
                    if sd is None and ck is not None:
                        sd = getattr(ck, "max_shelf_life_days", None)
                    shelf_days = float(sd or 0.0)
                except Exception:
                    shelf_days = 0.0

                daily_decay = 0.0
                try:
                    base_decay = 1.0 / float(shelf_days or 1.0)
                    temp_penalty = 0.0
                    hum_penalty = 0.0
                    if env_temp is not None and env_hum is not None and ck_required is not None:
                        try:
                            temp_diff = abs(float(env_temp) - float(getattr(ck_required, "optimal_temp_c", env_temp)))
                        except Exception:
                            temp_diff = 0.0
                        try:
                            hum_diff = abs(float(env_hum) - float(getattr(ck_required, "optimal_humidity_pct", env_hum)))
                        except Exception:
                            hum_diff = 0.0
                        days_norm = float(shelf_days or 1.0)
                        temp_penalty = (temp_diff / days_norm) * 0.002
                        hum_penalty = (hum_diff / days_norm) * 0.001
                    daily_decay = max(0.0, base_decay + temp_penalty + hum_penalty)
                except Exception:
                    daily_decay = 0.0

                # Compute continuous decay based on actual elapsed hours since warehouse entry
                # Get warehouse entry timestamp (use entry_date combined with current time)
                entry_datetime = datetime.combine(entry, datetime.min.time()) if entry else datetime.now(timezone.utc)
                # Ensure entry_datetime is timezone-aware
                if entry_datetime.tzinfo is None:
                    entry_datetime = entry_datetime.replace(tzinfo=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                elapsed_hours = max(0.0, float((now_utc - entry_datetime).total_seconds() / 3600.0))
                
                # Get optimal conditions for stress calculation
                opt_t = None
                opt_h = None
                try:
                    opt_t = getattr(ck_required, "optimal_temp_c", None) if ck_required else None
                except Exception:
                    opt_t = None
                try:
                    opt_h = getattr(ck_required, "optimal_humidity_pct", None) if ck_required else None
                except Exception:
                    opt_h = None
                
                # Calculate stress multipliers
                temp_dev = 0.0
                hum_dev = 0.0
                if env_temp is not None and opt_t is not None:
                    try:
                        temp_dev = abs(float(env_temp) - float(opt_t))
                    except Exception:
                        temp_dev = 0.0
                if env_hum is not None and opt_h is not None:
                    try:
                        hum_dev = abs(float(env_hum) - float(opt_h))
                    except Exception:
                        hum_dev = 0.0
                
                # Stress multipliers: temperature affects decay more strongly than humidity
                temp_multiplier = 1.0 + (0.08 * max(0.0, temp_dev))
                humidity_multiplier = 1.0 + (0.02 * max(0.0, hum_dev))
                stress_multiplier = temp_multiplier * humidity_multiplier
                
                # Storage mismatch penalty
                storage_incompatible = False
                try:
                    req_n = str(required_storage or "").strip().lower()
                    act_n = str(actual_storage_profile or "").strip().lower()
                    if req_n and act_n and req_n != act_n:
                        storage_incompatible = True
                except Exception:
                    pass
                if storage_incompatible:
                    stress_multiplier *= 1.25
                
                # Calculate decay rate per hour based on shelf life
                try:
                    shelf_life_hours = float(shelf_days) * 24.0 if shelf_days > 0 else 72.0
                    base_decay_per_hour = 1.0 / shelf_life_hours
                except Exception:
                    base_decay_per_hour = 1.0 / 72.0  # Default: 72 hours
                
                # Calculate total loss over elapsed time
                loss = base_decay_per_hour * elapsed_hours * stress_multiplier
                
                # Update freshness
                wh_fresh = _clamp01(float(entry_fresh) - float(loss))
                b.warehouse_freshness = round(float(wh_fresh), 6)
                b.last_freshness_update_date = today
                
                # For predictions, calculate future decay rates (24h and 48h ahead)
                future_loss_24h = base_decay_per_hour * 24.0 * stress_multiplier
                predicted_wh_fresh = _clamp01(float(wh_fresh) - float(future_loss_24h))
                
                future_loss_48h = base_decay_per_hour * 48.0 * stress_multiplier
                predicted_wh_fresh_48h = _clamp01(float(wh_fresh) - float(future_loss_48h))
                
                # Generate alerts based on conditions
                pred_alerts = []
                if temp_dev > 4.0:
                    pred_alerts.append("Temperature outside optimal range")
                if hum_dev > 15.0:
                    pred_alerts.append("Humidity outside optimal range")
                if storage_incompatible:
                    pred_alerts.append("Storage incompatible for crop")
                if float(predicted_wh_fresh) < float(wh_fresh) - 1e-9:
                    pred_alerts.append("Predicted freshness drop within 24 hours")
                
                # Decay rate per hour for display
                decay_rate_per_hour = base_decay_per_hour * stress_multiplier

                # Simple freshness-based risk status
                if wh_fresh > 0.50:
                    risk_status = "SAFE"
                elif wh_fresh > 0.30:
                    risk_status = "RISK"
                else:
                    risk_status = "HIGH"
                b.status = risk_status
                db.session.add(b)
                dirty = True

                alerts = list(pred_alerts)

                # Storage compatibility: compatible only if env is within optimal and storage is not incompatible.
                storage_compatibility = "Compatible" if ("Temperature outside optimal range" not in alerts and "Humidity outside optimal range" not in alerts and "Storage incompatible for crop" not in alerts) else "Not Compatible"

                # Remaining safe days: derived from CURRENT warehouse freshness.
                remaining_safe_days = 0.0
                spoilage_threshold = 0.30
                
                # If freshness is already at or below threshold, no safe days remain
                if wh_fresh <= spoilage_threshold:
                    remaining_safe_days = 0.0
                elif daily_decay > 0.0:
                    try:
                        wh_remaining = (float(wh_fresh) - float(spoilage_threshold)) / float(daily_decay)
                        if wh_remaining is not None and isinstance(wh_remaining, float) and math.isfinite(wh_remaining):
                            remaining_safe_days = float(round(float(wh_remaining), 2))
                        else:
                            remaining_safe_days = 0.0
                    except Exception:
                        remaining_safe_days = 0.0
                else:
                    # If no decay, use shelf life as remaining days
                    remaining_safe_days = float(shelf_days) if shelf_days > 0 else 0.0

                # Set recommendation based on remaining days
                if remaining_safe_days <= 0:
                    rec = "Move batch to salvage or discard immediately"
                    exp = "Crop has already crossed safe freshness threshold"
                    outlook = "Immediate action required to minimize losses"
                    alert_message = f"CRITICAL: {b.crop_type} freshness at {round(wh_fresh*100,0):.0f}% - below safe threshold. Immediate salvage or discard required."
                else:
                    rec = ""
                    exp = ""
                    outlook = ""
                    alert_message = ""

                stored_rows.append({
                    "id": b.id,
                    "crop_type": b.crop_type,
                    "harvest_date": str(b.harvest_date),
                    "predicted_warehouse_freshness": float(round(float(predicted_wh_fresh), 6)),
                    "freshness": float(b.warehouse_freshness or 0.0),
                    "warehouse_entry_freshness": float(b.warehouse_entry_freshness or 0.0),
                    "decay_rate_per_hour": float(round(float(decay_rate_per_hour), 8)),
                    "optimal_temperature_c": opt_t,
                    "optimal_humidity_pct": opt_h,
                    "warehouse_temperature_c": env_temp,
                    "warehouse_humidity_pct": env_hum,
                    "remaining_safe_days": remaining_safe_days,
                    "risk_status": risk_status,
                    "alerts": alerts,
                    "alert_message": alert_message,
                    "storage_type": required_storage,
                    "storage_compatibility": storage_compatibility,
                    "recommendation": rec,
                    "explanation": exp,
                    "short_term_outlook": outlook,
                })
            else:
                alerts = []

                # Deterministic handoff: use logistics-delivered arrival freshness/time.
                shp = None
                try:
                    shp = Shipment.query.filter_by(batch_id=b.id).order_by(Shipment.created_at.desc()).first()
                except Exception:
                    shp = None
                try:
                    arrival_fresh = float(getattr(shp, "current_freshness", None) or 0.0)
                except Exception:
                    arrival_fresh = 0.0
                arrival_fresh = _clamp01(float(arrival_fresh))

                # Copy once: persist the logistics final freshness as warehouse entry freshness.
                stored_entry = getattr(b, "warehouse_entry_freshness", None)
                if stored_entry is None:
                    try:
                        b.warehouse_entry_freshness = round(float(arrival_fresh), 6)
                        db.session.add(b)
                        dirty = True
                    except Exception:
                        pass
                    entry_fresh = float(arrival_fresh)
                else:
                    try:
                        entry_fresh = float(stored_entry)
                    except Exception:
                        entry_fresh = float(arrival_fresh)
                entry_fresh = _clamp01(float(entry_fresh))

                arrival_time_iso = None
                try:
                    dt = getattr(shp, "delivery_time", None)
                    arrival_time_iso = dt.isoformat() + "Z" if dt is not None else None
                except Exception:
                    arrival_time_iso = None

                # Required storage comes from dataset.
                ck_required = twin.get_crop_knowledge(b.crop_type, storage_type=None) or ck
                required_storage = (ck_required.storage_type if ck_required else (ck.storage_type if ck else ""))

                # Actual storage profile before acceptance:
                # if the warehouse supports the required storage, assume it is held accordingly;
                # otherwise it is effectively Ambient and should trigger incompatibility.
                supported = WAREHOUSE_SUPPORTED_STORAGE.get(user_warehouse, {"DRY"})
                req_norm = _normalize_storage_type(required_storage)
                is_supported = (not req_norm) or (req_norm in supported)
                wh_storage_type = str(required_storage or "") if is_supported else "Ambient"
                ck_profile = ck_required or ck

                predicted_wh_fresh, pred_alerts, storage_incompatible = _predict_warehouse_freshness_24h(
                    entry_freshness=float(entry_fresh),
                    ck=ck_profile,
                    storage_type=str(wh_storage_type or ""),
                    current_temperature=env_temp,
                    current_humidity=env_hum,
                    prediction_window_hours=24.0,
                )

                predicted_wh_fresh_48h, _pred_alerts_48, storage_incompatible_48 = _predict_warehouse_freshness_24h(
                    entry_freshness=float(entry_fresh),
                    ck=ck_profile,
                    storage_type=str(wh_storage_type or ""),
                    current_temperature=env_temp,
                    current_humidity=env_hum,
                    prediction_window_hours=48.0,
                )

                try:
                    decay_rate_per_hour = max(0.0, (float(entry_fresh) - float(predicted_wh_fresh)) / 24.0)
                except Exception:
                    decay_rate_per_hour = 0.0

                risk_status = _warehouse_risk_status(
                    current_freshness=float(entry_fresh),
                    predicted_24h=float(predicted_wh_fresh),
                    predicted_48h=float(predicted_wh_fresh_48h),
                    decay_rate_per_hour=float(decay_rate_per_hour),
                    storage_incompatible=bool(storage_incompatible or storage_incompatible_48),
                )

                alerts = list(pred_alerts)

                rec = ""
                exp = ""
                outlook = ""
                alert_message = ""

                incoming_rows.append({
                    "id": b.id,
                    "crop_type": b.crop_type,
                    "harvest_date": str(b.harvest_date),
                    "warehouse_entry_freshness": round(float(entry_fresh), 6),
                    "arrival_time": arrival_time_iso,
                    "risk_status": risk_status,
                    "alerts": alerts,
                    "alert_message": alert_message,
                    "recommendation": rec,
                    "explanation": exp,
                    "short_term_outlook": outlook,
                })

        warehouse_info = {
            "warehouse_name": user_warehouse,
            "region": _region_for_warehouse(user_warehouse),
            "temperature_c": env_temp,
            "humidity_pct": env_hum,
        }

        try:
            sb_all = SalvageBatch.query.order_by(SalvageBatch.created_at.desc()).all()
        except Exception:
            sb_all = []
        for sb in (sb_all or []):
            b = None
            try:
                b = CropBatch.query.get(int(getattr(sb, "batch_id", 0) or 0))
            except Exception:
                b = None
            if b is None:
                continue
            if (str(getattr(b, "warehouse", "") or "").strip() != str(user_warehouse or "").strip()):
                continue
            row = {
                "salvage_id": int(getattr(sb, "id", 0) or 0),
                "shipment_id": int(getattr(sb, "shipment_id", 0) or 0),
                "batch_id": int(getattr(sb, "batch_id", 0) or 0),
                "crop": str(getattr(sb, "crop", "") or str(getattr(b, "crop_type", "") or "")),
                "quantity_pct": getattr(sb, "quantity_pct", None),
                "reason": str(getattr(sb, "reason", "") or ""),
                "status": str(getattr(sb, "salvage_status", "") or "").strip().upper(),
                "created_at": getattr(sb, "created_at", None).isoformat() + "Z" if getattr(sb, "created_at", None) is not None else None,
                "completed_at": getattr(sb, "completed_at", None).isoformat() + "Z" if getattr(sb, "completed_at", None) is not None else None,
            }
            if row["status"] == "COMPLETED":
                salvage_completed_rows.append(row)
            else:
                salvage_pending_rows.append(row)

        if dirty:
            db.session.commit()

        return jsonify({
            "warehouse": warehouse_info,
            "incoming_batches": incoming_rows,
            "stored_batches": stored_rows,
            "salvage_batches": salvage_pending_rows,
            "salvage_records": salvage_completed_rows,
        })
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"msg": f"internal error: {type(e).__name__}: {e}"}), 500


@warehouse_bp.get("/recommendation")
@roles_required(ROLE_WAREHOUSE)
def recommendation():
    """Lazy-load GenAI recommendation payload for a single batch.

    This keeps /dashboard fast by not calling the LLM per row.
    """
    claims = get_jwt() or {}
    user_warehouse = claims.get("warehouse_location")
    if not user_warehouse:
        return jsonify({"msg": "warehouse location not found in token"}), 400

    try:
        batch_id = int(request.args.get("batch_id") or 0)
    except Exception:
        batch_id = 0
    if not batch_id:
        return jsonify({"msg": "batch_id required"}), 400

    scope = str(request.args.get("scope") or "").strip().lower()  # incoming|stored
    if scope not in {"incoming", "stored"}:
        scope = "incoming"

    b = CropBatch.query.get(batch_id)
    if not b:
        return jsonify({"msg": "batch not found"}), 404
    if (b.warehouse or "").strip() != user_warehouse:
        return jsonify({"msg": "forbidden"}), 403

    twin = get_warehouse_twin()
    today = datetime.now(timezone.utc).date()
    env = twin.climate_for(user_warehouse, today)
    env_temp = env[1] if env else None
    env_hum = env[2] if env else None

    ck = twin.get_crop_knowledge(b.crop_type)
    ck_required = twin.get_crop_knowledge(b.crop_type, storage_type=None) or ck
    required_storage = (ck_required.storage_type if ck_required else "")

    supported = WAREHOUSE_SUPPORTED_STORAGE.get(user_warehouse, {"DRY"})
    req_norm = _normalize_storage_type(required_storage)
    is_supported = (not req_norm) or (req_norm in supported)
    wh_storage_type = str(required_storage or "") if is_supported else "Ambient"
    ck_profile = ck_required or ck

    # Use current freshness if available; otherwise fall back to entry freshness.
    entry_fresh = getattr(b, "warehouse_entry_freshness", None)
    try:
        entry_fresh = float(entry_fresh) if entry_fresh is not None else None
    except Exception:
        entry_fresh = None
    if entry_fresh is None:
        entry_fresh = float(getattr(b, "freshness_score", 0.0) or 0.0)
    entry_fresh = _clamp01(float(entry_fresh))

    current_fresh = getattr(b, "warehouse_freshness", None)
    try:
        current_fresh = float(current_fresh) if current_fresh is not None else None
    except Exception:
        current_fresh = None
    if current_fresh is None:
        current_fresh = float(entry_fresh)
    current_fresh = _clamp01(float(current_fresh))

    predicted_wh_fresh, pred_alerts, storage_incompatible = _predict_warehouse_freshness_24h(
        entry_freshness=float(current_fresh),
        ck=ck_profile,
        storage_type=str(wh_storage_type or ""),
        current_temperature=env_temp,
        current_humidity=env_hum,
        prediction_window_hours=24.0,
    )

    predicted_wh_fresh_48h, _pred_alerts_48, storage_incompatible_48 = _predict_warehouse_freshness_24h(
        entry_freshness=float(current_fresh),
        ck=ck_profile,
        storage_type=str(wh_storage_type or ""),
        current_temperature=env_temp,
        current_humidity=env_hum,
        prediction_window_hours=48.0,
    )

    try:
        decay_rate_per_hour = max(0.0, (float(current_fresh) - float(predicted_wh_fresh)) / 24.0)
    except Exception:
        decay_rate_per_hour = 0.0

    risk_status = _warehouse_risk_status(
        current_freshness=float(current_fresh),
        predicted_24h=float(predicted_wh_fresh),
        predicted_48h=float(predicted_wh_fresh_48h),
        decay_rate_per_hour=float(decay_rate_per_hour),
        storage_incompatible=bool(storage_incompatible or storage_incompatible_48),
    )

    alerts = list(pred_alerts)

    storage_compatibility = "Not Compatible" if (
        "Storage incompatible for crop" in alerts
        or "Temperature outside optimal range" in alerts
        or "Humidity outside optimal range" in alerts
    ) else "Compatible"

    # Calculate remaining safe days
    spoilage_threshold = 0.30
    remaining_days = 0.0
    try:
        shelf_days = float(getattr(ck_profile, "max_shelf_life_days", None) or 0.0)
        daily_decay = 1.0 / shelf_days if shelf_days > 0 else 0.0
        if predicted_wh_fresh <= spoilage_threshold:
            remaining_days = 0.0
        elif daily_decay > 0.0:
            remaining_days = (predicted_wh_fresh - spoilage_threshold) / daily_decay
            if not isinstance(remaining_days, float) or not math.isfinite(remaining_days):
                remaining_days = 0.0
        else:
            remaining_days = shelf_days
    except Exception:
        remaining_days = 0.0

    rec = ""
    exp = ""
    outlook = ""
    alert_message = ""
    
    # Priority: Check if remaining days is 0 for salvage recommendation
    if remaining_days <= 0:
        rec = "Move batch to salvage processing immediately or dispose of it"
        exp = "Crop has already fallen below safe freshness threshold"
        outlook = "Immediate action required to minimize losses"
        alert_message = f"CRITICAL: {b.crop_type} at {round(predicted_wh_fresh*100,0):.0f}% freshness - below safe threshold. Immediate salvage or disposal required."
    else:
        # Only generate preventive recommendations when remaining_days > 0
        try:
            out = generate_warehouse_recommendation({
                "crop": b.crop_type,
                "storage_type": required_storage,
                "warehouse_entry_freshness": float(entry_fresh),
                "predicted_warehouse_freshness": float(predicted_wh_fresh),
                "warehouse_spoilage_risk": risk_status,
                "current_temperature": env_temp,
                "current_humidity": env_hum,
                "optimal_temperature": getattr(ck_profile, "optimal_temp_c", None) if ck_profile else None,
                "optimal_humidity": getattr(ck_profile, "optimal_humidity_pct", None) if ck_profile else None,
            })
            if isinstance(out, dict):
                rec = str(out.get("recommendation") or "").strip()
                exp = str(out.get("explanation") or "").strip()
                outlook = str(out.get("short_term_outlook") or "").strip()
        except Exception:
            pass

        try:
            opt_t = getattr(ck_profile, "optimal_temp_c", None) if ck_profile else None
            opt_h = getattr(ck_profile, "optimal_humidity_pct", None) if ck_profile else None
            temp_dev = abs(float(env_temp) - float(opt_t)) if (env_temp is not None and opt_t is not None) else 0.0
            hum_dev = abs(float(env_hum) - float(opt_h)) if (env_hum is not None and opt_h is not None) else 0.0
            g = generate_warehouse_alert_and_recommendation({
                "crop": b.crop_type,
                "current_freshness": float(predicted_wh_fresh),
                "predicted_freshness_24h": float(predicted_wh_fresh),
                "warehouse_risk_level": str(risk_status),
                "temperature_deviation_c": float(temp_dev),
                "humidity_deviation_pct": float(hum_dev),
                "storage_compatibility": str(storage_compatibility),
            })
            if isinstance(g, dict):
                alert_message = str(g.get("alert_message") or "").strip()
        except Exception:
            pass

    return jsonify({
        "batch_id": int(b.id),
        "scope": scope,
        "alert_message": alert_message,
        "recommendation": rec,
        "explanation": exp,
        "short_term_outlook": outlook,
    })


@warehouse_bp.post("/flag-emergency")
@roles_required(ROLE_WAREHOUSE)
def flag_emergency_dispatch():
    data = request.get_json() or {}
    batch_id = data.get("batch_id")
    
    if not batch_id:
        return jsonify({"msg": "batch_id required"}), 400
    
    # 1️⃣ Validate Request
    batch = CropBatch.query.filter_by(id=int(batch_id)).first()
    if not batch:
        return jsonify({"msg": "batch not found"}), 404

    risk_status = str(getattr(batch, "status", "") or "").strip().upper()

    remaining_days = None
    try:
        wh_fresh = float(getattr(batch, "warehouse_freshness", None) or 0.0)
    except Exception:
        wh_fresh = 0.0

    env_temp = None
    env_hum = None
    try:
        ws = WarehouseStatus.query.filter_by(batch_id=int(batch.id)).order_by(WarehouseStatus.timestamp.desc()).first()
    except Exception:
        ws = None
    if ws is not None:
        try:
            env_temp = float(getattr(ws, "temperature", None)) if getattr(ws, "temperature", None) is not None else None
        except Exception:
            env_temp = None
        try:
            env_hum = float(getattr(ws, "humidity", None)) if getattr(ws, "humidity", None) is not None else None
        except Exception:
            env_hum = None

    shelf_days = 0.0
    opt_t = None
    opt_h = None
    try:
        twin = get_warehouse_twin()
        ck = twin.get_crop_knowledge(str(getattr(batch, "crop_type", "") or ""), None)
        if ck is not None:
            shelf_days = float(getattr(ck, "max_shelf_life_days", 0.0) or 0.0)
            opt_t = getattr(ck, "optimal_temp_c", None)
            opt_h = getattr(ck, "optimal_humidity_pct", None)
    except Exception:
        shelf_days = 0.0

    daily_decay = 0.0
    try:
        base_decay = 1.0 / float(shelf_days or 1.0)
        temp_penalty = 0.0
        hum_penalty = 0.0
        if env_temp is not None and env_hum is not None and opt_t is not None and opt_h is not None:
            try:
                temp_diff = abs(float(env_temp) - float(opt_t))
            except Exception:
                temp_diff = 0.0
            try:
                hum_diff = abs(float(env_hum) - float(opt_h))
            except Exception:
                hum_diff = 0.0
            days_norm = float(shelf_days or 1.0)
            temp_penalty = (temp_diff / days_norm) * 0.002
            hum_penalty = (hum_diff / days_norm) * 0.001
        daily_decay = max(0.0, float(base_decay) + float(temp_penalty) + float(hum_penalty))
    except Exception:
        daily_decay = 0.0

    spoilage_threshold = 0.40
    wh_remaining = 0.0
    try:
        if daily_decay > 0.0:
            wh_remaining = (float(wh_fresh) - float(spoilage_threshold)) / float(daily_decay)
        else:
            wh_remaining = 0.0
    except Exception:
        wh_remaining = 0.0

    try:
        baseline_days = max(0.0, float(shelf_days) * float(wh_fresh)) if (float(shelf_days) > 0.0 and float(wh_fresh) > 0.0) else 0.0
    except Exception:
        baseline_days = 0.0
    if baseline_days > 0.0:
        wh_remaining = min(max(0.0, float(wh_remaining)), float(baseline_days))
    else:
        wh_remaining = max(0.0, float(wh_remaining))
    remaining_days = float(round(float(wh_remaining), 2))

    if risk_status != "HIGH" or float(remaining_days) > 0.0:
        return jsonify({"msg": "Emergency flagging only allowed for CRITICAL crops with exhausted shelf life"}), 409
    
    # 2️⃣ Find associated shipment
    shipment = Shipment.query.filter_by(batch_id=batch.id).order_by(Shipment.created_at.desc()).first()
    if not shipment:
        return jsonify({"msg": "shipment not found for batch"}), 404
    
    # 3️⃣ Update Shipment State - Flag emergency + create salvage record (warehouse-owned)
    shipment.status = "EMERGENCY_REQUIRED"
    shipment.priority = "HIGH"
    shipment.allowed_sale = False
    shipment.updated_at = datetime.utcnow()
    
    # 4️⃣ Update Batch Status
    batch.status = "EMERGENCY_REQUIRED"
    batch.updated_at = datetime.utcnow()

    # Salvage record must exist before logistics can confirm salvage completion.
    try:
        existing = SalvageBatch.query.filter_by(shipment_id=int(shipment.id)).order_by(SalvageBatch.created_at.desc()).first()
    except Exception:
        existing = None
    if existing is None:
        qty_pct = None
        try:
            f = getattr(batch, "warehouse_freshness", None)
            f = float(f) if f is not None else 0.0
        except Exception:
            f = 0.0
        try:
            qty_pct = float(round(max(0.0, min(1.0, float(f))) * 100.0, 2))
        except Exception:
            qty_pct = None
        try:
            sb = SalvageBatch(
                shipment_id=int(shipment.id),
                batch_id=int(batch.id),
                crop=str(getattr(batch, "crop_type", "") or getattr(shipment, "crop", "") or ""),
                quantity_pct=qty_pct,
                reason="Shelf life exhausted",
                salvage_status="PENDING",
            )
            db.session.add(sb)
        except Exception:
            pass
    
    # 5️⃣ Create Audit Log
    try:
        from ..models import BlockchainLog
        audit_log = BlockchainLog(
            action="EMERGENCY_FLAGGED",
            reference_id=int(shipment.id),
            shipment_id=int(shipment.id),
            batch_id=batch.id,
            details="SHELF_LIFE_EXHAUSTED_WAREHOUSE_FLAG"
        )
        db.session.add(audit_log)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create audit log: {e}")
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to flag emergency dispatch: {e}")
        return jsonify({"msg": "database error"}), 500
    
    # 6️⃣ Backend Response
    return jsonify({
        "success": True,
        "batch_id": int(batch_id),
        "shipment_id": int(shipment.id),
        "status": "EMERGENCY_REQUIRED",
        "message": "Emergency flagged. Logistics team notified."
    })

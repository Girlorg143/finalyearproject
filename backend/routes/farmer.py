from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from ..extensions import db
from ..models import CropBatch, MLPrediction, ROLE_FARMER
from ..utils import roles_required
from ..services.warehouse_locations import get_nearest_warehouses, get_warehouse_details, CITY_TO_REGION, WAREHOUSE_REGIONS
from ..services.coordinates import get_nearest_warehouses_by_distance, get_city_coordinates, get_warehouse_coordinates, haversine_distance
from ..services.weather import get_weather
from ..services.genai import generate_farmer_recommendation
from ..models import Shipment, WarehouseStatus
from ..services.warehouse_twin import get_warehouse_twin

farmer_bp = Blueprint("farmer", __name__)


def _season_labels_for_crop(crop: str) -> list:
    meta = _get_crop_meta()
    rows = meta.get(str(crop or "").strip().lower(), [])
    seasons = []
    for r in (rows or []):
        s = str((r or {}).get("season") or "").strip()
        if not s:
            continue
        if s.strip().lower() == "perennial":
            return ["Perennial"]
        if s not in seasons:
            seasons.append(s)
    return seasons


def _season_label_for_today() -> str:
    try:
        month = int(datetime.now(timezone.utc).month)
    except Exception:
        month = 0
    return _season_label_for_month(month)


@farmer_bp.post("/batches/<int:batch_id>/request_pickup")
@roles_required(ROLE_FARMER)
def request_pickup(batch_id: int):
    claims = get_jwt() or {}
    farmer_id = int(claims.get("sub"))
    b = CropBatch.query.filter_by(id=int(batch_id), farmer_id=farmer_id).first()
    if not b:
        return jsonify({"msg": "batch not found"}), 404

    today = datetime.now(timezone.utc).date()
    try:
        days_since_harvest = int((today - (getattr(b, "harvest_date", None) or today)).days)
        if days_since_harvest < 0:
            days_since_harvest = 0
    except Exception:
        days_since_harvest = 0

    crop = getattr(b, "crop_type", "") or ""
    try:
        base_shelf_life_days = float(_base_shelf_life_days_for_crop(crop) or 1.0)
    except Exception:
        base_shelf_life_days = 1.0
    if base_shelf_life_days <= 0.0:
        base_shelf_life_days = 1.0

    freshness = None
    try:
        snap = getattr(b, "farmer_freshness_snapshot", None)
        if snap is None:
            snap = getattr(b, "freshness_score", None)
        if snap is not None:
            freshness = float(snap)
    except Exception:
        freshness = None

    if freshness is None:
        freshness_calc = 1.0 - (float(days_since_harvest) / float(base_shelf_life_days))
        if freshness_calc < 0.0:
            freshness_calc = 0.0
        if freshness_calc > 1.0:
            freshness_calc = 1.0
        freshness = float(freshness_calc)

    freshness = float(round(float(freshness), 2))

    if float(freshness) <= 0.0:
        return jsonify({"msg": "Crop is spoiled and cannot be transported.", "freshness": float(freshness)}), 409

    risk_status = _risk_status_from_freshness(float(freshness))
    if str(risk_status or "").strip().upper() == "HIGH SPOILAGE RISK":
        return jsonify({"msg": "pickup blocked: high spoilage risk", "freshness": float(freshness), "risk_status": risk_status}), 409

    destination_wh = (getattr(b, "warehouse", None) or "").strip()
    if not destination_wh:
        return jsonify({"msg": "no warehouse assigned for this batch"}), 409

    origin = getattr(b, "location", None) or ""
    route_txt = f"{origin} -> {destination_wh}"

    # Freeze farmer-side freshness at pickup request time so farmer dashboard does not
    # continue recalculating it while the shipment is handled by logistics.
    try:
        snap = getattr(b, "freshness_score", None)
        if snap is None:
            snap = float(freshness)
        b.farmer_freshness_snapshot = float(snap)
    except Exception:
        pass

    try:
        exists = Shipment.query.filter_by(batch_id=b.id).order_by(Shipment.created_at.desc()).first()
        if exists:
            st_raw = str(getattr(exists, "status", "") or "").strip()
            st = st_raw.upper()
            if st and st not in {"DELIVERED", "CANCELLED"}:
                return jsonify({"msg": "pickup already requested", "shipment_id": exists.id, "status": st_raw}), 200
    except Exception:
        pass

    shp = Shipment(
        batch_id=b.id,
        crop=str(getattr(b, "crop_type", "") or ""),
        quantity=float(getattr(b, "quantity", 0.0) or 0.0),
        pickup_location=str(origin),
        destination_warehouse=str(destination_wh),
        initial_freshness=float(freshness),
        current_freshness=float(freshness),
        transit_hours_total=0.0,
        route=route_txt,
        status="PICKUP_REQUESTED",
        eta_hours=None,
        logistics_id=None,
        destination=destination_wh,
        mode=None,
        source_warehouse=str(origin),
        updated_by=farmer_id,
    )
    b.current_stage = "LOGISTICS"
    db.session.add(shp)
    db.session.add(b)
    db.session.commit()
    return jsonify({
        "msg": "pickup_requested",
        "shipment_id": shp.id,
        "batch_id": b.id,
        "origin": origin,
        "destination": destination_wh,
        "freshness": float(freshness),
        "risk_status": risk_status,
        "status": shp.status,
    })


@farmer_bp.post("/request-pickup/<int:batch_id>")
@roles_required(ROLE_FARMER)
def request_pickup_alias(batch_id: int):
    return request_pickup(batch_id)




_CROP_OPTIONS_CACHE = {"mtime": None, "values": []}

_CROP_UNIT_MAP = {
    "banana": "dozens",
    "cauliflower": "pieces",
    "cabbage": "pieces",
    "rice": "kg",
    "sugarcane": "tonnes",
}


def _unit_for_crop(crop: str) -> str:
    c = str(crop or "").strip().lower()
    return _CROP_UNIT_MAP.get(c, "kg")


def _risk_status_from_freshness(f: float) -> str:
    if float(f) > 0.70:
        return "SAFE"
    if float(f) >= 0.40:
        return "RISK"
    return "HIGH"




_CROP_META_CACHE = {"mtime": None, "values": {}}


def _crop_meta_path() -> str:
    corrected = _dataset_path("crop_freshness_shelf_life_seasonal_corrected.csv")
    seasonal = _dataset_path("crop_freshness_shelf_life_seasonal.csv")
    if os.path.exists(corrected):
        return corrected
    if os.path.exists(seasonal):
        return seasonal
    return _dataset_path("crop_freshness_shelf_life.csv")


def _get_crop_meta() -> dict:
    path = _crop_meta_path()
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None

    if _CROP_META_CACHE.get("values") and _CROP_META_CACHE.get("mtime") == mtime:
        return dict(_CROP_META_CACHE.get("values") or {})

    by_crop = {}
    try:
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.read_csv(path, encoding="utf-8-sig")

        crop_col = None
        for c in ("Crop", "crop", "CROP"):
            if c in df.columns:
                crop_col = c
                break

        season_col = None
        for c in ("Season", "season", "SEASON"):
            if c in df.columns:
                season_col = c
                break

        life_col = None
        for c in ("Max_Shelf_Life_Days", "max_shelf_life_days", "MaxShelfLifeDays"):
            if c in df.columns:
                life_col = c
                break

        temp_col = None
        for c in ("Optimal_Temp_C", "optimal_temp_c", "OptimalTempC"):
            if c in df.columns:
                temp_col = c
                break

        hum_col = None
        for c in ("Optimal_Humidity_%", "Optimal_Humidity", "optimal_humidity", "optimal_humidity_pct"):
            if c in df.columns:
                hum_col = c
                break

        if crop_col and life_col:
            for _, row in df.iterrows():
                crop = str(row.get(crop_col, "") or "").strip().lower()
                if not crop:
                    continue
                try:
                    max_days = float(row.get(life_col))
                except Exception:
                    continue
                if max_days <= 0.0:
                    continue
                season = ""
                if season_col:
                    season = str(row.get(season_col, "") or "").strip()
                optimal_temp_c = None
                if temp_col:
                    try:
                        optimal_temp_c = float(row.get(temp_col))
                    except Exception:
                        optimal_temp_c = None

                optimal_humidity_pct = None
                if hum_col:
                    try:
                        optimal_humidity_pct = float(row.get(hum_col))
                    except Exception:
                        optimal_humidity_pct = None

                by_crop.setdefault(crop, []).append({
                    "season": season,
                    "max_days": max_days,
                    "optimal_temp_c": optimal_temp_c,
                    "optimal_humidity_pct": optimal_humidity_pct,
                })
    except Exception as e:
        print(f"DEBUG: crop meta read failed for {path}: {type(e).__name__}: {e}")
        by_crop = {}

    _CROP_META_CACHE["mtime"] = mtime
    _CROP_META_CACHE["values"] = dict(by_crop)
    return dict(by_crop)


def _season_label_for_month(month: int) -> str:
    if month in (6, 7, 8, 9, 10):
        return "Kharif"
    if month in (10, 11, 12, 1, 2, 3):
        return "Rabi"
    if month in (3, 4, 5, 6):
        return "Zaid"
    return ""


def _allowed_months_for_season(season: str) -> set:
    s = str(season or "").strip().lower()
    if s == "perennial":
        return set(range(1, 13))
    if s == "kharif":
        return {6, 7, 8, 9, 10}
    if s == "rabi":
        return {10, 11, 12, 1, 2, 3}
    if s == "zaid":
        return {3, 4, 5, 6}
    return set()


def _seasonal_warning_for_crop(crop: str, harvest_date) -> str:
    try:
        month = int(getattr(harvest_date, "month", 0) or 0)
    except Exception:
        month = 0
    if month <= 0:
        return ""

    meta = _get_crop_meta()
    rows = meta.get(str(crop or "").strip().lower(), [])
    if not rows:
        return ""

    seasons = [str(r.get("season", "") or "").strip() for r in rows]
    for s in seasons:
        if str(s).strip().lower() == "perennial":
            return ""

    allowed = set()
    for s in seasons:
        allowed |= _allowed_months_for_season(s)

    if allowed and month not in allowed:
        return "Selected harvest date is outside the typical harvest season for this crop."
    return ""


def _weather_readings_for_city(city: str, _cache: dict) -> dict:
    c = str(city or "").strip()
    if not c:
        return {"temp_c": None, "humidity_pct": None, "summary": ""}
    key = c.lower()
    cached = _cache.get(key)
    if isinstance(cached, dict) and ("temp_c" in cached or "humidity_pct" in cached or "summary" in cached):
        return dict(cached)

    coords = None
    try:
        coords = get_city_coordinates(c)
    except Exception:
        coords = None
    if not coords:
        out = {"temp_c": None, "humidity_pct": None, "summary": ""}
        _cache[key] = dict(out)
        return out

    try:
        lat, lon = coords
        j = get_weather(lat, lon) or {}
        main = j.get("main") if isinstance(j, dict) else {}
        wlist = j.get("weather") if isinstance(j, dict) else None
        desc = ""
        if isinstance(wlist, list) and wlist:
            desc = str((wlist[0] or {}).get("description") or "").strip()
        temp = main.get("temp") if isinstance(main, dict) else None
        hum = main.get("humidity") if isinstance(main, dict) else None

        temp_c = None
        try:
            tval = float(temp) if temp is not None else None
        except Exception:
            tval = None
        if tval is not None:
            if tval > 80:
                tval = tval - 273.15
            temp_c = float(tval)

        humidity_pct = None
        try:
            humidity_pct = float(hum) if hum is not None else None
        except Exception:
            humidity_pct = None

        bits = []
        if temp_c is not None:
            bits.append(f"{round(temp_c, 1)}°C")
        if humidity_pct is not None:
            bits.append(f"{int(round(humidity_pct))}% humidity")
        if desc:
            bits.append(desc)
        summary = ", ".join([b for b in bits if b])
        out = {"temp_c": temp_c, "humidity_pct": humidity_pct, "summary": summary}
        _cache[key] = dict(out)
        return out
    except Exception:
        out = {"temp_c": None, "humidity_pct": None, "summary": ""}
        _cache[key] = dict(out)
        return out


def _base_shelf_life_days_for_crop(crop: str) -> float:
    meta = _get_crop_meta()
    rows = meta.get(str(crop or "").strip().lower(), [])
    if not rows:
        return 1.0
    try:
        v = max([float(r.get("max_days") or 0.0) for r in rows])
        if v > 0.0:
            return float(v)
    except Exception:
        pass
    return 1.0


def _city_from_location(loc: str) -> str:
    s = str(loc or "").strip()
    if not s:
        return ""
    if "," in s:
        return s.split(",")[0].strip()
    return s

def _warehouse_distance_km(city: str, warehouse_name: str) -> float:
    c = str(city or "").strip()
    w = str(warehouse_name or "").strip()
    if not c or not w:
        return 0.0
    try:
        city_coords = get_city_coordinates(c)
        wh_coords = get_warehouse_coordinates(w)
        if not city_coords or not wh_coords:
            return 0.0
        return float(haversine_distance(city_coords[0], city_coords[1], wh_coords[0], wh_coords[1]))
    except Exception:
        return 0.0

_INDIAN_CITIES = [
    "Agra","Ahmedabad","Ajmer","Aligarh","Allahabad","Amravati","Amritsar","Asansol","Aurangabad","Bengaluru","Bhopal","Bhubaneswar","Bikaner","Bilaspur","Chandigarh","Chennai","Coimbatore","Cuttack","Dehradun","Delhi","Dhanbad","Durgapur","Erode","Faridabad","Firozabad","Gaya","Ghaziabad","Gorakhpur","Gulbarga","Guntur","Gurugram","Guwahati","Gwalior","Howrah","Hubballi","Hyderabad","Indore","Jabalpur","Jaipur","Jalandhar","Jammu","Jamnagar","Jamshedpur","Jhansi","Jodhpur","Jorhat","Kanpur","Kochi","Kolhapur","Kolkata","Kota","Kozhikode","Kurnool","Latur","Lucknow","Ludhiana","Madurai","Mangaluru","Meerut","Moradabad","Mumbai","Mysuru","Nagpur","Nanded","Nashik","Nellore","Noida","Patna","Puducherry","Pune","Raipur","Rajahmundry","Rajkot","Ranchi","Rourkela","Salem","Sangli","Shimla","Siliguri","Solapur","Srinagar","Surat","Thane","Thanjavur","Thiruvananthapuram","Tiruchirappalli","Tirunelveli","Tiruppur","Udaipur","Ujjain","Vadodara","Varanasi","Vijayawada","Visakhapatnam","Srikakulam","Warangal", "Aizawl","Gangtok","Imphal","Itanagar","Kohima","Panaji","Shillong", "Agartala","Port Blair","Leh","Brahmapur","Jamnagar","Jalgaon","Bharatpur","Bhilai","Bhiwandi","Kakinada","Kharagpur","Nizamabad","Saharanpur","Sonipat","Udupi","Vellore","Alappuzha","Kollam","Thrissur","Tirupati","Muzaffarpur",
]

def _dataset_path(name: str) -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "agri_supply_chain_datasets", name)


def _get_crop_options() -> list:
    corrected = _dataset_path("crop_freshness_shelf_life_seasonal_corrected.csv")
    seasonal = _dataset_path("crop_freshness_shelf_life_seasonal.csv")
    base = _dataset_path("crop_freshness_shelf_life.csv")
    if os.path.exists(corrected):
        path = corrected
    elif os.path.exists(seasonal):
        path = seasonal
    else:
        path = base
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None

    if _CROP_OPTIONS_CACHE.get("values") and _CROP_OPTIONS_CACHE.get("mtime") == mtime:
        return list(_CROP_OPTIONS_CACHE.get("values") or [])

    values = []
    try:
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.read_csv(path, encoding="utf-8-sig")

        crop_col = None
        for c in ("Crop", "crop", "CROP"):
            if c in df.columns:
                crop_col = c
                break

        if crop_col:
            s = df[crop_col].dropna().astype(str).map(lambda x: x.strip()).loc[lambda x: x != ""]
            values = sorted(set(s.tolist()), key=lambda x: x.lower())
    except Exception as e:
        print(f"DEBUG: crop options read failed for {path}: {type(e).__name__}: {e}")
        values = []

    _CROP_OPTIONS_CACHE["mtime"] = mtime
    _CROP_OPTIONS_CACHE["values"] = list(values)
    return list(values)

@farmer_bp.get("/warehouses")
@roles_required(ROLE_FARMER)
def get_warehouses():
    """Get nearest warehouses based on city using geographic distance"""
    city = request.args.get("city")
    if not city:
        return jsonify({"msg": "city parameter is required"}), 400
    
    print(f"DEBUG: Getting nearest warehouses for city: {city}")
    
    try:
        # Get warehouses sorted by geographic distance
        nearest_warehouses = get_nearest_warehouses_by_distance(city, limit=5)
        if not nearest_warehouses:
            print(f"DEBUG: No distance-based warehouses found for city: {city}. Falling back to region-based mapping.")
            try:
                fallback_names = get_nearest_warehouses(city)
            except Exception:
                fallback_names = []
            nearest_warehouses = [(name, 0.0) for name in (fallback_names or [])][:5]
        
        warehouse_details = []
        
        for i, (warehouse_name, distance_km) in enumerate(nearest_warehouses):
            details = get_warehouse_details(warehouse_name)
            warehouse_info = {
                "name": details["name"],
                "capacity": details["capacity"],
                "specialization": details["specialization"],
                "distance_km": round(distance_km, 2),
                "is_nearest": i == 0,  # Mark first one as nearest
                "is_central_backup": warehouse_name == "Nagpur Central Warehouse"
            }
            warehouse_details.append(warehouse_info)
        
        print(f"DEBUG: Returning {len(warehouse_details)} warehouses for {city}")
        print(f"DEBUG: Nearest warehouse: {warehouse_details[0]['name']} ({warehouse_details[0]['distance_km']} km)")
        
        return jsonify({
            "city": city,
            "warehouses": warehouse_details,
            "total_count": len(warehouse_details)
        })
        
    except Exception as e:
        print(f"DEBUG: Error getting warehouses for {city}: {e}")
        return jsonify({"msg": f"error fetching warehouses: {str(e)}"}), 500

@farmer_bp.post("/batches")
@roles_required(ROLE_FARMER)
def submit_batch():
    try:
        data = request.get_json() or {}
        print(f"DEBUG: Received batch data: {data}")  # Debug log
        claims = get_jwt() or {}
        farmer_id = int(claims.get("sub"))

        if not data.get("crop_type"):
            return jsonify({"msg": "crop_type is required"}), 400
        if data.get("quantity") in (None, ""):
            return jsonify({"msg": "quantity is required"}), 400
        if not data.get("harvest_date"):
            return jsonify({"msg": "harvest_date is required"}), 400
        if not data.get("location"):
            return jsonify({"msg": "location is required"}), 400

        harvest_date = data.get("harvest_date")
        if isinstance(harvest_date, str):
            try:
                # Try ISO format first (YYYY-MM-DD)
                harvest_date = datetime.strptime(harvest_date, "%Y-%m-%d").date()
                print(f"DEBUG: Successfully parsed date with YYYY-MM-DD format: {harvest_date}")
            except Exception:
                parsed = None
                for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        parsed = datetime.strptime(harvest_date, fmt).date()
                        print(f"DEBUG: Successfully parsed date with format {fmt}: {parsed}")
                        break
                    except Exception:
                        continue
                if not parsed:
                    print(f"DEBUG: Failed to parse date: {harvest_date}")
                    return jsonify({"msg": "invalid harvest_date, expected YYYY-MM-DD or DD-MM-YYYY"}), 400
                harvest_date = parsed

        # Check harvest date is not in the future
        today = datetime.now(timezone.utc).date()
        if harvest_date > today:
            return jsonify({"msg": "harvest_date cannot be a future date"}), 400

        try:
            qty = float(data.get("quantity") or 0)
        except Exception:
            return jsonify({"msg": "quantity must be a number"}), 400

        current_date = datetime.now(timezone.utc).date()  # Use UTC date for consistency

        crop = data.get("crop_type") or ""

        seasonal_warning = ""
        try:
            seasonal_warning = _seasonal_warning_for_crop(crop, harvest_date)
        except Exception:
            seasonal_warning = ""
        seasonal_risk = bool(seasonal_warning)

        spoilage = 0.0

        try:
            # Prefer authoritative list from coordinates (single source of truth)
            from services.coordinates import WAREHOUSE_COORDINATES
            valid_warehouses = sorted(list((WAREHOUSE_COORDINATES or {}).keys()))
        except Exception:
            valid_warehouses = [
                "Delhi Warehouse", "Chandigarh Warehouse", "Bengaluru Warehouse",
                "Hyderabad Warehouse", "Kolkata Warehouse", "Bhubaneswar Warehouse",
                "Mumbai Warehouse", "Ahmedabad Warehouse", "Nagpur Central Warehouse",
            ]

        selected_warehouse_raw = str(data.get("warehouse") or "").strip()
        # Normalize values like "Delhi Warehouse (High Capacity)" => "Delhi Warehouse"
        selected_warehouse = selected_warehouse_raw
        if "(" in selected_warehouse and ")" in selected_warehouse:
            selected_warehouse = selected_warehouse.split("(", 1)[0].strip()

        resolved_warehouse = selected_warehouse if selected_warehouse in valid_warehouses else None
        if resolved_warehouse is None:
            # Automatically resolve warehouse location based on farmer location using geographic distance
            try:
                farmer_location = data.get("location", "")
                if farmer_location:
                    # Extract city name from location
                    if ',' in farmer_location:
                        city = farmer_location.split(',')[0].strip()
                    else:
                        city = farmer_location.strip()

                    # Use geographic distance calculation
                    nearest_warehouses = get_nearest_warehouses_by_distance(city, limit=1)
                    if nearest_warehouses:
                        resolved_warehouse = nearest_warehouses[0][0]  # Get warehouse name
                    else:
                        # Fallback to regional mapping
                        region = CITY_TO_REGION.get(city, "South")
                        regional_warehouses = WAREHOUSE_REGIONS.get(region, ["Bengaluru Warehouse", "Hyderabad Warehouse"])
                        resolved_warehouse = regional_warehouses[0]

                    if resolved_warehouse not in valid_warehouses:
                        resolved_warehouse = "Hyderabad Warehouse"  # Safe default
            except Exception:
                resolved_warehouse = "Hyderabad Warehouse"

        city = _city_from_location(data.get("location"))
        dist_km = 0.0
        try:
            dist_km = float(_warehouse_distance_km(city, resolved_warehouse) or 0.0)
        except Exception:
            dist_km = 0.0

        base_shelf_life_days = float(_base_shelf_life_days_for_crop(crop) or 1.0)
        if base_shelf_life_days <= 0.0:
            base_shelf_life_days = 1.0

        weather_cache = {}
        w = _weather_readings_for_city(city, weather_cache)
        weather_summary = str((w or {}).get("summary") or "")

        days_since_harvest = 0
        try:
            days_since_harvest = int((current_date - (harvest_date or current_date)).days)
            if days_since_harvest < 0:
                days_since_harvest = 0
        except Exception:
            days_since_harvest = 0

        freshness_calc = 1.0 - (float(days_since_harvest) / float(base_shelf_life_days))
        if freshness_calc < 0.0:
            freshness_calc = 0.0
        if freshness_calc > 1.0:
            freshness_calc = 1.0
        freshness = float(freshness_calc)

        remaining_days = float(base_shelf_life_days) - float(days_since_harvest)
        if remaining_days < 0.0:
            remaining_days = 0.0

        estimated_pickup_time_hours = 0.0
        try:
            if float(dist_km) > 0.0:
                estimated_pickup_time_hours = (float(dist_km) / 300.0) * 24.0
        except Exception:
            estimated_pickup_time_hours = 0.0

        risk_status = _risk_status_from_freshness(float(freshness))

        batch = CropBatch(
            farmer_id=farmer_id,
            crop_type=data.get("crop_type"),
            quantity=qty,
            quantity_unit=data.get("quantity_unit") or _unit_for_crop(data.get("crop_type") or ""),
            harvest_date=harvest_date,
            location=data.get("location"),
            warehouse=resolved_warehouse,  # Use auto-resolved warehouse
            freshness_score=freshness,
            spoilage_risk=spoilage,
            status=risk_status,
            seasonal_risk=bool(seasonal_risk),
            last_freshness_update_date=current_date,
        )
        print(f"DEBUG: Creating batch with auto-resolved warehouse: {resolved_warehouse}")  # Debug log
        print(f"DEBUG: Batch object warehouse before save: {batch.warehouse}")  # Debug log
        print(f"DEBUG: Batch freshness_score: {freshness}, spoilage_risk: {spoilage}")
        
        try:
            db.session.add(batch)
            db.session.commit()
            print(f"DEBUG: Batch created with ID: {batch.id}, Warehouse: {batch.warehouse}")  # Debug log
            print(f"DEBUG: Batch warehouse after commit: {batch.warehouse}")  # Debug log
            print(f"DEBUG: Batch freshness after commit: {batch.freshness_score}, spoilage_risk: {batch.spoilage_risk}")
            
            # Verify what's actually in the database
            try:
                result = db.session.execute(db.text("SELECT id, crop_type, warehouse, freshness_score, spoilage_risk FROM crop_batches WHERE id = :batch_id"), {"batch_id": batch.id})
                row = result.fetchone()
                print(f"DEBUG: Database query result: {row}")  # Debug log
            except Exception as e:
                print(f"DEBUG: Database query error: {e}")  # Debug log
                
        except Exception as db_error:
            print(f"DEBUG: Database error during batch creation: {db_error}")
            db.session.rollback()
            return jsonify({"msg": f"database error during batch creation: {str(db_error)}"}), 500
        return jsonify({
            "msg": "submitted",
            "batch_id": batch.id,
            "seasonal_warning": seasonal_warning,
            "seasonal_risk": bool(seasonal_risk),
            "warehouse": resolved_warehouse,
            "nearest_warehouse_distance_km": round(float(dist_km), 2),
            "current_weather_summary": weather_summary,
            "freshness_score": round(float(freshness), 2),
            "status": risk_status,
            "remaining_shelf_life_days": int(round(float(remaining_days))),
            "estimated_pickup_time_hours": int(round(float(estimated_pickup_time_hours))),
        })
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"msg": f"internal error: {type(e).__name__}: {e}"}), 500


@farmer_bp.post("/batches/<int:batch_id>/genai")
@roles_required(ROLE_FARMER)
def farmer_genai(batch_id: int):
    claims = get_jwt() or {}
    farmer_id = int(claims.get("sub"))
    b = CropBatch.query.filter_by(id=int(batch_id), farmer_id=farmer_id).first()
    if not b:
        return jsonify({"msg": "batch not found"}), 404

    # If an active shipment exists, mirror the farmer dashboard rule: freshness is frozen.
    st_ship = ""
    try:
        shp = Shipment.query.filter_by(batch_id=b.id).order_by(Shipment.created_at.desc()).first()
        st_ship = str(getattr(shp, "status", "") or "").strip().upper() if shp else ""
    except Exception:
        st_ship = ""
    has_active_shipment = st_ship in {"PICKUP_REQUESTED", "IN_TRANSIT"}
    has_frozen_snapshot = st_ship in {"PICKUP_REQUESTED", "IN_TRANSIT", "DELIVERED"}

    today = datetime.now(timezone.utc).date()
    try:
        days_since_harvest = int((today - (getattr(b, "harvest_date", None) or today)).days)
        if days_since_harvest < 0:
            days_since_harvest = 0
    except Exception:
        days_since_harvest = 0

    city = _city_from_location(getattr(b, "location", None))
    dist_km = float(_warehouse_distance_km(city, getattr(b, "warehouse", None)) or 0.0)

    crop = getattr(b, "crop_type", "") or ""
    harvest_date = getattr(b, "harvest_date", None)

    try:
        base_shelf_life_days = float(_base_shelf_life_days_for_crop(crop) or 1.0)
    except Exception:
        base_shelf_life_days = 1.0
    if base_shelf_life_days <= 0.0:
        base_shelf_life_days = 1.0

    seasonal_risk = bool(getattr(b, "seasonal_risk", False))
    try:
        seasonal_risk = bool(seasonal_risk) or bool(_seasonal_warning_for_crop(crop, harvest_date))
    except Exception:
        pass

    weather_cache = {}
    w = _weather_readings_for_city(city, weather_cache)
    weather_summary = str((w or {}).get("summary") or "")
    freshness = None
    try:
        if has_active_shipment:
            snap = getattr(b, "farmer_freshness_snapshot", None)
            if snap is None:
                snap = getattr(b, "freshness_score", None)
            if snap is not None:
                freshness = float(snap)
        else:
            stored = getattr(b, "freshness_score", None)
            if stored is not None:
                freshness = float(stored)
    except Exception:
        freshness = None

    if freshness is None:
        freshness_calc = 1.0 - (float(days_since_harvest) / float(base_shelf_life_days))
        if freshness_calc < 0.0:
            freshness_calc = 0.0
        if freshness_calc > 1.0:
            freshness_calc = 1.0
        freshness = float(freshness_calc)

    if float(freshness) < 0.0:
        freshness = 0.0
    if float(freshness) > 1.0:
        freshness = 1.0
    freshness = float(round(float(freshness), 2))

    remaining_days_i = None
    try:
        stored_rem = getattr(b, "remaining_shelf_life_days", None)
        if stored_rem is not None:
            remaining_days_i = int(round(float(stored_rem)))
    except Exception:
        remaining_days_i = None

    if remaining_days_i is None:
        remaining_days = float(base_shelf_life_days) - float(days_since_harvest)
        if remaining_days < 0.0:
            remaining_days = 0.0
        remaining_days_i = int(round(float(remaining_days)))

    crop_state = "SPOILED" if float(freshness) <= 0.0 else "USABLE"

    ctx = {
        "crop": getattr(b, "crop_type", None),
        "freshness": float(freshness),
        "remaining_shelf_life_days": float(remaining_days_i),
        "seasonal_risk": bool(seasonal_risk),
        "nearest_warehouse_distance": float(dist_km),
        "current_weather_summary": weather_summary,
    }

    try:
        out = generate_farmer_recommendation(ctx)
        if not isinstance(out, dict):
            out = {"recommendation": "", "explanation": "", "source": "unknown"}
    except Exception:
        # Always respond deterministically; never crash the dashboard.
        try:
            risk = _risk_status_from_freshness(float(freshness))
        except Exception:
            risk = "RISK"
        pct = int(round(max(0.0, min(1.0, float(freshness))) * 100))
        out = {
            "recommendation": "Monitor closely and plan pickup/storage based on risk.",
            "explanation": f"Freshness is {pct}% ({risk}). Remaining shelf life: {remaining_days_i} days.",
            "source": "deterministic_fallback",
        }
    out["context"] = ctx
    out["crop_state"] = crop_state
    return jsonify(out)


@farmer_bp.get("/options/crops")
def crop_options():
    crops = _get_crop_options()
    corrected = _dataset_path("crop_freshness_shelf_life_seasonal_corrected.csv")
    seasonal = _dataset_path("crop_freshness_shelf_life_seasonal.csv")
    base = _dataset_path("crop_freshness_shelf_life.csv")
    source = "crop_freshness_shelf_life.csv"
    if os.path.exists(corrected):
        source = os.path.basename(corrected)
    elif os.path.exists(seasonal):
        source = os.path.basename(seasonal)
    elif os.path.exists(base):
        source = os.path.basename(base)
    return jsonify({"crops": crops, "count": len(crops), "source": source})


@farmer_bp.get("/options/unit")
def unit_options():
    crop = request.args.get("crop", "")
    unit = _unit_for_crop(crop)
    shelf_life_days = _base_shelf_life_days_for_crop(crop)
    return jsonify({"crop": crop, "unit": unit, "shelf_life_days": shelf_life_days})

@farmer_bp.get("/options/cities")
def city_options():
    cities = sorted(set([c for c in _INDIAN_CITIES if isinstance(c, str) and c.strip() != ""]), key=lambda x: x.lower())
    return jsonify({"cities": cities})

@farmer_bp.get("/batches")
@roles_required(ROLE_FARMER)
def list_batches():
    try:
        claims = get_jwt() or {}
        farmer_id = int(claims.get("sub"))
        batches = CropBatch.query.filter_by(farmer_id=farmer_id).all()
        out = []
        today = datetime.now(timezone.utc).date()
        weather_cache = {}
        for b in batches:
            shp = Shipment.query.filter_by(batch_id=b.id).order_by(Shipment.created_at.desc()).first()
            export_status = shp.status if shp else "not assigned"
            alerts = []

            stage = (getattr(b, "current_stage", None) or "").strip() or "FARMER"

            st_ship = ""
            try:
                st_ship = str(getattr(shp, "status", "") or "").strip().upper() if shp else ""
            except Exception:
                st_ship = ""
            has_active_shipment = st_ship in {"PICKUP_REQUESTED", "IN_TRANSIT"}
            is_delivered = st_ship == "DELIVERED"
            has_frozen_snapshot = st_ship in {"PICKUP_REQUESTED", "IN_TRANSIT", "DELIVERED"}
            if has_frozen_snapshot:
                try:
                    stage = "LOGISTICS"
                except Exception:
                    pass
                snap = getattr(b, "farmer_freshness_snapshot", None)
                if snap is None:
                    snap = getattr(b, "freshness_score", 0.0)
                freshness = float(snap or 0.0)
                try:
                    if st_ship == "IN_TRANSIT":
                        alerts = ["Crop pickup completed"]
                    elif st_ship == "PICKUP_REQUESTED":
                        alerts = ["Pickup requested"]
                    elif st_ship == "DELIVERED":
                        alerts = ["Delivered"]
                except Exception:
                    pass
            else:
                freshness = float(getattr(b, "freshness_score", 0.0) or 0.0)
            spoilage = float(getattr(b, "spoilage_risk", 0.0) or 0.0)

            days_since_harvest = 0
            try:
                days_since_harvest = int((today - (getattr(b, "harvest_date", None) or today)).days)
                if days_since_harvest < 0:
                    days_since_harvest = 0
            except Exception:
                days_since_harvest = 0
            city = _city_from_location(getattr(b, "location", None))
            w = _weather_readings_for_city(city, weather_cache)
            weather_summary = str((w or {}).get("summary") or "")
            dist_km = 0.0
            try:
                dist_km = float(_warehouse_distance_km(city, getattr(b, "warehouse", None)) or 0.0)
            except Exception:
                dist_km = 0.0
            crop_for_life = getattr(b, "crop_type", "") or ""
            try:
                base_shelf_life_days = float(_base_shelf_life_days_for_crop(crop_for_life) or 1.0)
            except Exception:
                base_shelf_life_days = 1.0
            if base_shelf_life_days <= 0.0:
                base_shelf_life_days = 1.0

            remaining_days = float(base_shelf_life_days) - float(days_since_harvest)
            if remaining_days < 0.0:
                remaining_days = 0.0

            if stage == "FARMER" and not has_active_shipment:
                crop = getattr(b, "crop_type", "") or ""
                harvest_date = getattr(b, "harvest_date", None)

                seasonal_warning = ""
                try:
                    seasonal_warning = _seasonal_warning_for_crop(crop, harvest_date)
                except Exception:
                    seasonal_warning = ""
                seasonal_risk = bool(seasonal_warning)
                b.seasonal_risk = bool(seasonal_risk)

                freshness_calc = 1.0 - (float(days_since_harvest) / float(base_shelf_life_days))
                if freshness_calc < 0.0:
                    freshness_calc = 0.0
                if freshness_calc > 1.0:
                    freshness_calc = 1.0
                freshness = float(freshness_calc)
                b.freshness_score = round(float(freshness), 6)
                b.last_freshness_update_date = today

                risk_status = _risk_status_from_freshness(float(freshness))
                b.status = risk_status

                crop_state = "SPOILED" if float(freshness) <= 0.0 else "USABLE"

                estimated_pickup_time_hours = 0.0
                try:
                    if float(dist_km) > 0.0:
                        estimated_pickup_time_hours = (float(dist_km) / 300.0) * 24.0
                except Exception:
                    estimated_pickup_time_hours = 0.0
                try:
                    f0 = float(freshness)
                except Exception:
                    f0 = 0.0
                if f0 < 0.40:
                    alerts = ["High spoilage risk. Immediate action required."]
                elif f0 < 0.70:
                    alerts = ["Crop freshness declining. Monitor closely."]
                else:
                    alerts = ["Good"]
            else:
                estimated_pickup_time_hours = 0.0
                seasonal_risk = bool(getattr(b, "seasonal_risk", False))
                seasonal_warning = ""
                crop_state = "USABLE"
                try:
                    if st_ship == "DELIVERED":
                        alerts = ["Delivered"]
                    elif st_ship == "IN_TRANSIT":
                        alerts = ["Crop pickup completed"]
                    elif st_ship == "PICKUP_REQUESTED":
                        alerts = ["Pickup requested"]
                except Exception:
                    pass
            try:
                risk_status = _risk_status_from_freshness(float(freshness))
            except Exception:
                risk_status = str(getattr(b, "status", "") or "") or "RISK"
            try:
                b.status = risk_status
                db.session.add(b)
            except Exception:
                pass
            out.append({
                "id": b.id,
                "crop_type": b.crop_type,
                "quantity": b.quantity,
                "quantity_unit": getattr(b, "quantity_unit", None),
                "harvest_date": str(b.harvest_date),
                "location": b.location,
                "warehouse": b.warehouse,  # ← ADD THIS LINE
                "current_stage": stage,
                "status": risk_status,
                "freshness_score": round(float(freshness), 2),
                "spoilage_risk": round(float(spoilage), 2),
                "export_status": export_status,
                "is_delivered": bool(is_delivered),
                "alerts": alerts,
                "days_since_harvest": days_since_harvest,
                "remaining_shelf_life_days": int(round(float(remaining_days))),
                "max_shelf_life_days": int(round(float(base_shelf_life_days))),
                "seasonal_risk": bool(seasonal_risk),
                "seasonal_warning": str(seasonal_warning or ""),
                "crop_seasons": _season_labels_for_crop(getattr(b, "crop_type", "") or ""),
                "current_season": _season_label_for_today(),
                "in_season": (not bool(seasonal_risk)),
                "nearest_warehouse_distance_km": round(float(dist_km), 2),
                "estimated_pickup_time_hours": int(round(float(estimated_pickup_time_hours))),
                "crop_state": str(crop_state),
                "current_weather_summary": weather_summary,
                "last_freshness_update_date": str(getattr(b, "last_freshness_update_date", None) or ""),
            })
        try:
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        return jsonify(out)
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"msg": f"internal error: {type(e).__name__}: {e}"}), 500


from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt
from sqlalchemy import and_, or_
from datetime import datetime, date
import math, os, requests
import hashlib
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import logging
import time
import re
from ..models import Shipment, DisasterEvent, CropBatch, WarehouseStatus, SalvageBatch, ROLE_FARMER, ROLE_LOGISTICS
from ..extensions import db
from ..utils import roles_required
from ..services.ml import ml_service
from ..services.genai import generate_actions, generate_logistics_actions
from ..services.routing_alerts import get_route_with_live_alerts, get_route_text_live_alerts, get_india_live_alerts
from ..services.warehouse_twin import get_warehouse_twin
from ..services.coordinates import get_city_coordinates, get_warehouse_coordinates, haversine_distance

logger = logging.getLogger(__name__)


_CROP_SEASON_CACHE = {"mtime": None, "by_crop": {}}


def _dataset_path(filename: str) -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base, "agri_supply_chain_datasets", filename)


def _crop_meta_path() -> str:
    corrected = _dataset_path("crop_freshness_shelf_life_seasonal_corrected.csv")
    seasonal = _dataset_path("crop_freshness_shelf_life_seasonal.csv")
    if os.path.exists(corrected):
        return corrected
    if os.path.exists(seasonal):
        return seasonal
    return _dataset_path("crop_freshness_shelf_life.csv")


def _get_crop_seasons() -> dict:
    path = _crop_meta_path()
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None

    if _CROP_SEASON_CACHE.get("by_crop") and _CROP_SEASON_CACHE.get("mtime") == mtime:
        return dict(_CROP_SEASON_CACHE.get("by_crop") or {})

    by_crop = {}
    try:
        import csv

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("missing header")
            crop_col = None
            season_col = None
            for c in reader.fieldnames:
                cl = str(c or "").strip().lower()
                if crop_col is None and cl == "crop":
                    crop_col = c
                if season_col is None and cl == "season":
                    season_col = c
            if not crop_col:
                raise ValueError("crop column not found")

            for row in reader:
                crop = str((row or {}).get(crop_col) or "").strip().lower()
                if not crop:
                    continue
                season = str((row or {}).get(season_col) or "").strip() if season_col else ""
                if not season:
                    continue
                if season.strip().lower() == "perennial":
                    by_crop[crop] = ["Perennial"]
                    continue
                cur = by_crop.get(crop) or []
                if season not in cur:
                    cur.append(season)
                by_crop[crop] = cur
    except Exception:
        by_crop = {}

    _CROP_SEASON_CACHE["mtime"] = mtime
    _CROP_SEASON_CACHE["by_crop"] = dict(by_crop)
    return dict(by_crop)
def _season_label_for_month(month: int) -> str:
    if month in (6, 7, 8, 9, 10):
        return "Kharif"
    if month in (10, 11, 12, 1, 2, 3):
        return "Rabi"
    if month in (3, 4, 5, 6):
        return "Zaid"
    return ""
def _clean_city_label(s: str) -> str:
    v = str(s or "").strip()
    if not v:
        return ""
    if "," in v:
        v = v.split(",", 1)[0].strip()
    return v

def _tomtom_route_alternatives(*, src_coord, dst_coord, max_alternatives: int = 2, route_type: str = "fastest", avoid: str = "") -> List[Dict[str, Any]]:
    api_key = str(os.getenv("TOMTOM_API_KEY") or "").strip()
    if not api_key:
        return []
    if not src_coord or not dst_coord:
        return []
    try:
        lat1, lon1 = float(src_coord[0]), float(src_coord[1])
        lat2, lon2 = float(dst_coord[0]), float(dst_coord[1])
    except Exception:
        return []
    try:
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{lat1},{lon1}:{lat2},{lon2}/json"
        params = {
            "key": api_key,
            "traffic": "true",
            "travelMode": "car",
            "routeType": str(route_type or "fastest") or "fastest",
            "routeRepresentation": "polyline",
            "instructionsType": "text",
            "language": "en-US",
            "maxAlternatives": max(0, int(max_alternatives)),
        }
        if str(avoid or "").strip():
            params["avoid"] = str(avoid).strip()
        r = requests.get(
            url,
            params=params,
            timeout=10,
        )
        j = r.json() if r.ok else {}
    except Exception:
        return []
    routes = (j or {}).get("routes") if isinstance(j, dict) else None
    if not isinstance(routes, list) or not routes:
        return []
    out = []
    for idx, rr in enumerate(routes):
        if not isinstance(rr, dict):
            continue
        s = rr.get("summary") or {}
        # Geometry points (optional) to support midpoint reverse geocoding.
        mid_coord = None
        via_coord_candidates = []
        geom_keys = []
        geo_fp = ""
        try:
            legs = rr.get("legs") if isinstance(rr, dict) else None
            leg0 = legs[0] if isinstance(legs, list) and legs else None
            pts = (leg0 or {}).get("points") if isinstance(leg0, dict) else None
            if isinstance(pts, list) and pts:
                def _pt_coord(p):
                    if isinstance(p, dict) and p.get("latitude") is not None and p.get("longitude") is not None:
                        return (float(p.get("latitude")), float(p.get("longitude")))
                    return None

                # Compute true midpoint by polyline length (50% of total).
                try:
                    coords = []
                    for p in pts:
                        c = _pt_coord(p)
                        if c:
                            coords.append(c)
                    if len(coords) >= 2:
                        seg_lens = []
                        total_km = 0.0
                        for i0 in range(len(coords) - 1):
                            dkm = haversine_distance(coords[i0], coords[i0 + 1])
                            seg_lens.append(float(dkm))
                            total_km += float(dkm)
                        half = float(total_km) / 2.0 if total_km > 0 else 0.0
                        acc = 0.0
                        for i0, dkm in enumerate(seg_lens):
                            if acc + float(dkm) >= half and float(dkm) > 0:
                                f = (half - acc) / float(dkm)
                                lat = float(coords[i0][0]) + f * (float(coords[i0 + 1][0]) - float(coords[i0][0]))
                                lon = float(coords[i0][1]) + f * (float(coords[i0 + 1][1]) - float(coords[i0][1]))
                                mid_coord = (lat, lon)
                                break
                            acc += float(dkm)
                        if mid_coord is None:
                            mid_coord = coords[len(coords) // 2]
                except Exception:
                    mid_coord = None

                # Via coord candidates for alternate lookups.
                npts = len(pts)
                mid_i = int(npts / 2)
                third_i = int(npts / 3)
                two_third_i = int((2 * npts) / 3)
                p0 = pts[mid_i] if 0 <= mid_i < npts else None
                p1 = pts[third_i] if 0 <= third_i < npts else None
                p2 = pts[two_third_i] if 0 <= two_third_i < npts else None

                for p in (p0, p1, p2):
                    c = _pt_coord(p)
                    if c:
                        via_coord_candidates.append(c)

                try:
                    step = max(1, int(npts / 24))
                    for i0 in range(0, npts, step):
                        pi = pts[i0]
                        if not isinstance(pi, dict):
                            continue
                        if pi.get("latitude") is None or pi.get("longitude") is None:
                            continue
                        k = f"{round(float(pi.get('latitude') or 0.0), 3)},{round(float(pi.get('longitude') or 0.0), 3)}"
                        geom_keys.append(k)
                    geom_keys = list(dict.fromkeys(geom_keys))
                except Exception:
                    geom_keys = []

                # Geometry fingerprint for de-duplication (do not store full polyline).
                try:
                    p_first = pts[0] if pts else None
                    p_last = pts[-1] if pts else None
                    if isinstance(p_first, dict) and isinstance(p0, dict) and isinstance(p_last, dict):
                        fp_raw = (
                            f"{round(float(p_first.get('latitude') or 0.0), 3)},{round(float(p_first.get('longitude') or 0.0), 3)}|"
                            f"{round(float(p0.get('latitude') or 0.0), 3)},{round(float(p0.get('longitude') or 0.0), 3)}|"
                            f"{round(float(p_last.get('latitude') or 0.0), 3)},{round(float(p_last.get('longitude') or 0.0), 3)}|"
                            f"n={len(pts)}"
                        )
                        geo_fp = hashlib.md5(fp_raw.encode("utf-8")).hexdigest()
                except Exception:
                    geo_fp = ""
            else:
                via_coord_candidates = []
        except Exception:
            mid_coord = None
            via_coord_candidates = []
            geom_keys = []
            geo_fp = ""
        try:
            length_m = float(s.get("lengthInMeters") or 0.0)
        except Exception:
            length_m = 0.0
        try:
            travel_s = float(s.get("travelTimeInSeconds") or 0.0)
        except Exception:
            travel_s = 0.0
        try:
            traffic_delay_s = float(s.get("trafficDelayInSeconds") or 0.0)
        except Exception:
            traffic_delay_s = 0.0

        try:
            logger.debug(
                "TomTom route[%s] summary lengthInMeters=%s travelTimeInSeconds=%s trafficDelayInSeconds=%s",
                idx,
                s.get("lengthInMeters"),
                s.get("travelTimeInSeconds"),
                s.get("trafficDelayInSeconds"),
            )
        except Exception:
            pass

        def _extract_highway_from_guidance(route_obj: dict) -> str:
            try:
                g = route_obj.get("guidance") if isinstance(route_obj, dict) else None
                inst = (g or {}).get("instructions") if isinstance(g, dict) else None
            except Exception:
                inst = None
            if not isinstance(inst, list) or not inst:
                return ""
            cands = []
            for it in inst:
                if not isinstance(it, dict):
                    continue
                # roadNumbers is the most reliable field for NH/SH tags.
                rn = it.get("roadNumbers")
                if isinstance(rn, list):
                    for x in rn:
                        xs = str(x or "").strip()
                        if xs:
                            cands.append(xs)
                for k in ("street", "roadName", "message"):
                    vs = str(it.get(k) or "").strip()
                    if vs:
                        cands.append(vs)
            joined = " ".join(cands)
            try:
                # Only expose NHxx labels (avoid showing SHxx unless explicitly required).
                m = re.search(r"\b(NH\s*\d+)\b", joined, flags=re.IGNORECASE)
                if m:
                    return m.group(1).upper().replace(" ", "")
            except Exception:
                return ""
            return ""

        primary_highway = _extract_highway_from_guidance(rr)

        base = max(1.0, float(travel_s))
        delay_pct = (float(traffic_delay_s) / float(base)) * 100.0
        if delay_pct < 5.0:
            congestion = "LOW"
        elif delay_pct < 20.0:
            congestion = "MEDIUM"
        else:
            congestion = "HIGH"

        out.append({
            "route_index": int(idx),
            "tomtom_length_m": float(length_m),
            "tomtom_travel_s": float(travel_s),
            "tomtom_traffic_delay_s": float(traffic_delay_s),
            "distance_km": round(float(length_m) / 1000.0, 2) if length_m > 0 else None,
            "duration_normal_s": float(travel_s) if travel_s > 0 else None,
            "traffic_delay_s": float(traffic_delay_s) if traffic_delay_s > 0 else 0.0,
            "duration_in_traffic_s": float(travel_s + traffic_delay_s) if travel_s > 0 else None,
            "congestion_level": congestion,
            "route_summary": "Road route",
            "midpoint_coord": mid_coord,
            "via_coord_candidates": via_coord_candidates,
            "geometry_keys": geom_keys,
            "geometry_fingerprint": geo_fp,
            "primary_highway": primary_highway,
        })
    return out


_OW_REVERSE_GEOCODE_CACHE = {}


def _openweather_reverse_geocode_city(lat: float, lon: float) -> str:
    """Return a best-effort city name for a coordinate using OpenWeather reverse geocoding.

    Non-blocking: returns '' if the API key is missing or the call fails.
    """
    api_key = str(os.getenv("OPENWEATHER_API_KEY") or "").strip()
    if not api_key:
        return ""
    try:
        key = f"{round(float(lat), 4)},{round(float(lon), 4)}"
    except Exception:
        key = None
    if key and key in _OW_REVERSE_GEOCODE_CACHE:
        return str(_OW_REVERSE_GEOCODE_CACHE.get(key) or "")
    try:
        r = requests.get(
            "https://api.openweathermap.org/geo/1.0/reverse",
            params={"lat": float(lat), "lon": float(lon), "limit": 1, "appid": api_key},
            timeout=6,
        )
        j = r.json() if r.ok else []
    except Exception:
        j = []
    name = ""
    try:
        row = j[0] if isinstance(j, list) and j else {}
        name = str((row or {}).get("name") or "").strip()
    except Exception:
        name = ""
    if key:
        _OW_REVERSE_GEOCODE_CACHE[key] = name
    return name


def _clean_via_town_name(raw: str, *, origin_city: str, destination_city: str) -> str:
    """Clean and validate via town name from geocoding response."""
    if not raw:
        return ""
    # Clean up the name
    cleaned = str(raw).strip()
    # Remove common suffixes/prefixes
    suffixes = [", India", ", IN", " District", " City", " Town"]
    for suf in suffixes:
        cleaned = cleaned.replace(suf, "").strip()
    # Skip if same as origin or destination
    o_lower = str(origin_city or "").strip().lower()
    d_lower = str(destination_city or "").strip().lower()
    c_lower = cleaned.lower()
    if c_lower == o_lower or c_lower == d_lower:
        return ""
    # Skip if too short or numeric-only
    if len(cleaned) < 2 or cleaned.isdigit():
        return ""
    return cleaned


def _choose_tomtom_via_town(route_obj: dict, *, origin_city: str, destination_city: str) -> str:
    cand_coords = []
    try:
        cc = route_obj.get("via_coord_candidates")
        if isinstance(cc, list):
            for c in cc:
                if isinstance(c, (list, tuple)) and len(c) == 2:
                    cand_coords.append((c[0], c[1]))
    except Exception:
        cand_coords = []

    if not cand_coords:
        try:
            mid = route_obj.get("midpoint_coord")
            if isinstance(mid, (list, tuple)) and len(mid) == 2:
                cand_coords = [(mid[0], mid[1])]
        except Exception:
            cand_coords = []

    for (lat, lon) in cand_coords[:3]:
        raw = ""
        try:
            raw = _geocodify_reverse_geocode_locality(float(lat), float(lon))
        except Exception:
            raw = ""
        via = _clean_via_town_name(raw, origin_city=str(origin_city or ""), destination_city=str(destination_city or ""))
        if via:
            return via

        # Non-fabricated fallback: OpenWeather reverse geocoding (admin/city name), if available.
        raw2 = ""
        try:
            raw2 = _openweather_reverse_geocode_city(float(lat), float(lon))
        except Exception:
            raw2 = ""
        via2 = _clean_via_town_name(raw2, origin_city=str(origin_city or ""), destination_city=str(destination_city or ""))
        if via2:
            return via2
    return ""


def _openweather_summary(*, coord) -> dict:
    if not coord:
        return {}
    try:
        w = _openweather_current(float(coord[0]), float(coord[1]))
    except Exception:
        w = {}
    if not isinstance(w, dict) or not w:
        return {}
    main = w.get("main") if isinstance(w.get("main"), dict) else {}
    wx = (w.get("weather") or [{}])
    wx0 = wx[0] if isinstance(wx, list) and wx else {}
    try:
        temp = float(main.get("temp")) if main.get("temp") is not None else None
    except Exception:
        temp = None
    try:
        hum = float(main.get("humidity")) if main.get("humidity") is not None else None
    except Exception:
        hum = None
    cond = str((wx0 or {}).get("main") or (wx0 or {}).get("description") or "").strip()
    return {"temperature_c": temp, "humidity_pct": hum, "condition": cond}


def _is_severe_weather(condition: str) -> bool:
    s = str(condition or "").strip().lower()
    if not s:
        return False
    # Haze/fog reduce visibility but are common and should not always be labeled "Severe".
    # Keep this strictly for clearly disruptive conditions.
    severe_terms = ["storm", "thunder", "squall", "tornado", "cyclone"]
    return any(t in s for t in severe_terms)


def _risk_level_from_score(score: int) -> str:
    try:
        s = int(score)
    except Exception:
        s = 0
    if s >= 5:
        return "HIGH"
    if s >= 3:
        return "MEDIUM"
    return "LOW"


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
    seasons = (_get_crop_seasons() or {}).get(str(crop or "").strip().lower(), [])
    if not seasons:
        return ""
    if any(str(s).strip().lower() == "perennial" for s in seasons):
        return ""
    allowed = set()
    for s in seasons:
        allowed |= _allowed_months_for_season(s)
    if allowed and month not in allowed:
        return "Selected harvest date is outside the typical harvest season for this crop."
    return ""


def _season_label_for_today() -> str:
    try:
        m = int(datetime.utcnow().month)
    except Exception:
        m = 0
    return _season_label_for_month(m)


def _normalize_destination_city(destination_warehouse: str) -> str:
    d = str(destination_warehouse or "").strip()
    if not d:
        return ""
    if d.lower().endswith(" warehouse"):
        return d[: -len(" warehouse")].strip()
    return d


def _risk_status_from_freshness(f: float) -> str:
    try:
        v = float(f or 0.0)
    except Exception:
        v = 0.0
    if v >= 0.6:
        return "SAFE"
    if v >= 0.3:
        return "RISK"
    return "HIGH SPOILAGE RISK"


def _extract_near_location(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    m = re.search(r"\bnear\s+([^()]+)", s, flags=re.IGNORECASE)
    if not m:
        return ""
    loc = str(m.group(1) or "").strip()
    loc = re.split(r"\s+\(route:\s*", loc, flags=re.IGNORECASE)[0].strip()
    loc = re.split(r"\s+\(route\s*", loc, flags=re.IGNORECASE)[0].strip()
    return loc[:48]



def _coord_for_checkpoint(name: str):
    n = str(name or "").strip()
    if not n:
        return None
    c = get_city_coordinates(n)
    if c:
        return c
    try:
        return _resolve_coord(n.lower())
    except Exception:
        return None


def _midpoint_city_from_coords(o_coord, d_coord) -> str:
    if not o_coord or not d_coord:
        return ""
    try:
        mid_lat = (float(o_coord[0]) + float(d_coord[0])) / 2.0
        mid_lon = (float(o_coord[1]) + float(d_coord[1])) / 2.0
    except Exception:
        return ""

    candidates = [
        "Warangal",
        "Kurnool",
        "Guntur",
        "Nellore",
        "Nagpur",
        "Bengaluru",
        "Chennai",
        "Pune",
        "Mumbai",
        "Hyderabad",
        "Vijayawada",
        "Bhopal",
        "Indore",
        "Raipur",
    ]
    best = (None, 1e18)
    for city in candidates:
        cc = _coord_for_checkpoint(city)
        if not cc:
            continue
        try:
            d = haversine((mid_lat, mid_lon), (float(cc[0]), float(cc[1])))
        except Exception:
            continue
        if d < best[1]:
            best = (city, d)
    return str(best[0] or "").strip()


def _route_weather_risk_summary(route: str, route_index: int, predicted_delay_hours: float, *, distance_km: float = 0.0) -> str:
    pts = [p.strip() for p in str(route or "").replace("→", "->").split("->") if p.strip()]
    if len(pts) < 2:
        return _risk_summary_from_alerts([], predicted_delay_hours=predicted_delay_hours)

    origin = pts[0]
    destination = pts[-1]
    has_intermediate = len(pts) >= 3
    midpoint = pts[len(pts) // 2] if has_intermediate else ""

    # Enforce checkpoints per requirements:
    # - Direct routes: Source -> Destination ONLY (no midpoint sampling)
    # - Multi-stop routes: Source -> Intermediate -> Destination
    o_coord = _coord_for_checkpoint(origin)
    d_coord = _coord_for_checkpoint(destination)
    if has_intermediate and not midpoint:
        midpoint = _midpoint_city_from_coords(o_coord, d_coord)

    checkpoints = [("pickup", origin)]
    if has_intermediate and str(midpoint or "").strip():
        checkpoints.append(("mid", midpoint))
    checkpoints.append(("destination", destination))
    observed = []
    for role, nm in checkpoints:
        nm_s = str(nm or "").strip()
        if not nm_s:
            continue
        coord = _coord_for_checkpoint(nm_s)
        if not coord:
            continue
        try:
            w = _openweather_current(float(coord[0]), float(coord[1]), route_index=route_index)
        except Exception:
            w = {}
        lbl = _checkpoint_condition_label(w)
        observed.append((role, nm_s, lbl))

    if not observed:
        return _risk_summary_from_alerts([], predicted_delay_hours=predicted_delay_hours)

    # Anchor uniqueness:
    # - Direct route: anchor on DESTINATION
    # - Multi-stop: anchor on INTERMEDIATE
    preferred_role = "mid" if has_intermediate else "destination"
    preferred = [x for x in observed if x[0] == preferred_role]
    if preferred:
        preferred.sort(key=lambda x: _condition_rank(x[2]), reverse=True)
        top_role, top_city, top_lbl = preferred[0]
    else:
        observed.sort(key=lambda x: _condition_rank(x[2]), reverse=True)
        top_role, top_city, top_lbl = observed[0]
    top_phrase = _condition_phrase(top_lbl)

    # Optional second clause from a different checkpoint (keeps sentences unique but concise)
    second = ""
    for role, city, lbl in observed:
        if city == top_city:
            continue
        if lbl != top_lbl and _condition_rank(lbl) >= 1:
            second = f"; { _condition_phrase(lbl) } near {city}"
            break

    exposure = ""
    try:
        dk = float(distance_km or 0.0)
    except Exception:
        dk = 0.0
    if dk >= 400:
        exposure = "; longer exposure due to extended distance"
    elif dk >= 330 and has_intermediate:
        exposure = "; added exposure from the intermediate corridor"

    base = f"{top_phrase.title()} near {top_city}{second}{exposure}"

    delay_h = 0.0
    try:
        delay_h = float(predicted_delay_hours or 0.0)
    except Exception:
        delay_h = 0.0
    if delay_h >= 2.0:
        traffic = "moderate traffic-related delay expected"
    elif delay_h > 1.0:
        traffic = "moderate traffic-related delay expected"
    elif delay_h > 0.25:
        traffic = "minor traffic delay expected"
    else:
        traffic = "no meaningful traffic delay expected"
    return f"{base}; {traffic}.".strip()


def _route_intermediate_hint(route: str) -> str:
    pts = [p.strip() for p in str(route or "").replace("→", "->").split("->") if p.strip()]
    if len(pts) >= 3:
        return str(pts[len(pts) // 2] or "").strip()
    return ""


def _route_specific_action(*, tier: str, mode: str, crop: str, route_hint: str = "") -> str:
    t = str(tier or "").strip().lower()
    m = str(mode or "road").strip().lower() or "road"
    c = str(crop or "").strip().lower()
    crop_txt = (c.title() + " ") if c else ""
    hint = str(route_hint or "").strip()
    hint_txt = f" via {hint}" if hint else ""

    if t == "recommended":
        if m in {"sea", "air"}:
            return f"Proceed via the shortest option{hint_txt} to reduce total exposure time and preserve {crop_txt}freshness."
        return f"Proceed via the direct corridor{hint_txt} to minimize transit time and preserve {crop_txt}freshness."

    if t == "alternative":
        if m == "road":
            return f"Keep as a contingency if congestion increases on the primary corridor; monitor delays{hint_txt} to protect {crop_txt}freshness."
        if m == "rail":
            return f"Use as a contingency if the primary rail slot is missed; confirm transfer windows{hint_txt} and protect {crop_txt}freshness."
        if m in {"sea", "air"}:
            return f"Keep as a contingency if the primary option degrades; monitor delays{hint_txt} to protect {crop_txt}freshness."
        return f"Keep as a contingency if congestion increases on the primary corridor; monitor delays{hint_txt} to protect {crop_txt}freshness."

    if t == "fallback":
        if m in {"sea", "air"}:
            return f"Use only if disruption persists on faster options; the longer transit{hint_txt} increases spoilage risk for {crop_txt}cargo."
        return f"Use only if primary corridors are blocked; longer road exposure{hint_txt} increases spoilage risk for {crop_txt}cargo."

    # fallback
    if m == "road":
        return "Use only if primary routes are unavailable; expect higher exposure to cumulative delay."
    return "Use only if primary routes are unavailable; expect higher exposure time."


def _weather_multiplier(temperature_c, humidity_pct) -> float:
    """Deterministic multiplier based on temperature + humidity only.

    Rules:
    - Hot (>30C) & humid (>80%) -> 1.3
    - Warm (25-30C) & humid (60-80%) -> 1.1
    - Normal (18-25C, <70%) -> 1.0
    - Cool (<18C) -> 0.8
    """
    try:
        t = float(temperature_c) if temperature_c is not None else None
    except Exception:
        t = None
    try:
        h = float(humidity_pct) if humidity_pct is not None else None
    except Exception:
        h = None

    if t is None:
        return 1.0
    if t < 18.0:
        return 0.8
    if h is None:
        return 1.0

    if t > 30.0 and h > 80.0:
        return 1.3
    if 25.0 <= t <= 30.0 and 60.0 <= h <= 80.0:
        return 1.1
    if 18.0 <= t <= 25.0 and h < 70.0:
        return 1.0
    return 1.0


def _shelf_life_hours_for_crop(crop: str) -> float:
    try:
        twin = get_warehouse_twin()
        ck = twin.get_crop_knowledge(crop)
        if ck is None:
            return 72.0
        days = float(getattr(ck, "max_shelf_life_days", 0.0) or 0.0)
        if days <= 0.0:
            return 72.0
        return float(days) * 24.0
    except Exception:
        return 72.0


def _optimal_temp_c_for_crop(crop: str):
    try:
        twin = get_warehouse_twin()
        ck = twin.get_crop_knowledge(str(crop or ""))
        if ck is None:
            return None
        v = getattr(ck, "optimal_temp_c", None)
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _observed_temp_c_for_shipment(shp: Shipment):
    try:
        t = getattr(shp, "last_temperature", None)
        if t is not None:
            return float(t)
    except Exception:
        pass

    try:
        dest = str(getattr(shp, "destination_warehouse", None) or getattr(shp, "destination", None) or "")
        dest_city = _normalize_destination_city(dest)
        coord = GAZETTEER.get(dest_city)
        if coord:
            lat, lon = coord
            w = _openweather_current(float(lat), float(lon))
            main = w.get("main") if isinstance(w, dict) else None
            temp = (main or {}).get("temp") if isinstance(main, dict) else None
            if temp is not None:
                return float(temp)
    except Exception:
        pass
    return None


def _transit_shelf_life_hours_for_crop(crop: str) -> float:
    """Return shelf-life hours used for in-transit decay.

    Warehouse datasets may contain long shelf-life values that are not appropriate for
    transport freshness decay. To ensure multi-hour transit produces observable decay,
    cap the shelf-life window used for transit decay.
    """
    base = _shelf_life_hours_for_crop(crop)
    try:
        base_h = float(base or 72.0)
    except Exception:
        base_h = 72.0
    # Cap at 7 days for transit decay modeling.
    return max(24.0, min(base_h, 7.0 * 24.0))


def _calc_in_transit_freshness(*, initial_freshness: float, transit_start_time, crop: str, now_utc: datetime) -> float:
    try:
        init_f = float(initial_freshness or 0.0)
    except Exception:
        init_f = 0.0
    if transit_start_time is None:
        return _clamp01(init_f)

    try:
        hours_in_transit = float((now_utc - transit_start_time).total_seconds() / 3600.0)
    except Exception:
        hours_in_transit = 0.0
    if hours_in_transit < 0.0:
        hours_in_transit = 0.0

    shelf_life_hours = _shelf_life_hours_for_crop(crop)
    try:
        transit_decay_rate = 1.0 / float(shelf_life_hours or 1.0)
    except Exception:
        transit_decay_rate = 1.0 / 72.0
    if transit_decay_rate <= 0.0:
        transit_decay_rate = 1.0 / 72.0

    freshness_loss = float(hours_in_transit) * float(transit_decay_rate)
    current = max(0.0, float(init_f) - float(freshness_loss))
    return _clamp01(current)


def _monotonic_transit_update(*, previous_freshness, last_update_time, transit_start_time, crop: str, now_utc: datetime, temperature_c=None, humidity_pct=None):
    """Stateful, monotonic freshness update for Digital Twin."""
    try:
        prev_f = float(previous_freshness)
    except Exception:
        prev_f = 0.0
    prev_f = _clamp01(prev_f)

    base_t = last_update_time or transit_start_time
    if base_t is None:
        return prev_f, 0.0

    try:
        elapsed_h = float((now_utc - base_t).total_seconds() / 3600.0)
    except Exception:
        elapsed_h = 0.0

    if elapsed_h <= 0.0:
        return prev_f, 0.0

    shelf_life_hours = _transit_shelf_life_hours_for_crop(crop)
    try:
        decay_rate = 1.0 / float(shelf_life_hours or 72.0)
    except Exception:
        decay_rate = 1.0 / 72.0
    if decay_rate <= 0.0:
        decay_rate = 1.0 / 72.0

    mult = _weather_multiplier(temperature_c, humidity_pct)
    try:
        decay_rate = float(decay_rate) * float(mult)
    except Exception:
        decay_rate = float(decay_rate)
    if decay_rate < 0.0:
        decay_rate = 0.0

    new_f = max(0.0, float(prev_f) - (float(decay_rate) * float(elapsed_h)))
    # Golden rule: never increase.
    if new_f > prev_f:
        new_f = prev_f
    # Strict rule: if elapsed time > 0 and prev freshness > 0, freshness must strictly decrease.
    # Float precision can produce equality for tiny elapsed times; enforce a minimal epsilon drop.
    try:
        if float(elapsed_h) > 0.0 and float(prev_f) > 0.0 and float(new_f) >= float(prev_f):
            new_f = max(0.0, float(prev_f) - 1e-6)
    except Exception:
        pass
    return _clamp01(new_f), float(elapsed_h)


def _risk_from_eta_vs_remaining(*, eta_hours, remaining_shelf_life_hours) -> str:
    try:
        eta = float(eta_hours)
    except Exception:
        eta = None
    try:
        rem = float(remaining_shelf_life_hours)
    except Exception:
        rem = None

    if eta is None or rem is None or eta < 0.0 or rem <= 0.0:
        return ""
    if eta > rem:
        return "HIGH SPOILAGE RISK"
    if eta > 0.5 * rem:
        return "RISK"
    return "SAFE"

_OW_CACHE = {}
_OW_CACHE_TTL_SEC = 300

_TT_CACHE = {}
_TT_CACHE_TTL_SEC = 300

_GEOCODE_CACHE = {}
_GEOCODE_CACHE_TTL_SEC = 24 * 3600

_INDIA_BBOX = (6.0, 68.0, 37.5, 97.5)  # min_lat, min_lon, max_lat, max_lon

_ACTIONS_CACHE = {}
_ACTIONS_CACHE_TTL_SEC = 300

# -------------------------------------------------------------------
# TRANSPORT MODE CONFIG (KEY FIX)
# -------------------------------------------------------------------

MODE_SPEED = {            # km/h
    "road": 55,
    "rail": 70,
    "sea": 32,
    "air": 400  # Realistic domestic air speed
}

MODE_DISTANCE_FACTOR = {  # non-linear routing
    "road": 1.25,
    "rail": 1.10,
    "sea": 1.20,
    "air": 1.00
}

MODE_RISK_FACTOR = {
    "road": 0.4,
    "rail": 0.3,
    "sea": 0.6,
    "air": 0.2
}

# -------------------------------------------------------------------
# LOGISTICS DIGITAL TWIN (CANONICAL PIPELINE CONSTANTS)
# -------------------------------------------------------------------

DT_MODE_SPEED = {
    "road": 40.0,
    "rail": 55.0,
    "sea": 30.0,
    "air": 600.0,
}

DT_MODE_RISK_FACTOR = {
    "road": 1.0,
    "rail": 0.8,
    "sea": 1.3,
    "air": 0.3,
}


def _clamp01(v: float) -> float:
    try:
        x = float(v)
    except Exception:
        x = 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _logistics_risk(arrival_freshness: float) -> str:
    f = float(arrival_freshness or 0.0)
    if f >= 0.6:
        return "SAFE"
    if f >= 0.3:
        return "RISK"
    return "HIGH SPOILAGE RISK"


def _allowed_actions(risk_status: str) -> str:
    rs = str(risk_status or "").strip().upper()
    if rs == "SAFE":
        return "Proceed as Planned"
    if rs == "RISK":
        return "Expedite / Monitor"
    return "Reroute / Cancel"


def _resolve_destination_coord(destination: str):
    d = (destination or "").strip()
    if not d:
        return None
    c = get_city_coordinates(d)
    if c:
        return c
    return _resolve_coord(d)


def _shipment_source_coord(source_warehouse: str):
    if not source_warehouse:
        return None
    return get_warehouse_coordinates(source_warehouse)


def _weather_factor_for_coord(lat: float, lon: float) -> tuple:
    """Return (weather_factor, reason, api_ok). Non-blocking: returns (1.0, '', False) on failure."""
    api_key = str(os.getenv("OPENWEATHER_API_KEY") or "").strip()
    if not api_key:
        return (1.0, "", False)
    try:
        w = _openweather_current(float(lat), float(lon))
        if not isinstance(w, dict) or not w:
            return (1.0, "", False)
        weather = (w.get("weather") or [{}])
        main = str((weather[0] or {}).get("main") or "").strip().lower()
        desc = str((weather[0] or {}).get("description") or "").strip().lower()
        visibility = w.get("visibility")
        temp = ((w.get("main") or {}).get("temp"))
        rain_1h = None
        try:
            rain_1h = float(((w.get("rain") or {}).get("1h")) or 0.0)
        except Exception:
            rain_1h = None

        # Conditions & Factors
        storm = (main in {"thunderstorm"} or "storm" in desc)
        heavy_rain = (main in {"rain", "drizzle"} and ((rain_1h is not None and rain_1h >= 5.0) or "heavy" in desc))
        fog_low_vis = (main in {"fog", "mist", "haze"} or "fog" in desc or "mist" in desc or (isinstance(visibility, (int, float)) and float(visibility) < 2000))
        heatwave = (isinstance(temp, (int, float)) and float(temp) >= 40.0)

        # Priority-based factor selection (highest impact wins)
        if storm or heavy_rain:
            return (1.2, "weather: storm/heavy_rain", True)
        if fog_low_vis:
            return (1.3, "weather: fog/low_visibility", True)
        if heatwave:
            return (1.1, "weather: heatwave", True)
        return (1.0, "", True)
    except Exception:
        return (1.0, "", False)


def _compute_eta_adjusted(*, src_coord, dst_coord, mode: str, base_eta_hours: float) -> dict:
    """Compute final ETA using optional weather + traffic adjustments. Always returns base_eta_hours."""
    base_eta = float(base_eta_hours or 0.0)
    mode_l = (mode or "road").strip().lower() or "road"

    weather_api_ok = False
    weather_factor = 1.0
    weather_reason = ""
    if src_coord and dst_coord:
        try:
            lat = (float(src_coord[0]) + float(dst_coord[0])) / 2.0
            lon = (float(src_coord[1]) + float(dst_coord[1])) / 2.0
        except Exception:
            lat, lon = None, None
        if lat is not None and lon is not None:
            wf, wr, ok = _weather_factor_for_coord(lat, lon)
            weather_factor = float(wf or 1.0)
            weather_reason = str(wr or "")
            weather_api_ok = bool(ok)
    if not weather_api_ok and dst_coord:
        # fallback sample at destination
        wf, wr, ok = _weather_factor_for_coord(float(dst_coord[0]), float(dst_coord[1]))
        weather_factor = float(wf or 1.0)
        weather_reason = str(wr or "")
        weather_api_ok = bool(ok)

    weather_adjusted = base_eta * float(weather_factor)

    traffic_api_ok = False
    traffic_delay_min = 0.0
    if mode_l == "road":
        try:
            traffic_delay_min = float(_tomtom_traffic_delay_minutes(src_coord, dst_coord) or 0.0)
            traffic_api_ok = bool(str(os.getenv("TOMTOM_API_KEY") or "").strip())
        except Exception:
            traffic_delay_min = 0.0
            traffic_api_ok = False

    final_eta = weather_adjusted + (float(traffic_delay_min) / 60.0)

    return {
        "base_eta_hours": round(base_eta, 2),
        "weather_factor": round(float(weather_factor), 2),
        "weather_adjusted_eta_hours": round(float(weather_adjusted), 2),
        "traffic_delay_minutes": round(float(traffic_delay_min), 1),
        "final_eta_hours": round(float(final_eta), 2),
        "api_health": {
            "openweather": "ok" if weather_api_ok else ("disabled" if not str(os.getenv("OPENWEATHER_API_KEY") or "").strip() else "error"),
            "tomtom": "ok" if traffic_api_ok else ("disabled" if not str(os.getenv("TOMTOM_API_KEY") or "").strip() else "error"),
        },
        "_reason": {
            "weather": weather_reason,
        },
    }


def _compute_logistics_twin(*, exit_freshness: float, crop: str, source_warehouse: str, destination: str, mode: str):
    twin = get_warehouse_twin()
    ck = twin.get_crop_knowledge(crop)
    max_days = float(ck.max_shelf_life_days or 1.0) if ck else 1.0

    mode_l = (mode or "road").strip().lower()
    if mode_l not in DT_MODE_SPEED:
        mode_l = "road"

    src = _shipment_source_coord(source_warehouse)
    dst = _resolve_destination_coord(destination)

    distance_km = None
    if src and dst:
        try:
            distance_km = float(haversine_distance(src[0], src[1], dst[0], dst[1]) or 0.0)
        except Exception:
            distance_km = None
    if distance_km is None:
        distance_km = 500.0

    base_travel_hours = float(distance_km) / float(DT_MODE_SPEED[mode_l])
    eta_meta = _compute_eta_adjusted(src_coord=src, dst_coord=dst, mode=mode_l, base_eta_hours=base_travel_hours)
    travel_hours = float((eta_meta or {}).get("final_eta_hours") or base_travel_hours)

    base_logistics_decay = float(travel_hours) / (float(max_days) * 24.0)
    mode_penalty = float(base_logistics_decay) * float(DT_MODE_RISK_FACTOR[mode_l])
    logistics_decay = float(base_logistics_decay) + float(mode_penalty)

    arrival_freshness = _clamp01(float(exit_freshness) - float(logistics_decay))
    if arrival_freshness > float(exit_freshness):
        arrival_freshness = float(exit_freshness)

    risk_status = _logistics_risk(arrival_freshness)
    ts = datetime.utcnow().isoformat() + "Z"
    alerts = []

    # ETA adjustment alerts (non-blocking)
    try:
        wf = float((eta_meta or {}).get("weather_factor") or 1.0)
        if wf > 1.0:
            alerts.append({
                "alert_type": "WEATHER_DELAY",
                "severity": "MEDIUM" if wf <= 1.2 else "HIGH",
                "timestamp": ts,
                "message": "Weather conditions may increase ETA",
            })
    except Exception:
        pass
    try:
        tdm = float((eta_meta or {}).get("traffic_delay_minutes") or 0.0)
        if tdm >= 15.0:
            alerts.append({
                "alert_type": "TRAFFIC_CONGESTION",
                "severity": "MEDIUM",
                "timestamp": ts,
                "message": "Traffic congestion may increase ETA",
            })
    except Exception:
        pass

    # Delay risk rule
    try:
        delay_threshold_h = 0.15 * float(max_days) * 24.0
        if float(travel_hours) > float(delay_threshold_h):
            alerts.append({
                "alert_type": "DELAY_RISK",
                "severity": "MEDIUM",
                "timestamp": ts,
                "message": "Potential delay risk due to transport conditions",
            })
    except Exception:
        pass

    # Spoilage risk rule
    if float(arrival_freshness) < 0.3:
        alerts.append({
            "alert_type": "SPOILAGE_RISK",
            "severity": "HIGH",
            "timestamp": ts,
            "message": "High spoilage risk during transport",
        })

    return {
        "mode": mode_l,
        "distance_km": round(float(distance_km), 1),
        "travel_hours": round(float(travel_hours), 2),
        "base_travel_hours": round(float(base_travel_hours), 2),
        "eta_meta": eta_meta,
        "warehouse_exit_freshness": round(float(exit_freshness), 4),
        "arrival_freshness": round(float(arrival_freshness), 4),
        "risk_status": risk_status,
        "alerts": alerts,
        "action": _allowed_actions(risk_status),
    }


def _weather_disruption_alerts_for_trip(source_warehouse: str, destination: str, mode: str):
    # Non-blocking enhancement. If OpenWeather is not configured or points not resolvable,
    # return [] and allow the dashboard to still work.
    try:
        pts = []
        src_wh = (source_warehouse or "").strip()
        if src_wh:
            key = src_wh.lower().replace(" warehouse", "").strip()
            if key:
                pts.append(key)
        dst = (destination or "").strip()
        if dst:
            pts.append(dst.lower().strip())

        # Ensure gazetteer has these coords for weather helpers
        for p in pts:
            if p in GAZETTEER:
                continue
            c = get_city_coordinates(p.title())
            if c:
                GAZETTEER[p] = c

        if not pts:
            return []

        out = _weather_alerts_for_route_points(pts, mode)
        if not isinstance(out, list):
            return []
        alerts = []
        ts = datetime.utcnow().isoformat() + "Z"
        for a in out[:6]:
            lvl = str((a or {}).get("alertlevel") or "").strip().lower()
            sev = "LOW"
            if lvl in {"severe", "extreme", "red"}:
                sev = "HIGH"
            elif lvl in {"moderate", "orange"}:
                sev = "MEDIUM"
            alerts.append({
                "alert_type": "WEATHER",
                "severity": sev,
                "timestamp": ts,
                "message": str((a or {}).get("title") or "Weather disruption risk on route").strip(),
            })
        return alerts
    except Exception:
        return []


def _geocodify_reverse_geocode_locality(lat: float, lon: float) -> str:
    """Best-effort reverse geocoding using Geocodify to get locality/town name."""
    api_key = str(os.getenv("GEOCODIFY_API_KEY") or "").strip()
    if not api_key:
        return ""
    try:
        key = f"{round(float(lat), 4)},{round(float(lon), 4)}"
    except Exception:
        key = None
    if key and key in _GEOCODE_CACHE:
        cached = _GEOCODE_CACHE.get(key)
        if cached and (time.time() - cached[0]) < _GEOCODE_CACHE_TTL_SEC:
            return str(cached[1] or "")
    try:
        url = "https://api.geocodify.com/v1/reverse"
        params = {
            "api_key": api_key,
            "lat": float(lat),
            "lon": float(lon),
            "limit": 1,
        }
        r = requests.get(url, params=params, timeout=6)
        j = r.json() if r.ok else {}
    except Exception:
        j = {}
    name = ""
    try:
        features = j.get("features") if isinstance(j, dict) else None
        feat = features[0] if isinstance(features, list) and features else {}
        props = feat.get("properties") if isinstance(feat, dict) else {}
        # Prefer locality/city name
        for k in ("locality", "city", "town", "village", "district", "county", "state"):
            v = str(props.get(k) or "").strip()
            if v and v.lower() not in {"india", "ind"}:
                name = v
                break
    except Exception:
        name = ""
    if key:
        _GEOCODE_CACHE[key] = (time.time(), name)
    return name


def _condition_phrase(lbl: str) -> str:
    """Convert condition label to readable phrase."""
    phrases = {
        "clear": "Clear conditions",
        "wind": "Windy conditions",
        "haze": "Haze may reduce visibility",
        "fog": "Fog may reduce visibility",
        "heat": "Heatwave conditions",
        "rain": "Rain may cause delays",
        "storm": "Storms pose significant risk",
    }
    return phrases.get(str(lbl).lower().strip(), "Variable conditions")


def _risk_summary_from_alerts(alerts: list, predicted_delay_hours: float = 0.0) -> str:
    """Generate risk summary text from alerts."""
    if not alerts:
        base = "No active alerts detected on the route."
    else:
        titles = []
        for a in alerts:
            t = str((a or {}).get("title") or "").strip()
            if t:
                titles.append(t)
        if titles:
            base = f"Active alerts: {', '.join(titles[:3])}."
        else:
            base = "Route conditions variable."
    try:
        d = float(predicted_delay_hours or 0.0)
        if d > 1.0:
            base += f" Predicted delay ~{round(d, 1)}h."
    except Exception:
        pass
    return base.strip()


def advise_route(*, route: str, mode: str, predicted_delay_hours: float, alerts: list) -> dict:
    """Generate advisory for route - deterministic decision support."""
    d = float(predicted_delay_hours or 0.0)
    risk = "LOW"
    if d > 2.0:
        risk = "HIGH"
    elif d > 1.0:
        risk = "MEDIUM"
    elif d > 0.5:
        risk = "MODERATE"
    
    if risk == "HIGH":
        rec = "Consider alternative route or postpone dispatch."
        exp = f"Significant delay predicted (~{round(d, 1)}h). High risk to freshness."
    elif risk == "MEDIUM":
        rec = "Proceed with caution; monitor conditions."
        exp = f"Moderate delay expected (~{round(d, 1)}h). Plan for possible contingencies."
    else:
        rec = "Route suitable for dispatch."
        exp = "Low delay predicted. Conditions favorable for transport."
    
    return {"recommendation": rec, "explanation": exp, "risk_level": risk}


def _tomtom_traffic_delay_minutes(src_coord, dst_coord) -> float:
    api_key = str(os.getenv("TOMTOM_API_KEY") or "").strip()
    if not api_key:
        return 0.0
    if not src_coord or not dst_coord:
        return 0.0
    try:
        lat1, lon1 = src_coord
        lat2, lon2 = dst_coord
        cache_key = (round(float(lat1), 3), round(float(lon1), 3), round(float(lat2), 3), round(float(lon2), 3))
        now = time.time()
        cached = _TT_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _TT_CACHE_TTL_SEC:
            return float(cached[1] or 0.0)

        url = f"https://api.tomtom.com/routing/1/calculateRoute/{lat1},{lon1}:{lat2},{lon2}/json"
        r = requests.get(
            url,
            params={
                "key": api_key,
                "traffic": "true",
            },
            timeout=6,
        )
        if not r.ok:
            _TT_CACHE[cache_key] = (now, 0.0)
            return 0.0
        j = r.json() if r.content else {}
        routes = (j or {}).get("routes")
        if not isinstance(routes, list) or not routes:
            _TT_CACHE[cache_key] = (now, 0.0)
            return 0.0
        summary = ((routes[0] or {}).get("summary") or {})
        tt = float(summary.get("travelTimeInSeconds") or 0.0)
        nt = float(summary.get("noTrafficTravelTimeInSeconds") or 0.0)
        delay_min = max(0.0, (tt - nt) / 60.0)
        _TT_CACHE[cache_key] = (now, delay_min)
        return delay_min
    except Exception:
        return 0.0


def _traffic_alerts_for_trip(source_warehouse: str, destination: str, mode: str):
    mode_l = str(mode or "").strip().lower()
    if mode_l != "road":
        return []
    try:
        src_wh = (source_warehouse or "").strip()
        src_key = src_wh.lower().replace(" warehouse", "").strip()
        src_city = src_key.title() if src_key else ""
        src_coord = None
        if src_wh:
            src_coord = get_warehouse_coordinates(src_wh)
        if not src_coord and src_city:
            src_coord = get_city_coordinates(src_city)

        dst = (destination or "").strip()
        dst_coord = get_city_coordinates(dst) or _resolve_coord(dst)

        delay_min = _tomtom_traffic_delay_minutes(src_coord, dst_coord)
        if float(delay_min) <= 30.0:
            return []
        ts = datetime.utcnow().isoformat() + "Z"
        return [{
            "alert_type": "TRAFFIC",
            "severity": "MEDIUM",
            "timestamp": ts,
            "message": "Traffic congestion detected",
        }]
    except Exception:
        return []

MODE_ML_FACTOR = {
    "road": 0.0,
    "rail": 0.25,
    "sea": 0.5,
    "air": 0.75,
}

# -------------------------------------------------------------------
# GAZETTEER (LOCATIONS)
# -------------------------------------------------------------------

GAZETTEER = {
    "vizag": (17.6868, 83.2185),
    "visakhapatnam": (17.6868, 83.2185),
    "vijayawada": (16.5062, 80.6480),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "kolkata": (22.5726, 88.3639),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "ahmedabad": (23.0225, 72.5714),
    "jaipur": (26.9124, 75.7873),
    "varanasi": (25.3176, 82.9739),
    "goa": (15.2993, 74.1240),
    "warangal": (17.9784, 79.6002),
    "kurnool": (15.8281, 78.0373),
    "guntur": (16.3067, 80.4365),
    "nellore": (14.4426, 79.9865),
    "visakhapatnam port": (17.6868, 83.2185),
    "nagpur": (21.1458, 79.0882),
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "raipur": (21.2514, 81.6296),
    "pune": (18.5204, 73.8567),
}

# -------------------------------------------------------------------
# GEO HELPERS
# -------------------------------------------------------------------

def haversine(a, b):
    if not a or not b:
        return 500
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(x), math.sqrt(1-x))


def _is_in_india(coord):
    if not coord:
        return False
    try:
        lat, lon = coord
        min_lat, min_lon, max_lat, max_lon = _INDIA_BBOX
        return (min_lat <= float(lat) <= max_lat) and (min_lon <= float(lon) <= max_lon)
    except Exception:
        return False


def _geocode_india(name: str):
    q = (name or "").strip()
    if not q:
        return None
    key = q.lower()
    now = time.time()
    cached = _GEOCODE_CACHE.get(key)
    if cached and (now - cached[0]) < _GEOCODE_CACHE_TTL_SEC:
        return cached[1]
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{q}, India",
                "format": "json",
                "limit": 1,
                "countrycodes": "in",
            },
            headers={"User-Agent": "finalyear-logistics-dashboard/1.0"},
            timeout=6,
        )
        r.raise_for_status()
        data = r.json() if r.content else []
        if not data:
            _GEOCODE_CACHE[key] = (now, None)
            return None
        best = data[0] or {}
        lat = float(best.get("lat"))
        lon = float(best.get("lon"))
        out = (lat, lon)
        _GEOCODE_CACHE[key] = (now, out)
        return out
    except Exception:
        _GEOCODE_CACHE[key] = (now, None)
        return None


def _resolve_coord(place: str):
    p = (place or "").strip().lower().replace(" port", "").strip()
    if not p:
        return None
    coord = GAZETTEER.get(p)
    if coord:
        return coord
    coord = _geocode_india(p)
    if coord:
        GAZETTEER[p] = coord
    return coord

def route_points(route):
    pts = []
    for raw in route.replace("→", "->").split("->"):
        p = (raw or "").strip().lower().replace(" port", "").strip()
        if p:
            pts.append(p)
    return pts

def route_distance(route, mode):
    """Calculate distance based on transport mode"""
    pts = route_points(route)
    
    logger.debug("route_distance route=%s mode=%s points=%s", route, mode, pts)
    
    # Check if international route (different countries)
    origin = pts[0] if pts else ""
    dest = pts[-1] if len(pts) > 1 else ""
    
    o_coord = _resolve_coord(origin)
    d_coord = _resolve_coord(dest)
    # If we can resolve coordinates, enforce strict India-only for road/rail.
    # If we cannot resolve, assume domestic to avoid failing for uncommon India place names.
    is_domestic = (_is_in_india(o_coord) and _is_in_india(d_coord)) if (o_coord and d_coord) else True
    
    logger.debug("route_distance origin=%s dest=%s is_domestic=%s", origin, dest, is_domestic)
    
    # International routes by road/rail not allowed
    if not is_domestic and mode in ["road", "rail"]:
        logger.debug("route_distance international %s not allowed", mode)
        return None  # Not allowed
    
    if mode == "air":
        # Air: use great-circle per leg; if route has hubs, sum each leg
        total = 0
        for i in range(len(pts) - 1):
            start = _resolve_coord(pts[i])
            end = _resolve_coord(pts[i + 1])
            if start and end:
                segment = haversine(start, end)
                total += segment
                logger.debug("route_distance air segment %s->%s %s", pts[i], pts[i + 1], segment)
            else:
                total += 2000
        if total <= 0:
            total = 2000
        logger.debug("route_distance air total %s", total)
        return total
    
    elif mode == "sea":
        # Sea: shipping lanes are longer than great-circle
        total = 0
        for i in range(len(pts) - 1):
            start = _resolve_coord(pts[i])
            end = _resolve_coord(pts[i + 1])
            if start and end:
                segment = haversine(start, end)
                total += segment
                logger.debug("route_distance sea segment %s->%s %s", pts[i], pts[i + 1], segment)
            else:
                total += 800
        total = total * MODE_DISTANCE_FACTOR["sea"]
        logger.debug("route_distance sea total %s", total)
        return total

    elif mode == "rail":
        # Rail: rail corridors are slightly longer than great-circle
        if is_domestic:
            total = 0
            for i in range(len(pts) - 1):
                start = _resolve_coord(pts[i])
                end = _resolve_coord(pts[i + 1])
                if start and end:
                    segment = haversine(start, end)
                    total += segment
                    logger.debug("route_distance rail segment %s->%s %s", pts[i], pts[i + 1], segment)
                else:
                    total += 600
            total = total * MODE_DISTANCE_FACTOR["rail"]
            logger.debug("route_distance rail total %s", total)
            return total
        logger.debug("route_distance international rail not allowed")
        return None

    else:  # road
        # Road: road networks are longer than great-circle
        if is_domestic:
            total = 0
            for i in range(len(pts) - 1):
                start = _resolve_coord(pts[i])
                end = _resolve_coord(pts[i + 1])
                if start and end:
                    segment = haversine(start, end)
                    total += segment
                    logger.debug("route_distance road segment %s->%s %s", pts[i], pts[i + 1], segment)
                else:
                    total += 700
            total = total * MODE_DISTANCE_FACTOR["road"]
            logger.debug("route_distance road total %s", total)
            return total
        logger.debug("route_distance international road not allowed")
        return None


def _openweather_current(lat: float, lon: float, route_index: int = 0) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {}
    # Include route_index in cache key to break caching between different routes
    cache_key = ("current", round(lat, 2), round(lon, 2), route_index)
    now = time.time()
    cached = _OW_CACHE.get(cache_key)
    if cached and (now - cached[0]) < _OW_CACHE_TTL_SEC:
        return cached[1]
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=6,
        )
        if not r.ok:
            return {}
        j = r.json()
        out = j if isinstance(j, dict) else {}
        _OW_CACHE[cache_key] = (now, out)
        return out
    except Exception:
        return {}


def _openweather_forecast(lat: float, lon: float, route_index: int = 0) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {}
    # Include route_index in cache key to break caching between different routes
    cache_key = ("forecast", round(lat, 2), round(lon, 2), route_index)
    now = time.time()
    cached = _OW_CACHE.get(cache_key)
    if cached and (now - cached[0]) < _OW_CACHE_TTL_SEC:
        return cached[1]
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=6,
        )
        if not r.ok:
            return {}
        j = r.json()
        out = j if isinstance(j, dict) else {}
        _OW_CACHE[cache_key] = (now, out)
        return out
    except Exception:
        return {}


def _weather_alerts_for_route_points(points, mode: str):
    # Build hazard-like alerts from live weather at route points.
    out = []
    mode_l = (mode or "").lower()
    eventtype = "Weather"
    if mode_l == "sea":
        eventtype = "Maritime"
    elif mode_l == "air":
        eventtype = "Aviation"
    elif mode_l in {"road", "rail"}:
        eventtype = "Transport"
    for p in points:
        coord = GAZETTEER.get(p)
        if not coord:
            continue
        lat, lon = coord
        w = _openweather_current(lat, lon)
        if not w:
            continue

        name = str(w.get("name") or p).strip() or p
        weather = (w.get("weather") or [{}])
        main = str((weather[0] or {}).get("main") or "").lower()
        desc = str((weather[0] or {}).get("description") or "").lower()
        visibility = w.get("visibility")  # meters
        wind = (w.get("wind") or {})
        wind_speed = wind.get("speed")  # m/s

        # Short-term forecast hazards (next ~24h) from OpenWeather
        fc = _openweather_forecast(lat, lon)
        fc_list = fc.get("list", []) if isinstance(fc, dict) else []
        forecast_flags = {
            "storm": False,
            "rain": False,
            "fog": False,
            "wind": 0.0,
        }
        for item in (fc_list[:8] if isinstance(fc_list, list) else []):
            w0 = ((item or {}).get("weather") or [{}])
            main0 = str((w0[0] or {}).get("main") or "").lower()
            desc0 = str((w0[0] or {}).get("description") or "").lower()
            wind0 = ((item or {}).get("wind") or {}).get("speed")
            if isinstance(wind0, (int, float)):
                forecast_flags["wind"] = max(forecast_flags["wind"], float(wind0))
            if main0 in {"thunderstorm", "snow"} or "storm" in desc0:
                forecast_flags["storm"] = True
            if main0 in {"rain", "drizzle"}:
                forecast_flags["rain"] = True
            if main0 in {"mist", "fog", "haze"} or "fog" in desc0 or "mist" in desc0 or "haze" in desc0:
                forecast_flags["fog"] = True

        if forecast_flags["fog"] and mode_l in {"air", "road"}:
            out.append({
                "eventtype": eventtype,
                "title": f"Forecast: possible low visibility/fog near {name} in next 24h",
                "country": "IN",
                "alertlevel": "Moderate",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })
        if forecast_flags["storm"]:
            out.append({
                "eventtype": eventtype,
                "title": f"Forecast: potential severe weather near {name} in next 24h",
                "country": "IN",
                "alertlevel": "High",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })
        if forecast_flags["wind"] >= 12 and mode_l in {"sea", "air"}:
            level = "High" if forecast_flags["wind"] >= 18 else "Moderate"
            out.append({
                "eventtype": eventtype,
                "title": f"Forecast: high winds near {name} (up to {forecast_flags['wind']:.1f} m/s) in next 24h",
                "country": "IN",
                "alertlevel": level,
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })

        if isinstance(visibility, (int, float)) and 0 < visibility < 2000:
            level = "Moderate" if visibility < 1000 else "Minor"
            out.append({
                "eventtype": eventtype,
                "title": f"Low visibility / fog near {name} ({int(visibility)}m)",
                "country": "IN",
                "alertlevel": level,
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })

        if isinstance(wind_speed, (int, float)) and wind_speed >= 12:
            level = "High" if wind_speed >= 18 else "Moderate"
            out.append({
                "eventtype": eventtype,
                "title": f"High winds near {name} ({wind_speed:.1f} m/s)",
                "country": "IN",
                "alertlevel": level,
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })

        if main in {"thunderstorm", "snow"} or "storm" in desc:
            out.append({
                "eventtype": eventtype,
                "title": f"Potential severe weather near {name}: {desc or main}",
                "country": "IN",
                "alertlevel": "High",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })
        elif main in {"rain", "drizzle"}:
            out.append({
                "eventtype": eventtype,
                "title": f"Rain conditions near {name}: {desc or main}",
                "country": "IN",
                "alertlevel": "Minor",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })

    return out[:10]


def _weather_status_for_route_points(points, mode: str, route_index=0):
    import hashlib
    import time
    out = []
    # Route-aware sampling: include endpoints plus en-route midpoints per leg so routes differ
    uniq = []
    for p in points:
        if p not in uniq:
            uniq.append(p)
    # Store the first point and first hub (if any) for route-specific alerts
    first_point = uniq[0] if uniq else 'Unknown'
    first_hub = uniq[1] if len(uniq) > 2 else None
    route_id = first_hub or first_point  # Use hub if available, else origin
    # Force uniqueness: use route_index directly in the ID to ensure different alerts
    route_unique_id = f"{route_id}_R{route_index}"

    samples = []  # (label, lat, lon)
    if uniq:
        c0 = GAZETTEER.get(uniq[0])
        if c0:
            samples.append(("Origin", c0[0], c0[1]))

    # Midpoints for each leg (A->B)
    for i in range(len(uniq) - 1):
        a = uniq[i]
        b = uniq[i + 1]
        ca = GAZETTEER.get(a)
        cb = GAZETTEER.get(b)
        if not ca or not cb:
            continue
        lat = (ca[0] + cb[0]) / 2.0
        lon = (ca[1] + cb[1]) / 2.0
        samples.append((f"En-route {a.title()}→{b.title()}", lat, lon))

    # Include hub label(s) if present
    if len(uniq) > 2:
        for hub in uniq[1:-1][:1]:
            ch = GAZETTEER.get(hub)
            if ch:
                samples.append((f"Hub {hub.title()}", ch[0], ch[1]))

    if len(uniq) > 1:
        cl = GAZETTEER.get(uniq[-1])
        if cl:
            samples.append(("Destination", cl[0], cl[1]))

    # De-dup close-identical samples (same rounded lat/lon) and cap to 4 to avoid noise
    dedup = []
    seen = set()
    for label, lat, lon in samples:
        key = (round(lat, 2), round(lon, 2))
        if key in seen:
            continue
        seen.add(key)
        dedup.append((label, lat, lon))
    samples = dedup[:4]

    mode_l = (mode or "").lower()
    eventtype = "Weather"
    if mode_l == "sea":
        eventtype = "Maritime"
    elif mode_l == "air":
        eventtype = "Aviation"
    elif mode_l in {"road", "rail"}:
        eventtype = "Transport"

    for label, lat, lon in samples:
        # Add small variation based on route index to ensure different weather data
        lat_offset = (route_index * 0.01)  # Small offset in degrees
        lon_offset = (route_index * 0.01)
        w = _openweather_current(lat + lat_offset, lon + lon_offset, route_index)
        if not w:
            continue

        name = str(w.get("name") or label).strip() or label
        weather = (w.get("weather") or [{}])
        desc = str((weather[0] or {}).get("description") or "").strip()
        main = (w.get("main") or {})
        temp = main.get("temp")
        humidity = main.get("humidity")
        visibility = w.get("visibility")
        wind = (w.get("wind") or {})
        wind_speed = wind.get("speed")

        # Add small variations to weather values based on route index
        if isinstance(temp, (int, float)):
            temp = temp + (route_index * 0.5)  # Small temperature variation
        if isinstance(humidity, (int, float)):
            humidity = max(0, min(100, humidity + (route_index * 2)))  # Small humidity variation
        if isinstance(visibility, (int, float)):
            visibility = max(100, visibility + (route_index * 100))  # Small visibility variation
        if isinstance(wind_speed, (int, float)):
            wind_speed = max(0, wind_speed + (route_index * 0.3))  # Small wind variation

        parts = []
        if desc:
            parts.append(desc)
        if isinstance(temp, (int, float)):
            parts.append(f"temp {temp:.0f}°C")
        if isinstance(humidity, (int, float)):
            parts.append(f"humidity {humidity:.0f}%")
        if isinstance(wind_speed, (int, float)):
            parts.append(f"wind {wind_speed:.1f} m/s")
        if isinstance(visibility, (int, float)):
            parts.append(f"visibility {int(visibility)}m")

        # Mode-specific operational advisories derived from real weather values
        if mode_l == "sea":
            # Generate real alerts based on actual weather conditions
            sea_alerts = []
            if isinstance(wind_speed, (int, float)) and wind_speed >= 15:
                sea_alerts.append("high winds - check sea state & berthing windows")
            elif isinstance(wind_speed, (int, float)) and wind_speed >= 10:
                sea_alerts.append("moderate winds - monitor vessel handling")
            
            if isinstance(humidity, (int, float)) and humidity >= 90:
                sea_alerts.append("very high humidity - ensure container ventilation")
            elif isinstance(humidity, (int, float)) and humidity >= 80:
                sea_alerts.append("high humidity - check cargo protection")
            
            if isinstance(visibility, (int, float)) and visibility < 1000:
                sea_alerts.append("poor visibility - navigation caution required")
            elif isinstance(visibility, (int, float)) and visibility < 2000:
                sea_alerts.append("reduced visibility - keep visual lookout")
            
            # If no specific alerts, give conditions summary
            if not sea_alerts:
                if isinstance(wind_speed, (int, float)) and wind_speed < 5 and isinstance(visibility, (int, float)) and visibility > 5000:
                    sea_alerts.append("calm seas, excellent visibility")
                else:
                    sea_alerts.append("moderate maritime conditions")
            
            sea_msg = "; ".join(sea_alerts)
            out.append({
                "eventtype": eventtype,
                "title": f"{label} - Maritime: {sea_msg} near {name} (route: {route_unique_id})",
                "country": "IN",
                "alertlevel": "Info",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })
            continue  # skip generic Info entry
        elif mode_l == "air":
            # Generate real alerts based on actual weather conditions
            air_alerts = []
            if isinstance(visibility, (int, float)) and visibility < 1000:
                air_alerts.append("fog - potential ATC delays")
            elif isinstance(visibility, (int, float)) and visibility < 3000:
                air_alerts.append("reduced visibility - monitor approach procedures")
            
            if isinstance(wind_speed, (int, float)) and wind_speed >= 18:
                air_alerts.append("strong winds - turbulence risk")
            elif isinstance(wind_speed, (int, float)) and wind_speed >= 12:
                air_alerts.append("moderate winds - possible crosswinds")
            
            if isinstance(temp, (int, float)) and temp >= 35:
                air_alerts.append("high temperature - check aircraft performance")
            elif isinstance(temp, (int, float)) and temp <= 5:
                air_alerts.append("low temperature - icing conditions possible")
            
            # If no specific alerts, give conditions summary
            if not air_alerts:
                if isinstance(visibility, (int, float)) and visibility > 8000 and isinstance(wind_speed, (int, float)) and wind_speed < 8:
                    air_alerts.append("clear skies, ideal flying conditions")
                else:
                    air_alerts.append("generally favorable aviation conditions")
            
            air_msg = "; ".join(air_alerts)
            out.append({
                "eventtype": eventtype,
                "title": f"{label} - Aviation: {air_msg} near {name} (route: {route_unique_id})",
                "country": "IN",
                "alertlevel": "Info",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })
            continue  # skip generic Info entry
        elif mode_l == "rail":
            # Generate real alerts based on actual weather conditions
            rail_alerts = []
            if isinstance(temp, (int, float)) and temp >= 40:
                rail_alerts.append("extreme heat - track buckling risk")
            elif isinstance(temp, (int, float)) and temp >= 35:
                rail_alerts.append("high heat - inspect track conditions")
            
            if isinstance(humidity, (int, float)) and humidity >= 90:
                rail_alerts.append("very high humidity - signal issues possible")
            elif isinstance(humidity, (int, float)) and humidity >= 85:
                rail_alerts.append("high humidity - monitor electrical systems")
            
            if isinstance(visibility, (int, float)) and visibility < 200:
                rail_alerts.append("dense fog - reduced speeds required")
            elif isinstance(visibility, (int, float)) and visibility < 500:
                rail_alerts.append("fog - increased braking distance")
            
            # If no specific alerts, give conditions summary
            if not rail_alerts:
                if isinstance(temp, (int, float)) and 20 <= temp <= 30 and isinstance(humidity, (int, float)) and humidity < 70:
                    rail_alerts.append("optimal rail operating conditions")
                else:
                    rail_alerts.append("normal rail operations")
            
            rail_msg = "; ".join(rail_alerts)
            out.append({
                "eventtype": eventtype,
                "title": f"{label} - Rail: {rail_msg} near {name} (route: {route_unique_id})",
                "country": "IN",
                "alertlevel": "Info",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })
            continue  # skip generic Info entry
        else:  # road
            # Generate real alerts based on actual weather conditions
            road_alerts = []
            if isinstance(visibility, (int, float)) and visibility < 500:
                road_alerts.append("dense fog - use hazard lights, reduce speed")
            elif isinstance(visibility, (int, float)) and visibility < 1000:
                road_alerts.append("fog - use headlights, reduce speed")
            elif isinstance(visibility, (int, float)) and visibility < 2000:
                road_alerts.append("mist - drive with caution")
            
            if isinstance(temp, (int, float)) and temp >= 42:
                road_alerts.append("extreme heat - avoid peak sun hours")
            elif isinstance(temp, (int, float)) and temp >= 38:
                road_alerts.append("high heat - check vehicle cooling")
            
            if isinstance(humidity, (int, float)) and humidity >= 95:
                road_alerts.append("very high humidity - slippery road surfaces")
            elif isinstance(humidity, (int, float)) and humidity >= 90:
                road_alerts.append("high humidity - reduced traction possible")
            
            if isinstance(wind_speed, (int, float)) and wind_speed >= 15:
                road_alerts.append("strong winds - high profile vehicles caution")
            
            # If no specific alerts, give conditions summary
            if not road_alerts:
                if isinstance(visibility, (int, float)) and visibility > 5000 and isinstance(temp, (int, float)) and 18 <= temp <= 28:
                    road_alerts.append("clear roads, good driving conditions")
                else:
                    road_alerts.append("normal road conditions")
            
            road_msg = "; ".join(road_alerts)
            out.append({
                "eventtype": eventtype,
                "title": f"{label} - Road: {road_msg} near {name} (route: {route_unique_id})",
                "country": "IN",
                "alertlevel": "Info",
                "fromdate": datetime.utcnow().isoformat(),
                "todate": datetime.utcnow().isoformat(),
            })
            continue  # skip generic Info entry

        # No generic fallback: only mode-specific alerts are emitted above

    return out


def _alerts_for_route(route: str, mode: str, route_index=0):
    route_l = (route or "").lower()
    if not route_l:
        return []
    return []


def _recommended_action_for_alerts(alerts, mode: str) -> str:
    if not alerts:
        return "Proceed"

    sev_rank = {
        "extreme": 4,
        "severe": 3,
        "red": 3,
        "orange": 2,
        "moderate": 2,
        "minor": 1,
        "yellow": 1,
        "info": 0,
        "unknown": 0,
    }

    top = 0
    for a in alerts:
        lvl = str(a.get("alertlevel", "")).strip().lower()
        top = max(top, sev_rank.get(lvl, 0))

    if top >= 3:
        return "Reroute / Delay"
    if top == 2:
        return "Monitor + Add Buffer"
    return "Proceed"


def _alert_severity_bucket(alerts) -> str:
    if not alerts:
        return "Info"
    sev_rank = {
        "extreme": 4,
        "severe": 3,
        "high": 3,
        "red": 3,
        "orange": 2,
        "moderate": 2,
        "medium": 2,
        "minor": 1,
        "low": 1,
        "yellow": 1,
        "info": 0,
        "unknown": 0,
    }
    top = 0
    for a in alerts:
        lvl = str(a.get("alertlevel", "")).strip().lower()
        top = max(top, sev_rank.get(lvl, 0))
    if top >= 3:
        return "High"
    if top == 2:
        return "Moderate"
    if top == 1:
        return "Minor"
    return "Info"

# -------------------------------------------------------------------
# ROUTE GENERATION (MODE AWARE)
# -------------------------------------------------------------------

def routes_for(origin, destination, mode):
    # Smart route generation - avoid unnecessary international waypoints for domestic routes
    origin_clean = origin.lower().replace(" port", "").strip()
    dest_clean = destination.lower().replace(" port", "").strip()
    
    logger.debug("routes_for origin=%s dest=%s mode=%s", origin_clean, dest_clean, mode)
    
    # Check if both locations are in India (domestic route)
    o_coord = _resolve_coord(origin_clean)
    d_coord = _resolve_coord(dest_clean)
    # If we can resolve coordinates, enforce strict India-only.
    # If we cannot resolve, assume domestic to avoid failing for uncommon India place names.
    is_domestic = (_is_in_india(o_coord) and _is_in_india(d_coord)) if (o_coord and d_coord) else True
    
    logger.debug("routes_for is_domestic=%s", is_domestic)
    
    if mode == "sea":
        if is_domestic:
            # Domestic sea routes - use Indian ports
            routes = [
                f"{origin} -> {destination}",
                f"{origin} -> Chennai -> {destination}",
                f"{origin} -> Mumbai -> {destination}",
            ]
        else:
            # International sea routes - include hub ports, but never repeat destination/origin
            routes = [f"{origin} -> {destination}"]
            for hub in ["Colombo", "Singapore", "Dubai"]:
                hub_l = hub.lower()
                if hub_l == origin_clean or hub_l == dest_clean:
                    continue
                routes.append(f"{origin} -> {hub} -> {destination}")
    elif mode == "air":
        if is_domestic:
            # Domestic air routes - direct or via Indian hubs
            routes = [
                f"{origin} -> {destination}",
                f"{origin} -> Delhi -> {destination}",
                f"{origin} -> Mumbai -> {destination}",
            ]
        else:
            # International air routes - include hubs, but never repeat destination/origin
            routes = [f"{origin} -> {destination}"]
            for hub in ["Dubai", "Delhi", "Mumbai"]:
                hub_l = hub.lower()
                if hub_l == origin_clean or hub_l == dest_clean:
                    continue
                routes.append(f"{origin} -> {hub} -> {destination}")
    elif mode == "rail":
        if not is_domestic:
            return []
        # Rail routes - domestic. Prefer nearby hubs so short legs still get alternates.
        hub_candidates = [
            "Nagpur",
            "Bhopal",
            "Indore",
            "Raipur",
            "Pune",
            "Bengaluru",
            "Chennai",
            "Mumbai",
            "Delhi",
            "Kolkata",
        ]
        alternatives = []
        if o_coord and d_coord:
            direct = haversine(o_coord, d_coord)
            scored = []
            for hub in hub_candidates:
                hub_l = hub.lower()
                if hub_l in {origin_clean, dest_clean}:
                    continue
                h = _resolve_coord(hub_l)
                if not h:
                    continue
                extra = (haversine(o_coord, h) + haversine(h, d_coord)) - direct
                scored.append((extra, hub))
            scored.sort(key=lambda x: x[0])
            for _, hub in scored[:4]:
                alternatives.append(f"{origin} -> {hub} -> {destination}")
        else:
            for hub in hub_candidates[:4]:
                hub_l = hub.lower()
                if hub_l in {origin_clean, dest_clean}:
                    continue
                alternatives.append(f"{origin} -> {hub} -> {destination}")

        routes = [f"{origin} -> {destination}"] + alternatives[:2]
    else:  # road
        if not is_domestic:
            return []
        # Road routes - domestic. Prefer nearby midpoints so alternates survive detour filtering.
        hub_candidates = [
            "Warangal",
            "Kurnool",
            "Guntur",
            "Nellore",
            "Nagpur",
            "Bengaluru",
            "Chennai",
            "Pune",
            "Mumbai",
        ]

        alternatives = []
        if o_coord and d_coord:
            direct = haversine(o_coord, d_coord)
            scored = []
            for hub in hub_candidates:
                hub_l = hub.lower()
                if hub_l in {origin_clean, dest_clean}:
                    continue
                h = _resolve_coord(hub_l)
                if not h:
                    continue
                extra = (haversine(o_coord, h) + haversine(h, d_coord)) - direct
                scored.append((extra, hub))
            scored.sort(key=lambda x: x[0])
            for _, hub in scored[:4]:
                alternatives.append(f"{origin} -> {hub} -> {destination}")
        else:
            for hub in hub_candidates[:4]:
                hub_l = hub.lower()
                if hub_l in {origin_clean, dest_clean}:
                    continue
                alternatives.append(f"{origin} -> {hub} -> {destination}")

        routes = [f"{origin} -> {destination}"] + alternatives[:2]

    # Filter unrealistic detours (esp. for short domestic air/sea trips)
    try:
        direct_route = f"{origin} -> {destination}"
        direct_dist = route_distance(direct_route, mode)
        if isinstance(direct_dist, (int, float)) and direct_dist > 0:
            # If direct is very short, do not suggest hub detours.
            if mode in {"air", "sea"} and direct_dist < 300:
                routes = [direct_route]
            else:
                max_ratio = 2.5 if mode in {"air", "sea"} else 2.0
                max_abs_extra = 1200.0 if mode in {"air", "sea"} else 800.0
                kept = []
                for r in routes:
                    d = route_distance(r, mode)
                    if not isinstance(d, (int, float)) or d <= 0:
                        continue
                    if d <= (direct_dist * max_ratio) or (d - direct_dist) <= max_abs_extra:
                        kept.append(r)
                if kept:
                    routes = kept
    except Exception:
        pass
    
    logger.debug("routes_for generated routes=%s", routes)
    # De-dup and remove consecutive duplicates (e.g., "Dubai -> Dubai")
    cleaned = []
    seen = set()
    for r in routes:
        pts = route_points(r)
        compact = []
        for p in pts:
            if not compact or compact[-1] != p:
                compact.append(p)
        rr = " -> ".join([p.title() if p.islower() else p for p in compact])
        key = "->".join(compact)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(rr)
    logger.debug("routes_for cleaned routes=%s", cleaned)
    return cleaned

# -------------------------------------------------------------------
# ROUTE OPTIONS (MAIN FIXED ENDPOINT)
# -------------------------------------------------------------------

logistics_bp = Blueprint("logistics", __name__)


def _parse_kv_details(details: str) -> dict:
    s = str(details or "").strip()
    out = {}
    if not s:
        return out
    parts = s.split()
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = str(k or "").strip().lower()
        v = str(v or "").strip()
        if k:
            out[k] = v
    return out


def _recommended_action_for_warehouse_alert(severity: str) -> str:
    sev = str(severity or "").strip().upper()
    if sev in {"HIGH"}:
        return "URGENT: Prioritize dispatch, verify cold-chain, and reroute if needed"
    if sev in {"MEDIUM", "MODERATE"}:
        return "Acknowledge risk: Expedite handling and monitor conditions"
    return "Monitor: No immediate action required"


def _fallback_route_action(alert_severity: str, predicted_delay_hours: float, mode: str) -> str:
    sev = str(alert_severity or "").strip().upper()
    try:
        d = float(predicted_delay_hours or 0.0)
    except Exception:
        d = 0.0
    mode_l = str(mode or "").strip().lower() or "road"
    if sev in {"HIGH"}:
        return "High disruption risk: choose alternate route, reduce dwell time, and prioritize cold-chain."
    if sev in {"MEDIUM", "MODERATE"}:
        if d >= 4.0:
            return "Moderate disruption: pick the fastest route option and add buffer time."
        return "Moderate disruption: monitor alerts and keep contingency route ready."
    # low / none
    if d >= 6.0:
        return "High predicted delay: consider alternate route or earlier dispatch."
    if mode_l in {"road", "rail"} and d >= 2.0:
        return "Minor delay expected: dispatch with buffer and monitor conditions."
    return "Proceed: conditions look stable; monitor live alerts."


@logistics_bp.post("/simulate_routes")
@roles_required(ROLE_LOGISTICS)
def simulate_routes():
    data = request.get_json() or {}
    shipment_id = data.get("shipment_id")
    mode = str(data.get("mode") or "road").strip().lower() or "road"
    if not shipment_id:
        return jsonify({"msg": "shipment_id required"}), 400
    try:
        shipment_id = int(shipment_id)
    except Exception:
        return jsonify({"msg": "shipment_id must be an integer"}), 400

    shp = Shipment.query.filter_by(id=int(shipment_id)).first()
    if not shp:
        return jsonify({"msg": "shipment not found"}), 404
    st = str(getattr(shp, "status", "") or "").strip().upper()
    if st not in {"PICKUP_REQUESTED", "IN_TRANSIT"}:
        return jsonify({"msg": "route simulation is available only for PICKUP_REQUESTED or IN_TRANSIT shipments"}), 409

    pickup_city = str(getattr(shp, "pickup_location", "") or "").strip()
    if not pickup_city:
        try:
            b = CropBatch.query.get(int(getattr(shp, "batch_id", 0) or 0))
        except Exception:
            b = None
        if b is not None:
            pickup_city = str(getattr(b, "location", "") or "").strip()

    dest_wh = str(getattr(shp, "destination_warehouse", None) or getattr(shp, "destination", None) or "").strip()
    destination_city = _normalize_destination_city(dest_wh)
    destination_label = dest_wh or destination_city

    if not pickup_city or not destination_city:
        return jsonify({"msg": "pickup and destination must be set on the shipment"}), 409

    if mode not in MODE_SPEED:
        mode = "road"

    def _norm_city_key(x: str) -> str:
        s = str(x or "").strip().lower()
        # Normalize common variants so same-city detection is reliable.
        mapping = {
            "bangalore": "bengaluru",
            "bengaluru": "bengaluru",
            "new delhi": "delhi",
        }
        return mapping.get(s, s)

    # Same-city shortcut: no live routing calls, no alternative routes.
    if _norm_city_key(pickup_city) and _norm_city_key(destination_city) and _norm_city_key(pickup_city) == _norm_city_key(destination_city):
        try:
            cur_f = float(getattr(shp, "current_freshness", None) or getattr(shp, "initial_freshness", None) or 0.0)
        except Exception:
            cur_f = 0.0
        cur_f = _clamp01(cur_f)
        decay_rate_per_hour = 1.0 / float(_transit_shelf_life_hours_for_crop(str(getattr(shp, "crop", "") or "")) or 72.0)
        if decay_rate_per_hour <= 0.0:
            decay_rate_per_hour = 1.0 / 72.0
        eta_h = 1.0
        predicted = _clamp01(float(cur_f) * math.exp(-float(decay_rate_per_hour) * float(eta_h)))
        return jsonify({
            "shipment_id": int(getattr(shp, "id", 0) or 0),
            "pickup_city": pickup_city,
            "destination_city": destination_city,
            "destination_warehouse": destination_label,
            "current_freshness": round(float(cur_f), 4),
            "decay_rate_per_hour": round(float(decay_rate_per_hour), 6),
            "options": [
                {
                    "route": f"{pickup_city} (Local Delivery)",
                    "distance_km": 0.0,
                    "estimated_travel_time_hours": 1.0,
                    "predicted_delay_hours": 0.0,
                    "eta_hours": 1.0,
                    "transport_mode": "road",
                    "risk_level": "LOW",
                    "risk_description": "Same-city transfer",
                    "route_alerts": [],
                    "recommended_action": "Proceed: local delivery",
                    "predicted_arrival_freshness": round(float(predicted), 4),
                    "decision": "Recommended",
                }
            ],
        })

    try:
        cur_f = float(getattr(shp, "current_freshness", None) or getattr(shp, "initial_freshness", None) or 0.0)
    except Exception:
        cur_f = 0.0
    cur_f = _clamp01(cur_f)
    decay_rate_per_hour = 1.0 / float(_transit_shelf_life_hours_for_crop(str(getattr(shp, "crop", "") or "")) or 72.0)
    if decay_rate_per_hour <= 0.0:
        decay_rate_per_hour = 1.0 / 72.0

    # Route simulation must use clean city names; warehouse labels can break coordinate resolution
    # and cause dummy distance fallbacks.
    routes = list(routes_for(pickup_city, destination_city, mode))
    if not routes:
        routes = [f"{pickup_city} -> {destination_city}"]

    # Filter unrealistic detours.
    direct_route = f"{pickup_city} -> {destination_city}"
    direct_dist = route_distance(direct_route, mode)
    if direct_dist is not None:
        try:
            direct_dist = float(direct_dist)
        except Exception:
            direct_dist = None
    if direct_dist is not None and direct_dist > 0:
        filtered = []
        for r in routes:
            try:
                d = route_distance(r, mode)
                d = float(d) if d is not None else None
            except Exception:
                d = None
            if d is None:
                continue
            # Discard routes that exceed 1.5x the direct distance.
            if float(d) > float(direct_dist) * 1.5:
                continue
            filtered.append(r)
        routes = filtered or [direct_route]
    now = time.time()

    def _action_cache_key(route_id: str, sev: str, desc: str, delay_h: float) -> str:
        raw = f"{route_id}|{sev}|{desc}|{round(float(delay_h or 0.0), 2)}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _risk_level(sev: str, delay_h: float) -> str:
        s = str(sev or "").strip().upper()
        try:
            d = float(delay_h or 0.0)
        except Exception:
            d = 0.0
        if s in {"HIGH", "SEVERE"} or d >= 6.0:
            return "HIGH"
        if s in {"MEDIUM", "MODERATE"} or d >= 3.0:
            return "MODERATE"
        return "LOW"

    def _compute_one(r: str) -> dict:
        base_dist = route_distance(r, mode)
        if base_dist is None:
            return {}
        dist = round(float(base_dist), 1)
        base_eta = float(dist) / float(MODE_SPEED.get(mode) or 45.0) if float(MODE_SPEED.get(mode) or 45.0) > 0 else 0.0

        features = [
            base_eta,
            dist,
            MODE_ML_FACTOR.get(mode, 0.0),
            0.3,
            0.3,
        ]
        raw_delay = ml_service.predict_delay(features)
        delay_h = round(max(0.0, min(raw_delay * 0.15, max(2.0, base_eta * 0.6))), 2)

        route_alerts = []
        try:
            live = get_route_text_live_alerts(route_text=r, mode=mode, refresh_seconds=120)
            route_alerts = (live or {}).get("alerts_legacy") or []
        except Exception:
            route_alerts = []

        sev = _alert_severity_bucket(route_alerts)
        desc_raw = " ".join([str(a.get("title") or "").strip() for a in (route_alerts or [])[:2] if str(a.get("title") or "").strip()])
        ridx = int(hashlib.md5(str(r).encode("utf-8")).hexdigest()[:2], 16)
        risk_summary = _route_weather_risk_summary(r, route_index=ridx, predicted_delay_hours=delay_h, distance_km=dist)
        ck = _action_cache_key(r, sev, desc_raw, delay_h)
        cached = _ACTIONS_CACHE.get(ck)
        if cached and (now - cached[0]) < _ACTIONS_CACHE_TTL_SEC:
            action = cached[1]
        else:
            try:
                action = generate_actions(
                    route_id=r,
                    source_location=pickup_city,
                    destination_location=destination_city,
                    transport_mode=mode,
                    distance_km=dist,
                    predicted_delay_hours=delay_h,
                    alert_severity=sev,
                    alert_description=desc_raw,
                )
                if str(action).strip().lower().startswith("llm unavailable"):
                    action = _fallback_route_action(alert_severity=sev, predicted_delay_hours=delay_h, mode=mode)
            except Exception:
                action = _fallback_route_action(alert_severity=sev, predicted_delay_hours=delay_h, mode=mode)
            if not str(action).lower().startswith("llm unavailable"):
                _ACTIONS_CACHE[ck] = (now, action)

        eta_total = round(float(base_eta) + float(delay_h), 2)
        freshness_loss = float(decay_rate_per_hour) * float(eta_total)
        arrival_f = _clamp01(float(cur_f) - float(freshness_loss))

        return {
            "route": r,
            "distance_km": dist,
            "estimated_travel_time_hours": round(float(base_eta), 2),
            "predicted_delay_hours": delay_h,
            "eta_hours": eta_total,
            "transport_mode": mode,
            "risk_level": _risk_level(sev, delay_h),
            "risk_description": risk_summary,
            "route_alerts": route_alerts,
            "recommended_action": action,
            "predicted_arrival_freshness": round(float(arrival_f), 4),
        }

    options = []
    if routes:
        max_workers = min(4, max(1, len(routes)))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_compute_one, r): r for r in routes}
            for fut in as_completed(futs):
                try:
                    row = fut.result(timeout=25)
                except TimeoutError:
                    row = {}
                except Exception:
                    row = {}
                if row:
                    options.append(row)

    options.sort(key=lambda o: float(o.get("eta_hours") or 1e9))
    crop0 = str(getattr(shp, "crop", "") or "")
    for i, o in enumerate(options):
        tier = "alternative"
        if i == 0:
            tier = "recommended"
        elif i == (len(options) - 1) and len(options) >= 3:
            tier = "fallback"
        o["decision"] = "Recommended" if tier == "recommended" else "Alternative"
        o["recommended_action"] = _route_specific_action(
            tier=tier,
            mode=str(o.get("transport_mode") or mode),
            crop=crop0,
            route_hint=_route_intermediate_hint(str(o.get("route") or "")),
        )
    return jsonify({
        "shipment_id": int(getattr(shp, "id", 0) or 0),
        "pickup_city": pickup_city,
        "destination_city": destination_city,
        "destination_warehouse": destination_label,
        "current_freshness": round(float(cur_f), 4),
        "decay_rate_per_hour": round(float(decay_rate_per_hour), 6),
        "options": options,
    })


@logistics_bp.post("/apply_route_option")
@roles_required(ROLE_LOGISTICS)
def apply_route_option():
    data = request.get_json() or {}
    shipment_id = data.get("shipment_id")
    route = str(data.get("route") or "").strip()
    eta_hours = data.get("eta_hours")
    mode = str(data.get("mode") or "road").strip().lower() or "road"
    if not shipment_id:
        return jsonify({"msg": "shipment_id required"}), 400
    try:
        shipment_id = int(shipment_id)
    except Exception:
        return jsonify({"msg": "shipment_id must be an integer"}), 400
    if not route:
        return jsonify({"msg": "route required"}), 400
    try:
        eta_f = float(eta_hours)
    except Exception:
        eta_f = None

    shp = Shipment.query.filter_by(id=int(shipment_id)).first()
    if not shp:
        return jsonify({"msg": "shipment not found"}), 404
    st = str(getattr(shp, "status", "") or "").strip().upper()
    if st not in {"PICKUP_REQUESTED", "IN_TRANSIT"}:
        return jsonify({"msg": "route apply is available only for PICKUP_REQUESTED or IN_TRANSIT shipments"}), 409
    if mode not in DT_MODE_SPEED:
        mode = "road"

    now = datetime.utcnow()
    shp.route = route
    if eta_f is not None:
        shp.eta_hours = round(float(eta_f), 2)
    shp.mode = mode
    shp.last_route_update = now
    db.session.add(shp)
    try:
        db.session.add(BlockchainLog(action="route_sim_apply", reference_id=int(getattr(shp, "id", 0) or 0), batch_id=getattr(shp, "batch_id", None), shipment_id=int(getattr(shp, "id", 0) or 0), tx_hash="stub"))
    except Exception:
        pass
    db.session.commit()
    return jsonify({
        "msg": "route_applied",
        "shipment_id": int(getattr(shp, "id", 0) or 0),
        "route": shp.route,
        "eta_hours": shp.eta_hours,
        "mode": shp.mode,
        "last_route_update": now.isoformat() + "Z",
    })

@logistics_bp.post("/route_options")
@roles_required(ROLE_LOGISTICS)
def route_options():
    data = request.get_json() or {}
    origin = data.get("origin", "Vizag")
    destination = data.get("destination", "Chennai")
    mode = data.get("mode", "road").lower()
    shipment_id = data.get("shipment_id")
    
    # Backend Enforcement: Reject market dispatch for EMERGENCY_REQUIRED shipments
    if shipment_id:
        shp = Shipment.query.filter_by(id=int(shipment_id)).first()
        if shp and str(getattr(shp, "status", "") or "").strip().upper() == "EMERGENCY_REQUIRED":
            return jsonify({"msg": "Market routing not allowed for emergency shipments. Use emergency dispatch workflow."}), 403
    
    logger.debug("route_options origin=%s destination=%s mode=%s", origin, destination, mode)
    logger.debug("route_options mode_speed=%s", MODE_SPEED.get(mode))

    routes = list(routes_for(origin, destination, mode))
    if not routes:
        routes = [f"{origin} -> {destination}"]
    now = time.time()

    def _action_cache_key(route_id: str, sev: str, desc: str, delay_h: float) -> str:
        raw = f"{route_id}|{sev}|{desc}|{round(float(delay_h or 0.0), 2)}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _compute_one(r: str) -> dict:
        base_dist = route_distance(r, mode)
        if base_dist is None:
            return {}

        dist = round(base_dist, 1)
        base_eta = dist / MODE_SPEED[mode]
        features = [
            base_eta,
            dist,
            MODE_ML_FACTOR.get(mode, 0.0),
            0.3,
            0.3,
        ]
        raw_delay = ml_service.predict_delay(features)
        delay_h = round(max(0.0, min(raw_delay * 0.15, max(2.0, base_eta * 0.6))), 2)

        route_alerts = []
        try:
            live = get_route_text_live_alerts(route_text=r, mode=mode, refresh_seconds=120)
            route_alerts = (live or {}).get("alerts_legacy") or []
        except Exception:
            route_alerts = []

        sev = _alert_severity_bucket(route_alerts)
        desc_raw = " ".join([str(a.get("title") or "").strip() for a in (route_alerts or [])[:2] if str(a.get("title") or "").strip()])
        ridx = int(hashlib.md5(str(r).encode("utf-8")).hexdigest()[:2], 16)
        risk_summary = _route_weather_risk_summary(r, route_index=ridx, predicted_delay_hours=delay_h, distance_km=dist)

        def _risk_level_from(sev0: str, delay_h0: float) -> str:
            s0 = str(sev0 or "").strip().upper()
            try:
                d0 = float(delay_h0 or 0.0)
            except Exception:
                d0 = 0.0
            if s0 == "HIGH" or d0 >= 6.0:
                return "HIGH"
            if s0 in {"MEDIUM", "MODERATE"} or d0 >= 3.0:
                return "MODERATE"
            if s0 == "LOW" or d0 > 0.0:
                return "LOW"
            return "INFO"

        risk_level = _risk_level_from(sev, delay_h)

        ck = _action_cache_key(r, sev, desc_raw, delay_h)
        cached = _ACTIONS_CACHE.get(ck)
        if cached and (now - cached[0]) < _ACTIONS_CACHE_TTL_SEC:
            action = cached[1]
        else:
            try:
                action = generate_actions(
                    route_id=r,
                    source_location=origin,
                    destination_location=destination,
                    transport_mode=mode,
                    distance_km=dist,
                    predicted_delay_hours=delay_h,
                    alert_severity=sev,
                    alert_description=desc_raw,
                )
                # Some llama-server failure modes return a string like "LLM unavailable: ..."
                # rather than raising. Treat that as a failure and fall back to deterministic guidance.
                if str(action).strip().lower().startswith("llm unavailable"):
                    action = _fallback_route_action(alert_severity=sev, predicted_delay_hours=delay_h, mode=mode)
            except Exception as e:
                action = _fallback_route_action(alert_severity=sev, predicted_delay_hours=delay_h, mode=mode)
            # Cache only successful LLM responses. If llama-server was down, avoid caching
            # the failure so a subsequent click will recover immediately.
            if not str(action).lower().startswith("llm unavailable"):
                _ACTIONS_CACHE[ck] = (now, action)

        return {
            "route": r,
            "distance_km": dist,
            "eta_hours": round(base_eta + delay_h, 2),
            "predicted_delay_hours": delay_h,
            "mode": mode,
            "risk_level": risk_level,
            "risk_description": risk_summary,
            "route_alerts": route_alerts,
            "recommended_action": action,
            "genai_advice": None,
        }

    options = []
    if routes:
        max_workers = min(4, max(1, len(routes)))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_compute_one, r): r for r in routes}
            for fut in as_completed(futs):
                try:
                    row = fut.result(timeout=25)
                except TimeoutError:
                    row = {}
                except Exception:
                    row = {}
                if row:
                    options.append(row)

    best = min(range(len(options)), key=lambda i: options[i]["eta_hours"]) if options else 0
    logger.debug("route_options best_index=%s", best)

    # Upgrade action/decision to be route-specific and non-repetitive.
    for i, o in enumerate(sorted(options, key=lambda x: float(x.get("eta_hours") or 1e9))):
        tier = "alternative"
        if i == 0:
            tier = "recommended"
        elif i == (len(options) - 1) and len(options) >= 3:
            tier = "fallback"
        o["decision"] = "Recommended" if tier == "recommended" else "Alternative"
        o["recommended_action"] = _route_specific_action(
            tier=tier,
            mode=str(o.get("mode") or mode),
            crop="",
            route_hint=_route_intermediate_hint(str(o.get("route") or "")),
        )

    resp = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "options": options,
        "recommended_index": best,
        "_build": "route_options_v3",
    }
    if not options:
        resp["_debug"] = {
            "routes": routes,
            "mode": mode,
        }
    return jsonify(resp)

# -------------------------------------------------------------------
# LIVE ALERTS (STRICTLY ROUTE-SPECIFIC FIX)
# -------------------------------------------------------------------

@logistics_bp.get("/alerts_live")
@roles_required(ROLE_LOGISTICS)
def alerts_live():
    route = (request.args.get("route") or "").lower()
    mode = (request.args.get("mode") or "").lower()  # Also get mode parameter
    logger.debug("alerts_live route=%s mode=%s", route, mode)
    
    # If no route is provided, return India-wide live alerts for nationwide monitoring.
    if not route or route == "":
        try:
            india_live = get_india_live_alerts(refresh_seconds=300)
            legacy = (india_live or {}).get("alerts_legacy") or []
            return jsonify(legacy[:20])
        except Exception:
            logger.debug("alerts_live no route provided")
            return jsonify([])
    
    # When route is specified, filter alerts for that specific route
    route_locs = route_points(route)
    logger.debug("alerts_live route_locations=%s", route_locs)

    # Prefer geometry-based live alerts for this route (same schema as before).
    try:
        live = get_route_text_live_alerts(route_text=route, mode=mode or "road", refresh_seconds=30)
        legacy = (live or {}).get("alerts_legacy") or []
        return jsonify(legacy[:20])
    except Exception:
        return jsonify([])

# -------------------------------------------------------------------
# PLAN ROUTE
# -------------------------------------------------------------------

@logistics_bp.post("/plan")
@roles_required(ROLE_LOGISTICS)
def plan_route():
    data = request.get_json() or {}
    claims = get_jwt()
    logistics_id = claims.get("sub")

    batch_id = data.get("batch_id")
    if not batch_id:
        return jsonify({"msg": "batch_id required"}), 400
    try:
        batch_id = int(batch_id)
    except Exception:
        return jsonify({"msg": "batch_id must be an integer"}), 400

    route = data.get("route")
    destination = (data.get("destination") or "").strip() or None
    mode = (data.get("mode") or "").strip().lower() or None

    b = None
    try:
        b = CropBatch.query.get(int(batch_id))
    except Exception:
        b = None
    if not b:
        return jsonify({"msg": "batch not found"}), 404

    source_wh = (getattr(b, "warehouse_name", None) or getattr(b, "warehouse", None) or "").strip()

    if not destination:
        return jsonify({"msg": "destination required"}), 400
    dst_coord = get_city_coordinates(destination)
    if not dst_coord:
        return jsonify({"msg": "destination must be a valid Indian city"}), 400

    mode_l = (mode or "road").strip().lower() or "road"
    if mode_l not in DT_MODE_SPEED:
        mode_l = "road"

    # Prefer pickup (farmer batch location / shipment pickup_location) over warehouse.
    pickup_city = ""
    try:
        shp2 = Shipment.query.filter_by(batch_id=batch_id).order_by(Shipment.created_at.desc()).first()
    except Exception:
        shp2 = None
    if shp2 is not None:
        pickup_city = str(getattr(shp2, "pickup_location", "") or "").strip()
    if not pickup_city:
        pickup_city = str(getattr(b, "location", "") or "").strip()
    src_coord = get_city_coordinates(pickup_city) if pickup_city else None
    if not src_coord and source_wh:
        src_coord = get_warehouse_coordinates(source_wh)
    if not src_coord:
        return jsonify({"msg": "pickup location not available"}), 409

    distance_km = float(haversine_distance(src_coord[0], src_coord[1], dst_coord[0], dst_coord[1]) or 0.0)
    base_travel_hours = float(distance_km) / float(DT_MODE_SPEED[mode_l]) if float(DT_MODE_SPEED[mode_l]) > 0 else 0.0
    eta_meta = _compute_eta_adjusted(src_coord=src_coord, dst_coord=dst_coord, mode=mode_l, base_eta_hours=base_travel_hours)
    eta_hours = float((eta_meta or {}).get("final_eta_hours") or base_travel_hours)
    eta_hours = round(float(eta_hours), 2)
    try:
        logger.info(
            "ETA plan batch=%s mode=%s base=%.2f final=%.2f weather_factor=%s traffic_delay_min=%s api=%s",
            batch_id,
            mode_l,
            float((eta_meta or {}).get("base_eta_hours") or base_travel_hours),
            float((eta_meta or {}).get("final_eta_hours") or eta_hours),
            (eta_meta or {}).get("weather_factor"),
            (eta_meta or {}).get("traffic_delay_minutes"),
            (eta_meta or {}).get("api_health"),
        )
    except Exception:
        pass

    # Snapshot warehouse-exit freshness at planning time (do not reuse logistics freshness).
    try:
        exit_f = float(getattr(b, "warehouse_freshness", None) or getattr(b, "warehouse_entry_freshness", None) or 0.0)
    except Exception:
        exit_f = 0.0
    exit_f = _clamp01(exit_f)
    exit_date = date.today()

    if not route:
        origin_txt = pickup_city
        if not origin_txt:
            try:
                origin_txt = source_wh.replace(" Warehouse", "").strip()
            except Exception:
                origin_txt = source_wh
        route = f"{origin_txt} -> {destination}"

    # Digital-twin refinement: route planning should apply only after pickup confirmation.
    # Update the existing shipment for this batch; do not reset status.
    shp = None
    try:
        shp = Shipment.query.filter_by(batch_id=batch_id).order_by(Shipment.created_at.desc()).first()
    except Exception:
        shp = None
    if shp is None:
        return jsonify({"msg": "shipment not found for batch"}), 409

    cur_status = str(getattr(shp, "status", "") or "").strip().upper()
    if cur_status not in {"PICKUP_REQUESTED", "IN_TRANSIT"}:
        return jsonify({"msg": "route planning is available only for PICKUP_REQUESTED or IN_TRANSIT shipments"}), 409

    shp.route = route
    shp.eta_hours = eta_hours
    shp.logistics_id = logistics_id
    shp.updated_by = logistics_id
    shp.destination = destination
    shp.mode = mode_l
    shp.source_warehouse = source_wh
    shp.warehouse_exit_freshness = exit_f
    shp.warehouse_exit_date = exit_date
    db.session.add(shp)

    db.session.add(BlockchainLog(action="route_plan", reference_id=batch_id, tx_hash="stub"))
    db.session.commit()

    return jsonify({
        "msg": "planned",
        "shipment_id": shp.id,
        "batch_id": batch_id,
        "source_warehouse": source_wh,
        "destination": destination,
        "mode": mode_l,
        "distance_km": round(float(distance_km), 1),
        "base_travel_hours": round(float(base_travel_hours), 2),
        "travel_hours": eta_hours,
        "eta_hours": eta_hours,
        "eta_meta": eta_meta,
    })


@logistics_bp.get("/batch_context/<int:batch_id>")
@roles_required(ROLE_LOGISTICS)
def batch_context(batch_id: int):
    b = None
    try:
        b = CropBatch.query.get(int(batch_id))
    except Exception:
        b = None
    if not b:
        return jsonify({"msg": "batch not found"}), 404
    source_wh = (getattr(b, "warehouse_name", None) or getattr(b, "warehouse", None) or "").strip()
    city = ""
    try:
        city = source_wh.replace(" Warehouse", "").strip()
    except Exception:
        city = source_wh
    return jsonify({
        "batch_id": b.id,
        "crop_type": getattr(b, "crop_type", None),
        "source_warehouse": source_wh,
        "start_location": city,
    })


@logistics_bp.post("/eta")
@roles_required(ROLE_LOGISTICS)
def eta_preview():
    data = request.get_json() or {}
    batch_id = data.get("batch_id")
    destination = (data.get("destination") or "").strip()
    mode = (data.get("mode") or "road").strip().lower() or "road"
    if not batch_id:
        return jsonify({"msg": "batch_id required"}), 400
    try:
        batch_id = int(batch_id)
    except Exception:
        return jsonify({"msg": "batch_id must be an integer"}), 400

    b = None
    try:
        b = CropBatch.query.get(int(batch_id))
    except Exception:
        b = None
    if not b:
        return jsonify({"msg": "batch not found"}), 404

    source_wh = (getattr(b, "warehouse_name", None) or getattr(b, "warehouse", None) or "").strip()
    pickup_city = ""
    try:
        shp = Shipment.query.filter_by(batch_id=batch_id).order_by(Shipment.created_at.desc()).first()
    except Exception:
        shp = None
    if shp is not None:
        pickup_city = str(getattr(shp, "pickup_location", "") or "").strip()
    if not pickup_city:
        pickup_city = str(getattr(b, "location", "") or "").strip()

    city = pickup_city
    if not city and source_wh:
        try:
            city = source_wh.replace(" Warehouse", "").strip()
        except Exception:
            city = source_wh

    if mode not in DT_MODE_SPEED:
        mode = "road"

    if not destination:
        return jsonify({"start_location": city, "source_warehouse": source_wh, "distance_km": None, "travel_hours": None})

    dst_coord = get_city_coordinates(destination)
    if not dst_coord:
        return jsonify({"msg": "destination must be a valid Indian city"}), 400
    src_coord = get_city_coordinates(pickup_city) if pickup_city else None
    if not src_coord and source_wh:
        src_coord = get_warehouse_coordinates(source_wh)
    if not src_coord:
        return jsonify({"msg": "pickup location not available"}), 409

    distance_km = float(haversine_distance(src_coord[0], src_coord[1], dst_coord[0], dst_coord[1]) or 0.0)
    base_travel_hours = float(distance_km) / float(DT_MODE_SPEED[mode]) if float(DT_MODE_SPEED[mode]) > 0 else 0.0
    eta_meta = _compute_eta_adjusted(src_coord=src_coord, dst_coord=dst_coord, mode=mode, base_eta_hours=base_travel_hours)
    final_eta = float((eta_meta or {}).get("final_eta_hours") or base_travel_hours)
    try:
        logger.info(
            "ETA preview batch=%s mode=%s base=%.2f final=%.2f weather_factor=%s traffic_delay_min=%s api=%s",
            batch_id,
            mode,
            float((eta_meta or {}).get("base_eta_hours") or base_travel_hours),
            float((eta_meta or {}).get("final_eta_hours") or final_eta),
            (eta_meta or {}).get("weather_factor"),
            (eta_meta or {}).get("traffic_delay_minutes"),
            (eta_meta or {}).get("api_health"),
        )
    except Exception:
        pass

    return jsonify({
        "start_location": city,
        "source_warehouse": source_wh,
        "destination": destination,
        "mode": mode,
        "distance_km": round(float(distance_km), 1),
        "base_travel_hours": round(float(base_travel_hours), 2),
        "travel_hours": round(float(final_eta), 2),
        "eta_hours": round(float(final_eta), 2),
        "eta_meta": eta_meta,
    })





@logistics_bp.get("/my_shipments")
@roles_required(ROLE_LOGISTICS, ROLE_FARMER)
def my_shipments():
    claims = get_jwt() or {}
    role = str(claims.get("role") or "").strip().lower()
    sub = claims.get("sub")

    q = Shipment.query
    if role == ROLE_LOGISTICS:
        # Logistics dashboard should be able to see all shipments.
        # Action endpoints still prevent hijacking shipments assigned to other logistics users.
        pass
    elif role == ROLE_FARMER and sub is not None:
        try:
            farmer_id = int(sub)
            q = q.join(CropBatch, Shipment.batch_id == CropBatch.id).filter(CropBatch.farmer_id == farmer_id)
        except Exception:
            pass

    rows = q.order_by(Shipment.created_at.desc()).limit(200).all()
    out = []
    any_updates = False
    for s in rows:
        pickup_loc = getattr(s, "pickup_location", None)
        if not pickup_loc:
            try:
                b = CropBatch.query.get(int(getattr(s, "batch_id", 0) or 0))
            except Exception:
                b = None
            if b is not None:
                pickup_loc = getattr(b, "location", None)
        try:
            created = s.created_at.isoformat() if getattr(s, "created_at", None) else None
        except Exception:
            created = None
        dest_wh = getattr(s, "destination_warehouse", None) or getattr(s, "destination", None)
        dest_city = _normalize_destination_city(dest_wh)
        try:
            delivered_at = getattr(s, "delivery_time", None)
            delivered_iso = delivered_at.isoformat() + "Z" if delivered_at is not None else None
        except Exception:
            delivered_iso = None
        out.append({
            "id": s.id,
            "batch_id": s.batch_id,
            "crop": getattr(s, "crop", None),
            "status": s.status,
            "eta_hours": s.eta_hours,
            "route": s.route,
            "pickup_location": pickup_loc,
            # Return destination as a normalized city for routing/Plan Route auto-fill.
            "destination": dest_city,
            # Preserve internal warehouse traceability.
            "destination_warehouse": dest_wh,
            "mode": getattr(s, "mode", None) or "road",
            "current_freshness": getattr(s, "current_freshness", None),
            "delivery_time": delivered_iso,
            "created_at": created,
            "crop_seasons": [],
            "current_season": _season_label_for_today(),
            "in_season": True,
            "seasonal_risk": False,
            "seasonal_warning": "",
        })

        try:
            b = CropBatch.query.get(int(getattr(s, "batch_id", 0) or 0))
        except Exception:
            b = None
        if b is not None:
            try:
                crop = str(getattr(b, "crop_type", "") or getattr(s, "crop", "") or "")
                harvest_date = getattr(b, "harvest_date", None)
                seasons = (_get_crop_seasons() or {}).get(str(crop or "").strip().lower(), [])
                warn = _seasonal_warning_for_crop(crop, harvest_date)
                seasonal_risk = bool(warn)
                out[-1]["crop_seasons"] = seasons
                out[-1]["seasonal_warning"] = warn
                out[-1]["seasonal_risk"] = bool(seasonal_risk)
                out[-1]["in_season"] = (not bool(seasonal_risk))
            except Exception:
                pass

    return jsonify(out)


@logistics_bp.get("/in_transit")
@roles_required(ROLE_LOGISTICS, ROLE_FARMER)
def in_transit():
    """Digital twin: shipments currently in transit."""
    claims = get_jwt() or {}
    role = str(claims.get("role") or "").strip().lower()
    sub = claims.get("sub")
    q = Shipment.query
    if role == ROLE_LOGISTICS:
        # Logistics dashboard should be able to see all active shipments.
        # Action endpoints still prevent hijacking shipments assigned to other logistics users.
        pass
    elif role == ROLE_FARMER and sub is not None:
        try:
            farmer_id = int(sub)
            q = q.join(CropBatch, Shipment.batch_id == CropBatch.id).filter(CropBatch.farmer_id == farmer_id)
        except Exception:
            pass

    rows = q.order_by(Shipment.created_at.desc()).limit(200).all()
    out = []
    any_updates = False
    for s in rows:
        st = str(getattr(s, "status", "") or "").strip().upper()
        # UI requirement: show in this panel only after logistics confirms pickup.
        if st != "IN_TRANSIT":
            continue

        now = datetime.utcnow()
        last_updated = now.isoformat() + "Z"

        freshness = getattr(s, "current_freshness", None)
        initial = getattr(s, "initial_freshness", None)
        if initial is None:
            initial = freshness
        try:
            initial_f = float(initial or 0.0)
        except Exception:
            initial_f = 0.0

        started_at = None
        hours_in_transit = 0.0
        if st == "IN_TRANSIT":
            started_at = getattr(s, "transit_start_time", None) or getattr(s, "pickup_confirmed_at", None)
            try:
                if started_at is not None:
                    hours_in_transit = float((now - started_at).total_seconds() / 3600.0)
            except Exception:
                hours_in_transit = 0.0
            if hours_in_transit < 0.0:
                hours_in_transit = 0.0

        freshness_update_ok = True
        freshness_update_error = ""
        if st == "IN_TRANSIT":
            crop = str(getattr(s, "crop", "") or "")

            prev_for_decay = None
            if freshness is not None:
                prev_for_decay = freshness
            else:
                prev_for_decay = initial_f

            last_upd = getattr(s, "last_freshness_update", None)
            last_temp = getattr(s, "last_temperature", None)
            last_hum = getattr(s, "last_humidity", None)

            new_f, _elapsed_h = _monotonic_transit_update(
                previous_freshness=prev_for_decay,
                last_update_time=last_upd,
                transit_start_time=started_at,
                crop=crop,
                now_utc=now,
                temperature_c=last_temp,
                humidity_pct=last_hum,
            )

            try:
                prev_f_val = _clamp01(float(prev_for_decay or 0.0))
            except Exception:
                prev_f_val = 0.0

            # Strict rule: if time elapsed (>0) and freshness was >0, freshness must strictly decrease.
            # If not, flag error and do not persist/update returned freshness.
            if float(_elapsed_h or 0.0) > 0.0 and float(prev_f_val) > 0.0:
                try:
                    if float(new_f) >= float(prev_f_val):
                        freshness_update_ok = False
                        freshness_update_error = "logic_error_non_decreasing_freshness"
                except Exception:
                    freshness_update_ok = False
                    freshness_update_error = "logic_error_invalid_freshness_update"

            if freshness_update_ok:
                freshness = float(new_f)
                # Persist current freshness + last_freshness_update so the system behaves like a real Digital Twin.
                try:
                    s.current_freshness = float(freshness)
                    s.last_freshness_update = now
                    db.session.add(s)
                    any_updates = True
                except Exception:
                    pass
            else:
                freshness = float(prev_f_val)

        # ETA-based risk vs remaining shelf life is auxiliary decision support.
        # UI risk_status must follow global freshness thresholds.
        shelf_life_hours = _transit_shelf_life_hours_for_crop(str(getattr(s, "crop", "") or ""))
        rate = 1.0 / float(shelf_life_hours or 72.0)
        remaining_hours = None
        try:
            remaining_hours = float(freshness or 0.0) / float(rate or (1.0 / 72.0))
        except Exception:
            remaining_hours = None

        eta_risk = _risk_from_eta_vs_remaining(
            eta_hours=getattr(s, "eta_hours", None),
            remaining_shelf_life_hours=remaining_hours,
        )
        risk = _risk_status_from_freshness(freshness if freshness is not None else initial_f)

        out.append({
            "shipment_id": s.id,
            "batch_id": s.batch_id,
            "crop": getattr(s, "crop", None),
            "pickup_location": getattr(s, "pickup_location", None),
            "destination_warehouse": getattr(s, "destination_warehouse", None),
            "current_freshness": freshness,
            "initial_freshness": float(initial_f),
            "last_freshness_update_timestamp": (getattr(s, "last_freshness_update", None).isoformat() + "Z") if getattr(s, "last_freshness_update", None) is not None else None,
            "transit_start_time": (started_at.isoformat() + "Z") if started_at is not None else None,
            "hours_in_transit": round(float(hours_in_transit), 4),
            "freshness_update_ok": bool(freshness_update_ok),
            "freshness_update_error": freshness_update_error,
            "temperature_deviation": getattr(s, "temperature_deviation", None),
            "eta_hours": getattr(s, "eta_hours", None),
            "eta_risk": eta_risk,
            "risk_status": risk,
            "status": st,
            "last_updated": last_updated,
            "crop_seasons": [],
            "current_season": _season_label_for_today(),
            "in_season": True,
            "seasonal_risk": False,
            "seasonal_warning": "",
        })

        try:
            b = CropBatch.query.get(int(getattr(s, "batch_id", 0) or 0))
        except Exception:
            b = None
        if b is not None:
            try:
                crop_b = str(getattr(b, "crop_type", "") or getattr(s, "crop", "") or "")
                harvest_date = getattr(b, "harvest_date", None)
                seasons = (_get_crop_seasons() or {}).get(str(crop_b or "").strip().lower(), [])
                warn = _seasonal_warning_for_crop(crop_b, harvest_date)
                seasonal_risk = bool(warn)
                
                # Check if current season matches crop's season
                current_season = _season_label_for_today()
                in_season = True
                out_of_season_warning = ""
                
                if seasons and current_season:
                    # Normalize seasons for comparison
                    season_list = [str(s).strip().lower() for s in seasons]
                    # Check if current season is in crop's seasons (handle perennial as always in season)
                    if "perennial" in season_list:
                        in_season = True
                    elif current_season.lower() not in season_list:
                        in_season = False
                        out_of_season_warning = f"Out of season: {crop_b} is typically harvested in {', '.join(seasons)}. Current season is {current_season}."
                
                out[-1]["crop_seasons"] = seasons
                out[-1]["seasonal_warning"] = warn + (" " + out_of_season_warning if out_of_season_warning else "")
                out[-1]["seasonal_risk"] = bool(seasonal_risk) or not in_season
                out[-1]["in_season"] = in_season
                out[-1]["out_of_season_warning"] = out_of_season_warning
            except Exception:
                pass
    if any_updates:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    return jsonify(out)


@logistics_bp.post("/find_routes")
@roles_required(ROLE_LOGISTICS)
def find_routes():
    """Suggest ROAD-only route options with deterministic risk + arrival freshness.

    This endpoint is used by the Logistics Dashboard "Suggest Routes"/"Find Routes" button.
    """
    data = request.get_json() or {}
    shipment_id = data.get("shipment_id")
    # ROAD-only: ignore any other mode.
    mode = "road"
    if not shipment_id:
        return jsonify({"msg": "shipment_id required"}), 400
    try:
        shipment_id = int(shipment_id)
    except Exception:
        return jsonify({"msg": "shipment_id must be an integer"}), 400

    shp = Shipment.query.filter_by(id=int(shipment_id)).first()
    if not shp:
        return jsonify({"msg": "shipment not found"}), 404

    st = str(getattr(shp, "status", "") or "").strip().upper()
    if st not in {"PICKUP_REQUESTED", "IN_TRANSIT"}:
        return jsonify({"msg": "route finding is available only for PICKUP_REQUESTED or IN_TRANSIT shipments"}), 409

    pickup_raw = str(getattr(shp, "pickup_location", "") or "").strip()
    destination_wh = str(getattr(shp, "destination_warehouse", None) or "").strip()

    if not pickup_raw or not destination_wh:
        return jsonify({"msg": "pickup_location and destination_warehouse must be set on the shipment"}), 409

    pickup_city = _clean_city_label(pickup_raw)
    destination_city = _normalize_destination_city(destination_wh)
    destination_label = destination_wh
    if not pickup_city or not destination_city:
        return jsonify({"msg": "pickup and destination must be valid"}), 409

    # Same-city shortcut
    if pickup_city.strip().lower() == destination_city.strip().lower():
        try:
            cur_f = float(getattr(shp, "current_freshness", None) or getattr(shp, "initial_freshness", None) or 0.0)
        except Exception:
            cur_f = 0.0
        cur_f = _clamp01(float(cur_f))

        decay_rate_per_hour = 1.0 / float(_transit_shelf_life_hours_for_crop(str(getattr(shp, "crop", "") or "")) or 72.0)
        if decay_rate_per_hour <= 0.0:
            decay_rate_per_hour = 1.0 / 72.0

        eta_h = 1.0
        predicted = _clamp01(float(cur_f) * math.exp(-float(decay_rate_per_hour) * float(eta_h)))
        return jsonify({
            "msg": "local_transfer",
            "notice": "Local transfer (0 km) – direct dispatch available",
            "shipment_id": int(getattr(shp, "id", 0) or 0),
            "pickup_city": pickup_city,
            "destination_city": destination_city,
            "destination_warehouse": destination_label,
            "transport_mode": "road",
            "current_freshness": round(float(cur_f), 4),
            "predicted_arrival_freshness": round(float(predicted), 4),
            "options": [],
        })

    src_coord = get_city_coordinates(pickup_city)
    # Destination: prefer warehouse coordinate if available, else destination city coordinate
    dst_coord = get_warehouse_coordinates(destination_label) or get_city_coordinates(destination_city)
    if not src_coord or not dst_coord:
        return jsonify({"msg": "pickup and destination must be valid Indian cities"}), 400

    # Current freshness (do not overwrite)
    try:
        cur_f = float(getattr(shp, "current_freshness", None) or getattr(shp, "initial_freshness", None) or 0.0)
    except Exception:
        cur_f = 0.0
    cur_f = _clamp01(float(cur_f))

    decay_rate_per_hour = 1.0 / float(_transit_shelf_life_hours_for_crop(str(getattr(shp, "crop", "") or "")) or 72.0)
    if decay_rate_per_hour <= 0.0:
        decay_rate_per_hour = 1.0 / 72.0

    # TomTom-only routing.
    base_routes = _tomtom_route_alternatives(src_coord=src_coord, dst_coord=dst_coord, max_alternatives=2, route_type="fastest")

    # Keep at most 2 truly distinct routes: distance diff >= 3% OR ETA diff >= 5%.
    def _pct_diff(a: float, b: float) -> float:
        try:
            aa = float(a)
            bb = float(b)
        except Exception:
            return 0.0
        if aa <= 0 or bb <= 0:
            return 0.0
        return abs(aa - bb) / min(aa, bb)

    def _route_eta_h(r: dict) -> float:
        try:
            s = float(r.get("duration_in_traffic_s") or 0.0)
        except Exception:
            s = 0.0
        return float(s) / 3600.0 if s > 0 else 0.0

    def _route_dist_km(r: dict) -> float:
        try:
            d = float(r.get("distance_km") or 0.0)
        except Exception:
            d = 0.0
        return float(d)

    def _route_highway(r: dict) -> str:
        try:
            return str(r.get("primary_highway") or "").strip().upper().replace(" ", "")
        except Exception:
            return ""

    # Route count + distinctness rule (strict):
    # - max 2 routes
    # - distinct if >=10% ETA difference OR different primary highway
    # - do NOT return two routes on the same highway corridor just because the via-town differs
    def _is_distinct(a: dict, b: dict) -> bool:
        ha = _route_highway(a)
        hb = _route_highway(b)
        if ha and hb and ha != hb:
            return True
        # If both have same highway, treat as same corridor (avoid duplicates)
        if ha and hb and ha == hb:
            return False
        ea = _route_eta_h(a)
        eb = _route_eta_h(b)
        if ea > 0 and eb > 0 and _pct_diff(ea, eb) >= 0.10:
            return True
        return False

    t_alts = []
    if isinstance(base_routes, list):
        for rr in base_routes:
            if not isinstance(rr, dict):
                continue
            if not t_alts:
                t_alts.append(rr)
                continue
            if len(t_alts) >= 2:
                break
            ok = True
            for ex in t_alts:
                if not _is_distinct(ex, rr):
                    ok = False
                    break
            if ok:
                t_alts.append(rr)
    # If only one route is returned, try additional TomTom strategies to obtain a second distinct option.
    if isinstance(t_alts, list) and len(t_alts) < 2:
        strategies = [
            {"route_type": "shortest", "avoid": ""},
            {"route_type": "fastest", "avoid": "tollRoads"},
            {"route_type": "shortest", "avoid": "tollRoads"},
        ]
        for stg in strategies:
            try:
                extra = _tomtom_route_alternatives(
                    src_coord=src_coord,
                    dst_coord=dst_coord,
                    max_alternatives=0,
                    route_type=str(stg.get("route_type")),
                    avoid=str(stg.get("avoid") or ""),
                )
            except Exception:
                extra = []
            for rr in (extra or []):
                if not isinstance(rr, dict):
                    continue
                if not t_alts:
                    t_alts.append(rr)
                    continue
                if len(t_alts) >= 2:
                    break
                ok = True
                for ex in t_alts:
                    if not _is_distinct(ex, rr):
                        ok = False
                        break
                if ok:
                    t_alts.append(rr)
                    break
            if len(t_alts) >= 2:
                break
    if isinstance(t_alts, list) and len(t_alts) > 2:
        t_alts = list(t_alts)[:2]

    if not t_alts:
        return jsonify({"msg": "no_routes", "error": "No TomTom routes returned for this origin-destination pair."}), 502

    # Weather summaries for endpoints (not per-route)
    w_src = _openweather_summary(coord=src_coord)
    w_dst = _openweather_summary(coord=dst_coord)
    severe_weather = _is_severe_weather((w_src.get("condition") or "")) or _is_severe_weather((w_dst.get("condition") or ""))

    # Crop optimal temperature
    opt_t = _optimal_temp_c_for_crop(str(getattr(shp, "crop", "") or ""))
    try:
        cur_temp = float(w_src.get("temperature_c")) if w_src.get("temperature_c") is not None else None
    except Exception:
        cur_temp = None
    temp_dev = None
    try:
        if opt_t is not None and cur_temp is not None:
            temp_dev = abs(float(cur_temp) - float(opt_t))
    except Exception:
        temp_dev = None

    long_exposure_threshold_h = 8.0
    temp_dev_threshold_c = 4.0

    def _traffic_level_label(*, congestion_level: str, traffic_delay_pct: float) -> str:
        cl = str(congestion_level or "").strip().upper()
        if cl in {"LOW", "MEDIUM", "HIGH"}:
            return "Low Traffic" if cl == "LOW" else ("Moderate Traffic" if cl == "MEDIUM" else "High Traffic")
        try:
            p = float(traffic_delay_pct)
        except Exception:
            p = None
        if p is None:
            return "Traffic"  # neutral fallback
        if p <= 10.0:
            return "Low Traffic"
        if p <= 25.0:
            return "Moderate Traffic"
        return "High Traffic"

    def _route_display_label(*, highway: str) -> str:
        hw = str(highway or "").strip().upper()
        if hw:
            hw = hw.replace(" ", "")
        if hw:
            return f"{pickup_city} → via {hw} → {destination_city}"
        return f"{pickup_city} → {destination_city}"

    def _corridor_label_from_highway(highway: str) -> str:
        hw = str(highway or "").strip().upper().replace(" ", "")
        if not hw:
            return f"{pickup_city} → {destination_city}"
        return f"{pickup_city} → {hw} → {destination_city}"

    def _route_display_label_with_via(*, via_town: str, highway: str) -> str:
        vt = str(via_town or "").strip()
        hw = str(highway or "").strip().upper().replace(" ", "")
        if vt and hw:
            return f"{pickup_city} → via {vt} ({hw}) → {destination_city}"
        if vt and not hw:
            return f"{pickup_city} → via {vt} → {destination_city}"
        if hw:
            return f"{pickup_city} → {hw} → {destination_city}"
        return f"{pickup_city} → {destination_city}"

    def _corridor_format(*, via_town: str, highway: str) -> str:
        vt = str(via_town or "").strip()
        hw = str(highway or "").strip().upper().replace(" ", "")
        if vt and hw:
            return f"{pickup_city} → via {vt} ({hw}) → {destination_city}"
        if hw:
            return f"{pickup_city} → {hw} → {destination_city}"
        return f"{pickup_city} → {destination_city}"

    def _condition_rank(lbl: str) -> int:
        """Return severity rank for weather conditions (higher = worse)."""
        ranks = {"clear": 0, "wind": 1, "haze": 2, "fog": 3, "heat": 4, "rain": 5, "storm": 6}
        return ranks.get(str(lbl).lower().strip(), 0)

    def _checkpoint_condition_label(w: dict) -> str:
        """Extract condition label from OpenWeather response."""
        try:
            weather_list = w.get("weather", []) if isinstance(w, dict) else []
            if not weather_list:
                return "clear"
            main = str(weather_list[0].get("main", "")).lower()
            desc = str(weather_list[0].get("description", "")).lower()
            
            # Map to standardized labels
            storm_keywords = ["storm", "thunder", "tornado", "hurricane"]
            rain_keywords = ["rain", "drizzle", "shower"]
            heat_keywords = ["hot", "warm", "heat"]
            haze_keywords = ["haze", "smoke", "dust", "sand", "ash"]
            fog_keywords = ["fog", "mist"]
            wind_keywords = ["wind", "breeze", "gale"]
            
            for kw in storm_keywords:
                if kw in main or kw in desc:
                    return "storm"
            for kw in rain_keywords:
                if kw in main or kw in desc:
                    return "rain"
            for kw in heat_keywords:
                if kw in main or kw in desc:
                    return "heat"
            for kw in haze_keywords:
                if kw in main or kw in desc:
                    return "haze"
            for kw in fog_keywords:
                if kw in main or kw in desc:
                    return "fog"
            for kw in wind_keywords:
                if kw in main or kw in desc:
                    return "wind"
            return "clear"
        except Exception:
            return "clear"

    def _traffic_impact_bucket(traffic_delay_pct: float) -> str:
        try:
            p = float(traffic_delay_pct)
        except Exception:
            return "Unknown"
        if p <= 10.0:
            return "Minor"
        if p <= 20.0:
            return "Moderate"
        return "Heavy"

    def _weather_impact_for_route(route_obj: dict, route_index: int) -> dict:
        # Deterministic + API-derived only: sample weather along route geometry keys if present.
        try:
            keys = route_obj.get("geometry_keys")
        except Exception:
            keys = None
        if not isinstance(keys, list) or not keys:
            # Fall back to endpoints summary.
            try:
                cond = str((w_src.get("condition") or "") + " " + (w_dst.get("condition") or "")).strip()
            except Exception:
                cond = ""
            lbl = _checkpoint_condition_label({"weather": [{"main": cond.split()[0] if cond else ""}]}) if cond else "unknown"
            return {"label": "Clear" if lbl == "clear" else ("Storm" if lbl == "storm" else ("Rain" if lbl == "rain" else "Variable")), "shared": True}

        pts = []
        for k in keys:
            s = str(k or "").strip()
            if not s or "," not in s:
                continue
            a, b = s.split(",", 1)
            try:
                pts.append((float(a), float(b)))
            except Exception:
                continue
        if len(pts) < 3:
            return {"label": "Variable", "shared": False}

        # Sample two interior points to limit API calls.
        samples = []
        try:
            samples.append(pts[len(pts) // 3])
        except Exception:
            pass
        try:
            samples.append(pts[(2 * len(pts)) // 3])
        except Exception:
            pass

        worst_lbl = "clear"
        for lat, lon in samples:
            try:
                w = _openweather_current(float(lat), float(lon), route_index=int(route_index))
            except Exception:
                w = {}
            lbl = _checkpoint_condition_label(w)
            if _condition_rank(lbl) > _condition_rank(worst_lbl):
                worst_lbl = lbl

        if worst_lbl == "storm":
            return {"label": "Storm", "shared": False}
        if worst_lbl == "rain":
            return {"label": "Rain", "shared": False}
        if worst_lbl == "heat":
            return {"label": "Heatwave", "shared": False}
        if worst_lbl in {"haze", "fog"}:
            return {"label": "Haze", "shared": False}
        if worst_lbl == "wind":
            return {"label": "Wind", "shared": False}
        if worst_lbl == "clear":
            return {"label": "Clear", "shared": False}
        return {"label": "Variable", "shared": False}

    def _risk_classification(*, eta_h: float, traffic_delay_pct: float, temp_dev_c: float, weather_lbl: str) -> str:
        score = 0
        try:
            p = float(traffic_delay_pct or 0.0)
        except Exception:
            p = 0.0
        try:
            eta0 = float(eta_h or 0.0)
        except Exception:
            eta0 = 0.0
        try:
            td = float(temp_dev_c) if temp_dev_c is not None else 0.0
        except Exception:
            td = 0.0

        wl = str(weather_lbl or "").strip().lower()

        if p >= 20.0:
            score += 2
        elif p >= 10.0:
            score += 1

        if eta0 > 10.0:
            score += 2
        elif eta0 > 8.0:
            score += 1

        if td >= 6.0:
            score += 2
        elif td >= 4.0:
            score += 1

        if wl in {"severe", "storm"}:
            score += 2
        elif wl in {"rain", "wind", "haze"}:
            score += 1

        if score >= 5:
            return "HIGH"
        if score >= 3:
            return "MEDIUM"
        return "SAFE"

    def _traffic_alert_from_congestion(cl: str) -> str:
        s = str(cl or "").strip().upper()
        if s == "LOW":
            return "Traffic: Low"
        if s == "MEDIUM":
            return "Traffic: Moderate"
        if s == "HIGH":
            return "Traffic: High"
        return "Traffic: Unknown"

    def _weather_alert_from_label(lbl: str) -> str:
        s = str(lbl or "").strip().lower()
        if s == "storm":
            return "Weather: Storm"
        if s == "rain":
            return "Weather: Rain"
        if s == "clear":
            return "Weather: Clear"
        if s:
            return f"Weather: {s.title()}"
        return "Weather: Variable"

    def _deterministic_recommendation(*, rank: int, risk: str) -> str:
        r = str(risk or "").strip().upper()
        if rank == 0:
            return "Preferred route – best balance of ETA and freshness."
        if r == "HIGH":
            return "Avoid – high disruption risk and longer exposure."
        return "Alternative – acceptable but higher exposure than preferred route."

    options = []
    for i, r in enumerate(t_alts):
        try:
            dist_km = float(r.get("distance_km")) if r.get("distance_km") is not None else None
        except Exception:
            dist_km = None
        try:
            dur_tr_s = float(r.get("duration_in_traffic_s")) if r.get("duration_in_traffic_s") is not None else None
        except Exception:
            dur_tr_s = None
        try:
            dur_norm_s = float(r.get("duration_normal_s")) if r.get("duration_normal_s") is not None else None
        except Exception:
            dur_norm_s = None

        eta_h = float(dur_tr_s) / 3600.0 if dur_tr_s and dur_tr_s > 0 else 0.0
        eta_h = round(float(eta_h), 2)

        base_eta_h = float(dur_norm_s) / 3600.0 if dur_norm_s and dur_norm_s > 0 else 0.0
        base_eta_h = round(float(base_eta_h), 2)
        delay_h = 0.0
        try:
            if base_eta_h and base_eta_h > 0 and eta_h and eta_h >= base_eta_h:
                delay_h = round(float(eta_h - base_eta_h), 2)
        except Exception:
            delay_h = 0.0

        traffic_delay_pct = 0.0
        if dur_norm_s and dur_norm_s > 0 and dur_tr_s and dur_tr_s >= dur_norm_s:
            traffic_delay_pct = ((float(dur_tr_s) - float(dur_norm_s)) / float(dur_norm_s)) * 100.0
        traffic_delay_pct = round(float(max(0.0, traffic_delay_pct)), 1)

        risk_score = 0
        alerts = []

        # Route-specific weather impact (API-derived). Used both for display + scoring.
        wx = _weather_impact_for_route(r, route_index=i)
        weather_impact = str((wx or {}).get("label") or "Variable")

        traffic_txt = _traffic_level_label(congestion_level=str(r.get("congestion_level") or ""), traffic_delay_pct=float(traffic_delay_pct))
        traffic_level = "Low" if "Low" in traffic_txt else ("Moderate" if "Moderate" in traffic_txt else ("High" if "High" in traffic_txt else "Unknown"))
        if float(traffic_delay_pct or 0.0) > 20.0:
            risk_score += 2

        traffic_tag = f"Traffic: {traffic_level}"
        try:
            if float(delay_h or 0.0) >= 0.1:
                traffic_tag = f"Traffic: {traffic_level} (+{delay_h}h)"
        except Exception:
            pass
        alerts.append(traffic_tag)

        # Weather tag (route-specific, consistent with Weather Impact column)
        if weather_impact in {"Storm", "Heatwave"}:
            risk_score += 2
        elif weather_impact in {"Rain", "Wind", "Haze"}:
            risk_score += 1
        alerts.append(f"Weather: {weather_impact}")

        if temp_dev is not None and float(temp_dev) > float(temp_dev_threshold_c):
            risk_score += 2
            alerts.append(f"Temp deviation: {round(float(temp_dev), 1)}°C")

        if eta_h > float(long_exposure_threshold_h):
            risk_score += 1
            alerts.append(f"Exposure: {eta_h}h")

        predicted = _clamp01(float(cur_f) * math.exp(-float(decay_rate_per_hour) * float(eta_h)))
        congestion_level = str(r.get("congestion_level") or "").strip() or "UNKNOWN"
        route_summary = str(r.get("route_summary") or "").strip()

        primary_hw = str(r.get("primary_highway") or "").strip().upper().replace(" ", "")
        via_town = _choose_tomtom_via_town(r, origin_city=pickup_city, destination_city=destination_city)
        # Display label must be explainable + non-fabricated.
        # Prefer: Origin → via City (Highway) → Destination
        # Fallback: Origin → Highway → Destination
        corridor = _corridor_format(via_town=via_town, highway=primary_hw)
        route_label = corridor

        traffic_impact = _traffic_impact_bucket(float(traffic_delay_pct))

        # Alerts must be structured and route-specific.
        alerts = []
        alerts.append(_traffic_alert_from_congestion(congestion_level))
        alerts.append(_weather_alert_from_label(str(weather_impact or "")))
        if temp_dev is not None:
            try:
                alerts.append(f"Temp deviation: {round(float(temp_dev), 1)}°C")
            except Exception:
                pass
        if eta_h > 10.0:
            alerts.append("Exposure: >10h")

        risk_level = _risk_classification(
            eta_h=float(eta_h),
            traffic_delay_pct=float(traffic_delay_pct),
            temp_dev_c=float(temp_dev) if temp_dev is not None else 0.0,
            weather_lbl=str(weather_impact or ""),
        )

        options.append({
            "route_option_id": f"R{i + 1}",
            "route": route_label,
            "route_corridor": corridor,
            "distance_km": round(float(dist_km), 2) if dist_km is not None else None,
            "eta_hours": float(eta_h),
            "eta_hours_base": float(base_eta_h),
            "traffic_delay_hours": float(delay_h),
            "traffic_delay_pct": float(traffic_delay_pct),
            "predicted_arrival_freshness": round(float(predicted), 4),
            "traffic_impact": traffic_impact,
            "weather_impact": weather_impact,
            "risk_level": str(risk_level),
            "risk_score": int(risk_score),
            "alerts": alerts,
            "route_summary": route_summary,
            "congestion_level": congestion_level,
            "primary_highway": primary_hw,
            "via_town": str(via_town or ""),
            "tomtom_summary": {
                "lengthInMeters": r.get("tomtom_length_m"),
                "travelTimeInSeconds": r.get("tomtom_travel_s"),
                "trafficDelayInSeconds": r.get("tomtom_traffic_delay_s"),
            },
            "recommendation": "",
        })

    # Sanity filter: drop options with impossible road speeds / ETA unit mismatches.
    def _is_impossible_option(o: dict) -> bool:
        try:
            d = float(o.get("distance_km") or 0.0)
        except Exception:
            d = 0.0
        try:
            h = float(o.get("eta_hours") or 0.0)
        except Exception:
            h = 0.0
        if d <= 0.0 or h <= 0.0:
            return False
        try:
            speed = float(d) / float(h)
        except Exception:
            speed = 0.0
        # Hard guardrails for ROAD: > 140 km/h is nearly always a unit/parsing bug.
        if d >= 100.0 and speed > 140.0:
            return True
        # Specific guardrail from your prompt.
        if d > 700.0 and h < 5.0:
            return True
        return False

    try:
        options = [o for o in options if not _is_impossible_option(o)]
    except Exception:
        pass

    if not options:
        return jsonify({"msg": "no_routes", "error": "No usable TomTom routes after sanity filtering."}), 502

    # De-duplicate identical corridor labels (avoid "same corridor twice")
    try:
        seen = set()
        deduped = []
        for o in (options or []):
            k = str(o.get("route_corridor") or o.get("route") or "").strip().lower()
            if not k or k in seen:
                continue
            seen.add(k)
            deduped.append(o)
        options = deduped
    except Exception:
        pass

    # Deterministic ranking (top-2): lowest risk, then highest predicted freshness, then lowest traffic-adjusted ETA.
    def _eta_key(o: dict) -> float:
        try:
            return float(o.get("eta_hours") or 1e9)
        except Exception:
            return 1e9

    def _pf_key(o: dict) -> float:
        try:
            return float(o.get("predicted_arrival_freshness") or 0.0)
        except Exception:
            return 0.0

    def _risk_score_key(o: dict) -> int:
        try:
            return int(o.get("risk_score") or 0)
        except Exception:
            return 0

    options.sort(key=lambda o: (_risk_score_key(o), -_pf_key(o), _eta_key(o)))
    options = options[:2]

    # Deterministic recommendation text per option.
    for ridx, o in enumerate(options):
        try:
            eta0 = float(o.get("eta_hours") or 0.0)
        except Exception:
            eta0 = 0.0
        try:
            pf0 = float(o.get("predicted_arrival_freshness") or 0.0)
        except Exception:
            pf0 = 0.0
        o["recommendation"] = _deterministic_recommendation(rank=int(ridx), risk=o.get("risk_level"))

    # GenAI advisory (non-authoritative)
    genai = None
    try:
        best = options[0] if options else None
        if best is not None:
            weather_summary = {
                "pickup": w_src,
                "destination": w_dst,
            }
            if str(best.get("risk_level") or "").strip().upper() == "LOW":
                genai = {
                    "preferred_route_option_id": str(best.get("route_option_id") or ""),
                    "dispatch_advice": "No additional action required.",
                    "explanation": "Risk is LOW based on traffic, weather, temperature deviation, and ETA.",
                }
            else:
                adv = advise_route(
                    route=str(best.get("route") or ""),
                    mode="road",
                    predicted_delay_hours=float((float(best.get("traffic_delay_pct") or 0.0) / 100.0) * float(best.get("eta_hours") or 0.0)),
                    alerts=[],
                )
                if isinstance(adv, dict):
                    genai = {
                        "preferred_route_option_id": str(best.get("route_option_id") or ""),
                        "dispatch_advice": str(adv.get("recommendation") or "").strip() or "",
                        "explanation": str(adv.get("explanation") or "").strip() or "",
                        "weather_summary": weather_summary,
                    }
    except Exception:
        genai = None

    notice = ""
    try:
        if isinstance(options, list) and len(options) == 1:
            notice = "Only one major road corridor available for this route."
    except Exception:
        notice = ""

    return jsonify({
        "msg": "routes_found",
        "notice": notice,
        "shipment_id": int(getattr(shp, "id", 0) or 0),
        "pickup_city": pickup_city,
        "destination_city": destination_city,
        "destination_warehouse": destination_label,
        "transport_mode": "road",
        "current_freshness": round(float(cur_f), 4),
        "decay_rate_per_hour": round(float(decay_rate_per_hour), 6),
        "weather": {
            "pickup": w_src,
            "destination": w_dst,
        },
        "options": options,
        "genai": genai,
    })


@logistics_bp.post("/status")
@roles_required(ROLE_LOGISTICS)
def set_status():
    data = request.get_json() or {}
    shipment_id = data.get("shipment_id")
    status = str(data.get("status") or "").strip().upper()
    allowed = {"IN_TRANSIT", "DELIVERED", "CANCELLED"}
    if not shipment_id:
        return jsonify({"msg": "shipment_id required"}), 400
    if status not in allowed:
        return jsonify({"msg": "invalid status"}), 400

    claims = get_jwt()
    logistics_id = claims.get("sub")

    shp = Shipment.query.filter_by(id=int(shipment_id)).first()
    if not shp:
        return jsonify({"msg": "shipment not found"}), 404

    # Allow confirming unassigned pickup requests, but forbid hijacking shipments
    # already assigned to a different logistics user.
    if logistics_id is not None:
        try:
            assigned = getattr(shp, "logistics_id", None)
            if assigned is not None and int(assigned) != int(logistics_id):
                return jsonify({"msg": "forbidden"}), 403
        except Exception:
            pass

    cur = str(getattr(shp, "status", "") or "").strip().upper()
    if cur in {"DELIVERED", "CANCELLED"}:
        return jsonify({"msg": "shipment is closed"}), 409

    # Delivery confirmation is allowed ONLY for in-transit shipments.
    if status == "DELIVERED" and cur != "IN_TRANSIT":
        return jsonify({"msg": "Delivery can only be confirmed for in-transit shipments."}), 409

    shp.status = status
    shp.updated_at = datetime.utcnow() if hasattr(shp, "updated_at") else getattr(shp, "updated_at", None)

    # On delivery: freeze freshness and create a warehouse intake record.
    if status == "DELIVERED":
        # Mandatory check: current freshness must be > 0
        try:
            cur_f0 = float(getattr(shp, "current_freshness", None) or getattr(shp, "initial_freshness", None) or 0.0)
        except Exception:
            cur_f0 = 0.0
        if float(cur_f0) <= 0.0:
            return jsonify({"msg": "cannot confirm delivery: freshness is 0"}), 409

        try:
            shp.delivery_time = datetime.utcnow()
        except Exception:
            pass

        # Freeze freshness using the deterministic in-transit formula.
        prev = getattr(shp, "current_freshness", None)
        if prev is None:
            prev = getattr(shp, "initial_freshness", None)
        try:
            prev_f = float(prev or 0.0)
        except Exception:
            prev_f = 0.0

        try:
            initial_f = float(getattr(shp, "initial_freshness", None) or prev_f or 0.0)
        except Exception:
            initial_f = float(prev_f)

        started_at = getattr(shp, "transit_start_time", None) or getattr(shp, "pickup_confirmed_at", None)
        computed = _calc_in_transit_freshness(
            initial_freshness=float(initial_f),
            transit_start_time=started_at,
            crop=str(getattr(shp, "crop", "") or ""),
            now_utc=datetime.utcnow(),
        )

        base_final = min(float(prev_f), float(computed))

        # Deterministic penalty: temperature deviation vs crop optimal temp.
        optimal_t = _optimal_temp_c_for_crop(str(getattr(shp, "crop", "") or ""))
        observed_t = _observed_temp_c_for_shipment(shp)
        temp_dev = None
        try:
            if optimal_t is not None and observed_t is not None:
                temp_dev = float(abs(float(observed_t) - float(optimal_t)))
        except Exception:
            temp_dev = None

        try:
            shp.temperature_deviation = float(temp_dev) if temp_dev is not None else getattr(shp, "temperature_deviation", None)
        except Exception:
            pass

        # Deterministic penalty: transit delay above planned ETA.
        delay_h = 0.0
        try:
            if started_at is not None:
                actual_h = float((datetime.utcnow() - started_at).total_seconds() / 3600.0)
            else:
                actual_h = 0.0
            eta_h = float(getattr(shp, "eta_hours", None) or 0.0)
            if eta_h > 0.0:
                delay_h = max(0.0, float(actual_h) - float(eta_h))
        except Exception:
            delay_h = 0.0

        # Penalty rates tuned to be visible yet bounded.
        temp_penalty_rate = 0.003
        delay_penalty_rate = 0.002
        temp_penalty = float(temp_dev or 0.0) * float(temp_penalty_rate)
        delay_penalty = float(delay_h or 0.0) * float(delay_penalty_rate)

        penalized = float(base_final) - float(temp_penalty) - float(delay_penalty)
        penalized = _clamp01(float(penalized))
        final_f = min(float(base_final), float(penalized))
        try:
            shp.current_freshness = float(final_f)
        except Exception:
            pass

        try:
            b = CropBatch.query.get(int(getattr(shp, "batch_id", 0) or 0))
        except Exception:
            b = None
        if b is not None:
            try:
                final_f = getattr(shp, "current_freshness", None)
                if final_f is not None:
                    # CRITICAL: Farmer freshness is harvest-based and must remain immutable
                    # after pickup. Do not overwrite CropBatch.freshness_score here.
                    # Only write warehouse entry freshness for warehouse intake/forecasting.
                    try:
                        if getattr(b, "warehouse_entry_freshness", None) is None:
                            b.warehouse_entry_freshness = float(final_f)
                    except Exception:
                        pass
                    try:
                        if getattr(b, "warehouse_entry_date", None) is None:
                            b.warehouse_entry_date = date.today()
                    except Exception:
                        pass
                db.session.add(b)
            except Exception:
                pass

        # Alert logging: Delivered to warehouse
        try:
            ts = datetime.utcnow().isoformat() + "Z"
            det = (
                f"alert_type=DELIVERY_STATUS "
                f"alert_message=Delivered_to_warehouse "
                f"alert_status=DELIVERED "
                f"alert_timestamp={ts} "
                f"batch_id={getattr(shp, 'batch_id', None)} "
                f"shipment_id={getattr(shp, 'id', None)}"
            )
            db.session.add(DisasterEvent(
                location=str(getattr(shp, "destination_warehouse", None) or getattr(shp, "destination", None) or ""),
                region=str(getattr(shp, "destination_warehouse", None) or getattr(shp, "destination", None) or ""),
                event_type="DELIVERY_STATUS",
                severity="INFO",
                details=det,
            ))
        except Exception:
            pass

        try:
            db.session.add(BlockchainLog(action="deliver_confirm", reference_id=int(shp.id), batch_id=getattr(shp, "batch_id", None), shipment_id=int(shp.id), tx_hash="stub"))
        except Exception:
            pass

    db.session.add(shp)
    db.session.commit()
    if status == "DELIVERED":
        return jsonify({
            "msg": "delivery_confirmed",
            "shipment_id": int(getattr(shp, "id", 0) or 0),
            "status": shp.status,
        }), 200

    # For other status changes (e.g., IN_TRANSIT, CANCELLED), return a generic
    # confirmation so the frontend can react without relying on side effects.
    return jsonify({
        "msg": "status_updated",
        "shipment_id": int(getattr(shp, "id", 0) or 0),
        "status": shp.status,
    }), 200


@logistics_bp.post("/telemetry")
@roles_required(ROLE_LOGISTICS)
def submit_telemetry():
    data = request.get_json() or {}
    shipment_id = data.get("shipment_id")
    if not shipment_id:
        return jsonify({"msg": "shipment_id required"}), 400

    try:
        temperature = float(data.get("temperature"))
    except Exception:
        temperature = None
    try:
        temperature_deviation = float(data.get("temperature_deviation"))
    except Exception:
        temperature_deviation = None
    try:
        humidity = float(data.get("humidity"))
    except Exception:
        humidity = None

    claims = get_jwt() or {}
    logistics_id = claims.get("sub")

    shp = Shipment.query.filter_by(id=int(shipment_id)).first()
    if not shp:
        return jsonify({"msg": "shipment not found"}), 404

    st = str(getattr(shp, "status", "") or "").strip().upper()
    if st in {"DELIVERED", "CANCELLED"}:
        return jsonify({"msg": "shipment is closed"}), 409

    prev = getattr(shp, "current_freshness", None)
    if prev is None:
        prev = getattr(shp, "initial_freshness", None)
    try:
        prev_f = float(prev or 0.0)
    except Exception:
        prev_f = 0.0

    try:
        initial_f = float(getattr(shp, "initial_freshness", None) or prev_f or 0.0)
    except Exception:
        initial_f = float(prev_f)

    # Digital Twin freshness is stateful + monotonic and weather-modified.
    started_at = getattr(shp, "transit_start_time", None) or getattr(shp, "pickup_confirmed_at", None)
    last_upd = getattr(shp, "last_freshness_update", None)
    now = datetime.utcnow()

    # Prefer incoming telemetry weather values; fallback to last known values.
    temp_for_decay = temperature if temperature is not None else getattr(shp, "last_temperature", None)
    hum_for_decay = humidity if humidity is not None else getattr(shp, "last_humidity", None)

    new_f, _elapsed_h = _monotonic_transit_update(
        previous_freshness=float(prev_f),
        last_update_time=last_upd,
        transit_start_time=started_at,
        crop=str(getattr(shp, "crop", "") or ""),
        now_utc=now,
        temperature_c=temp_for_decay,
        humidity_pct=hum_for_decay,
    )
    shp.current_freshness = float(round(float(new_f), 6))
    shp.last_freshness_update = now
    shp.last_telemetry_at = datetime.utcnow()
    if temperature is not None:
        shp.last_temperature = float(temperature)
    if humidity is not None:
        shp.last_humidity = float(humidity)
    if temperature_deviation is not None:
        try:
            shp.temperature_deviation = float(abs(float(temperature_deviation)))
        except Exception:
            pass
    shp.status = "IN_TRANSIT"
    shp.updated_by = int(logistics_id) if logistics_id is not None else getattr(shp, "updated_by", None)

    db.session.add(shp)
    db.session.commit()
    return jsonify({
        "msg": "telemetry_recorded",
        "shipment_id": shp.id,
        "status": shp.status,
        "previous_freshness": float(prev_f),
        "current_freshness": float(shp.current_freshness or 0.0),
    })


@logistics_bp.post("/pickup_confirm")
@roles_required(ROLE_LOGISTICS)
def pickup_confirm():
    data = request.get_json() or {}
    shipment_id = data.get("shipment_id")
    if not shipment_id:
        return jsonify({"msg": "shipment_id required"}), 400

    claims = get_jwt() or {}
    logistics_id = claims.get("sub")

    shp = Shipment.query.filter_by(id=int(shipment_id)).first()
    if not shp:
        return jsonify({"msg": "shipment not found"}), 404

    # Allow confirming unassigned pickup requests, but forbid hijacking shipments
    # already assigned to a different logistics user.
    if logistics_id is not None:
        try:
            assigned = getattr(shp, "logistics_id", None)
            if assigned is not None and int(assigned) != int(logistics_id):
                return jsonify({"msg": "forbidden"}), 403
        except Exception:
            pass

    cur = str(getattr(shp, "status", "") or "").strip().upper()
    if cur in {"DELIVERED", "CANCELLED"}:
        return jsonify({"msg": "shipment is closed"}), 409

    # Strict flow: only PICKUP_REQUESTED can be confirmed.
    if cur != "PICKUP_REQUESTED":
        return jsonify({"msg": "pickup confirmation is available only for PICKUP_REQUESTED shipments"}), 409

    # Pickup confirmation transitions PICKUP_REQUESTED -> IN_TRANSIT without altering freshness.
    shp.status = "IN_TRANSIT"

    now = datetime.utcnow()
    # Transit starts on logistics confirmation.
    try:
        shp.transit_start_time = now
    except Exception:
        pass
    try:
        shp.pickup_confirmed_at = now
    except Exception:
        pass

    # Snapshot farmer-stage freshness into shipment.initial_freshness.
    snap = None
    try:
        b = CropBatch.query.get(int(getattr(shp, "batch_id", 0) or 0))
    except Exception:
        b = None
    if b is not None:
        snap = getattr(b, "farmer_freshness_snapshot", None)
        if snap is None:
            snap = getattr(b, "freshness_score", None)
    if snap is None:
        snap = getattr(shp, "current_freshness", None)
    if snap is None:
        snap = getattr(shp, "initial_freshness", None)

    # GLOBAL RULE: freshness is stored as float [0,1] everywhere.
    # Transit initialization rule: shipment.initial_freshness must equal farmer freshness snapshot.
    # Validation rule: if shipment freshness is higher than farmer freshness at transit start, block.
    farmer_snap = _clamp01(snap)
    # Persist farmer-facing snapshot to the batch if it hasn't been captured yet.
    # This keeps the farmer dashboard freshness stable even if logistics/warehouse
    # flows later update CropBatch.freshness_score.
    try:
        if b is not None and getattr(b, "farmer_freshness_snapshot", None) is None:
            b.farmer_freshness_snapshot = float(farmer_snap)
            db.session.add(b)
    except Exception:
        pass
    try:
        prev_init = getattr(shp, "initial_freshness", None)
        prev_cur = getattr(shp, "current_freshness", None)
        prev_max = None
        try:
            prev_vals = []
            if prev_init is not None:
                prev_vals.append(float(prev_init))
            if prev_cur is not None:
                prev_vals.append(float(prev_cur))
            prev_max = max(prev_vals) if prev_vals else None
        except Exception:
            prev_max = None
        # Legacy/previous data can sometimes have shipment freshness slightly higher than the
        # farmer snapshot. Do not block pickup; reconcile down to farmer_snap so the Digital
        # Twin remains consistent going forward.
        if prev_max is not None and float(_clamp01(prev_max)) > float(farmer_snap) + 1e-9:
            try:
                shp.initial_freshness = float(farmer_snap)
                shp.current_freshness = float(farmer_snap)
            except Exception:
                pass
    except Exception:
        pass
    try:
        shp.initial_freshness = float(farmer_snap)
        # Initialize current freshness to the snapshot; after this point, it is recalculated.
        shp.current_freshness = float(farmer_snap)
    except Exception:
        pass

    try:
        if logistics_id is not None and getattr(shp, "logistics_id", None) is None:
            shp.logistics_id = int(logistics_id)
    except Exception:
        pass
    db.session.add(shp)
    # Alert lifecycle: Pickup Requested -> Picked Up (do not delete prior alerts).
    try:
        batch_id = getattr(shp, "batch_id", None)
        ship_id = getattr(shp, "id", None)
        det = f"alert_type=PICKUP_STATUS alert_message=Crop_pickup_completed alert_status=PICKED_UP alert_timestamp={now.isoformat()}Z batch_id={batch_id} shipment_id={ship_id}"
        db.session.add(DisasterEvent(
            location=str(getattr(shp, "pickup_location", None) or ""),
            region=str(getattr(shp, "pickup_location", None) or ""),
            event_type="PICKUP_STATUS",
            severity="INFO",
            details=det,
        ))
    except Exception:
        pass

    # Optional audit event for traceability.
    try:
        db.session.add(BlockchainLog(action="PICKUP_CONFIRMED", reference_id=int(getattr(shp, "id", 0) or 0), batch_id=getattr(shp, "batch_id", None), shipment_id=int(getattr(shp, "id", 0) or 0), tx_hash="stub"))
    except Exception:
        pass

    db.session.commit()
    return jsonify({"msg": "pickup_confirmed", "shipment": {"id": shp.id, "status": shp.status}})




@logistics_bp.post("/route_advisory")
@roles_required(ROLE_LOGISTICS)
def route_advisory():
    data = request.get_json() or {}
    crop = str(data.get("crop") or "").strip()
    try:
        current_freshness = float(data.get("current_freshness"))
    except Exception:
        current_freshness = None
    try:
        expected_freshness = float(data.get("expected_freshness"))
    except Exception:
        expected_freshness = None
    try:
        additional_delay_hours = float(data.get("additional_delay_hours") or 0.0)
    except Exception:
        additional_delay_hours = 0.0
    risk_status = str(data.get("risk_status") or "").strip().upper()
    route_alert_summary = str(data.get("route_alert_summary") or "").strip()

    # Deterministic fallback (LLM optional). Must not choose routes or modify freshness.
    if not risk_status:
        if expected_freshness is not None:
            risk_status = _risk_status_from_freshness(float(expected_freshness))
        elif current_freshness is not None:
            risk_status = _risk_status_from_freshness(float(current_freshness))
        else:
            risk_status = "RISK"

    d = max(0.0, float(additional_delay_hours or 0.0))
    # Provide decision-support fields without reprinting raw API strings.
    if route_alert_summary:
        # Normalize raw API strings into readable risk summary.
        risk_summary = _risk_summary_from_alerts([{"title": str(route_alert_summary)}], predicted_delay_hours=d)
    else:
        risk_summary = _risk_summary_from_alerts([], predicted_delay_hours=d)
    decision = "Recommended" if d <= 0.25 else "Alternative"
    rec = _route_specific_action(tier=("recommended" if decision == "Recommended" else "alternative"), mode=str(data.get("mode") or "road"), crop=crop)
    exp = risk_summary

    # Advisory-only: attempt to use GenAI helper for better phrasing.
    # Must not choose routes or modify freshness; it only explains impact and suggests mitigation.
    try:
        adv = advise_route(route=str(data.get("route") or ""), mode=str(data.get("mode") or "road"), predicted_delay_hours=float(d), alerts=[])
        if isinstance(adv, dict):
            rr = str(adv.get("recommendation") or "").strip()
            ee = str(adv.get("explanation") or "").strip()
            if rr and ee:
                rec = rr
                exp = ee
    except Exception:
        pass

    # Keep explanation short and tied to provided context.
    if route_alert_summary and ("alert" not in exp.lower()):
        exp = exp + " Alerts detected along the route may contribute to delays."

    formatted = f"Route:\n{str(data.get('route') or '').strip()}\n\nRisk Summary:\n{exp}\n\nRecommended Action:\n{rec}\n\nDecision:\n{decision}".strip()

    return jsonify({
        "recommendation": rec,
        "explanation": exp,
        "decision": decision,
        "formatted": formatted,
        "context": {
            "crop": crop,
            "risk_status": risk_status,
        }
    })


@logistics_bp.post("/emergency-dispatch")
@roles_required(ROLE_LOGISTICS)
def emergency_dispatch():
    data = request.get_json() or {}
    shipment_id = data.get("shipment_id")
    
    if not shipment_id:
        return jsonify({"msg": "shipment_id required"}), 400
    
    # 1️⃣ Validate Request
    shp = Shipment.query.filter_by(id=int(shipment_id)).first()
    if not shp:
        return jsonify({"msg": "shipment not found"}), 404

    cur_status = str(getattr(shp, "status", "") or "").strip().upper()
    if cur_status != "EMERGENCY_REQUIRED":
        return jsonify({"msg": "Shipment not flagged for emergency dispatch", "required": "EMERGENCY_REQUIRED"}), 409

    batch = CropBatch.query.filter_by(id=shp.batch_id).first()
    if not batch:
        return jsonify({"msg": "batch not found"}), 404

    now = datetime.utcnow()
    # Update shipment and batch state using the existing session transaction
    try:
        shp.status = "ROUTED_FOR_SALVAGE"
        try:
            shp.updated_at = now
        except Exception:
            pass

        # Keep batch out of stored inventory views
        try:
            batch.status = "SALVAGE_PENDING"
        except Exception:
            pass
        try:
            batch.current_stage = "SALVAGE"
        except Exception:
            pass

        db.session.add(shp)
        db.session.add(batch)
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"Failed to execute emergency dispatch: {e}")
        return jsonify({"msg": "database error"}), 500

    return jsonify({
        "success": True,
        "shipment_id": int(shipment_id),
        "status": "ROUTED_FOR_SALVAGE",
        "message": "Shipment routed for salvage successfully."
    })

@logistics_bp.post("/confirm-salvage")
@roles_required(ROLE_LOGISTICS)
def confirm_salvage_completed():
    data = request.get_json() or {}
    salvage_id = data.get("salvage_id")
    shipment_id = data.get("shipment_id")
    if not salvage_id and not shipment_id:
        return jsonify({"msg": "salvage_id or shipment_id required"}), 400

    sb = None
    if salvage_id:
        try:
            sb = SalvageBatch.query.filter_by(id=int(salvage_id)).first()
        except Exception:
            sb = None

    shp = None
    if sb is None and shipment_id:
        try:
            shp = Shipment.query.filter_by(id=int(shipment_id)).first()
        except Exception:
            shp = None
        if shp is None:
            return jsonify({"msg": "shipment not found"}), 404

        cur_status = str(getattr(shp, "status", "") or "").strip().upper()
        if cur_status != "ROUTED_FOR_SALVAGE":
            return jsonify({"msg": "Shipment is not ready for salvage confirmation", "required": "ROUTED_FOR_SALVAGE"}), 409

        try:
            sb = SalvageBatch.query.filter_by(shipment_id=int(shp.id)).order_by(SalvageBatch.created_at.desc()).first()
        except Exception:
            sb = None

    if sb is None:
        return jsonify({"msg": "Salvage record not found for shipment"}), 404

    if shp is None:
        try:
            shp = Shipment.query.filter_by(id=int(sb.shipment_id)).first()
        except Exception:
            shp = None
    batch = None
    try:
        batch = CropBatch.query.filter_by(id=int(sb.batch_id)).first()
    except Exception:
        batch = None

    if shp is None:
        return jsonify({"msg": "shipment not found"}), 404

    cur_status = str(getattr(shp, "status", "") or "").strip().upper()
    if cur_status != "ROUTED_FOR_SALVAGE":
        return jsonify({"msg": "Shipment is not ready for salvage confirmation", "required": "ROUTED_FOR_SALVAGE"}), 409

    now = datetime.utcnow()
    try:
        sb.salvage_status = "FINALIZED"
        sb.completed_at = now
        shp.status = "FINALIZED"
        if batch is not None:
            batch.status = "FINALIZED"
            try:
                batch.current_stage = "FINALIZED"
            except Exception:
                pass

        db.session.add(sb)
        db.session.add(shp)
        if batch is not None:
            db.session.add(batch)
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"Failed to confirm salvage: {e}")
        return jsonify({"msg": "database error"}), 500

    return jsonify({"success": True, "salvage_id": int(sb.id), "status": "FINALIZED"})

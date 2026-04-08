import os
import logging
import time
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from backend.config import Config

logger = logging.getLogger(__name__)

LatLon = Tuple[float, float]



def _tomtom_route_summary(origin: LatLon, destination: LatLon) -> Dict[str, Any]:
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key:
        return {}
    (olat, olon) = origin
    (dlat, dlon) = destination
    r = requests.get(
        f"https://api.tomtom.com/routing/1/calculateRoute/{olat},{olon}:{dlat},{dlon}/json",
        params={
            "key": api_key,
            "traffic": "true",
        },
        timeout=15,
    )
    if not r.ok:
        return {}
    j = r.json() if r.content else {}
    routes = (j or {}).get("routes")
    if not (isinstance(routes, list) and routes):
        return {}
    summary = (routes[0] or {}).get("summary") or {}
    out = {
        "travel_time_s": summary.get("travelTimeInSeconds"),
        "traffic_delay_s": summary.get("trafficDelayInSeconds"),
        "no_traffic_travel_time_s": summary.get("noTrafficTravelTimeInSeconds"),
        "length_m": summary.get("lengthInMeters"),
    }
    return out if isinstance(out, dict) else {}

def _extract_weather_metrics(current: Dict[str, Any], forecast: Dict[str, Any]) -> Dict[str, Any]:
    vis = current.get("visibility")
    rain_mm_1h = None
    rain = (current.get("rain") or {}) if isinstance(current, dict) else {}
    if isinstance(rain, dict):
        v1 = rain.get("1h")
        if isinstance(v1, (int, float)):
            rain_mm_1h = float(v1)
        v3 = rain.get("3h")
        if rain_mm_1h is None and isinstance(v3, (int, float)):
            rain_mm_1h = float(v3) / 3.0

    max_fc_rain_mm_1h = None
    fc_list = forecast.get("list", []) if isinstance(forecast, dict) else []
    for item in (fc_list[:8] if isinstance(fc_list, list) else []):
        rain0 = (item or {}).get("rain") or {}
        if isinstance(rain0, dict):
            v3 = rain0.get("3h")
            if isinstance(v3, (int, float)):
                mm1h = float(v3) / 3.0
                max_fc_rain_mm_1h = mm1h if max_fc_rain_mm_1h is None else max(max_fc_rain_mm_1h, mm1h)

    return {
        "visibility_m": float(vis) if isinstance(vis, (int, float)) else None,
        "rain_mm_per_h": rain_mm_1h,
        "forecast_max_rain_mm_per_h": max_fc_rain_mm_1h,
    }

_ROUTE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_GEOCODE_CACHE: Dict[str, Tuple[float, Tuple[LatLon, str]]] = {}
_GEOCODE_CACHE_TTL_SEC = 24 * 3600

_OW_CACHE: Dict[Tuple[str, float, float], Tuple[float, Dict[str, Any]]] = {}
_OW_CACHE_TTL_SEC = 300

_INDIA_BBOX = (6.0, 68.0, 37.5, 97.5)  # min_lat, min_lon, max_lat, max_lon

_INDIA_ALERTS_CACHE: Tuple[float, Dict[str, Any]] = (0.0, {})
_USGS_EQ_CACHE: Tuple[float, List[Dict[str, Any]]] = (0.0, [])

_LOCAL_GAZETTEER: Dict[str, LatLon] = {
    # Common dashboard cities / India major cities
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
}


def _now_ts() -> float:
    return time.time()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_in_india(lat: float, lon: float) -> bool:
    try:
        min_lat, min_lon, max_lat, max_lon = _INDIA_BBOX
        return (min_lat <= float(lat) <= max_lat) and (min_lon <= float(lon) <= max_lon)
    except Exception:
        return False


def _clip_bbox_to_india(bbox: Tuple[float, float, float, float]) -> Optional[Tuple[float, float, float, float]]:
    if not bbox:
        return None
    min_lat, min_lon, max_lat, max_lon = bbox
    i_min_lat, i_min_lon, i_max_lat, i_max_lon = _INDIA_BBOX
    out = (
        max(min_lat, i_min_lat),
        max(min_lon, i_min_lon),
        min(max_lat, i_max_lat),
        min(max_lon, i_max_lon),
    )
    if out[0] > out[2] or out[1] > out[3]:
        return None
    return out


def _haversine_km(a: LatLon, b: LatLon) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def _sample_points_along_line(points: List[LatLon], max_points: int = 10) -> List[LatLon]:
    if not points:
        return []
    if len(points) <= max_points:
        return points
    idxs = [int(round(i * (len(points) - 1) / (max_points - 1))) for i in range(max_points)]
    out: List[LatLon] = []
    seen = set()
    for i in idxs:
        p = points[i]
        key = (round(p[0], 5), round(p[1], 5))
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _bbox(points: List[LatLon]) -> Optional[Tuple[float, float, float, float]]:
    if not points:
        return None
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return (min(lats), min(lons), max(lats), max(lons))


def _rank_from_text(text: str) -> int:
    t = (text or "").strip().lower()
    if t in {"red", "extreme", "severe"}:
        return 3
    if t in {"orange", "moderate"}:
        return 2
    if t in {"yellow", "minor"}:
        return 1
    return 1


def _severity_bucket(rank: int) -> str:
    if rank >= 3:
        return "high"
    if rank == 2:
        return "medium"
    return "low"


def _openweather_api_key() -> str:
    k = str(os.getenv("OPENWEATHER_API_KEY") or "").strip()
    if k:
        return k
    try:
        return str(getattr(Config, "OPENWEATHER_API_KEY", "") or "").strip()
    except Exception:
        return ""


def _openweather_current(lat: float, lon: float) -> Dict[str, Any]:
    api_key = _openweather_api_key()
    if not api_key:
        return {}
    key = ("current", round(lat, 2), round(lon, 2))
    now = _now_ts()
    cached = _OW_CACHE.get(key)
    if cached and (now - cached[0]) < _OW_CACHE_TTL_SEC:
        return cached[1]
    r = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        timeout=10,
    )
    if not r.ok:
        return {}
    j = r.json()
    out = j if isinstance(j, dict) else {}
    _OW_CACHE[key] = (now, out)
    return out


def _openweather_forecast(lat: float, lon: float) -> Dict[str, Any]:
    api_key = _openweather_api_key()
    if not api_key:
        return {}
    key = ("forecast", round(lat, 2), round(lon, 2))
    now = _now_ts()
    cached = _OW_CACHE.get(key)
    if cached and (now - cached[0]) < _OW_CACHE_TTL_SEC:
        return cached[1]
    r = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        timeout=10,
    )
    if not r.ok:
        return {}
    j = r.json()
    out = j if isinstance(j, dict) else {}
    _OW_CACHE[key] = (now, out)
    return out


def _parse_location(loc: Union[str, Dict[str, Any]]) -> Tuple[LatLon, str]:
    if isinstance(loc, dict):
        lat = loc.get("lat")
        lon = loc.get("lon")
        name = str(loc.get("name") or "").strip() or "point"
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return (float(lat), float(lon)), name
        raise ValueError("Invalid location dict; expected {lat, lon}")

    q = str(loc).strip()
    if not q:
        raise ValueError("Empty location")

    g = _LOCAL_GAZETTEER.get(q.lower())
    if g:
        return (float(g[0]), float(g[1])), q

    if "," in q:
        a, b = [p.strip() for p in q.split(",", 1)]
        try:
            lat = float(a)
            lon = float(b)
            return (lat, lon), q
        except Exception:
            pass

    cached = _GEOCODE_CACHE.get(q.lower())
    now = _now_ts()
    if cached and (now - cached[0]) < _GEOCODE_CACHE_TTL_SEC:
        return cached[1]

    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": q, "format": "json", "limit": 1},
        headers={"User-Agent": "finalyear-logistics-dashboard/1.0"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json() if r.content else []
    if not data:
        raise ValueError(f"Unable to geocode location: {q}")
    best = data[0] or {}
    lat = float(best.get("lat"))
    lon = float(best.get("lon"))
    name = str(best.get("display_name") or q)
    out = ((lat, lon), name)
    _GEOCODE_CACHE[q.lower()] = (now, out)
    return out


def _route_osrm(origin: LatLon, destination: LatLon) -> Dict[str, Any]:
    (olat, olon) = origin
    (dlat, dlon) = destination
    url = f"http://router.project-osrm.org/route/v1/driving/{olon},{olat};{dlon},{dlat}"
    r = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=15)
    r.raise_for_status()
    j = r.json()
    routes = j.get("routes") or []
    if not routes:
        raise ValueError("No route returned from OSRM")
    best = routes[0]
    geom = ((best.get("geometry") or {}).get("coordinates") or [])
    pts: List[LatLon] = [(float(lat), float(lon)) for (lon, lat) in geom if isinstance(lon, (int, float)) and isinstance(lat, (int, float))]
    return {
        "provider": "osrm",
        "distance_m": best.get("distance"),
        "duration_s": best.get("duration"),
        "points": pts,
    }


def _route_interpolated(origin: LatLon, destination: LatLon, steps: int = 20) -> Dict[str, Any]:
    (olat, olon) = origin
    (dlat, dlon) = destination
    pts: List[LatLon] = []
    steps = max(2, min(steps, 50))
    for i in range(steps):
        t = i / (steps - 1)
        lat = olat + (dlat - olat) * t
        lon = olon + (dlon - olon) * t
        pts.append((lat, lon))
    dist_km = _haversine_km(origin, destination)
    return {
        "provider": "interpolated",
        "distance_m": dist_km * 1000.0,
        "duration_s": None,
        "points": pts,
    }


def get_route_geometry(origin: Union[str, Dict[str, Any]], destination: Union[str, Dict[str, Any]], mode: str) -> Dict[str, Any]:
    o_pt, o_name = _parse_location(origin)
    d_pt, d_name = _parse_location(destination)
    mode_l = (mode or "road").lower()

    if mode_l in {"road", "rail"}:
        route = _route_osrm(o_pt, d_pt)
    else:
        route = _route_interpolated(o_pt, d_pt)

    return {
        "origin": {"name": o_name, "lat": o_pt[0], "lon": o_pt[1]},
        "destination": {"name": d_name, "lat": d_pt[0], "lon": d_pt[1]},
        "mode": mode_l,
        "route": {
            "provider": route["provider"],
            "distance_m": route.get("distance_m"),
            "duration_s": route.get("duration_s"),
            "geometry": [{"lat": p[0], "lon": p[1]} for p in route.get("points", [])],
        },
    }


def get_multileg_route_geometry(waypoints: List[Union[str, Dict[str, Any]]], mode: str) -> Dict[str, Any]:
    if not waypoints or len(waypoints) < 2:
        raise ValueError("At least origin and destination are required")

    mode_l = (mode or "road").lower()
    origin_pt, origin_name = _parse_location(waypoints[0])
    dest_pt, dest_name = _parse_location(waypoints[-1])

    all_points: List[LatLon] = []
    total_dist_m: float = 0.0
    total_dur_s: Optional[float] = 0.0

    for i in range(len(waypoints) - 1):
        a_pt, _ = _parse_location(waypoints[i])
        b_pt, _ = _parse_location(waypoints[i + 1])
        if mode_l in {"road", "rail"}:
            seg = _route_osrm(a_pt, b_pt)
        else:
            seg = _route_interpolated(a_pt, b_pt)

        pts_seg = seg.get("points") or []
        if i > 0 and pts_seg:
            pts_seg = pts_seg[1:]
        all_points.extend(pts_seg)

        dm = seg.get("distance_m")
        if isinstance(dm, (int, float)):
            total_dist_m += float(dm)

        ds = seg.get("duration_s")
        if isinstance(ds, (int, float)):
            total_dur_s = (total_dur_s or 0.0) + float(ds)
        else:
            total_dur_s = None

    provider = "osrm" if mode_l in {"road", "rail"} else "interpolated"
    return {
        "origin": {"name": origin_name, "lat": origin_pt[0], "lon": origin_pt[1]},
        "destination": {"name": dest_name, "lat": dest_pt[0], "lon": dest_pt[1]},
        "mode": mode_l,
        "route": {
            "provider": provider,
            "distance_m": total_dist_m or None,
            "duration_s": total_dur_s,
            "geometry": [{"lat": p[0], "lon": p[1]} for p in all_points],
        },
    }


def _to_legacy_alert_schema(alerts: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    mode_l = (mode or "").lower()
    if mode_l == "sea":
        default_event = "Maritime"
    elif mode_l == "air":
        default_event = "Aviation"
    elif mode_l in {"road", "rail"}:
        default_event = "Transport"
    else:
        default_event = "Alert"

    sev_map = {"low": "Minor", "medium": "Moderate", "high": "High", "info": "Info"}
    out: List[Dict[str, Any]] = []
    for a in alerts or []:
        atype = str(a.get("type") or "").strip().lower()
        subtype = str(a.get("subtype") or "").strip().lower()
        severity = str(a.get("severity") or "low").strip().lower()
        loc = a.get("location") or {}
        name = str(loc.get("name") or "").strip()
        when = str(a.get("time") or _iso_now())
        impact = str(a.get("impact") or "").strip()

        if atype == "disaster":
            eventtype = "Disaster"
        elif atype == "road":
            eventtype = "Road"
        elif atype == "weather":
            eventtype = "Weather"
        else:
            eventtype = default_event

        title = impact
        if name and name.lower() not in title.lower():
            title = f"{title} near {name}" if title else name
        if subtype and subtype not in title.lower():
            title = f"{subtype.replace('_', ' ').title()}: {title}" if title else subtype

        out.append({
            "eventtype": eventtype,
            "title": title or "Alert",
            "country": "IN",
            "alertlevel": sev_map.get(severity, "Minor"),
            "fromdate": when,
            "todate": when,
            "meta": a.get("meta"),
        })

    rank = {"high": 3, "severe": 3, "moderate": 2, "minor": 1, "info": 0, "unknown": 0}
    out.sort(key=lambda x: rank.get(str(x.get("alertlevel") or "").lower(), 0), reverse=True)
    return out[:25]


def _parse_route_text(route_text: str) -> List[str]:
    pts: List[str] = []
    for raw in str(route_text or "").replace("→", "->").split("->"):
        p = (raw or "").strip()
        if p:
            pts.append(p)
    return pts


def get_route_text_live_alerts(route_text: str, mode: str, refresh_seconds: int = 30) -> Dict[str, Any]:
    pts = _parse_route_text(route_text)
    if len(pts) < 2:
        raise ValueError("route_text must include at least origin and destination")
    return get_multileg_route_with_live_alerts(pts, mode=mode, refresh_seconds=refresh_seconds)


def _dedup_legacy_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for a in alerts or []:
        key = (
            str(a.get("eventtype") or "").strip().lower(),
            str(a.get("title") or "").strip().lower(),
            str(a.get("alertlevel") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def get_india_live_alerts(refresh_seconds: int = 300) -> Dict[str, Any]:
    now = _now_ts()
    global _INDIA_ALERTS_CACHE
    cached_ts, cached_val = _INDIA_ALERTS_CACHE
    if cached_val and (now - float(cached_ts or 0.0)) < max(30, int(refresh_seconds)):
        return cached_val

    # Representative points across India (kept small for performance)
    points: List[LatLon] = [
        (28.6139, 77.2090),  # Delhi
        (19.0760, 72.8777),  # Mumbai
        (13.0827, 80.2707),  # Chennai
        (22.5726, 88.3639),  # Kolkata
        (17.3850, 78.4867),  # Hyderabad
        (12.9716, 77.5946),  # Bengaluru
    ]

    alerts: List[Dict[str, Any]] = []

    # Always include a lightweight India-wide live weather snapshot (still live API data).
    # This avoids the dashboard showing None when conditions are normal but live monitoring is desired.
    try:
        if _openweather_api_key():
            for (lat, lon) in points[:6]:
                cur = _openweather_current(lat, lon)
                if not cur:
                    continue
                name = str(cur.get("name") or "").strip() or "India"
                weather = (cur.get("weather") or [{}])
                desc = str((weather[0] or {}).get("description") or "").strip()
                temp = ((cur.get("main") or {}) if isinstance(cur, dict) else {}).get("temp")
                wind = (cur.get("wind") or {}) if isinstance(cur, dict) else {}
                ws = wind.get("speed")
                parts = []
                if desc:
                    parts.append(desc)
                if isinstance(temp, (int, float)):
                    parts.append(f"{float(temp):.0f}°C")
                if isinstance(ws, (int, float)):
                    parts.append(f"wind {float(ws):.1f} m/s")
                impact = f"Current weather in {name}: " + (", ".join(parts) if parts else "live conditions")
                alerts.append({
                    "type": "weather",
                    "subtype": "current_conditions",
                    "severity": "low",
                    "location": {"lat": lat, "lon": lon, "name": name},
                    "time": _iso_now(),
                    "impact": impact,
                    "source": "openweather",
                })
    except Exception:
        pass

    try:
        alerts.extend(_weather_alerts(points, mode="road"))
    except Exception:
        pass
    try:
        alerts.extend(_tomtom_incidents(_INDIA_BBOX))
    except Exception:
        pass

    sev_rank = {"high": 3, "medium": 2, "low": 1}
    alerts.sort(key=lambda a: sev_rank.get(str(a.get("severity")), 1), reverse=True)

    legacy = _to_legacy_alert_schema(alerts, mode="road")
    legacy = _dedup_legacy_alerts(legacy)

    out = {
        "alerts": alerts[:50],
        "alerts_legacy": legacy[:50],
        "generated_at": _iso_now(),
        "refresh_seconds": int(refresh_seconds),
        "scope": "IN",
    }
    _INDIA_ALERTS_CACHE = (now, out)
    return out

def get_multileg_route_with_live_alerts(
    waypoints: List[Union[str, Dict[str, Any]]],
    mode: str,
    refresh_seconds: int = 30,
) -> Dict[str, Any]:
    mode_l = (mode or "road").lower()
    cache_key = f"MULTI|{mode_l}|" + "->".join([str(w) for w in waypoints])
    now = _now_ts()
    cached = _ROUTE_CACHE.get(cache_key)
    if cached and (now - cached[0]) < max(5, int(refresh_seconds)):
        return cached[1]

    geom = get_multileg_route_geometry(waypoints, mode_l)
    pts_xy = [(p["lat"], p["lon"]) for p in (geom.get("route") or {}).get("geometry", [])]
    pts_xy = [p for p in pts_xy if _is_in_india(p[0], p[1])]
    bbox = _clip_bbox_to_india(_bbox(pts_xy) or (0.0, 0.0, 0.0, 0.0))

    metrics: Dict[str, Any] = {
        "estimated_travel_time_s": (geom.get("route") or {}).get("duration_s"),
        "current_travel_time_s": None,
        "traffic_delay_minutes": None,
        "visibility_m": None,
        "rain_intensity_mm_per_h": None,
    }

    if mode_l == "road" and waypoints and len(waypoints) >= 2:
        try:
            o_pt, _ = _parse_location(waypoints[0])
            d_pt, _ = _parse_location(waypoints[-1])
            tt = _tomtom_route_summary(o_pt, d_pt)
            tts = tt.get("travel_time_s")
            tds = tt.get("traffic_delay_s")
            if isinstance(tts, (int, float)):
                metrics["current_travel_time_s"] = float(tts)
            if isinstance(tds, (int, float)):
                metrics["traffic_delay_minutes"] = round(float(tds) / 60.0, 1)
        except Exception:
            pass

    # Weather metrics sampled along the route
    try:
        vis_min = None
        rain_max = None
        for (lat, lon) in _sample_points_along_line(pts_xy, max_points=3):
            cur = _openweather_current(lat, lon)
            if not cur:
                continue
            fc = _openweather_forecast(lat, lon)
            wm = _extract_weather_metrics(cur, fc)
            v = wm.get("visibility_m")
            if isinstance(v, (int, float)):
                vis_min = v if vis_min is None else min(vis_min, v)
            r0 = wm.get("rain_mm_per_h")
            r1 = wm.get("forecast_max_rain_mm_per_h")
            for rv in [r0, r1]:
                if isinstance(rv, (int, float)):
                    rain_max = rv if rain_max is None else max(rain_max, rv)
        if isinstance(vis_min, (int, float)):
            metrics["visibility_m"] = float(vis_min)
        if isinstance(rain_max, (int, float)):
            metrics["rain_intensity_mm_per_h"] = round(float(rain_max), 2)
    except Exception:
        pass

    alerts: List[Dict[str, Any]] = []
    try:
        alerts.extend(_current_conditions_alerts(pts_xy, max_points=4))
    except Exception:
        pass
    
    # ---------------- Rule-based alerts (spec) ----------------
    try:
        now_iso = _iso_now()
        traffic_delay = metrics.get("traffic_delay_minutes")
        if isinstance(traffic_delay, (int, float)) and traffic_delay > 30:
            sev = "high" if traffic_delay >= 60 else "medium"
            alerts.append({
                "type": "road",
                "subtype": "traffic_congestion",
                "severity": sev,
                "location": geom.get("origin"),
                "time": now_iso,
                "impact": f"Traffic congestion detected (delay ~{int(round(float(traffic_delay)))} min)",
                "source": "tomtom" if os.getenv("TOMTOM_API_KEY") else "routing",
                "meta": {"traffic_delay_minutes": traffic_delay},
            })

        rain_int = metrics.get("rain_intensity_mm_per_h")
        if isinstance(rain_int, (int, float)) and rain_int >= 2.0:
            sev = "high" if rain_int >= 8.0 else "medium"
            alerts.append({
                "type": "weather",
                "subtype": "rain",
                "severity": sev,
                "location": geom.get("origin"),
                "time": now_iso,
                "impact": f"Weather disruption risk: rain intensity ~{rain_int:.1f} mm/h",
                "source": "openweather",
                "meta": {"rain_mm_per_h": rain_int},
            })

        vis_m = metrics.get("visibility_m")
        if isinstance(vis_m, (int, float)) and 0 < vis_m < 1500:
            sev = "high" if vis_m < 800 else "medium"
            alerts.append({
                "type": "weather",
                "subtype": "low_visibility",
                "severity": sev,
                "location": geom.get("origin"),
                "time": now_iso,
                "impact": f"Low visibility conditions: ~{int(round(float(vis_m)))} m",
                "source": "openweather",
                "meta": {"visibility_m": vis_m},
            })
    except Exception:
        pass
    try:
        alerts.extend(_weather_alerts(pts_xy, mode_l))
    except Exception:
        pass
    if bbox is not None:
        try:
            alerts.extend(_tomtom_incidents(bbox))
        except Exception:
            pass

    sev_rank = {"high": 3, "medium": 2, "low": 1}
    alerts.sort(key=lambda a: sev_rank.get(str(a.get("severity")), 1), reverse=True)

    out = {
        **geom,
        "metrics": metrics,
        "alerts": alerts,
        "alerts_legacy": _to_legacy_alert_schema(alerts, mode_l),
        "generated_at": _iso_now(),
        "refresh_seconds": int(refresh_seconds),
    }

    _ROUTE_CACHE[cache_key] = (now, out)
    return out

def _weather_alerts(points: List[LatLon], mode: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    mode_l = (mode or "").lower()

    for (lat, lon) in _sample_points_along_line(points, max_points=3):
        current = _openweather_current(lat, lon)
        if not current:
            continue

        name = str(current.get("name") or "en-route").strip() or "en-route"
        weather = (current.get("weather") or [{}])
        main = str((weather[0] or {}).get("main") or "").lower()
        desc = str((weather[0] or {}).get("description") or "").lower()
        vis = current.get("visibility")
        wind = (current.get("wind") or {})
        wind_speed = wind.get("speed")
        temp = (current.get("main") or {}).get("temp")

        # Forecast-based hazards (next ~24h)
        forecast = _openweather_forecast(lat, lon)
        fc_list = forecast.get("list", []) if isinstance(forecast, dict) else []
        flags = {
            "storm": False,
            "heavy_rain": False,
            "fog": False,
            "max_temp": float(temp) if isinstance(temp, (int, float)) else None,
        }
        for item in (fc_list[:8] if isinstance(fc_list, list) else []):
            w0 = ((item or {}).get("weather") or [{}])
            main0 = str((w0[0] or {}).get("main") or "").lower()
            desc0 = str((w0[0] or {}).get("description") or "").lower()
            if main0 == "thunderstorm" or "storm" in desc0:
                flags["storm"] = True
            if main0 in {"rain", "drizzle"}:
                rain = (item or {}).get("rain") or {}
                vol = rain.get("3h")
                if isinstance(vol, (int, float)) and vol >= 10:
                    flags["heavy_rain"] = True
            if main0 in {"mist", "fog", "haze"} or any(k in desc0 for k in ["fog", "mist", "haze"]):
                flags["fog"] = True
            t0 = ((item or {}).get("main") or {}).get("temp")
            if isinstance(t0, (int, float)):
                flags["max_temp"] = max(flags["max_temp"] or t0, t0)

        if isinstance(flags.get("max_temp"), (int, float)) and flags["max_temp"] >= 40:
            out.append({
                "type": "weather",
                "subtype": "heatwave",
                "severity": "high" if flags["max_temp"] >= 45 else "medium",
                "location": {"lat": lat, "lon": lon, "name": name},
                "time": _iso_now(),
                "impact": f"High temperature expected near {name} (up to {flags['max_temp']:.0f}°C) which may slow loading/unloading and driver endurance.",
                "source": "openweather",
            })

        if flags["storm"]:
            out.append({
                "type": "weather",
                "subtype": "storm",
                "severity": "high" if mode_l in {"sea", "air"} else "medium",
                "location": {"lat": lat, "lon": lon, "name": name},
                "time": _iso_now(),
                "impact": f"Storm conditions possible near {name} in the next 24h; expect disruption/delays.",
                "source": "openweather",
            })

        if flags["heavy_rain"]:
            out.append({
                "type": "weather",
                "subtype": "heavy_rain",
                "severity": "medium",
                "location": {"lat": lat, "lon": lon, "name": name},
                "time": _iso_now(),
                "impact": f"Heavy rain possible near {name} in the next 24h; higher accident risk and slower speeds.",
                "source": "openweather",
            })

        if flags["fog"] or (isinstance(vis, (int, float)) and 0 < vis < 1500):
            sev = "high" if mode_l == "air" else ("medium" if isinstance(vis, (int, float)) and vis < 800 else "low")
            out.append({
                "type": "weather",
                "subtype": "fog",
                "severity": sev,
                "location": {"lat": lat, "lon": lon, "name": name},
                "time": _iso_now(),
                "impact": f"Low visibility/fog near {name} may cause delays and safety risk.",
                "source": "openweather",
            })

        if isinstance(wind_speed, (int, float)) and wind_speed >= 15:
            out.append({
                "type": "weather",
                "subtype": "high_wind",
                "severity": "high" if wind_speed >= 20 else "medium",
                "location": {"lat": lat, "lon": lon, "name": name},
                "time": _iso_now(),
                "impact": f"High winds near {name} ({wind_speed:.1f} m/s) may impact stability and port/airport ops.",
                "source": "openweather",
            })

        if main in {"thunderstorm", "snow"} or "storm" in desc:
            out.append({
                "type": "weather",
                "subtype": "severe_weather",
                "severity": "high" if mode_l in {"sea", "air"} else "medium",
                "location": {"lat": lat, "lon": lon, "name": name},
                "time": _iso_now(),
                "impact": f"Severe weather near {name}: {desc or main}.",
                "source": "openweather",
            })

    # De-dup by subtype+rounded location
    dedup: Dict[Tuple[str, str, int, int], Dict[str, Any]] = {}
    for a in out:
        loc = a.get("location") or {}
        key = (str(a.get("type")), str(a.get("subtype")), int(round(float(loc.get("lat", 0)) * 10)), int(round(float(loc.get("lon", 0)) * 10)))
        if key not in dedup:
            dedup[key] = a
    return list(dedup.values())[:25]


def _current_conditions_alerts(points: List[LatLon], max_points: int = 4) -> List[Dict[str, Any]]:
    if not points:
        return []
    if not _openweather_api_key():
        return []

    out: List[Dict[str, Any]] = []
    for (lat, lon) in _sample_points_along_line(points, max_points=max(2, min(int(max_points), 8))):
        cur = _openweather_current(lat, lon)
        if not cur:
            continue
        name = str(cur.get("name") or "en-route").strip() or "en-route"
        weather = (cur.get("weather") or [{}])
        desc = str((weather[0] or {}).get("description") or "").strip()
        temp = ((cur.get("main") or {}) if isinstance(cur, dict) else {}).get("temp")
        wind = (cur.get("wind") or {}) if isinstance(cur, dict) else {}
        ws = wind.get("speed")
        parts: List[str] = []
        if desc:
            parts.append(desc)
        if isinstance(temp, (int, float)):
            parts.append(f"{float(temp):.0f}°C")
        if isinstance(ws, (int, float)):
            parts.append(f"wind {float(ws):.1f} m/s")
        title = f"Current conditions near {name}: " + (", ".join(parts) if parts else "live conditions")
        out.append({
            "type": "weather",
            "subtype": "current_conditions",
            "severity": "low",
            "location": {"lat": float(lat), "lon": float(lon), "name": name},
            "time": _iso_now(),
            "impact": title,
            "source": "openweather",
        })

    dedup: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
    for a in out:
        loc = a.get("location") or {}
        key = (str(a.get("subtype")), int(round(float(loc.get("lat", 0)) * 10)), int(round(float(loc.get("lon", 0)) * 10)))
        if key not in dedup:
            dedup[key] = a
    return list(dedup.values())[:25]


def _gdacs_events() -> List[Dict[str, Any]]:
    r = requests.get(
        "https://www.gdacs.org/gdacsapi/api/events/geteventlist/JSON",
        params={"alertlevel": "Orange,Red"},
        timeout=15,
    )
    if not r.ok:
        return []
    j = r.json()
    feats = j.get("features", []) if isinstance(j, dict) else []
    return feats if isinstance(feats, list) else []


def _usgs_eq_events() -> List[Dict[str, Any]]:
    now = _now_ts()
    cached_ts, cached_val = _USGS_EQ_CACHE
    if cached_val and (now - float(cached_ts or 0.0)) < 300:
        return cached_val

    try:
        r = requests.get(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
            timeout=15,
        )
        if not r.ok:
            _USGS_EQ_CACHE = (now, [])
            return []
        j = r.json() if r.content else {}
        feats = (j or {}).get("features") or []
        feats = feats if isinstance(feats, list) else []
        _USGS_EQ_CACHE = (now, feats)
        return feats
    except Exception:
        _USGS_EQ_CACHE = (now, [])
        return []


def _usgs_eq_alerts(points: List[LatLon], buffer_km: float = 150.0) -> List[Dict[str, Any]]:
    if not points:
        return []
    sampled = _sample_points_along_line(points, max_points=18)
    out: List[Dict[str, Any]] = []

    for f in _usgs_eq_events():
        props = (f or {}).get("properties") or {}
        geom = (f or {}).get("geometry") or {}
        coords = geom.get("coordinates")
        if not (isinstance(coords, list) and len(coords) >= 2):
            continue
        lon = coords[0]
        lat = coords[1]
        if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
            continue

        ev_pt = (float(lat), float(lon))
        if not _is_in_india(ev_pt[0], ev_pt[1]):
            continue

        dmin = min(_haversine_km(ev_pt, p) for p in sampled)
        if dmin > buffer_km:
            continue

        mag = props.get("mag")
        sev_rank = 1
        if isinstance(mag, (int, float)):
            if float(mag) >= 6.0:
                sev_rank = 3
            elif float(mag) >= 5.0:
                sev_rank = 2

        place = str(props.get("place") or "").strip()
        title = "Earthquake detected"
        if isinstance(mag, (int, float)):
            title = f"Earthquake M{float(mag):.1f}"
        if place:
            title = f"{title} near {place}"

        t_ms = props.get("time")
        when = _iso_now()
        try:
            if isinstance(t_ms, (int, float)):
                when = datetime.fromtimestamp(float(t_ms) / 1000.0, tz=timezone.utc).isoformat()
        except Exception:
            when = _iso_now()

        out.append({
            "type": "disaster",
            "subtype": "earthquake",
            "severity": _severity_bucket(sev_rank),
            "location": {"lat": ev_pt[0], "lon": ev_pt[1], "name": "India"},
            "time": when,
            "impact": title,
            "source": "usgs",
            "meta": {
                "magnitude": mag,
                "distance_to_route_km": round(dmin, 1),
                "url": props.get("url"),
            },
        })

    return out[:25]


def _gdacs_alerts(points: List[LatLon], buffer_km: float = 75.0) -> List[Dict[str, Any]]:
    if not points:
        return []
    sampled = _sample_points_along_line(points, max_points=18)
    out: List[Dict[str, Any]] = []
    for f in _gdacs_events():
        geom = (f or {}).get("geometry") or {}
        coords = geom.get("coordinates")
        if not (isinstance(coords, list) and len(coords) >= 2):
            continue
        lon = coords[0]
        lat = coords[1]
        if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
            continue
        ev_pt = (float(lat), float(lon))
        if not _is_in_india(ev_pt[0], ev_pt[1]):
            continue

        # nearest sampled point distance
        dmin = min(_haversine_km(ev_pt, p) for p in sampled)
        if dmin > buffer_km:
            continue

        p = (f or {}).get("properties") or {}
        alertlevel = str(p.get("alertlevel") or "").strip()
        rank = _rank_from_text(alertlevel)
        out.append({
            "type": "disaster",
            "subtype": str(p.get("eventtype") or "event").lower(),
            "severity": _severity_bucket(rank),
            "location": {"lat": ev_pt[0], "lon": ev_pt[1], "name": str(p.get("country") or "")},
            "time": str(p.get("fromdate") or p.get("pubdate") or _iso_now()),
            "impact": str(p.get("title") or "Potential disruption near route"),
            "source": "gdacs",
            "meta": {
                "gdacs_id": p.get("eventid"),
                "alertlevel": alertlevel,
                "distance_to_route_km": round(dmin, 1),
                "url": p.get("url"),
            },
        })

    return out[:25]


def _tomtom_incidents(bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key:
        return []

    min_lat, min_lon, max_lat, max_lon = bbox
    # TomTom expects bbox as "minLon,minLat,maxLon,maxLat"
    bbox_str = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    r = requests.get(
        "https://api.tomtom.com/traffic/services/5/incidentDetails",
        params={
            "key": api_key,
            "bbox": bbox_str,
            "fields": "{incidents{type,properties{iconCategory,magnitudeOfDelay,events{code,description,extraDescription,iconCategory},startTime,endTime},geometry{type,coordinates}}}",
            "language": "en-GB",
            "timeValidityFilter": 43200,
        },
        timeout=15,
    )
    if not r.ok:
        return []

    j = r.json() if r.content else {}
    incidents = (((j or {}).get("incidents") or {}).get("incidents") or [])
    if not isinstance(incidents, list):
        return []

    out: List[Dict[str, Any]] = []
    for inc in incidents[:50]:
        props = (inc or {}).get("properties") or {}
        geom = (inc or {}).get("geometry") or {}
        coords = geom.get("coordinates")
        pt: Optional[LatLon] = None
        if isinstance(coords, list) and coords:
            # take first coordinate of a line/polygon/point
            first = coords[0]
            if isinstance(first, list) and len(first) >= 2 and isinstance(first[0], (int, float)):
                # may be [lon,lat]
                pt = (float(first[1]), float(first[0]))
            elif isinstance(first, (int, float)) and len(coords) >= 2:
                pt = (float(coords[1]), float(coords[0]))

        magnitude = props.get("magnitudeOfDelay")
        rank = 1
        if isinstance(magnitude, (int, float)):
            if magnitude >= 5:
                rank = 3
            elif magnitude >= 3:
                rank = 2

        out.append({
            "type": "road",
            "subtype": "traffic_incident",
            "severity": _severity_bucket(rank),
            "location": {"lat": pt[0], "lon": pt[1], "name": ""} if pt else None,
            "time": str(props.get("startTime") or _iso_now()),
            "impact": str(((props.get("events") or [{}])[0] or {}).get("description") or "Traffic incident / disruption"),
            "source": "tomtom",
            "meta": {
                "iconCategory": props.get("iconCategory"),
                "magnitudeOfDelay": magnitude,
                "endTime": props.get("endTime"),
            },
        })

    return out[:25]


def get_route_with_live_alerts(
    origin: Union[str, Dict[str, Any]],
    destination: Union[str, Dict[str, Any]],
    mode: str,
    refresh_seconds: int = 30,
) -> Dict[str, Any]:
    mode_l = (mode or "road").lower()
    cache_key = f"{str(origin)}|{str(destination)}|{mode_l}"
    now = _now_ts()

    cached = _ROUTE_CACHE.get(cache_key)
    if cached and (now - cached[0]) < max(5, int(refresh_seconds)):
        return cached[1]

    geom = get_route_geometry(origin, destination, mode_l)
    pts = [(p["lat"], p["lon"]) for p in (geom.get("route") or {}).get("geometry", [])]

    pts = [p for p in pts if _is_in_india(p[0], p[1])]
    bbox = _clip_bbox_to_india(_bbox(pts) or (0.0, 0.0, 0.0, 0.0))

    alerts: List[Dict[str, Any]] = []
    try:
        alerts.extend(_current_conditions_alerts(pts, max_points=4))
    except Exception:
        pass
    try:
        alerts.extend(_weather_alerts(pts, mode_l))
    except Exception:
        pass

    if bbox is not None:
        try:
            alerts.extend(_tomtom_incidents(bbox))
        except Exception:
            pass

    sev_rank = {"high": 3, "medium": 2, "low": 1}
    alerts.sort(key=lambda a: sev_rank.get(str(a.get("severity")), 1), reverse=True)

    out = {
        **geom,
        "alerts": alerts,
        "generated_at": _iso_now(),
        "refresh_seconds": int(refresh_seconds),
    }

    _ROUTE_CACHE[cache_key] = (now, out)
    return out

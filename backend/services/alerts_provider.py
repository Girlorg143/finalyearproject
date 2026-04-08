import os
import sys
from typing import List, Dict

# Attempt to import the uploaded food_logistics live alerts module
# The folder name contains a space, so we build the absolute path explicitly.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
_FOOD_LOGISTICS_DIRS = [
    os.path.join(_PROJECT_ROOT, "food_logistics zip"),
    os.path.join(_PROJECT_ROOT, "food_logistics"),  # alternative if user renames
]

_live_mod = None
_india_mod = None
for _d in _FOOD_LOGISTICS_DIRS:
    if os.path.isdir(_d) and _d not in sys.path:
        sys.path.insert(0, _d)
    try:
        # Module name as in the uploaded folder
        import live_alerts as _live_mod  # type: ignore
        _live_mod = _live_mod
    except Exception:
        _live_mod = None
try:
    import india_live_alerts as _india_mod  # type: ignore
except Exception:
    _india_mod = None


def _normalize_alerts(alerts: List[Dict]) -> List[Dict]:
    """Map food_logistics.live_alerts schema to our API schema.
    Expected keys from provider: event, severity, urgency, area, start, end, optional risk_score
    Output keys: eventtype, title, country, alertlevel, fromdate, todate, risk_score
    """
    out: List[Dict] = []
    for a in alerts or []:
        out.append({
            "eventtype": a.get("event"),
            "title": a.get("area"),
            "country": "US",  # source is weather.gov
            "alertlevel": a.get("severity"),
            "fromdate": a.get("start"),
            "todate": a.get("end"),
            "risk_score": a.get("risk_score"),
        })
    return out


def get_live_alerts() -> List[Dict]:
    """Fetch live alerts from the uploaded provider if available.
    Falls back to empty list if module or network is unavailable.
    """
    out: List[Dict] = []
    # NOAA-based global provider
    if _live_mod is not None:
        try:
            data = _live_mod.fetch_live_alerts()
            alerts = _live_mod.extract_alerts(data)
            if hasattr(_live_mod, "add_risk_scores"):
                alerts = _live_mod.add_risk_scores(alerts)
            out.extend(_normalize_alerts(alerts))
        except Exception:
            pass
    # India-focused alerts (subset by Indian seas/states)
    if _india_mod is not None:
        try:
            alerts_in = _india_mod.fetch_india_alerts()
            if hasattr(_india_mod, "add_india_risk"):
                alerts_in = _india_mod.add_india_risk(alerts_in)
            # Normalize similar to NOAA mapping
            for a in alerts_in or []:
                out.append({
                    "eventtype": a.get("event"),
                    "title": a.get("area"),
                    "country": "IN",
                    "alertlevel": a.get("severity"),
                    "fromdate": a.get("time"),
                    "todate": a.get("time"),
                    "risk_score": a.get("risk_score"),
                })
        except Exception:
            pass
    return out


def find_alerts_for_route(route_text: str) -> List[Dict]:
    """Return alerts relevant to the given route by substring matching on area/event.
    """
    if not route_text:
        return []
    route_l = route_text.lower()
    # Derive keywords from common ports/places to improve matching
    kw = set()
    if "vizag" in route_l or "visakhapatnam" in route_l:
        kw.update(["vizag", "visakhapatnam", "andhra pradesh", "east coast"])
    if "colombo" in route_l:
        kw.update(["colombo", "sri lanka", "lka"])
    if "dubai" in route_l or "jebel ali" in route_l:
        kw.update(["dubai", "jebel ali", "uae", "united arab emirates"])
    # Fallback to splitting on arrows/-> and spaces
    for token in [p.strip() for p in route_text.replace("→", "->").split("->")]:
        if token:
            kw.add(token.lower())

    def match_norm(alert: Dict) -> bool:
        title = (str(alert.get("title", "")) + " " + str(alert.get("country", ""))).lower()
        for k in kw:
            if k and k in title:
                return True
        return False

    out: List[Dict] = []
    # NOAA provider
    if _live_mod is not None:
        try:
            data = _live_mod.fetch_live_alerts()
            alerts = _live_mod.extract_alerts(data)
            if hasattr(_live_mod, "add_risk_scores"):
                alerts = _live_mod.add_risk_scores(alerts)
            for a in alerts:
                a_norm = {
                    "eventtype": a.get("event"),
                    "title": a.get("area"),
                    "country": "US",
                    "alertlevel": a.get("severity"),
                    "fromdate": a.get("start"),
                    "todate": a.get("end"),
                    "risk_score": a.get("risk_score"),
                }
                if match_norm(a_norm):
                    out.append(a_norm)
        except Exception:
            pass
    # India provider
    if _india_mod is not None:
        try:
            alerts_in = _india_mod.fetch_india_alerts()
            if hasattr(_india_mod, "add_india_risk"):
                alerts_in = _india_mod.add_india_risk(alerts_in)
            for a in alerts_in or []:
                a_norm = {
                    "eventtype": a.get("event"),
                    "title": a.get("area"),
                    "country": "IN",
                    "alertlevel": a.get("severity"),
                    "fromdate": a.get("time"),
                    "todate": a.get("time"),
                    "risk_score": a.get("risk_score"),
                }
                if match_norm(a_norm):
                    out.append(a_norm)
        except Exception:
            pass
    return out

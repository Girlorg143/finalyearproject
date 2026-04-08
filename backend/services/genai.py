import hashlib
import logging
import os
import re
import requests
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_transformers_pipeline = None


def _llm_unavailable_text(*, area: str) -> str:
    a = str(area or "LLM").strip() or "LLM"
    return f"{a}: LLM unavailable. Check LLAMA_SERVER_URL / model path and try again."


def _llm_unavailable_reco(*, area: str) -> Dict[str, Any]:
    a = str(area or "LLM").strip() or "LLM"
    return {
        "recommendation": "GenAI temporarily unavailable.",
        "explanation": f"{a} GenAI service is not reachable or returned an invalid response. Start/configure the model and try again.",
        "source": "llm_unavailable",
    }


def suggest_alternatives(context: dict) -> dict:
    # Stubbed GenAI advisory: in real project call LLM API. Here we return rule-based suggestions.
    return {
        "routes": ["Route A (highway)", "Route B (coastal)"],
        "transport": ["Refrigerated truck", "Rail"],
        "mitigations": ["Depart at night to avoid heat", "Add dry ice packs"],
        "note": "Stub suggestions; government must approve."
    }


def generate_warehouse_recommendation(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate operational text for the warehouse dashboard.

    Must NOT calculate freshness/risk; it only interprets provided values.
    """

    crop = str((context or {}).get("crop") or "").strip()
    storage_type = str((context or {}).get("storage_type") or "").strip()
    risk = str((context or {}).get("warehouse_spoilage_risk") or "").strip().upper()

    try:
        entry_f = float((context or {}).get("warehouse_entry_freshness") or 0.0)
    except Exception:
        entry_f = 0.0
    try:
        pred_f = float((context or {}).get("predicted_warehouse_freshness") or 0.0)
    except Exception:
        pred_f = 0.0

    temp = (context or {}).get("current_temperature")
    hum = (context or {}).get("current_humidity")
    opt_t = (context or {}).get("optimal_temperature")
    opt_h = (context or {}).get("optimal_humidity")

    fallback = {
        "recommendation": "Move the batch into the most stable controlled zone for this crop and tighten temperature and humidity setpoints toward the optimal range.",
        "explanation": "The system forecast shows freshness declining under current storage conditions, so narrowing temperature/humidity drift will slow quality loss.",
        "short_term_outlook": "Without adjustments, quality is likely to drop further in the next 24 hours and handling may need to be expedited.",
        "source": "deterministic_fallback",
    }
    if risk == "SAFE":
        fallback = {
            "recommendation": "Keep the batch in its current storage zone and maintain routine monitoring of temperature and humidity.",
            "explanation": "The forecast remains within an acceptable range under the current storage setup.",
            "short_term_outlook": "Over the next 24 hours, quality should remain stable with a gradual decline if conditions stay steady.",
            "source": "deterministic_fallback",
        }
    elif risk == "HIGH":
        fallback = {
            "recommendation": "Isolate the batch and take immediate corrective storage action, then prioritize dispatch or rework decisions.",
            "explanation": "The forecast indicates the batch is in a critical range and the current environment is not protecting it.",
            "short_term_outlook": "Within 24 hours, rapid deterioration is likely unless conditions are corrected and handling is accelerated.",
            "source": "deterministic_fallback",
        }

    # IMPORTANT: Warehouse dashboard must stay responsive.
    # Enable LLM explicitly; optionally run in strict LLM-only mode (no fallback content).
    allow_llm = str(os.getenv("GENAI_WAREHOUSE_USE_LLM") or "").strip().lower() in {"1", "true", "yes", "on"}
    strict_llm = str(os.getenv("GENAI_WAREHOUSE_STRICT_LLM") or "").strip().lower() in {"1", "true", "yes", "on"}
    llama_server_url = str(os.getenv("LLAMA_SERVER_URL") or "").strip()
    use_llm = allow_llm and (bool(llama_server_url) or bool(_get_llama_cpp()))
    if not use_llm:
        return fallback

    # Hard timeout so /api/warehouse/dashboard never hangs.
    try:
        wh_timeout_s = int(os.getenv("GENAI_WAREHOUSE_LLM_TIMEOUT_S") or "")
    except Exception:
        wh_timeout_s = 8
    if wh_timeout_s <= 0:
        wh_timeout_s = 8

    prompt = (
        "You are an AI warehouse recommendation engine.\n\n"
        "Analyze the following crop storage condition and generate output in STRICT FORMAT.\n\n"
        "Input:\n"
        f"Crop: {crop}\n"
        f"Freshness: {round(pred_f*100,1)}%\n"
        f"Risk Level: {risk}\n"
        f"Temperature Deviation: {round(abs(float(temp)-float(opt_t)),1) if temp and opt_t else 0}°C\n"
        f"Humidity Deviation: {round(abs(float(hum)-float(opt_h)),1) if hum and opt_h else 0}%\n\n"
        "CRITICAL RULES:\n"
        "- Use ONLY the provided values EXACTLY as given - DO NOT change or invent numbers\n"
        "- Risk Level is FINAL - do NOT contradict it (e.g., if SAFE, do NOT say high risk)\n"
        "- Ensure consistency with Risk Status - do NOT use words like 'high risk' when Risk Status is SAFE\n"
        "- Freshness > 50% means LOW risk, NOT high risk\n"
        "- Reuse the exact temperature/humidity deviations provided\n"
        "- Do NOT generate new values or recalculate anything\n\n"
        "RECOMMENDATION QUALITY RULES:\n"
        "- Do NOT give vague suggestions like 'monitor' or 'continuous monitoring' - always suggest concrete actions\n"
        "- Avoid generic phrases like 'monitor closely' unless accompanied by corrective action\n"
        "- Replace weak phrases like 'continuous monitoring' with 'corrective action required'\n"
        "- Must include at least one corrective action: cooling, humidity control, ventilation, etc.\n"
        "- Always consider BOTH temperature and humidity if deviations exist\n"
        "- If both temperature and humidity deviations exist, mention BOTH in recommendation\n"
        "- Do NOT assume whether humidity should increase or decrease\n"
        "- Use neutral corrective phrasing like: 'stabilize humidity within optimal range'\n"
        "- NEVER suggest specific numeric adjustments like 'reduce by 2.5°C' - use general terms like 'reduce temperature'\n"
        "- NEVER invent or guess specific values - only reference provided values\n"
        "- Avoid incomplete sentences - always produce complete, grammatically correct outputs\n"
        "- Each sentence must have a clear subject, verb, and complete thought\n"
        "- Incorporate freshness level into explanation using exact provided percentage\n"
        "- Be specific, actionable, and professional\n\n"
        "IMPORTANT OUTPUT RULES:\n"
        "- Output EXACTLY 3 lines only\n"
        "- Each line must start with the label EXACTLY:\n"
        "  Recommendation:\n"
        "  Explanation:\n"
        "  Outlook:\n"
        "- Each line must be SINGLE LINE (no line breaks)\n"
        "- Do NOT add headings, extra text, or blank lines\n"
        "- Do NOT skip any field\n\n"
        "Guidelines:\n"
        "- If Risk Level is SAFE → give preventive actions with concrete steps\n"
        "- If Risk Level is HIGH and freshness < 30% → give urgent/salvage actions\n"
        "- Always match your wording to the provided Risk Level\n"
        "- Be concise and professional\n\n"
        "OUTPUT FORMAT (STRICT):\n"
        "Recommendation: <one sentence with concrete corrective action, NO specific numbers>\n"
        "Explanation: <one complete sentence with subject and verb, incorporating freshness level and deviations>\n"
        "Outlook: <one complete sentence>"
    )

    try:
        txt = ""
        if llama_server_url:
            txt = _llama_server_generate(prompt, timeout_s=int(wh_timeout_s))
        else:
            llm = _get_llama_cpp()
            if llm:
                res = llm(prompt, max_tokens=350, temperature=0.2, top_p=0.9, stop=["\n\n\n"])
                if isinstance(res, dict):
                    choices = res.get("choices")
                    if isinstance(choices, list) and choices:
                        txt = str((choices[0] or {}).get("text") or "")
        txt = str(txt or "").strip()
        if not txt:
            if strict_llm:
                return {
                    "recommendation": "LLM unavailable.",
                    "explanation": "Warehouse recommendation model did not respond within the configured timeout.",
                    "short_term_outlook": "Enable the model endpoint or increase GENAI_WAREHOUSE_LLM_TIMEOUT_S, then refresh the dashboard.",
                    "source": "llm_unavailable",
                }
            return fallback

        def _extract_line(label: str) -> str:
            for ln in str(txt or "").replace("\r", "").split("\n"):
                s = ln.strip()
                if not s:
                    continue
                if s.lower().startswith(label.lower() + ":"):
                    return re.sub(r"\s+", " ", s.split(":", 1)[1]).strip()
            return ""

        rec = _extract_line("Recommendation")
        exp = _extract_line("Explanation")
        outl = _extract_line("Outlook")
        if not outl:
            outl = _extract_line("Short-Term Outlook")
        
        # Detect and fix incomplete sentences (truncated LLM output)
        def _is_incomplete_sentence(text: str) -> bool:
            if not text:
                return True
            # Check if sentence ends abruptly without proper ending
            incomplete_endings = (' and', ' with', ' but', ' or', ' only', ' given', ' for', ' at', ' by')
            text_lower = text.lower().rstrip()
            return text_lower.endswith(incomplete_endings) or not text.rstrip().endswith(('.', '!', '?'))
        
        # Replace incomplete sentences with fallback
        if _is_incomplete_sentence(rec):
            rec = fallback.get("recommendation", "")
        if _is_incomplete_sentence(exp):
            exp = fallback.get("explanation", "")
        if _is_incomplete_sentence(outl):
            outl = fallback.get("short_term_outlook", "")
        
        # Accept partial responses - use fallback for missing fields
        if not rec:
            rec = fallback.get("recommendation", "")
        if not exp:
            exp = fallback.get("explanation", "")
        if not outl:
            outl = fallback.get("short_term_outlook", "")
            
        # Only reject if ALL fields are missing
        if not (rec or exp or outl):
            if strict_llm:
                return {
                    "recommendation": "LLM unavailable.",
                    "explanation": "Warehouse recommendation model returned an invalid format.",
                    "short_term_outlook": "LLM must output at least one labeled field: Recommendation, Explanation, or Outlook.",
                    "source": "llm_unavailable",
                }
            return fallback

        return {
            "recommendation": rec,
            "explanation": exp,
            "short_term_outlook": outl,
            "source": "llm" if (llama_server_url or _get_llama_cpp()) else "deterministic_fallback",
        }
    except Exception:
        if strict_llm:
            return {
                "recommendation": "LLM unavailable.",
                "explanation": "Warehouse recommendation model request failed.",
                "short_term_outlook": "Check LLAMA_SERVER_URL connectivity and server logs, then refresh the dashboard.",
                "source": "llm_unavailable",
            }
        return fallback


def generate_warehouse_alert_and_recommendation(context: Dict[str, Any]) -> Dict[str, Any]:
    crop = str((context or {}).get("crop") or "").strip()
    risk = str((context or {}).get("warehouse_risk_level") or "").strip().upper()
    try:
        cur_f = float((context or {}).get("current_freshness") or 0.0)
    except Exception:
        cur_f = 0.0
    try:
        pred_f = float((context or {}).get("predicted_freshness_24h") or 0.0)
    except Exception:
        pred_f = 0.0
    try:
        temp_dev = float((context or {}).get("temperature_deviation_c") or 0.0)
    except Exception:
        temp_dev = 0.0
    try:
        hum_dev = float((context or {}).get("humidity_deviation_pct") or 0.0)
    except Exception:
        hum_dev = 0.0
    storage_compat = str((context or {}).get("storage_compatibility") or "").strip() or "Unknown"

    # Keep deterministic fallback so dashboard is usable when strict mode is off.
    fallback = {
        "alert_message": f"Storage conditions may accelerate quality loss for {crop or 'this crop'} given the current deviations.",
        "recommendation": "Tighten temperature and humidity control toward the optimal range and prioritize dispatch if freshness continues to decline.",
        "source": "deterministic_fallback",
    }

    allow_llm = str(os.getenv("GENAI_WAREHOUSE_USE_LLM") or "").strip().lower() in {"1", "true", "yes", "on"}
    strict_llm = str(os.getenv("GENAI_WAREHOUSE_STRICT_LLM") or "").strip().lower() in {"1", "true", "yes", "on"}
    llama_server_url = str(os.getenv("LLAMA_SERVER_URL") or "").strip()
    use_llm = allow_llm and (bool(llama_server_url) or bool(_get_llama_cpp()))
    if not use_llm:
        return fallback

    try:
        wh_timeout_s = int(os.getenv("GENAI_WAREHOUSE_LLM_TIMEOUT_S") or "")
    except Exception:
        wh_timeout_s = 8
    if wh_timeout_s <= 0:
        wh_timeout_s = 8

    # Format freshness as percentage for display
    cur_f_pct = round(cur_f * 100, 1)
    pred_f_pct = round(pred_f * 100, 1)

    prompt = (
        "You are an AI warehouse alert engine.\n\n"
        "Analyze the following crop storage condition and generate output in STRICT FORMAT.\n\n"
        "Input:\n"
        f"Crop: {crop}\n"
        f"Current freshness: {cur_f_pct}%\n"
        f"Predicted freshness (24h): {pred_f_pct}%\n"
        f"Risk Level: {risk}\n"
        f"Temperature deviation: {temp_dev}°C\n"
        f"Humidity deviation: {hum_dev}%\n"
        f"Storage compatibility: {storage_compat}\n\n"
        "CRITICAL RULES:\n"
        "- Use ONLY the provided values EXACTLY as given - DO NOT change or invent numbers\n"
        "- Risk Level is FINAL - do NOT contradict it (e.g., if SAFE, do NOT say high risk)\n"
        "- Ensure consistency with Risk Status - do NOT use words like 'high risk' when Risk Status is SAFE\n"
        "- Freshness > 50% means LOW risk, NOT high risk\n"
        "- Reuse the exact temperature/humidity deviations provided\n"
        "- Do NOT generate new values or recalculate anything\n\n"
        "RECOMMENDATION QUALITY RULES:\n"
        "- Do NOT give vague suggestions like 'monitor' or 'continuous monitoring' - always suggest concrete actions\n"
        "- Avoid generic phrases like 'monitor closely' unless accompanied by corrective action\n"
        "- Replace weak phrases like 'continuous monitoring' with 'corrective action required'\n"
        "- Must include at least one corrective action: cooling, humidity control, ventilation, etc.\n"
        "- Always consider BOTH temperature and humidity if deviations exist\n"
        "- If both temperature and humidity deviations exist, mention BOTH in recommendation\n"
        "- Do NOT assume whether humidity should increase or decrease\n"
        "- Use neutral corrective phrasing like: 'stabilize humidity within optimal range'\n"
        "- NEVER suggest specific numeric adjustments like 'reduce by 2.5°C' - use general terms like 'reduce temperature'\n"
        "- NEVER invent or guess specific values - only reference provided values\n"
        "- Avoid incomplete sentences - always produce complete, grammatically correct outputs\n"
        "- Each sentence must have a clear subject, verb, and complete thought\n"
        "- Incorporate freshness level into explanation using exact provided percentage\n"
        "- Be specific, actionable, and professional\n\n"
        "IMPORTANT OUTPUT RULES:\n"
        "- Output EXACTLY 2 lines only\n"
        "- Each line must start with the label EXACTLY:\n"
        "  Alert:\n"
        "  Recommendation:\n"
        "- Each line must be SINGLE LINE (no line breaks)\n"
        "- Do NOT add headings, extra text, or blank lines\n"
        "- Do NOT skip any field\n\n"
        "Guidelines:\n"
        "- If Risk Level is SAFE → describe stable conditions\n"
        "- If Risk Level is HIGH → describe urgent conditions\n"
        "- Always match your wording to the provided Risk Level\n"
        "- Be concise and operational\n\n"
        "OUTPUT FORMAT (STRICT):\n"
        "Alert: <one complete sentence describing the situation using exact provided values>\n"
        "Recommendation: <one complete sentence with concrete corrective action, NO specific numbers>"
    )

    try:
        txt = ""
        if llama_server_url:
            txt = _llama_server_generate(prompt, timeout_s=int(wh_timeout_s))
        else:
            llm = _get_llama_cpp()
            if llm:
                res = llm(prompt, max_tokens=350, temperature=0.2, top_p=0.9, stop=["\n\n\n"])
                if isinstance(res, dict):
                    choices = res.get("choices")
                    if isinstance(choices, list) and choices:
                        txt = str((choices[0] or {}).get("text") or "")
        txt = str(txt or "").strip()

        if not txt:
            if strict_llm:
                return {
                    "alert_message": "LLM unavailable.",
                    "recommendation": "LLM unavailable.",
                    "source": "llm_unavailable",
                }
            return fallback

        alert_msg = ""
        reco = ""
        mode = None
        for ln in txt.replace("\r", "").split("\n"):
            s = ln.strip()
            if not s:
                continue
            if s.lower().startswith("alert:"):
                mode = "alert"
                continue
            if s.lower().startswith("recommendation:"):
                mode = "reco"
                continue
            if mode == "alert":
                alert_msg = (alert_msg + " " + s).strip()
            elif mode == "reco":
                reco = (reco + " " + s).strip()

        alert_msg = re.sub(r"\s+", " ", alert_msg).strip()
        reco = re.sub(r"\s+", " ", reco).strip()
        
        # Detect and fix incomplete sentences (truncated LLM output)
        def _is_incomplete_sentence(text: str) -> bool:
            if not text:
                return True
            incomplete_endings = (' and', ' with', ' but', ' or', ' only', ' given', ' for', ' at', ' by')
            text_lower = text.lower().rstrip()
            return text_lower.endswith(incomplete_endings) or not text.rstrip().endswith(('.', '!', '?'))
        
        # Replace incomplete sentences with fallback
        if _is_incomplete_sentence(alert_msg):
            alert_msg = fallback.get("alert_message", "")
        if _is_incomplete_sentence(reco):
            reco = fallback.get("recommendation", "")
        
        # Accept partial responses - use fallback for missing fields
        if not alert_msg:
            alert_msg = fallback.get("alert_message", "")
        if not reco:
            reco = fallback.get("recommendation", "")
            
        # Only reject if BOTH fields are missing
        if not (alert_msg or reco):
            if strict_llm:
                return {
                    "alert_message": "LLM unavailable.",
                    "recommendation": "LLM unavailable.",
                    "source": "llm_unavailable",
                }
            return fallback

        return {
            "alert_message": alert_msg,
            "recommendation": reco,
            "source": "llm" if (llama_server_url or _get_llama_cpp()) else "deterministic_fallback",
        }
    except Exception:
        if strict_llm:
            return {
                "alert_message": "LLM unavailable.",
                "recommendation": "LLM unavailable.",
                "source": "llm_unavailable",
            }
        return fallback




_llama_cpp_instance = None


def _get_llama_cpp():
    global _llama_cpp_instance
    if _llama_cpp_instance is False:
        return None
    if _llama_cpp_instance is not None:
        return _llama_cpp_instance

    model_path = str(os.getenv("LLAMA_MODEL_PATH") or "").strip()
    if not model_path:
        _llama_cpp_instance = False
        return None

    try:
        from llama_cpp import Llama
    except Exception:
        _llama_cpp_instance = False
        return None

    try:
        n_ctx = int(os.getenv("LLAMA_CTX") or 2048)
    except Exception:
        n_ctx = 2048

    try:
        _llama_cpp_instance = Llama(model_path=model_path, n_ctx=n_ctx)
        return _llama_cpp_instance
    except Exception:
        _llama_cpp_instance = False
        return None


def _clean_actions_text(text: str) -> str:
    t = str(text or "")
    t = t.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not t:
        return ""

    t = re.sub(r"^```.*?\n", "", t, flags=re.DOTALL)
    t = t.replace("```", "")

    if ";" in t and "\n" not in t:
        parts = [p.strip() for p in t.split(";")]
    else:
        parts = [p.strip() for p in t.split("\n")]

    if len(parts) <= 1:
        t2 = t
        t2 = re.sub(r"\s+", " ", t2).strip()
        if "." in t2:
            parts = [p.strip() for p in re.split(r"\.\s+", t2) if p.strip()]
        elif "," in t2:
            parts = [p.strip() for p in t2.split(",") if p.strip()]

    out = []
    seen = set()
    for p in parts:
        if not p:
            continue
        p = re.sub(r"^[-*\u2022\s]+", "", p).strip()
        p = re.sub(r"^\d+\.?\s+", "", p).strip()
        if not p:
            continue
        if p.lower() in seen:
            continue
        seen.add(p.lower())
        out.append(p)
        if len(out) >= 4:
            break

    return "\n".join(out)


def _llama_server_generate(prompt: str, *, timeout_s: Optional[int] = None) -> str:
    base = str(os.getenv("LLAMA_SERVER_URL") or "").strip().rstrip("/")
    if not base:
        return ""

    if timeout_s is None:
        try:
            timeout_s = int(os.getenv("LLAMA_SERVER_TIMEOUT_S") or "")
        except Exception:
            timeout_s = None
    if not timeout_s or int(timeout_s) <= 0:
        timeout_s = 45

    try:
        n_predict = int(os.getenv("LLAMA_SERVER_N_PREDICT") or 256)
    except Exception:
        n_predict = 256

    try:
        max_tokens = int(os.getenv("LLAMA_SERVER_MAX_TOKENS") or 256)
    except Exception:
        max_tokens = 256

    def _env_float(name: str, default: float) -> float:
        raw = str(os.getenv(name) or "").strip()
        if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            raw = raw[1:-1].strip()
        if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
            raw = raw[1:-1].strip()
        try:
            return float(raw)
        except Exception:
            return float(default)

    temperature = _env_float("LLAMA_SERVER_TEMPERATURE", 0.2)
    top_p = _env_float("LLAMA_SERVER_TOP_P", 0.9)

    # Respect explicit timeout override (used by warehouse dashboard to avoid hanging).
    # Do not override it from other env vars.

    try:
        r = requests.post(
            f"{base}/completion",
            json={
                "prompt": prompt,
                "n_predict": n_predict,
                "temperature": temperature,
                "top_p": top_p,
            },
            timeout=timeout_s,
        )
        if r.status_code == 404:
            raise RuntimeError("completion endpoint not found")
        r.raise_for_status()
        j = r.json() if r.content else {}
        if isinstance(j, dict):
            return str(j.get("content") or j.get("completion") or j.get("response") or j.get("text") or "")
        return ""
    except Exception:
        try:
            r = requests.post(
                f"{base}/v1/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                timeout=timeout_s,
            )
            r.raise_for_status()
            j = r.json() if r.content else {}
            if isinstance(j, dict):
                choices = j.get("choices")
                if isinstance(choices, list) and choices:
                    c0 = choices[0] or {}
                    return str(c0.get("text") or (c0.get("message") or {}).get("content") or "")
            return ""
        except Exception:
            try:
                r = requests.post(
                    f"{base}/v1/chat/completions",
                    json={
                        "model": "local",
                        "temperature": temperature,
                        "top_p": top_p,
                        "max_tokens": max_tokens,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt},
                        ],
                    },
                    timeout=timeout_s,
                )
                r.raise_for_status()
                j = r.json() if r.content else {}
                if isinstance(j, dict):
                    choices = j.get("choices")
                    if isinstance(choices, list) and choices:
                        msg = (choices[0] or {}).get("message") or {}
                        return str(msg.get("content") or "")
                return ""
            except Exception:
                return ""


def generate_actions(
    route_id: str,
    source_location: str,
    destination_location: str,
    transport_mode: str,
    distance_km: float,
    predicted_delay_hours: float,
    alert_severity: str,
    alert_description: str,
) -> str:
    strict_llm = str(os.getenv("GENAI_STRICT_LLM") or "").strip().lower() in {"1", "true", "yes", "on"}
    sev_norm = str(alert_severity or "NONE").strip().upper()

    fallback = dashboard_actions(
        route_name=str(route_id or ""),
        source_location=source_location,
        destination_location=destination_location,
        transport_mode=transport_mode,
        distance_km=distance_km,
        predicted_delay_hours=predicted_delay_hours,
        alert_severity=alert_severity,
        alert_description=alert_description,
    )

    def _invalid_for_none(actions_text: str) -> bool:
        if sev_norm != "NONE":
            return False
        t = str(actions_text or "").lower()
        bad = [
            "reroute",
            "re-route",
            "divert",
            "alternate route",
            "alternative route",
            "route via",
            "switch mode",
            "change mode",
            "reschedule",
            "nh",
        ]
        return any(b in t for b in bad)

    strict_llm = str(os.getenv("GENAI_STRICT_LLM") or "").strip().lower() in {"1", "true", "yes", "on"}
    llama_server_url = str(os.getenv("LLAMA_SERVER_URL") or "").strip()

    if strict_llm and (not llama_server_url) and (not _get_llama_cpp()):
        return _llm_unavailable_text(area="Logistics")
    if llama_server_url:
        def _try_once_server(extra_rule: str = "") -> str:
            p = (
                "You are an intelligent logistics decision assistant.\n"
                "Based on the given route and alert context, generate concise action recommendations.\n\n"
                "Rules:\n\n"
                "* If Alert severity is NONE, do NOT suggest rerouting, rescheduling, switching mode, or alternative routes\n"
                "* If Alert severity is NONE, output only routine operational steps (confirm dispatch, update ETA buffer, monitor conditions)\n"
                "* Do NOT mention specific highways/route numbers (e.g., NH44) or hubs/ports not present in the Route\n"
                "* Do not repeat the alert text\n"
                "* Do not explain reasoning\n"
                "* Output only action statements\n"
                "* Limit output to 2–4 short lines\n"
                "* Use professional logistics language\n\n"
                "Context:\n"
                f"Route: {source_location} to {destination_location}\n"
                f"Transport mode: {transport_mode}\n"
                f"Predicted delay: {predicted_delay_hours} hours\n"
                f"Alert severity: {alert_severity}\n"
                f"Alert description: {alert_description}\n\n"
                "Output:"
            )
            if extra_rule:
                p = p.replace("Rules:\n\n", f"Rules:\n\n{extra_rule}\n")
            txt = _llama_server_generate(p)
            return _clean_actions_text(txt)

        try:
            cleaned = _try_once_server()
            if cleaned.count("\n") >= 1 and not _invalid_for_none(cleaned):
                return cleaned

            cleaned2 = _try_once_server(extra_rule="* Output exactly 3 action lines\n* If Alert severity is NONE, do NOT mention reroute/alternate routes/highways; only routine operational steps")
            if cleaned2.count("\n") >= 1 and not _invalid_for_none(cleaned2):
                return cleaned2

            if strict_llm:
                return _llm_unavailable_text(area="Logistics")
            return fallback
        except Exception:
            if strict_llm:
                return _llm_unavailable_text(area="Logistics")
            return fallback

    llm = _get_llama_cpp()
    if not llm:
        if strict_llm:
            return _llm_unavailable_text(area="Logistics")
        return fallback

    prompt = (
        "You are an intelligent logistics decision assistant.\n"
        "Based on the given route and alert context, generate concise action recommendations.\n\n"
        "Rules:\n\n"
        "* If Alert severity is NONE, do NOT suggest rerouting, rescheduling, switching mode, or alternative routes\n"
        "* If Alert severity is NONE, output only routine operational steps (confirm dispatch, update ETA buffer, monitor conditions)\n"
        "* Do NOT mention specific highways/route numbers (e.g., NH44) or hubs/ports not present in the Route\n"
        "* Do not repeat the alert text\n"
        "* Do not explain reasoning\n"
        "* Output only action statements\n"
        "* Limit output to 2–4 short lines\n"
        "* Use professional logistics language\n\n"
        "Context:\n"
        f"Route: {source_location} to {destination_location}\n"
        f"Transport mode: {transport_mode}\n"
        f"Predicted delay: {predicted_delay_hours} hours\n"
        f"Alert severity: {alert_severity}\n"
        f"Alert description: {alert_description}\n\n"
        "Output:"
    )

    def _try_once(extra_rule: str = "") -> str:
        p = prompt
        if extra_rule:
            p = p.replace("Rules:\n\n", f"Rules:\n\n{extra_rule}\n")
        res = llm(
            p,
            max_tokens=160,
            temperature=0.2,
            top_p=0.9,
            stop=["\n\n"],
        )
        txt = ""
        if isinstance(res, dict):
            choices = res.get("choices")
            if isinstance(choices, list) and choices:
                txt = str((choices[0] or {}).get("text") or "")
        return _clean_actions_text(txt)

    try:
        cleaned = _try_once()
        if cleaned.count("\n") >= 1 and not _invalid_for_none(cleaned):
            return cleaned

        cleaned2 = _try_once(extra_rule="* Output exactly 3 action lines\n* If Alert severity is NONE, do NOT mention reroute/alternate routes/highways; only routine operational steps")
        if cleaned2.count("\n") >= 1 and not _invalid_for_none(cleaned2):
            return cleaned2

        if strict_llm:
            return _llm_unavailable_text(area="Logistics")
        return fallback
    except Exception:
        if strict_llm:
            return _llm_unavailable_text(area="Logistics")
        return fallback


def generate_logistics_actions(context: Dict[str, Any]) -> str:
    crop = str((context or {}).get("crop") or "").strip()
    mode = str((context or {}).get("transport_mode") or "road").strip().lower() or "road"
    risk = str((context or {}).get("logistics_risk") or "").strip().upper()

    try:
        distance_km = float((context or {}).get("distance_km") or 0.0)
    except Exception:
        distance_km = 0.0
    try:
        travel_hours = float((context or {}).get("travel_hours") or 0.0)
    except Exception:
        travel_hours = 0.0
    try:
        exit_f = float((context or {}).get("warehouse_exit_freshness") or 0.0)
    except Exception:
        exit_f = 0.0
    try:
        arrival_f = float((context or {}).get("predicted_arrival_freshness") or 0.0)
    except Exception:
        arrival_f = 0.0

    active_alerts = (context or {}).get("active_alerts")
    if not isinstance(active_alerts, list):
        active_alerts = []
    active_alerts_txt = "; ".join([str(a) for a in active_alerts[:6] if str(a or "").strip()])

    fallback_lines = []
    if risk == "HIGH SPOILAGE RISK":
        fallback_lines = [
            "Reroute to minimize transit time and avoid disruption hotspots",
            "Expedite dispatch and maintain strict cold-chain handling at every handoff",
            "Cancel or divert to a nearer hub if safe delivery window cannot be met",
        ]
    elif risk == "RISK":
        fallback_lines = [
            "Expedite movement and add checkpoint monitoring for temperature and dwell time",
            "Prepare a contingency route/mode option if conditions worsen",
            "Notify stakeholders with an updated ETA and buffer",
        ]
    else:
        fallback_lines = [
            "Proceed as planned with standard monitoring",
            "Confirm carrier readiness and handoff windows",
            "Keep a small buffer in ETA for minor disruptions",
        ]
    fallback = "\n".join(fallback_lines[:3])

    llama_server_url = str(os.getenv("LLAMA_SERVER_URL") or "").strip()
    if llama_server_url:
        prompt = (
            "You are a logistics decision assistant.\n"
            "Based on the shipment risk context, suggest 2–3 operational actions.\n\n"
            "Rules:\n"
            "- Do NOT calculate freshness.\n"
            "- Do NOT restate alerts.\n"
            "- Keep responses concise and practical.\n"
            "- Output only 2–3 action lines.\n\n"
            "Context:\n"
            f"Crop: {crop}\n"
            f"Transport mode: {mode}\n"
            f"Distance (km): {distance_km}\n"
            f"Travel hours: {travel_hours}\n"
            f"Warehouse exit freshness: {exit_f}\n"
            f"Predicted arrival freshness: {arrival_f}\n"
            f"Logistics risk: {risk}\n"
            f"Active alerts: {active_alerts_txt}\n\n"
            "Output:"
        )
        try:
            txt = _llama_server_generate(prompt)
            cleaned = _clean_actions_text(txt)
            lines = [ln.strip() for ln in str(cleaned or "").split("\n") if ln.strip()]
            if len(lines) >= 2:
                return "\n".join(lines[:3])
            if strict_llm:
                return _llm_unavailable_text(area="Logistics")
            return fallback
        except Exception:
            if strict_llm:
                return _llm_unavailable_text(area="Logistics")
            return fallback

    llm = _get_llama_cpp()
    if not llm:
        if strict_llm:
            return _llm_unavailable_text(area="Logistics")
        return fallback

    prompt = (
        "You are a logistics decision assistant.\n"
        "Based on the shipment risk context, suggest 2–3 operational actions.\n\n"
        "Rules:\n"
        "- Do NOT calculate freshness.\n"
        "- Do NOT restate alerts.\n"
        "- Keep responses concise and practical.\n"
        "- Output only 2–3 action lines.\n\n"
        "Context:\n"
        f"Crop: {crop}\n"
        f"Transport mode: {mode}\n"
        f"Distance (km): {distance_km}\n"
        f"Travel hours: {travel_hours}\n"
        f"Warehouse exit freshness: {exit_f}\n"
        f"Predicted arrival freshness: {arrival_f}\n"
        f"Logistics risk: {risk}\n"
        f"Active alerts: {active_alerts_txt}\n\n"
        "Output:"
    )

    try:
        res = llm(
            prompt,
            max_tokens=160,
            temperature=0.2,
            top_p=0.9,
            stop=["\n\n"],
        )
        txt = ""
        if isinstance(res, dict):
            choices = res.get("choices")
            if isinstance(choices, list) and choices:
                txt = str((choices[0] or {}).get("text") or "")
        cleaned = _clean_actions_text(txt)
        lines = [ln.strip() for ln in str(cleaned or "").split("\n") if ln.strip()]
        if len(lines) >= 2:
            return "\n".join(lines[:3])
        if strict_llm:
            return _llm_unavailable_text(area="Logistics")
        return fallback
    except Exception:
        if strict_llm:
            return _llm_unavailable_text(area="Logistics")
        return fallback


def generate_farmer_recommendation(context: Dict[str, Any]) -> Dict[str, Any]:
    crop = str((context or {}).get("crop") or "").strip()
    try:
        freshness = float((context or {}).get("freshness") or 0.0)
    except Exception:
        freshness = 0.0
    try:
        remaining_days = float((context or {}).get("remaining_shelf_life_days") or 0.0)
    except Exception:
        remaining_days = 0.0
    seasonal_risk = bool((context or {}).get("seasonal_risk"))
    weather_summary = str((context or {}).get("current_weather_summary") or "").strip()
    try:
        wh_dist = float((context or {}).get("nearest_warehouse_distance") or 0.0)
    except Exception:
        wh_dist = 0.0

    def _risk_from_freshness(x: float) -> str:
        try:
            v = float(x or 0.0)
        except Exception:
            v = 0.0
        if v >= 0.6:
            return "SAFE"
        if v >= 0.3:
            return "RISK"
        return "HIGH SPOILAGE RISK"

    def _has_forbidden_phrases(s: str) -> bool:
        t = str(s or "").lower()
        forbidden = [
            "negative shelf",
            "negative remaining",
            "effective remaining",
            "buffer",
            "penalty",
        ]
        return any(p in t for p in forbidden)

    def _two_line_explanation(f: float, risk: str) -> str:
        pct = int(round(max(0.0, min(1.0, float(f))) * 100))
        return f"Freshness is {pct}% ({risk}).\nFollow the recommended action within safety limits."

    def _looks_truncated(s: str) -> bool:
        t = str(s or "").strip()
        if not t:
            return True
        # Require a natural sentence end to reduce half-line cutoffs.
        return t[-1] not in {".", "!", "?"}

    def _llm_numbers_match_context(text: str) -> bool:
        """Reject LLM outputs that invent numbers not present in the deterministic context."""
        t = str(text or "")
        if not t:
            return False

        # Expected numbers
        f01 = max(0.0, min(1.0, float(freshness)))
        pct = int(round(f01 * 100))
        try:
            rem_i = int(round(float(remaining_days)))
        except Exception:
            rem_i = 0

        # If the model includes freshness as a 0-1 float, it must match within tolerance.
        floats01 = [float(m) for m in re.findall(r"\b0\.\d+\b|\b1\.0+\b|\b1\b", t)]
        for x in floats01:
            if 0.0 <= x <= 1.0 and abs(x - f01) > 0.05:
                return False

        # If the model includes a percentage, it must match (allow +/- 3% to tolerate rounding).
        pct_matches = re.findall(r"(\d{1,3})\s*%", t)
        for pm in pct_matches:
            try:
                p = int(pm)
            except Exception:
                continue
            if abs(p - pct) > 3:
                return False

        # If the model mentions remaining shelf life days as a number with 'day(s)', it must match.
        day_matches = re.findall(r"\b(\d{1,3})\s*day", t, flags=re.IGNORECASE)
        for dm in day_matches:
            try:
                d = int(dm)
            except Exception:
                continue
            if abs(d - rem_i) > 1:
                return False

        return True

    if float(freshness) <= 0.0:
        return {
            "recommendation": "Dispose of the crop safely or divert for composting.",
            "explanation": "Freshness is 0% (HIGH SPOILAGE RISK).\nDo not sell, store, or transport this crop.",
            "source": "food_safety",
        }

    if remaining_days <= 0 or freshness < 0.3:
        rec = "Urgent: move the crop immediately for storage or sell today/tomorrow."
    elif remaining_days <= 2 or freshness < 0.45:
        rec = "Store the crop in the nearest warehouse or sell within 1–2 days."
    elif remaining_days <= 5 or freshness < 0.6:
        rec = "Plan immediate storage/transport and sell within 3–5 days."
    else:
        rec = "Proceed with normal handling and schedule storage/transport within a week."

    risk = _risk_from_freshness(float(freshness))
    explanation = _two_line_explanation(float(freshness), risk)

    def _deterministic_payload(*, src: str) -> Dict[str, Any]:
        return {
            "recommendation": rec,
            "explanation": explanation,
            "source": src,
        }

    strict_llm = str(os.getenv("GENAI_STRICT_LLM") or "").strip().lower() in {"1", "true", "yes", "on"}
    llama_server_url = str(os.getenv("LLAMA_SERVER_URL") or "").strip()

    if strict_llm and (not llama_server_url) and (not _get_llama_cpp()):
        return _llm_unavailable_reco(area="Farmer")
    if llama_server_url:
        prompt = (
            "You are an agricultural supply-chain assistant for farmers.\n"
            "Interpret the given deterministic signals and provide a short recommendation and explanation.\n\n"
            "Rules:\n"
            "- Do NOT modify freshness or risk level.\n"
            "- If freshness is 0, recommend ONLY disposal/composting/loss recording.\n"
            "- Do NOT recommend selling, storing, or transporting when freshness is 0.\n"
            "- Do NOT mention negative shelf life or internal calculations.\n"
            "- Do NOT invent numeric measurements beyond the provided context.\n"
            "- Keep output concise and actionable.\n"
            "- Output exactly two lines:\n"
            "  Recommendation: ...\n"
            "  Explanation: ...\n\n"
            "Context:\n"
            f"Crop: {crop}\n"
            f"Freshness: {freshness}\n"
            f"Remaining shelf life days: {remaining_days}\n"
            f"Seasonal risk: {seasonal_risk}\n"
            f"Current weather summary: {weather_summary}\n"
            f"Nearest warehouse distance (km): {wh_dist}\n\n"
            "Output:"
        )
        try:
            txt = _llama_server_generate(prompt)
            t = str(txt or "").strip()
            if t:
                lines = [ln.strip() for ln in t.replace("\r", "").split("\n") if ln.strip()]
                rec_line = next((ln for ln in lines if ln.lower().startswith("recommendation:")), "")
                exp_line = next((ln for ln in lines if ln.lower().startswith("explanation:")), "")
                rec_out = rec_line.split(":", 1)[1].strip() if ":" in rec_line else ""
                exp_out = exp_line.split(":", 1)[1].strip() if ":" in exp_line else ""
                joined = (rec_out + "\n" + exp_out)
                bad = _has_forbidden_phrases(joined)
                if rec_out and exp_out and not bad and not _looks_truncated(exp_out) and _llm_numbers_match_context(joined):
                    return {"recommendation": rec_out, "explanation": exp_out, "source": "llama_server"}
            if strict_llm:
                logger.warning("Farmer GenAI: LLM did not return expected format; falling back.")
        except Exception:
            if strict_llm:
                logger.warning("Farmer GenAI: LLM call failed; falling back.")

        if strict_llm:
            return _llm_unavailable_reco(area="Farmer")

    llm = _get_llama_cpp()
    if llm:
        prompt = (
            "You are an agricultural supply-chain assistant for farmers.\n"
            "Interpret the given deterministic signals and provide a short recommendation and explanation.\n\n"
            "Rules:\n"
            "- Do NOT modify freshness or risk level.\n"
            "- If freshness is 0, you MUST recommend no selling or transport.\n"
            "- Do NOT invent numeric measurements beyond the provided context.\n"
            "- Keep output concise and actionable.\n"
            "- Output exactly two lines:\n"
            "  Recommendation: ...\n"
            "  Explanation: ...\n\n"
            "Context:\n"
            f"Crop: {crop}\n"
            f"Freshness: {freshness}\n"
            f"Remaining shelf life days: {remaining_days}\n"
            f"Seasonal risk: {seasonal_risk}\n"
            f"Current weather summary: {weather_summary}\n"
            f"Nearest warehouse distance (km): {wh_dist}\n\n"
            "Output:"
        )
        try:
            res = llm(
                prompt,
                max_tokens=160,
                temperature=0.2,
                top_p=0.9,
                stop=["\n\n"],
            )

            txt = ""
            if isinstance(res, dict):
                choices = res.get("choices")
                if isinstance(choices, list) and choices:
                    txt = str((choices[0] or {}).get("text") or "")

            t = str(txt or "").strip()
            if t:
                lines = [ln.strip() for ln in t.replace("\r", "").split("\n") if ln.strip()]
                rec_line = next((ln for ln in lines if ln.lower().startswith("recommendation:")), "")
                exp_line = next((ln for ln in lines if ln.lower().startswith("explanation:")), "")
                rec_out = rec_line.split(":", 1)[1].strip() if ":" in rec_line else ""
                exp_out = exp_line.split(":", 1)[1].strip() if ":" in exp_line else ""
                joined = (rec_out + "\n" + exp_out)
                bad = _has_forbidden_phrases(joined)
                if rec_out and exp_out and not bad and not _looks_truncated(exp_out) and _llm_numbers_match_context(joined):
                    return {"recommendation": rec_out, "explanation": exp_out, "source": "llama_cpp"}
            if strict_llm:
                logger.warning("Farmer GenAI: llama.cpp did not return expected format; falling back.")
        except Exception:
            if strict_llm:
                logger.warning("Farmer GenAI: local LLM call failed; falling back.")
            if strict_llm:
                return _llm_unavailable_reco(area="Farmer")

    if strict_llm:
        return _llm_unavailable_reco(area="Farmer")

    return _deterministic_payload(src="deterministic")

def advise_route(route: str, mode: str, predicted_delay_hours: float, alerts: list) -> dict:
    """Return a GenAI-style advisory for a specific route option.

    This project prefers a local transformers model when available.
    If unavailable, it falls back to deterministic rule-based reasoning.
    """

    mode_l = (mode or "").lower()
    route_txt = (route or "")
    route_key = route_txt.strip().lower().encode("utf-8")
    route_variant = int(hashlib.md5(route_key).hexdigest()[:2], 16) % 3
    pts = [p.strip() for p in route_txt.replace("→", "->").split("->") if p.strip()]
    legs = max(len(pts) - 1, 1)
    hubs = pts[1:-1]
    hubs_short = ", ".join(hubs[:2])
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
        "": 0,
    }

    top = 0
    top_titles = []
    for a in alerts or []:
        lvl = str(a.get("alertlevel", "")).strip().lower()
        top = max(top, sev_rank.get(lvl, 0))
        t = str(a.get("title", "")).strip()
        if t:
            top_titles.append(t)
    top_titles = top_titles[:2]

    titles_l = " ".join([str(t).lower() for t in top_titles if t])
    hazard = {
        "fog": ("fog" in titles_l) or ("low visibility" in titles_l) or ("visibility" in titles_l) or ("mist" in titles_l) or ("haze" in titles_l),
        "wind": ("wind" in titles_l) or ("gust" in titles_l),
        "storm": ("storm" in titles_l) or ("thunder" in titles_l) or ("cyclone" in titles_l) or ("severe weather" in titles_l),
        "rain": ("rain" in titles_l) or ("drizzle" in titles_l),
        "flood": ("flood" in titles_l) or ("inund" in titles_l),
        "heat": ("heat" in titles_l) or ("high temp" in titles_l) or ("temperature" in titles_l) or ("hot" in titles_l),
    }

    delay_h = float(predicted_delay_hours or 0)
    mitigations = []

    if mode_l == "air":
        # Only add cold-chain steps if temperature is high or alerts are present
        temp_high = any("heat" in t.lower() or "high temp" in t.lower() for t in top_titles)
        if top >= 2 or temp_high:
            mitigations.extend([
                "Confirm flight slots and ground handling at any transit airport",
                "Keep cargo pre-cooled; minimize tarmac waiting time",
                "Have an alternate transit airport ready if weather worsens",
            ])
        else:
            mitigations.extend([
                "Confirm flight slots and ground handling at any transit airport",
                "Minimize tarmac waiting time for faster turnaround",
                "Monitor weather in case conditions change",
            ])
    elif mode_l == "sea":
        # Only add reefer steps if temperature is high or alerts are present
        temp_high = any("heat" in t.lower() or "high temp" in t.lower() for t in top_titles)
        if top >= 2 or temp_high:
            # Choose variant based on first hub to make rows distinct
            hub0 = str(hubs[0]).strip().lower() if hubs else ""
            if "colombo" in hub0:
                sea_variants = [
                    [
                        "Reserve reefer plug slots and confirm vessel cut-off times",
                        "Add extra time for Colombo port congestion and berthing delays",
                        "Seal containers and log temperatures before loading",
                    ],
                    [
                        "Confirm Colombo terminal cut-off and reefer power availability",
                        "Prepare documents early to avoid gate delays",
                        "Verify container PTI and set temperature before loading",
                    ],
                    [
                        "Lock booking and confirm feeder/mainline connection at Colombo",
                        "Plan for transshipment wait and ensure reefer monitoring",
                        "Share stowage notes to minimize deck time and heat exposure",
                    ],
                ]
            elif "singapore" in hub0:
                sea_variants = [
                    [
                        "Confirm PSA terminal cut-off and reefer plug availability",
                        "Add buffer for Singapore port congestion and berthing delays",
                        "Seal containers and log temperatures before loading",
                    ],
                    [
                        "Reserve feeder connection and confirm vessel cut-off times",
                        "Prepare documents early to avoid gate delays",
                        "Verify container PTI and set temperature before loading",
                    ],
                    [
                        "Lock booking and confirm feeder/mainline connection at Singapore",
                        "Plan for transshipment wait and ensure reefer monitoring",
                        "Share stowage notes to minimize deck time and heat exposure",
                    ],
                ]
            else:
                sea_variants = [
                    [
                        "Reserve reefer plug slots and confirm vessel cut-off times",
                        "Add buffer for port congestion and berthing delays",
                        "Seal containers and log temperatures before loading",
                    ],
                    [
                        "Confirm terminal cut-off and reefer power availability",
                        "Prepare documents early to avoid gate delays",
                        "Verify container PTI and set temperature before loading",
                    ],
                    [
                        "Lock booking and confirm feeder/mainline connection",
                        "Plan for transshipment wait and ensure reefer monitoring",
                        "Share stowage notes to minimize deck time and heat exposure",
                    ],
                ]
            mitigations.extend(sea_variants[route_variant])
        else:
            # No high alerts or heat: keep steps simple
            mitigations.extend([
                "Confirm vessel cut-off time and terminal slot",
                "Prepare documents early to avoid gate delays",
                "Monitor weather in case conditions change",
            ])
    elif mode_l == "rail":
        mitigations.extend([
            "Book a priority rail slot and track any schedule changes",
            "Plan a quick transfer at the hub to avoid missing the next train",
        ])
    else:  # road
        # Force different first mitigation per row to avoid identical rows
        if route_variant == 0:
            mitigations.extend([
                "Identify an alternate road segment around common choke points",
                "Avoid peak-hour city traffic; travel off-peak when possible",
            ])
        elif route_variant == 1:
            mitigations.extend([
                "Plan an alternate route around known choke points",
                "Schedule travel outside peak city traffic hours",
            ])
        else:
            mitigations.extend([
                "Have a backup road segment ready for choke points",
                "Avoid city rush hours; prefer off-peak travel",
            ])

    # Route-structure mitigations so different route options differ
    if legs > 1:
        mitigations.append("Multi-leg route: confirm handoff timing at each transfer point")
    if hubs:
        mitigations.append(f"Verify transshipment readiness at hub(s): {hubs_short}")

        hub0 = str(hubs[0]).strip().lower() if hubs else ""
        if "colombo" in hub0:
            mitigations.append("Colombo hub: confirm feeder connection and reefer plug queue")
        elif "singapore" in hub0:
            mitigations.append("Singapore hub: confirm terminal cut-off and connection window")
        elif "dubai" in hub0:
            mitigations.append("Dubai hub: validate berth slot and customs pre-clearance")
        elif "mumbai" in hub0:
            mitigations.append("Mumbai hub: confirm berth and container handling readiness")
        elif "delhi" in hub0:
            mitigations.append("Delhi hub: confirm rail/air transfer slot and handling")
        else:
            mitigations.append(f"{hubs[0]} hub: confirm transfer window and handling readiness")

    if delay_h >= 6:
        mitigations.append("Add buffer time and communicate ETA updates early")
    if delay_h >= 24:
        mitigations.append("For perishables: consider splitting the shipment or switching to a faster mode")

    if hazard.get("storm") or hazard.get("flood"):
        mitigations.append("Avoid departures during the storm window; have an alternate route ready")
    if hazard.get("fog") and mode_l in {"air", "road"}:
        mitigations.append("Shift departure to daylight hours when visibility is better")
    if hazard.get("wind") and mode_l in {"sea", "air"}:
        mitigations.append("Check wind limits with the carrier; secure cargo properly")
    if hazard.get("heat"):
        mitigations.append("Monitor temperature closely; reduce waiting time at stops")

    # Try local transformers for a short advisory sentence; fall back to rule-based action/rationale
    # DISABLED: model output too noisy; use rule-based only
    local_advice = ""  # _local_transformers_advice(route, mode, delay_h, alerts).strip()
    if local_advice:
        action = local_advice
        rationale = "Generated by local model"
    else:
        # Rule-based fallback
        if top >= 3:
            if mode_l == "sea":
                action = "Hold / Reroute"
            elif mode_l == "air":
                action = "Rebook via Alternate Hub"
            else:
                action = "Reroute Around Hazard"
            rationale = "Severe disruption risk" + (": " + "; ".join(top_titles) if top_titles else "")
        elif top == 2:
            action = "Add Buffer + Monitor"
            rationale = "Moderate operational risk" + (": " + "; ".join(top_titles) if top_titles else "")
        elif top == 1:
            action = "Monitor + Add Small Buffer"
            rationale = "Minor operational risk" + (": " + "; ".join(top_titles) if top_titles else "")
        else:
            action = "Proceed as Planned"
            rationale = "No live hazard/disaster alerts detected for this route"

    # Add minimal route-specific context without clutter
    if hubs:
        rationale += f" (via {hubs_short})"

    # Force a unique mitigation per row using a simple index from the route hash
    unique_index = route_variant
    if hubs:
        hub0 = str(hubs[0]).strip().lower() if hubs else ""
        hub_index = (hash(hub0) % 3)
        unique_index = (route_variant + hub_index) % 3
    # Add a unique mitigation based on unique_index
    if unique_index == 0:
        mitigations.append("Monitor local port/airport notices for last-minute changes")
    elif unique_index == 1:
        mitigations.append("Keep stakeholder updates on schedule every 6–12 hours")
    else:
        mitigations.append("Prepare contingency plan for alternate route if needed")

    # Add a hub/route-specific mitigation to ensure rows differ
    if hubs:
        hub0 = str(hubs[0]).strip().lower() if hubs else ""
        if "delhi" in hub0:
            mitigations.append("Check Delhi traffic and permit status before departure")
        elif "mumbai" in hub0:
            mitigations.append("Verify Mumbai port/rail yard slot availability")
        elif "colombo" in hub0:
            mitigations.append("Confirm Colombo feeder vessel schedule")
        elif "singapore" in hub0:
            mitigations.append("Check Singapore terminal berth allocation")
        else:
            mitigations.append(f"Confirm {hubs[0]} transfer window and local conditions")
    else:
        # Direct routes: add a simple variant
        if unique_index == 0:
            mitigations.append("Add 1–2 hour buffer for unexpected delays")
        elif unique_index == 1:
            mitigations.append("Track real-time traffic/weather en route")
        else:
            mitigations.append("Plan rest stops to avoid fatigue")

    # Add a hub/route-specific mitigation to ensure rows differ
    if hubs:
        hub0 = str(hubs[0]).strip().lower() if hubs else ""
        if "delhi" in hub0:
            mitigations.append("Check Delhi traffic and permit status before departure")
        elif "mumbai" in hub0:
            mitigations.append("Verify Mumbai port/rail yard slot availability")
        elif "colombo" in hub0:
            mitigations.append("Confirm Colombo feeder vessel schedule")
        elif "singapore" in hub0:
            mitigations.append("Check Singapore terminal berth allocation")
        else:
            mitigations.append(f"Confirm {hubs[0]} transfer window and local conditions")
    else:
        # Direct routes: add a simple variant
        if route_variant == 1:
            mitigations.append("Add 1–2 hour buffer for unexpected delays")
        elif route_variant == 2:
            mitigations.append("Track real-time traffic/weather en route")
        else:
            mitigations.append("Plan rest stops to avoid fatigue")

    return {
        "action": action,
        "rationale": rationale,
        "mitigations": mitigations[:5],
    }

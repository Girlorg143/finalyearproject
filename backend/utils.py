from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from .models import ROLE_FARMER, ROLE_WAREHOUSE, ROLE_LOGISTICS, ROLE_ADMIN

ROLE_TO_DASH = {
    ROLE_FARMER: "/farmer",
    ROLE_WAREHOUSE: "/warehouse",
    ROLE_LOGISTICS: "/logistics",
    ROLE_ADMIN: "/admin",
}

def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception as e:
                return jsonify({"msg": f"unauthorized: {type(e).__name__}: {e}"}), 401
            claims = get_jwt()
            role = claims.get("role", "").lower()
            if role not in [r.lower() for r in roles]:
                return jsonify({"msg": "forbidden", "required": roles}), 403
            return fn(*args, **kwargs)
        return decorated
    return wrapper

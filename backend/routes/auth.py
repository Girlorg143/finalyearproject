from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from ..extensions import db, bcrypt
from ..models import User, Role, UserRole, ROLE_FARMER, ROLE_WAREHOUSE, ROLE_LOGISTICS, ROLE_ADMIN
from ..utils import ROLE_TO_DASH

auth_bp = Blueprint("auth", __name__)

@auth_bp.get("/warehouse-locations")
def get_warehouse_locations():
    """Get list of available warehouse locations for dropdown"""
    try:
        # Use actual warehouses from the project
        warehouse_locations = [
            "Delhi Warehouse",
            "Chandigarh Warehouse", 
            "Bengaluru Warehouse",
            "Hyderabad Warehouse",
            "Kolkata Warehouse",
            "Bhubaneswar Warehouse",
            "Mumbai Warehouse",
            "Ahmedabad Warehouse",
            "Nagpur Central Warehouse"
        ]
        return jsonify({"warehouse_locations": warehouse_locations})
    except Exception as e:
        return jsonify({"msg": f"error fetching warehouse locations: {str(e)}"}), 500

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    name = data.get("name"); email = data.get("email"); password = data.get("password"); role = data.get("role")
    warehouse_location = data.get("warehouse_location")
    
    # Validate required fields
    if not all([name, email, password, role]):
        return jsonify({"msg": "missing fields"}), 400
    
    # For warehouse role, warehouse_location is required
    if role.lower() == "warehouse" and not warehouse_location:
        return jsonify({"msg": "warehouse location is required for warehouse role"}), 400
    
    try:
        r = Role.query.filter_by(name=role).first()
        if not r:
            r = Role(name=role)
            db.session.add(r)
            db.session.commit()
        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "email exists"}), 409
        pw_hash = bcrypt.generate_password_hash(password).decode()
        
        # Create user with warehouse_location if warehouse role
        user_data = {
            "name": name,
            "email": email, 
            "password_hash": pw_hash,
            "role_id": r.id
        }
        
        # Add warehouse_location only for warehouse role
        if role.lower() == "warehouse":
            user_data["warehouse_location"] = warehouse_location.strip()
        
        user = User(**user_data)
        db.session.add(user)
        db.session.commit()
        
        # also persist user_roles mapping
        ur = UserRole(user_id=user.id, role_id=r.id)
        db.session.add(ur)
        db.session.commit()
        return jsonify({"msg": "registered"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"registration error: {str(e)}"}), 500

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email"); password = data.get("password")
    warehouse_location = data.get("warehouse_location")
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Login attempt: email={email}, role attempt, warehouse={warehouse_location}")
    
    user = User.query.filter_by(email=email).first()
    if not user:
        logger.warning(f"Login failed: user not found for email={email}")
        return jsonify({"msg": "invalid credentials"}), 401
    
    if not bcrypt.check_password_hash(user.password_hash, password):
        logger.warning(f"Login failed: invalid password for email={email}")
        return jsonify({"msg": "invalid credentials"}), 401
    
    if not user.is_active:
        logger.warning(f"Login failed: account inactive for email={email}")
        return jsonify({"msg": "account inactive"}), 403
    
    role = user.role.name
    logger.info(f"Login success: user found, role={role}, stored_wh={user.warehouse_location}")
    
    # For warehouse role, validate warehouse_location matches
    if role.lower() == "warehouse":
        if not warehouse_location:
            logger.warning(f"Login failed: warehouse location missing for email={email}")
            return jsonify({"msg": "warehouse location is required for warehouse login"}), 400
        stored_wh = (user.warehouse_location or "").strip().lower()
        provided_wh = warehouse_location.strip().lower()
        if stored_wh != provided_wh:
            logger.warning(f"Login failed: warehouse mismatch. Stored='{stored_wh}', Provided='{provided_wh}'")
            return jsonify({"msg": "warehouse location does not match user record"}), 401
    
    # Prepare additional claims
    additional_claims = {
        "role": role, 
        "email": user.email
    }
    
    # Add warehouse_location to claims for warehouse users
    if role.lower() == "warehouse" and user.warehouse_location:
        additional_claims["warehouse_location"] = user.warehouse_location.strip()
    
    # Use string identity to satisfy JWT Subject type requirement
    token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
    return jsonify({"access_token": token, "redirect": ROLE_TO_DASH.get(role, "/"), "role": role})

@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    
    if not all([email, new_password, confirm_password]):
        return jsonify({"msg": "missing fields"}), 400
    
    if new_password != confirm_password:
        return jsonify({"msg": "passwords do not match"}), 400
    
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"msg": "email not found"}), 404
        
        pw_hash = bcrypt.generate_password_hash(new_password).decode()
        user.password_hash = pw_hash
        db.session.commit()
        
        return jsonify({"msg": "password updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"password update error: {str(e)}"}), 500

@auth_bp.get("/me")
@jwt_required()
def me():
    claims = get_jwt()
    return jsonify({"email": claims.get("email"), "role": claims.get("role")})

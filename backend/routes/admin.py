from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt
from ..extensions import db
from ..models import User, Role, ROLE_ADMIN, CropBatch, Shipment, WeatherLog, GenAISuggestion
from ..utils import roles_required
from sqlalchemy import func
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__)

@admin_bp.get("/users")
@roles_required(ROLE_ADMIN)
def list_users():
    """Get users with optional role filtering"""
    role_filter = request.args.get('role', '')
    search = request.args.get('search', '')
    
    query = User.query
    
    if role_filter:
        query = query.join(Role).filter(Role.name == role_filter.lower())
    
    if search:
        query = query.filter(User.name.ilike(f'%{search}%'))
    
    rows = query.all()
    
    result = []
    for u in rows:
        user_data = {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.name,
            "is_active": u.is_active,
            "location": getattr(u, 'location', None) or "N/A"
        }
        
        # Add batch counts for farmers
        if u.role.name == 'farmer':
            batches = CropBatch.query.filter_by(farmer_id=u.id).all()
            user_data["total_batches"] = len(batches)
            # Active = not delivered/cancelled AND not expired (freshness > 0)
            user_data["active_batches"] = len([b for b in batches if b.status not in ['DELIVERED', 'CANCELLED'] and (b.freshness_score or 0) > 0])
            user_data["high_risk_batches"] = len([b for b in batches if (b.freshness_score or 0) < 0.3])
        
        result.append(user_data)
    
    return jsonify(result)

@admin_bp.post("/users/status")
@roles_required(ROLE_ADMIN)
def update_status():
    data = request.get_json() or {}
    claims = get_jwt(); admin_id = int(claims.get("sub"))
    user = User.query.get(data.get("user_id"))
    if not user:
        return jsonify({"msg": "not found"}), 404
    user.is_active = bool(data.get("is_active", True))
    db.session.commit()
    # Log admin action for audit trail
    from ..models import BlockchainLog
    log = BlockchainLog(action="admin_user_status", reference_id=user.id, tx_hash=f"admin_{admin_id}")
    db.session.add(log); db.session.commit()
    return jsonify({"msg": "updated"})

@admin_bp.get("/dashboard/stats")
@roles_required(ROLE_ADMIN)
def dashboard_stats():
    """Get dashboard summary statistics"""
    total_batches = CropBatch.query.count()
    
    # Risk distribution - use freshness_score to determine risk levels
    high_count = CropBatch.query.filter(CropBatch.freshness_score < 0.3).count()
    risk_count = CropBatch.query.filter(CropBatch.freshness_score.between(0.3, 0.7)).count()
    safe_count = CropBatch.query.filter(CropBatch.freshness_score >= 0.7).count()
    
    # Shipments - use actual status values from logistics system
    total_shipments = Shipment.query.count()
    in_transit = Shipment.query.filter(Shipment.status.in_(['IN_TRANSIT', 'InTransit'])).count()
    delivered = Shipment.query.filter(Shipment.status.in_(['DELIVERED', 'Delivered'])).count()
    
    # Average freshness
    avg_freshness = db.session.query(func.avg(CropBatch.freshness_score)).scalar() or 0
    
    # Salvage batches (batches with very low freshness)
    salvage_count = CropBatch.query.filter(CropBatch.freshness_score < 0.3).count()
    
    # User counts by role
    farmer_count = User.query.join(Role).filter(Role.name == 'farmer').count()
    warehouse_count = User.query.join(Role).filter(Role.name == 'warehouse').count()
    logistics_count = User.query.join(Role).filter(Role.name == 'logistics').count()
    
    return jsonify({
        "total_batches": total_batches,
        "safe_count": safe_count,
        "risk_count": risk_count,
        "high_count": high_count,
        "total_shipments": total_shipments,
        "in_transit": in_transit,
        "delivered": delivered,
        "avg_freshness": round(float(avg_freshness), 2),
        "salvage_count": salvage_count,
        "farmer_count": farmer_count,
        "warehouse_count": warehouse_count,
        "logistics_count": logistics_count
    })

@admin_bp.get("/dashboard/batches")
@roles_required(ROLE_ADMIN)
def dashboard_batches():
    """Get all batches with filtering options"""
    # Get filter parameters
    crop_type = request.args.get('crop_type', '')
    risk_level = request.args.get('risk_level', '')
    warehouse = request.args.get('warehouse', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = CropBatch.query
    
    # Apply filters
    if crop_type:
        query = query.filter_by(crop_type=crop_type)
    if warehouse:
        query = query.filter_by(warehouse=warehouse)
    if risk_level:
        if risk_level == 'HIGH' or 'HIGH RISK':
            query = query.filter(CropBatch.freshness_score < 0.3)
        elif risk_level == 'RISK':
            query = query.filter(CropBatch.freshness_score.between(0.3, 0.7))
        elif risk_level == 'SAFE':
            query = query.filter(CropBatch.freshness_score >= 0.7)
    if date_from:
        query = query.filter(CropBatch.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(CropBatch.created_at <= datetime.fromisoformat(date_to))
    
    batches = query.order_by(CropBatch.created_at.desc()).all()
    
    return jsonify([{
        "id": b.id,
        "crop_type": b.crop_type,
        "freshness_score": round(float(b.freshness_score or 0), 2),
        "farmer_risk_status": 'HIGH' if (b.freshness_score or 0) < 0.3 else ('RISK' if (b.freshness_score or 0) < 0.7 else 'SAFE'),
        "days_remaining": int((b.freshness_score or 0) * 30),  # Estimate based on freshness
        "status": b.status,
        "warehouse": b.warehouse or "N/A",
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "quantity": b.quantity,
        "quantity_unit": b.quantity_unit
    } for b in batches])

@admin_bp.get("/dashboard/charts/freshness")
@roles_required(ROLE_ADMIN)
def freshness_distribution():
    """Get freshness distribution data for bar chart"""
    batches = CropBatch.query.all()
    data = [{
        "id": b.id,
        "crop": b.crop_type,
        "freshness": round(float(b.freshness_score or 0), 2)
    } for b in batches]
    return jsonify(data)

@admin_bp.get("/dashboard/charts/risk")
@roles_required(ROLE_ADMIN)
def risk_distribution():
    """Get risk distribution data for pie chart"""
    safe = CropBatch.query.filter(CropBatch.freshness_score >= 0.7).count()
    risk = CropBatch.query.filter(CropBatch.freshness_score.between(0.3, 0.7)).count()
    high = CropBatch.query.filter(CropBatch.freshness_score < 0.3).count()
    
    return jsonify({
        "labels": ["SAFE", "RISK", "HIGH"],
        "data": [safe, risk, high],
        "colors": ["#22c55e", "#f59e0b", "#ef4444"]
    })

@admin_bp.get("/dashboard/charts/trend")
@roles_required(ROLE_ADMIN)
def freshness_trend():
    """Get freshness trend over time for line chart"""
    # Get batches from last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    batches = CropBatch.query.filter(CropBatch.created_at >= thirty_days_ago).order_by(CropBatch.created_at).all()
    
    # Group by date and calculate average freshness
    from collections import defaultdict
    daily_data = defaultdict(list)
    
    for b in batches:
        if b.created_at:
            date_key = b.created_at.strftime('%Y-%m-%d')
            daily_data[date_key].append(float(b.freshness_score or 0))
    
    # Calculate daily averages
    trend_data = []
    for date in sorted(daily_data.keys()):
        avg = sum(daily_data[date]) / len(daily_data[date])
        trend_data.append({"date": date, "freshness": round(avg, 2)})
    
    return jsonify(trend_data)

@admin_bp.get("/dashboard/charts/crops")
@roles_required(ROLE_ADMIN)
def crop_analysis():
    """Get average freshness by crop type for bar chart"""
    from sqlalchemy import func
    
    results = db.session.query(
        CropBatch.crop_type,
        func.avg(CropBatch.freshness_score).label('avg_freshness'),
        func.count(CropBatch.id).label('count')
    ).group_by(CropBatch.crop_type).all()
    
    return jsonify([{
        "crop": r.crop_type,
        "avg_freshness": round(float(r.avg_freshness or 0), 2),
        "count": r.count
    } for r in results])

@admin_bp.get("/dashboard/alerts/recent")
@roles_required(ROLE_ADMIN)
def recent_alerts():
    # Use WeatherLog alerts field or GenAISuggestion as alternative
    recent_suggestions = GenAISuggestion.query.order_by(GenAISuggestion.created_at.desc()).limit(5).all()
    return jsonify([{
        "id": s.id,
        "batch_id": s.batch_id,
        "message": s.suggestion_text[:100] + "..." if s.suggestion_text and len(s.suggestion_text) > 100 else s.suggestion_text,
        "severity": "INFO",
        "created_at": s.created_at.isoformat() if s.created_at else None
    } for s in recent_suggestions])

@admin_bp.get("/dashboard/batches/high-risk")
@roles_required(ROLE_ADMIN)
def high_risk_batches():
    """Get high-risk batches list"""
    high_risk = CropBatch.query.filter(CropBatch.freshness_score < 0.3).order_by(CropBatch.freshness_score.asc()).limit(10).all()
    return jsonify([{
        "id": b.id,
        "crop_type": b.crop_type,
        "freshness_score": round(float(b.freshness_score or 0), 2),
        "warehouse": b.warehouse or "N/A",
        "days_remaining": int((b.freshness_score or 0) * 30)
    } for b in high_risk])

@admin_bp.get("/warehouse-locations")
@roles_required(ROLE_ADMIN)
def get_warehouse_locations():
    """Get list of warehouses with batch counts"""
    # Get unique warehouse names from batches
    warehouses = db.session.query(CropBatch.warehouse).distinct().all()
    warehouse_names = [w[0] for w in warehouses if w[0]]
    
    # Add default warehouses if none exist
    if not warehouse_names:
        warehouse_names = [
            "Delhi Warehouse",
            "Chandigarh Warehouse", 
            "Bengaluru Warehouse",
            "Mumbai Warehouse",
            "Chennai Warehouse",
            "Kolkata Warehouse",
            "Hyderabad Warehouse",
            "Ahmedabad Warehouse",
            "Nagpur Central Warehouse"
        ]
    
    return jsonify({"warehouse_locations": warehouse_names})

@admin_bp.get("/dashboard/shipments")
@roles_required(ROLE_ADMIN)
def get_shipments():
    """Get all shipments with optional status filter"""
    status_filter = request.args.get('status', '')
    
    query = Shipment.query
    
    if status_filter:
        query = query.filter(Shipment.status == status_filter)
    
    shipments = query.order_by(Shipment.created_at.desc()).all()
    
    return jsonify([{
        "id": s.id,
        "source": s.source_warehouse or s.pickup_location or "N/A",
        "destination": s.destination or s.destination_warehouse or "N/A",
        "status": s.status or "UNKNOWN",
        "delay_status": "On Time",  # Default since no delay_status field exists
        "batch_id": s.batch_id,
        "created_at": s.created_at.isoformat() if s.created_at else None
    } for s in shipments])

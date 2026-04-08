from datetime import datetime
from .extensions import db

ROLE_FARMER = "farmer"
ROLE_WAREHOUSE = "warehouse"
ROLE_LOGISTICS = "logistics"
ROLE_ADMIN = "admin"

class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    warehouse_location = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    role = db.relationship("Role")

class UserRole(db.Model):
    __tablename__ = "user_roles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

class CropBatch(db.Model):
    __tablename__ = "crop_batches"
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    crop_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    quantity_unit = db.Column(db.String(32))
    harvest_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    warehouse = db.Column(db.String(200))
    current_stage = db.Column(db.String(32))
    warehouse_name = db.Column(db.String(200))
    storage_start_date = db.Column(db.Date)
    last_simulated_date = db.Column(db.Date)
    warehouse_entry_date = db.Column(db.Date)
    last_freshness_update_date = db.Column(db.Date)
    farmer_freshness_snapshot = db.Column(db.Float)
    warehouse_entry_freshness = db.Column(db.Float)
    warehouse_freshness = db.Column(db.Float)
    status = db.Column(db.String(50), default="submitted")
    freshness_score = db.Column(db.Float)
    spoilage_risk = db.Column(db.Float)
    seasonal_risk = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FarmerProfile(db.Model):
    __tablename__ = "farmer_profile"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    land_size = db.Column(db.Float)
    farm_location = db.Column(db.String(200))

class WarehouseStatus(db.Model):
    __tablename__ = "warehouse_status"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("crop_batches.id"), nullable=False)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    storage_duration_hours = db.Column(db.Integer)
    status = db.Column(db.String(50), default="safe")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    warehouse_location = db.Column(db.String(200), nullable=True)

class StorageLog(db.Model):
    __tablename__ = "storage_logs"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("crop_batches.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    condition_status = db.Column(db.String(50))

class Shipment(db.Model):
    __tablename__ = "shipments"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("crop_batches.id"), nullable=False)
    crop = db.Column(db.String(100))
    quantity = db.Column(db.Float)
    pickup_location = db.Column(db.String(200))
    destination_warehouse = db.Column(db.String(200))
    initial_freshness = db.Column(db.Float)
    current_freshness = db.Column(db.Float)
    transit_start_time = db.Column(db.DateTime)
    pickup_confirmed_at = db.Column(db.DateTime)
    delivery_time = db.Column(db.DateTime)
    last_route_update = db.Column(db.DateTime)
    last_freshness_update = db.Column(db.DateTime)
    last_telemetry_at = db.Column(db.DateTime)
    last_temperature = db.Column(db.Float)
    last_humidity = db.Column(db.Float)
    transit_hours_total = db.Column(db.Float)
    exporter_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    logistics_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    route = db.Column(db.Text)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id"))
    status = db.Column(db.String(50), default="planned")
    eta_hours = db.Column(db.Float)
    warehouse_exit_freshness = db.Column(db.Float)
    warehouse_exit_date = db.Column(db.Date)
    source_warehouse = db.Column(db.String(200))
    destination = db.Column(db.String(200))
    mode = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))

class Route(db.Model):
    __tablename__ = "routes"
    id = db.Column(db.Integer, primary_key=True)
    distance = db.Column(db.Float)
    transport_mode = db.Column(db.String(50))

class MLPrediction(db.Model):
    __tablename__ = "ml_predictions"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("crop_batches.id"))
    model_type = db.Column(db.String(50))
    prediction = db.Column(db.Float)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MLMetric(db.Model):
    __tablename__ = "ml_metrics"
    id = db.Column(db.Integer, primary_key=True)
    model_type = db.Column(db.String(50))
    accuracy = db.Column(db.Float)
    precision = db.Column(db.Float)
    recall = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DisasterEvent(db.Model):
    __tablename__ = "disaster_events"
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(200))
    region = db.Column(db.String(200))
    event_type = db.Column(db.String(100))
    severity = db.Column(db.String(50))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WeatherLog(db.Model):
    __tablename__ = "weather_logs"
    id = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(200))
    rainfall = db.Column(db.Float)
    alerts = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlockchainLog(db.Model):
    __tablename__ = "blockchain_logs"
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(120))
    reference_id = db.Column(db.Integer)
    batch_id = db.Column(db.Integer)
    shipment_id = db.Column(db.Integer)
    tx_hash = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GenAISuggestion(db.Model):
    __tablename__ = "genai_suggestions"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("crop_batches.id"))
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id"))
    context = db.Column(db.Text)
    suggested_routes = db.Column(db.Text)
    methods = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SalvageBatch(db.Model):
    __tablename__ = "salvage_batches"
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("crop_batches.id"), nullable=False)
    crop = db.Column(db.String(100))
    quantity_pct = db.Column(db.Float)
    reason = db.Column(db.String(200), default="Shelf life exhausted")
    salvage_status = db.Column(db.String(50), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

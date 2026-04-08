# Schema Mapping: Dashboard → Tables/Models

## Overview
- **Framework**: Flask → SQLAlchemy → SQLite + Blockchain Hash Verification
- **Goal**: Every dashboard action is traceable in SQLite

---

## Dashboard → Table Mapping

| Dashboard | Routes | Primary Tables/Models | Key Operations |
|-----------|--------|----------------------|----------------|
| **Farmer** | `/api/farmer/batches` (POST/GET), `/api/farmer/blockchain_log` | `CropBatch`, `MLPrediction`, `Shipment`, `WarehouseStatus`, `BlockchainLog` | Submit batch, list batches, log blockchain |
| **Warehouse** | `/api/warehouse/status` (GET/POST) | `WarehouseStatus`, `CropBatch` | Update warehouse conditions, view status |
| **Exporter** | `/api/exporter/assignments` | `Shipment`, `CropBatch` | View assigned shipments |
| **Logistics** | `/api/logistics/plan`, `/api/logistics/status`, `/api/logistics/my_shipments`, `/api/logistics/predict_delay`, `/api/logistics/preview` | `Shipment`, `DisasterEvent`, `BlockchainLog` | Plan routes, update status, predict delays |
| **Government** | `/api/government/batches`, `/api/government/exporters`, `/api/government/assign_exporter` | `CropBatch`, `Shipment`, `BlockchainLog`, `User`, `Role` | View all batches, assign exporters |
| **Admin** | `/api/admin/users` (GET/POST) | `User`, `Role` | Manage users |
| **Auth** | `/api/auth/register`, `/api/auth/login`, `/api/auth/me` | `User`, `Role`, `UserRole` | Authentication |
| **Dashboards** | `/{farmer,warehouse,exporter,logistics,government,admin}` | Templates only (no DB ops) | Serve frontend pages |

---

## Column Validation Summary

### Core Tables (All Required Columns Present)
- **User**: id, name, email, password_hash, role_id, is_active, created_at
- **Role**: id, name
- **UserRole**: id, user_id, role_id
- **CropBatch**: id, farmer_id, crop_type, quantity, harvest_date, location, status, freshness_score, spoilage_risk, created_at
- **WarehouseStatus**: id, batch_id, temperature, humidity, storage_duration_hours, status, timestamp
- **Shipment**: id, batch_id, exporter_id, logistics_id, route, status, eta_hours, created_at
- **MLPrediction**: id, batch_id, model_type, prediction, details, created_at
- **BlockchainLog**: id, action, reference_id, tx_hash, created_at

### Supporting Tables
- **FarmerProfile**: id, user_id, land_size, farm_location
- **StorageLog**: id, batch_id, timestamp, condition_status
- **Route**: id, distance, transport_mode
- **MLMetric**: id, model_type, accuracy, precision, recall, created_at
- **DisasterEvent**: id, location, event_type, severity, details, created_at
- **WeatherLog**: id, region, rainfall, alerts, created_at
- **GenAISuggestion**: id, context, suggested_routes, methods, created_at

---

## Issues Identified

### 1. Potential Redundancy
- `UserRole` table may be redundant since `User.role_id` already provides the primary role
- `StorageLog` appears underutilized; similar data exists in `WarehouseStatus`

### 2. Missing Traceability
- Some actions lack explicit audit trails:
  - Warehouse status updates don't log who made the change
  - Logistics route planning doesn't always create blockchain logs
  - Admin user status changes lack audit logging

### 3. Incomplete Relationships
- `Route` table exists but is not linked to `Shipment` via foreign key
- `GenAISuggestion` is not linked to any specific batch or shipment

---

## Recommendations

### High Priority
1. Add audit fields to critical tables:
   - `WarehouseStatus`: add `updated_by` (user_id)
   - `Shipment`: add `updated_by` (user_id)
2. Create explicit foreign key from `Shipment.route` to `Route.id`
3. Link `GenAISuggestion` to `batch_id` or `shipment_id`

### Medium Priority
1. Evaluate necessity of `UserRole` vs `User.role_id`
2. Consider consolidating `StorageLog` into `WarehouseStatus`
3. Add blockchain logging for all state-changing operations

### Low Priority
1. Add indexes for frequently queried fields
2. Consider soft delete for critical records

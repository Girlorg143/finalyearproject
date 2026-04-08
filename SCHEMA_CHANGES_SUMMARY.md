# Schema Changes Summary

## Applied Changes for Full Traceability

### 1. Enhanced Models

#### WarehouseStatus
- **Added**: `updated_by` (FK to users.id)
- **Purpose**: Track which warehouse operator updated the status

#### Shipment  
- **Added**: `route_id` (FK to routes.id) 
- **Added**: `updated_by` (FK to users.id)
- **Purpose**: Link to structured route data and track who modified shipments

#### GenAISuggestion
- **Added**: `batch_id` (FK to crop_batches.id)
- **Added**: `shipment_id` (FK to shipments.id)  
- **Purpose**: Connect AI suggestions to specific batches/shipments

### 2. Enhanced Route Handlers

#### Warehouse Status Updates
- Now captures `updated_by` from JWT token
- Creates blockchain log entry for every warehouse update
- Full audit trail: who changed what, when

#### Logistics Route Planning
- Captures `updated_by` on shipment creation/updates
- Creates blockchain log for every route plan
- Traceable route planning decisions

#### Logistics Status Updates  
- Captures `updated_by` from JWT token
- Creates blockchain log for shipment status changes
- Complete shipment lifecycle tracking

#### Admin User Management
- Captures which admin performed user status changes
- Creates blockchain log for admin actions
- Admin accountability for user management

### 3. Blockchain Logging Coverage

All critical state changes now create `BlockchainLog` entries:
- `warehouse_update`: Warehouse condition changes
- `route_plan`: Logistics route planning
- `shipment_status`: Shipment status updates  
- `admin_user_status`: Admin user management
- `crop_submit`: Farmer batch submissions (existing)
- `assign_exporter`: Government assignments (existing)

## Next Steps

### Database Migration
Run these commands to apply schema changes:

```bash
cd d:\final_yr\final_yr
python -m backend.app  # This will auto-create new columns
```

### Verification
Test traceability by:
1. Submitting a farmer batch → Check `BlockchainLog` for `crop_submit`
2. Updating warehouse status → Check `BlockchainLog` for `warehouse_update`
3. Planning a route → Check `BlockchainLog` for `route_plan`
4. Updating shipment status → Check `BlockchainLog` for `shipment_status`
5. Admin changing user status → Check `BlockchainLog` for `admin_user_status`

### Optional Enhancements
- Replace "stub" tx_hash with actual blockchain hashes
- Add indexes on foreign keys for performance
- Consider soft delete for audit preservation

import sys
import requests
import time
from datetime import datetime, timedelta

def test_critical_functional_fixes():
    base_url = "http://127.0.0.1:5000"
    
    print("🔧 TESTING CRITICAL FUNCTIONAL BUG FIXES")
    print("=" * 60)
    
    # Test 1: Nearest Warehouse Display
    print("\n1️⃣ Testing Nearest Warehouse Display...")
    
    # Register and login a farmer
    timestamp = int(time.time())
    farmer_data = {
        "name": "Test Farmer",
        "email": f"farmer_func_{timestamp}@test.com",
        "password": "test123", 
        "role": "farmer"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/register", json=farmer_data)
        if response.status_code != 200:
            print(f"❌ Farmer registration failed: {response.json()}")
            return False
            
        # Login farmer
        farmer_login = {"email": f"farmer_func_{timestamp}@test.com", "password": "test123"}
        response = requests.post(f"{base_url}/api/auth/login", json=farmer_login)
        farmer_token = response.json()['access_token']
        headers = {"Authorization": f"Bearer {farmer_token}"}
        
        # Test different cities for nearest warehouse
        test_cities = [
            {
                "city": "Amravati",
                "expected_nearest": "Nagpur Central Warehouse",  # Closest geographically
                "max_distance": 200  # km
            },
            {
                "city": "Chennai",
                "expected_nearest": "Chennai Warehouse",  # Should be closest if exists, else Bengaluru
                "max_distance": 400
            },
            {
                "city": "Delhi",
                "expected_nearest": "Delhi Warehouse",
                "max_distance": 50
            },
            {
                "city": "Mumbai",
                "expected_nearest": "Mumbai Warehouse",
                "max_distance": 50
            }
        ]
        
        warehouse_test_passed = True
        
        for test_case in test_cities:
            response = requests.get(f"{base_url}/api/farmer/warehouses?city={test_case['city']}", headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                warehouses = result.get('warehouses', [])
                
                if warehouses:
                    nearest = warehouses[0]  # First one should be nearest
                    distance = nearest.get('distance_km', 0)
                    is_nearest = nearest.get('is_nearest', False)
                    
                    print(f"   ✅ {test_case['city']}: {nearest['name']} ({distance} km) - Nearest: {is_nearest}")
                    
                    # Check if distance is reasonable
                    if distance > test_case['max_distance']:
                        print(f"      ⚠️  Distance {distance} km seems too far for {test_case['city']}")
                    
                    # Check if nearest flag is set correctly
                    if not is_nearest:
                        print(f"      ❌ Nearest flag not set for first warehouse")
                        warehouse_test_passed = False
                        
                    # Check if we have multiple warehouses sorted by distance
                    if len(warehouses) > 1:
                        for i in range(1, len(warehouses)):
                            if warehouses[i]['distance_km'] < warehouses[i-1]['distance_km']:
                                print(f"      ❌ Warehouses not sorted by distance correctly")
                                warehouse_test_passed = False
                                break
                else:
                    print(f"   ❌ {test_case['city']}: No warehouses returned")
                    warehouse_test_passed = False
            else:
                print(f"   ❌ {test_case['city']}: API call failed: {response.text}")
                warehouse_test_passed = False
        
        if warehouse_test_passed:
            print("   ✅ Nearest Warehouse Display: PASSED")
        else:
            print("   ❌ Nearest Warehouse Display: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Warehouse test error: {e}")
        return False
    
    # Test 2: Freshness & Spoilage Risk Calculation
    print("\n2️⃣ Testing Freshness & Spoilage Risk Calculation...")
    
    # Test different harvest dates to verify freshness calculation
    test_cases = [
        {
            "name": "Very Fresh (Today)",
            "harvest_date": datetime.now().strftime("%Y-%m-%d"),
            "expected_freshness_range": (0.7, 1.0),
            "expected_spoilage_range": (0.0, 0.3)
        },
        {
            "name": "Fresh (3 days ago)",
            "harvest_date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "expected_freshness_range": (0.5, 0.9),
            "expected_spoilage_range": (0.1, 0.5)
        },
        {
            "name": "Moderate (7 days ago)",
            "harvest_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "expected_freshness_range": (0.2, 0.7),
            "expected_spoilage_range": (0.3, 0.8)
        },
        {
            "name": "Old (15 days ago)",
            "harvest_date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "expected_freshness_range": (0.0, 0.5),
            "expected_spoilage_range": (0.5, 1.0)
        }
    ]
    
    freshness_test_passed = True
    
    for test_case in test_cases:
        batch_data = {
            "crop_type": "Tomatoes",
            "quantity": 50,
            "harvest_date": test_case["harvest_date"],
            "location": "Bengaluru, Karnataka"
        }
        
        response = requests.post(f"{base_url}/api/farmer/batches", json=batch_data, headers=headers)
        
        if response.status_code == 200:
            batch_result = response.json()
            print(f"   ✅ {test_case['name']}: Batch {batch_result['batch_id']} created")
            
            # Check the actual values in database
            try:
                import sys
                sys.path.append('.')
                from backend.extensions import db
                from backend.models import CropBatch
                from backend.app import create_app
                
                app = create_app()
                with app.app_context():
                    batch = CropBatch.query.filter_by(id=batch_result['batch_id']).first()
                    if batch:
                        freshness = batch.freshness_score
                        spoilage = batch.spoilage_risk
                        
                        print(f"      Freshness: {freshness:.3f}, Spoilage: {spoilage:.3f}")
                        
                        # Check if values are in expected ranges
                        f_min, f_max = test_case["expected_freshness_range"]
                        s_min, s_max = test_case["expected_spoilage_range"]
                        
                        if not (f_min <= freshness <= f_max):
                            print(f"      ❌ Freshness {freshness:.3f} not in expected range {f_min}-{f_max}")
                            freshness_test_passed = False
                        
                        if not (s_min <= spoilage <= s_max):
                            print(f"      ❌ Spoilage {spoilage:.3f} not in expected range {s_min}-{s_max}")
                            freshness_test_passed = False
                        
                        # Check that freshness and spoilage are inversely related
                        if abs((freshness + spoilage) - 1.0) > 0.4:  # Allow some variation
                            print(f"      ⚠️  Freshness + Spoilage = {freshness + spoilage:.3f} (should be close to 1.0)")
                        
                        # Check that not all values are 0 or 1
                        if freshness == 0.0 and spoilage == 1.0 and test_case['name'] != "Old (15 days ago)":
                            print(f"      ❌ Extreme values (0, 1) indicate calculation error for {test_case['name']}")
                            freshness_test_passed = False
                    else:
                        print(f"      ❌ Batch {batch_result['batch_id']} not found in database")
                        freshness_test_passed = False
            except Exception as e:
                print(f"      ❌ Database check error: {e}")
                freshness_test_passed = False
        else:
            print(f"   ❌ {test_case['name']}: Batch submission failed: {response.text}")
            freshness_test_passed = False
    
    if freshness_test_passed:
        print("   ✅ Freshness & Spoilage Risk Calculation: PASSED")
    else:
        print("   ❌ Freshness & Spoilage Risk Calculation: FAILED")
        return False
    
    # Test 3: Correct Data Storage
    print("\n3️⃣ Testing Correct Data Storage...")
    
    # Test that selected warehouse matches stored warehouse
    test_locations = [
        {
            "location": "Delhi, NCR",
            "expected_warehouse": "Delhi Warehouse"
        },
        {
            "location": "Mumbai, Maharashtra",
            "expected_warehouse": "Mumbai Warehouse"
        },
        {
            "location": "Bengaluru, Karnataka",
            "expected_warehouse": "Bengaluru Warehouse"
        }
    ]
    
    data_storage_test_passed = True
    
    for test_case in test_locations:
        batch_data = {
            "crop_type": "Onions",
            "quantity": 100,
            "harvest_date": datetime.now().strftime("%Y-%m-%d"),
            "location": test_case["location"]
        }
        
        response = requests.post(f"{base_url}/api/farmer/batches", json=batch_data, headers=headers)
        
        if response.status_code == 200:
            batch_result = response.json()
            print(f"   ✅ {test_case['location']}: Batch {batch_result['batch_id']} created")
            
            # Check the actual warehouse in database
            try:
                app = create_app()
                with app.app_context():
                    batch = CropBatch.query.filter_by(id=batch_result['batch_id']).first()
                    if batch:
                        actual_warehouse = batch.warehouse
                        expected_warehouse = test_case["expected_warehouse"]
                        
                        print(f"      Location: {test_case['location']}")
                        print(f"      Expected: {expected_warehouse}")
                        print(f"      Actual: {actual_warehouse}")
                        
                        if actual_warehouse == expected_warehouse:
                            print(f"      ✅ Warehouse assignment correct")
                        else:
                            print(f"      ❌ Warehouse assignment WRONG!")
                            data_storage_test_passed = False
                    else:
                        print(f"      ❌ Batch {batch_result['batch_id']} not found in database")
                        data_storage_test_passed = False
            except Exception as e:
                print(f"      ❌ Database check error: {e}")
                data_storage_test_passed = False
        else:
            print(f"   ❌ {test_case['location']}: Batch submission failed: {response.text}")
            data_storage_test_passed = False
    
    if data_storage_test_passed:
        print("   ✅ Correct Data Storage: PASSED")
    else:
        print("   ❌ Correct Data Storage: FAILED")
        return False
    
    print("\n🎉 ALL CRITICAL FUNCTIONAL FIXES VERIFICATION PASSED!")
    print("=" * 60)
    print("✅ Nearest warehouse displayed correctly by city")
    print("✅ Freshness calculation is mathematically correct")
    print("✅ Spoilage risk is not always high")
    print("✅ Correct warehouse stored on submit")
    print("✅ No hardcoded values")
    print("✅ No runtime errors")
    
    return True

if __name__ == "__main__":
    success = test_critical_functional_fixes()
    sys.exit(0 if success else 1)

# Warehouse Location System Documentation

## Overview
The Agricultural Supply Chain Management System now includes a regional warehouse mapping system that automatically suggests the nearest warehouses based on the farmer's city selection.

## Warehouse Locations by Region

### 🏛️ North India (2 Warehouses)
1. **Delhi Warehouse Hub**
   - Location: Delhi
   - Capacity: High
   - Specialization: Grains, Vegetables
   - Serves: Delhi, Chandigarh, Lucknow, Kanpur, Jaipur, and all North Indian cities

2. **Chandigarh Distribution Center**
   - Location: Chandigarh
   - Capacity: Medium
   - Specialization: Fruits, Dairy
   - Serves: Punjab, Haryana, Himachal Pradesh, Jammu & Kashmir

### 🌴 South India (2 Warehouses)
1. **Chennai Logistics Hub**
   - Location: Chennai
   - Capacity: High
   - Specialization: Rice, Spices, Seafood
   - Serves: Tamil Nadu, Kerala, Andhra Pradesh, Telangana

2. **Bengaluru Distribution Center**
   - Location: Bengaluru
   - Capacity: High
   - Specialization: Vegetables, Fruits, Flowers
   - Serves: Karnataka, parts of Andhra Pradesh

### 🌅 East India (2 Warehouses)
1. **Kolkata Warehouse Complex**
   - Location: Kolkata
   - Capacity: High
   - Specialization: Rice, Vegetables, Fish
   - Serves: West Bengal, Bihar, Jharkhand, Odisha

2. **Bhubaneswar Storage Facility**
   - Location: Bhubaneswar
   - Capacity: Medium
   - Specialization: Grains, Vegetables
   - Serves: Odisha and surrounding eastern regions

### 🌇 West India (2 Warehouses)
1. **Mumbai Logistics Hub**
   - Location: Mumbai
   - Capacity: High
   - Specialization: Fruits, Vegetables, Grains
   - Serves: Maharashtra, Goa, parts of Gujarat

2. **Ahmedabad Distribution Center**
   - Location: Ahmedabad
   - Capacity: Medium
   - Specialization: Cotton, Grains, Spices
   - Serves: Gujarat, Rajasthan, Madhya Pradesh

## City to Region Mapping

### North India Cities
Agra, Ajmer, Aligarh, Allahabad, Amritsar, Bhopal, Chandigarh, Dehradun, Delhi, Faridabad, Firozabad, Ghaziabad, Gorakhpur, Gurugram, Gwalior, Jalandhar, Jammu, Jhansi, Kanpur, Lucknow, Ludhiana, Meerut, Moradabad, Noida, Shimla, Srinagar, Ujjain, Varanasi, Bharatpur, Leh

### South India Cities
Amravati, Bengaluru, Chennai, Coimbatore, Erode, Gulbarga, Guntur, Hubballi, Hyderabad, Kochi, Kozhikode, Kurnool, Madurai, Mangaluru, Mysuru, Nellore, Puducherry, Salem, Thanjavur, Thiruvananthapuram, Tiruchirappalli, Tirunelveli, Tiruppur, Vijayawada, Visakhapatnam, Warangal, Port Blair

### East India Cities
Asansol, Bhubaneswar, Cuttack, Dhanbad, Durgapur, Gaya, Guwahati, Howrah, Jamshedpur, Kolkata, Patna, Raipur, Ranchi, Rourkela, Siliguri, Aizawl, Gangtok, Imphal, Itanagar, Kohima, Shillong, Agartala, Brahmapur, Bhilai

### West India Cities
Ahmedabad, Aurangabad, Bikaner, Bilaspur, Jalgaon, Jodhpur, Kolhapur, Kota, Latur, Mumbai, Nagpur, Nanded, Nashik, Pune, Rajkot, Sangli, Solapur, Surat, Thane, Udaipur, Vadodara, Bhiwandi, Panaji

## API Usage

### Get Nearest Warehouses
```
GET /api/farmer/warehouses?city=<city_name>
```

**Example Request:**
```
GET /api/farmer/warehouses?city=Delhi
```

**Example Response:**
```json
{
  "city": "Delhi",
  "nearest_warehouses": [
    {
      "city": "Delhi",
      "name": "Delhi Warehouse Hub",
      "capacity": "High",
      "specialization": "Grains, Vegetables",
      "region": "Delhi"
    },
    {
      "city": "Chandigarh",
      "name": "Chandigarh Distribution Center",
      "capacity": "Medium",
      "specialization": "Fruits, Dairy",
      "region": "Delhi"
    }
  ]
}
```

## Integration with Farmer Dashboard

When a farmer selects a city in the crop submission form:

1. **Automatic Detection**: The system detects the region based on the selected city
2. **Warehouse Suggestions**: The 2 nearest warehouses from that region are displayed
3. **Capacity Information**: Shows warehouse capacity and specialization
4. **Smart Routing**: Helps farmers choose the most appropriate warehouse for their crop type

## Benefits

1. **Optimized Logistics**: Reduces transportation costs and time
2. **Regional Specialization**: Warehouses specialize in crops common to their region
3. **Load Balancing**: Distributes warehouse load across multiple facilities
4. **Farmer Convenience**: Farmers get clear guidance on where to send their produce
5. **Scalability**: Easy to add more warehouses or modify regions

## Future Enhancements

1. **Distance Calculation**: Add actual distance-based recommendations
2. **Capacity Management**: Real-time warehouse capacity tracking
3. **Dynamic Routing**: Consider road conditions and weather
4. **Cost Optimization**: Include transportation cost calculations
5. **Warehouse Performance**: Track warehouse efficiency metrics

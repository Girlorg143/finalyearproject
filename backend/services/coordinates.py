"""
Geographic coordinates and distance calculation service
for accurate nearest warehouse determination
"""

import math
from typing import List, Tuple, Dict, Optional

# City coordinates (latitude, longitude) for major Indian cities
CITY_COORDINATES = {
    # North India
    "Delhi": (28.6139, 77.2090),
    "New Delhi": (28.6139, 77.2090),
    "Noida": (28.5355, 77.3910),
    "Gurgaon": (28.4595, 77.0266),
    "Ghaziabad": (28.6692, 77.4538),
    "Faridabad": (28.4089, 77.3178),
    "Gurugram": (28.4595, 77.0266),
    "Howrah": (22.5958, 88.2636),
    "Nizamabad": (18.6804, 78.0957),
    "Chandigarh": (30.7333, 76.7794),
    "Ludhiana": (30.9010, 75.8573),
    "Jalandhar": (31.3260, 75.5762),
    "Amritsar": (31.6340, 74.8723),
    "Jaipur": (26.9124, 75.7873),
    "Jodhpur": (26.2389, 73.0243),
    "Udaipur": (24.5854, 73.7125),
    "Ajmer": (26.4499, 74.6399),
    "Kota": (25.2138, 75.8648),
    "Bikaner": (28.0229, 73.3119),
    "Jammu": (32.7266, 74.8570),
    "Srinagar": (34.0837, 74.7973),
    "Dehradun": (30.3165, 78.0322),
    "Rishikesh": (30.0869, 78.2676),
    "Haridwar": (29.9457, 78.1642),
    "Lucknow": (26.8467, 80.9462),
    "Kanpur": (26.4499, 80.3319),
    "Agra": (27.1767, 78.0081),
    "Varanasi": (25.3176, 82.9739),
    "Allahabad": (25.4358, 81.8463),
    "Gorakhpur": (26.7483, 83.3792),
    "Bareilly": (28.3660, 79.4304),
    "Moradabad": (28.8389, 78.7733),
    "Saharanpur": (29.9640, 77.5460),
    "Firozabad": (27.1592, 78.3952),
    "Aligarh": (27.8974, 78.0884),
    "Meerut": (28.9845, 77.7064),
    "Sonipat": (28.9931, 77.0151),
    "Bhiwandi": (19.3002, 73.0578),
    "Bhopal": (23.2599, 77.4126),
    "Indore": (22.7196, 75.8577),
    "Gwalior": (26.2124, 78.1789),
    "Jabalpur": (23.1815, 79.9864),
    "Jhansi": (25.4484, 78.5685),
    
    # South India
    "Bengaluru": (12.9716, 77.5946),
    "Bangalore": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707),
    "Mysuru": (12.2958, 76.6394),
    "Mysore": (12.2958, 76.6394),
    "Hubballi": (15.3647, 75.1240),
    "Hubli": (15.3647, 75.1240),
    "Mangaluru": (12.9141, 74.8560),
    "Mangalore": (12.9141, 74.8560),
    "Tumkur": (13.3398, 77.1130),
    "Belagavi": (15.8497, 74.4977),
    "Belgaum": (15.8497, 74.4977),
    "Gulbarga": (17.3297, 76.8343),
    "Bidar": (17.9119, 77.5160),
    "Vijayawada": (16.5062, 80.6480),
    "Visakhapatnam": (17.6868, 83.2185),
    "Srikakulam": (18.2969, 83.8977),
    "Tirupati": (13.6288, 79.4191),
    "Kurnool": (15.8281, 78.0373),
    "Nellore": (14.4426, 79.9865),
    "Kochi": (9.9312, 76.2673),
    
    # Kerala Cities (Added)
    "Alappuzha": (9.4900, 76.3264),
    "Kollam": (8.8932, 76.6141),
    "Thrissur": (10.5276, 76.2144),
    "Kozhikode": (11.2588, 75.7804),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Kannur": (11.8745, 75.3704),
    "Kasaragod": (12.5000, 74.9860),
    "Malappuram": (11.0588, 76.0700),
    "Palakkad": (10.7867, 76.6548),
    "Pathanamthitta": (9.2700, 76.7900),
    "Idukki": (9.8500, 76.9700),
    "Wayanad": (11.7000, 76.2800),
    "Ernakulam": (9.9816, 76.2999),
    "Cochin": (9.9312, 76.2673),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Trivandrum": (8.5241, 76.9366),
    "Kozhikode": (11.2588, 75.7804),
    "Calicut": (11.2588, 75.7804),
    "Thrissur": (10.5276, 76.2144),
    "Kollam": (8.8932, 76.6141),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198),
    "Tiruchirappalli": (10.7905, 78.7047),
    "Salem": (11.6643, 78.1460),
    "Tirunelveli": (8.7139, 77.7567),
    "Erode": (11.3410, 77.7282),
    "Vellore": (12.9165, 79.1325),
    "Tiruppur": (11.1085, 77.3411),
    "Thanjavur": (10.7870, 79.1378),
    
    # East India
    "Howrah": (22.5958, 88.2636),
    "Kolkata": (22.5726, 88.3639),
    "Calcutta": (22.5726, 88.3639),
    # Chhattisgarh industrial city (used in farmer dashboard location input)
    "Bhilai": (21.1938, 81.3509),
    "Bhubaneswar": (20.2961, 85.8245),
    "Cuttack": (20.4625, 85.8830),
    "Rourkela": (22.2594, 84.8833),
    "Puri": (19.8135, 85.8312),
    "Jamshedpur": (22.8046, 86.2029),
    "Dhanbad": (23.7957, 86.4304),
    "Ranchi": (23.3441, 85.3096),
    "Patna": (25.5941, 85.1376),
    "Gaya": (24.7929, 85.0012),
    "Bhagalpur": (25.2352, 86.9799),
    "Muzaffarpur": (26.1199, 85.3900),
    "Siliguri": (26.7271, 88.4260),
    "Asansol": (23.6886, 86.9660),
    "Durgapur": (23.5483, 87.2913),
    "Guwahati": (26.1445, 91.7362),
    "Dispur": (26.1433, 91.7898),
    "Shillong": (25.5788, 91.8933),
    "Aizawl": (23.7271, 92.7176),
    "Imphal": (24.8170, 93.9368),
    "Agartala": (23.8315, 91.2868),
    "Kohima": (25.6701, 94.1078),
    "Itanagar": (27.0844, 93.6053),
    "Gangtok": (27.3314, 88.6138),
    
    # West India
    "Mumbai": (19.0760, 72.8777),
    "Bombay": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Nagpur": (21.1458, 79.0882),
    "Nashik": (19.9975, 73.7898),
    "Aurangabad": (19.8762, 75.3433),
    "Solapur": (17.6599, 75.9064),
    "Kolhapur": (16.7050, 74.2433),
    "Sangli": (16.8524, 74.5815),
    "Latur": (18.3980, 76.5797),
    "Ahmednagar": (19.0948, 74.7390),
    "Nanded": (19.1383, 77.3210),
    "Malegaon": (20.5541, 74.5310),
    "Jalgaon": (21.0077, 75.8567),
    "Dhule": (20.9042, 74.7796),
    "Ahmedabad": (23.0225, 72.5714),
    "Surat": (21.1702, 72.8311),
    "Thane": (19.2183, 72.9781),
    "Bilaspur": (22.0797, 82.1391),
    "Brahmapur": (19.3111, 84.7929),
    "Jorhat": (26.7509, 94.2036),
    "Kakinada": (16.9891, 82.2475),
    "Kharagpur": (22.3460, 87.2320),
    "Leh": (34.1526, 77.5770),
    "Port Blair": (11.6234, 92.7265),
    "Puducherry": (11.9416, 79.8083),
    "Rajahmundry": (17.0005, 81.8040),
    "Shimla": (31.1048, 77.1734),
    "Udupi": (13.3409, 74.7421),
    "Ujjain": (23.1765, 75.7885),
    "Varanasi": (25.3176, 82.9739),
    "Visakhapatnam": (17.6868, 83.2185),
    "Warangal": (17.9784, 79.5941),
    "Raipur": (21.2514, 81.6296),
    "Vadodara": (22.3072, 73.1812),
    "Baroda": (22.3072, 73.1812),
    "Rajkot": (22.3039, 70.8022),
    "Bhavnagar": (21.7645, 72.1519),
    "Jamnagar": (22.4707, 70.0577),
    "Junagadh": (21.5222, 70.4579),
    "Gandhinagar": (23.2156, 72.6369),
    "Anand": (22.5545, 72.9288),
    "Bharuch": (21.7075, 72.9975),
    "Porbandar": (21.6436, 69.6047),
    "Bhuj": (23.2472, 69.6702),
    "Panaji": (15.4909, 73.8278),
    "Panjim": (15.4909, 73.8278),
    "Margao": (15.2986, 73.9189),
    "Vasco": (15.3845, 73.8288),
    
    # Central India
    "Nagpur": (21.1458, 79.0882),
    "Amravati": (20.9374, 77.7796),
    "Akola": (20.7002, 77.0082),
    "Yavatmal": (20.3885, 78.1274),
    "Chandrapur": (19.9615, 79.2961),
    "Gondia": (21.4598, 80.1912),
    "Wardha": (20.7453, 78.6022),
    "Bhandara": (21.0934, 79.6547),
    "Gadchiroli": (20.7957, 80.0045),
    "Betul": (21.9049, 77.9030),
    "Chhindwara": (22.0577, 78.9369),
    "Seoni": (22.0924, 79.6475),
    "Mandla": (22.6030, 80.3768),
    "Balaghat": (21.8047, 80.1813),
    "Shahdol": (23.2932, 81.3545),
    "Umaria": (23.5348, 80.8358),
    "Singrauli": (24.2005, 82.6748),
    "Sidhi": (24.4087, 81.8802),
    "Satna": (24.5834, 80.8322),
    "Rewa": (24.5314, 81.2929),
    "Katni": (23.5746, 80.3536),
    "Jabalpur": (23.1815, 79.9864),
    "Dindori": (22.9426, 81.0751),
    "Mandla": (22.6030, 80.3768),
    "Anuppur": (23.1047, 81.6836),
    "Shahdol": (23.2932, 81.3545),
    "Umaria": (23.5348, 80.8358),
    "Panna": (24.7208, 80.2068),
    "Damoh": (23.8400, 79.0713),
    "Sagar": (23.8370, 78.7921),
    "Tikamgarh": (25.2869, 78.8285),
    "Chhatarpur": (24.9056, 79.5857),
    "Pithoragarh": (29.5813, 80.2181),
    "Almora": (29.5984, 79.6459),
    "Nainital": (29.3879, 79.4580),
    "Udham Singh Nagar": (28.9857, 79.4059),
    "Haldwani": (29.2245, 79.4608),
    "Roorkee": (29.8565, 77.8868),
    "Haridwar": (29.9457, 78.1642),
    "Rishikesh": (30.0869, 78.2676),
    "Dehradun": (30.3165, 78.0322),
    "Mussoorie": (30.4590, 78.0647),
    "Nainital": (29.3879, 79.4580),
    "Ranikhet": (29.6468, 79.4258),
    "Almora": (29.5984, 79.6459),
    "Bageshwar": (29.8373, 79.7763),
    "Champawat": (29.3315, 80.0995),
    "Pithoragarh": (29.5813, 80.2181),
    "Udham Singh Nagar": (28.9857, 79.4059),
    "Uttarkashi": (30.7329, 78.3478),
    "Chamoli": (30.4010, 79.3499),
    "Rudraprayag": (30.2845, 78.9874),
    "Tehri Garhwal": (30.3784, 78.4549),
    "Garhwal": (30.0668, 79.4092),
    "Pauri Garhwal": (29.8455, 78.7787),
    "Dehradun": (30.3165, 78.0322)
}

# Warehouse coordinates (latitude, longitude)
WAREHOUSE_COORDINATES = {
    "Delhi Warehouse": (28.6139, 77.2090),
    "Chandigarh Warehouse": (30.7333, 76.7794),
    "Bengaluru Warehouse": (12.9716, 77.5946),
    "Hyderabad Warehouse": (17.3850, 78.4867),
    "Kolkata Warehouse": (22.5726, 88.3639),
    "Bhubaneswar Warehouse": (20.2961, 85.8245),
    "Mumbai Warehouse": (19.0760, 72.8777),
    "Ahmedabad Warehouse": (23.0225, 72.5714),
    "Nagpur Central Warehouse": (21.1458, 79.0882)
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    
    Returns: Distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r

def get_city_coordinates(city: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a city name
    Handles various city name formats
    """
    if not city:
        return None
        
    # Clean up the city name
    city_clean = city.strip()
    
    # Handle common variations
    city_variations = {
        "Bangalore": "Bengaluru",
        "Trivandrum": "Thiruvananthapuram",
        "Calcutta": "Kolkata",
        "Bombay": "Mumbai",
        "Madras": "Chennai",
        "Cochin": "Kochi",
        "Calicut": "Kozhikode",
        "Baroda": "Vadodara",
        "Panjim": "Panaji"
    }
    
    # Check variations first
    if city_clean in city_variations:
        city_clean = city_variations[city_clean]
    
    # Try exact match
    if city_clean in CITY_COORDINATES:
        return CITY_COORDINATES[city_clean]
    
    # Try case-insensitive match
    city_lower = city_clean.lower()
    for name, coords in CITY_COORDINATES.items():
        if name.lower() == city_lower:
            return coords
    
    return None

def get_nearest_warehouses_by_distance(location: str, limit: int = 5) -> List[Tuple[str, float]]:
    """
    Get warehouses sorted by distance from the given location
    Returns list of (warehouse_name, distance_km) tuples
    """
    city_coords = get_city_coordinates(location)
    if not city_coords:
        print(f"DEBUG: No coordinates found for location: {location}")
        return []
    
    city_lat, city_lon = city_coords
    warehouse_distances = []
    
    for warehouse_name, (warehouse_lat, warehouse_lon) in WAREHOUSE_COORDINATES.items():
        distance = haversine_distance(city_lat, city_lon, warehouse_lat, warehouse_lon)
        warehouse_distances.append((warehouse_name, distance))
    
    # Sort by distance (ascending)
    warehouse_distances.sort(key=lambda x: x[1])
    
    print(f"DEBUG: Location {location} ({city_lat}, {city_lon})")
    print(f"DEBUG: Nearest warehouses: {warehouse_distances[:limit]}")
    
    return warehouse_distances[:limit]

def get_warehouse_coordinates(warehouse_name: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a warehouse
    """
    return WAREHOUSE_COORDINATES.get(warehouse_name)

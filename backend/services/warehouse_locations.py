"""
Warehouse Location Service - Maps cities to nearest warehouses
Updated with Central warehouse as backup option
"""

WAREHOUSE_REGIONS = {
    "North": ["Delhi Warehouse", "Chandigarh Warehouse"],
    "South": ["Bengaluru Warehouse", "Hyderabad Warehouse"], 
    "East": ["Kolkata Warehouse", "Bhubaneswar Warehouse"],
    "West": ["Mumbai Warehouse", "Ahmedabad Warehouse"],
    "Central": ["Nagpur Central Warehouse"]  # Always available as backup
}

# City to region mapping based on geography
CITY_TO_REGION = {
    # North India
    "Agra": "North", "Ajmer": "North", "Aligarh": "North", "Allahabad": "North",
    "Amritsar": "North", "Bhopal": "North", "Chandigarh": "North", "Dehradun": "North",
    "Delhi": "North", "Faridabad": "North", "Firozabad": "North", "Ghaziabad": "North",
    "Gorakhpur": "North", "Gurugram": "North", "Gwalior": "North", "Jalandhar": "North",
    "Jammu": "North", "Jhansi": "North", "Kanpur": "North", "Lucknow": "North",
    "Ludhiana": "North", "Meerut": "North", "Moradabad": "North", "Noida": "North",
    "Shimla": "North", "Srinagar": "North", "Ujjain": "North", "Varanasi": "North",
    "Bharatpur": "North", "Leh": "North", "Jabalpur": "North", "Indore": "North",
    
    # South India - Complete list with all Kerala, Tamil Nadu, Karnataka, Andhra, Telangana cities
    "Amravati": "South", "Bengaluru": "South", "Chennai": "South", "Coimbatore": "South",
    "Erode": "South", "Gulbarga": "South", "Guntur": "South", "Hubballi": "South",
    "Hyderabad": "South", "Kochi": "South", "Kozhikode": "South", "Kurnool": "South",
    "Madurai": "South", "Mangaluru": "South", "Mysuru": "South", "Nellore": "South",
    "Puducherry": "South", "Salem": "South", "Thanjavur": "South", "Thiruvananthapuram": "South",
    "Tiruchirappalli": "South", "Tirunelveli": "South", "Tiruppur": "South",
    "Vijayawada": "South", "Visakhapatnam": "South", "Warangal": "South", "Port Blair": "South",
    "Srikakulam": "South",
    "Kakinada": "South", "Rajahmundry": "South", "Tirupati": "South", "Anantapur": "South",
    "Kurnool": "South", "Nizamabad": "South", "Karimnagar": "South", "Khammam": "South",
    "Mahbubnagar": "South", "Nalgonda": "South", "Rangareddy": "South", "Medak": "South",
    
    # Kerala Cities (All South Region)
    "Alappuzha": "South", "Kollam": "South", "Thrissur": "South", "Kochi": "South",
    "Kozhikode": "South", "Thiruvananthapuram": "South", "Kannur": "South", "Kasaragod": "South",
    "Malappuram": "South", "Palakkad": "South", "Pathanamthitta": "South", "Idukki": "South",
    "Wayanad": "South", "Ernakulam": "South",
    
    # Additional South Indian Cities
    "Udupi": "South", "Vellore": "South", "Tirupati": "South", "Muzaffarpur": "South",
    "Kharagpur": "South", "Bellary": "South", "Hospet": "South", "Davanagere": "South",
    "Shimoga": "South", "Mangalore": "South", "Tumkur": "South", "Kolar": "South",
    "Chitradurga": "South", "Raichur": "South", "Bidar": "South", "Gulbarga": "South",
    "Bijapur": "South", "Bagalkot": "South", "Gadag": "South", "Haveri": "South",
    "Dharwad": "South", "Uttara Kannada": "South", "Dakshina Kannada": "South", "Udupi": "South",
    
    # East India
    "Asansol": "East", "Bhubaneswar": "East", "Cuttack": "East", "Dhanbad": "East",
    "Durgapur": "East", "Gaya": "East", "Guwahati": "East", "Howrah": "East",
    "Jamshedpur": "East", "Kolkata": "East", "Patna": "East", "Raipur": "East",
    "Ranchi": "East", "Rourkela": "East", "Siliguri": "East", "Aizawl": "East",
    "Gangtok": "East", "Imphal": "East", "Itanagar": "East", "Kohima": "East",
    "Shillong": "East", "Agartala": "East", "Brahmapur": "East", "Bhilai": "East",
    "Jorhat": "East", "Dibrugarh": "East", "Silchar": "East", "Malda": "East",
    
    # West India
    "Ahmedabad": "West", "Aurangabad": "West", "Bikaner": "West", "Bilaspur": "West",
    "Jalgaon": "West", "Jodhpur": "West", "Kolhapur": "West", "Kota": "West",
    "Latur": "West", "Mumbai": "West", "Nagpur": "West", "Nanded": "West",
    "Nashik": "West", "Pune": "West", "Rajkot": "West", "Sangli": "West",
    "Solapur": "West", "Surat": "West", "Thane": "West", "Udaipur": "West",
    "Vadodara": "West", "Bhiwandi": "West", "Panaji": "West", "Jamnagar": "West",
    "Junagadh": "West", "Bhavnagar": "West", "Porbandar": "West", "Rajkot": "West"
}

def get_nearest_warehouses(location: str) -> list:
    """Get nearest warehouses for a given location (regional + central backup)"""
    # Extract city name from full location string
    if ',' in location:
        city = location.split(',')[0].strip()
    else:
        city = location.strip()
    
    region = CITY_TO_REGION.get(city, "South")  # Default to South instead of North
    regional_warehouses = WAREHOUSE_REGIONS.get(region, ["Bengaluru Warehouse", "Hyderabad Warehouse"])
    central_warehouse = WAREHOUSE_REGIONS.get("Central", ["Nagpur Central Warehouse"])
    
    # Return regional warehouses first, then central warehouse as backup
    return regional_warehouses + central_warehouse

def get_warehouse_details(warehouse_name: str) -> dict:
    """Get warehouse details"""
    details = {
        "Delhi Warehouse": {"name": "Delhi Warehouse", "capacity": "High", "specialization": "Grains, Vegetables"},
        "Chandigarh Warehouse": {"name": "Chandigarh Warehouse", "capacity": "Medium", "specialization": "Fruits, Dairy"},
        "Bengaluru Warehouse": {"name": "Bengaluru Warehouse", "capacity": "High", "specialization": "Vegetables, Fruits, Flowers"},
        "Hyderabad Warehouse": {"name": "Hyderabad Warehouse", "capacity": "High", "specialization": "Rice, Spices, Seafood"},
        "Kolkata Warehouse": {"name": "Kolkata Warehouse", "capacity": "High", "specialization": "Rice, Vegetables, Fish"},
        "Bhubaneswar Warehouse": {"name": "Bhubaneswar Warehouse", "capacity": "Medium", "specialization": "Grains, Vegetables"},
        "Mumbai Warehouse": {"name": "Mumbai Warehouse", "capacity": "High", "specialization": "Fruits, Vegetables, Grains"},
        "Ahmedabad Warehouse": {"name": "Ahmedabad Warehouse", "capacity": "Medium", "specialization": "Cotton, Grains, Spices"},
        "Nagpur Central Warehouse": {"name": "Nagpur Central Warehouse", "capacity": "Very High", "specialization": "All Types - Central Backup"}
    }
    return details.get(warehouse_name, {"name": warehouse_name, "capacity": "Medium", "specialization": "General Storage"})

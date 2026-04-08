/**
 * Dynamic Warehouse Dropdown System
 * Updates warehouse options based on selected city
 */

class WarehouseDropdown {
    constructor() {
        this.citySelect = null;
        this.warehouseSelect = null;
        this.cities = [];
        this.init();
    }

    async init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupDropdowns());
        } else {
            this.setupDropdowns();
        }
    }

    setupDropdowns() {
        // Find or create city dropdown
        this.citySelect = document.getElementById('citySelect') || 
                        document.querySelector('select[name="city"]') ||
                        document.querySelector('select[id*="city"]');
        
        // Find or create warehouse dropdown
        this.warehouseSelect = document.getElementById('warehouseSelect') ||
                             document.querySelector('select[name="warehouse"]') ||
                             document.querySelector('select[id*="warehouse"]');

        console.log('Warehouse Dropdown Setup:', {
            citySelect: this.citySelect ? 'Found' : 'Not Found',
            warehouseSelect: this.warehouseSelect ? 'Found' : 'Not Found'
        });

        if (!this.citySelect) {
            console.error('City dropdown not found');
            return;
        }

        if (!this.warehouseSelect) {
            console.error('Warehouse dropdown not found');
            return;
        }

        // Add event listener for city change
        this.citySelect.addEventListener('change', () => {
            console.log('City changed to:', this.citySelect.value);
            this.onCityChange();
        });

        // Initialize with first city if selected
        if (this.citySelect.value) {
            console.log('Initial city found:', this.citySelect.value);
            setTimeout(() => this.onCityChange(), 100); // Delay to ensure cities are loaded
        }
    }

    populateCities() {
        // List of Indian cities from the backend
        const cities = [
            "Agra", "Ahmedabad", "Ajmer", "Aligarh", "Allahabad", "Amravati", "Amritsar", "Asansol",
            "Aurangabad", "Bengaluru", "Bhopal", "Bhubaneswar", "Bikaner", "Bilaspur", "Chandigarh",
            "Chennai", "Coimbatore", "Cuttack", "Dehradun", "Delhi", "Dhanbad", "Durgapur", "Erode",
            "Faridabad", "Firozabad", "Gaya", "Ghaziabad", "Gorakhpur", "Gulbarga", "Guntur", "Gurugram",
            "Guwahati", "Gwalior", "Howrah", "Hubballi", "Hyderabad", "Indore", "Jabalpur", "Jaipur",
            "Jalandhar", "Jammu", "Jamnagar", "Jamshedpur", "Jhansi", "Jodhpur", "Jorhat", "Kanpur",
            "Kochi", "Kolhapur", "Kolkata", "Kota", "Kozhikode", "Kurnool", "Latur", "Lucknow",
            "Ludhiana", "Madurai", "Mangaluru", "Meerut", "Moradabad", "Mumbai", "Mysuru", "Nagpur",
            "Nanded", "Nashik", "Nellore", "Noida", "Patna", "Puducherry", "Pune", "Raipur",
            "Rajahmundry", "Rajkot", "Ranchi", "Rourkela", "Salem", "Sangli", "Shimla", "Siliguri",
            "Solapur", "Srinagar", "Surat", "Thane", "Thanjavur", "Thiruvananthapuram", "Tiruchirappalli",
            "Tirunelveli", "Tiruppur", "Udaipur", "Ujjain", "Vadodara", "Varanasi", "Vijayawada",
            "Visakhapatnam", "Warangal", "Aizawl", "Gangtok", "Imphal", "Itanagar", "Kohima", "Panaji",
            "Shillong", "Agartala", "Port Blair", "Leh", "Brahmapur", "Jalgaon", "Bharatpur", "Bhilai", "Bhiwandi"
        ];

        // Get current language for translations
        const currentLang = localStorage.getItem('farmer_lang') || 'en';

        // Clear existing options except placeholder
        const placeholderText = currentLang === 'en' ? 'Select City' : (typeof t_ === 'function' ? t_('selectCity') : 'Select City');
        this.citySelect.innerHTML = `<option value="">${placeholderText}</option>`;
        
        // Add cities sorted alphabetically with translations
        console.log('Populating cities with lang:', currentLang);
        console.log('translateCityName available:', typeof translateCityName === 'function');
        cities.sort().forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            // Translate city name if translation function is available
            if (typeof translateCityName === 'function') {
                option.textContent = translateCityName(city, currentLang);
                console.log(`City: ${city} -> ${option.textContent}`);
            } else {
                console.log(`City: ${city} -> NO TRANSLATION FUNCTION`);
                option.textContent = city;
            }
            this.citySelect.appendChild(option);
        });
    }

    async onCityChange() {
        const selectedCity = this.citySelect.value;
        console.log('onCityChange called with city:', selectedCity);
        
        if (!selectedCity) {
            console.log('No city selected, clearing warehouse dropdown');
            this.clearWarehouseDropdown();
            return;
        }

        try {
            // Show loading state
            this.warehouseSelect.innerHTML = '<option value="">Loading warehouses...</option>';
            this.warehouseSelect.disabled = true;

            console.log('Fetching warehouses for city:', selectedCity);
            // Fetch warehouses for selected city
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            const headers = token ? { 'Authorization': 'Bearer ' + token } : {};
            const response = await fetch(`/api/farmer/warehouses?city=${encodeURIComponent(selectedCity)}`, { headers });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Warehouse data received:', data);
            this.populateWarehouseDropdown(data.warehouses || data.nearest_warehouses);

        } catch (error) {
            console.error('Error fetching warehouses:', error);
            this.warehouseSelect.innerHTML = '<option value="">Error loading warehouses</option>';
        } finally {
            this.warehouseSelect.disabled = false;
        }
    }

    populateWarehouseDropdown(warehouses) {
        // Get current language for translations
        const currentLang = localStorage.getItem('farmer_lang') || 'en';

        // Clear existing options
        const placeholderText = currentLang === 'en' ? 'Select Warehouse' : (typeof t_ === 'function' ? t_('selectWarehouse') : 'Select Warehouse');
        this.warehouseSelect.innerHTML = `<option value="">${placeholderText}</option>`;

        // Add warehouse options with translations
        warehouses.forEach(warehouse => {
            const option = document.createElement('option');
            option.value = warehouse.name;
            
            // Translate warehouse name if translation function is available
            let displayText = warehouse.name;
            if (typeof translateWarehouseName === 'function') {
                // Build display name with storage type if available
                const storageType = warehouse.storage_type || this.getStorageType(warehouse.name);
                const fullName = storageType ? `${warehouse.name} (${storageType})` : warehouse.name;
                displayText = translateWarehouseName(fullName, currentLang);
            }
            option.textContent = displayText;
            
            // Add data attributes for additional info
            option.setAttribute('data-capacity', warehouse.capacity);
            option.setAttribute('data-specialization', warehouse.specialization);
            option.setAttribute('data-is-central-backup', warehouse.is_central_backup);
            
            this.warehouseSelect.appendChild(option);
        });

        // Enable warehouse dropdown
        this.warehouseSelect.disabled = false;

        // Add event listener for warehouse selection
        this.warehouseSelect.addEventListener('change', () => this.showWarehouseInfo());
    }

    clearWarehouseDropdown() {
        // Get current language for translations
        const currentLang = localStorage.getItem('farmer_lang') || 'en';
        const placeholderText = currentLang === 'en' ? 'Select City First' : (typeof t_ === 'function' ? t_('selectCityFirst') : 'Select City First');
        
        this.warehouseSelect.innerHTML = `<option value="">${placeholderText}</option>`;
        this.warehouseSelect.disabled = true;
        
        // Clear warehouse info
        const infoDiv = document.getElementById('warehouse_info');
        if (infoDiv) {
            infoDiv.textContent = '';
        }
    }

    showWarehouseInfo() {
        const details = this.getSelectedWarehouseDetails();
        const infoDiv = document.getElementById('warehouse_info');
        
        if (!details || !details.name) {
            if (infoDiv) infoDiv.textContent = '';
            return;
        }

        let infoText = `Selected: ${details.name}`;
        
        if (infoDiv) {
            infoDiv.textContent = infoText;
            infoDiv.style.color = '#666';
        }
    }

    // Utility method to get selected warehouse details
    getSelectedWarehouseDetails() {
        const selectedOption = this.warehouseSelect.options[this.warehouseSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            return null;
        }

        return {
            name: selectedOption.value,
            capacity: selectedOption.getAttribute('data-capacity'),
            specialization: selectedOption.getAttribute('data-specialization'),
            isCentralBackup: selectedOption.getAttribute('data-is-central-backup') === 'true'
        };
    }

    // Utility method to get storage type for a warehouse
    getStorageType(warehouseName) {
        const storageMap = {
            'Delhi Warehouse': 'DRY',
            'Chandigarh Warehouse': 'COLD',
            'Nagpur Central Warehouse': 'DRY+COLD',
            'Bengaluru Warehouse': 'DRY+COLD',
            'Hyderabad Warehouse': 'DRY+COLD',
            'Kolkata Warehouse': 'DRY+COLD',
            'Bhubaneswar Warehouse': 'DRY',
            'Mumbai Warehouse': 'DRY+COLD',
            'Ahmedabad Warehouse': 'DRY'
        };
        return storageMap[warehouseName] || 'DRY';
    }

    // Utility method to reset both dropdowns
    reset() {
        this.citySelect.value = '';
        this.clearWarehouseDropdown();
    }
}

// Auto-initialize when script loads
const warehouseDropdown = new WarehouseDropdown();

// Export for global access
window.WarehouseDropdown = WarehouseDropdown;
window.warehouseDropdown = warehouseDropdown;

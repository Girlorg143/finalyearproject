// Admin Dashboard JavaScript
const API_BASE = '/api/admin';
const HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
};

let freshnessChart, riskChart, trendChart, cropChart, shelfLifeChart;
let currentFilters = { crop_type: '', risk_level: '', date_from: '', date_to: '' };

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadCharts();
    loadBatchesTable();
    populateCropFilter();
    
    // Load initial section data
    loadFarmers();
    loadWarehouses();
    loadShipments();
});

// Tab Switching Function
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Update section visibility
    document.querySelectorAll('.section-view').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`${tabName}-section`).classList.add('active');
    
    // Load section-specific data
    if (tabName === 'farmers') {
        loadFarmers();
        loadCharts();
    }
    if (tabName === 'warehouses') {
        loadWarehouses();
        loadWarehouseInsights();
    }
    if (tabName === 'logistics') {
        loadShipments();
        loadLogisticsInsights();
    }
}

async function loadDashboardStats() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/stats`, { headers: HEADERS });
        if (!res.ok) {
            const errorText = await res.text();
            console.error('Server error:', errorText);
            throw new Error(`Failed to load stats: ${res.status}`);
        }
        const data = await res.json();
        
        document.getElementById('totalBatches').textContent = data.total_batches;
        document.getElementById('safeBatches').textContent = data.safe_count;
        document.getElementById('riskBatches').textContent = data.risk_count;
        document.getElementById('highBatches').textContent = data.high_count;
        document.getElementById('totalShipments').textContent = data.total_shipments;
        
        const shipmentDetails = document.getElementById('shipmentDetails');
        if (shipmentDetails) {
            shipmentDetails.textContent = `Transit: ${data.in_transit} | Delivered: ${data.delivered}`;
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadCharts() {
    await loadFreshnessChart();
    await loadRiskChart();
    await loadTrendChart();
    await loadCropChart();
    await loadShelfLifeChart();
}

async function loadFreshnessChart() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/charts/freshness`, { headers: HEADERS });
        const data = await res.json();
        
        const ctx = document.getElementById('freshnessChart').getContext('2d');
        if (freshnessChart) freshnessChart.destroy();
        
        freshnessChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => `Batch #${d.id}`),
                datasets: [{
                    label: 'Freshness Score',
                    data: data.map(d => d.freshness),
                    backgroundColor: data.map(d => d.freshness >= 0.7 ? '#22c55e' : d.freshness >= 0.4 ? '#f59e0b' : '#ef4444'),
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 1, title: { display: true, text: 'Freshness (0-1)' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    } catch (error) {
        console.error('Error loading freshness chart:', error);
    }
}

async function loadRiskChart() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/charts/risk`, { headers: HEADERS });
        const data = await res.json();
        
        const ctx = document.getElementById('riskChart').getContext('2d');
        if (riskChart) riskChart.destroy();
        
        riskChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.data,
                    backgroundColor: data.colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    } catch (error) {
        console.error('Error loading risk chart:', error);
    }
}

async function loadTrendChart() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/charts/trend`, { headers: HEADERS });
        const data = await res.json();
        
        const ctx = document.getElementById('trendChart').getContext('2d');
        if (trendChart) trendChart.destroy();
        
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Average Freshness',
                    data: data.map(d => d.freshness),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 1, title: { display: true, text: 'Freshness Score' } }
                }
            }
        });
    } catch (error) {
        console.error('Error loading trend chart:', error);
    }
}

async function loadCropChart() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/charts/crops`, { headers: HEADERS });
        const data = await res.json();
        
        const ctx = document.getElementById('cropChart').getContext('2d');
        if (cropChart) cropChart.destroy();
        
        cropChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.crop),
                datasets: [{
                    label: 'Avg Freshness',
                    data: data.map(d => d.avg_freshness),
                    backgroundColor: '#8b5cf6',
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 1, title: { display: true, text: 'Avg Freshness' } }
                }
            }
        });
    } catch (error) {
        console.error('Error loading crop chart:', error);
    }
}

async function loadShelfLifeChart() {
    try {
        // Static shelf life data for common crops (in days)
        const shelfLifeData = [
            { crop: 'Grapes', days: 7 },
            { crop: 'Tomato', days: 7 },
            { crop: 'Brinjal', days: 12 },
            { crop: 'Rice', days: 365 },
            { crop: 'Wheat', days: 365 },
            { crop: 'Maize', days: 180 },
            { crop: 'Orange', days: 21 },
            { crop: 'Pulses', days: 365 },
            { crop: 'Cabbage', days: 60 },
            { crop: 'Soybean', days: 180 },
            { crop: 'Banana', days: 7 },
            { crop: 'Groundnut', days: 180 },
            { crop: 'Cauliflower', days: 21 },
            { crop: 'Onion', days: 180 },
            { crop: 'Mango', days: 14 },
            { crop: 'Cotton', days: 365 },
            { crop: 'Chilli', days: 180 },
            { crop: 'Potato', days: 90 },
            { crop: 'Sugarcane', days: 14 },
            { crop: 'Apple', days: 180 }
        ];
        
        const ctx = document.getElementById('shelfLifeChart').getContext('2d');
        if (shelfLifeChart) shelfLifeChart.destroy();
        
        shelfLifeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: shelfLifeData.map(d => d.crop),
                datasets: [{
                    label: 'Max Shelf Life (Days)',
                    data: shelfLifeData.map(d => d.days),
                    backgroundColor: '#3b82f6',
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        beginAtZero: true, 
                        title: { display: true, text: 'Max Shelf Life (Days)' }
                    },
                    x: {
                        ticks: {
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    } catch (error) {
        console.error('Error loading shelf life chart:', error);
    }
}

async function loadBatchesTable() {
    try {
        const queryParams = new URLSearchParams();
        if (currentFilters.crop_type) queryParams.append('crop_type', currentFilters.crop_type);
        if (currentFilters.risk_level) queryParams.append('risk_level', currentFilters.risk_level);
        if (currentFilters.date_from) queryParams.append('date_from', currentFilters.date_from);
        if (currentFilters.date_to) queryParams.append('date_to', currentFilters.date_to);
        
        const url = `${API_BASE}/dashboard/batches?${queryParams.toString()}`;
        const res = await fetch(url, { headers: HEADERS });
        
        if (!res.ok) throw new Error('Failed to load batches');
        const data = await res.json();
        
        const tbody = document.getElementById('tableBody');
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">No batches found</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.map(b => `
            <tr>
                <td>#${b.id}</td>
                <td>${b.crop_type}</td>
                <td>${b.freshness_score.toFixed(2)}</td>
                <td><span class="badge badge-${b.farmer_risk_status.toLowerCase()}">${b.farmer_risk_status}</span></td>
                <td>${b.days_remaining || 'N/A'}</td>
                <td>${b.status || 'N/A'}</td>
                <td>${b.warehouse || 'N/A'}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading batches:', error);
        document.getElementById('tableBody').innerHTML = '<tr><td colspan="7" class="error">Failed to load data</td></tr>';
    }
}

async function loadRecentAlerts() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/alerts/recent`, { headers: HEADERS });
        const data = await res.json();
        
        const container = document.getElementById('recentAlerts');
        if (data.length === 0) {
            container.innerHTML = '<p class="no-data">No recent alerts</p>';
            return;
        }
        
        container.innerHTML = data.map(a => `
            <div class="alert-item alert-${a.severity.toLowerCase()}">
                <strong>Batch #${a.batch_id}:</strong> ${a.message}
                <small>${new Date(a.created_at).toLocaleString()}</small>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

async function loadHighRiskBatches() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/batches/high-risk`, { headers: HEADERS });
        const data = await res.json();
        
        const container = document.getElementById('highRiskList');
        if (data.length === 0) {
            container.innerHTML = '<p class="no-data">No high-risk batches</p>';
            return;
        }
        
        container.innerHTML = data.map(b => `
            <div class="risk-item">
                <strong>Batch #${b.id}:</strong> ${b.crop_type}
                <span class="freshness">Freshness: ${b.freshness_score.toFixed(2)}</span>
                <span class="days">${b.days_remaining} days left</span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading high-risk batches:', error);
    }
}

async function loadUsers() {
    try {
        const res = await fetch(`${API_BASE}/users`, { headers: HEADERS });
        if (!res.ok) throw new Error('Failed to load users');
        const data = await res.json();
        console.log('Loaded', data.length, 'users');
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

async function populateCropFilter() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/batches`, { headers: HEADERS });
        const data = await res.json();
        const crops = [...new Set(data.map(b => b.crop_type))].sort();
        
        const select = document.getElementById('filterCrop');
        select.innerHTML = '<option value="">All Crops</option>' + 
            crops.map(c => `<option value="${c}">${c}</option>`).join('');
    } catch (error) {
        console.error('Error populating crop filter:', error);
    }
}

// Load Farmers Data
async function loadFarmers() {
    try {
        const search = document.getElementById('farmerSearch')?.value || '';
        const res = await fetch(`${API_BASE}/users?role=farmer&search=${search}`, { headers: HEADERS });
        
        if (!res.ok) throw new Error('Failed to load farmers');
        const data = await res.json();
        
        const tbody = document.getElementById('farmersTableBody');
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No farmers found</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.map(f => `
            <tr>
                <td>${f.name}</td>
                <td>${f.total_batches || 0}</td>
                <td>${f.active_batches || 0}</td>
                <td>${f.high_risk_batches || 0}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading farmers:', error);
        document.getElementById('farmersTableBody').innerHTML = '<tr><td colspan="4" class="error">Failed to load farmers</td></tr>';
    }
}

// Load Warehouses Data
async function loadWarehouses() {
    try {
        const res = await fetch(`${API_BASE}/warehouse-locations`, { headers: HEADERS });
        
        if (!res.ok) throw new Error('Failed to load warehouses');
        const data = await res.json();
        
        const tbody = document.getElementById('warehousesTableBody');
        if (!data.warehouse_locations || data.warehouse_locations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No warehouses found</td></tr>';
            return;
        }
        
        // For each warehouse, get batch count info
        const warehouseData = await Promise.all(
            data.warehouse_locations.map(async (wh) => {
                try {
                    const batchRes = await fetch(`${API_BASE}/dashboard/batches?warehouse=${encodeURIComponent(wh)}`, { headers: HEADERS });
                    const batches = await batchRes.json();
                    const highRisk = batches.filter(b => b.farmer_risk_status === 'HIGH').length;
                    return {
                        name: wh,
                        location: wh.replace(' Warehouse', ''),
                        stored_batches: batches.length,
                        high_risk_batches: highRisk,
                        status: 'Active'
                    };
                } catch (e) {
                    return {
                        name: wh,
                        location: wh.replace(' Warehouse', ''),
                        stored_batches: 0,
                        high_risk_batches: 0,
                        status: 'Inactive'
                    };
                }
            })
        );
        
        tbody.innerHTML = warehouseData.map(w => `
            <tr>
                <td>${w.name}</td>
                <td>${w.location}</td>
                <td>${w.stored_batches}</td>
                <td>${w.high_risk_batches}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading warehouses:', error);
        document.getElementById('warehousesTableBody').innerHTML = '<tr><td colspan="4" class="error">Failed to load warehouses</td></tr>';
    }
}

// Load Shipments Data
async function loadShipments() {
    try {
        const statusFilter = document.getElementById('shipmentStatusFilter')?.value || '';
        console.log('Loading shipments with filter:', statusFilter);
        const res = await fetch(`${API_BASE}/dashboard/shipments?status=${statusFilter}`, { headers: HEADERS });
        
        if (!res.ok) {
            const errorText = await res.text();
            console.error('Shipments API error:', res.status, errorText);
            throw new Error(`Failed to load shipments: ${res.status}`);
        }
        const data = await res.json();
        console.log('Shipments data:', data);
        
        const tbody = document.getElementById('shipmentsTableBody');
        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No shipments found</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.map(s => `
            <tr>
                <td>#${s.id}</td>
                <td>${s.source || 'N/A'}</td>
                <td>${s.destination || 'N/A'}</td>
                <td><span class="badge badge-${(s.status || 'unknown').toLowerCase().replace('_', '-')}">${(s.status || 'UNKNOWN').replace('_', ' ')}</span></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading shipments:', error);
        document.getElementById('shipmentsTableBody').innerHTML = '<tr><td colspan="4" class="error">Failed to load shipments: ' + error.message + '</td></tr>';
    }
}

function applyFilters() {
    currentFilters = {
        crop_type: document.getElementById('filterCrop').value,
        risk_level: document.getElementById('filterRisk').value,
        date_from: document.getElementById('filterDateFrom').value,
        date_to: document.getElementById('filterDateTo').value
    };
    loadBatchesTable();
}

function resetFilters() {
    document.getElementById('filterCrop').value = '';
    document.getElementById('filterRisk').value = '';
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    currentFilters = { crop_type: '', risk_level: '', date_from: '', date_to: '' };
    loadBatchesTable();
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    window.location.href = '/';
}

setInterval(() => {
    loadDashboardStats();
    loadRecentAlerts();
    loadHighRiskBatches();
}, 60000);

// Warehouse Insights Charts
let warehouseTempChart = null;
let warehouseRiskChart = null;
let warehouseTrendChart = null;

// Logistics Insights Charts
let transitFreshnessChart = null;
let shipmentStatusChart = null;
let delayFreshnessChart = null;

// Load Warehouse Insights Charts
async function loadWarehouseInsights() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/batches`, { headers: HEADERS });
        const batches = await res.json();
        
        renderWarehouseTempScatter(batches);
        renderWarehouseRiskChart(batches);
        renderWarehouseTrendChart(batches);
    } catch (error) {
        console.error('Error loading warehouse insights:', error);
    }
}

// Freshness vs Temperature Scatter Plot
function renderWarehouseTempScatter(batches) {
    const ctx = document.getElementById('warehouseTempScatterChart');
    if (!ctx) return;
    
    // Simulate temperature data (15-30°C) based on freshness score
    // Lower freshness tends to correlate with higher temperature
    const dataPoints = batches.map(b => ({
        x: 15 + Math.random() * 15 - (1 - b.freshness_score) * 10, // Simulated temp
        y: b.freshness_score,
        warehouse: b.warehouse
    }));
    
    if (warehouseTempChart) warehouseTempChart.destroy();
    
    warehouseTempChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Batches',
                data: dataPoints,
                backgroundColor: dataPoints.map(d => 
                    d.y >= 0.7 ? '#10b981' : d.y >= 0.3 ? '#f59e0b' : '#ef4444'
                ),
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: 'Temperature (°C)' },
                    min: 10,
                    max: 35
                },
                y: {
                    title: { display: true, text: 'Freshness Score' },
                    min: 0,
                    max: 1
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Risk Distribution Across Warehouses
function renderWarehouseRiskChart(batches) {
    const ctx = document.getElementById('warehouseRiskChart');
    if (!ctx) return;
    
    // Group by warehouse
    const warehouseRisk = {};
    batches.forEach(b => {
        const wh = b.warehouse || 'Unknown';
        if (!warehouseRisk[wh]) warehouseRisk[wh] = { SAFE: 0, RISK: 0, HIGH: 0 };
        warehouseRisk[wh][b.farmer_risk_status]++;
    });
    
    const warehouses = Object.keys(warehouseRisk);
    
    if (warehouseRiskChart) warehouseRiskChart.destroy();
    
    warehouseRiskChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: warehouses,
            datasets: [
                {
                    label: 'SAFE',
                    data: warehouses.map(w => warehouseRisk[w].SAFE),
                    backgroundColor: '#10b981'
                },
                {
                    label: 'RISK',
                    data: warehouses.map(w => warehouseRisk[w].RISK),
                    backgroundColor: '#f59e0b'
                },
                {
                    label: 'HIGH',
                    data: warehouses.map(w => warehouseRisk[w].HIGH),
                    backgroundColor: '#ef4444'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true, title: { display: true, text: 'Batch Count' } }
            }
        }
    });
}

// Storage Freshness Trend
function renderWarehouseTrendChart(batches) {
    const ctx = document.getElementById('warehouseTrendChart');
    if (!ctx) return;
    
    // Simulate freshness decay over time for storage
    const hours = Array.from({length: 24}, (_, i) => i);
    const avgFreshness = batches.length > 0 
        ? batches.reduce((sum, b) => sum + b.freshness_score, 0) / batches.length 
        : 0.8;
    
    // Simulate decay curve
    const decayData = hours.map(h => Math.max(0, avgFreshness * Math.exp(-h * 0.02)));
    
    if (warehouseTrendChart) warehouseTrendChart.destroy();
    
    warehouseTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours.map(h => `${h}h`),
            datasets: [{
                label: 'Average Freshness',
                data: decayData,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Storage Time' } },
                y: { min: 0, max: 1, title: { display: true, text: 'Freshness Score' } }
            }
        }
    });
}

// Load Logistics Insights Charts
async function loadLogisticsInsights() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/shipments`, { headers: HEADERS });
        const shipments = await res.json();
        const batchRes = await fetch(`${API_BASE}/dashboard/batches`, { headers: HEADERS });
        const batches = await batchRes.json();
        
        renderTransitFreshnessChart(shipments, batches);
        renderShipmentStatusChart(shipments);
        renderDelayFreshnessChart(shipments, batches);
    } catch (error) {
        console.error('Error loading logistics insights:', error);
    }
}

// Transit Freshness Trend
function renderTransitFreshnessChart(shipments, batches) {
    const ctx = document.getElementById('transitFreshnessChart');
    if (!ctx) return;
    
    // Simulate freshness decay during transit over 48 hours
    const hours = Array.from({length: 24}, (_, i) => i);
    
    // Get active shipments
    const activeShipments = shipments.filter(s => s.status === 'IN_TRANSIT').slice(0, 3);
    
    const datasets = activeShipments.map((s, idx) => {
        const colors = ['#3b82f6', '#10b981', '#f59e0b'];
        const baseFreshness = 0.7 + Math.random() * 0.3;
        const decayRate = 0.01 + Math.random() * 0.02; // Varies by shipment
        
        return {
            label: `Shipment #${s.id}`,
            data: hours.map(h => Math.max(0, baseFreshness * Math.exp(-h * decayRate))),
            borderColor: colors[idx % colors.length],
            backgroundColor: 'transparent',
            tension: 0.4
        };
    });
    
    if (transitFreshnessChart) transitFreshnessChart.destroy();
    
    transitFreshnessChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours.map(h => `${h}h`),
            datasets: datasets.length > 0 ? datasets : [{
                label: 'Simulated Transit',
                data: hours.map(h => Math.max(0, 0.85 * Math.exp(-h * 0.015))),
                borderColor: '#3b82f6',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Hours Since Dispatch' } },
                y: { min: 0, max: 1, title: { display: true, text: 'Freshness Score' } }
            }
        }
    });
}

// Shipment Status Distribution
function renderShipmentStatusChart(shipments) {
    const ctx = document.getElementById('shipmentStatusChart');
    if (!ctx) return;
    
    const statusCounts = { 'In Transit': 0, 'Delivered': 0, 'Delayed': 0 };
    shipments.forEach(s => {
        if (s.status === 'IN_TRANSIT') statusCounts['In Transit']++;
        else if (s.status === 'DELIVERED') statusCounts['Delivered']++;
        else statusCounts['Delayed']++;
    });
    
    // If no data, show simulated distribution
    if (shipments.length === 0) {
        statusCounts['In Transit'] = 3;
        statusCounts['Delivered'] = 7;
        statusCounts['Delayed'] = 2;
    }
    
    if (shipmentStatusChart) shipmentStatusChart.destroy();
    
    shipmentStatusChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(statusCounts),
            datasets: [{
                data: Object.values(statusCounts),
                backgroundColor: ['#3b82f6', '#10b981', '#ef4444']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

// Delay vs Freshness Loss
function renderDelayFreshnessChart(shipments, batches) {
    const ctx = document.getElementById('delayFreshnessChart');
    if (!ctx) return;
    
    // Simulate freshness loss for each shipment
    const shipmentData = shipments.slice(0, 8).map((s, i) => {
        const isDelayed = s.status !== 'DELIVERED' && Math.random() > 0.5;
        const freshnessLoss = isDelayed 
            ? 0.3 + Math.random() * 0.4 
            : Math.random() * 0.2;
        
        return {
            id: `#${s.id}`,
            loss: freshnessLoss,
            delayed: isDelayed
        };
    });
    
    if (delayFreshnessChart) delayFreshnessChart.destroy();
    
    delayFreshnessChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: shipmentData.map(d => d.id),
            datasets: [{
                label: 'Freshness Loss',
                data: shipmentData.map(d => d.loss),
                backgroundColor: shipmentData.map(d => d.delayed ? '#ef4444' : '#3b82f6'),
                borderColor: shipmentData.map(d => d.delayed ? '#dc2626' : '#2563eb'),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { min: 0, max: 1, title: { display: true, text: 'Freshness Loss' } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

const t=localStorage.getItem('access_token'); if(!t) location.href='/'
const userRole = (localStorage.getItem('user_role') || '').toLowerCase().trim();
const H={'Content-Type':'application/json','Authorization':'Bearer '+t};

// Navigation function for delivered shipments
function showDeliveredShipments() {
  // Remove active state from all navigation buttons
  document.querySelectorAll('.nav-action-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Add active state to delivered shipments button
  const deliveredBtn = Array.from(document.querySelectorAll('.nav-action-btn')).find(btn => 
    btn.textContent.trim().includes('Delivered Shipments')
  );
  if (deliveredBtn) {
    deliveredBtn.classList.add('active');
  }
  
  // Update page heading and subtitle
  const welcomeMessage = document.getElementById('welcomeMessage');
  if (welcomeMessage) {
    welcomeMessage.textContent = 'Delivered Shipments';
  }
  
  // Hide other sections and show only delivered shipments
  const sections = [
    { id: 'alertsSection', hide: true },
    { id: 'planRouteSection', hide: true },
    { id: 'routeOverviewSection', hide: true },
    { id: 'myShipmentsSection', hide: true },
    { id: 'inTransitSection', hide: true },
    { id: 'deliveredShipmentsSection', hide: false },
    { id: 'emergencyRequiredSection', hide: true }
  ];
  
  sections.forEach(section => {
    const element = document.getElementById(section.id);
    if (element) {
      element.style.display = section.hide ? 'none' : 'block';
    }
  });
  
  // Show "Go to Dashboard" button in delivered shipments section
  const goToDashboardBtn = document.querySelector('.go-to-dashboard-btn');
  if (goToDashboardBtn) {
    goToDashboardBtn.style.display = 'flex';
  }
  
  // Scroll to delivered shipments section
  const deliveredSection = document.getElementById('deliveredShipments');
  if (deliveredSection) {
    deliveredSection.scrollIntoView({ behavior: 'smooth' });
  }
  
  // Load delivered shipments data (this will filter and show only delivered shipments using existing logic)
  loadDeliveredShipments();
}

// Navigation function for in-transit shipments
function showInTransitShipments() {
  // Remove active state from all navigation buttons
  document.querySelectorAll('.nav-action-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Add active state to in-transit button
  const inTransitBtn = Array.from(document.querySelectorAll('.nav-action-btn')).find(btn => 
    btn.textContent.trim().includes('In-Transit')
  );
  if (inTransitBtn) {
    inTransitBtn.classList.add('active');
  }
  
  // Update page heading and subtitle
  const welcomeMessage = document.getElementById('welcomeMessage');
  if (welcomeMessage) {
    welcomeMessage.textContent = 'In-Transit Batches';
  }
  
  // Hide other sections and show only in-transit shipments
  const sections = [
    { id: 'alertsSection', hide: true },
    { id: 'planRouteSection', hide: true },
    { id: 'routeOverviewSection', hide: true },
    { id: 'myShipmentsSection', hide: true },
    { id: 'inTransitSection', hide: false },
    { id: 'deliveredShipmentsSection', hide: true },
    { id: 'emergencyRequiredSection', hide: true }
  ];
  
  sections.forEach(section => {
    const element = document.getElementById(section.id);
    if (element) {
      element.style.display = section.hide ? 'none' : 'block';
    }
  });
  
  // Show "Go to Dashboard" button in in-transit section
  const goToDashboardBtn = document.querySelector('.go-to-dashboard-btn');
  if (goToDashboardBtn) {
    goToDashboardBtn.style.display = 'flex';
  }
  
  // Scroll to in-transit section
  const inTransitSection = document.getElementById('inTransit');
  if (inTransitSection) {
    inTransitSection.scrollIntoView({ behavior: 'smooth' });
  }
  
  // Load in-transit shipments data (this will filter and show only in-transit shipments using existing logic)
  loadInTransit();
}

// Navigation function for emergency dispatch
function showEmergencyDispatch() {
  // Remove active state from all navigation buttons
  document.querySelectorAll('.nav-action-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Add active state to emergency dispatch button
  const emergencyBtn = Array.from(document.querySelectorAll('.nav-action-btn')).find(btn => 
    btn.textContent.trim().includes('Emergency Dispatch')
  );
  if (emergencyBtn) {
    emergencyBtn.classList.add('active');
  }
  
  // Update page heading and subtitle
  const welcomeMessage = document.getElementById('welcomeMessage');
  if (welcomeMessage) {
    welcomeMessage.textContent = 'Emergency Dispatch';
  }
  
  // Hide other sections and show only emergency dispatch section
  const sections = [
    { id: 'alertsSection', hide: true },
    { id: 'planRouteSection', hide: true },
    { id: 'routeOverviewSection', hide: true },
    { id: 'myShipmentsSection', hide: true },
    { id: 'inTransitSection', hide: true },
    { id: 'deliveredShipmentsSection', hide: true },
    { id: 'emergencyRequiredSection', hide: false }
  ];
  
  sections.forEach(section => {
    const element = document.getElementById(section.id);
    if (element) {
      element.style.display = section.hide ? 'none' : 'block';
    }
  });
  
  // Show "Go to Dashboard" button in emergency dispatch section
  const goToDashboardBtn = document.querySelector('.go-to-dashboard-btn');
  if (goToDashboardBtn) {
    goToDashboardBtn.style.display = 'flex';
  }
  
  // Scroll to emergency dispatch section
  const emergencySection = document.getElementById('emergencyRequired');
  if (emergencySection) {
    emergencySection.scrollIntoView({ behavior: 'smooth' });
  }
  
  // Load emergency dispatch data (this will filter and show only emergency/critical shipments using existing logic)
  loadEmergencyRequired();
}

// Function to reset to normal dashboard view
function showNormalDashboard() {
  // Remove active state from all navigation buttons
  document.querySelectorAll('.nav-action-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Reset page heading
  const welcomeMessage = document.getElementById('welcomeMessage');
  if (welcomeMessage) {
    welcomeMessage.textContent = 'Welcome, Logistics';
  }
  
  // Hide all shipment sections on main dashboard view
  const sections = [
    { id: 'alertsSection', hide: false },
    { id: 'planRouteSection', hide: false },
    { id: 'myShipmentsSection', hide: false },  // Show by default
    { id: 'inTransitSection', hide: true },  // Hide by default
    { id: 'deliveredShipmentsSection', hide: true },  // Hide by default
    { id: 'emergencyRequiredSection', hide: true }  // Hide by default
  ];
  
  sections.forEach(section => {
    const element = document.getElementById(section.id);
    if (element) {
      element.style.display = section.hide ? 'none' : 'block';
    }
  });
  
  // Hide "Go to Dashboard" button in normal view
  const goToDashboardBtn = document.querySelector('.go-to-dashboard-btn');
  if (goToDashboardBtn) {
    goToDashboardBtn.style.display = 'none';
  }
}

// Function to scroll to In-Transit section
function scrollToInTransit() {
  // Reset to normal dashboard view first
  showNormalDashboard();
  
  // Scroll to in-transit section
  const inTransitSection = document.getElementById('inTransit');
  if (inTransitSection) {
    inTransitSection.scrollIntoView({ behavior: 'smooth' });
  }
}

// Function to scroll to Emergency Dispatch section
function scrollToEmergencyDispatch() {
  // Reset to normal dashboard view first
  showNormalDashboard();
  
  // Scroll to emergency dispatch section
  const emergencySection = document.getElementById('emergencyRequired');
  if (emergencySection) {
    emergencySection.scrollIntoView({ behavior: 'smooth' });
  }
}

async function _ensureLogisticsAuth(){
  // Backend is authoritative for role; localStorage can be stale.
  let res;
  try{
    res = await fetch('/api/auth/me', { headers: H });
  }catch(e){
    return true;
  }
  if(res.status===401 || res.status===422){
    try{ localStorage.clear(); }catch(e){}
    location.href = '/';
    return false;
  }
  const j = await res.json().catch(()=>null);
  const role = String((j && j.role) || '').toLowerCase().trim();
  if(!role || role !== 'logistics'){
    try{ localStorage.clear(); }catch(e){}
    location.href = '/';
    return false;
  }
  return true;
}

async function loadDeliveredShipments(){
  const box = document.getElementById('deliveredShipments');
  if(!box) return;
  let res;
  try{
    res = await fetch('/api/logistics/my_shipments', {headers:H});
  }catch(e){
    box.textContent = '';
    return;
  }
  const rows = await res.json().catch(()=>[]);
  if(!res.ok || !Array.isArray(rows)){
    box.textContent = '';
    return;
  }
  const delivered = rows.filter(r=>String((r && r.status) || '').toUpperCase()==='DELIVERED');
  if(delivered.length===0){
    box.innerHTML = '<div>No delivered shipments yet.</div>';
    return;
  }
  box.innerHTML = '<table><tr><th>Shipment ID</th><th>Batch ID</th><th>Crop</th><th>Destination warehouse</th><th>Final freshness</th><th>Delivered at</th></tr>'+
    delivered.map(r=>{
      const tsRaw = r.delivery_time || r.delivered_at || '';
      const ts = tsRaw ? new Date(String(tsRaw)).toLocaleString() : '';
      const fr = (typeof r.current_freshness === 'number') ? r.current_freshness : parseFloat(r.current_freshness);
      const frTxt = Number.isFinite(fr) ? _fmtFreshness(fr) : '';
      return `<tr>`+
        `<td>${r.id ?? ''}</td>`+
        `<td>${r.batch_id ?? ''}</td>`+
        `<td>${r.crop ?? ''}</td>`+
        `<td>${r.destination_warehouse ?? r.destination ?? ''}</td>`+
        `<td>${frTxt}</td>`+
        `<td>${ts}</td>`+
      `</tr>`;
    }).join('') + '</table>';
}

async function loadEmergencyRequired(){
  const box = document.getElementById('emergencyRequired');
  if(!box) return;

  let res;
  try{
    res = await fetch('/api/logistics/my_shipments', {headers:H});
  }catch(e){
    box.textContent = '';
    return;
  }

  const rows = await res.json().catch(()=>[]);
  if(!res.ok || !Array.isArray(rows)){
    box.textContent = '';
    return;
  }

  const emerg = rows.filter(r=>String((r && r.status) || '').toUpperCase()==='EMERGENCY_REQUIRED');
  if(emerg.length===0){
    box.innerHTML = '<div>No emergency shipments at the moment.</div>';
    return;
  }

  box.innerHTML = '<div style="margin-bottom:6px;font-size:0.95em;opacity:0.9">Emergency dispatch required due to shelf-life exhaustion.</div>'+
    '<table><tr><th>Shipment ID</th><th>Batch ID</th><th>Crop</th><th>Destination warehouse</th><th>Status</th><th>Action</th></tr>'+
    emerg.map(r=>{
      const sid = (r && (r.id ?? r.shipment_id)) ? String(r.id ?? r.shipment_id) : '';
      return `<tr>`+
        `<td>${sid}</td>`+
        `<td>${r.batch_id ?? ''}</td>`+
        `<td>${r.crop ?? ''}</td>`+
        `<td>${r.destination_warehouse ?? r.destination ?? ''}</td>`+
        `<td>${r.status ?? ''}</td>`+
        `<td><button type="button" data-exec-emergency="${sid}">Execute Emergency Dispatch</button></td>`+
      `</tr>`;
    }).join('') + '</table>';

  box.querySelectorAll('button[data-exec-emergency]').forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const sid = String(btn.getAttribute('data-exec-emergency') || '').trim();
      const shipment_id = parseInt(sid, 10);
      if(!Number.isFinite(shipment_id)) return;
      if(!confirm('Execute emergency dispatch for this shipment?')) return;

      try{ btn.disabled = true; }catch(e){}

      let r;
      try{
        r = await fetch('/api/logistics/emergency-dispatch', {method:'POST', headers:H, body: JSON.stringify({ shipment_id })});
      }catch(e){
        alert('Backend not reachable. Start backend and refresh.');
        try{ btn.disabled = false; }catch(_e){}
        return;
      }

      const jj = await r.json().catch(()=>null);
      if(!r.ok){
        const m = jj && (jj.msg || jj.message || jj.error) ? String(jj.msg || jj.message || jj.error) : `Request failed (${r.status})`;
        alert(m);
        try{ btn.disabled = false; }catch(_e){}
        return;
      }

      const okMsg = jj && jj.message ? String(jj.message) : 'Emergency dispatch executed.';
      alert(okMsg);

      const proceed = confirm('Shipment routed for salvage successfully. Click OK to finalize.');
      if(proceed){
        let r2;
        try{
          r2 = await fetch('/api/logistics/confirm-salvage', {method:'POST', headers:H, body: JSON.stringify({ shipment_id })});
        }catch(e){
          alert('Backend not reachable. Start backend and refresh.');
          try{ btn.disabled = false; }catch(_e){}
          return;
        }
        const jj2 = await r2.json().catch(()=>null);
        if(!r2.ok){
          const m2 = jj2 && (jj2.msg || jj2.message || jj2.error) ? String(jj2.msg || jj2.message || jj2.error) : `Request failed (${r2.status})`;
          alert(m2);
          try{ btn.disabled = false; }catch(_e){}
          return;
        }
        alert('Finalized successfully.');
      }

      try{ await loadEmergencyRequired(); }catch(e){}
      try{ await loadDeliveredShipments(); }catch(e){}
      try{ await loadInTransit(); }catch(e){}
    });
  });
}

let _pendingDelivery = null;
function _openConfirmDeliveryModal(shipmentId, triggerBtn){
  const modal = document.getElementById('confirmDeliveryModal');
  const msg = document.getElementById('confirmDeliveryMsg');
  const btnOk = document.getElementById('btnConfirmDelivery');
  const btnX = document.getElementById('btnCancelDelivery');
  const btnCancel = document.getElementById('btnCancelDelivery2');
  if(!modal || !btnOk) return false;
  _pendingDelivery = { shipmentId, triggerBtn };
  if(msg) msg.textContent = `Shipment ID: ${shipmentId}`;
  try{ modal.style.display = 'flex'; }catch(e){}

  const close = ()=>{
    try{ modal.style.display = 'none'; }catch(e){}
    try{
      if(_pendingDelivery && _pendingDelivery.triggerBtn){
        _pendingDelivery.triggerBtn.disabled = false;
      }
    }catch(e){}
    _pendingDelivery = null;
  };

  const onCancel = ()=> close();
  try{ if(btnX) btnX.onclick = onCancel; }catch(e){}
  try{ if(btnCancel) btnCancel.onclick = onCancel; }catch(e){}

  try{
    btnOk.onclick = async ()=>{
      if(!_pendingDelivery) return;
      try{ btnOk.disabled = true; }catch(e){}
      try{ if(msg) msg.textContent = 'Confirming delivery...'; }catch(e){}
      try{
        const payload = { shipment_id: _pendingDelivery.shipmentId, status: 'DELIVERED' };
        const r = await fetch('/api/logistics/status', {method:'POST', headers:H, body: JSON.stringify(payload)});
        const jj = await r.json().catch(()=>({}));
        if(!r.ok){
          const m = (jj && (jj.msg || jj.message)) ? String(jj.msg || jj.message) : 'Unable to confirm delivery.';
          alert(m);
          try{ btnOk.disabled = false; }catch(e){}
          return;
        }
        alert('Delivery confirmed. Shipment successfully handed over to warehouse.');
        await loadMyShipments();
        await loadInTransit();
        await loadWarehouseAlerts();
        try{ await loadDeliveredShipments(); }catch(e){}
        const redirectUrl = (jj && jj.redirect_url) ? String(jj.redirect_url) : '';
        const sid = (jj && jj.shipment && (jj.shipment.id ?? jj.shipment.shipment_id)) ? (jj.shipment.id ?? jj.shipment.shipment_id) : _pendingDelivery.shipmentId;
        const url = redirectUrl || (sid ? `/warehouse?shipment_id=${encodeURIComponent(String(sid))}` : '/warehouse');
        close();
        setTimeout(()=>{
          try{ window.location.assign(url); }catch(e){ window.location.href = url; }
        }, 50);
      }catch(e){
        alert('Unable to confirm delivery. Please refresh.');
        try{ btnOk.disabled = false; }catch(_e){}
      }
    };
  }catch(e){}

  return true;
}

function _fmtHours(x){
  const n = (typeof x === 'number') ? x : parseFloat(x);
  if(!Number.isFinite(n)) return '';
  return `${n.toFixed(1)} hrs`;
}

function _autofillPlanFromShipment(s){
  const planForm = document.getElementById('planForm');
  if(!planForm) return;
  const batchEl = planForm.querySelector('input[name="batch_id"]');
  const pickupEl = document.getElementById('startLocation');
  const destEl = planForm.querySelector('input[name="destination"]');
  const modeEl = planForm.querySelector('select[name="mode"]');
  if(!batchEl || !pickupEl || !destEl || !modeEl) return;

  try{
    const sid = (s && (s.id ?? s.shipment_id)) ? parseInt(String(s.id ?? s.shipment_id), 10) : NaN;
    window.autoFilledShipmentId = Number.isFinite(sid) ? sid : null;
  }catch(e){ window.autoFilledShipmentId = null; }

  try{ batchEl.value = (s && s.batch_id != null) ? String(s.batch_id) : ''; }catch(e){}
  try{ pickupEl.value = (s && s.pickup_location != null) ? String(s.pickup_location) : ''; }catch(e){}
  try{
    let d0 = (s && s.destination != null) ? String(s.destination) : '';
    if(d0){
      d0 = d0.replace(/\s+warehouse\s*$/i, '').trim();
    }
    destEl.value = d0;
  }catch(e){}
  try{ modeEl.value = (s && s.mode) ? String(s.mode).toLowerCase() : 'road'; }catch(e){ modeEl.value='road'; }

  try{ batchEl.readOnly = true; }catch(e){}
  try{ destEl.readOnly = true; }catch(e){}
  try{ pickupEl.readOnly = true; }catch(e){}
  try{ modeEl.disabled = true; }catch(e){}
}

async function _handleFindRoutes(){
  const planForm = document.getElementById('planForm');
  if(!planForm) return;
  const planMsg = document.getElementById('planMsg');
  const routeEl = planForm.querySelector('input[name="route"]');
  const etaEl = planForm.querySelector('input[name="eta_hours"]');
  const modeEl = planForm.querySelector('select[name="mode"]');
  const btn = document.getElementById('findRoutesBtn');
  if(!routeEl || !etaEl || !modeEl || !btn) return;

  const shipment_id = (typeof window.autoFilledShipmentId === 'number') ? window.autoFilledShipmentId : null;
  if(!Number.isFinite(shipment_id) || shipment_id <= 0){
    if(planMsg) planMsg.textContent = 'No active shipment available for route finding.';
    return;
  }

  const mode = (modeEl.value || 'road').toLowerCase() || 'road';
  try{
    if(btn.dataset.loading === '1') return;
    btn.dataset.loading = '1';
    btn.disabled = true;
    if(planMsg) planMsg.textContent = 'Finding routes...';
  }catch(e){}

  let res;
  try{
    res = await fetch('/api/logistics/find_routes', { method:'POST', headers:H, body: JSON.stringify({ shipment_id, mode }) });
  }catch(e){
    if(planMsg) planMsg.textContent = 'Backend not reachable. Start backend and refresh.';
    try{ btn.dataset.loading = '0'; btn.disabled = false; }catch(_e){}
    return;
  }

  if(res.status===401 || res.status===422){
    try{ localStorage.removeItem('access_token'); localStorage.removeItem('token'); }catch(e){}
    alert('Session expired. Please login again.');
    location.href = '/';
    return;
  }
  if(res.status===403){
    if(planMsg) planMsg.textContent = 'Forbidden: login as a Logistics user to access route planning.';
    try{ btn.dataset.loading = '0'; btn.disabled = false; }catch(_e){}
    return;
  }

  const j = await res.json().catch(()=>null);
  if(!res.ok || !j){
    const msg = j && (j.msg || j.error || j.message) ? String(j.msg || j.error || j.message) : `Request failed (${res.status})`;
    if(planMsg) planMsg.textContent = msg;
    try{ btn.dataset.loading = '0'; btn.disabled = false; }catch(_e){}
    return;
  }

  if(String(j.msg||'') === 'local_transfer'){
    if(planMsg) planMsg.textContent = String(j.notice || 'Local transfer (0 km) – direct dispatch available');
    try{
      const tblBox = document.getElementById('routeOptionsTable');
      if(tblBox) tblBox.innerHTML = '';
    }catch(e){}
    try{ btn.dataset.loading = '0'; btn.disabled = false; }catch(e){}
    return;
  }

  const options = Array.isArray(j.options) ? j.options : [];
  if(!options.length){
    if(planMsg) planMsg.textContent = String(j.notice || 'No route options returned.');
    try{ btn.dataset.loading = '0'; btn.disabled = false; }catch(_e){}
    return;
  }

  const best = options[0] || {};
  try{ routeEl.value = String(best.route || ''); }catch(e){}
  try{ etaEl.value = (typeof best.eta_hours !== 'undefined' && best.eta_hours !== null) ? String(best.eta_hours) : ''; }catch(e){}

  try{
    const ov = document.getElementById('routeOverview');
    if(ov){
      const clRaw = String(best.congestion_level || '').trim().toUpperCase();
      const traffic = (clRaw === 'LOW') ? 'Low congestion' : (clRaw === 'MEDIUM' ? 'Moderate congestion' : (clRaw === 'HIGH' ? 'Heavy congestion' : 'Unknown'));
      let distTxt = (best.distance_km ?? '');
      try{
        const dn = (typeof best.distance_km === 'number') ? best.distance_km : parseFloat(best.distance_km);
        if(Number.isFinite(dn) && dn <= 0) distTxt = '0 km (Same city)';
      }catch(e){}
      const pf = (typeof best.predicted_arrival_freshness === 'number') ? best.predicted_arrival_freshness : parseFloat(best.predicted_arrival_freshness);
      const pfTxt = Number.isFinite(pf) ? _fmtFreshness(pf) : '';
      const risk = String(best.risk_level || '').trim();
      ov.innerHTML = '<div><strong>Route:</strong> ' + (best.route||'') + '</div>'+
        '<div><strong>ETA (h):</strong> ' + (best.eta_hours ?? '') + '</div>'+
        '<div><strong>Distance (km):</strong> ' + distTxt + '</div>'+
        '<div><strong>Traffic:</strong> ' + traffic + '</div>'+
        '<div><strong>Arrival Freshness:</strong> ' + pfTxt + '</div>'+
        '<div><strong>Risk:</strong> ' + risk + '</div>';
    }
  }catch(e){}

  try{
    const tblBox = document.getElementById('routeOptionsTable');
    if(tblBox){
      const decayK = (typeof j.decay_rate_per_hour === 'number') ? j.decay_rate_per_hour : parseFloat(j.decay_rate_per_hour);
      const k = Number.isFinite(decayK) ? Math.max(0, decayK) : 0;
      const curF0 = (typeof j.current_freshness === 'number') ? j.current_freshness : parseFloat(j.current_freshness);
      const curF = Number.isFinite(curF0) ? Math.max(0, Math.min(1, curF0)) : 0;

      const _clamp01 = (x)=>{
        const n = (typeof x === 'number') ? x : parseFloat(x);
        if(!Number.isFinite(n)) return 0;
        return Math.max(0, Math.min(1, n));
      };

      const _pct = (f)=>{
        const c = _clamp01(f);
        return `${Math.round(c*100)}%`;
      };

      const _riskFromPct = (pct)=>{
        const n = (typeof pct === 'number') ? pct : parseFloat(pct);
        if(!Number.isFinite(n)) return 'SAFE';
        if(n >= 70) return 'SAFE';
        if(n >= 50) return 'MEDIUM';
        return 'HIGH';
      };

      const _riskFromFreshness = (f)=> _riskFromPct(Math.round(_clamp01(f) * 100));

      // Deterministic what-if: follow the user-specified linear formulation in the modal.
      const _predictFreshnessLinear = ({ etaH, kPerH, currentF })=>{
        const eta = (typeof etaH === 'number') ? etaH : parseFloat(etaH);
        const kk = (typeof kPerH === 'number') ? kPerH : parseFloat(kPerH);
        const cf = _clamp01(currentF);
        if(!Number.isFinite(eta) || eta < 0) return cf;
        if(!Number.isFinite(kk) || kk <= 0) return cf;
        return _clamp01(cf - (kk * eta));
      };

      const _ensureSimModal = ()=>{
        let modal = document.getElementById('dtSimModal');
        if(modal) return modal;
        modal = document.createElement('div');
        modal.id = 'dtSimModal';
        modal.style.display = 'none';
        modal.style.position = 'fixed';
        modal.style.inset = '0';
        modal.style.background = 'rgba(0,0,0,0.55)';
        modal.style.zIndex = '10050';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.innerHTML =
          '<div style="background:#fff;border-radius:12px;max-width:820px;width:94%;max-height:86vh;overflow:auto;padding:16px 16px 12px 16px;box-shadow:0 12px 40px rgba(0,0,0,0.30);">'+
            '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;position:sticky;top:0;background:#fff;padding-bottom:10px;">'+
              '<h3 style="margin:0">Logistics Digital Twin – What-if Simulation</h3>'+
              '<button type="button" id="dtSimClose" style="border:none;background:transparent;font-size:20px;line-height:20px;cursor:pointer">×</button>'+
            '</div>'+
            '<div id="dtSimBody" style="font-size:0.95em;line-height:1.45"></div>'+
          '</div>';
        document.body.appendChild(modal);
        try{
          modal.addEventListener('click', (e)=>{
            if(e && e.target === modal){ modal.style.display = 'none'; }
          });
        }catch(e){}
        try{
          const x = modal.querySelector('#dtSimClose');
          if(x){ x.addEventListener('click', ()=>{ modal.style.display = 'none'; }); }
        }catch(e){}
        return modal;
      };

      const _renderScenarioLine = (label, f)=>{
        const pct = Math.round(_clamp01(f) * 100);
        const risk = _riskFromPct(pct);
        return { label, pct, risk };
      };

      const _riskBadgeHtml = (risk)=>{
        const r = String(risk||'').toUpperCase();
        const bg = (r === 'SAFE') ? '#16a34a' : (r === 'MEDIUM' ? '#f59e0b' : (r === 'HIGH' ? '#ef4444' : '#6b7280'));
        const txt = r || '';
        return txt ? `<span style="display:inline-block;padding:3px 10px;border-radius:999px;color:#fff;background:${bg};font-weight:700;font-size:12px;letter-spacing:0.2px">${txt}</span>` : '';
      };

      const _cardStyle = 'border:1px solid #1f2937;border-radius:12px;padding:12px 12px;background:#0b1220;color:#f9fafb;';
      const _cardTitleStyle = 'font-weight:800;margin:0 0 10px 0;font-size:14px;color:#f9fafb;';
      const _kvRow = (k0, v0)=>`<div style="display:flex;justify-content:space-between;gap:12px;margin:4px 0;"><div style="opacity:0.9">${k0}</div><div style="font-weight:700;text-align:right">${v0}</div></div>`;

      const _scenarioTable = (rows)=>{
        const hdr = '<tr>'+
          '<th style="text-align:left;padding:8px 10px;border-bottom:1px solid #334155;color:#e5e7eb;font-size:12px">Condition</th>'+
          '<th style="text-align:right;padding:8px 10px;border-bottom:1px solid #334155;color:#e5e7eb;font-size:12px">Freshness</th>'+
          '<th style="text-align:right;padding:8px 10px;border-bottom:1px solid #334155;color:#e5e7eb;font-size:12px">Risk</th>'+
        '</tr>';
        const body = (rows||[]).map(r=>{
          return '<tr>'+
            `<td style="padding:8px 10px;border-bottom:1px solid #111827;color:#f9fafb">${r.label}</td>`+
            `<td style="padding:8px 10px;border-bottom:1px solid #111827;text-align:right;font-weight:800;color:#f9fafb">${r.pct}%</td>`+
            `<td style="padding:8px 10px;border-bottom:1px solid #111827;text-align:right">${_riskBadgeHtml(r.risk)}</td>`+
          '</tr>';
        }).join('');
        return `<table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:10px;overflow:hidden">${hdr}${body}</table>`;
      };

      const _openSimulationModal = (opt)=>{
        const modal = _ensureSimModal();
        const body = modal.querySelector('#dtSimBody');
        if(!body) return;

        const eta0 = (typeof opt.eta_hours === 'number') ? opt.eta_hours : parseFloat(opt.eta_hours);
        const eta = Number.isFinite(eta0) ? Math.max(0, eta0) : 0;
        const basePred = (typeof opt.predicted_arrival_freshness === 'number') ? opt.predicted_arrival_freshness : parseFloat(opt.predicted_arrival_freshness);
        const baseF = _clamp01(Number.isFinite(basePred) ? basePred : 0);
        const baseRisk = _riskFromFreshness(baseF);

        // Scenario A: Delay Spike
        const a2 = _predictFreshnessLinear({ etaH: eta + 2, kPerH: k, currentF: curF });
        const a4 = _predictFreshnessLinear({ etaH: eta + 4, kPerH: k, currentF: curF });

        // Scenario B: Traffic Congestion Increase
        const b20 = _predictFreshnessLinear({ etaH: eta * 1.2, kPerH: k, currentF: curF });
        const b40 = _predictFreshnessLinear({ etaH: eta * 1.4, kPerH: k, currentF: curF });

        // Scenario C: Temperature Spike During Transit
        // Deterministic proportional factor (no new APIs): +3°C => +15% decay, +6°C => +30% decay
        const k3 = k * 1.15;
        const k6 = k * 1.30;
        const c3 = _predictFreshnessLinear({ etaH: eta, kPerH: k3, currentF: curF });
        const c6 = _predictFreshnessLinear({ etaH: eta, kPerH: k6, currentF: curF });

        // Scenario D: Combined Worst Case
        const dEta = (eta + 3) * 1.3;
        const dK = k * 1.25;
        const d = _predictFreshnessLinear({ etaH: dEta, kPerH: dK, currentF: curF });

        const worst = Math.min(a4, b40, c6, d);
        const worstPct = Math.round(_clamp01(worst) * 100);
        const worstRisk = _riskFromPct(worstPct);

        const stability = (worstRisk === 'HIGH') ? 'Route highly sensitive to delay and temperature spikes.' : 'Route is stable under moderate disruption.';
        const dispatch = (worstRisk === 'HIGH' || baseRisk === 'HIGH') ? 'Immediate dispatch recommended.' : 'Consider alternate route if disruption indicators rise.';

        const aRows = [
          _renderScenarioLine('+2h delay', a2),
          _renderScenarioLine('+4h delay', a4),
        ];
        const bRows = [
          _renderScenarioLine('+20% traffic delay', b20),
          _renderScenarioLine('+40% traffic delay', b40),
        ];
        const cRows = [
          _renderScenarioLine('+3°C temperature rise', c3),
          _renderScenarioLine('+6°C temperature rise', c6),
        ];
        const dRows = [
          _renderScenarioLine('+3h delay, +30% traffic, +5°C rise', d),
        ];

        const routeName = (opt.route_corridor || opt.route || '').toString();
        const distanceTxt = (opt.distance_km ?? '—');
        const riskTxt = String(opt.risk_level || baseRisk || '').toString();

        const routeSummaryCard =
          `<div style="${_cardStyle}margin-bottom:12px;">`+
            `<div style="${_cardTitleStyle}">Route Summary</div>`+
            _kvRow('Route', routeName) +
            _kvRow('Distance', `${distanceTxt} km`) +
            _kvRow('ETA', `${eta.toFixed(2)} h`) +
            _kvRow('Predicted Arrival Freshness', _pct(baseF)) +
            _kvRow('Current Risk', _riskBadgeHtml(riskTxt)) +
          `</div>`;

        const scenarioCard = (title, tblHtml, extraStyle='')=>{
          return `<div style="${_cardStyle}${extraStyle}margin-bottom:12px;">`+
            `<div style="${_cardTitleStyle}">${title}</div>`+
            `${tblHtml}`+
          `</div>`;
        };

        const warnStyle = 'border:1px solid #ef4444;box-shadow:0 0 0 1px rgba(239,68,68,0.25) inset;';

        const advisoryCard =
          `<div style="border:1px solid #0ea5e9;border-radius:12px;padding:12px 12px;background:#06253a;color:#e6f6ff;margin-top:6px;">`+
            `<div style="font-weight:900;margin:0 0 8px 0;">Advisory</div>`+
            `<div style="margin:6px 0;"><strong>Stability Assessment:</strong> ${stability}</div>`+
            `<div style="margin:6px 0;"><strong>Dispatch Recommendation:</strong> ${dispatch}</div>`+
          `</div>`;

        body.innerHTML =
          routeSummaryCard +
          scenarioCard('Scenario A – Delay Impact', _scenarioTable(aRows)) +
          scenarioCard('Scenario B – Traffic Impact', _scenarioTable(bRows)) +
          scenarioCard('Scenario C – Temperature Impact', _scenarioTable(cRows)) +
          scenarioCard('Scenario D – Combined Worst Case', _scenarioTable(dRows), warnStyle) +
          advisoryCard;

        modal.style.display = 'flex';
      };

      const rows = options.map((o)=>{
        let dist = (o.distance_km ?? '');
        try{
          const dn = (typeof o.distance_km === 'number') ? o.distance_km : parseFloat(o.distance_km);
          if(Number.isFinite(dn) && dn <= 0) dist = '0 km (Same city)';
        }catch(e){}
        const eta = (typeof o.eta_hours === 'number') ? o.eta_hours : parseFloat(o.eta_hours);
        const etaTxt = Number.isFinite(eta) ? String(eta) : '';
        const pf = (typeof o.predicted_arrival_freshness === 'number') ? o.predicted_arrival_freshness : parseFloat(o.predicted_arrival_freshness);
        const pfTxt = Number.isFinite(pf) ? _fmtFreshness(pf) : '';
        const risk = String(o.risk_level || '').trim();
        const corridor = String(o.route_corridor || o.route || '').trim();
        const rid = String(o.route_option_id || '').trim();
        const reco = String(o.recommendation || '').trim() || '—';
        const route = String(o.route || '').trim();
        const alertsArr = Array.isArray(o.alerts) ? o.alerts : [];
        const alertsTxt = alertsArr.map(a=>String(a||'').trim()).filter(Boolean).join('; ') || '—';
        
        // Format route with arrows and highway info
        const routeParts = route.split(' ');
        const mainRoute = routeParts[0] || '';
        const highwayInfo = routeParts.slice(1).join(' ');
        const formattedRoute = mainRoute.replace(/→/g, ' → ') + (highwayInfo ? `<div class="route-highway">via ${highwayInfo}</div>` : '');
        
        return `<tr>`+
          `<td>${rid}</td>`+
          `<td><div class="route-path">${formattedRoute}</div></td>`+
          `<td>${dist}</td>`+
          `<td>${etaTxt}</td>`+
          `<td>${pfTxt}</td>`+
          `<td>${risk}</td>`+
          `<td>${alertsTxt}</td>`+
          `<td>${reco}</td>`+
          `<td>`+
            `<div class="route-action-container">`+
              `<button type="button" class="route-action-btn" data-simulate-route="1" data-route-id="${encodeURIComponent(rid)}">Simulate</button>`+
              `<button type="button" class="route-action-btn" data-apply-route="1" data-route="${encodeURIComponent(route)}" data-eta="${encodeURIComponent(etaTxt)}">Apply</button>`+
            `</div>`+
          `</td>`+
          '</tr>';
      }).join('');

      tblBox.innerHTML = '<table>'+
        '<tr><th>Route ID</th><th>Route via</th><th>Distance (km)</th><th>ETA (h)</th><th>Arrival Freshness (%)</th><th>Risk</th><th>Alerts</th><th>Recommendation</th><th>Action</th></tr>'+
        rows +
        '</table>';

      tblBox.querySelectorAll('button[data-simulate-route="1"]').forEach(b=>{
        b.addEventListener('click', ()=>{
          try{
            const rid0 = decodeURIComponent(b.getAttribute('data-route-id')||'');
            const opt = options.find(x=>String((x && x.route_option_id) || '').trim() === rid0) || (options[0] || {});
            _openSimulationModal(opt);
          }catch(e){}
        });
      });

      tblBox.querySelectorAll('button[data-apply-route="1"]').forEach(b=>{
        b.addEventListener('click', async ()=>{
          const r0 = decodeURIComponent(b.getAttribute('data-route')||'');
          const e0 = decodeURIComponent(b.getAttribute('data-eta')||'');
          if(!r0) return;
          try{
            b.disabled = true;
            if(planMsg) planMsg.textContent = 'Applying selected route...';
            const r2 = await fetch('/api/logistics/apply_route_option', {method:'POST', headers:H, body: JSON.stringify({ shipment_id, route: r0, eta_hours: e0, mode: 'road' })});
            const j2 = await r2.json().catch(()=>null);
            if(!r2.ok || !j2){
              const msg2 = j2 && (j2.msg || j2.error || j2.message) ? String(j2.msg || j2.error || j2.message) : `Request failed (${r2.status})`;
              if(planMsg) planMsg.textContent = msg2;
              b.disabled = false;
              return;
            }
            try{ routeEl.value = r0; }catch(e){}
            try{ etaEl.value = String(j2.eta_hours ?? e0 ?? ''); }catch(e){}
            if(planMsg) planMsg.textContent = 'Route applied. ETA updated.';
            try{ await loadMyShipments(); }catch(e){}
            try{ await loadInTransit(); }catch(e){}
          }catch(e){
            if(planMsg) planMsg.textContent = 'Unable to apply route. Please refresh.';
          }finally{
            try{ b.disabled = false; }catch(e){}
          }
        });
      });
    }
  }catch(e){}

  if(planMsg) planMsg.textContent = 'Routes found. Select a route option to apply.';
  try{ btn.dataset.loading = '0'; btn.disabled = false; }catch(e){}

  try{ await loadMyShipments(); }catch(e){}
  try{ await loadInTransit(); }catch(e){}
}
async function loadWarehouseAlerts(){
  const box = document.getElementById('warehouseAlerts');
  if(!box) return;
  const res = await fetch('/api/logistics/warehouse_alerts', {headers:H});
  const rows = await res.json().catch(()=>[]);
  if(!res.ok || !Array.isArray(rows)){
    box.textContent = 'Unable to load data. Please refresh.';
    return;
  }
  if(rows.length===0){
    box.innerHTML = '<div>No warehouse alerts</div>';
    return;
  }
  box.innerHTML = rows.map(a=>{
    const ts = a.detected_at ? new Date(a.detected_at).toLocaleString() : '';
    const bid = (a.batch_id !== null && typeof a.batch_id !== 'undefined') ? a.batch_id : 'N/A';
    const sev = String(a.severity||'').toUpperCase();
    const wh = a.warehouse || a.region || '';
    const msg = a.message || '';
    const act = a.recommended_action || '';
    const color = sev === 'HIGH' ? '#ef4444' : (sev === 'MEDIUM' ? '#f59e0b' : '#6b7280');
    return `<div style="border:1px solid #1f2937;padding:8px;border-radius:8px;margin:8px 0">`
      + `<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">`
      + `<span style="background:${color};color:#fff;padding:2px 8px;border-radius:999px;font-size:12px">${sev}</span>`
      + `<strong>Batch ${bid}</strong>`
      + `<span>${wh}</span>`
      + `<span style="opacity:0.85">${ts}</span>`
      + `</div>`
      + `<div style="margin-top:6px">${msg}</div>`
      + (act? `<div style="margin-top:6px"><strong>Action:</strong> ${act}</div>` : '')
      + `</div>`;
  }).join('');
}

if(document.getElementById('warehouseAlerts')){
  loadWarehouseAlerts();
  setInterval(loadWarehouseAlerts, 15000);
}

const planForm=document.getElementById('planForm');

function _q(sel){ return document.querySelector(sel); }

function _setReadonlyGrey(el){
  if(!el) return;
  el.readOnly = true;
  el.disabled = true;
  el.style.opacity = '0.75';
  el.style.background = '#111827';
  el.style.color = '#e5e7eb';
}

async function refreshBatchContext(){
  const batchEl = _q('#planForm input[name="batch_id"]');
  const startEl = document.getElementById('startLocation');
  if(!batchEl || !startEl) return;
  const bid = parseInt(batchEl.value||'');
  if(!Number.isFinite(bid)){
    return;
  }
  const res = await fetch(`/api/logistics/batch_context/${bid}`, { headers: H });
  const j = await res.json().catch(()=>null);
  if(!res.ok || !j){
    return;
  }
  try{ window.lastBatchContext = j; }catch(e){}
}

async function refreshEta(){
  const batchEl = _q('#planForm input[name="batch_id"]');
  const destEl = _q('#planForm input[name="destination"]');
  const modeEl = _q('#planForm select[name="mode"]');
  const etaEl = _q('#planForm input[name="eta_hours"]');
  if(!batchEl || !destEl || !modeEl || !etaEl) return;

  _setReadonlyGrey(etaEl);

  const bid = parseInt(batchEl.value||'');
  const destination = String(destEl.value||'').trim();
  const mode = String(modeEl.value||'road').trim().toLowerCase() || 'road';
  if(!Number.isFinite(bid) || !destination){
    etaEl.value = '';
    return;
  }

  const res = await fetch('/api/logistics/eta', { method:'POST', headers:H, body: JSON.stringify({ batch_id: bid, destination, mode }) });
  const j = await res.json().catch(()=>null);
  if(!res.ok || !j){
    etaEl.value = '';
    return;
  }
  if(typeof j.eta_hours !== 'undefined' && j.eta_hours !== null){
    etaEl.value = j.eta_hours;
  }
}

function setRoutePlanningEnabled(enabled){
  const planMsg = document.getElementById('planMsg');
  if(userRole !== 'logistics') return;

  const planForm = document.getElementById('planForm');
  if(!planForm) return;

  const els = [
    _q('#planForm input[name="batch_id"]'),
    _q('#planForm input[name="destination"]'),
    _q('#planForm select[name="mode"]'),
    _q('#planForm input[name="route"]'),
    document.getElementById('openMapsBtn'),
    document.getElementById('suggestRoutesBtn'),
    document.getElementById('suggestedRoutes'),
    document.getElementById('findRoutesBtn'),
    document.getElementById('routeMode'),
    document.getElementById('routeOptions'),
    _q('#planForm button[type="submit"]'),
  ].filter(Boolean);

  if(enabled){
    els.forEach(el=>{ try{ el.disabled = false; el.readOnly = false; el.style.opacity = '1'; }catch(e){} });
    const startEl = document.getElementById('startLocation');
    if(startEl){ _setReadonlyGrey(startEl); }
    const etaEl = _q('#planForm input[name="eta_hours"]');
    if(etaEl){ _setReadonlyGrey(etaEl); }
    if(planMsg && planMsg.textContent === 'Route planning becomes available after pickup confirmation.'){
      planMsg.textContent = '';
    }
  }else{
    els.forEach(el=>{ try{ el.disabled = true; el.style.opacity = '0.6'; }catch(e){} });
    if(planMsg){ planMsg.textContent = 'Route planning becomes available after pickup confirmation.'; }
  }
}

planForm.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const data = Object.fromEntries(new FormData(planForm).entries());
  data.batch_id = parseInt(data.batch_id);
  data.destination = (data.destination||'').toString().trim();
  if(!data.destination) delete data.destination;
  data.mode = (data.mode||'').toString().trim().toLowerCase();
  if(!data.mode) delete data.mode;
  delete data.origin;
  delete data.eta_hours;

   // Bind planning explicitly to the selected shipment, if any
   try{
     const sid = (typeof window.autoFilledShipmentId === 'number') ? window.autoFilledShipmentId : window.selectedShipmentId;
     if(Number.isFinite(sid) && sid > 0){
       data.shipment_id = sid;
     }
   }catch(e){}

  await refreshBatchContext();
  await refreshEta();
  const res = await fetch('/api/logistics/plan', {method:'POST', headers:H, body: JSON.stringify(data)});
  const planMsg = document.getElementById('planMsg');
  planMsg.textContent = res.ok? 'Planned.' : 'Planning failed';
  if(res.ok){
    const j = await res.json().catch(()=>null);
    const etaEl = document.querySelector('#planForm input[name="eta_hours"]');
    if(j && etaEl && typeof j.eta_hours !== 'undefined') etaEl.value = j.eta_hours;
    await loadMyShipments();
    await loadInTransit();
    planMsg.textContent += ' | The logistics dashboard auto-derives route parameters from warehouse data, recalculates freshness dynamically, and uses GenAI exclusively for decision support.';
  }
});

// Find Routes button (persist route metadata; does NOT change status)
try{
  const fr = document.getElementById('findRoutesBtn');
  if(fr){ fr.addEventListener('click', _handleFindRoutes); }
}catch(e){}


function _fmtFreshness(x){
  const n0 = (typeof x === 'number') ? x : parseFloat(x);
  if(!Number.isFinite(n0)) return '-';
  const n = Math.max(0, Math.min(1, n0));
  const pct = Math.round(n * 100);
  return `${pct}% (Predicted on arrival)`;
}

function _riskFromFreshness(f){
  const n = (typeof f === 'number') ? f : parseFloat(f);
  if(!Number.isFinite(n)) return '';
  if(n >= 0.6) return 'SAFE';
  if(n >= 0.3) return 'RISK';
  return 'HIGH SPOILAGE RISK';
}

function _riskBadgeHtml(risk){
  const r = String(risk||'').toUpperCase();
  const bg = (r === 'SAFE') ? '#16a34a' : (r === 'RISK' ? '#f59e0b' : (r ? '#ef4444' : '#6b7280'));
  const txt = risk ? String(risk) : '';
  return txt ? `<span style="display:inline-block;padding:2px 8px;border-radius:999px;color:#fff;background:${bg};font-size:12px">${txt}</span>` : '';
}

function _severityLabelFromAlert(a){
  const sevRaw = String((a && (a.alertlevel || a.severity || a.level)) || '').trim().toLowerCase();
  if(sevRaw === 'extreme' || sevRaw === 'severe' || sevRaw === 'high' || sevRaw === 'red') return 'High';
  if(sevRaw === 'moderate' || sevRaw === 'orange' || sevRaw === 'medium') return 'Moderate';
  if(sevRaw === 'minor' || sevRaw === 'yellow' || sevRaw === 'low') return 'Minor';
  return 'Info';
}

function _decisionFromAlerts(apiAlerts){
  const alerts = Array.isArray(apiAlerts) ? apiAlerts : [];
  const rank = {'info':0,'minor':1,'moderate':2,'high':3};
  let top = 0;
  for(const a of alerts){
    const lab = _severityLabelFromAlert(a).toLowerCase();
    top = Math.max(top, rank[lab] ?? 0);
  }
  if(top >= 3) return 'Avoid if possible';
  if(top >= 2) return 'Proceed with caution';
  return 'Proceed';
}

function _actionLinesFromAlerts(apiAlerts, mode){
  const m = String(mode||'').toLowerCase();
  const alerts = Array.isArray(apiAlerts) ? apiAlerts : [];
  const titles = alerts.map(a => String((a && (a.title || a.details || a.message || a.eventtype)) || '')).join(' ').toLowerCase();
  const sevHigh = alerts.some(a => _severityLabelFromAlert(a) === 'High');
  const sevMod = alerts.some(a => _severityLabelFromAlert(a) === 'Moderate');

  const out = [];
  if(titles.includes('visibility') || titles.includes('fog') || titles.includes('mist') || titles.includes('haze')){
    out.push('Set reduced-speed and headway rules; enforce headlight/reflective checks before departure');
    out.push('Schedule departure away from low-visibility windows; confirm driver rest plan for delays');
  }
  if(titles.includes('rain') || titles.includes('storm') || titles.includes('flood') || titles.includes('thunder')){
    out.push('Verify road closures and safe stopping points; pre-brief detours without changing planned ETA');
    out.push('Increase inspection frequency at stops (tarpaulin, seals, pallet stability) to prevent water ingress');
  }
  if(titles.includes('wind') || titles.includes('gust')){
    out.push('Secure load with additional straps and corner protectors; verify axle weight distribution');
  }
  if(titles.includes('heat') || titles.includes('hot') || titles.includes('temperature')){
    out.push('Confirm reefer setpoint and pre-cool; verify generator fuel and door-open discipline at handoffs');
  }

  if(m === 'sea' || m === 'port'){
    out.push('Confirm terminal cut-off and gate slot; pre-file documents to avoid port dwell');
  }else if(m === 'rail'){
    out.push('Confirm train slot and yard handoff window; prepare contingency for missed connection');
  }else{
    out.push('Confirm driver assignment, fuel plan, and toll/permit readiness before dispatch');
  }

  if(sevHigh){
    out.push('Escalate to control tower for go/no-go approval and exception handling plan');
  }else if(sevMod){
    out.push('Add checkpoint call-ins at intermediate hubs; ensure exception workflow is ready');
  }else{
    out.push('Log route conditions and keep standard checkpoint updates for traceability');
  }

  // Keep exactly 3 actions.
  const uniq = [];
  const seen = new Set();
  for(const x of out){
    const k = x.toLowerCase();
    if(seen.has(k)) continue;
    seen.add(k);
    uniq.push(x);
    if(uniq.length >= 3) break;
  }
  while(uniq.length < 3){
    uniq.push('Confirm handoff timing and keep standard checkpoint updates for traceability');
  }
  return uniq.slice(0,3);
}

function _formatDecisionSupportBlock(o, isRecommended){
  const routePath = String((o && (o.route || o.route_path)) || '').trim();
  const mode = String((o && (o.mode || o.transport_mode)) || '').trim();
  const apiAlerts = (o && (o.route_alerts || o.api_alerts)) ? (o.route_alerts || o.api_alerts) : [];

  const routeLine = isRecommended ? `${routePath} (recommended)` : routePath;
  const alerts = Array.isArray(apiAlerts) ? apiAlerts : [];
  const alertLines = alerts.length
    ? alerts.slice(0,4).map(a=>{
        const sev = _severityLabelFromAlert(a);
        const title = String((a && (a.title || a.details || a.message || a.eventtype)) || '').trim();
        const loc = String((a && (a.location || a.city || a.region)) || '').trim();
        const summary = (title && loc) ? `${title} (${loc})` : (title || loc || '');
        return `[${sev}] ${summary}`.trim();
      }).filter(Boolean)
    : ['[Info] No API alerts for this route'];

  const actionLines = _actionLinesFromAlerts(alerts, mode);
  const decision = _decisionFromAlerts(alerts);

  return (
    `Route:\n${routeLine}\n\n`+
    `Alerts:\n${alertLines.join('\n')}\n\n`+
    `Action:\n- ${actionLines[0]}\n- ${actionLines[1]}\n- ${actionLines[2]}\n\n`+
    `Decision:\n${decision}`
  );
}

function _calcExpectedFreshness(currentFreshness, additionalDelayHours, temperatureDeviation){
  const cf = (typeof currentFreshness === 'number') ? currentFreshness : parseFloat(currentFreshness);
  const d = (typeof additionalDelayHours === 'number') ? additionalDelayHours : parseFloat(additionalDelayHours);
  const td = (typeof temperatureDeviation === 'number') ? temperatureDeviation : parseFloat(temperatureDeviation);
  const cur = Number.isFinite(cf) ? cf : 0;
  const delayH = Number.isFinite(d) ? Math.max(0, d) : 0;
  const tdev = Number.isFinite(td) ? Math.abs(td) : 0;
  const expected = Math.max(0, cur - ((delayH/24*0.05) + (tdev*0.01)));
  return expected;
}

function _fmtAlerts(alerts){
  if(!Array.isArray(alerts) || alerts.length===0) return 'None';
  return alerts.map(a=>{
    const sev = String(a.severity||'').toUpperCase();
    const ts = a.timestamp ? new Date(a.timestamp).toLocaleString() : '';
    const msg = a.message || '';
    const tsTxt = ts ? ` (${ts})` : '';
    return `[${sev}] ${msg}${tsTxt}`;
  }).join('<br>');
}

async function loadInTransit(){
  const box = document.getElementById('inTransit');
  if(!box) return;
  const res = await fetch('/api/logistics/in_transit', {headers:H});
  const rows = await res.json().catch(()=>[]);
  if(!res.ok || !Array.isArray(rows)){
    box.textContent = 'Unable to load data. Please refresh.';
    return;
  }
  if(rows.length===0){
    box.innerHTML = '<div>No active shipments. Await pickup requests from farmers.</div>';
    const ov = document.getElementById('routeOverview');
    if(ov) ov.innerHTML = '<div>No active shipments.</div>';
    setRoutePlanningEnabled(false);
    try{ window.__hasActiveShipments = false; }catch(e){}
    try{ _setAlertsVisibility(false); }catch(e){}
    return;
  }

  try{ window.__hasActiveShipments = true; }catch(e){}
  try{ _setAlertsVisibility(true); }catch(e){}

  // Track last known displayed freshness to avoid UI regressions when backend flags a logic error.
  if(!window._lastFreshnessByShipmentId) window._lastFreshnessByShipmentId = {};

  const hasInTransit = rows.some(r => String((r && r.status) || '').toUpperCase() === 'IN_TRANSIT');
  setRoutePlanningEnabled(hasInTransit);

  try{
    const active = rows.find(r => String((r && r.status) || '').toUpperCase() === 'IN_TRANSIT') || null;
    window.activeInTransitShipment = active;
  }catch(e){ window.activeInTransitShipment = null; }

  const ov = document.getElementById('routeOverview');
  if(ov) ov.innerHTML = '<div><strong>Active Shipments:</strong> ' + rows.length + '</div>';

  const qp = new URLSearchParams(location.search || '');
  const focusId = qp.get('shipment_id');

  const showActions = false;
  const head = '<table><tr>'+
    '<th>Shipment ID</th><th>Crop</th><th>Batch ID</th><th>Pickup location</th><th>Destination warehouse</th><th>Current freshness</th><th>Risk</th><th>Status</th>'+
    '</tr>';

  box.innerHTML = head +
    rows.map(r=>{
      const sid = (typeof r.shipment_id !== 'undefined' && r.shipment_id !== null) ? String(r.shipment_id) : '';
      const isFocus = focusId && sid && String(focusId) === sid;
      const style = isFocus ? ' style="outline:2px solid #22c55e"' : '';
      const st = String(r.status||'');
      const ts = (r && r.last_updated) ? new Date(r.last_updated).toLocaleString() : new Date().toLocaleString();
      const riskTxt = (typeof r.risk_status !== 'undefined' && r.risk_status !== null) ? String(r.risk_status) : '';
      const initF = (r && typeof r.initial_freshness === 'number' && Number.isFinite(r.initial_freshness)) ? r.initial_freshness : null;
      const hit = (r && typeof r.hours_in_transit === 'number' && Number.isFinite(r.hours_in_transit)) ? r.hours_in_transit : null;
      const sidNum = parseInt(sid||'0', 10);
      const ok = (r && typeof r.freshness_update_ok === 'boolean') ? r.freshness_update_ok : true;
      const err = String((r && r.freshness_update_error) || '').trim();
      const freshRaw = (typeof r.current_freshness === 'number') ? r.current_freshness : parseFloat(r.current_freshness);
      const lastKnown = window._lastFreshnessByShipmentId[sidNum];
      const freshnessForUI = (!ok && Number.isFinite(lastKnown)) ? lastKnown : freshRaw;
      if(ok && Number.isFinite(sidNum) && Number.isFinite(freshRaw)){
        window._lastFreshnessByShipmentId[sidNum] = freshRaw;
      }
      const uiErr = (!ok && err) ? (`<div style="color:#ef4444;font-size:12px;margin-top:2px">Freshness update blocked: ${err}</div>`) : '';
      const twinLine = (initF !== null || hit !== null)
        ? `<div style="font-size:0.85em;opacity:0.85;margin-top:2px">Initial: ${initF!==null?_fmtFreshness(initF):'-'} | In transit: ${hit!==null?hit.toFixed(2)+' h':'-'}</div>`
        : '';
      return `<tr data-shipment-id="${sid}"${style}>`+
        `<td>${sid}</td>`+
        `<td>${r.crop ?? ''}</td>`+
        `<td>${r.batch_id ?? ''}</td>`+
        `<td>${r.pickup_location ?? ''}</td>`+
        `<td>${r.destination_warehouse ?? ''}</td>`+
        `<td>${_fmtFreshness(freshnessForUI)}${uiErr}${twinLine}<div style="font-size:0.85em;opacity:0.8;margin-top:2px">Last updated: ${ts}</div></td>`+
        `<td>${_riskBadgeHtml(riskTxt)}</td>`+
        `<td>${r.status ?? ''}</td>`+
        `</tr>`;
    }).join('') + '</table>';

  if(focusId){
    try{
      const tr = box.querySelector(`tr[data-shipment-id="${CSS.escape(String(focusId))}"]`);
      if(tr){ tr.scrollIntoView({block:'center'}); }
    }catch(e){}
  }
}

if(document.getElementById('inTransit')){
  loadInTransit();
  setInterval(loadInTransit, 20000);
}

if(document.getElementById('deliveredShipments')){
  loadDeliveredShipments();
  setInterval(loadDeliveredShipments, 30000);
}

if(document.getElementById('emergencyRequired')){
  loadEmergencyRequired();
  setInterval(loadEmergencyRequired, 20000);
}



// Alerts auto-polling
let __alertsPollHandle = null;

function _setAlertsVisibility(show){
  const box = document.getElementById('alerts');
  if(!box) return;
  const section = box.closest('section') || box.parentElement;
  if(section) section.style.display = show ? '' : 'none';

  if(show){
    if(__alertsPollHandle === null){
      loadAlerts();
      __alertsPollHandle = setInterval(loadAlerts, 15000);
    }
  }else{
    if(__alertsPollHandle !== null){
      clearInterval(__alertsPollHandle);
      __alertsPollHandle = null;
    }
    box.innerHTML = '';
  }
}

async function loadAlerts(){
  try{
    if(window.__hasActiveShipments === false){
      _setAlertsVisibility(false);
      return;
    }
  }catch(e){}
  const res = await fetch('/api/logistics/alerts', {headers:H});
  const box = document.getElementById('alerts');
  if(!box) return;
  if(res.status===401 || res.status===422){
    try{ localStorage.removeItem('access_token'); localStorage.removeItem('token'); }catch(e){}
    box.innerHTML = '<div>Session expired. Please login again.</div>';
    location.href = '/';
    return;
  }
  if(res.status===403){
    box.innerHTML = '<div>Forbidden: login as a Logistics user to view alerts.</div>';
    return;
  }
  const data = await res.json().catch(()=>[]);
  
  // Also fetch shipments data to check delivery status
  let shipmentsData = [];
  try {
    const shipmentsRes = await fetch('/api/logistics/my_shipments', {headers:H});
    if(shipmentsRes.ok) {
      shipmentsData = await shipmentsRes.json().catch(() => []);
    }
  } catch(e) {
    // Continue with empty shipments data if fetch fails
  }
  
  // Filter to show ONLY records with Pickup Status = "Picked Up"
  const pickedUpData = (Array.isArray(data) ? data : []).filter(a => {
    const ev = String((a && a.event_type) || '');
    const st = String((a && a.alert_status) || '');
    return ev === 'PICKUP_STATUS' && st === 'PICKED_UP';
  });
  
  box.innerHTML = pickedUpData.length
    ? pickedUpData.map(a=>{
        const ev = String((a && a.event_type) || '');
        const st = String((a && a.alert_status) || '');
        const tsRaw = (a && (a.alert_timestamp || a.created_at)) ? String(a.alert_timestamp || a.created_at) : '';
        const ts = tsRaw ? new Date(tsRaw).toLocaleString() : '';
        const region = (a && a.region) || '';
        
        // Check if this batch is delivered by cross-referencing shipments data
        const batchId = (a && a.batch_id) || '';
        const deliveredShipment = shipmentsData.find(r => 
          String((r && r.status) || '').toUpperCase() === 'DELIVERED' && 
          String(r.batch_id || '') === String(batchId)
        );
        
        const isDelivered = !!deliveredShipment;
        const deliveryTsRaw = isDelivered ? (deliveredShipment.delivery_time || deliveredShipment.delivered_at || '') : '';
        const deliveryTs = deliveryTsRaw ? new Date(String(deliveryTsRaw)).toLocaleString() : '';
        const deliveryLocation = isDelivered ? (deliveredShipment.destination_warehouse || deliveredShipment.destination || '') : '';
        
        return `
            <div class="status-card">
              <div class="status-card-left">
                <div class="status-field">
                  <span class="status-label">Pickup Status</span>
                  <span class="status-value success">Picked Up</span>
                </div>
                <div class="status-field">
                  <span class="status-label">Location</span>
                  <span class="status-value">${region}</span>
                </div>
                <div class="status-field">
                  <span class="status-label">Date & Time</span>
                  <span class="status-value">${ts}</span>
                </div>
              </div>
              <div class="status-card-right">
                <div class="status-field">
                  <span class="status-label">Delivery Status</span>
                  <span class="status-value ${isDelivered ? 'success' : 'pending'}">${isDelivered ? 'Delivered' : 'Pending'}</span>
                </div>
                <div class="status-field">
                  <span class="status-label">Location</span>
                  <span class="status-value">${deliveryLocation || (isDelivered ? '-' : 'Not delivered yet')}</span>
                </div>
                <div class="status-field">
                  <span class="status-label">Date & Time</span>
                  <span class="status-value">${deliveryTs || (isDelivered ? '-' : 'Not delivered yet')}</span>
                </div>
              </div>
            </div>
          `;
      }).join('')
    : '<div class="no-status-records">No picked-up records to display.</div>';
}
if(document.getElementById('alerts')){ try{ _setAlertsVisibility(false); }catch(e){} }

// My shipments list with quick status set
async function loadMyShipments(){
  const res = await fetch('/api/logistics/my_shipments', {headers:H});
  const rows = await res.json();
  let table = document.getElementById('myShipments');
  if(!table){
    const container = document.querySelector('.dashboard-card') || document.body;
    const h3 = document.createElement('h2');
    h3.textContent = 'My Shipments';
    container.appendChild(h3);

    // Small UI hint to guide logistics users
    const hint = document.createElement('div');
    hint.id = 'shipmentSelectionHint';
    hint.textContent = 'Select a shipment to manage logistics actions.';
    hint.style.fontSize = '0.9em';
    hint.style.opacity = '0.9';
    hint.style.marginBottom = '6px';
    container.appendChild(hint);

    table = document.createElement('table');
    table.id = 'myShipments';
    container.appendChild(table);
  }
  const showActions = (userRole === 'logistics');
  const safeRows = (Array.isArray(rows) ? rows : []).filter(r=>{
    const st = String((r && r.status) || '').toUpperCase();
    return st === 'PICKUP_REQUESTED' || st === 'IN_TRANSIT';
  });

  // Update Active Shipments count
  try{
    const activeShipmentsCount = document.getElementById('activeShipmentsCount');
    if(activeShipmentsCount){
      activeShipmentsCount.textContent = `Active Shipments: ${safeRows.length}`;
    }
  }catch(e){}

  try{
    const hasAny = !!(safeRows && safeRows.length);
    window.__hasActiveShipments = hasAny;
    _setAlertsVisibility(hasAny);
  }catch(e){}

  if(!safeRows.length){
    table.innerHTML = '<div class="no-shipments-message">No active shipments. Pickup must be requested by farmer.</div>';
    try{ _autofillPlanFromShipment(null); }catch(e){}
    try{ window.selectedShipmentId = null; window.selectedShipment = null; }catch(e){}
    return;
  }

  // Maintain a lookup by shipment id for selection handling
  try{
    window._shipmentById = {};
    safeRows.forEach(r=>{
      const sid = (r && (r.id ?? r.shipment_id));
      const sidNum = parseInt(String(sid ?? ''), 10);
      if(Number.isFinite(sidNum) && sidNum > 0){
        window._shipmentById[sidNum] = r;
      }
    });
  }catch(e){ window._shipmentById = {}; }
  
  // Generate card layout instead of table
  table.innerHTML = safeRows.map(r => {
    const st = String(r.status||'');
    const stU = st.toUpperCase();
    const canPickup = stU === 'PICKUP_REQUESTED';
    const canTransit = stU === 'IN_TRANSIT';
    const etaDisplay = (r.eta_hours!=null && String(r.eta_hours)!=='') ? _fmtHours(r.eta_hours) : ((r.route && String(r.route).trim()) ? 'ETA unavailable. Please generate route.' : '');
    
    const actionButton = showActions
      ? (canPickup 
        ? `<button type="button" class="shipment-action-btn" data-act="pickup" data-id="${String(r.id)}">Confirm Pickup</button>`
        : (canTransit 
          ? `<button type="button" class="shipment-action-btn" data-act="deliver" data-id="${String(r.id)}">Confirm Delivery</button>`
          : ''))
      : '';

    return `
      <div class="shipment-card" data-shipment-id="${String(r.id)}">
        <div class="shipment-card-column">
          <div class="shipment-field">
            <span class="field-label">Shipment ID</span>
            <span class="field-value">${r.id}</span>
          </div>
          <div class="shipment-field">
            <span class="field-label">Batch ID</span>
            <span class="field-value">${r.batch_id}</span>
          </div>
        </div>
        <div class="shipment-card-column">
          <div class="shipment-field">
            <span class="field-label">Status</span>
            <span class="field-value status-${stU.toLowerCase()}">${r.status}</span>
          </div>
          <div class="shipment-field">
            <span class="field-label">ETA</span>
            <span class="field-value">${etaDisplay}</span>
          </div>
        </div>
        <div class="shipment-card-column">
          <div class="shipment-field">
            <span class="field-label">Route</span>
            <span class="field-value route-text">${r.route||'Not specified'}${r.via ? ` via ${r.via}` : ''}</span>
          </div>
        </div>
        <div class="shipment-card-column">
          <div class="shipment-action-container">
            ${actionButton}
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Helper to visually indicate selection and bind context
  function _selectShipmentRow(shipmentId){
    const sidNum = parseInt(String(shipmentId||''), 10);
    if(!Number.isFinite(sidNum) || sidNum <= 0) return;

    try{ window.selectedShipmentId = sidNum; }catch(e){}
    try{ window.selectedShipment = (window._shipmentById && window._shipmentById[sidNum]) || null; }catch(e){ window.selectedShipment = null; }

    // Highlight selected card with a subtle, transparent style
    try{
      table.querySelectorAll('.shipment-card').forEach(card=>{
        const isSelected = parseInt(String(card.getAttribute('data-shipment-id')||''), 10) === sidNum;
        if(isSelected){
          card.style.outline = '2px solid rgba(34,197,94,0.9)';  // green border
          card.style.backgroundColor = 'rgba(148, 163, 184, 0.18)'; // soft slate tint
        }else{
          card.style.outline = '';
          card.style.backgroundColor = '';
        }
      });
    }catch(e){}

    // Autofill plan form and enable planning only for the selected shipment
    if(window.selectedShipment){
      try{ _autofillPlanFromShipment(window.selectedShipment); }catch(e){}
      const stU = String(window.selectedShipment.status || '').toUpperCase();
      // Route planning only meaningful once shipment is in transit
      setRoutePlanningEnabled(stU === 'IN_TRANSIT');
    }
  }

  // Card-click selection: exactly one shipment at a time
  try{
    table.querySelectorAll('.shipment-card').forEach(card=>{
      card.style.cursor = 'pointer';
      card.addEventListener('click', ()=>{
        const sidAttr = card.getAttribute('data-shipment-id') || '';
        _selectShipmentRow(sidAttr);
      });
    });
  }catch(e){}

  // If a shipment_id is present in the URL, auto-select it on load
  try{
    const qp = new URLSearchParams(location.search || '');
    const focusId = qp.get('shipment_id');
    if(focusId){
      _selectShipmentRow(focusId);
    }
  }catch(e){}

  if(showActions){
    try{
      table.querySelectorAll('button[data-act]').forEach(btn=>{
        btn.addEventListener('click', async ()=>{
          const act = btn.getAttribute('data-act');
          const sid = btn.getAttribute('data-id');
          const shipment_id = parseInt(String(sid||''), 10);
          if(!Number.isFinite(shipment_id) || shipment_id <= 0) return;
          // Ensure the clicked shipment becomes the active selection
          try{ _selectShipmentRow(shipment_id); }catch(e){}
          try{
            if(act === 'pickup'){
              const r = await fetch('/api/logistics/pickup_confirm', {method:'POST', headers:H, body: JSON.stringify({shipment_id})});
              const j = await r.json().catch(()=>({}));
              if(!r.ok){
                const msg = (j && (j.msg || j.message || j.error)) ? String(j.msg || j.message || j.error) : `Confirm Pickup failed (${r.status})`;
                alert(msg);
                return;
              }
              await loadMyShipments();
              await loadInTransit();
              return;
            }
            if(act === 'deliver'){
              try{ btn.disabled = true; }catch(e){}
              const opened = _openConfirmDeliveryModal(shipment_id, btn);
              if(!opened){
                alert('Unable to open confirmation dialog. Please refresh.');
                try{ btn.disabled = false; }catch(e){}
              }
              return;
            }
          }catch(e){
            alert('Unable to load data. Please refresh.');
          }
        });
      });
    }catch(e){}
  }
}

// Prefill weather → factors helper
async function prefillFactors(city){
  const res = await fetch('/api/logistics/weather?city='+encodeURIComponent(city), {headers:H});
  const j = await res.json();
  if(!res.ok) return;
  const delayForm = document.getElementById('delayForm');
  delayForm.querySelector('input[name="weather_factor"]').value = j.weather_factor;
  delayForm.querySelector('input[name="congestion"]').value = j.congestion;
  const compareForm = document.getElementById('compareForm');
  compareForm.querySelector('input[name="weather_factor"]').value = j.weather_factor;
  compareForm.querySelector('input[name="congestion"]').value = j.congestion;
}

// initial loads
// Validate auth on page load to prevent repeated 403s when a wrong-role token is present.
_ensureLogisticsAuth().then(ok=>{
  if(!ok) return;
  if(document.getElementById('alerts')){ loadAlerts(); setInterval(loadAlerts, 15000); }
  loadMyShipments();
  if(document.getElementById('inTransit')){
    loadInTransit();
    setInterval(loadInTransit, 20000);
  }
});

// GenAI recommendations (top-level handler)
const genaiForm = document.getElementById('genaiForm');
if(genaiForm){
  genaiForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(genaiForm).entries());
    if(fd.risk!==undefined && fd.risk!=='') fd.risk = parseFloat(fd.risk);
    // augment with selected route details (predicted delay and alerts) if available
    if(typeof window.lastRouteDetails === 'object' && window.lastRouteDetails){
      if(typeof window.lastRouteDetails.predicted_delay_hours !== 'undefined') fd.delay_hours = window.lastRouteDetails.predicted_delay_hours;
      if(Array.isArray(window.lastRouteDetails.route_alerts)) fd.route_alerts = window.lastRouteDetails.route_alerts;
    }
    const btn = genaiForm.querySelector('button[type="submit"]');
    if(btn) btn.disabled = true;
    const res = await fetch('/api/logistics/genai', {method:'POST', headers:H, body: JSON.stringify(fd)});
    const j = await res.json().catch(()=>({}));
    const box = document.getElementById('genaiMsg');
    if(res.ok){
      // Convert suggestion to bullet points, handling numbered lists and paragraphs
      let bullets = j.suggestion
        .replace(/^\d+\.\s*/gm, '')
        .replace(/^\(\d+\)\s*/gm, '')
        .split(/\n\s*\n|\.\s*(?=\n)|\n(?=\d+\.)/)
        .map(s => s.trim())
        .filter(s => s.length > 0)
        .map(s => `• ${s.replace(/\.$/, '')}`)
        .join('<br>');
      box.innerHTML = `${bullets}<br><small>${j.notes}</small>`;
    } else {
      box.textContent = j.msg||'Advice failed';
    }
    if(btn) btn.disabled = false;
  });
}

// Open route in Google Maps from Plan form
const openMapsBtn = document.getElementById('openMapsBtn');
if(openMapsBtn){
  openMapsBtn.addEventListener('click', ()=>{
    const routeInput = document.querySelector('#planForm input[name="route"]');
    const raw = (routeInput?.value||'').trim();
    if(!raw){ return; }
    const parts = raw.split('->').map(s=>s.trim()).filter(Boolean);
    if(parts.length===1){
      window.open('https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(parts[0]), '_blank');
      return;
    }
    const origin = parts[0];
    const destination = parts[parts.length-1];
    const waypoints = parts.slice(1, parts.length-1).join('|');
    const url = 'https://www.google.com/maps/dir/?api=1'
      + '&origin=' + encodeURIComponent(origin)
      + '&destination=' + encodeURIComponent(destination)
      + (waypoints? ('&waypoints='+encodeURIComponent(waypoints)) : '')
      + '&travelmode=driving';
    window.open(url, '_blank');
  });
}

// Live alerts (filtered by current route if provided)
async function loadLiveAlerts(){
  const routeInput = document.querySelector('#planForm input[name="route"]');
  const modeSelect = document.getElementById('routeMode') || document.querySelector('#planForm select[name="mode"]');
  const routeVal = encodeURIComponent((routeInput?.value||'').trim());
  const modeVal = encodeURIComponent((modeSelect?.value||'').trim());
  
  // Include both route and mode parameters
  const url = routeVal ? (`/api/logistics/alerts_live?route=${routeVal}&mode=${modeVal}`) : '/api/logistics/alerts_live';
  
  const res = await fetch(url, {headers:H});
  const j = await res.json().catch(()=>[]);
  const box = document.getElementById('alertsLive');
  if(!box) return;
  if(!res.ok || !Array.isArray(j)){
    box.textContent = 'Could not load live alerts';
    return;
  }
  if(j.length===0){ box.textContent = routeVal? 'No alerts along this route' : 'No alerts'; return; }
  box.innerHTML = j.map(a=>`<div>[${a.alertlevel}] ${a.eventtype}: ${a.title} (${a.country||'N/A'})</div>`).join('');
}
const refreshLiveAlertsBtn = document.getElementById('refreshLiveAlerts');
if(refreshLiveAlertsBtn){ refreshLiveAlertsBtn.addEventListener('click', loadLiveAlerts); }
if(document.getElementById('alertsLive')){ loadLiveAlerts(); setInterval(loadLiveAlerts, 60000); }

// =============== New: Suggest Routes, Route Alerts, Preview Impact ===============
const suggestBtn = document.getElementById('suggestRoutesBtn');
const suggestSelect = document.getElementById('suggestedRoutes');
const routeInput = document.querySelector('#planForm input[name="route"]');
const disasterFlag = document.getElementById('routeDisasterFlag');

try{
  if(suggestBtn) suggestBtn.style.display = 'none';
  if(suggestSelect) suggestSelect.style.display = 'none';
}catch(e){}

function _alertLevelRank(level){
  const lvl = String(level||'').trim().toLowerCase();
  const sev = { extreme: 4, severe: 3, red: 3, orange: 2, moderate: 2, minor: 1, yellow: 1, info: 0, unknown: 0 };
  return (lvl in sev) ? sev[lvl] : 0;
}

function _shortAlertTitle(title, isDirect){
  let s = String(title||'').trim();
  s = s.replace(/^Forecast:\s*/i, '');
  s = s.replace(/\s+in next\s+24h\s*$/i, '');
  s = s.replace(/^[-–—]+\s*/, '');
  s = s.replace(/^Hub\s+[^-:]+\s*-\s*/i, '');
  s = s.replace(/^(?:[^-:]+\s*-\s*)?Current conditions near\s*[^:]+:\s*/i, '');
  s = s.replace(/\s*,\s*humidity\s*\d+%/ig, '');
  // Preserve mode-specific prefixes like "Maritime:", "Aviation:", "Rail:", "Road:"
  const modePrefix = s.match(/^(Maritime|Aviation|Rail|Road):\s*/i);
  const prefix = modePrefix ? modePrefix[0] : '';
  s = s.replace(/^(Maritime|Aviation|Rail|Road):\s*/i, '');
  if(isDirect){
    s = s.replace(/\b(Origin|Destination|Hub)\b\s*/ig, '');
    s = s.replace(/\bEn-route\b\s*[^:]+:\s*/ig, '');
  } else {
    s = s.replace(/\bEn-route\b\s*/ig, '');
  }
  s = s.replace(/\s+/g, ' ').trim();
  if(s.length > 92) s = s.slice(0, 89) + '...';
  return prefix + s;
}

function _pickTopAlert(alerts){
  if(!Array.isArray(alerts) || alerts.length===0) return null;
  const sevOrder = {'extreme':4,'severe':3,'moderate':2,'minor':1,'info':0,'':0,'unknown':0};
  let top = alerts[0];
  let topSev = sevOrder[String(top.alertlevel||'').toLowerCase()]||0;
  for(let i=1;i<alerts.length;i++){
    const sev = sevOrder[String(alerts[i].alertlevel||'').toLowerCase()]||0;
    if(sev > topSev){ top = alerts[i]; topSev = sev; }
  }
  return topSev > 0 ? top : null; // Return null if only Info-level items
}

function _pickTopAlerts(alerts, n){
  if(!Array.isArray(alerts) || alerts.length===0) return [];
  const sevOrder = {'extreme':4,'severe':3,'moderate':2,'minor':1,'info':0,'':0,'unknown':0};
  const items = alerts.map(a=>({a, sev: sevOrder[String((a||{}).alertlevel||'').toLowerCase()]||0}));
  items.sort((x,y)=> (y.sev - x.sev));
  const out = [];
  const seen = new Set();
  for(const it of items){
    if(out.length >= n) break;
    if(!it || !it.a) continue;
    const lvl = String(it.a.alertlevel||'').trim().toLowerCase();
    if((sevOrder[lvl]||0) <= 0) continue;
    const key = (String(it.a.eventtype||'')+'|'+String(it.a.title||'')+'|'+String(it.a.alertlevel||'')).toLowerCase();
    if(seen.has(key)) continue;
    seen.add(key);
    out.push(it.a);
  }
  return out;
}

function _formatTopAlert(alerts, isDirect){
  const topList = _pickTopAlerts(alerts, 3);
  if(topList.length){
    return topList.map(a=>{
      const lvl = String(a.alertlevel||'').trim() || 'Unknown';
      const et = String(a.eventtype||'').trim() || 'Alert';
      const title = _shortAlertTitle(a.title, isDirect);
      return `[${lvl}] ${et}: ${title}`;
    }).join('<br>');
  }
  const a = _pickTopAlert(alerts);
  if(!a){
    // If there are only Info-level items, show the first one (which is now mode-specific)
    if(Array.isArray(alerts) && alerts.length){
      const info = alerts.find(x => _alertLevelRank(x && x.alertlevel) === 0);
      if(info){
        const title = _shortAlertTitle(info.title, isDirect);
        return title || 'Weather: OK';
      }
    }
    return 'None';
  }
  const lvl = String(a.alertlevel||'').trim() || 'Unknown';
  const et = String(a.eventtype||'').trim() || 'Alert';
  const title = _shortAlertTitle(a.title, isDirect);
  return `[${lvl}] ${et}: ${title}`;
}

// Dynamic UI: Origin/Destination + Route Finder (no template changes needed)
function ensureRouteFinderUI(){
  const planForm = document.getElementById('planForm'); if(!planForm) return;
  const routeInputEl = document.querySelector('#planForm input[name="route"]');
  const routeRow = routeInputEl ? routeInputEl.closest('div') : null;
  if(!document.getElementById('findRoutesBtn')){
    const row = document.createElement('div');
    row.style.display='flex'; row.style.gap='8px'; row.style.alignItems='center'; row.style.marginBottom='6px';
    row.innerHTML = `
      <input id="startLocation" placeholder="Start location (auto)" disabled>
      <select id="routeMode"><option>road</option></select>
      <button type="button" id="findRoutesBtn">Find Routes</button>
      <select id="routeOptions" style="max-width:420px;"></select>
    `;
    if(routeRow){ planForm.insertBefore(row, routeRow); } else { planForm.appendChild(row); }
  }
  const startEl = document.getElementById('startLocation');
  _setReadonlyGrey(startEl);
  try{
    const m = document.getElementById('routeMode');
    if(m){ m.value = 'road'; }
  }catch(e){}
  // Ensure we never create or keep a duplicate destination field.
  const dup = document.querySelectorAll('#planForm input[name="destination"]');
  if(dup && dup.length > 1){
    for(let i=1;i<dup.length;i++){
      try{ dup[i].remove(); }catch(e){}
    }
  }
  if(!document.getElementById('routeOptionsTable')){
    const tableBox = document.createElement('div'); tableBox.id='routeOptionsTable';
    const flag = document.getElementById('routeDisasterFlag');
    if(flag && flag.parentElement){
      flag.parentElement.appendChild(tableBox);
    } else {
      planForm.appendChild(tableBox);
    }
  }
}
ensureRouteFinderUI();

async function getRouteOptions(){
  const originEl = document.getElementById('startLocation');
  const destEl = document.querySelector('#planForm input[name="destination"]');
  const modeEl = document.getElementById('routeMode');
  const optsEl = document.getElementById('routeOptions');
  const tblBox = document.getElementById('routeOptionsTable');
  if(!originEl || !destEl || !modeEl || !optsEl || !tblBox) return;
  const btn = document.getElementById('findRoutesBtn');
  if(btn){
    if(btn.dataset.loading === '1') return;
    btn.dataset.loading = '1';
    btn.disabled = true;
  }
  const body = { origin: (originEl.value||'').trim()||'Vizag', destination: (destEl.value||'').trim()||'Chennai', mode: (modeEl.value||'road').toLowerCase() };
  let res;
  try{
    res = await fetch('/api/logistics/route_options', { method:'POST', headers:H, body: JSON.stringify(body) });
  }catch(e){
    tblBox.innerHTML = '<div>Backend not reachable. Start the backend server and refresh.</div>';
    if(btn){ btn.dataset.loading = '0'; btn.disabled = false; }
    return;
  }
  const j = await res.json().catch(()=>({ options: [] }));
  window.lastRouteOptionsResponse = j;
  optsEl.innerHTML = '';
  if(!res.ok){
    const msg = (j && (j.error || j.message || j.msg || j.detail)) ? String(j.error || j.message || j.msg || j.detail) : '';
    if(res.status===401 || res.status===403){
      tblBox.innerHTML = '<div>Not authorized. Please login again as Logistics user.</div>';
    } else {
      tblBox.innerHTML = `<div>Route options request failed (${res.status}). ${msg}</div>`;
    }
    if(btn){ btn.dataset.loading = '0'; btn.disabled = false; }
    return;
  }
  if(!Array.isArray(j.options) || j.options.length===0){
    tblBox.innerHTML = '<div>No route options found</div>';
    if(btn){ btn.dataset.loading = '0'; btn.disabled = false; }
    return;
  }
    j.options.forEach((o,idx)=>{
    const opt = document.createElement('option');
    const hazard = (Array.isArray(o.route_alerts) && o.route_alerts.some(a=>_alertLevelRank(a && a.alertlevel) > 0)) ? ' ⚠' : '';
    opt.value = o.route;
    const eta = (typeof o.eta_hours === 'number') ? o.eta_hours : parseFloat(o.eta_hours);
    const delay = (typeof o.predicted_delay_hours === 'number') ? o.predicted_delay_hours : parseFloat(o.predicted_delay_hours);
    const etaTxt = Number.isFinite(eta) ? `${eta} h ETA` : 'ETA N/A';
    const delayTxt = Number.isFinite(delay) ? `${delay} h delay` : 'delay N/A';
    opt.textContent = `${o.route} — ${o.distance_km} km, ${etaTxt} (${delayTxt})${hazard}`;
    if(typeof j.recommended_index==='number' && j.recommended_index===idx) opt.textContent = '⭐ '+opt.textContent;
    optsEl.appendChild(opt);
  });
  // Do not auto-select or auto-fill a route. User must manually pick.
  // Render mandatory table (route intelligence output)
  const _oneSentence = (s)=>{
    const t = String(s||'').replace(/\s+/g,' ').trim();
    if(!t) return '';
    const idx = t.indexOf('.');
    return idx>=0 ? (t.slice(0, idx+1)).trim() : t;
  };
  const _ensureUnique = (txt, seen, fallback)=>{
    const t = String(txt||'').trim();
    if(!t) return '';
    const key = t.toLowerCase();
    if(!seen.has(key)){
      seen.add(key);
      return t;
    }
    const extra = String(fallback||'').trim();
    const tweaked = extra ? `${t} (${extra})` : `${t} (route-specific)`;
    seen.add(tweaked.toLowerCase());
    return tweaked;
  };
  const seenSummaries = new Set();
  const seenActions = new Set();

  tblBox.innerHTML = '<table><tr><th>Route Option</th><th>Route</th><th>Distance (km)</th><th>Delay (h)</th><th>Mode</th><th>Route Risk Summary</th><th>Recommended Decision</th></tr>'+
    j.options.map((o,i)=>{
      const routePath = String(o.route||'').trim();
      const routeOption = `Route Option ${i+1}`;
      let dist = (typeof o.distance_km === 'number') ? o.distance_km : (o.distance_km ?? '');
      try{
        const dn = (typeof o.distance_km === 'number') ? o.distance_km : parseFloat(o.distance_km);
        if(Number.isFinite(dn) && dn <= 0) dist = '0 km (Same city)';
      }catch(e){}
      const delay = (typeof o.predicted_delay_hours === 'number') ? o.predicted_delay_hours : parseFloat(o.predicted_delay_hours);
      const delayTxt = Number.isFinite(delay) ? delay.toFixed(2) : '';
      const modeTxt = String(o.mode || o.transport_mode || '').trim();
      const rawSummary = _oneSentence(o.risk_description);
      const rawAction = _oneSentence(o.recommended_action);
      const summary = _ensureUnique(rawSummary, seenSummaries, routePath);
      const action = _ensureUnique(rawAction, seenActions, routePath);
      return `<tr>`+
        `<td>${routeOption}</td>`+
        `<td>${routePath}</td>`+
        `<td>${dist}</td>`+
        `<td>${delayTxt}</td>`+
        `<td>${modeTxt}</td>`+
        `<td>${summary}</td>`+
        `<td>${action}</td>`+
      `</tr>`;
    }).join('') + '</table>';

  if(!document.getElementById('whatIfBox')){
    const w = document.createElement('div');
    w.id = 'whatIfBox';
    w.style.marginTop = '10px';
    tblBox.parentElement?.appendChild(w);
  }
  const whatIfBox = document.getElementById('whatIfBox');
  if(whatIfBox){
    whatIfBox.innerHTML = canSimulate
      ? '<div><strong>What-If Simulation Result</strong><div style="opacity:0.85">Select a route option to simulate delay impact and generate advisory.</div></div>'
      : '<div>Route planning is available only after pickup confirmation.</div>';
  }

  if(btn){ btn.dataset.loading = '0'; btn.disabled = false; }
}

const findRoutesBtn = document.getElementById('findRoutesBtn');
if(findRoutesBtn){ /* binding handled above via _handleFindRoutes */ }
const routeOptionsSelect = document.getElementById('routeOptions');
if(routeOptionsSelect){ routeOptionsSelect.addEventListener('change', async ()=>{
  if(routeInput){ routeInput.value = routeOptionsSelect.value; await checkRouteAlerts(routeInput.value); }
  // Sync stored details when dropdown changes
  const idx = routeOptionsSelect.selectedIndex;
  const jr = window.lastRouteOptionsResponse;
  if(jr && Array.isArray(jr.options) && jr.options[idx]){
    window.lastRouteDetails = jr.options[idx];
  }

  // Advisory + simulation (no persistence)
  try{
    const details = window.lastRouteDetails;
    const s = window.activeInTransitShipment;
    if(!details || !s || String(s.status||'').toUpperCase()!=='IN_TRANSIT') return;

    const etaEl = document.querySelector('#planForm input[name="eta_hours"]');
    let plannedEta = etaEl ? parseFloat(etaEl.value||'') : null;
    if(!Number.isFinite(plannedEta)) plannedEta = parseFloat(s.eta_hours||'')
    if(!Number.isFinite(plannedEta)) plannedEta = 0;
    const newEta = parseFloat(details.eta_hours||'');
    const additional_delay_hours = Number.isFinite(newEta) ? Math.max(0, newEta - plannedEta) : 0;
    const expected_freshness = _calcExpectedFreshness(s.current_freshness, additional_delay_hours, s.temperature_deviation);
    const risk_status = _riskFromFreshness(expected_freshness);
    const alerts = Array.isArray(details.route_alerts) ? details.route_alerts : [];
    const route_alert_summary = _formatTopAlert(alerts, true).replace(/<br>/g,'; ');

    const payload = {
      crop: s.crop || '',
      current_freshness: s.current_freshness,
      expected_freshness,
      additional_delay_hours,
      risk_status,
      route_alert_summary,
    };

    const res = await fetch('/api/logistics/route_advisory', { method:'POST', headers:H, body: JSON.stringify(payload) });
    const j = await res.json().catch(()=>null);
    const rec = j && (j.recommendation || j.rec) ? String(j.recommendation || j.rec) : '';
    const exp = j && (j.explanation || j.exp) ? String(j.explanation || j.exp) : '';
    const advisory = (rec && exp) ? (`Recommendation: ${rec}\nExplanation: ${exp}`) : '';
    details._advisory_text = advisory;

    const whatIfBox = document.getElementById('whatIfBox');
    if(whatIfBox){
      whatIfBox.innerHTML =
        `<div><strong>What-If Simulation Result</strong></div>`+
        `<div style="margin-top:6px"><strong>Selected route:</strong> ${details.route||''}</div>`+
        `<div><strong>ETA (h):</strong> ${Number.isFinite(newEta)? newEta:''}</div>`+
        `<div><strong>Additional delay (h):</strong> ${additional_delay_hours.toFixed(2)}</div>`+
        `<div><strong>Expected freshness:</strong> ${_fmtFreshness(expected_freshness)}</div>`+
        `<div><strong>Risk status:</strong> ${risk_status}</div>`+
        `<div style="margin-top:6px"><strong>Detected alerts:</strong> ${route_alert_summary || 'None'}</div>`+
        `<div style="margin-top:6px"><strong>GenAI recommendation</strong><div style="white-space:pre-wrap">${advisory || 'Unavailable'}</div></div>`;
    }
  }catch(e){}
}); }

async function checkRouteAlerts(routeText){
  if(!routeText){ disasterFlag.textContent=''; return; }
  const res = await fetch('/api/logistics/route_alerts', {method:'POST', headers:H, body: JSON.stringify({route: routeText})});
  const j = await res.json().catch(()=>[]);
  if(res.ok && Array.isArray(j) && j.length){
    const top = j[0];
    disasterFlag.textContent = `Disaster detected near route: [${top.alertlevel}] ${top.eventtype} - ${top.title}`;
  } else {
    disasterFlag.textContent = '';
  }
}

if(suggestBtn){
  suggestBtn.addEventListener('click', async ()=>{
    // Legacy UI disabled: use "Find Routes" which calls /api/logistics/find_routes.
    return;
    const tblBox = document.getElementById('routeOptionsTable');
    const planMsg = document.getElementById('planMsg');
    const shipment_id = (typeof window.autoFilledShipmentId === 'number') ? window.autoFilledShipmentId : null;
    if(!Number.isFinite(shipment_id) || shipment_id <= 0){
      if(planMsg) planMsg.textContent = 'No active shipments. Pickup must be requested by farmer.';
      return;
    }
    const modeEl = document.querySelector('#planForm select[name="mode"]');
    const mode = (modeEl?.value || 'road').toLowerCase() || 'road';
    if(tblBox) tblBox.innerHTML = '<div>Simulating route options...</div>';
    let res;
    try{
      res = await fetch('/api/logistics/simulate_routes', {method:'POST', headers:H, body: JSON.stringify({ shipment_id, mode })});
    }catch(e){
      if(tblBox) tblBox.innerHTML = '<div>Backend not reachable. Start the backend server and refresh.</div>';
      return;
    }
    const j = await res.json().catch(()=>null);
    if(!res.ok || !j){
      const msg = j && (j.msg || j.error || j.message) ? String(j.msg || j.error || j.message) : `Request failed (${res.status})`;
      if(tblBox) tblBox.innerHTML = `<div>${msg}</div>`;
      return;
    }
    const options = Array.isArray(j.options) ? j.options : [];
    suggestSelect.innerHTML = '';
    options.forEach((o)=>{
      const opt = document.createElement('option');
      opt.value = o.route || '';
      const risk = String(o.risk_level||'');
      opt.textContent = `${o.route} — ${o.distance_km} km, ${o.eta_hours} h, ${risk}`;
      suggestSelect.appendChild(opt);
    });
    if(options.length){
      suggestSelect.selectedIndex = 0;
      if(routeInput) routeInput.value = options[0].route || '';
      await checkRouteAlerts(routeInput.value);
    }

    const rowsHtml = options.map((o, idx)=>{
      const risk = String(o.risk_level||'');
      const riskDesc = String(o.risk_description||'');
      const rec = String(o.recommended_action||'');
      const delay = (o.predicted_delay_hours!=null) ? String(o.predicted_delay_hours) : '';
      const eta = (o.eta_hours!=null) ? String(o.eta_hours) : '';
      return `<tr>`+
        `<td>${idx+1}</td>`+
        `<td>${o.route||''}</td>`+
        `<td>${o.distance_km ?? ''}</td>`+
        `<td>${delay}</td>`+
        `<td>${o.transport_mode ?? ''}</td>`+
        `<td>${risk}${riskDesc?`<div style="font-size:0.85em;opacity:0.85;margin-top:2px">${riskDesc}</div>`:''}</td>`+
        `<td>${rec}</td>`+
        `<td><button type="button" data-sim-select="1" data-route="${encodeURIComponent(String(o.route||''))}" data-eta="${encodeURIComponent(String(eta))}" data-mode="${encodeURIComponent(String(o.transport_mode||mode))}">Select</button></td>`+
      `</tr>`;
    }).join('');

    if(tblBox){
      tblBox.innerHTML = '<table>'+
        '<tr><th>Route Option</th><th>Route</th><th>Distance</th><th>Predicted Delay</th><th>Mode</th><th>Risk Description</th><th>Recommended Action</th><th></th></tr>'+
        rowsHtml +
        '</table>';

      tblBox.querySelectorAll('button[data-sim-select="1"]').forEach(btn=>{
        btn.addEventListener('click', async ()=>{
          const route = decodeURIComponent(btn.getAttribute('data-route')||'');
          const eta_hours = decodeURIComponent(btn.getAttribute('data-eta')||'');
          const m = decodeURIComponent(btn.getAttribute('data-mode')||mode);
          if(!route) return;
          try{
            btn.disabled = true;
            if(planMsg) planMsg.textContent = 'Applying selected route...';
            const r2 = await fetch('/api/logistics/apply_route_option', {method:'POST', headers:H, body: JSON.stringify({ shipment_id, route, eta_hours, mode: m })});
            const j2 = await r2.json().catch(()=>null);
            if(!r2.ok || !j2){
              const msg2 = j2 && (j2.msg || j2.error || j2.message) ? String(j2.msg || j2.error || j2.message) : `Request failed (${r2.status})`;
              if(planMsg) planMsg.textContent = msg2;
              btn.disabled = false;
              return;
            }
            try{ if(routeInput) routeInput.value = route; }catch(e){}
            try{
              const etaEl = document.querySelector('#planForm input[name="eta_hours"]');
              if(etaEl) etaEl.value = String(j2.eta_hours ?? eta_hours ?? '');
            }catch(e){}
            if(planMsg) planMsg.textContent = 'Route applied. ETA updated.';
            try{ await loadMyShipments(); }catch(e){}
            try{ await loadInTransit(); }catch(e){}
          }catch(e){
            if(planMsg) planMsg.textContent = 'Unable to apply route. Please refresh.';
          }finally{
            try{ btn.disabled = false; }catch(e){}
          }
        });
      });
    }
  });
}

if(suggestSelect){
  suggestSelect.addEventListener('change', async ()=>{
    routeInput.value = suggestSelect.value;
    await checkRouteAlerts(routeInput.value);
  });
}

if(routeInput){
  routeInput.addEventListener('blur', ()=> checkRouteAlerts(routeInput.value));
}


// (No-op) additional handler removed; main GenAI handler already augments with preview

// Helper: copy selected route details into GenAI form
function ensureCopyToGenAIBtn(){
  const genaiForm = document.getElementById('genaiForm');
  if(!genaiForm || document.getElementById('copyToGenAIBtn')) return;
  const btn = document.createElement('button');
  btn.id='copyToGenAIBtn'; btn.textContent='Use Selected Route';
  btn.type='button'; btn.style.marginTop='8px';
  genaiForm.appendChild(btn);
  btn.addEventListener('click', ()=>{
    const details = window.lastRouteDetails;
    if(!details){ alert('No route selected yet. Use Find Routes first.'); return; }
    const modeField = genaiForm.querySelector('select[name="mode"]');
    const routeField = genaiForm.querySelector('input[name="route"]');
    const riskField = genaiForm.querySelector('input[name="risk"]');
    if(modeField) modeField.value = (document.getElementById('routeMode')?.value) || 'road';
    if(routeField) routeField.value = details.route || '';
    // Auto-set risk based on alerts count and delay
    let risk = 0.2;
    if(Array.isArray(details.route_alerts) && details.route_alerts.length){
      const severe = details.route_alerts.some(a=>a.alertlevel && ['Severe','Extreme'].includes(a.alertlevel));
      risk = severe ? 0.8 : 0.5;
    }
    if(details.predicted_delay_hours > 24) risk = Math.max(risk, 0.5);
    if(riskField) riskField.value = risk;
  });
}
ensureCopyToGenAIBtn();

// Wire up locked Start Location + auto ETA computation.
const batchIdEl = document.querySelector('#planForm input[name="batch_id"]');
const destEl = document.querySelector('#planForm input[name="destination"]');
const modeEl = document.querySelector('#planForm select[name="mode"]');
if(batchIdEl){
  batchIdEl.addEventListener('input', async ()=>{ await refreshBatchContext(); await refreshEta(); });
  batchIdEl.addEventListener('change', async ()=>{ await refreshBatchContext(); await refreshEta(); });
}
if(destEl){
  destEl.addEventListener('input', async ()=>{ await refreshEta(); });
  destEl.addEventListener('change', async ()=>{ await refreshEta(); });
}
if(modeEl){
  modeEl.addEventListener('change', async ()=>{ await refreshEta(); });
}
// initial
if(userRole === 'logistics'){
  refreshBatchContext();
  refreshEta();
}

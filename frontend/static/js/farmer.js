const t=localStorage.getItem('access_token');
const userRole=localStorage.getItem('user_role');

// Global variables for state management
let _submittedBatches = []; // Store all submitted batches
let _selectedBatchId = null; // Track selected batch for main dashboard
let _selectedStoredBatchId = null; // Track selected stored batch for stored batches section

// Language management - _currentLang is now defined in farmer_translations.js

function setLanguage(lang) {
  console.log('setLanguage called with:', lang);
  updateCurrentLang(lang);
  
  // Update select element
  const langSelect = document.getElementById('langSelect');
  if (langSelect) langSelect.value = lang;
  
  // Reload all dropdowns with new language
  console.log('Reloading dropdowns...');
  loadCropOptions();
  loadCityOptions();
  
  // Update all UI text
  console.log('Updating page text...');
  updatePageText();
  
  // Refresh city/warehouse dropdowns from inline script
  if (typeof refreshDropdowns === 'function') {
    console.log('Calling refreshDropdowns...');
    refreshDropdowns();
  }
}

function t_(key) {
  if (!FarmerTranslations || !FarmerTranslations[key]) {
    console.warn(`Translation key not found: ${key}`);
    return key;
  }
  const translated = FarmerTranslations[key][_currentLang] || FarmerTranslations[key]['en'] || key;
  console.log(`t_(${key}) [${_currentLang}] = "${translated}"`);
  return translated;
}

function updatePageText() {
  console.log('updatePageText called, current lang:', _currentLang);
  
  // Update all elements with data-i18n attribute
  const elements = document.querySelectorAll('[data-i18n]');
  console.log('Found', elements.length, 'elements with data-i18n');
  
  elements.forEach(el => {
    const key = el.getAttribute('data-i18n');
    const translated = t_(key);
    console.log(`Translating key: ${key} -> "${translated}"`);
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      el.placeholder = translated;
    } else {
      el.textContent = translated;
    }
  });
  
  // Update placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.placeholder = t_(key);
  });
  
  // Refresh dynamic content
  refreshDynamicContent();
}

function refreshDynamicContent() {
  // Refresh alerts and risk status labels
  if (_submittedBatches.length > 0) {
    loadSubmittedBatchDetails();
  }
  loadBatches();
  if (_selectedStoredBatchId) {
    loadStoredBatchDetails(_selectedStoredBatchId);
  }
}

// Initialize language on page load
document.addEventListener('DOMContentLoaded', function() {
  // Set initial language
  const langSelect = document.getElementById('langSelect');
  if (langSelect) {
    langSelect.value = _currentLang;
  }
  updatePageText();
});

// Access control check
if(!t || userRole !== 'farmer'){
  localStorage.clear();
  location.href='/';
}

function _fallbackAlertLabels(b){
  const s = String((b && b.status) ? b.status : '').toUpperCase();
  const f = (b && typeof b.freshness_score === 'number') ? b.freshness_score : null;
  if(f !== null && Number.isFinite(f)){
    const f0 = Math.max(0, Math.min(1, f));
    if(f0 < 0.40) return [t_('highSpoilageRisk')];
    if(f0 < 0.70) return [t_('freshnessDeclining')];
    return [t_('good')];
  }
  if(s === 'HIGH') return [t_('highSpoilageRisk')];
  if(s === 'RISK') return [t_('freshnessDeclining')];
  if(s === 'SAFE') return [t_('good')];
  return [];
}

const H={'Content-Type':'application/json','Authorization':'Bearer '+t};

function _setSelectedEmptyState(show){
  const el = document.getElementById('selectedBatchEmptyState');
  if(!el) return;
  el.style.display = show ? '' : 'none';
}

function _clearPanelContents(){
  const ids = ['panel_overview','panel_freshness','panel_alerts','panel_warehouse','panel_genai'];
  for(const id of ids){
    const el = document.getElementById(id);
    if(el) el.textContent = '';
  }
}

function _setSelectedRowHighlight(batchId){
  // Handle main batches table
  const table = document.getElementById('batches');
  if(!table) return;
  try{
    const rows = table.querySelectorAll('tr[data-bid]');
    rows.forEach(r=>{
      r.classList.remove('batch-row-selected');
    });
    if(batchId === null || batchId === undefined) return;
    const sel = table.querySelector(`tr[data-bid="${String(batchId)}"]`);
    if(sel){
      sel.classList.add('batch-row-selected');
    }
  }catch(e){}
  
  // Handle submitted batch table
  const submittedTable = document.getElementById('submittedBatchTable');
  if(!submittedTable) return;
  try{
    const submittedRows = submittedTable.querySelectorAll('tr[data-bid]');
    submittedRows.forEach(r=>{
      r.classList.remove('batch-row-selected');
    });
    if(batchId === null || batchId === undefined) return;
    const submittedSel = submittedTable.querySelector(`tr[data-bid="${String(batchId)}"]`);
    if(submittedSel){
      submittedSel.classList.add('batch-row-selected');
    }
  }catch(e){}
}

function _authFail(){
  localStorage.removeItem('access_token');
  localStorage.removeItem('token');
  alert('Session expired. Please login again.');
  location.href = '/';
}

function _setErr(id, msg){
  const el = document.getElementById(id);
  if(!el) return;
  el.textContent = msg || '';
}

async function loadCropOptions(){
  const sel = document.getElementById('cropSelect');
  if(!sel) return;
  try{
    const res = await fetch('/api/farmer/options/crops', {headers:H});
    if(res.status===401 || res.status===422){ _authFail(); return; }
    if(!res.ok){
      let detail = '';
      try{
        const raw = await res.text();
        detail = raw ? raw : '';
      }catch(e){
        detail = '';
      }
      alert(`Failed to load crops (${res.status})${detail?`: ${detail}`:''}`);
      return;
    }
    const j = await res.json();
    const crops = (j && j.crops) ? j.crops : [];
    console.log('Crop options loaded:', {count: j && j.count, source: j && j.source});
    if(!Array.isArray(crops) || crops.length === 0){
      alert(`No crops returned from backend${(j && j.source)?` (source: ${j.source})`:''}.`);
    }
    sel.innerHTML = `<option value="">${t_('selectCrop')}</option>` +
      crops.map(c=>`<option value="${String(c).replace(/"/g,'&quot;')}">${translateCropName(c, _currentLang)}</option>`).join('');
  }catch(e){
    alert('Failed to load crops');
  }
}

async function loadUnitForSelectedCrop(){
  const cropSel = document.getElementById('cropSelect');
  const unitEl = document.getElementById('quantity_unit');
  const shelfLifeEl = document.getElementById('shelf_life_info');
  if(!cropSel || !unitEl) return;
  const crop = (cropSel.value || '').trim();
  if(!crop){
    unitEl.value = 'kg';
    if(shelfLifeEl) shelfLifeEl.textContent = '';
    return;
  }
  try{
    const res = await fetch(`/api/farmer/options/unit?crop=${encodeURIComponent(crop)}`, {headers:H});
    if(res.status===401 || res.status===422){ _authFail(); return; }
    if(!res.ok){
      unitEl.value = 'kg';
      if(shelfLifeEl) shelfLifeEl.textContent = '';
      return;
    }
    const j = await res.json();
    unitEl.value = (j && j.unit) ? j.unit : 'kg';
    if(shelfLifeEl && j && typeof j.shelf_life_days === 'number' && j.shelf_life_days > 0) {
      shelfLifeEl.textContent = `Shelf Life: ${j.shelf_life_days} days`;
    } else if(shelfLifeEl) {
      shelfLifeEl.textContent = '';
    }
  }catch(e){
    unitEl.value = 'kg';
    if(shelfLifeEl) shelfLifeEl.textContent = '';
  }
}

function initAutoUnitSelection(){
  const cropSel = document.getElementById('cropSelect');
  if(!cropSel) return;
  cropSel.addEventListener('change', loadUnitForSelectedCrop);
}

function initDailyAutoRefresh(){
  let last = new Date().toISOString().slice(0,10);
  setInterval(async ()=>{
    const cur = new Date().toISOString().slice(0,10);
    if(cur !== last){
      last = cur;
      try{ await loadBatches(); }catch(e){}
    }
  }, 5 * 60 * 1000);
}

async function loadCityOptions(){
  const sel = document.getElementById('citySelect');
  if(!sel) return;
  try{
    const res = await fetch('/api/farmer/options/cities', {headers:H});
    if(res.status===401 || res.status===422){ _authFail(); return; }
    if(!res.ok){
      let detail = '';
      try{
        const raw = await res.text();
        detail = raw ? raw : '';
      }catch(e){
        detail = '';
      }
      alert(`Failed to load cities (${res.status})${detail?`: ${detail}`:''}`);
      return;
    }
    const j = await res.json();
    const cities = (j && j.cities) ? j.cities : [];
    sel.innerHTML = `<option value="">${t_('selectCity')}</option>` +
      cities.map(c=>`<option value="${String(c).replace(/"/g,'&quot;')}">${translateCityName(c, _currentLang)}</option>`).join('');
  }catch(e){
    alert('Failed to load cities');
  }
}

function initHarvestDatePicker(){
  const picker = document.getElementById('harvest_date_picker');
  const display = document.getElementById('harvest_date_display');
  const hidden = document.getElementById('harvest_date');
  if(!picker || !display || !hidden) return;

  picker.addEventListener('keydown', (e)=> e.preventDefault());
  picker.addEventListener('input', (e)=> e.preventDefault());
  picker.addEventListener('change', ()=>{
    const v = picker.value || '';
    if(!v){
      display.value = '';
      hidden.value = '';
      return;
    }
    const parts = v.split('-');
    if(parts.length !== 3){
      display.value = '';
      hidden.value = '';
      return;
    }
    const ddmmyyyy = `${parts[2]}-${parts[1]}-${parts[0]}`;
    display.value = ddmmyyyy;
    hidden.value = ddmmyyyy;
  });

  display.addEventListener('click', ()=>{
    try{ picker.showPicker(); }catch(e){ picker.focus(); }
  });
}

async function loadBatches(){
  const res = await fetch('/api/farmer/batches', {headers:H});
  if(res.status===401 || res.status===422){
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    alert('Session expired. Please login again.');
    location.href = '/';
    return;
  }
  if(!res.ok){
    let detail='';
    let raw='';
    try { raw = await res.text(); } catch(e) { raw = ''; }
    if(raw){
      try {
        const j = JSON.parse(raw);
        detail = j && (j.msg || j.message || JSON.stringify(j));
      } catch(e) {
        detail = raw;
      }
    }
    alert(`Failed to load batches (${res.status})${detail?`: ${detail}`:''}`);
    return;
  }
  const data = await res.json();
  const el = document.getElementById('batches');
  el.innerHTML = '<tr>'+
    `<th>${t_('batchId')}</th><th>${t_('crop')}</th><th>${t_('quantity')}</th><th>${t_('harvestDateCol')}</th><th>${t_('daysSinceHarvest')}</th>`+
    `<th>${t_('freshnessScore')}</th><th>${t_('farmerRiskStatus')}</th><th>${t_('alerts')}</th>`+
    '</tr>' +
    data.map(b=>{
      // render quantity with unit if we stored a unit in details; fallback to kg for display
      const unit = (b && b.quantity_unit) ? b.quantity_unit : 'kg';
      const dsh = (b && typeof b.days_since_harvest === 'number') ? b.days_since_harvest : '';
      const fresh = (b && typeof b.freshness_score === 'number') ? b.freshness_score : null;
      const freshText = (typeof fresh === 'number' && Number.isFinite(fresh)) ? `${Math.max(0, Math.min(1, fresh)).toFixed(2)}` : '';
      const batchSeason = (b && b.batch_season) ? String(b.batch_season) : '';
      const translatedSeason = batchSeason ? translateSeasonName(batchSeason, _currentLang) : '';
      const seasonBadge = translatedSeason
        ? ` <span style="background:#334155;color:white;padding:1px 6px;border-radius:999px;font-size:11px">${translatedSeason}</span>`
        : '';
      const rawAlerts = Array.isArray(b.alerts) ? b.alerts : [];
      const effectiveAlerts = rawAlerts.length ? rawAlerts : _fallbackAlertLabels(b);
      const alerts = effectiveAlerts.length
        ? effectiveAlerts.map(a=>{
            const label = String(a||'');
            const ok = label.toLowerCase() === 'good';
            const bg = ok ? '#22c55e' : '#ef4444';
            // Translate label
            let translatedLabel = label;
            if (label.toLowerCase() === 'good') translatedLabel = t_('good') || 'Good';
            else if (label.toLowerCase() === 'delivered') translatedLabel = t_('delivered') || 'Delivered';
            else if (label.toLowerCase().includes('pickup completed')) translatedLabel = t_('pickupCompleted') || 'Crop pickup completed';
            else if (label.toLowerCase().includes('pickup requested')) translatedLabel = t_('pickupRequested') || 'Pickup requested';
            else if (label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage')) translatedLabel = t_('highSpoilageRisk') || label;
            else if (label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk')) translatedLabel = t_('freshnessDeclining') || label;
            return `<span style="background:${bg};color:white;padding:2px 6px;border-radius:3px;font-size:11px">${translatedLabel}</span>`;
          }).join(' ')
        : '';
      const translatedCrop = translateCropName(b.crop_type, _currentLang);
      // Translate status
      const status = String(b.status || '').toUpperCase();
      let translatedStatus = b.status || '';
      if (status === 'SAFE') translatedStatus = t_('safe') || 'SAFE';
      else if (status === 'HIGH') translatedStatus = t_('high') || 'HIGH';
      else if (status === 'GOOD') translatedStatus = t_('good') || 'GOOD';
      return `<tr data-bid="${b.id}" style="cursor:pointer">`+
        `<td>${b.id}</td>`+
        `<td>${translatedCrop}${seasonBadge}</td>`+
        `<td>${b.quantity} ${unit}</td>`+
        `<td>${b.harvest_date}</td>`+
        `<td>${dsh}</td>`+
        `<td>${freshText}</td>`+
        `<td>${translatedStatus}</td>`+
        `<td>${alerts}</td>`+
      `</tr>`
    }).join('');

  try{
    initBatchRowSelection(data);
    if(!Array.isArray(data) || data.length === 0){
      _selectedBatchId = null;
      _setSelectedRowHighlight(null);
      _clearPanelContents();
      _setSelectedEmptyState(true);
    }else{
      const cur = (_selectedBatchId !== null) ? (data||[]).find(x=>x && x.id === _selectedBatchId) : null;
      if(cur){
        selectBatch(cur);
      }else{
        // Default: select most recent batch (highest id)
        let mostRecent = data[0];
        for(const b of (data||[])){
          if(b && typeof b.id === 'number' && typeof mostRecent.id === 'number' && b.id > mostRecent.id){
            mostRecent = b;
          }
        }
        if(mostRecent) selectBatch(mostRecent);
      }
    }
  }catch(e){}

  renderCharts(data);
}

function _riskColor(status){
  const s = String(status||'').toUpperCase();
  if(s === 'SAFE') return '#16a34a';
  if(s === 'RISK') return '#f59e0b';
  if(s === 'HIGH SPOILAGE RISK') return '#dc2626';
  return '#64748b';
}

function initBatchRowSelection(data){
  const table = document.getElementById('batches');
  if(!table) return;
  if(table._batchClickBound) return;
  table._batchClickBound = true;
  table.addEventListener('click', (e)=>{
    const tr = e.target && e.target.closest ? e.target.closest('tr[data-bid]') : null;
    if(!tr) return;
    const bid = parseInt(tr.getAttribute('data-bid'), 10);
    if(!Number.isFinite(bid)) return;
    const b = (data||[]).find(x=>x && x.id === bid);
    if(b) selectBatch(b);
  });
}

function selectBatch(b){
  if(!b) return;
  _selectedBatchId = b.id;
  _setSelectedEmptyState(false);
  _setSelectedRowHighlight(b.id);
  renderPanels(b);
  loadGenAIForBatch(b.id);
}

function renderPanels(b){
  const ov = document.getElementById('panel_overview');
  const fr = document.getElementById('panel_freshness');
  const al = document.getElementById('panel_alerts');
  const wh = document.getElementById('panel_warehouse');
  const ga = document.getElementById('panel_genai');

  const unit = (b && b.quantity_unit) ? b.quantity_unit : 'kg';
  const dsh = (b && typeof b.days_since_harvest === 'number') ? b.days_since_harvest : '';
  const fresh = (b && typeof b.freshness_score === 'number') ? b.freshness_score : null;
  const freshText = (typeof fresh === 'number' && Number.isFinite(fresh)) ? `${Math.max(0, Math.min(1, fresh)).toFixed(2)}` : '';
  let rem = (b && typeof b.remaining_shelf_life_days === 'number') ? b.remaining_shelf_life_days : null;
  if(typeof rem === 'number' && Number.isFinite(rem) && rem < 0) rem = 0;
  const remText = (typeof rem === 'number' && Number.isFinite(rem)) ? `${Math.round(rem)} days` : '';
  const seasonalRisk = !!(b && b.seasonal_risk);
  const batchSeason = (b && b.batch_season) ? String(b.batch_season) : '';
  const primarySeason = batchSeason;
  const currentSeason = (b && b.current_season) ? String(b.current_season) : '';
  const inSeason = (typeof (b && b.in_season) === 'boolean') ? !!b.in_season : !seasonalRisk;
  const seasonalWarning = (b && b.seasonal_warning) ? String(b.seasonal_warning) : '';
  const dist = (b && typeof b.nearest_warehouse_distance_km === 'number') ? b.nearest_warehouse_distance_km : null;
  const distText = (typeof dist === 'number' && Number.isFinite(dist))
    ? ((dist <= 0) ? '0 km (Same city)' : `${dist.toFixed(2)} km`)
    : 'Warehouse data unavailable';
  const pickupHours = (b && typeof b.estimated_pickup_time_hours === 'number') ? b.estimated_pickup_time_hours : null;
  const pickupText = (typeof pickupHours === 'number' && Number.isFinite(pickupHours) && pickupHours > 0)
    ? `${Math.round(pickupHours)} hours`
    : ((typeof dist === 'number' && Number.isFinite(dist) && dist <= 0) ? 'Local pickup' : '');
  const weather = (b && b.current_weather_summary) ? String(b.current_weather_summary) : 'Weather unavailable';

  const state = (b && b.crop_state) ? String(b.crop_state) : '';
  const isSpoiled = (state.toUpperCase() === 'SPOILED') || (typeof fresh === 'number' && Number.isFinite(fresh) && fresh <= 0);
  const status = String((b && b.status) ? b.status : '').toUpperCase();
  const delivered = !!(b && (b.is_delivered || String(b.export_status||'').toUpperCase()==='DELIVERED'));
  const pickupCompleted = status === 'CROP PICKUP COMPLETED';

  if(ov){
    const seasonLine = (primarySeason || currentSeason)
      ? `<div style="margin-top:4px"><b>Season:</b> ${primarySeason || '-'}${currentSeason ? ` <span style=\"opacity:0.85\">| Current: ${currentSeason}</span>` : ''} `+
        `<span style="margin-left:6px;background:${inSeason ? '#16a34a' : '#f59e0b'};color:white;padding:1px 8px;border-radius:999px;font-size:11px">${inSeason ? 'In-season' : 'Off-season'}</span></div>`
      : '';
    const advisory = (!inSeason && (seasonalWarning || seasonalRisk))
      ? `<div style="margin-top:4px;color:#f59e0b"><b>Season Advisory:</b> ${seasonalWarning || 'Harvest date is outside the typical season for this crop.'}</div>`
      : '';
    ov.innerHTML = `<div><b>Batch:</b> ${b.id}</div>`+
      `<div><b>Crop:</b> ${b.crop_type}${primarySeason ? ` <span style=\"background:#334155;color:white;padding:1px 6px;border-radius:999px;font-size:11px\">${primarySeason}</span>` : ''}</div>`+
      `<div><b>Quantity:</b> ${b.quantity} ${unit}</div>`+
      `<div><b>Harvest date:</b> ${b.harvest_date}</div>`+
      `<div><b>Days since harvest:</b> ${dsh}</div>`+
      seasonLine +
      advisory;
  }

  if(fr){
    const col = _riskColor(b.status);
    fr.innerHTML = `<div><b>Freshness:</b> ${freshText}</div>`+
      `<div><b>Remaining shelf life:</b> ${remText}</div>`+
      `<div><b>Risk status:</b> <span style="color:${col};font-weight:700">${b.status}</span></div>`;
  }

  if(al){
    const rawAlerts = Array.isArray(b.alerts) ? b.alerts : [];
    const effectiveAlerts = rawAlerts.length ? rawAlerts : _fallbackAlertLabels(b);
    al.innerHTML = effectiveAlerts.length
      ? effectiveAlerts.map(x=>{
          const label = String(x||'');
          const ok = label.toLowerCase() === 'good';
          const bg = ok ? '#22c55e' : '#ef4444';
          // Translate label
          let translatedLabel = label;
          if (label.toLowerCase() === 'good') translatedLabel = t_('good') || 'Good';
          else if (label.toLowerCase() === 'delivered') translatedLabel = t_('delivered') || 'Delivered';
          else if (label.toLowerCase().includes('pickup completed')) translatedLabel = t_('pickupCompleted') || 'Crop pickup completed';
          else if (label.toLowerCase().includes('pickup requested')) translatedLabel = t_('pickupRequested') || 'Pickup requested';
          else if (label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage')) translatedLabel = t_('highSpoilageRisk') || label;
          else if (label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk')) translatedLabel = t_('freshnessDeclining') || label;
          return `<div style="margin:2px 0"><span style="background:${bg};color:white;padding:2px 6px;border-radius:3px;font-size:11px">${translatedLabel}</span></div>`;
        }).join('')
      : '';
  }

  if(wh){
    const pickupLine = (!isSpoiled && pickupText) ? `<div><b>Estimated pickup time:</b> ${pickupText}</div>` : '';
    const localLine = (!isSpoiled && typeof dist === 'number' && Number.isFinite(dist) && dist <= 0)
      ? `<div style="margin-top:4px"><span style="background:#334155;color:white;padding:1px 8px;border-radius:999px;font-size:11px">Local route</span> <span style="opacity:0.9">Pickup and warehouse are in the same city.</span></div>`
      : '';
    wh.innerHTML = `<div><b>Nearest warehouse:</b> ${b.warehouse || ''}</div>`+
      `<div><b>Distance:</b> ${distText}</div>`+
      pickupLine +
      localLine +
      `<div><b>Weather:</b> ${weather}</div>`;
  }

  if(ga){
    ga.textContent = '';
  }

  try{
    const a = document.getElementById('btnRequestPickup');
    const c = document.getElementById('btnSellCrop');
    const storedPickupBtn = document.getElementById('btnRequestPickupStored');
    const spoilTip = 'Action disabled: Crop is spoiled and unfit for sale, storage, or transport.';
    const spoilPickupAlert = 'Crop is spoiled. Pickup is not allowed.';
    const highRiskTip = 'Action disabled: Pickup blocked due to HIGH SPOILAGE RISK.';
    const saleTip = 'Action disabled: Crop is unfit for sale.';
    const clearTip = '';

    const freshVal = (typeof fresh === 'number' && Number.isFinite(fresh)) ? fresh : null;
    const canSell = (freshVal !== null && freshVal >= 0.3);
    const isHighSpoilageRisk = status === 'HIGH SPOILAGE RISK';
    const canPickup = !isSpoiled && !isHighSpoilageRisk;

    if(delivered){
      const tip = 'Action disabled: Delivered.';
      if(a){ a.disabled = true; a.title = tip; a.dataset.blockedMsg = 'Delivered.'; }
      if(c){ c.disabled = true; c.title = tip; }
      if(storedPickupBtn){ storedPickupBtn.disabled = true; storedPickupBtn.title = tip; storedPickupBtn.dataset.blockedMsg = 'Delivered.'; }
      return;
    }

    if(pickupCompleted){
      const tip = 'Action disabled: Crop pickup completed.';
      if(a){ a.disabled = true; a.title = tip; a.dataset.blockedMsg = 'Crop pickup completed.'; }
      if(c){ c.disabled = true; c.title = tip; }
      if(storedPickupBtn){ storedPickupBtn.disabled = true; storedPickupBtn.title = tip; storedPickupBtn.dataset.blockedMsg = 'Crop pickup completed.'; }
      return;
    }

    if(isSpoiled){
      if(a){ a.disabled = true; a.title = spoilTip; a.dataset.blockedMsg = spoilPickupAlert; }
      if(c){ c.disabled = true; c.title = spoilTip; }
      if(storedPickupBtn){ storedPickupBtn.disabled = true; storedPickupBtn.title = spoilTip; storedPickupBtn.dataset.blockedMsg = spoilPickupAlert; }
    }else{
      if(a){
        a.disabled = !canPickup;
        a.title = canPickup ? clearTip : highRiskTip;
        a.dataset.blockedMsg = canPickup ? '' : 'Pickup blocked: HIGH SPOILAGE RISK.';
      }
      if(c){ c.disabled = !canSell; c.title = canSell ? clearTip : saleTip; }
      if(storedPickupBtn){
        storedPickupBtn.disabled = !canPickup;
        storedPickupBtn.title = canPickup ? clearTip : highRiskTip;
        storedPickupBtn.dataset.blockedMsg = canPickup ? '' : 'Pickup blocked: HIGH SPOILAGE RISK.';
      }
    }
  }catch(e){}
}

async function loadGenAIForBatch(batchId){
  const ga = document.getElementById('panel_genai');
  if(!ga) return;
  if(!batchId){ ga.textContent = ''; return; }
  ga.textContent = t_('loading') || 'Loading recommendation...';
  try{
    const res = await fetch(`/api/farmer/batches/${encodeURIComponent(batchId)}/genai`, {method:'POST', headers:H, body: JSON.stringify({})});
    if(res.status===401 || res.status===422){ _authFail(); return; }
    if(!res.ok){
      ga.textContent = `${t_('failedToLoad')} (${res.status})`;
      return;
    }
    const j = await res.json();
    let rec = (j && j.recommendation) ? String(j.recommendation) : '';
    let exp = (j && j.explanation) ? String(j.explanation) : '';
    
    // Translate AI recommendations if language is not English
    if (_currentLang !== 'en' && typeof aiTranslator !== 'undefined') {
      try {
        ga.innerHTML = `<div style="color:#666;"><i>Translating to ${t_(_currentLang) || _currentLang}...</i></div>`;
        
        if (rec) {
          rec = await aiTranslator.translateText(rec, _currentLang);
        }
        if (exp) {
          exp = await aiTranslator.translateText(exp, _currentLang);
        }
      } catch (e) {
        console.warn('AI recommendation translation failed:', e);
        ga.innerHTML = `<div style="color:#666;"><i>Translation timeout - showing English...</i></div>`;
        // Fallback: use original English text
      }
    } else {
      // Use pattern-based translation as fallback
      rec = rec ? translateAIOutput(rec) : '';
      exp = exp ? translateAIOutput(exp) : '';
    }
    
    ga.innerHTML = `<div><b>${t_('recommendation')}:</b> ${rec}</div>`+
      `<div style="margin-top:4px"><b>${t_('explanation')}:</b> ${exp}</div>`;
  }catch(e){
    ga.textContent = t_('failedToLoad') || 'Failed to load recommendation.';
  }
}

function initActionButtons(){
  const a = document.getElementById('btnRequestPickup');
  const c = document.getElementById('btnSellCrop');
  const storedPickupBtn = document.getElementById('btnRequestPickupStored');

  if(a) a.addEventListener('click', async ()=>{
    if(!_selectedBatchId){
      alert('Select a batch first.');
      return;
    }

    // If UI disabled state prevented click, this won't run; but if user triggers anyway,
    // enforce clear safety messaging.
    try{
      if(a.disabled){
        const msg = (a.dataset && a.dataset.blockedMsg) ? String(a.dataset.blockedMsg) : '';
        if(msg){ alert(msg); }
        return;
      }
    }catch(e){}

    try{
      const res = await fetch(`/api/farmer/request-pickup/${encodeURIComponent(_selectedBatchId)}`, {method:'POST', headers:H, body: JSON.stringify({})});
      if(res.status===401 || res.status===422){ _authFail(); return; }
      const j = await res.json().catch(()=>({}));
      if(!res.ok){
        alert((j && j.msg) ? String(j.msg) : `Request Pickup failed (${res.status})`);
        return;
      }
      alert('Pickup requested. Redirecting to Logistics Dashboard...');
      const sid = (j && (j.shipment_id || (j.shipment && j.shipment.id))) ? (j.shipment_id || (j.shipment && j.shipment.id)) : '';
      const url = sid ? `/logistics?shipment_id=${encodeURIComponent(String(sid||''))}` : '/logistics';
      try{ console.log('Redirecting to:', url); }catch(e){}
      setTimeout(()=>{
        try{ window.location.assign(url); }catch(e){ window.location.href = url; }
      }, 50);
    }catch(e){
      alert('Request Pickup failed.');
    }
  });

  if(c) c.addEventListener('click', async ()=>{
    if(!_selectedBatchId){
      alert('Select a batch first.');
      return;
    }
    try{
      const res = await fetch(`/api/farmer/batches/${encodeURIComponent(_selectedBatchId)}/request_sell`, {method:'POST', headers:H, body: JSON.stringify({})});
      if(res.status===401 || res.status===422){ _authFail(); return; }
      const j = await res.json().catch(()=>({}));
      if(!res.ok){
        alert((j && j.msg) ? String(j.msg) : `Sell request failed (${res.status})`);
        return;
      }
      alert('Sell requested. Logistics will arrange movement to market.');
      try{ await loadBatches(); }catch(e){}
    }catch(e){
      alert('Sell request failed.');
    }
  });

  // Stored batch Request Pickup button
  if(storedPickupBtn) storedPickupBtn.addEventListener('click', async function(event) {
    // Force check if button should be disabled BEFORE any other logic
    if (this.disabled || this.classList.contains('force-disabled')) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      
      const msg = (this.dataset && this.dataset.blockedMsg) ? String(this.dataset.blockedMsg) : 'Action disabled.';
      if(msg){ alert(msg); }
      return false;
    }
    
    if(!_selectedStoredBatchId){
      alert('Select a stored batch first.');
      return;
    }

    // If UI disabled state prevented click, this won't run; but if user triggers anyway,
    // enforce clear safety messaging.
    try{
      if(storedPickupBtn.disabled){
        const msg = (storedPickupBtn.dataset && storedPickupBtn.dataset.blockedMsg) ? String(storedPickupBtn.dataset.blockedMsg) : '';
        if(msg){ alert(msg); }
        return;
      }
    }catch(e){}

    try{
      const res = await fetch(`/api/farmer/request-pickup/${encodeURIComponent(_selectedStoredBatchId)}`, {method:'POST', headers:H, body: JSON.stringify({})});
      if(res.status===401 || res.status===422){ _authFail(); return; }
      const j = await res.json().catch(()=>({}));
      if(!res.ok){
        alert((j && j.msg) ? String(j.msg) : `Request Pickup failed (${res.status})`);
        return;
      }
      alert('Pickup requested. Redirecting to Logistics Dashboard...');
      const sid = (j && (j.shipment_id || (j.shipment && j.shipment.id))) ? (j.shipment_id || (j.shipment && j.shipment.id)) : '';
      const url = sid ? `/logistics?shipment_id=${encodeURIComponent(String(sid||''))}` : '/logistics';
      try{ console.log('Redirecting to:', url); }catch(e){}
      setTimeout(()=>{
        try{ window.location.assign(url); }catch(e){ window.location.href = url; }
      }, 50);
    }catch(e){
      alert('Request Pickup failed.');
    }
  });
}

const form=document.getElementById('batchForm');
form.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const msgEl = document.getElementById('submitMsg');
  if(msgEl){
    msgEl.textContent = '';
    msgEl.classList.remove('success','error');
  }
  _setErr('crop_type_error','');
  _setErr('harvest_date_error','');
  _setErr('location_error','');
  const data = Object.fromEntries(new FormData(form).entries());
  data.quantity = parseFloat(data.quantity);
  
  // Specific warehouse debugging
  const warehouseElement = document.getElementById('warehouseSelect');
  const hiddenWarehouseElement = document.getElementById('warehouse_hidden');
  
  console.log('Warehouse element value:', warehouseElement ? warehouseElement.value : 'NOT FOUND');
  console.log('Hidden warehouse element value:', hiddenWarehouseElement ? hiddenWarehouseElement.value : 'NOT FOUND');
  console.log('Warehouse in form data:', data.warehouse);
  console.log('Hidden warehouse in form data:', data.warehouse_hidden);
  console.log('All form data:', data);
  
  // Use hidden field as primary warehouse source; never force a dummy fallback.
  // If no warehouse was selected, omit the field so backend can auto-resolve.
  const hiddenWh = (hiddenWarehouseElement && hiddenWarehouseElement.value) ? String(hiddenWarehouseElement.value).trim() : '';
  const selectWh = (warehouseElement && warehouseElement.value) ? String(warehouseElement.value).trim() : '';
  const finalWh = hiddenWh || selectWh;
  if (finalWh) {
    data.warehouse = finalWh;
    console.log('Using selected warehouse value:', data.warehouse);
  } else {
    delete data.warehouse;
    console.log('No warehouse selected; backend will auto-resolve nearest warehouse');
  }

  let ok = true;
  if(!data.crop_type){ _setErr('crop_type_error','Crop is required.'); ok=false; }
  if(!Number.isFinite(data.quantity)){ ok=false; }
  if(!data.harvest_date){ _setErr('harvest_date_error','Harvest date is required.'); ok=false; }
  if(!data.location){ _setErr('location_error','City is required.'); ok=false; }
  // Temporarily disable warehouse validation to test submission
  // if(!data.warehouse){ 
  //   // Show warehouse error in the warehouse info div
  //   const warehouseInfo = document.getElementById('warehouse_info');
  //   if(warehouseInfo) {
  //     warehouseInfo.textContent = '⚠️ Please select a warehouse';
  //     warehouseInfo.style.color = '#d63384';
  //   }
  //   ok=false; 
  // }
  if(!ok) return;

  // Ensure unit is always present and derived from crop selection
  const unitEl = document.getElementById('quantity_unit');
  if(unitEl && unitEl.value){
    data.quantity_unit = unitEl.value;
  }

  // keep unit client-side for display; backend stores numeric quantity
  console.log('Submitting batch data:', data); // Debug log
  const res = await fetch('/api/farmer/batches', {method:'POST', headers:H, body: JSON.stringify(data)});
  let j = {};
  let text = '';
  try {
    text = await res.text();
    if(text){
      try { j = JSON.parse(text); } catch(e) { j = {}; }
    }
  } catch(e) {
    text = '';
    j = {};
  }
  if(res.status===401 || res.status===422){
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    if(msgEl){
      msgEl.textContent = 'Session expired. Redirecting to login...';
      msgEl.classList.remove('success');
      msgEl.classList.add('error');
    }
    setTimeout(()=> location.href='/', 800);
    return;
  }
  if(res.ok){
    const seasonalWarning = (j && j.seasonal_warning) ? String(j.seasonal_warning) : '';
    if(msgEl){
      msgEl.textContent = seasonalWarning ? `Submitted successfully. ${seasonalWarning}` : 'Submitted successfully.';
      msgEl.classList.remove('error');
      msgEl.classList.add('success');
    }
    
    // Do not show submitted batch details; keep dashboard clean
    // displaySubmittedBatchDetails(data);
    
    await loadBatches();
    // do not reset unit selection; clear text inputs only
    const cropSel = document.getElementById('cropSelect');
    if(cropSel) cropSel.value='';
    form.querySelector('input[name="quantity"]').value='';
    const picker = document.getElementById('harvest_date_picker');
    const display = document.getElementById('harvest_date_display');
    const hidden = document.getElementById('harvest_date');
    if(picker) picker.value='';
    if(display) display.value='';
    if(hidden) hidden.value='';
    const citySel = document.getElementById('citySelect');
    if(citySel) citySel.value='';
    
    // Clear warehouse dropdown and info
    const warehouseSel = document.getElementById('warehouseSelect');
    if(warehouseSel) {
      warehouseSel.value = '';
      warehouseSel.disabled = true;
      warehouseSel.innerHTML = `<option value="">${t_('selectCityFirst') || 'Select City First'}</option>`;
    }
    const warehouseInfo = document.getElementById('warehouse_info');
    if(warehouseInfo) warehouseInfo.textContent = '';
  } else {
    if(msgEl){
      msgEl.textContent = (j && j.msg) ? j.msg : `Submit failed (${res.status})${text?`: ${text}`:''}`;
      msgEl.classList.remove('success');
      msgEl.classList.add('error');
    }
  }
});

// Open Google Maps with current location input
const mapsBtn = document.getElementById('openMaps');
if(mapsBtn){
  mapsBtn.addEventListener('click', ()=>{
    const citySel = document.getElementById('citySelect');
    const loc = citySel ? (citySel.value || '') : '';
    if(!loc){
      alert('Please select a city first.');
      return;
    }
    const url = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(loc);
    const w = window.open(url, '_blank', 'noopener');
    if(!w){
      location.href = url;
    }
  });
}

function renderCharts(batches){
  // Charts removed - visualizations section no longer exists
}

// function initAutoUnitSelection(){
//   const cropSel = document.getElementById('cropSelect');
//   if(cropSel){
//     cropSel.addEventListener('change', async ()=>{
//       await loadUnitForSelectedCrop();
//     });
//   }
// }

document.addEventListener('DOMContentLoaded', async ()=>{
  initHarvestDatePicker();
  initAutoUnitSelection();
  initActionButtons();
  initDailyAutoRefresh();
  await loadCropOptions();
  await loadUnitForSelectedCrop();
  await loadCityOptions();
  await loadBatches();
});

// View toggle functionality
function toggleStoredBatchesView() {
  const submitSection = document.getElementById('submitBatchSection');
  const batchesSection = document.getElementById('batchesSection');
  const storedBatchesSection = document.getElementById('storedBatchesSection');
  
  // Hide main sections, show stored batches
  if (submitSection) submitSection.style.display = 'none';
  if (batchesSection) batchesSection.style.display = 'none';
  if (storedBatchesSection) storedBatchesSection.style.display = 'block';
  
  // Load stored batches data
  loadStoredBatches();
}

// Function to return to main view
function toggleMainView() {
  const submitSection = document.getElementById('submitBatchSection');
  const batchesSection = document.getElementById('batchesSection');
  const storedBatchesSection = document.getElementById('storedBatchesSection');
  
  // Show main sections, hide stored batches
  if (submitSection) submitSection.style.display = 'block';
  if (batchesSection) batchesSection.style.display = 'block';
  if (storedBatchesSection) storedBatchesSection.style.display = 'none';
}

// Function to load stored batches with improved styling
async function loadStoredBatches() {
  const res = await fetch('/api/farmer/batches', {headers:H});
  if(res.status===401 || res.status===422){
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    alert('Session expired. Please login again.');
    location.href = '/';
    return;
  }
  if(!res.ok){
    let detail='';
    let raw='';
    try { raw = await res.text(); } catch(e) { raw = ''; }
    if(raw){
      try {
        const j = JSON.parse(raw);
        detail = j && (j.msg || j.message || JSON.stringify(j));
      } catch(e) {
        detail = raw;
      }
    }
    alert(`Failed to load stored batches (${res.status})${detail?`: ${detail}`:''}`);
    return;
  }
  
  const data = await res.json();
  const el = document.getElementById('storedBatchesTable');
  
  // Filter only stored batches (those that have been submitted and are in storage)
  const storedBatches = data.filter(b => b.status && b.status !== 'pending');
  
  el.innerHTML = '<tr>'+
    `<th>${t_('batchId')}</th><th>${t_('crop')}</th><th>${t_('quantity')}</th><th>${t_('harvestDateCol')}</th><th>${t_('daysSinceHarvest')}</th>`+
    `<th>${t_('freshnessScore')}</th><th>${t_('farmerRiskStatus')}</th><th>${t_('alerts')}</th>`+
    '</tr>' +
    storedBatches.map(b=> {
      // render quantity with unit if we stored a unit in details; fallback to kg for display
      const unit = (b && b.quantity_unit) ? b.quantity_unit : 'kg';
      const dsh = (b && typeof b.days_since_harvest === 'number') ? b.days_since_harvest : '';
      const fresh = (b && typeof b.freshness_score === 'number') ? b.freshness_score : null;
      const freshText = (typeof fresh === 'number' && Number.isFinite(fresh)) ? `${Math.max(0, Math.min(1, fresh)).toFixed(2)}` : '';
      const batchSeason = (b && b.batch_season) ? String(b.batch_season) : '';
      const translatedSeason = batchSeason ? translateSeasonName(batchSeason, _currentLang) : '';
      const seasonBadge = translatedSeason
        ? ` <span style="background:#334155;color:white;padding:1px 6px;border-radius:999px;font-size:11px">${translatedSeason}</span>`
        : '';
      const rawAlerts = Array.isArray(b.alerts) ? b.alerts : [];
      const effectiveAlerts = rawAlerts.length ? rawAlerts : _fallbackAlertLabels(b);
      
      // Create styled alert badges with translation
      const alerts = effectiveAlerts.length
        ? effectiveAlerts.map(a=> {
            const label = String(a||'');
            const isGood = label.toLowerCase() === 'good';
            const isHigh = label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage');
            const isMedium = label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk');
            const isDelivered = label.toLowerCase() === 'delivered';
            const isPickupCompleted = label.toLowerCase().includes('pickup completed');
            const isPickupRequested = label.toLowerCase().includes('pickup requested');
            const alertClass = isGood ? 'low' : (isHigh ? 'high' : (isMedium ? 'medium' : (isDelivered ? 'delivered' : (isPickupCompleted ? 'pickup-completed' : (isPickupRequested ? 'pickup-requested' : 'medium')))));
            // Translate alert label
            let translatedLabel = label;
            if (label.toLowerCase() === 'good') translatedLabel = t_('good') || 'Good';
            else if (label.toLowerCase() === 'delivered') translatedLabel = t_('delivered') || 'Delivered';
            else if (label.toLowerCase().includes('pickup completed')) translatedLabel = t_('pickupCompleted') || 'Crop pickup completed';
            else if (label.toLowerCase().includes('pickup requested')) translatedLabel = t_('pickupRequested') || 'Pickup requested';
            else if (label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage')) translatedLabel = t_('highSpoilageRisk') || label;
            else if (label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk')) translatedLabel = t_('freshnessDeclining') || label;
            return `<span class="alert-badge ${alertClass}">${translatedLabel}</span>`;
          }).join(' ')
        : '';
      
      // Create risk status badge with translation
      const status = String(b.status || '').toUpperCase();
      let riskClass = 'medium';
      if (status === 'SAFE' || status === 'GOOD') riskClass = 'safe';
      else if (status === 'HIGH' || status === 'CRITICAL') riskClass = 'high';
      
      // Translate status
      let translatedStatus = b.status || 'UNKNOWN';
      if (status === 'SAFE') translatedStatus = t_('safe') || 'SAFE';
      else if (status === 'HIGH') translatedStatus = t_('high') || 'HIGH';
      else if (status === 'GOOD') translatedStatus = t_('good') || 'GOOD';
      
      const riskBadge = `<span class="risk-badge ${riskClass}">${translatedStatus}</span>`;
      
      const translatedCrop = translateCropName(b.crop_type, _currentLang);
      
      return `<tr data-bid="${b.id}" style="cursor:pointer">`+
        `<td>${b.id}</td>`+
        `<td>${translatedCrop}${seasonBadge}</td>`+
        `<td>${b.quantity} ${unit}</td>`+
        `<td>${b.harvest_date}</td>`+
        `<td>${dsh}</td>`+
        `<td>${freshText}</td>`+
        `<td>${riskBadge}</td>`+
        `<td>${alerts}</td>`+
      `</tr>`;
    }).join('');
    
  // Add click handlers to stored batch rows
  const storedRows = el.querySelectorAll('tr[data-bid]');
  storedRows.forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function() {
      const batchId = this.getAttribute('data-bid');
      const batchData = storedBatches.find(b => b.id == batchId);
      
      if (batchData && batchData.id) {
        // Update stored batch details locally (not main dashboard)
        selectStoredBatch(batchData);
      }
    });
  });
    
  // Show empty state if no stored batches
  if (storedBatches.length === 0) {
    el.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-light);">No stored batches found. Submit batches to see them here.</td></tr>';
  }
}

// Function to handle stored batch selection (local to stored batches section)
function selectStoredBatch(b) {
  if (!b) return;
  
  // Update stored batch selection state
  _selectedStoredBatchId = b.id;
  
  // Show stored batch details panel
  const storedBatchDetails = document.getElementById('storedBatchDetails');
  const storedBatchEmptyState = document.getElementById('storedBatchEmptyState');
  
  if (storedBatchDetails) {
    storedBatchDetails.style.display = 'block';
  }
  
  if (storedBatchEmptyState) {
    storedBatchEmptyState.style.display = 'none';
  }
  
  // Update stored batch details panels
  renderStoredBatchPanels(b);
  
  // Update stored pickup button state
  updateStoredPickupButtonState(b);
  
  // Highlight selected row in stored batches table only
  highlightStoredBatchRow(b.id);
}

// Function to render stored batch details panels
function renderStoredBatchPanels(b) {
  // Clear previous content
  const panelIds = ['stored_panel_overview', 'stored_panel_freshness', 'stored_panel_alerts', 'stored_panel_warehouse', 'stored_panel_genai'];
  panelIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  });
  
  // Render overview
  const overviewEl = document.getElementById('stored_panel_overview');
  if (overviewEl) {
    const translatedCrop = translateCropName(b.crop_type, _currentLang);
    overviewEl.innerHTML = `
      <div class="batch-info">
        <p><strong>${t_('batchId')}:</strong> #${b.id}</p>
        <p><strong>${t_('cropType')}:</strong> ${translatedCrop || '-'}</p>
        <p><strong>${t_('quantity')}:</strong> ${b.quantity} ${b.quantity_unit || 'kg'}</p>
        <p><strong>${t_('harvestDate')}:</strong> ${b.harvest_date || '-'}</p>
        <p><strong>${t_('daysSinceHarvest')}:</strong> ${b.days_since_harvest || '-'}</p>
        <p><strong>${t_('shelfLifeDays')}:</strong> ${b.max_shelf_life_days || '-'}</p>
      </div>
    `;
  }
  
  // Render freshness
  const freshnessEl = document.getElementById('stored_panel_freshness');
  if (freshnessEl) {
    const fresh = (b && typeof b.freshness_score === 'number') ? b.freshness_score : null;
    const freshness = (typeof fresh === 'number' && Number.isFinite(fresh)) ? `${Math.max(0, Math.min(1, fresh)).toFixed(2)}` : '';
    // Translate status
    let statusText = '';
    if (fresh >= 0.7) statusText = t_('good') || 'Good';
    else if (fresh >= 0.4) statusText = t_('moderate') || 'Moderate';
    else statusText = t_('poor') || 'Poor';
    freshnessEl.innerHTML = `
      <div class="freshness-info">
        <p><strong>${t_('freshnessScore')}:</strong> ${freshness}</p>
        <p><strong>${t_('status')}:</strong> ${statusText}</p>
      </div>
    `;
  }
  
  // Render alerts
  const alertsEl = document.getElementById('stored_panel_alerts');
  if (alertsEl) {
    const rawAlerts = Array.isArray(b.alerts) ? b.alerts : [];
    const effectiveAlerts = rawAlerts.length ? rawAlerts : _fallbackAlertLabels(b);
    
    const alerts = effectiveAlerts.length
      ? effectiveAlerts.map(a => {
          const label = String(a || '');
          const isGood = label.toLowerCase() === 'good';
          const isHigh = label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage');
          const isMedium = label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk');
          const isDelivered = label.toLowerCase() === 'delivered';
          const isPickupCompleted = label.toLowerCase().includes('pickup completed');
          const isPickupRequested = label.toLowerCase().includes('pickup requested');
          const alertClass = isGood ? 'low' : (isHigh ? 'high' : (isMedium ? 'medium' : (isDelivered ? 'delivered' : (isPickupCompleted ? 'pickup-completed' : (isPickupRequested ? 'pickup-requested' : 'medium')))));
          // Translate label
          let translatedLabel = label;
          if (label.toLowerCase() === 'good') translatedLabel = t_('good') || 'Good';
          else if (label.toLowerCase() === 'delivered') translatedLabel = t_('delivered') || 'Delivered';
          else if (label.toLowerCase().includes('pickup completed')) translatedLabel = t_('pickupCompleted') || 'Crop pickup completed';
          else if (label.toLowerCase().includes('pickup requested')) translatedLabel = t_('pickupRequested') || 'Pickup requested';
          else if (label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage')) translatedLabel = t_('highSpoilageRisk') || label;
          else if (label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk')) translatedLabel = t_('freshnessDeclining') || label;
          return `<span class="alert-badge ${alertClass}">${translatedLabel}</span>`;
        }).join(' ')
      : '<span style="color: var(--text-light);">No alerts</span>';
    
    alertsEl.innerHTML = alerts;
  }
  
  // Render warehouse info
  const warehouseEl = document.getElementById('stored_panel_warehouse');
  if (warehouseEl) {
    // Translate status and risk level
    const status = String(b.status || '').toUpperCase();
    let translatedStatus = b.status || 'SAFE';
    if (status === 'SAFE') translatedStatus = t_('safe') || 'SAFE';
    else if (status === 'HIGH') translatedStatus = t_('high') || 'HIGH';
    else if (status === 'GOOD') translatedStatus = t_('good') || 'GOOD';
    
    const riskLevel = String(b.farmer_risk_status || '').toUpperCase();
    let translatedRisk = b.farmer_risk_status || 'LOW';
    if (riskLevel === 'LOW') translatedRisk = t_('low') || 'LOW';
    else if (riskLevel === 'MEDIUM') translatedRisk = t_('medium') || 'MEDIUM';
    else if (riskLevel === 'HIGH') translatedRisk = t_('high') || 'HIGH';
    
    // Translate warehouse name
    const translatedWarehouse = translateWarehouseName(b.warehouse || 'Default Warehouse', _currentLang);
    
    warehouseEl.innerHTML = `
      <div class="warehouse-info">
        <p><strong>${t_('storageLocation')}:</strong> ${translatedWarehouse}</p>
        <p><strong>${t_('status')}:</strong> ${translatedStatus}</p>
        <p><strong>${t_('riskLevel')}:</strong> ${translatedRisk}</p>
      </div>
    `;
  }
  
  // Render GenAI recommendations
  const genaiEl = document.getElementById('stored_panel_genai');
  if (genaiEl) {
    // Load GenAI recommendation for stored batch
    loadGenAIForStoredBatch(b.id);
  }
}

// Function to highlight selected stored batch row
function highlightStoredBatchRow(batchId) {
  const storedTable = document.getElementById('storedBatchesTable');
  if (!storedTable) return;
  
  try {
    const rows = storedTable.querySelectorAll('tr[data-bid]');
    rows.forEach(r => {
      r.classList.remove('batch-row-selected');
    });
    
    if (batchId === null || batchId === undefined) return;
    
    const sel = storedTable.querySelector(`tr[data-bid="${String(batchId)}"]`);
    if (sel) {
      sel.classList.add('batch-row-selected');
    }
  } catch (e) {}
}

// Function to update stored pickup button state
function updateStoredPickupButtonState(b) {
  if (!b) return;
  
  const storedPickupBtn = document.getElementById('btnRequestPickupStored');
  if (!storedPickupBtn) return;
  
  try {
    const status = String((b && b.status) ? b.status : '').toUpperCase();
    const exportStatus = String((b && b.export_status) ? b.export_status : '').toUpperCase();
    const alertsArr = Array.isArray(b && b.alerts) ? b.alerts : [];
    const alertsUpper = alertsArr.map(x => String(x || '').trim().toUpperCase());

    const isSpoiled = status === 'SPOILED';
    const alertDelivered = alertsUpper.includes('DELIVERED') || alertsArr.some(x => String(x || '').trim() === 'Delivered');
    const alertPicked = alertsUpper.includes('REQUEST_PICKED_UP') || alertsUpper.includes('PICKED_UP');
    const delivered = !!(b && (b.is_delivered || status === 'DELIVERED' || exportStatus === 'DELIVERED' || alertDelivered));
    const alreadyPicked = exportStatus === 'REQUEST_PICKED_UP' || exportStatus === 'PICKED_UP' || alertPicked;

    const fresh = (b && typeof b.freshness_score === 'number') ? b.freshness_score : null;
    const freshVal = (typeof fresh === 'number' && Number.isFinite(fresh)) ? fresh : null;
    const isHighSpoilageRisk = status === 'HIGH SPOILAGE RISK';
    const canPickup = !isSpoiled && !isHighSpoilageRisk;
    const spoilTip = 'Action disabled: Crop is spoiled and unfit for sale, storage, or transport.';
    const spoilPickupAlert = 'Crop is spoiled. Pickup is not allowed.';
    const highRiskTip = 'Action disabled: Pickup blocked due to HIGH SPOILAGE RISK.';
    const clearTip = '';
    
    if (delivered) {
      const tip = 'Request already processed: Delivered.';
      storedPickupBtn.disabled = true;
      storedPickupBtn.classList.add('force-disabled');
      storedPickupBtn.title = tip;
      storedPickupBtn.dataset.blockedMsg = 'Request already processed: Delivered.';
      return;
    }
    
    if (alreadyPicked) {
      const tip = 'Request already processed.';
      storedPickupBtn.disabled = true;
      storedPickupBtn.classList.add('force-disabled');
      storedPickupBtn.title = tip;
      storedPickupBtn.dataset.blockedMsg = 'Request already processed.';
      return;
    }

    storedPickupBtn.classList.remove('force-disabled');
    
    if (isSpoiled) {
      storedPickupBtn.disabled = true;
      storedPickupBtn.title = spoilTip;
      storedPickupBtn.dataset.blockedMsg = spoilPickupAlert;
    } else {
      storedPickupBtn.disabled = !canPickup;
      storedPickupBtn.title = canPickup ? clearTip : highRiskTip;
      storedPickupBtn.dataset.blockedMsg = canPickup ? '' : 'Pickup blocked: HIGH SPOILAGE RISK.';
    }
  } catch (e) {}
}

// Function to load GenAI recommendation for stored batch
async function loadGenAIForStoredBatch(batchId) {
  const ga = document.getElementById('stored_panel_genai');
  if (!ga) return;
  if (!batchId) { 
    ga.innerHTML = '<div style="color: var(--text-light);">Recommendation unavailable for this stored batch.</div>'; 
    return; 
  }
  
  ga.textContent = t_('loading') || 'Loading recommendation...';
  try {
    const res = await fetch(`/api/farmer/batches/${encodeURIComponent(batchId)}/genai`, {method:'POST', headers:H, body: JSON.stringify({})});
    if (res.status === 401 || res.status === 422) { 
      _authFail(); 
      return; 
    }
    
    if (!res.ok) {
      ga.innerHTML = '<div style="color: var(--text-light);">Recommendation unavailable for this stored batch.</div>';
      return;
    }
    
    const j = await res.json();
    let rec = (j && j.recommendation) ? String(j.recommendation) : '';
    let exp = (j && j.explanation) ? String(j.explanation) : '';
    
    // Translate AI recommendations if language is not English
    if (_currentLang !== 'en' && typeof aiTranslator !== 'undefined') {
      try {
        if (rec) {
          rec = await aiTranslator.translateText(rec, _currentLang);
        }
        if (exp) {
          exp = await aiTranslator.translateText(exp, _currentLang);
        }
      } catch (e) {
        console.warn('AI recommendation translation failed:', e);
        // Fallback: use original English text
      }
    }
    
    if (rec || exp) {
      ga.innerHTML = `<div><b>${t_('recommendation')}:</b> ${rec || 'No specific recommendation available.'}</div>` +
        `<div style="margin-top:4px"><b>${t_('explanation')}:</b> ${exp || 'No explanation available.'}</div>`;
    } else {
      ga.innerHTML = '<div style="color: var(--text-light);">Recommendation unavailable for this stored batch.</div>';
    }
  } catch (e) {
    ga.innerHTML = '<div style="color: var(--text-light);">Recommendation unavailable for this stored batch.</div>';
  }
}

// Function to display submitted batch details
function displaySubmittedBatchDetails(submittedData) {
  const submittedSection = document.getElementById('submittedBatchSection');
  
  // Show the submitted batch section
  if (submittedSection) {
    submittedSection.style.display = 'block';
  }
  
  // Add new batch to the submitted batches list
  _submittedBatches.push(submittedData);
  
  // Render all submitted batches
  renderSubmittedBatchesTable();
  
  // Try to get the complete batch data after a delay
  setTimeout(async () => {
    try {
      const res = await fetch('/api/farmer/batches', {headers:H});
      if (res.ok) {
        const batches = await res.json();
        if (Array.isArray(batches) && batches.length > 0) {
          // Get most recent batch (highest ID)
          const mostRecentBatch = batches.reduce((prev, current) => 
            (current.id > prev.id) ? current : prev
          );
          
          // Update the last submitted batch with complete data
          if (_submittedBatches.length > 0) {
            _submittedBatches[_submittedBatches.length - 1] = mostRecentBatch;
            renderSubmittedBatchesTable();
          }
        }
      }
    } catch (error) {
      console.log('Could not fetch complete batch data:', error);
    }
  }, 1000);
}

// Function to render all submitted batches table
function renderSubmittedBatchesTable() {
  const tableBody = document.getElementById('submittedBatchTableBody');
  if (!tableBody) return;
  
  if (_submittedBatches.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-light);">No submitted batches yet.</td></tr>';
    return;
  }
  
  // Create table rows for all submitted batches (newest first)
  const tableRows = _submittedBatches.slice().reverse().map(batchData => {
    const batchRow = createSubmittedBatchRow(batchData);
    return batchRow;
  }).join('');
  
  tableBody.innerHTML = tableRows;
  
  // Add click handlers to all submitted batch rows
  const submittedRows = tableBody.querySelectorAll('tr[data-bid]');
  submittedRows.forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function() {
      const batchId = this.getAttribute('data-bid');
      const batchData = _submittedBatches.find(b => b.id == batchId);
      
      if (batchData && batchData.id) {
        selectBatch(batchData);
      }
    });
  });
}

// Function to create submitted batch table row
function createSubmittedBatchRow(batchData) {
  if (!batchData) return '';
  
  // Extract batch information
  const batchId = batchData.id || 'Processing...';
  const crop = batchData.crop_type || batchData.crop || '-';
  const quantity = batchData.quantity ? `${batchData.quantity} ${batchData.quantity_unit || 'kg'}` : '-';
  const harvestDate = batchData.harvest_date || '-';
  
  // Calculate days since harvest (placeholder for now)
  const daysSinceHarvest = batchData.days_since_harvest || calculateDaysSinceHarvest(harvestDate);
  
  // Freshness - use same logic as main batches table
  const fresh = (batchData && typeof batchData.freshness_score === 'number') ? batchData.freshness_score : null;
  const freshness = (typeof fresh === 'number' && Number.isFinite(fresh)) ? `${Math.max(0, Math.min(1, fresh)).toFixed(2)}` : '';
  
  // Risk status
  const riskStatus = batchData.farmer_risk_status || batchData.status || 'SAFE';
  const riskBadge = createRiskBadge(riskStatus);
  
  // Handle alerts properly - use the same logic as stored batches
  const rawAlerts = Array.isArray(batchData.alerts) ? batchData.alerts : [];
  const effectiveAlerts = rawAlerts.length ? rawAlerts : _fallbackAlertLabels(batchData);
  
  // Create styled alert badges
  const alerts = effectiveAlerts.length
    ? effectiveAlerts.map(a=> {
        const label = String(a||'');
        const isGood = label.toLowerCase() === 'good';
        const isHigh = label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage');
        const isMedium = label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk');
        const isDelivered = label.toLowerCase() === 'delivered';
        const isPickupCompleted = label.toLowerCase().includes('pickup completed');
        const isPickupRequested = label.toLowerCase().includes('pickup requested');
        const alertClass = isGood ? 'low' : (isHigh ? 'high' : (isMedium ? 'medium' : (isDelivered ? 'delivered' : (isPickupCompleted ? 'pickup-completed' : (isPickupRequested ? 'pickup-requested' : 'medium')))));
        return `<span class="alert-badge ${alertClass}">${label}</span>`;
      }).join(' ')
    : '';
  
  return `<tr data-bid="${batchData.id || 'pending'}" style="cursor:pointer">
    <td>${batchId}</td>
    <td>${crop}</td>
    <td>${quantity}</td>
    <td>${harvestDate}</td>
    <td style="text-align: center;">${daysSinceHarvest}</td>
    <td style="text-align: center;">${freshness}</td>
    <td>${riskBadge}</td>
    <td>${alerts}</td>
  </tr>`;
}

// Helper function to create risk badge HTML
function createRiskBadge(riskStatus) {
  const status = String(riskStatus || '').toUpperCase();
  let badgeClass = 'safe';
  let displayText = status;
  
  if (status.includes('HIGH')) {
    badgeClass = 'high';
    displayText = 'HIGH';
  } else if (status.includes('MEDIUM')) {
    badgeClass = 'medium';
    displayText = 'MEDIUM';
  } else if (status.includes('SAFE')) {
    badgeClass = 'safe';
    displayText = 'SAFE';
  }
  
  return `<span class="risk-badge ${badgeClass}">${displayText}</span>`;
}

// Helper function to calculate days since harvest (placeholder)
function calculateDaysSinceHarvest(harvestDate) {
  if (!harvestDate) return 0;
  
  try {
    const harvest = new Date(harvestDate);
    const today = new Date();
    const diffTime = Math.abs(today - harvest);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  } catch (error) {
    return 0;
  }
}

// Function to enforce button states for all batches
function enforcePickupButtonStates() {
  // Force check all Request Pickup buttons and disable if needed
  const allPickupButtons = document.querySelectorAll('[id*="RequestPickup"], [id*="requestPickup"]');
  
  allPickupButtons.forEach(button => {
    if (!button) return;
    
    // Get current selected batch data
    let currentBatch = null;
    
    // Try to get batch data from different sources
    if (typeof _selectedStoredBatchId !== 'undefined' && _selectedStoredBatchId !== null) {
      // For stored batches, we need to find the batch in the stored batches data
      const storedBatchRows = document.querySelectorAll('#storedBatchesTable tr[data-bid]');
      const selectedRow = document.querySelector(`#storedBatchesTable tr[data-bid="${_selectedStoredBatchId}"]`);
      if (selectedRow) {
        // Extract status from the row or use a global variable
        const statusCells = selectedRow.querySelectorAll('td');
        if (statusCells.length > 6) {
          const statusText = statusCells[6].textContent.trim().toUpperCase();
          if (statusText === 'DELIVERED' || statusText === 'CROP PICKUP COMPLETED') {
            forceDisableButton(button, statusText);
            return;
          }
        }
      }
    }
    
    if (typeof _selectedBatchId !== 'undefined' && _selectedBatchId !== null) {
      // For main dashboard batches
      const mainBatchRows = document.querySelectorAll('#batches tr[data-bid]');
      const selectedRow = document.querySelector(`#batches tr[data-bid="${_selectedBatchId}"]`);
      if (selectedRow) {
        const statusCells = selectedRow.querySelectorAll('td');
        if (statusCells.length > 6) {
          const statusText = statusCells[6].textContent.trim().toUpperCase();
          if (statusText === 'DELIVERED' || statusText === 'CROP PICKUP COMPLETED') {
            forceDisableButton(button, statusText);
            return;
          }
        }
      }
    }
  });
}

// Function to forcefully disable a button
function forceDisableButton(button, status) {
  if (!button) return;
  
  // Force disable with multiple methods
  button.disabled = true;
  button.setAttribute('disabled', 'disabled');
  button.style.pointerEvents = 'none';
  button.style.opacity = '0.5';
  button.style.cursor = 'not-allowed';
  
  // Set appropriate tooltip
  const tip = status === 'DELIVERED' ? 'Action disabled: Delivered' : 'Action disabled: Crop pickup completed';
  button.title = tip;
  button.setAttribute('title', tip);
  
  // Store blocked message
  button.dataset.blockedMsg = status === 'DELIVERED' ? 'Delivered.' : 'Crop pickup completed.';
  
  // Add visual disabled class
  button.classList.add('force-disabled');
}

// Function to check if button should be disabled based on status
function shouldDisablePickupButton(status) {
  const statusUpper = String(status || '').toUpperCase();
  return statusUpper === 'DELIVERED' || statusUpper === 'CROP PICKUP COMPLETED';
}

// Helper function to find batch by ID
function findBatchById(batchId) {
  // This would need access to the batches data
  // For now, let the existing functions handle it
  return null;
}

// Helper function to find stored batch by ID  
function findStoredBatchById(batchId) {
  // This would need access to the stored batches data
  // For now, let the existing functions handle it
  return null;
}

// AI Output Translation Helper
function translateAIOutput(text) {
  if (!text) return text;
  if (_currentLang === 'en') return text;
  
  // Common patterns in AI recommendations
  const patterns = [
    // Immediate action patterns
    { en: /immediate action required/gi, hi: 'तत्काल कार्रवाई आवश्यक', te: 'వెంటనే చర్య అవసరం', ta: 'உடனடி நடவடிக்கை தேவை', kn: 'ತಕ್ಷಣ ಕ್ರಮ ಅಗತ್ಯ' },
    { en: /move batch to salvage/gi, hi: 'बैच को बचाव में स्थानांतरित करें', te: 'బ్యాచ్‌ను రక్షణకు తరలించండి', ta: 'தொகுதியை மீட்புக்கு நகர்த்தவும்', kn: 'ಬ್ಯಾಚ್‌ನ್ನು ರಕ್ಷಣೆಗೆ ಸ್ಥಳಾಂತರಿಸಿ' },
    { en: /discard immediately/gi, hi: 'तुरंत निपटान करें', te: 'వెంటనే విస్మరించండి', ta: 'உடனடியாக நிராகரிக்கவும்', kn: 'ತಕ್ಷಣ ತ್ಯಜಿಸಿ' },
    // Risk patterns
    { en: /high spoilage risk/gi, hi: 'उच्च खराब होने का जोखिम', te: 'అధిక చెడిపోయే అపాయం', ta: 'உயர் சிதைவு ஆபத்து', kn: 'ಉನ್ನತ ಹಾಳಾಗುವ ಅಪಾಯ' },
    { en: /freshness declining/gi, hi: 'ताजगी घट रही है', te: 'తాజాదనం తగ్గుతోంది', ta: 'புதுமை குறைந்து வருகிறது', kn: 'ತಾಜಾತನ ಕಡಿಮೆಯಾಗುತ್ತಿದೆ' },
    { en: /below safe threshold/gi, hi: 'सुरक्षित सीमा से नीचे', te: 'సురక్షిత మితి కంటే తక్కువ', ta: 'பாதுகாப்பான வரம்புக்கு கீழே', kn: 'ಸುರಕ್ಷಿತ ಮಿತಿಗಿಂತ ಕಡಿಮೆ' },
    // Temperature/Humidity patterns
    { en: /temperature.*out.*optimal/gi, hi: 'तापमान इष्टतम सीमा से बाहर', te: 'ఉష్ణోగ్రత అనుకూల పరిధిలో లేదు', ta: 'வெப்பநிலை உகந்த வரம்பிற்கு வெளியே', kn: 'ತಾಪಮಾನ ಸೂಕ್ತ ಪರಿಧಿಯಲ್ಲಿ ಇಲ್ಲ' },
    { en: /humidity.*out.*optimal/gi, hi: 'आर्द्रता इष्टतम सीमा से बाहर', te: 'తేమ అనుకూల పరిధిలో లేదు', ta: 'ஈரப்பதம் உகந்த வரம்பிற்கு வெளியே', kn: 'ಆರ್ದ್ರತೆ ಸೂಕ್ತ ಪರಿಧಿಯಲ್ಲಿ ಇಲ್ಲ' },
    // Storage patterns
    { en: /storage incompatible/gi, hi: 'भंडारण असंगत', te: 'నిల్వ అనుకూలంగా లేదు', ta: 'சேமிப்பு பொருத்தமற்றது', kn: 'ಸಂಗ್ರಹಣೆ ಅನುಕೂಲವಾಗಿಲ್ಲ' },
    { en: /warehouse.*not suitable/gi, hi: 'गोदाम उपयुक्त नहीं', te: 'గోదాము అనుకూలంగా లేదు', ta: 'கிடங்கு பொருத்தமானதல்ல', kn: 'ಗೋದಾಮು ಸೂಕ್ತವಾಗಿಲ್ಲ' },
    // Action patterns
    { en: /recommend immediate dispatch/gi, hi: 'तत्काल प्रेषण की सिफारिश', te: 'వెంటనే పంపిణీకి సిఫార్సు', ta: 'உடனடி அனுப்புதலை பரிந்துரைக்கவும்', kn: 'ತಕ್ಷಣ ರವಾನೆಗೆ ಶಿಫಾರಸು' },
    { en: /monitor closely/gi, hi: 'करीब से निगरानी करें', te: 'సన్నిహితంగా పర్యవేక్షించండి', ta: 'கவனமாக கண்காணிக்கவும்', kn: 'ಹತ್ತಿರವಾಗಿ ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿ' },
    { en: /conditions favorable/gi, hi: 'परिस्थितियां अनुकूल', te: 'పరిస్థితులు అనుకూలంగా ఉన్నాయి', ta: 'நிலைமைகள் சாதகமாக உள்ளன', kn: 'ಪರಿಸ್ಥಿತಿಗಳು ಅನುಕೂಲವಾಗಿವೆ' },
  ];
  
  let translated = text;
  patterns.forEach(p => {
    if (p[_currentLang]) {
      translated = translated.replace(p.en, p[_currentLang]);
    }
  });
  
  return translated;
}

// Additional translation keys needed
const AdditionalTranslations = {
  loading: {
    en: "Loading recommendation...",
    hi: "सिफारिश लोड हो रही है...",
    te: "సిఫార్సు లోడ్ అవుతోంది...",
    ta: "பரிந்துரை லோட் செய்துகொண்டிருக்கிறது...",
    kn: "ಸಲಹೆಯನ್ನು ಲೋಡ್ ಮಾಡುತ್ತಿದೆ..."
  },
  // Add more translation keys as needed
};

// Call enforcement function after page load and after batch selection
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(enforcePickupButtonStates, 100);
  
  // Add aggressive event listener to block all pickup button clicks
  document.addEventListener('click', function(event) {
    const target = event.target;
    
    // Check if clicked element is a Request Pickup button
    if (target && (
      target.id === 'btnRequestPickup' || 
      target.id === 'btnRequestPickupStored' ||
      target.closest('#btnRequestPickup') ||
      target.closest('#btnRequestPickupStored')
    )) {
      const button = target.id === 'btnRequestPickup' ? target : 
                     target.id === 'btnRequestPickupStored' ? target :
                     target.closest('#btnRequestPickup') || 
                     target.closest('#btnRequestPickupStored');
      
      // Check if button should be disabled
      if (button && (button.disabled || button.classList.contains('force-disabled'))) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        
        // Show appropriate message
        const msg = button.dataset.blockedMsg || 'Action disabled.';
        if (msg) {
          alert(msg);
        }
        return false;
      }
    }
  }, true); // Use capture phase to catch events early
  
  // Also enforce button states periodically
  setInterval(enforcePickupButtonStates, 1000);
}); // Close DOMContentLoaded

// Also call after any batch selection
const originalSelectBatch = selectBatch;
if (typeof originalSelectBatch === 'function') {
  selectBatch = function(b) {
    originalSelectBatch(b);
    setTimeout(enforcePickupButtonStates, 50);
  };
}

const originalSelectStoredBatch = selectStoredBatch;
if (typeof originalSelectStoredBatch === 'function') {
  selectStoredBatch = function(b) {
    originalSelectStoredBatch(b);
    setTimeout(enforcePickupButtonStates, 50);
  };
}
function calculateFreshness(daysSinceHarvest) {
  if (daysSinceHarvest <= 3) return '0.9';
  if (daysSinceHarvest <= 7) return '0.7';
  if (daysSinceHarvest <= 14) return '0.5';
  return '0.3';
}

// Function to update selected batch details in the "Selected Batch Details" section
function updateSelectedBatchDetails(batchData) {
  if (!batchData) return;
  
  // Update the selected batch ID tracking
  _selectedBatchId = batchData.id;
  
  // Find and update the selected batch details section
  const selectedBatchSection = document.querySelector('.selected-batch-details');
  if (!selectedBatchSection) return;
  
  // Update the batch ID in the selected batch details
  const selectedBatchIdEl = selectedBatchSection.querySelector('.batch-id');
  if (selectedBatchIdEl) {
    selectedBatchIdEl.textContent = `Batch #${batchData.id}`;
  }
  
  // Update other batch details
  const cropEl = selectedBatchSection.querySelector('.crop-name');
  if (cropEl) {
    cropEl.textContent = batchData.crop_type || batchData.crop || '-';
  }
  
  const quantityEl = selectedBatchSection.querySelector('.quantity');
  if (quantityEl) {
    const unit = batchData.quantity_unit || 'kg';
    quantityEl.textContent = `${batchData.quantity} ${unit}`;
  }
  
  const harvestDateEl = selectedBatchSection.querySelector('.harvest-date');
  if (harvestDateEl) {
    harvestDateEl.textContent = batchData.harvest_date || '-';
  }
  
  const daysEl = selectedBatchSection.querySelector('.days-since-harvest');
  if (daysEl) {
    const days = batchData.days_since_harvest || calculateDaysSinceHarvest(batchData.harvest_date);
    daysEl.textContent = days;
  }
  
  const freshnessEl = selectedBatchSection.querySelector('.freshness-score');
  if (freshnessEl) {
    // Use same logic as main batches table
    const fresh = (batchData && typeof batchData.freshness_score === 'number') ? batchData.freshness_score : null;
    const freshness = (typeof fresh === 'number' && Number.isFinite(fresh)) ? `${Math.max(0, Math.min(1, fresh)).toFixed(2)}` : '';
    freshnessEl.textContent = freshness;
  }
  
  const statusEl = selectedBatchSection.querySelector('.status');
  if (statusEl) {
    statusEl.textContent = batchData.status || 'SAFE';
  }
  
  // Update alerts in the selected batch section
  const alertsEl = selectedBatchSection.querySelector('.alerts');
  if (alertsEl) {
    const rawAlerts = Array.isArray(batchData.alerts) ? batchData.alerts : [];
    const effectiveAlerts = rawAlerts.length ? rawAlerts : _fallbackAlertLabels(batchData);
    
    const alerts = effectiveAlerts.length
      ? effectiveAlerts.map(a=> {
          const label = String(a||'');
          const isGood = label.toLowerCase() === 'good';
          const isHigh = label.toLowerCase().includes('high') || label.toLowerCase().includes('spoilage');
          const isMedium = label.toLowerCase().includes('declining') || label.toLowerCase().includes('risk');
          const isDelivered = label.toLowerCase() === 'delivered';
          const isPickupCompleted = label.toLowerCase().includes('pickup completed');
          const isPickupRequested = label.toLowerCase().includes('pickup requested');
          const alertClass = isGood ? 'low' : (isHigh ? 'high' : (isMedium ? 'medium' : (isDelivered ? 'delivered' : (isPickupCompleted ? 'pickup-completed' : (isPickupRequested ? 'pickup-requested' : 'medium')))));
          return `<span class="alert-badge ${alertClass}">${label}</span>`;
        }).join(' ')
      : '<span style="color: var(--text-light);">No alerts</span>';
    
    alertsEl.innerHTML = alerts;
  }
  
  // Update recommendations
  const recommendationsEl = selectedBatchSection.querySelector('.recommendations');
  if (recommendationsEl) {
    const recommendations = generateRecommendations(batchData);
    recommendationsEl.innerHTML = recommendations;
  }
  
  // Show the selected batch section if it's hidden
  if (selectedBatchSection.style.display === 'none') {
    selectedBatchSection.style.display = 'block';
  }
}

// Function to highlight the selected row
function highlightSelectedRow(selectedRow) {
  // Remove previous selections in submitted batch table
  const submittedTable = document.getElementById('submittedBatchTable');
  if (submittedTable) {
    const allRows = submittedTable.querySelectorAll('tbody tr');
    allRows.forEach(row => {
      row.style.backgroundColor = '';
      row.style.border = '';
    });
  }
  
  // Remove previous selections in main batches table
  const mainTable = document.querySelector('.batches-table');
  if (mainTable) {
    const allRows = mainTable.querySelectorAll('tbody tr');
    allRows.forEach(row => {
      row.style.backgroundColor = '';
      row.style.border = '';
    });
  }
  
  // Highlight the selected row
  if (selectedRow) {
    selectedRow.style.backgroundColor = 'var(--bg-light)';
    selectedRow.style.borderLeft = '4px solid var(--primary-color)';
  }
}

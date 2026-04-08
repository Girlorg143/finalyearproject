const t=localStorage.getItem('access_token'); 
const userRole=localStorage.getItem('user_role');
const warehouseLocation=localStorage.getItem('warehouse_location');

// Access control check
if(!t || userRole !== 'warehouse' || !warehouseLocation) {
    localStorage.clear();
    location.href='/';
}

function _escapeHtml(s){
  const t = String(s ?? '');
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function _riskAwareActionButtons(b, remDays){
  const riskRaw = String(b && b.risk_status ? b.risk_status : '').trim().toUpperCase();
  const d = (typeof remDays === 'number') ? remDays : parseFloat(remDays);
  const batchId = b && b.id ? String(b.id) : '';

  // Determine risk state
  let riskState = '';
  if(Number.isFinite(d) && d > 2 && (riskRaw === 'SAFE' || riskRaw === 'LOW')){
    riskState = 'SAFE';
  } else if(Number.isFinite(d) && d > 0 && d <= 7 && (riskRaw === 'RISK' || riskRaw === 'MEDIUM')){
    riskState = 'MEDIUM';
  } else if((!Number.isFinite(d) || d <= 0) && (riskRaw === 'HIGH' || riskRaw === 'CRITICAL')){
    riskState = 'CRITICAL';
  }

  // Generate buttons based on risk state
  let buttons = '';
  
  if(riskState === 'SAFE'){
    buttons = '';
  } else if(riskState === 'CRITICAL'){
    // CRITICAL: Add Emergency Dispatch button only, disable other actions
    buttons = `<button type="button" class="action-btn" data-flag-emergency="${batchId}">Emergency Dispatch</button>`;
  } else {
    buttons = '';
  }

  return buttons;
}

function _renderRecoPanel(b, key, colspan){
  const id = `reco_${key}_${String(b && b.id ? b.id : '')}`;
  const btn = `<button type="button" class="action-btn" data-reco-toggle="${id}" data-batch-id="${String(b && b.id ? b.id : '')}" data-scope="${String(key||'')}">View</button>`;
  const contentId = `${id}_content`;
  const body = `<div id="${contentId}">Loading...</div>`;

  const row = (
    `<tr id="${id}" style="display:none">`+
      `<td colspan="${Number.isFinite(colspan) ? colspan : 11}" style="background:#f9fafb;color:#374151;padding:16px;border-top:1px solid #e5e7eb">`+
        `${body}`+
      `</td>`+
    `</tr>`
  );
  return { btn, row, toggleId: id, contentId };
}

function _truncate(s, maxLen){
  const t = String(s ?? '');
  if(t.length <= maxLen) return t;
  return t.slice(0, maxLen - 1) + '…';
}

const H={'Content-Type':'application/json','Authorization':'Bearer '+t};

async function acceptBatchWithOptions(batchId, opts){
  const msg = document.getElementById('warehouseMsg');
  if(msg) msg.textContent = '';
  const payload = Object.assign({ batch_id: batchId }, (opts||{}));
  const res = await fetch('/api/warehouse/accept', {method:'POST', headers:H, body: JSON.stringify(payload)});
  if(res.status===401 || res.status===422){ _authFail(); return; }
  if(!res.ok){
    let detail='';
    try{ detail = await res.text(); }catch(_){ detail=''; }
    if(msg) msg.textContent = detail || `Failed to accept batch (${res.status})`;
    return;
  }
  if(msg) msg.textContent = 'Batch accepted into warehouse storage.';
  await loadDashboard();
}

// Update warehouse header
document.addEventListener('DOMContentLoaded', function() {
    const header = document.getElementById('warehouseHeader');
    const userInfo = document.getElementById('userInfo');
    const welcomeMessage = document.getElementById('welcomeMessage');
    
    if (header) {
        header.textContent = `Welcome to ${warehouseLocation}`;
    }
    
    if (welcomeMessage) {
        welcomeMessage.textContent = 'Warehouse Dashboard';
    }
    
    if (userInfo) {
        userInfo.textContent = '';
    }
    
    // Initialize with no sections visible by default
    // Sections will show only after button click
});

// Navigation functions
function showStoredBatches() {
    // Remove active state from all navigation buttons
    document.querySelectorAll('.nav-action-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Remove active class from all sections
    document.getElementById('storedBatchesSection').classList.remove('active');
    document.getElementById('salvageBatchesSection').classList.remove('active');
    
    // Add active state to stored batches button
    const storedBtn = Array.from(document.querySelectorAll('.nav-action-btn')).find(btn => 
        btn.textContent.trim().includes('Stored Batches')
    );
    if (storedBtn) {
        storedBtn.classList.add('active');
    }
    
    // Add active class to stored batches section
    const storedSection = document.getElementById('storedBatchesSection');
    if (storedSection) {
        storedSection.classList.add('active');
    }
    
    // Update page heading and subtitle
    const welcomeMessage = document.getElementById('welcomeMessage');
    if (welcomeMessage) {
        welcomeMessage.textContent = 'Stored Batches';
    }
    
    // Hide other sections and show only stored batches
    const sections = [
        { id: 'warehouseEnvironmentSection', hide: true },
        { id: 'incomingBatchesSection', hide: true },
        { id: 'storedBatchesSection', hide: false },
        { id: 'salvageBatchesSection', hide: true }
    ];
    
    sections.forEach(section => {
        const element = document.getElementById(section.id);
        if (element) {
            element.style.display = section.hide ? 'none' : 'block';
        }
    });
    
    // Show "Go to Dashboard" button in stored batches view
    const goToDashboardBtn = document.querySelector('.go-to-dashboard-btn');
    if (goToDashboardBtn) {
        goToDashboardBtn.style.display = 'flex';
        goToDashboardBtn.classList.add('show');
    }
    
    // Scroll to stored batches section
    const storedSectionScroll = document.getElementById('storedBatchesSection');
    if (storedSectionScroll) {
        storedSectionScroll.scrollIntoView({ behavior: 'smooth' });
    }
}

function showSalvageBatches() {
    // Remove active state from all navigation buttons
    document.querySelectorAll('.nav-action-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Remove active class from all sections
    document.getElementById('storedBatchesSection').classList.remove('active');
    document.getElementById('salvageBatchesSection').classList.remove('active');
    
    // Add active state to salvage batches button
    const salvageBtn = Array.from(document.querySelectorAll('.nav-action-btn')).find(btn => 
        btn.textContent.trim().includes('Salvage Batches')
    );
    if (salvageBtn) {
        salvageBtn.classList.add('active');
    }
    
    // Add active class to salvage batches section
    const salvageSection = document.getElementById('salvageBatchesSection');
    if (salvageSection) {
        salvageSection.classList.add('active');
    }
    
    // Update page heading and subtitle
    const welcomeMessage = document.getElementById('welcomeMessage');
    if (welcomeMessage) {
        welcomeMessage.textContent = 'Salvage Batches';
    }
    
    // Hide other sections and show only salvage batches
    const sections = [
        { id: 'warehouseEnvironmentSection', hide: true },
        { id: 'incomingBatchesSection', hide: true },
        { id: 'storedBatchesSection', hide: true },
        { id: 'salvageBatchesSection', hide: false }
    ];
    
    sections.forEach(section => {
        const element = document.getElementById(section.id);
        if (element) {
            element.style.display = section.hide ? 'none' : 'block';
        }
    });
    
    // Show "Go to Dashboard" button in salvage batches view
    const goToDashboardBtn = document.querySelector('.go-to-dashboard-btn');
    if (goToDashboardBtn) {
        goToDashboardBtn.style.display = 'flex';
        goToDashboardBtn.classList.add('show');
    }
    
    // Scroll to salvage batches section
    const salvageSectionScroll = document.getElementById('salvageBatchesSection');
    if (salvageSectionScroll) {
        salvageSectionScroll.scrollIntoView({ behavior: 'smooth' });
    }
}

function showNormalDashboard() {
    // Hide all batch sections and show main dashboard
    const sections = [
        { id: 'warehouseEnvironmentSection', hide: false },
        { id: 'incomingBatchesSection', hide: false },
        { id: 'storedBatchesSection', hide: true },
        { id: 'salvageBatchesSection', hide: true }
    ];
    
    sections.forEach(section => {
        const element = document.getElementById(section.id);
        if (element) {
            element.style.display = section.hide ? 'none' : 'block';
        }
    });
    
    // Remove active classes from all sections
    document.getElementById('storedBatchesSection').classList.remove('active');
    document.getElementById('salvageBatchesSection').classList.remove('active');
    
    // Hide "Go to Dashboard" button in main dashboard view
    const goToDashboardBtn = document.querySelector('.go-to-dashboard-btn');
    if (goToDashboardBtn) {
        goToDashboardBtn.style.display = 'none';
        goToDashboardBtn.classList.remove('show');
    }
    
    // Update page heading
    const welcomeMessage = document.getElementById('welcomeMessage');
    if (welcomeMessage) {
        welcomeMessage.textContent = 'Warehouse Dashboard';
    }
    
    // Remove active state from all navigation buttons
    document.querySelectorAll('.nav-action-btn').forEach(btn => {
        btn.classList.remove('active');
    });
}

function _authFail(){
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  localStorage.removeItem('warehouse_location');
  location.href='/';
}

function _fmtPct01(v){
  const n = typeof v === 'number' ? v : parseFloat(v);
  if(!Number.isFinite(n)) return '';
  return Math.round(n * 100) + '%';
}

function _clamp01(x){
  const n = (typeof x === 'number') ? x : parseFloat(x);
  if(!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function _riskFromFreshnessWarehouse(f){
  const pct = Math.round(_clamp01(f) * 100);
  if(pct > 60) return 'SAFE';
  if(pct >= 40) return 'MEDIUM';
  return 'HIGH';
}

function _riskBadgeHtml(risk){
  const r = String(risk||'').toUpperCase();
  const bg = (r === 'SAFE') ? '#16a34a' : (r === 'MEDIUM' ? '#f59e0b' : (r === 'HIGH' ? '#ef4444' : '#6b7280'));
  const txt = r || '';
  return txt ? `<span style="display:inline-block;padding:3px 10px;border-radius:999px;color:#fff;background:${bg};font-weight:700;font-size:12px;letter-spacing:0.2px">${txt}</span>` : '';
}

function _daysBadgeHtml(days){
  const d = (typeof days === 'number') ? days : parseFloat(days);
  if(!Number.isFinite(d)) return '<span>-</span>';
  const v = Math.max(0, Math.round(d));
  const label = `${v} day${v===1?'':'s'}`;
  const color = (v <= 3) ? '#ef4444' : (v <= 7 ? '#f59e0b' : '#16a34a');
  return `<span style="color: ${color}; font-weight: 600; font-size: 0.875rem;">${label} remaining</span>`;
}

function _computeAdjustedDailyDecayRate(b){
  const baseKph0 = (typeof b.decay_rate_per_hour === 'number') ? b.decay_rate_per_hour : parseFloat(b.decay_rate_per_hour);
  const baseDaily = (Number.isFinite(baseKph0) && baseKph0 > 0) ? (baseKph0 * 24.0) : 0;

  const t = (typeof b.warehouse_temperature_c === 'number') ? b.warehouse_temperature_c : parseFloat(b.warehouse_temperature_c);
  const h = (typeof b.warehouse_humidity_pct === 'number') ? b.warehouse_humidity_pct : parseFloat(b.warehouse_humidity_pct);
  const optT = (typeof b.optimal_temperature_c === 'number') ? b.optimal_temperature_c : parseFloat(b.optimal_temperature_c);
  const optH = (typeof b.optimal_humidity_pct === 'number') ? b.optimal_humidity_pct : parseFloat(b.optimal_humidity_pct);

  const tDev = (Number.isFinite(t) && Number.isFinite(optT)) ? Math.abs(t - optT) : 0;
  const hDev = (Number.isFinite(h) && Number.isFinite(optH)) ? Math.abs(h - optH) : 0;

  // If within optimal band, keep base decay. Otherwise increase proportionally.
  // Deterministic multipliers chosen to be visible but bounded.
  const within = (tDev <= 1.0) && (hDev <= 5.0);
  if(within) return baseDaily;

  const factor = 1 + (0.06 * Math.min(10, tDev)) + (0.01 * Math.min(30, hDev));
  return baseDaily * factor;
}

function _computeRemainingSafeDays(b){
  const spoilageThreshold = 0.40;
  const cur = _clamp01(b && b.freshness);
  const daily = _computeAdjustedDailyDecayRate(b);
  if(!(daily > 0)) return null;
  const rem = (cur - spoilageThreshold) / daily;
  if(!Number.isFinite(rem)) return null;
  return Math.max(0, rem);
}


function _warehouseDecisionGuidanceHtml(b, remDays){
  const d = (typeof remDays === 'number') ? remDays : parseFloat(remDays);

  let mode = '';
  let text = '';

  // Recommendation logic based on remaining safe days
  if(Number.isFinite(d) && d > 2){
    mode = 'safe';
    text = 'Maintain current storage conditions.';
  } else if(Number.isFinite(d) && d > 1){
    mode = 'safe';
    text = 'Optimize temperature and humidity.';
  } else if(Number.isFinite(d) && d > 0){
    mode = 'medium';
    text = 'Urgent action required to prevent spoilage.';
  } else {
    // 0 or negative days - shelf life exhausted
    mode = 'high';
    text = 'Move to salvage / discard immediately.';
  }

  const color = mode === 'safe' ? '#16a34a' : (mode === 'medium' ? '#f59e0b' : '#ef4444');
  const bgColor = mode === 'safe' ? '#f0fdf4' : (mode === 'medium' ? '#fffbeb' : '#fef2f2');

  return (
    `<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; font-weight: 500; color: ${color}; font-size: 0.8rem; padding: 0.75rem; background: ${bgColor}; border-left: 3px solid ${color}; border-radius: 4px; margin: 0.5rem 0;">`+
      `<strong style="font-weight: 600; display: block; margin-bottom: 0.25rem;">Next-step guidance:</strong> ${_escapeHtml(text)}`+
    '</div>'
  );
}

function _ensureWarehouseSimModal(){
  let modal = document.getElementById('whSimModal');
  if(modal) return modal;
  modal = document.createElement('div');
  modal.id = 'whSimModal';
  modal.style.display = 'none';
  modal.style.position = 'fixed';
  modal.style.inset = '0';
  modal.style.background = 'rgba(0,0,0,0.40)';
  modal.style.zIndex = '10050';
  modal.style.alignItems = 'center';
  modal.style.justifyContent = 'center';
  modal.innerHTML =
    '<div style="background:#ffffff;border-radius:12px;max-width:900px;width:94%;max-height:86vh;overflow:auto;padding:20px;box-shadow:0 12px 40px rgba(0,0,0,0.15);border:1px solid #e5e7eb;">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;position:sticky;top:0;background:#ffffff;padding-bottom:12px;border-bottom:1px solid #e5e7eb;margin-bottom:16px;">'+
        '<h3 style="margin:0;color:#111827;font-size:18px;font-weight:600;">Warehouse Digital Twin – What-if Simulation</h3>'+
        '<button type="button" id="whSimClose" style="border:none;background:transparent;font-size:20px;line-height:20px;cursor:pointer;color:#6b7280;padding:4px;border-radius:4px;">×</button>'+
      '</div>'+
      '<div id="whSimBody" style="font-size:0.95em;line-height:1.45;color:#374151;"></div>'+
    '</div>';
  document.body.appendChild(modal);
  try{
    modal.addEventListener('click', (e)=>{
      if(e && e.target === modal){ modal.style.display = 'none'; }
    });
  }catch(e){}
  try{
    const x = modal.querySelector('#whSimClose');
    if(x){ x.addEventListener('click', ()=>{ modal.style.display = 'none'; }); }
  }catch(e){}
  return modal;
}

function _openWarehouseSimulationModal(b){
  const modal = _ensureWarehouseSimModal();
  const body = modal.querySelector('#whSimBody');
  if(!body) return;

  const cardStyle = 'border:1px solid #e5e7eb;border-radius:8px;padding:16px;background:#ffffff;color:#374151;margin-bottom:16px;';
  const cardTitleStyle = 'font-weight:600;margin:0 0 12px 0;font-size:16px;color:#111827;';
  const kvRow = (k0, v0)=>`<div style="display:flex;justify-content:space-between;gap:12px;margin:8px 0;"><div style="color:#6b7280;font-weight:500;">${k0}</div><div style="font-weight:600;text-align:right;color:#111827;">${v0}</div></div>`;
  const clamp = _clamp01;
  const pctTxt = (f)=>`${Math.round(clamp(f)*100)}%`;

  const curF = clamp(b && b.freshness);
  const curRisk = _riskFromFreshnessWarehouse(curF);
  const temp = (typeof b.warehouse_temperature_c === 'number') ? b.warehouse_temperature_c : parseFloat(b.warehouse_temperature_c);
  const hum = (typeof b.warehouse_humidity_pct === 'number') ? b.warehouse_humidity_pct : parseFloat(b.warehouse_humidity_pct);
  const remDays0 = _computeRemainingSafeDays(b);

  const baseDaily = _computeAdjustedDailyDecayRate(b);
  const baseHourly = (baseDaily > 0) ? (baseDaily / 24.0) : 0;

  const projectFreshness = ({ extraTempC=0, extraHumPct=0, hours=24 })=>{
    const hrs = (typeof hours === 'number') ? hours : parseFloat(hours);
    if(!Number.isFinite(hrs) || hrs <= 0) return curF;

    // Stress multipliers (deterministic): temperature affects decay more strongly than humidity.
    const tMul = 1 + (0.08 * Math.max(0, extraTempC));
    const hMul = 1 + (0.02 * Math.max(0, extraHumPct));
    const stressMul = tMul * hMul;

    const loss = baseHourly * hrs * stressMul;
    return clamp(curF - loss);
  };

  const remainingDaysAfter = (freshAfter)=>{
    const spoilageThreshold = 0.40;
    if(!(baseDaily > 0)) return null;
    const rem = (clamp(freshAfter) - spoilageThreshold) / baseDaily;
    if(!Number.isFinite(rem)) return null;
    return Math.max(0, rem);
  };

  const mkRow = (label, freshAfter, explanation)=>{
    const risk = _riskFromFreshnessWarehouse(freshAfter);
    const rem = remainingDaysAfter(freshAfter);
    const remTxt = (rem == null) ? '-' : `${Math.max(0, Math.round(rem))} days`;
    const riskColor = (risk === 'SAFE') ? '#16a34a' : (risk === 'MEDIUM' ? '#f59e0b' : '#ef4444');
    return {
      label,
      freshness: pctTxt(freshAfter),
      risk: `<span style="display:inline-block;padding:4px 8px;border-radius:6px;color:#fff;background:${riskColor};font-weight:600;font-size:12px;">${risk}</span>`,
      days: remTxt,
      explanation: String(explanation||'')
    };
  };

  const scenarioA = [
    mkRow('+2°C for 24h', projectFreshness({ extraTempC:2, extraHumPct:0, hours:24 }), 'Higher temperature accelerates enzymatic activity and moisture loss.'),
    mkRow('+5°C for 24h', projectFreshness({ extraTempC:5, extraHumPct:0, hours:24 }), 'Significant temperature rise increases microbial growth risk.'),
  ];
  const scenarioB = [
    mkRow('+10% humidity for 24h', projectFreshness({ extraTempC:0, extraHumPct:10, hours:24 }), 'Humidity spike increases condensation risk and spoilage pressure.'),
  ];
  const scenarioC = [
    mkRow('+4°C and +15% humidity for 48h', projectFreshness({ extraTempC:4, extraHumPct:15, hours:48 }), 'Combined stress compounds decay rate over an extended window.'),
  ];

  const allRows = [...scenarioA, ...scenarioB, ...scenarioC];
  let worst = curF;
  for(const r of allRows){
    try{
      const f = parseFloat(String(r.freshness||'').replace('%',''));
      if(Number.isFinite(f)) worst = Math.min(worst, f/100);
    }catch(e){}
  }
  const worstRisk = _riskFromFreshnessWarehouse(worst);

  let advisory = '';
  if(Math.round(clamp(worst)*100) < 40){
    advisory = 'Projected freshness falls below 40%. Recommend urgent clearance.';
  }else if(Math.round(clamp(worst)*100) < 50){
    advisory = 'Projected freshness falls below 50%. Recommend dispatch or immediate cold control.';
  }else{
    advisory = 'Storage is stable under moderate stress. Continue monitoring and maintain optimal controls.';
  }

  const scenarioTable = (rows)=>{
    const hdr = '<tr>'+
      '<th style="text-align:left;padding:8px 10px;border-bottom:1px solid #e5e7eb;color:#374151;font-weight:600;background:#f9fafb;">Condition</th>'+
      '<th style="text-align:center;padding:8px 10px;border-bottom:1px solid #e5e7eb;color:#374151;font-weight:600;background:#f9fafb;">Freshness</th>'+
      '<th style="text-align:center;padding:8px 10px;border-bottom:1px solid #e5e7eb;color:#374151;font-weight:600;background:#f9fafb;">Risk</th>'+
      '<th style="text-align:center;padding:8px 10px;border-bottom:1px solid #e5e7eb;color:#374151;font-weight:600;background:#f9fafb;">Days Remaining</th>'+
    '</tr>';
    const bodyRows = (rows||[]).map(r=>{
      return '<tr>'+
        `<td style="padding:8px 10px;border-bottom:1px solid #f3f4f6;color:#374151;">${_escapeHtml(r.label)}</td>`+
        `<td style="padding:8px 10px;border-bottom:1px solid #f3f4f6;text-align:center;font-weight:600;color:#111827;">${_escapeHtml(r.freshness)}</td>`+
        `<td style="padding:8px 10px;border-bottom:1px solid #f3f4f6;text-align:center;">${r.risk}</td>`+
        `<td style="padding:8px 10px;border-bottom:1px solid #f3f4f6;text-align:center;color:#111827;">${_escapeHtml(r.days)}</td>`+
      '</tr>'+
      `<tr><td colspan="4" style="padding:8px 10px;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:14px;line-height:1.4;">${_escapeHtml(r.explanation)}</td></tr>`;
    }).join('');
    return `<table style="width:100%;border-collapse:collapse;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">${hdr}${bodyRows}</table>`;
  };

  const scenarioCard = (title, tblHtml)=>{
    return `<div style="${cardStyle}margin-bottom:12px;">`+
      `<div style="${cardTitleStyle}">${title}</div>`+
      `${tblHtml}`+
    `</div>`;
  };

  const summaryCard =
    `<div style="${cardStyle}margin-bottom:12px;">`+
      `<div style="${cardTitleStyle}">Batch Summary</div>`+
      kvRow('Batch ID', _escapeHtml(b && b.id != null ? String(b.id) : '')) +
      kvRow('Crop', _escapeHtml(b && b.crop_type ? String(b.crop_type) : '')) +
      kvRow('Current Freshness', pctTxt(curF)) +
      kvRow('Current Risk', _riskBadgeHtml(curRisk)) +
      kvRow('Current Temperature', Number.isFinite(temp) ? `${temp.toFixed(1)} °C` : '-') +
      kvRow('Current Humidity', Number.isFinite(hum) ? `${hum.toFixed(1)} %` : '-') +
      kvRow('Remaining Safe Days', remDays0 == null ? '-' : `${Math.max(0, Math.round(remDays0))} days`) +
    `</div>`;

  const advisoryCard =
    `<div style="border:1px solid #0ea5e9;border-radius:8px;padding:16px;background:#f0f9ff;color:#0c4a6e;margin-top:16px;border-left:4px solid #0ea5e9;">`+
      `<div style="font-weight:600;margin:0 0 12px 0;color:#075985;">Advisory</div>`+
      `<div style="margin:8px 0;line-height:1.5;"><strong>Stability Assessment:</strong> ${worstRisk === 'HIGH' ? 'Batch is highly sensitive to environment spikes.' : 'Batch is stable under moderate disruption.'}</div>`+
      `<div style="margin:8px 0;line-height:1.5;"><strong>Dispatch Recommendation:</strong> ${_escapeHtml(advisory)}</div>`+
    `</div>`;

  body.innerHTML =
    summaryCard +
    scenarioCard('Scenario A: Temperature Increase', scenarioTable(scenarioA)) +
    scenarioCard('Scenario B: Humidity Spike', scenarioTable(scenarioB)) +
    scenarioCard('Scenario C: Combined Stress', scenarioTable(scenarioC)) +
    advisoryCard;

  modal.style.display = 'flex';
}

function _renderAlerts(arr){
  if(!Array.isArray(arr) || arr.length === 0) return '';
  return arr.map(a => {
    // Support both legacy string alerts and the new {message, detected_at} format
    if(a && typeof a === 'object'){
      const msg = a.message || '';
      const ts = a.detected_at ? String(a.detected_at) : '';
      const d = ts ? (()=>{ try{ return new Date(ts).toISOString().slice(0,10); }catch(e){ return ''; } })() : '';
      const label = d ? `${msg} (Detected: ${d})` : msg;
      return `<span class="alert-badge high">${label}</span>`;
    }
    return `<span class="alert-badge high">${String(a)}</span>`;
  }).join(' ');
}

async function loadDashboard(){
  const res = await fetch('/api/warehouse/dashboard', {headers:H});
  if(res.status===401 || res.status===422){ _authFail(); return; }
  const msg = document.getElementById('warehouseMsg');
  if(!res.ok){
    let detail='';
    try{ detail = await res.text(); }catch(_){ detail=''; }
    if(msg) msg.textContent = detail || `Failed to load warehouse dashboard (${res.status})`;
    return;
  }

  const data = await res.json();
  const wh = (data && data.warehouse) ? data.warehouse : {};

  const envWarehouseName = document.getElementById('envWarehouseName');
  const envRegion = document.getElementById('envRegion');
  const envDate = document.getElementById('envDate');
  const envTemp = document.getElementById('envTemp');
  const envHum = document.getElementById('envHum');
  const envCompatibility = document.getElementById('envCompatibility');

  if(envWarehouseName) envWarehouseName.textContent = wh.warehouse_name || 'Warehouse';
  if(envRegion) envRegion.textContent = wh.region || '';
  if(envDate){
    envDate.textContent = '';
    try{ if(envDate.parentElement) envDate.parentElement.style.display = 'none'; }catch(e){}
  }
  if(envTemp) envTemp.textContent = (typeof wh.temperature_c === 'number') ? `${wh.temperature_c.toFixed(1)} °C` : (wh.temperature_c ?? '');
  if(envHum) envHum.textContent = (typeof wh.humidity_pct === 'number') ? `${wh.humidity_pct.toFixed(1)} %` : (wh.humidity_pct ?? '');

  const stored = Array.isArray(data.stored_batches) ? data.stored_batches : [];
  const incoming = Array.isArray(data.incoming_batches) ? data.incoming_batches : [];
  const salvageBatches = Array.isArray(data.salvage_batches) ? data.salvage_batches : [];
  const salvageRecords = Array.isArray(data.salvage_records) ? data.salvage_records : [];

  if(envCompatibility){
    envCompatibility.textContent = '';
    try{ if(envCompatibility.parentElement) envCompatibility.parentElement.style.display = 'none'; }catch(e){}
  }

  const incomingTable = document.getElementById('incomingBatches');
  if(incomingTable){
    incomingTable.innerHTML = '<tr>'+
      '<th>Batch ID</th><th>Crop</th><th>Harvest Date</th><th>Warehouse Entry Freshness</th><th>Recommendation</th><th>Action</th>'+
      '</tr>' +
      incoming.map(b=>{
        const rs = (b.risk_status||'');
        let entryFresh = (b && b.warehouse_entry_freshness !== null && b.warehouse_entry_freshness !== undefined) ? b.warehouse_entry_freshness : null;
        let actionHtml = '';
        const reco = _renderRecoPanel(b, 'incoming', 7);
        const recoCell = `<div>${reco.btn}</div>`;
        if(String(rs||'').toUpperCase() === 'SAFE'){
          actionHtml = `<button type="button" class="action-btn" data-accept="${b.id}">Accept</button>`;
        }else{
          actionHtml = `<button type="button" class="action-btn" data-ack="${b.id}">Accept</button>`;
        }
        return `<tr>`+
          `<td>${b.id}</td>`+
          `<td>${b.crop_type||''}</td>`+
          `<td>${b.harvest_date||''}</td>`+
          `<td>${_fmtPct01(entryFresh) || '-'}</td>`+
          `<td>${recoCell}</td>`+
          `<td>${actionHtml}</td>`+
        `</tr>` + reco.row;
      }).join('');

    incomingTable.querySelectorAll('button[data-accept]').forEach(btn=>{
      btn.addEventListener('click', async ()=>{
        const id = parseInt(btn.getAttribute('data-accept'));
        if(!Number.isFinite(id)) return;
        await acceptBatchWithOptions(id, {});
      });
    });

    incomingTable.querySelectorAll('button[data-ack]').forEach(btn=>{
      btn.addEventListener('click', async ()=>{
        const id = parseInt(btn.getAttribute('data-ack'));
        if(!Number.isFinite(id)) return;
        const ok = confirm('This batch is in RISK status. Accept with acknowledgement?');
        if(!ok) return;
        await acceptBatchWithOptions(id, { acknowledge_risk: true });
      });
    });

    incomingTable.querySelectorAll('button[data-reco-toggle]').forEach(btn=>{
      btn.addEventListener('click', async ()=>{
        const id = btn.getAttribute('data-reco-toggle');
        if(!id) return;
        const row = document.getElementById(id);
        if(!row) return;

        const willOpen = (row.style.display === 'none' || row.style.display === '');
        row.style.display = willOpen ? '' : 'none';
        if(!willOpen) return;

        const batchId = parseInt(btn.getAttribute('data-batch-id'));
        if(!Number.isFinite(batchId)) return;

        const content = document.getElementById(`${id}_content`);
        if(!content) return;
        if(content.getAttribute('data-loaded') === '1') return;

        content.textContent = 'Loading...';
        try{
          const res = await fetch(`/api/warehouse/recommendation?batch_id=${batchId}&scope=incoming`, {headers:H});
          if(res.status===401 || res.status===422){ _authFail(); return; }
          if(!res.ok){
            let detail='';
            try{ detail = await res.text(); }catch(_){ detail=''; }
            content.textContent = detail || `Failed to load recommendation (${res.status})`;
            return;
          }
          const r = await res.json();
          const alertMsg = _escapeHtml(r && r.alert_message ? r.alert_message : '');
          const rec = _escapeHtml(r && r.recommendation ? r.recommendation : '');
          const exp = _escapeHtml(r && r.explanation ? r.explanation : '');
          const out = _escapeHtml(r && r.short_term_outlook ? r.short_term_outlook : '');
          content.innerHTML = (
            `<div><strong>Alert:</strong> ${alertMsg || '-'}</div>`+
            `<div style="margin-top:8px"><strong>Recommendation:</strong> ${rec || '-'}</div>`+
            `<div><strong>Explanation:</strong> ${exp || '-'}</div>`+
            `<div><strong>Short-Term Outlook:</strong> ${out || '-'}</div>`
          );
          content.setAttribute('data-loaded','1');
        }catch(e){
          content.textContent = 'Failed to load recommendation.';
        }
      });
    });
  }

  const storedTable = document.getElementById('storedBatches');
  if(storedTable){
    storedTable.innerHTML = '<tr>'+
      '<th>Batch ID</th><th>Crop</th><th>Harvest Date</th><th>Warehouse Entry Freshness</th><th>Predicted Warehouse Freshness</th><th>Risk Status</th><th>Remaining Safe Days</th><th>Recommendation</th><th></th>'+
      '</tr>' +
      stored.map(b=>{
        const reco = _renderRecoPanel(b, 'stored', 10);
        const predictedFresh = (b && (b.predicted_warehouse_freshness ?? b.predicted_freshness));
        const remDaysRaw = (b && (b.remaining_safe_days !== undefined ? b.remaining_safe_days : null));
        const remDays = (remDaysRaw !== null && remDaysRaw !== undefined && Number.isFinite(Number(remDaysRaw)))
          ? Number(remDaysRaw)
          : _computeRemainingSafeDays(b);
        const remCell = _daysBadgeHtml(remDays);
        const actionButtons = _riskAwareActionButtons(b, remDays);
        const recoCell = `<div class="action-btn-row">${reco.btn}</div>`;
        return `<tr>`+
          `<td>${b.id}</td>`+
          `<td>${b.crop_type||''}</td>`+
          `<td>${b.harvest_date||''}</td>`+
          `<td>${_fmtPct01(b.warehouse_entry_freshness)}</td>`+
          `<td>${_fmtPct01(predictedFresh) || '-'}</td>`+
          `<td>${b.risk_status||''}</td>`+
          `<td>${remCell}</td>`+
          `<td>${recoCell}</td>`+
          `<td><div class="action-btn-row">${actionButtons}</div></td>`+
        `</tr>` + reco.row;
      }).join('');

    // Add event handlers for Flag Emergency Dispatch buttons
    storedTable.querySelectorAll('button[data-flag-emergency]').forEach(btn=>{
      btn.addEventListener('click', async ()=>{
        const id = parseInt(btn.getAttribute('data-flag-emergency'));
        if(!Number.isFinite(id)) return;
        const b = stored.find(x=>parseInt(x && x.id) === id) || null;
        if(!b) return;
        
        // Flag Emergency Dispatch: Warehouse-only action to flag for logistics
        if(!confirm('Flag this crop for emergency dispatch? Logistics team will handle salvage routing.')) {
          return;
        }
        
        try {
          const emergencyData = {
            batch_id: id
          };
          
          const res = await fetch('/api/warehouse/flag-emergency', {
            method: 'POST',
            headers: H,
            body: JSON.stringify(emergencyData)
          });
          
          if(res.ok) {
            const response = await res.json();
            if(response.success) {
              alert(response.message);
              // Update UI to show EMERGENCY_REQUIRED status
              await loadDashboard(); // Refresh to show updated status
            } else {
              alert('Failed to flag emergency dispatch: ' + (response.msg || 'Unknown error'));
            }
          } else {
            const errorText = await res.text();
            alert('Failed to flag emergency dispatch: ' + errorText);
          }
        } catch(e) {
          alert('Error flagging emergency dispatch. Please try again.');
        }
      });
    });

    storedTable.querySelectorAll('button[data-reco-toggle]').forEach(btn=>{
      btn.addEventListener('click', async ()=>{
        const id = btn.getAttribute('data-reco-toggle');
        if(!id) return;
        const row = document.getElementById(id);
        if(!row) return;

        const willOpen = (row.style.display === 'none' || row.style.display === '');
        row.style.display = willOpen ? '' : 'none';
        if(!willOpen) return;

        const batchId = parseInt(btn.getAttribute('data-batch-id'));
        if(!Number.isFinite(batchId)) return;

        const contentId = `${id}_content`;
        const contentDiv = document.getElementById(contentId);
        if (contentDiv) {
          const cardStyle = 'border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; background: #ffffff; color: #374151; margin-bottom: 16px;';
          const titleStyle = 'font-weight: 600; margin: 0 0 12px 0; font-size: 16px; color: #111827;';
          const sectionStyle = 'margin-bottom: 16px;';
          const labelStyle = 'font-weight: 500; color: #374151; margin-bottom: 4px;';
          
          try{
            const res = await fetch(`/api/warehouse/recommendation?batch_id=${batchId}&scope=stored`, {headers:H});
            if(res.status===401 || res.status===422){ _authFail(); return; }
            if(!res.ok){
              let detail='';
              try{ detail = await res.text(); }catch(_){ detail=''; }
              contentDiv.innerHTML = (
                `<div style="${cardStyle}">`+
                  `<h4 style="${titleStyle}">Warehouse Recommendation</h4>`+
                  
                  `<div style="${sectionStyle}">`+
                    `<div style="${labelStyle}">Alert:</div>`+
                    `<div style="color: #ef4444; font-weight: 500;">${_escapeHtml(detail || 'Failed to load recommendation')}</div>`+
                  `</div>`+
                `</div>`
              );
              return;
            }
            const r = await res.json();
            const data = {
              alert: r && r.alert_message ? r.alert_message : '',
              recommendation: r && r.recommendation ? r.recommendation : '',
              explanation: r && r.explanation ? r.explanation : '',
              short_term_outlook: r && r.short_term_outlook ? r.short_term_outlook : ''
            };
            contentDiv.innerHTML = (
              `<div style="${cardStyle}">`+
                `<h4 style="${titleStyle}">Warehouse Recommendation</h4>`+
                
                `<div style="${sectionStyle}">`+
                  `<div style="${labelStyle}">Alert:</div>`+
                  `<div style="color: #ef4444; font-weight: 500;">${_escapeHtml(data.alert || 'No alerts')}</div>`+
                `</div>`+
                
                `<div style="${sectionStyle}">`+
                  `<div style="${labelStyle}">Recommendation:</div>`+
                  `<div style="color: #374151; line-height: 1.5;">${_escapeHtml(data.recommendation || 'No recommendation available')}</div>`+
                `</div>`+
                
                `<div style="${sectionStyle}">`+
                  `<div style="${labelStyle}">Explanation:</div>`+
                  `<div style="color: #6b7280; line-height: 1.5; font-size: 14px;">${_escapeHtml(data.explanation || 'No explanation available')}</div>`+
                `</div>`+
                
                `<div style="${sectionStyle}">`+
                  `<div style="${labelStyle}">Short-term Outlook:</div>`+
                  `<div style="color: #6b7280; line-height: 1.5; font-size: 14px;">${_escapeHtml(data.short_term_outlook || 'No outlook available')}</div>`+
                `</div>`+
              `</div>`
            );
            contentDiv.setAttribute('data-loaded','1');
          }catch(e){
            contentDiv.innerHTML = (
              `<div style="${cardStyle}">`+
                `<h4 style="${titleStyle}">Warehouse Recommendation</h4>`+
                
                `<div style="${sectionStyle}">`+
                  `<div style="${labelStyle}">Alert:</div>`+
                  `<div style="color: #ef4444; font-weight: 500;">Failed to load recommendation</div>`+
                `</div>`+
              `</div>`
            );
          }
        }
      });
    });
  }

  const salvageTable = document.getElementById('salvageBatches');
  if(salvageTable){
    salvageTable.innerHTML = '<tr>'+
      '<th>Salvage ID</th><th>Shipment ID</th><th>Batch ID</th><th>Crop</th><th>Quantity</th><th>Reason</th><th>Status</th><th>Date</th>'+
      '</tr>' +
      (salvageBatches.length ? salvageBatches.map(r=>{
        const dtRaw = r.created_at || '';
        let dTxt = '';
        try{ dTxt = dtRaw ? new Date(String(dtRaw)).toLocaleString() : ''; }catch(e){ dTxt=''; }
        const q = (r && r.quantity_pct != null) ? `${Number(r.quantity_pct).toFixed(0)}%` : '';
        return `<tr>`+
          `<td>${r.salvage_id ?? ''}</td>`+
          `<td>${r.shipment_id ?? ''}</td>`+
          `<td>${r.batch_id ?? ''}</td>`+
          `<td>${r.crop ?? ''}</td>`+
          `<td>${q}</td>`+
          `<td>${r.reason ?? ''}</td>`+
          `<td>${r.status ?? ''}</td>`+
          `<td>${dTxt}</td>`+
        `</tr>`;
      }).join('') : '<tr><td colspan="8">No salvage batches.</td></tr>');
  }
}

loadDashboard();

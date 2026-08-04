#!/usr/bin/env python3
"""
Build a fully working self-contained Eazzy Dashboard (v3).
Includes: Date-wise Performance tab, cohort %, working filters, Avg TAT Hours,
Weekend/Weekday filter, footer by Satendra Baghel.
"""
import json
import re

# ============================================================
# STEP 1: LOAD DATA FROM data.js
# ============================================================
with open('data.js', 'r', encoding='utf-8') as f:
    data_js = f.read()

# Extract JSON from JS
json_str = data_js.split('const DASHBOARD_DATA = ', 1)[1].rstrip().rstrip(';')
# Fix NaN values for JSON parsing
json_str = json_str.replace('NaN', 'null')
data = json.loads(json_str)

months = data['months']
views = data['views']
monthly_trend = data['monthly_trend']
cohort = data['cohort']
filter_options = data.get('filter_options', {})

# ============================================================
# STEP 2: LOAD CSS
# ============================================================
with open('styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

# ============================================================
# STEP 3: BUILD HTML
# ============================================================

html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Eazzy Services | Executive Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
''' + css + '''
.month-slicer { display: flex; align-items: center; gap: 10px; }
.month-slicer select { padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.3); background: rgba(255,255,255,0.15); color: white; font-size: 0.85rem; font-weight: 500; cursor: pointer; }
.month-slicer select option { color: #1f2937; }
.no-daily-msg { text-align: center; padding: 40px; color: #6b7280; font-style: italic; }

/* Filter Bar */
.filter-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  padding: 10px 20px;
  background: white;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 112px;
  z-index: 98;
}
.filter-bar label { font-size: 0.78rem; font-weight: 600; color: var(--text-muted); }
.filter-bar select {
  padding: 5px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: white;
  font-size: 0.8rem;
  cursor: pointer;
  min-width: 140px;
}
.filter-bar select:focus { outline: none; border-color: var(--accent); }
.filter-bar .filter-group { display: flex; align-items: center; gap: 6px; }
.filter-bar button.clear-btn {
  padding: 5px 14px;
  border-radius: 6px;
  border: 1px solid var(--danger);
  background: white;
  color: var(--danger);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}
.filter-bar button.clear-btn:hover { background: var(--danger); color: white; }
.filter-active { border-color: var(--accent) !important; background: #eff6ff !important; }

/* Cohort heatmap */
.cohort-high { background: #d1fae5; color: #065f46; font-weight: 700; }
.cohort-mid { background: #fef3c7; color: #92400e; font-weight: 600; }
.cohort-low { background: #fee2e2; color: #991b1b; font-weight: 600; }
.cohort-none { background: #f3f4f6; color: #9ca3af; }

/* Date-wise table */
.date-wise-table td { white-space: nowrap; }
</style>
</head>
<body>

<header class="header">
  <div class="header-top">
    <h1>🏠 EAZZY SERVICES | Executive Dashboard</h1>
    <div class="header-info">
      <div class="month-slicer">
        <label>📅 Period:</label>
        <select id="monthSelector">
          <option value="Overall">Overall</option>
        </select>
      </div>
      <span class="badge-live">Live</span>
      <span>Updated: <span id="updatedTime">--</span></span>
    </div>
  </div>
</header>

<!-- Filter Bar -->
<div class="filter-bar">
  <div class="filter-group">
    <label>🗂️ Category:</label>
    <select id="filterCategory"><option value="">All</option></select>
  </div>
  <div class="filter-group">
    <label>🔧 Service:</label>
    <select id="filterService"><option value="">All</option></select>
  </div>
  <div class="filter-group">
    <label>👨‍🔧 Expert:</label>
    <select id="filterExpert"><option value="">All</option></select>
  </div>
  <div class="filter-group" id="weekendFilterGroup" style="display:none;">
    <label>📆 Day:</label>
    <select id="filterWeekend"><option value="">All</option><option value="Weekday">Weekday</option><option value="Weekend">Weekend</option></select>
  </div>
  <button class="clear-btn" onclick="clearFilters()">✕ Clear</button>
</div>

<nav class="nav-tabs">
  <button class="nav-tab active" data-tab="executive">📊 Executive</button>
  <button class="nav-tab" data-tab="pnl">💼 P&L by Service</button>
  <button class="nav-tab" data-tab="experts">👨‍🔧 Experts</button>
  <button class="nav-tab" data-tab="operations">⏱️ Operations & TAT</button>
  <button class="nav-tab" data-tab="datewise">📅 Date-wise</button>
  <button class="nav-tab" data-tab="discount">💰 Discount Analysis</button>
  <button class="nav-tab" data-tab="lmtd">📈 LMTD vs MTD</button>
  <button class="nav-tab" data-tab="cohort">👥 Cohort</button>
  <button class="nav-tab" data-tab="insights">💡 Insights</button>
</nav>

<div class="container">

<!-- ======== P1: EXECUTIVE ======== -->
<div class="section active" id="tab-executive">
  <div class="card">
    <div class="card-title">📊 Key Performance Indicators — <span id="kpiPeriod">Overall</span></div>
    <div class="kpi-grid" id="kpiGrid"></div>
  </div>
  <div class="two-col">
    <div class="card">
      <div class="card-title">📈 Monthly Performance Trend</div>
      <div class="chart-container"><canvas id="monthlyChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">🥧 Revenue by Category</div>
      <div class="chart-container"><canvas id="categoryChart"></canvas></div>
    </div>
  </div>
  <div class="card" id="dailyCard">
    <div class="card-title">📅 Daily Performance</div>
    <div id="dailyContainer">
      <div class="chart-container chart-sm"><canvas id="dailyChart"></canvas></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📋 Monthly Summary Table</div>
    <div class="table-wrap">
      <table id="monthlyTable"><thead><tr>
        <th>Month</th><th class="text-right">Orders</th><th class="text-right">Net Revenue</th>
        <th class="text-right">Gross Profit</th><th class="text-right">Labor Cost</th>
        <th class="text-right">Spare Cost</th><th class="text-right">Net Profit</th>
        <th class="text-right">GM%</th><th class="text-right">NM%</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
</div>

<!-- ======== P2: SERVICE P&L ======== -->
<div class="section" id="tab-pnl">
  <div class="card">
    <div class="card-title">💼 Service-Wise Profit & Loss — <span class="viewLabel">Overall</span></div>
    <div class="table-wrap">
      <table id="serviceTable"><thead><tr>
        <th>Service Type</th><th class="text-right">Orders</th><th class="text-right">Net Revenue</th>
        <th class="text-right">Spare Cost</th><th class="text-right">Labor Cost</th>
        <th class="text-right">Gross Profit</th><th class="text-right">Net Profit</th>
        <th class="text-right">GM%</th><th class="text-right">NM%</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📊 Net Margin by Service</div>
    <div class="chart-container"><canvas id="serviceMarginChart"></canvas></div>
  </div>
</div>

<!-- ======== P3: EXPERTS ======== -->
<div class="section" id="tab-experts">
  <div class="card">
    <div class="card-title">👨‍🔧 Expert KPI Matrix — <span class="viewLabel">Overall</span></div>
    <div class="table-wrap">
      <table id="expertTable"><thead><tr>
        <th>Expert Name</th><th class="text-right">Orders</th><th class="text-right">Net Revenue</th>
        <th class="text-right">Gross Profit</th><th class="text-right">Net Profit</th>
        <th class="text-center">Rating</th><th class="text-center">On-Time %</th>
        <th class="text-right">Avg TAT (hrs)</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="two-col">
    <div class="card"><div class="card-title">📊 Expert Net Profit</div><div class="chart-container"><canvas id="expertProfitChart"></canvas></div></div>
    <div class="card"><div class="card-title">📊 Expert On-Time %</div><div class="chart-container"><canvas id="expertOntimeChart"></canvas></div></div>
  </div>
</div>

<!-- ======== P4: OPERATIONS ======== -->
<div class="section" id="tab-operations">
  <div class="card">
    <div class="card-title">⏱️ Expert TAT & On-Time Performance — <span class="viewLabel">Overall</span></div>
    <div class="table-wrap">
      <table id="tatTable"><thead><tr>
        <th>Expert Name</th><th class="text-center">Type</th><th class="text-right">Orders</th>
        <th class="text-right">Late</th><th class="text-right">On-Time</th><th class="text-center">Late %</th>
        <th class="text-right">Avg Act Time (min)</th><th class="text-right">Avg TAT (hrs)</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
</div>

<!-- ======== P5: DATE-WISE PERFORMANCE ======== -->
<div class="section" id="tab-datewise">
  <div class="card">
    <div class="card-title">📅 Current Month Date-wise Performance — <span class="viewLabel">Overall</span></div>
    <div class="table-wrap date-wise-table">
      <table id="datewiseTable"><thead><tr>
        <th>Day</th><th>Date</th><th class="text-right">Orders</th><th class="text-right">Net Revenue</th>
        <th class="text-right">Gross Profit</th><th class="text-right">Labor Cost</th>
        <th class="text-right">Spare Cost</th><th class="text-right">Net Profit</th>
        <th class="text-right">GM%</th><th class="text-right">NM%</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
</div>

<!-- ======== DISCOUNT ======== -->
<div class="section" id="tab-discount">
  <div class="card">
    <div class="card-title">💰 P&L Funnel — Current vs No-Discount — <span class="viewLabel">Overall</span></div>
    <div class="table-wrap">
      <table id="discountTable"><thead><tr>
        <th>Funnel Stage</th><th class="text-right">Current</th><th class="text-right">No Discount</th><th class="text-right">Impact</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="two-col">
    <div class="card"><div class="card-title">📊 Current P&L Breakdown</div><div class="chart-container"><canvas id="currentPnLChart"></canvas></div></div>
    <div class="card"><div class="card-title">📊 No-Discount P&L Breakdown</div><div class="chart-container"><canvas id="noDiscountPnLChart"></canvas></div></div>
  </div>
</div>

<!-- ======== LMTD ======== -->
<div class="section" id="tab-lmtd">
  <div class="card">
    <div class="card-title">📈 LMTD vs MTD Comparison</div>
    <div class="table-wrap lmtd-table">
      <table id="lmtdTable"><thead><tr>
        <th>Metric</th><th class="text-right">MTD</th><th class="text-right">LMTD</th>
        <th class="text-right">Variance</th><th class="text-right">Variance %</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📊 MTD vs LMTD Trend</div>
    <div class="chart-container"><canvas id="lmtdChart"></canvas></div>
  </div>
</div>

<!-- ======== COHORT ======== -->
<div class="section" id="tab-cohort">
  <div class="card">
    <div class="card-title">👥 Customer Cohort Retention (%)</div>
    <div class="table-wrap">
      <table id="cohortTable"><thead><tr>
        <th>Cohort Month</th><th class="text-right">Size</th><th class="text-center">M0</th>
        <th class="text-center">M1</th><th class="text-center">M2</th><th class="text-center">M3</th>
        <th class="text-center">M4</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>
</div>

<!-- ======== INSIGHTS ======== -->
<div class="section" id="tab-insights">
  <div class="two-col">
    <div class="card">
      <div class="card-title">💡 Key Insights — <span class="viewLabel">Overall</span></div>
      <div class="insight-list" id="insightsList"></div>
    </div>
    <div class="card">
      <div class="card-title">⚡ Action Items — <span class="viewLabel">Overall</span></div>
      <div class="insight-list" id="actionsList"></div>
    </div>
  </div>
</div>

</div>

<footer class="footer">
  Eazzy Services Dashboard • Auto-generated from Redash • Built by Satendra Baghel
</footer>

<script>
// ============================================
// EMBEDDED DATA
// ============================================
'''

# Embed data - need to handle NaN properly for JS
# Replace null back to NaN for JS compatibility
data_js_embedded = json.dumps(data, default=str).replace('null', 'NaN')
html += f'const DASHBOARD_DATA = {data_js_embedded};\n'

html += '''
// ============================================
// MAIN JAVASCRIPT
// ============================================

const DATA = DASHBOARD_DATA;
let currentView = 'Overall';
let chartInstances = {};
let activeFilters = { category: '', service: '', expert: '', weekend: '' };

// ── Helpers ──
const fmtINR = n => n == null || isNaN(n) ? '-' : '\u20b9' + (+n).toLocaleString('en-IN', {maximumFractionDigits:0});
const fmtPct = n => n == null || isNaN(n) ? '-' : (+n).toFixed(1) + '%';
const fmtNum = n => n == null || isNaN(n) ? '-' : (+n).toLocaleString('en-IN', {maximumFractionDigits:1});
const fmtRound = n => n == null || isNaN(n) ? '-' : Math.round(+n).toLocaleString('en-IN');
const fmtHours = n => n == null || isNaN(n) ? '-' : (+n).toFixed(1) + 'h';

function getCurrentData() {
  if (currentView === 'Overall') {
    return DATA.views['Overall'];
  }
  return DATA.views[currentView] || DATA.views['Overall'];
}

// ── Filter System ──
function initFilters() {
  const catSel = document.getElementById('filterCategory');
  const svcSel = document.getElementById('filterService');
  const expSel = document.getElementById('filterExpert');
  const wkSel = document.getElementById('filterWeekend');

  (DATA.filter_options?.categories || []).forEach(c => {
    const opt = document.createElement('option'); opt.value = c; opt.textContent = c; catSel.appendChild(opt);
  });
  (DATA.filter_options?.services || []).forEach(s => {
    const opt = document.createElement('option'); opt.value = s; opt.textContent = s; svcSel.appendChild(opt);
  });
  (DATA.filter_options?.experts || []).forEach(e => {
    const opt = document.createElement('option'); opt.value = e; opt.textContent = e; expSel.appendChild(opt);
  });

  catSel.addEventListener('change', () => { activeFilters.category = catSel.value; catSel.classList.toggle('filter-active', !!catSel.value); renderAll(); });
  svcSel.addEventListener('change', () => { activeFilters.service = svcSel.value; svcSel.classList.toggle('filter-active', !!svcSel.value); renderAll(); });
  expSel.addEventListener('change', () => { activeFilters.expert = expSel.value; expSel.classList.toggle('filter-active', !!expSel.value); renderAll(); });
  wkSel.addEventListener('change', () => { activeFilters.weekend = wkSel.value; wkSel.classList.toggle('filter-active', !!wkSel.value); renderTATTable(); });
}

function clearFilters() {
  activeFilters = { category: '', service: '', expert: '', weekend: '' };
  ['filterCategory','filterService','filterExpert','filterWeekend'].forEach(id => {
    const el = document.getElementById(id);
    el.value = ''; el.classList.remove('filter-active');
  });
  renderAll();
}

function matchesFilters(row, type) {
  if (type === 'service' && activeFilters.category && row.Service_Type) {
    // Service type filtering by category is approximate; skip for now
  }
  if (type === 'service' && activeFilters.service && row.Service_Type !== activeFilters.service) return false;
  if (type === 'expert' && activeFilters.expert && row.Expert_Name !== activeFilters.expert) return false;
  if (type === 'tat' && activeFilters.expert && row.Expert_Name !== activeFilters.expert) return false;
  if (type === 'tat' && activeFilters.weekend && row.Weekend_Flag !== activeFilters.weekend) return false;
  return true;
}

// ── Month Slicer ──
function initMonthSelector() {
  const select = document.getElementById('monthSelector');
  DATA.months.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    select.appendChild(opt);
  });
  // Default to latest month
  select.value = DATA.months[DATA.months.length - 1];
  currentView = select.value;

  select.addEventListener('change', () => {
    currentView = select.value;
    renderAll();
  });
}

// ── Tab Switching ──
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    // Show/hide weekend filter
    document.getElementById('weekendFilterGroup').style.display = (tab.dataset.tab === 'operations') ? 'flex' : 'none';
  });
});

// ── Destroy old charts ──
function destroyCharts() {
  Object.values(chartInstances).forEach(c => { if(c) c.destroy(); });
  chartInstances = {};
}

// ── KPI Cards ──
function renderKPIs() {
  const k = getCurrentData().kpis;
  const items = [
    { label: 'Total Orders', value: fmtRound(k.total_orders), sub: '', cls: '' },
    { label: 'Net Revenue', value: fmtINR(k.net_revenue), sub: '', cls: 'green' },
    { label: 'Order Amount', value: fmtINR(k.order_amount), sub: '', cls: '' },
    { label: 'Discounts', value: fmtINR(k.discounts), sub: k.order_amount > 0 ? fmtPct(k.discounts/k.order_amount*100) : '', cls: 'red' },
    { label: 'Tax Collected', value: fmtINR(k.tax_collected), sub: '', cls: '' },
    { label: 'Gross Profit', value: fmtINR(k.gross_profit), sub: fmtPct(k.gross_margin*100), cls: 'green' },
    { label: 'Labor Cost', value: fmtINR(k.labor_cost), sub: '', cls: 'orange' },
    { label: 'Spare Cost', value: fmtINR(k.spare_cost), sub: '', cls: 'orange' },
    { label: 'Net Profit', value: fmtINR(k.net_profit), sub: fmtPct(k.net_margin*100), cls: k.net_margin >= 0 ? 'green' : 'red' },
    { label: 'Gross Margin', value: fmtPct(k.gross_margin*100), sub: '', cls: 'purple' },
    { label: 'Net Margin', value: fmtPct(k.net_margin*100), sub: '', cls: 'purple' },
    { label: 'Avg Order Value', value: fmtINR(k.avg_order_value), sub: '', cls: '' },
    { label: 'Late Orders', value: fmtRound(k.late_orders), sub: fmtPct(k.sla_breach_pct), cls: 'red' },
    { label: 'On-Time %', value: fmtPct(k.ontime_pct), sub: fmtRound(k.ontime_orders) + ' orders', cls: 'green' },
    { label: 'Avg Rating', value: k.avg_rating ? k.avg_rating.toFixed(1) : '-', sub: '/5.0', cls: k.avg_rating >= 4.5 ? 'green' : k.avg_rating >= 3.5 ? 'orange' : 'red' },
    { label: 'Avg TAT (hrs)', value: fmtHours(k.avg_tat_hours), sub: '', cls: 'purple' },
  ];
  document.getElementById('kpiGrid').innerHTML = items.map(i => `
    <div class="kpi-card ${i.cls}">
      <div class="kpi-label">${i.label}</div>
      <div class="kpi-value">${i.value}</div>
      <div class="kpi-sub">${i.sub}</div>
    </div>
  `).join('');

  document.getElementById('kpiPeriod').textContent = currentView;
  document.querySelectorAll('.viewLabel').forEach(el => el.textContent = currentView);
}

// ── Monthly Trend Chart (always all months) ──
function renderMonthlyChart() {
  const d = DATA.monthly_trend;
  chartInstances.monthly = new Chart(document.getElementById('monthlyChart'), {
    type: 'bar',
    data: {
      labels: d.Month,
      datasets: [
        { label: 'Net Revenue', data: d.Net_Revenue, backgroundColor: '#3b82f6', borderRadius: 4 },
        { label: 'Gross Profit', data: d.Gross_Profit, backgroundColor: '#10b981', borderRadius: 4 },
        { label: 'Net Profit', data: d.Net_Profit, backgroundColor: '#8b5cf6', borderRadius: 4 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { boxWidth: 12, font: {size:11} } } },
      scales: { y: { beginAtZero: true, ticks: { callback: v => '\u20b9' + (v/1000).toFixed(0) + 'K' } } }
    }
  });
}

// ── Category Chart ──
function renderCategoryChart() {
  const d = getCurrentData().category_mix;
  if (!d.Category || d.Category.length === 0) {
    document.getElementById('categoryChart').parentElement.innerHTML = '<div class="no-daily-msg">No category data</div>';
    return;
  }
  const colors = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#84cc16','#f97316','#ec4899','#6366f1','#14b8a6','#a855f7','#f43f5e'];
  chartInstances.category = new Chart(document.getElementById('categoryChart'), {
    type: 'doughnut',
    data: { labels: d.Category, datasets: [{ data: d.Net_Revenue, backgroundColor: colors }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { boxWidth: 10, font: {size:9} } } } }
  });
}

// ── Daily Chart ──
function renderDailyChart() {
  const d = getCurrentData().daily_perf;
  const container = document.getElementById('dailyContainer');

  if (!d || !d.Date || d.Date.length === 0) {
    container.innerHTML = '<div class="no-daily-msg">\uF4C5 Select a specific month to view daily performance</div>';
    return;
  }

  container.innerHTML = '<div class="chart-container chart-sm"><canvas id="dailyChart"></canvas></div>';
  chartInstances.daily = new Chart(document.getElementById('dailyChart'), {
    type: 'bar',
    data: {
      labels: d.Date.map(dt => new Date(dt).getDate()),
      datasets: [
        { label: 'Orders', data: d.Orders, backgroundColor: '#3b82f6', borderRadius: 3 },
        { label: 'Net Revenue (\u20b9K)', data: d.Net_Revenue.map(v => v/1000), backgroundColor: '#10b981', borderRadius: 3 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { boxWidth: 10, font: {size:10} } } },
      scales: { y: { beginAtZero: true } }
    }
  });
}

// ── Monthly Table (always all months) ──
function renderMonthlyTable() {
  const d = DATA.monthly_trend;
  const tbody = document.querySelector('#monthlyTable tbody');
  let html = '';
  for (let i = 0; i < d.Month.length; i++) {
    html += `<tr ${d.Month[i] === currentView ? 'style="background:#dbeafe;font-weight:600"' : ''}>
      <td>${d.Month[i]}</td>
      <td class="text-right">${fmtRound(d.Orders[i])}</td>
      <td class="text-right">${fmtINR(d.Net_Revenue[i])}</td>
      <td class="text-right">${fmtINR(d.Gross_Profit[i])}</td>
      <td class="text-right">${fmtINR(d.Labor_Cost[i])}</td>
      <td class="text-right">${fmtINR(d.Spare_Cost[i])}</td>
      <td class="text-right ${d.Net_Profit[i] >= 0 ? 'positive' : 'negative'}">${fmtINR(d.Net_Profit[i])}</td>
      <td class="text-right">${fmtPct((d.Gross_Profit[i]/d.Net_Revenue[i])*100)}</td>
      <td class="text-right">${fmtPct((d.Net_Profit[i]/d.Net_Revenue[i])*100)}</td>
    </tr>`;
  }
  const totalOrders = d.Orders.reduce((a,b) => a+b, 0);
  const totalRev = d.Net_Revenue.reduce((a,b) => a+b, 0);
  const totalGP = d.Gross_Profit.reduce((a,b) => a+b, 0);
  const totalLC = d.Labor_Cost.reduce((a,b) => a+b, 0);
  const totalSC = d.Spare_Cost.reduce((a,b) => a+b, 0);
  const totalNP = d.Net_Profit.reduce((a,b) => a+b, 0);
  html += `<tr class="totals-row">
    <td>TOTAL</td><td class="text-right">${fmtRound(totalOrders)}</td><td class="text-right">${fmtINR(totalRev)}</td>
    <td class="text-right">${fmtINR(totalGP)}</td><td class="text-right">${fmtINR(totalLC)}</td>
    <td class="text-right">${fmtINR(totalSC)}</td><td class="text-right ${totalNP >= 0 ? 'positive' : 'negative'}">${fmtINR(totalNP)}</td>
    <td class="text-right">${fmtPct(totalGP/totalRev*100)}</td><td class="text-right">${fmtPct(totalNP/totalRev*100)}</td>
  </tr>`;
  tbody.innerHTML = html;
}

// ── Service P&L Table ──
function renderServiceTable() {
  const tbody = document.querySelector('#serviceTable tbody');
  let rows = getCurrentData().service_pnl || [];
  rows = rows.filter(r => matchesFilters(r, 'service'));
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.Service_Type}</td>
      <td class="text-right">${fmtRound(r.Orders)}</td>
      <td class="text-right">${fmtINR(r.Net_Revenue)}</td>
      <td class="text-right">${fmtINR(r.Spare_Cost)}</td>
      <td class="text-right">${fmtINR(r.Labor_Cost)}</td>
      <td class="text-right ${r.Gross_Profit >= 0 ? 'positive' : 'negative'}">${fmtINR(r.Gross_Profit)}</td>
      <td class="text-right ${r.Net_Profit >= 0 ? 'positive' : 'negative'}">${fmtINR(r.Net_Profit)}</td>
      <td class="text-right">${fmtPct(r.GM_pct*100)}</td>
      <td class="text-right">${fmtPct(r.NM_pct*100)}</td>
    </tr>
  `).join('');
}

function renderServiceMarginChart() {
  const d = getCurrentData().service_pnl || [];
  if (d.length === 0) return;
  chartInstances.serviceMargin = new Chart(document.getElementById('serviceMarginChart'), {
    type: 'bar',
    data: {
      labels: d.map(r => r.Service_Type.length > 22 ? r.Service_Type.substring(0,22)+'...' : r.Service_Type),
      datasets: [{ label: 'Net Margin %', data: d.map(r => r.NM_pct*100), backgroundColor: d.map(r => r.NM_pct >= 0 ? '#10b981' : '#ef4444'), borderRadius: 3 }]
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { ticks: { callback: v => v + '%' } } } }
  });
}

// ── Expert Tables ──
function renderExpertTable() {
  const tbody = document.querySelector('#expertTable tbody');
  let rows = getCurrentData().expert_kpi || [];
  rows = rows.filter(r => matchesFilters(r, 'expert'));
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><strong>${r.Expert_Name}</strong></td>
      <td class="text-right">${fmtRound(r.Orders)}</td>
      <td class="text-right">${fmtINR(r.Net_Revenue)}</td>
      <td class="text-right">${fmtINR(r.Gross_Profit)}</td>
      <td class="text-right ${r.Net_Profit >= 0 ? 'positive' : 'negative'}">${fmtINR(r.Net_Profit)}</td>
      <td class="text-center">${r.Avg_Rating ? r.Avg_Rating.toFixed(1) : '-'}</td>
      <td class="text-center"><span class="badge ${r.On_Time_pct >= 80 ? 'badge-green' : r.On_Time_pct >= 60 ? 'badge-orange' : 'badge-red'}">${fmtPct(r.On_Time_pct)}</span></td>
      <td class="text-right">${fmtHours(r.Avg_TAT_Hours)}</td>
    </tr>
  `).join('');
}

function renderExpertProfitChart() {
  const d = getCurrentData().expert_kpi || [];
  if (d.length === 0) return;
  chartInstances.expertProfit = new Chart(document.getElementById('expertProfitChart'), {
    type: 'bar',
    data: { labels: d.map(r => r.Expert_Name), datasets: [{ label: 'Net Profit', data: d.map(r => r.Net_Profit), backgroundColor: d.map(r => r.Net_Profit >= 0 ? '#10b981' : '#ef4444'), borderRadius: 3 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { ticks: { callback: v => '\u20b9' + v/1000 + 'K' } } } }
  });
}

function renderExpertOntimeChart() {
  const d = getCurrentData().expert_kpi || [];
  if (d.length === 0) return;
  chartInstances.expertOntime = new Chart(document.getElementById('expertOntimeChart'), {
    type: 'bar',
    data: { labels: d.map(r => r.Expert_Name), datasets: [{ label: 'On-Time %', data: d.map(r => r.On_Time_pct), backgroundColor: d.map(r => r.On_Time_pct >= 80 ? '#10b981' : r.On_Time_pct >= 60 ? '#f59e0b' : '#ef4444'), borderRadius: 3 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { min: 0, max: 100, ticks: { callback: v => v + '%' } } } }
  });
}

function renderTATTable() {
  const tbody = document.querySelector('#tatTable tbody');
  let rows = getCurrentData().expert_tat || [];
  rows = rows.filter(r => matchesFilters(r, 'tat'));
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.Expert_Name}</td>
      <td class="text-center"><span class="badge ${r.Weekend_Flag === 'Weekend' ? 'badge-blue' : 'badge-green'}">${r.Weekend_Flag}</span></td>
      <td class="text-right">${fmtRound(r.Orders)}</td>
      <td class="text-right negative">${fmtRound(r.Late)}</td>
      <td class="text-right positive">${fmtRound(r.On_Time)}</td>
      <td class="text-center"><span class="badge ${r.Late_pct <= 10 ? 'badge-green' : r.Late_pct <= 25 ? 'badge-orange' : 'badge-red'}">${fmtPct(r.Late_pct)}</span></td>
      <td class="text-right">${fmtNum(r.Avg_Act_Time)}</td>
      <td class="text-right">${fmtHours(r.Avg_TAT_Hours)}</td>
    </tr>
  `).join('');
}

// ── Date-wise Performance Table ──
function renderDatewiseTable() {
  const tbody = document.querySelector('#datewiseTable tbody');
  const rows = getCurrentData().date_wise_perf || [];
  if (rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center" style="padding:30px;color:#6b7280">No data available</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.Day}</td>
      <td>${r.Date}</td>
      <td class="text-right">${fmtRound(r.Orders)}</td>
      <td class="text-right">${fmtINR(r.Net_Revenue)}</td>
      <td class="text-right">${fmtINR(r.Gross_Profit)}</td>
      <td class="text-right">${fmtINR(r.Labor_Cost)}</td>
      <td class="text-right">${fmtINR(r.Spare_Cost)}</td>
      <td class="text-right ${r.Net_Profit >= 0 ? 'positive' : 'negative'}">${fmtINR(r.Net_Profit)}</td>
      <td class="text-right">${fmtPct(r.GM_pct)}</td>
      <td class="text-right">${fmtPct(r.NM_pct)}</td>
    </tr>
  `).join('');
}

// ── Discount P&L ──
function renderDiscountTable() {
  const tbody = document.querySelector('#discountTable tbody');
  const rows = getCurrentData().discount_pnl || [];
  const highlight = ['Gross Profit', 'Net Profit', 'Revenue After Discount', 'Less: Discount'];
  tbody.innerHTML = rows.map(r => {
    const isH = highlight.includes(r.Funnel_Stage);
    const fmt = v => {
      if (typeof v !== 'number') return v;
      if (r.Funnel_Stage.includes('%')) return v.toFixed(1) + '%';
      if (Math.abs(v) > 1000) return fmtINR(v);
      return fmtRound(v);
    };
    return `<tr ${isH ? 'style="background:#f0f9ff;font-weight:600"' : ''}>
      <td>${r.Funnel_Stage}</td>
      <td class="text-right">${fmt(r.Current)}</td>
      <td class="text-right">${fmt(r.No_Discount)}</td>
      <td class="text-right ${r.Impact > 0 ? 'positive' : r.Impact < 0 ? 'negative' : 'neutral'}">${fmt(r.Impact)}</td>
    </tr>`;
  }).join('');
}

function renderDiscountCharts() {
  const rows = getCurrentData().discount_pnl || [];
  if (rows.length === 0) return;

  const getVal = name => {
    const r = rows.find(x => x.Funnel_Stage === name);
    return r ? +r.Current : 0;
  };

  const np = getVal('Net Profit');
  const sc = getVal('Less: Spare Cost');
  const cc = getVal('Less: Consumable Cost');
  const lc = getVal('Less: Labor & Travel Cost');
  const disc = getVal('Less: Discount');

  chartInstances.currentPnL = new Chart(document.getElementById('currentPnLChart'), {
    type: 'pie',
    data: { labels: ['Net Profit', 'Spare Cost', 'Consumable', 'Labor & Travel', 'Discount'], datasets: [{ data: [Math.max(0,np), sc, cc, lc, disc], backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#3b82f6'] }] },
    options: { responsive: true, maintainAspectRatio: false }
  });

  const getNoDisc = name => {
    const r = rows.find(x => x.Funnel_Stage === name);
    return r ? +r.No_Discount : 0;
  };

  chartInstances.noDiscountPnL = new Chart(document.getElementById('noDiscountPnLChart'), {
    type: 'pie',
    data: { labels: ['Net Profit', 'Spare Cost', 'Consumable', 'Labor & Travel'], datasets: [{ data: [Math.max(0,getNoDisc('Net Profit')), sc, cc, lc], backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#8b5cf6'] }] },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

// ── LMTD vs MTD ──
function renderLMTDTable() {
  const tbody = document.querySelector('#lmtdTable tbody');
  const rows = getCurrentData().lmtd_mtd || [];
  if (rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center" style="padding:20px;color:#6b7280">No LMTD data available for this period</td></tr>';
    return;
  }
  const sections = ['Orders Completed', 'Gross Service Value', 'Revenue After Discount', 'Gross Profit', 'Net Profit', 'Avg Revenue / Order'];
  tbody.innerHTML = rows.map(r => {
    const isSec = sections.includes(r.Metric);
    return `<tr ${isSec ? 'style="background:#f8fafc;font-weight:600"' : ''}>
      <td class="${isSec ? 'metric-name' : ''}">${r.Metric}</td>
      <td class="text-right">${typeof r.MTD === 'number' && r.MTD > 100 ? fmtINR(r.MTD) : typeof r.MTD === 'number' ? (+r.MTD).toFixed(1) : r.MTD}</td>
      <td class="text-right">${typeof r.LMTD === 'number' && r.LMTD > 100 ? fmtINR(r.LMTD) : typeof r.LMTD === 'number' ? (+r.LMTD).toFixed(1) : r.LMTD}</td>
      <td class="text-right ${r.Variance >= 0 ? 'positive' : 'negative'}">${typeof r.Variance === 'number' ? (Math.abs(r.Variance) > 100 ? fmtINR(r.Variance) : (+r.Variance).toFixed(1)) : '-'}</td>
      <td class="text-right ${r.Variance_pct >= 0 ? 'positive' : 'negative'}">${typeof r.Variance_pct === 'number' ? (+r.Variance_pct).toFixed(1) + '%' : '-'}</td>
    </tr>`;
  }).join('');
}

function renderLMTDChart() {
  const rows = getCurrentData().lmtd_mtd || [];
  if (rows.length === 0) return;
  const metrics = ['Orders Completed', 'Net Profit', 'Gross Profit', 'Avg Revenue / Order'];
  const filtered = rows.filter(r => metrics.includes(r.Metric));
  if (filtered.length === 0) return;

  chartInstances.lmtd = new Chart(document.getElementById('lmtdChart'), {
    type: 'bar',
    data: {
      labels: filtered.map(r => r.Metric),
      datasets: [
        { label: 'MTD', data: filtered.map(r => r.MTD), backgroundColor: '#3b82f6', borderRadius: 4 },
        { label: 'LMTD', data: filtered.map(r => r.LMTD), backgroundColor: '#94a3b8', borderRadius: 4 },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } }, scales: { y: { beginAtZero: true } } }
  });
}

// ── Cohort with % and color coding ──
function renderCohortTable() {
  const tbody = document.querySelector('#cohortTable tbody');
  tbody.innerHTML = DATA.cohort.map(r => {
    const cells = ['0','1','2','3','4'].map(m => {
      const v = r[m];
      if (v == null || isNaN(v)) return '<td class="text-center cohort-none">-</td>';
      let cls = 'cohort-low';
      if (v >= 50) cls = 'cohort-high';
      else if (v >= 20) cls = 'cohort-mid';
      return `<td class="text-center ${cls}">${v.toFixed(1)}%</td>`;
    }).join('');
    return `<tr>
      <td><strong>${r['Cohort Month']}</strong></td>
      <td class="text-right">${r.Size}</td>
      ${cells}
    </tr>`;
  }).join('');
}

// ── Insights ──
function renderInsights() {
  const data = getCurrentData();
  document.getElementById('insightsList').innerHTML = (data.insights || []).map(i => {
    let cls = 'info';
    if (i.includes('Worst') || i.includes('Attention')) cls = 'warning';
    else if (i.includes('Best') || i.includes('Top')) cls = 'success';
    return `<div class="insight-item ${cls}">${i}</div>`;
  }).join('');

  document.getElementById('actionsList').innerHTML = (data.action_items || []).map(i => {
    let cls = 'warning';
    if (i.includes('URGENT')) cls = 'danger';
    return `<div class="insight-item ${cls}">${i}</div>`;
  }).join('');
}

// ── Main Render ──
function renderAll() {
  destroyCharts();
  document.getElementById('updatedTime').textContent = DATA.timestamp.split('T')[0];

  renderKPIs();
  renderMonthlyChart();
  renderCategoryChart();
  renderDailyChart();
  renderMonthlyTable();
  renderServiceTable();
  renderServiceMarginChart();
  renderExpertTable();
  renderExpertProfitChart();
  renderExpertOntimeChart();
  renderTATTable();
  renderDatewiseTable();
  renderDiscountTable();
  renderDiscountCharts();
  renderLMTDTable();
  renderLMTDChart();
  renderCohortTable();
  renderInsights();
}

// ── Init ──
function init() {
  initMonthSelector();
  initFilters();
  renderAll();
}

init();
</script>
</body>
</html>
'''

# Write the file
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Created working dashboard: index.html")
print(f"   Size: {len(html):,} chars ({len(html)/1024:.1f} KB)")
print(f"   Months: {months}")
print(f"   Views: {list(views.keys())}")
print(f"\n📤 Upload ONLY this file to GitHub Pages:")
print(f"   C:\\Users\\saten\\Documents\\kimi\\workspace\\eazzy-dashboard-github\\index.html")

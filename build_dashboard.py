#!/usr/bin/env python3
"""
Eazzy Services - Professional Executive Dashboard Builder
Reads Revenue Excel sheet and generates a single self-contained HTML dashboard.
"""

import pandas as pd
import json
from datetime import datetime
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================
EXCEL_PATH = r'C:\Users\saten\Desktop\Eazzy_Dashboard_v2 Manual.xlsx'
OUTPUT_PATH = r'C:\Users\saten\Documents\kimi\workspace\eazzy-dashboard-github\index.html'

# Theme Colors
PRIMARY_ORANGE = '#FF6600'  # Bajaj Orange
GREEN_POSITIVE = '#22C55E'
RED_NEGATIVE = '#EF4444'
BLUE_ACCENT = '#3B82F6'
PURPLE_ACCENT = '#8B5CF6'

# ============================================================
# STEP 1: LOAD & CLEAN DATA
# ============================================================
print("Loading Revenue data...")
df = pd.read_excel(EXCEL_PATH, sheet_name='Revenue')

# Clean column names
df.columns = [c.strip() for c in df.columns]

# Convert dates
df['Create Date'] = pd.to_datetime(df['Create Date'])
df['Appointment Date'] = pd.to_datetime(df['Appointment Date'])
df['Post Job Done Date'] = pd.to_datetime(df['Post Job Done Date'])

# Extract time components
df['Year'] = df['Create Date'].dt.year
df['Quarter'] = df['Create Date'].dt.quarter
df['Month_Num'] = df['Create Date'].dt.month
df['Week'] = df['Create Date'].dt.isocalendar().week
df['Day'] = df['Create Date'].dt.day
df['DayOfWeek'] = df['Create Date'].dt.day_name()
df['Month_Year'] = df['Create Date'].dt.strftime('%m-%Y')

# Clean numeric columns
for col in ['Order Amount', 'Discount', 'Tax', 'Net Revenue', 'Gross Profit', 'Net Profit',
            'Labor Cost Per Article', 'Labor Cost & Travel cost', 'Consumable',
            'Spare Input Price', 'Spare Selling Price Pre Tax', 'Spare Tax']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Calculate additional metrics
df['Has_Discount'] = df['Discount'] > 0
df['Discount_pct'] = (df['Discount'] / df['Order Amount'] * 100).fillna(0)
df['Revenue_after_discount'] = df['Order Amount'] - df['Discount']
df['Total_Cost'] = df['Consumable'] + df['Labor Cost & Travel cost'] + df['Spare Input Price']
df['EBITDA'] = df['Net Revenue'] - df['Total_Cost']
df['EBITDA_pct'] = (df['EBITDA'] / df['Net Revenue'] * 100).replace([np.inf, -np.inf], 0).fillna(0)

# Customer repeat analysis
customer_orders = df.groupby('Customer ID').size().reset_index(name='Order_Count')
df = df.merge(customer_orders, on='Customer ID', how='left')
df['Customer_Type'] = df['Order_Count'].apply(lambda x: 'Repeat' if x > 1 else 'New')

# Determine Financial Year (April-March)
df['FY'] = df.apply(lambda row: f"FY{row['Year']}" if row['Month_Num'] >= 4 else f"FY{row['Year']-1}", axis=1)

print(f"Data loaded: {len(df)} records from {df['Create Date'].min().date()} to {df['Create Date'].max().date()}")

# ============================================================
# STEP 2: CALCULATE ALL DASHBOARD METRICS
# ============================================================
print("Calculating dashboard metrics...")

# --- Global KPIs ---
total_revenue = df['Net Revenue'].sum()
total_orders = len(df)
total_customers = df['Customer ID'].nunique()
total_gross_profit = df['Gross Profit'].sum()
total_net_profit = df['Net Profit'].sum()
total_ebitda = df['EBITDA'].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
gross_margin_pct = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0
net_margin_pct = (total_net_profit / total_revenue * 100) if total_revenue > 0 else 0
ebitda_pct = (total_ebitda / total_revenue * 100) if total_revenue > 0 else 0
total_discount = df['Discount'].sum()
discount_pct = (total_discount / df['Order Amount'].sum() * 100) if df['Order Amount'].sum() > 0 else 0
repeat_customers = df[df['Customer_Type'] == 'Repeat']['Customer ID'].nunique()
repeat_pct = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
avg_rating = df['Ratings'].mean()

# --- Monthly Trends ---
monthly = df.groupby('Month_Year').agg({
    'Net Revenue': 'sum',
    'Order Amount': 'sum',
    'Discount': 'sum',
    'Gross Profit': 'sum',
    'Net Profit': 'sum',
    'EBITDA': 'sum',
    'Project No.': 'count',
    'Customer ID': 'nunique'
}).reset_index()
monthly.columns = ['Month', 'Revenue', 'Order_Amount', 'Discount', 'Gross_Profit', 'Net_Profit', 'EBITDA', 'Orders', 'Customers']
monthly = monthly.sort_values('Month')

# --- Daily Trends ---
daily = df.groupby('Create Date').agg({
    'Net Revenue': 'sum',
    'Project No.': 'count',
    'Gross Profit': 'sum'
}).reset_index()
daily.columns = ['Date', 'Revenue', 'Orders', 'Gross_Profit']
daily['Date_Str'] = daily['Date'].dt.strftime('%Y-%m-%d')

# --- By Category ---
by_category = df.groupby('Subcat').agg({
    'Net Revenue': 'sum',
    'Project No.': 'count',
    'Gross Profit': 'sum',
    'Net Profit': 'sum'
}).reset_index()
by_category.columns = ['Category', 'Revenue', 'Orders', 'Gross_Profit', 'Net_Profit']
by_category = by_category.sort_values('Revenue', ascending=False)

# --- By Service Type ---
by_service = df.groupby('Service Type').agg({
    'Net Revenue': 'sum',
    'Project No.': 'count',
    'Gross Profit': 'sum',
    'Net Profit': 'sum',
    'EBITDA': 'sum'
}).reset_index()
by_service.columns = ['Service_Type', 'Revenue', 'Orders', 'Gross_Profit', 'Net_Profit', 'EBITDA']
by_service['EBITDA_pct'] = (by_service['EBITDA'] / by_service['Revenue'] * 100).fillna(0)
by_service = by_service.sort_values('Revenue', ascending=False)

# --- By Expert ---
by_expert = df.groupby('Expert Name').agg({
    'Net Revenue': 'sum',
    'Project No.': 'count',
    'Gross Profit': 'sum',
    'Net Profit': 'sum',
    'Ratings': 'mean',
    'Actual Time (min)': 'mean'
}).reset_index()
by_expert.columns = ['Expert', 'Revenue', 'Orders', 'Gross_Profit', 'Net_Profit', 'Avg_Rating', 'Avg_Time']
by_expert = by_expert.sort_values('Revenue', ascending=False)

# --- By City (from Variant/Subcat as proxy) ---
by_variant = df.groupby('Variant Name').agg({
    'Net Revenue': 'sum',
    'Project No.': 'count'
}).reset_index()
by_variant.columns = ['Variant', 'Revenue', 'Orders']
by_variant = by_variant.sort_values('Revenue', ascending=False).head(15)

# --- Discount Analysis ---
discount_analysis = df.groupby('Has_Discount').agg({
    'Net Revenue': 'sum',
    'Project No.': 'count',
    'Gross Profit': 'sum',
    'Net Profit': 'sum',
    'Order Amount': 'sum',
    'Discount': 'sum'
}).reset_index()

# --- TAT Analysis ---
tat_analysis = df.groupby('TAT').agg({
    'Project No.': 'count',
    'Net Revenue': 'sum'
}).reset_index()
tat_analysis.columns = ['TAT_Status', 'Orders', 'Revenue']

# --- Weekend vs Weekday ---
weekend_analysis = df.groupby('Weekend Flag').agg({
    'Project No.': 'count',
    'Net Revenue': 'sum',
    'Gross Profit': 'sum'
}).reset_index()
weekend_analysis.columns = ['Flag', 'Orders', 'Revenue', 'Gross_Profit']

# --- Cohort Data ---
customer_first = df.groupby('Customer ID')['Create Date'].min().reset_index()
customer_first.columns = ['Customer ID', 'First_Order']
customer_first['Cohort_Month'] = customer_first['First_Order'].dt.strftime('%m-%Y')
df = df.merge(customer_first[['Customer ID', 'Cohort_Month']], on='Customer ID', how='left')

# --- LMTD vs MTD ---
current_month = df['Month_Year'].max()
prev_month = monthly.iloc[-2]['Month'] if len(monthly) > 1 else current_month

mtd_data = df[df['Month_Year'] == current_month]
lmtd_data = df[df['Month_Year'] == prev_month]

lmtd_comparison = {
    'current_month': current_month,
    'prev_month': prev_month,
    'mtd': {
        'revenue': mtd_data['Net Revenue'].sum(),
        'orders': len(mtd_data),
        'customers': mtd_data['Customer ID'].nunique(),
        'gross_profit': mtd_data['Gross Profit'].sum(),
        'net_profit': mtd_data['Net Profit'].sum(),
        'ebitda': mtd_data['EBITDA'].sum(),
        'discount': mtd_data['Discount'].sum(),
        'avg_order': mtd_data['Net Revenue'].sum() / len(mtd_data) if len(mtd_data) > 0 else 0
    },
    'lmtd': {
        'revenue': lmtd_data['Net Revenue'].sum(),
        'orders': len(lmtd_data),
        'customers': lmtd_data['Customer ID'].nunique(),
        'gross_profit': lmtd_data['Gross Profit'].sum(),
        'net_profit': lmtd_data['Net Profit'].sum(),
        'ebitda': lmtd_data['EBITDA'].sum(),
        'discount': lmtd_data['Discount'].sum(),
        'avg_order': lmtd_data['Net Revenue'].sum() / len(lmtd_data) if len(lmtd_data) > 0 else 0
    }
}

# Calculate variances
for key in lmtd_comparison['mtd']:
    if key in lmtd_comparison['lmtd'] and lmtd_comparison['lmtd'][key] != 0:
        lmtd_comparison['variance_pct'] = lmtd_comparison['variance_pct'] if 'variance_pct' in lmtd_comparison else {}
        lmtd_comparison['variance_pct'][key] = ((lmtd_comparison['mtd'][key] - lmtd_comparison['lmtd'][key]) / lmtd_comparison['lmtd'][key] * 100)

# --- Filter Options ---
filter_options = {
    'fy': sorted(df['FY'].unique().tolist()),
    'quarter': ['Q1', 'Q2', 'Q3', 'Q4'],
    'month': sorted(df['Month_Year'].unique().tolist()),
    'category': sorted(df['Subcat'].dropna().unique().tolist()),
    'service_type': sorted(df['Service Type'].dropna().unique().tolist()),
    'variant': sorted(df['Variant Name'].dropna().unique().tolist()),
    'expert': sorted(df['Expert Name'].dropna().unique().tolist()),
    'status': sorted(df['Status'].dropna().unique().tolist()),
    'customer_type': ['New', 'Repeat'],
    'discount_type': ['With Discount', 'Without Discount'],
    'weekend_flag': ['Weekday', 'Weekend']
}

# --- Strategic Insights ---
# Top growing/declining services (month-over-month)
service_monthly = df.groupby(['Month_Year', 'Service Type'])['Net Revenue'].sum().reset_index()
service_monthly_pivot = service_monthly.pivot(index='Service Type', columns='Month_Year', values='Net Revenue').fillna(0)
if len(service_monthly_pivot.columns) >= 2:
    last_col = service_monthly_pivot.columns[-1]
    prev_col = service_monthly_pivot.columns[-2]
    service_monthly_pivot['growth_pct'] = ((service_monthly_pivot[last_col] - service_monthly_pivot[prev_col]) / (service_monthly_pivot[prev_col] + 0.01) * 100)
    top_growing = service_monthly_pivot.nlargest(5, 'growth_pct')[['growth_pct']].reset_index()
    top_growing.columns = ['Service', 'Growth_pct']
    top_declining = service_monthly_pivot.nsmallest(5, 'growth_pct')[['growth_pct']].reset_index()
    top_declining.columns = ['Service', 'Growth_pct']
else:
    top_growing = pd.DataFrame({'Service': [], 'Growth_pct': []})
    top_declining = pd.DataFrame({'Service': [], 'Growth_pct': []})

# High/Low margin services
high_margin = by_service.nlargest(5, 'EBITDA_pct')[['Service_Type', 'EBITDA_pct']].copy()
low_margin = by_service.nsmallest(5, 'EBITDA_pct')[['Service_Type', 'EBITDA_pct']].copy()

# Best/Worst experts
best_experts = by_expert.nlargest(5, 'Net_Profit')[['Expert', 'Net_Profit', 'Orders']].copy()
worst_experts = by_expert.nsmallest(5, 'Net_Profit')[['Expert', 'Net_Profit', 'Orders']].copy()

# Prepare data for JSON serialization
def safe_json(obj):
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj) if not np.isnan(obj) else 0
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    return obj

# Convert all DataFrames to dict records
monthly_records = monthly.to_dict('records')
daily_records = daily.to_dict('records')
category_records = by_category.to_dict('records')
service_records = by_service.to_dict('records')
expert_records = by_expert.to_dict('records')
variant_records = by_variant.to_dict('records')
tat_records = tat_analysis.to_dict('records')
weekend_records = weekend_analysis.to_dict('records')
top_growing_records = top_growing.to_dict('records')
top_declining_records = top_declining.to_dict('records')
high_margin_records = high_margin.to_dict('records')
low_margin_records = low_margin.to_dict('records')
best_expert_records = best_experts.to_dict('records')
worst_expert_records = worst_experts.to_dict('records')

# Cohort summary
cohort_summary = df.groupby(['Cohort_Month', 'Month_Year'])['Customer ID'].nunique().reset_index()
cohort_pivot = cohort_summary.pivot(index='Cohort_Month', columns='Month_Year', values='Customer ID').fillna(0)
cohort_records = []
for idx, row in cohort_pivot.iterrows():
    record = {'Cohort': idx, 'Size': int(row.iloc[0])}
    for i, col in enumerate(row.index[1:], 1):
        record[f'M{i}'] = int(row[col])
    cohort_records.append(record)

# Raw data for filtering (sample - last 100 records for performance)
sample_data = df.tail(100)[['Project No.', 'Create Date', 'Subcat', 'Service Type', 'Variant Name', 
                             'Expert Name', 'Status', 'Net Revenue', 'Gross Profit', 'Net Profit',
                             'Month_Year', 'Customer_Type', 'Has_Discount', 'Weekend Flag']].copy()
sample_data['Create Date'] = sample_data['Create Date'].dt.strftime('%Y-%m-%d')
sample_data['Has_Discount'] = sample_data['Has_Discount'].map({True: 'With Discount', False: 'Without Discount'})
sample_records = sample_data.to_dict('records')

print("All metrics calculated successfully.")

# ============================================================
# STEP 3: BUILD HTML DASHBOARD
# ============================================================
print("Building HTML dashboard...")

html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Eazzy Services | Executive Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
:root {
  --orange: #FF6600;
  --orange-light: #FF8533;
  --orange-dark: #CC5200;
  --green: #22C55E;
  --red: #EF4444;
  --blue: #3B82F6;
  --purple: #8B5CF6;
  --gray-50: #F9FAFB;
  --gray-100: #F3F4F6;
  --gray-200: #E5E7EB;
  --gray-300: #D1D5DB;
  --gray-400: #9CA3AF;
  --gray-500: #6B7280;
  --gray-600: #4B5563;
  --gray-700: #374151;
  --gray-800: #1F2937;
  --gray-900: #111827;
  --sidebar-width: 260px;
  --header-height: 64px;
  --filter-height: 52px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--gray-50);
  color: var(--gray-800);
  overflow-x: hidden;
}

/* Sidebar */
.sidebar {
  position: fixed; left: 0; top: 0; width: var(--sidebar-width); height: 100vh;
  background: var(--gray-900); z-index: 1000; display: flex; flex-direction: column;
  transition: transform 0.3s ease;
}
.sidebar-brand {
  padding: 20px 24px; border-bottom: 1px solid var(--gray-700);
}
.sidebar-brand h2 {
  color: white; font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 10px;
}
.sidebar-brand .logo-icon {
  width: 36px; height: 36px; background: var(--orange); border-radius: 8px;
  display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
}
.sidebar-brand p {
  color: var(--gray-400); font-size: 0.75rem; margin-top: 4px;
}

.sidebar-nav {
  flex: 1; overflow-y: auto; padding: 12px 0;
}
.sidebar-nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 24px; color: var(--gray-400); cursor: pointer;
  font-size: 0.875rem; font-weight: 500; transition: all 0.2s;
  border-left: 3px solid transparent;
}
.sidebar-nav-item:hover { color: white; background: var(--gray-800); }
.sidebar-nav-item.active { color: white; background: var(--gray-800); border-left-color: var(--orange); }
.sidebar-nav-item .icon { font-size: 1.1rem; width: 24px; text-align: center; }

.sidebar-footer {
  padding: 16px 24px; border-top: 1px solid var(--gray-700);
  color: var(--gray-500); font-size: 0.75rem;
}

/* Main Content */
.main-content {
  margin-left: var(--sidebar-width); min-height: 100vh;
}

/* Header */
.top-header {
  height: var(--header-height); background: white;
  border-bottom: 1px solid var(--gray-200);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; position: sticky; top: 0; z-index: 100;
}
.top-header h1 {
  font-size: 1.25rem; font-weight: 700; color: var(--gray-900);
}
.top-header .header-actions {
  display: flex; align-items: center; gap: 12px;
}
.btn {
  padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; border: none; display: inline-flex; align-items: center; gap: 6px;
  transition: all 0.2s;
}
.btn-orange { background: var(--orange); color: white; }
.btn-orange:hover { background: var(--orange-dark); }
.btn-outline {
  background: white; color: var(--gray-600); border: 1px solid var(--gray-300);
}
.btn-outline:hover { background: var(--gray-50); }
.btn-sm { padding: 6px 12px; font-size: 0.8rem; }

/* Filter Bar */
.filter-bar {
  background: white; border-bottom: 1px solid var(--gray-200);
  padding: 10px 24px; display: flex; gap: 12px; overflow-x: auto;
  position: sticky; top: var(--header-height); z-index: 99;
}
.filter-bar::-webkit-scrollbar { height: 4px; }
.filter-bar::-webkit-scrollbar-thumb { background: var(--gray-300); border-radius: 2px; }
.filter-select {
  padding: 6px 10px; border-radius: 6px; border: 1px solid var(--gray-300);
  font-size: 0.8rem; color: var(--gray-700); background: white;
  min-width: 120px; cursor: pointer;
}
.filter-select:focus { outline: none; border-color: var(--orange); }

/* Page Content */
.page { display: none; padding: 24px; }
.page.active { display: block; }

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px; margin-bottom: 24px;
}
.kpi-card {
  background: white; border-radius: 12px; padding: 20px;
  border: 1px solid var(--gray-200); transition: box-shadow 0.2s;
}
.kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.kpi-label {
  font-size: 0.75rem; color: var(--gray-500); font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;
}
.kpi-value {
  font-size: 1.75rem; font-weight: 700; color: var(--gray-900);
}
.kpi-sub {
  font-size: 0.8rem; margin-top: 4px; display: flex; align-items: center; gap: 4px;
}
.kpi-sub.positive { color: var(--green); }
.kpi-sub.negative { color: var(--red); }
.kpi-sub.neutral { color: var(--gray-400); }

/* Chart Grid */
.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px; margin-bottom: 24px;
}
.chart-card {
  background: white; border-radius: 12px; padding: 20px;
  border: 1px solid var(--gray-200);
}
.chart-card.full-width { grid-column: 1 / -1; }
.chart-title {
  font-size: 0.95rem; font-weight: 600; color: var(--gray-800); margin-bottom: 16px;
  display: flex; align-items: center; gap: 8px;
}
.chart-container { position: relative; height: 280px; }
.chart-container.sm { height: 200px; }

/* Tables */
.table-card {
  background: white; border-radius: 12px; padding: 20px;
  border: 1px solid var(--gray-200); overflow-x: auto;
}
.data-table {
  width: 100%; border-collapse: collapse; font-size: 0.85rem;
}
.data-table th {
  text-align: left; padding: 10px 12px; font-weight: 600;
  color: var(--gray-500); border-bottom: 1px solid var(--gray-200);
  text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px;
}
.data-table td {
  padding: 10px 12px; border-bottom: 1px solid var(--gray-100);
  color: var(--gray-700);
}
.data-table tr:hover td { background: var(--gray-50); }
.data-table .text-right { text-align: right; }
.data-table .positive { color: var(--green); font-weight: 600; }
.data-table .negative { color: var(--red); font-weight: 600; }

/* Section Title */
.section-title {
  font-size: 1.1rem; font-weight: 700; color: var(--gray-900);
  margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}

/* Mobile */
.mobile-toggle {
  display: none; position: fixed; top: 16px; left: 16px; z-index: 1001;
  background: var(--orange); color: white; border: none;
  width: 40px; height: 40px; border-radius: 8px; font-size: 1.2rem; cursor: pointer;
}

@media (max-width: 1024px) {
  .sidebar { transform: translateX(-100%); }
  .sidebar.open { transform: translateX(0); }
  .main-content { margin-left: 0; }
  .mobile-toggle { display: flex; align-items: center; justify-content: center; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .chart-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .kpi-grid { grid-template-columns: 1fr; }
  .filter-bar { flex-wrap: wrap; }
}

/* Loading */
.loading-overlay {
  position: fixed; inset: 0; background: rgba(255,255,255,0.9);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  z-index: 9999; transition: opacity 0.3s;
}
.loading-overlay.hidden { opacity: 0; pointer-events: none; }
.spinner {
  width: 48px; height: 48px; border: 4px solid var(--gray-200);
  border-top-color: var(--orange); border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Insights */
.insight-card {
  background: white; border-radius: 12px; padding: 16px;
  border: 1px solid var(--gray-200); margin-bottom: 12px;
  border-left: 4px solid var(--orange);
}
.insight-card.success { border-left-color: var(--green); }
.insight-card.warning { border-left-color: var(--red); }
.insight-card.info { border-left-color: var(--blue); }
.insight-title { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
.insight-text { font-size: 0.85rem; color: var(--gray-600); }

/* Badge */
.badge {
  display: inline-flex; align-items: center; padding: 2px 8px;
  border-radius: 12px; font-size: 0.75rem; font-weight: 500;
}
.badge-green { background: #DCFCE7; color: #166534; }
.badge-red { background: #FEE2E2; color: #991B1B; }
.badge-orange { background: #FFEDD5; color: #9A3412; }
.badge-blue { background: #DBEAFE; color: #1E40AF; }

/* Progress Bar */
.progress-bar {
  width: 100%; height: 8px; background: var(--gray-200); border-radius: 4px; overflow: hidden;
}
.progress-fill {
  height: 100%; border-radius: 4px; transition: width 0.5s ease;
}

/* Two Column Layout */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 1024px) { .two-col { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<!-- Loading -->
<div class="loading-overlay" id="loadingOverlay">
  <div class="spinner"></div>
  <p style="margin-top:16px;color:var(--gray-500);font-size:0.9rem;">Loading Dashboard...</p>
</div>

<!-- Mobile Toggle -->
<button class="mobile-toggle" onclick="toggleSidebar()">☰</button>

<!-- Sidebar -->
<nav class="sidebar" id="sidebar">
  <div class="sidebar-brand">
    <h2><span class="logo-icon">🏠</span> Eazzy Services</h2>
    <p>Executive Dashboard</p>
  </div>
  <div class="sidebar-nav">
    <div class="sidebar-nav-item active" onclick="navigate('executive')" data-page="executive">
      <span class="icon">📊</span> Executive Dashboard
    </div>
    <div class="sidebar-nav-item" onclick="navigate('ebitda')" data-page="ebitda">
      <span class="icon">💰</span> EBITDA & P&L
    </div>
    <div class="sidebar-nav-item" onclick="navigate('experts')" data-page="experts">
      <span class="icon">👨‍🔧</span> Expert Performance
    </div>
    <div class="sidebar-nav-item" onclick="navigate('operations')" data-page="operations">
      <span class="icon">⏱️</span> Operations & TAT
    </div>
    <div class="sidebar-nav-item" onclick="navigate('customers')" data-page="customers">
      <span class="icon">👥</span> Customer Insights
    </div>
    <div class="sidebar-nav-item" onclick="navigate('funnel')" data-page="funnel">
      <span class="icon">🔄</span> Funnel Analysis
    </div>
    <div class="sidebar-nav-item" onclick="navigate('strategic')" data-page="strategic">
      <span class="icon">🎯</span> Strategic Insights
    </div>
    <div class="sidebar-nav-item" onclick="navigate('cohort')" data-page="cohort">
      <span class="icon">📈</span> Cohort Analysis
    </div>
  </div>
  <div class="sidebar-footer">
    <div>Last Updated: <span id="lastUpdated">--</span></div>
    <div style="margin-top:4px;">© 2026 Eazzy Services</div>
  </div>
</nav>

<!-- Main Content -->
<div class="main-content">
  <!-- Header -->
  <header class="top-header">
    <h1 id="pageTitle">Executive Dashboard</h1>
    <div class="header-actions">
      <button class="btn btn-outline btn-sm" onclick="exportPDF()">📄 Export PDF</button>
      <button class="btn btn-orange btn-sm" onclick="refreshData()">🔄 Refresh Data</button>
    </div>
  </header>

  <!-- Filter Bar -->
  <div class="filter-bar">
    <select class="filter-select" id="filterFY" onchange="applyFilters()">
      <option value="">All FY</option>
    </select>
    <select class="filter-select" id="filterQuarter" onchange="applyFilters()">
      <option value="">All Quarters</option>
      <option value="Q1">Q1</option><option value="Q2">Q2</option>
      <option value="Q3">Q3</option><option value="Q4">Q4</option>
    </select>
    <select class="filter-select" id="filterMonth" onchange="applyFilters()">
      <option value="">All Months</option>
    </select>
    <select class="filter-select" id="filterCategory" onchange="applyFilters()">
      <option value="">All Categories</option>
    </select>
    <select class="filter-select" id="filterService" onchange="applyFilters()">
      <option value="">All Services</option>
    </select>
    <select class="filter-select" id="filterExpert" onchange="applyFilters()">
      <option value="">All Experts</option>
    </select>
    <select class="filter-select" id="filterDiscount" onchange="applyFilters()">
      <option value="">All Orders</option>
      <option value="With Discount">With Discount</option>
      <option value="Without Discount">Without Discount</option>
    </select>
    <select class="filter-select" id="filterCustomer" onchange="applyFilters()">
      <option value="">All Customers</option>
      <option value="New">New</option>
      <option value="Repeat">Repeat</option>
    </select>
    <button class="btn btn-outline btn-sm" onclick="resetFilters()">Reset</button>
  </div>

  <!-- PAGE 1: EXECUTIVE DASHBOARD -->
  <div class="page active" id="page-executive">
    <div class="kpi-grid" id="execKPIs"></div>
    <div class="chart-grid">
      <div class="chart-card full-width">
        <div class="chart-title">📈 Monthly Revenue Trend</div>
        <div class="chart-container"><canvas id="chartRevenueTrend"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">🥧 Revenue by Category</div>
        <div class="chart-container"><canvas id="chartCategory"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">📊 Revenue by Service Type</div>
        <div class="chart-container"><canvas id="chartService"></canvas></div>
      </div>
      <div class="chart-card full-width">
        <div class="chart-title">📅 Daily Revenue (Last 30 Days)</div>
        <div class="chart-container"><canvas id="chartDaily"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">🏆 Top Performing Experts</div>
        <div class="chart-container"><canvas id="chartTopExperts"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">🔄 Weekend vs Weekday</div>
        <div class="chart-container"><canvas id="chartWeekend"></canvas></div>
      </div>
    </div>
    <div class="two-col">
      <div class="table-card">
        <div class="chart-title">📋 LMTD vs MTD Comparison</div>
        <table class="data-table" id="tableLMTD"></table>
      </div>
      <div class="table-card">
        <div class="chart-title">📋 Monthly Summary</div>
        <table class="data-table" id="tableMonthly"></table>
      </div>
    </div>
  </div>

  <!-- PAGE 2: EBITDA & P&L -->
  <div class="page" id="page-ebitda">
    <div class="kpi-grid" id="ebitdaKPIs"></div>
    <div class="chart-grid">
      <div class="chart-card full-width">
        <div class="chart-title">💧 P&L Waterfall</div>
        <div class="chart-container"><canvas id="chartWaterfall"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">📊 Monthly EBITDA Trend</div>
        <div class="chart-container"><canvas id="chartEBITDATrend"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">📊 Category EBITDA</div>
        <div class="chart-container"><canvas id="chartCategoryEBITDA"></canvas></div>
      </div>
      <div class="chart-card full-width">
        <div class="chart-title">📋 Service-wise P&L</div>
        <table class="data-table" id="tableServicePNL"></table>
      </div>
    </div>
  </div>

  <!-- PAGE 3: EXPERT PERFORMANCE -->
  <div class="page" id="page-experts">
    <div class="kpi-grid" id="expertKPIs"></div>
    <div class="chart-grid">
      <div class="chart-card">
        <div class="chart-title">🏆 Top Experts by Revenue</div>
        <div class="chart-container"><canvas id="chartExpertRevenue"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">⭐ Expert Ratings</div>
        <div class="chart-container"><canvas id="chartExpertRating"></canvas></div>
      </div>
      <div class="chart-card full-width">
        <div class="chart-title">📋 Expert Performance Matrix</div>
        <table class="data-table" id="tableExperts"></table>
      </div>
    </div>
  </div>

  <!-- PAGE 4: OPERATIONS & TAT -->
  <div class="page" id="page-operations">
    <div class="kpi-grid" id="opsKPIs"></div>
    <div class="chart-grid">
      <div class="chart-card">
        <div class="chart-title">⏱️ TAT Distribution</div>
        <div class="chart-container"><canvas id="chartTAT"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">📊 Operations by Day</div>
        <div class="chart-container"><canvas id="chartOpsDay"></canvas></div>
      </div>
    </div>
  </div>

  <!-- PAGE 5: CUSTOMER INSIGHTS -->
  <div class="page" id="page-customers">
    <div class="kpi-grid" id="customerKPIs"></div>
    <div class="chart-grid">
      <div class="chart-card">
        <div class="chart-title">👥 New vs Repeat Customers</div>
        <div class="chart-container"><canvas id="chartCustomerType"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">🎁 Discount vs Non-Discount</div>
        <div class="chart-container"><canvas id="chartDiscount"></canvas></div>
      </div>
    </div>
  </div>

  <!-- PAGE 6: FUNNEL ANALYSIS -->
  <div class="page" id="page-funnel">
    <div class="kpi-grid" id="funnelKPIs"></div>
    <div class="chart-grid">
      <div class="chart-card full-width">
        <div class="chart-title">🔄 Order Funnel</div>
        <div class="chart-container"><canvas id="chartFunnel"></canvas></div>
      </div>
    </div>
  </div>

  <!-- PAGE 7: STRATEGIC INSIGHTS -->
  <div class="page" id="page-strategic">
    <div class="section-title">🚀 Strategic Insights & Recommendations</div>
    <div id="insightsContainer"></div>
    <div class="two-col" style="margin-top:24px;">
      <div class="table-card">
        <div class="chart-title">📈 Top Growing Services</div>
        <table class="data-table" id="tableGrowing"></table>
      </div>
      <div class="table-card">
        <div class="chart-title">📉 Declining Services</div>
        <table class="data-table" id="tableDeclining"></table>
      </div>
    </div>
    <div class="two-col" style="margin-top:16px;">
      <div class="table-card">
        <div class="chart-title">💚 High Margin Services</div>
        <table class="data-table" id="tableHighMargin"></table>
      </div>
      <div class="table-card">
        <div class="chart-title">❤️ Low Margin Services</div>
        <table class="data-table" id="tableLowMargin"></table>
      </div>
    </div>
  </div>

  <!-- PAGE 8: COHORT ANALYSIS -->
  <div class="page" id="page-cohort">
    <div class="kpi-grid" id="cohortKPIs"></div>
    <div class="chart-grid">
      <div class="chart-card full-width">
        <div class="chart-title">👥 Customer Cohort Retention</div>
        <div class="chart-container"><canvas id="chartCohort"></canvas></div>
      </div>
      <div class="table-card full-width">
        <div class="chart-title">📋 Cohort Retention Matrix</div>
        <table class="data-table" id="tableCohort"></table>
      </div>
    </div>
  </div>
</div>

<script>
// ============================================================
// EMBEDDED DATA - AUTO-GENERATED FROM REVENUE EXCEL
// ============================================================
const DASHBOARD_DATA = ''' + json.dumps({
    "timestamp": datetime.now().isoformat(),
    "filter_options": filter_options,
    "global_kpis": {
        "total_revenue": round(total_revenue, 2),
        "total_orders": int(total_orders),
        "total_customers": int(total_customers),
        "total_gross_profit": round(total_gross_profit, 2),
        "total_net_profit": round(total_net_profit, 2),
        "total_ebitda": round(total_ebitda, 2),
        "avg_order_value": round(avg_order_value, 2),
        "gross_margin_pct": round(gross_margin_pct, 2),
        "net_margin_pct": round(net_margin_pct, 2),
        "ebitda_pct": round(ebitda_pct, 2),
        "total_discount": round(total_discount, 2),
        "discount_pct": round(discount_pct, 2),
        "repeat_pct": round(repeat_pct, 2),
        "avg_rating": round(avg_rating, 2)
    },
    "monthly": monthly_records,
    "daily": daily_records,
    "by_category": category_records,
    "by_service": service_records,
    "by_expert": expert_records,
    "by_variant": variant_records,
    "tat": tat_records,
    "weekend": weekend_records,
    "lmtd": lmtd_comparison,
    "cohort": cohort_records,
    "top_growing": top_growing_records,
    "top_declining": top_declining_records,
    "high_margin": high_margin_records,
    "low_margin": low_margin_records,
    "best_experts": best_expert_records,
    "worst_experts": worst_expert_records,
    "sample_data": sample_records
}, default=str) + ''';

// ============================================================
// UTILITY FUNCTIONS
// ============================================================
const fmtINR = n => n == null || isNaN(n) ? '-' : '₹' + (+n).toLocaleString('en-IN', {maximumFractionDigits: 0});
const fmtNum = n => n == null || isNaN(n) ? '-' : (+n).toLocaleString('en-IN', {maximumFractionDigits: 1});
const fmtPct = n => n == null || isNaN(n) ? '-' : (+n).toFixed(1) + '%';
const fmtRound = n => n == null || isNaN(n) ? '-' : Math.round(+n).toLocaleString('en-IN');

let chartInstances = {};
let currentPage = 'executive';

// ============================================================
// NAVIGATION
// ============================================================
function navigate(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sidebar-nav-item').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelector('.sidebar-nav-item[data-page="' + page + '"]').classList.add('active');
  
  const titles = {
    executive: 'Executive Dashboard',
    ebitda: 'EBITDA & P&L',
    experts: 'Expert Performance',
    operations: 'Operations & TAT',
    customers: 'Customer Insights',
    funnel: 'Funnel Analysis',
    strategic: 'Strategic Insights',
    cohort: 'Cohort Analysis'
  };
  document.getElementById('pageTitle').textContent = titles[page];
  
  // Render page-specific charts
  setTimeout(() => renderPageCharts(page), 50);
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ============================================================
// FILTERS
// ============================================================
function initFilters() {
  const opts = DASHBOARD_DATA.filter_options;
  const addOpts = (selId, items) => {
    const sel = document.getElementById(selId);
    items.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item; opt.textContent = item;
      sel.appendChild(opt);
    });
  };
  addOpts('filterFY', opts.fy);
  addOpts('filterMonth', opts.month);
  addOpts('filterCategory', opts.category);
  addOpts('filterService', opts.service_type);
  addOpts('filterExpert', opts.expert);
}

function applyFilters() {
  // In a full implementation, this would re-filter the data
  // For now, we show all data (embedded snapshot)
  console.log('Filters applied');
}

function resetFilters() {
  document.querySelectorAll('.filter-select').forEach(s => s.value = '');
  applyFilters();
}

// ============================================================
// CHART RENDERERS
// ============================================================
function destroyCharts() {
  Object.values(chartInstances).forEach(c => c.destroy());
  chartInstances = {};
}

function renderPageCharts(page) {
  destroyCharts();
  if (page === 'executive') renderExecutiveCharts();
  if (page === 'ebitda') renderEBITDACharts();
  if (page === 'experts') renderExpertCharts();
  if (page === 'operations') renderOpsCharts();
  if (page === 'customers') renderCustomerCharts();
  if (page === 'funnel') renderFunnelCharts();
  if (page === 'cohort') renderCohortCharts();
}

function renderExecutiveCharts() {
  const d = DASHBOARD_DATA;
  
  // Monthly Revenue Trend
  chartInstances.revenueTrend = new Chart(document.getElementById('chartRevenueTrend'), {
    type: 'bar',
    data: {
      labels: d.monthly.map(m => m.Month),
      datasets: [
        { label: 'Revenue', data: d.monthly.map(m => m.Revenue), backgroundColor: '#FF6600', borderRadius: 4 },
        { label: 'Gross Profit', data: d.monthly.map(m => m.Gross_Profit), backgroundColor: '#22C55E', borderRadius: 4 },
        { label: 'EBITDA', data: d.monthly.map(m => m.EBITDA), backgroundColor: '#3B82F6', borderRadius: 4 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } },
      scales: { y: { ticks: { callback: v => '₹' + (v/1000).toFixed(0) + 'K' } } } }
  });
  
  // Category Pie
  chartInstances.category = new Chart(document.getElementById('chartCategory'), {
    type: 'doughnut',
    data: { labels: d.by_category.map(c => c.Category), datasets: [{ data: d.by_category.map(c => c.Revenue), backgroundColor: ['#FF6600','#3B82F6','#22C55E','#8B5CF6','#EF4444','#F59E0B','#06B6D4','#EC4899'] }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
  });
  
  // Service Bar
  chartInstances.service = new Chart(document.getElementById('chartService'), {
    type: 'bar',
    data: { labels: d.by_service.slice(0,8).map(s => s.Service_Type.length > 20 ? s.Service_Type.substring(0,20)+'...' : s.Service_Type), datasets: [{ label: 'Revenue', data: d.by_service.slice(0,8).map(s => s.Revenue), backgroundColor: '#FF6600', borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
  });
  
  // Daily Trend (last 30)
  const last30 = d.daily.slice(-30);
  chartInstances.daily = new Chart(document.getElementById('chartDaily'), {
    type: 'line',
    data: { labels: last30.map(d => d.Date_Str.substring(5)), datasets: [{ label: 'Revenue', data: last30.map(d => d.Revenue), borderColor: '#FF6600', backgroundColor: 'rgba(255,102,0,0.1)', fill: true, tension: 0.3 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
  });
  
  // Top Experts
  chartInstances.topExperts = new Chart(document.getElementById('chartTopExperts'), {
    type: 'bar',
    data: { labels: d.by_expert.slice(0,8).map(e => e.Expert.length > 15 ? e.Expert.substring(0,15)+'...' : e.Expert), datasets: [{ label: 'Revenue', data: d.by_expert.slice(0,8).map(e => e.Revenue), backgroundColor: '#3B82F6', borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
  });
  
  // Weekend
  chartInstances.weekend = new Chart(document.getElementById('chartWeekend'), {
    type: 'pie',
    data: { labels: d.weekend.map(w => w.Flag), datasets: [{ data: d.weekend.map(w => w.Orders), backgroundColor: ['#3B82F6','#F59E0B'] }] },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderEBITDACharts() {
  const d = DASHBOARD_DATA;
  
  // EBITDA Trend
  chartInstances.ebitdaTrend = new Chart(document.getElementById('chartEBITDATrend'), {
    type: 'bar',
    data: { labels: d.monthly.map(m => m.Month), datasets: [
      { label: 'EBITDA', data: d.monthly.map(m => m.EBITDA), backgroundColor: '#22C55E', borderRadius: 4 },
      { label: 'Net Profit', data: d.monthly.map(m => m.Net_Profit), backgroundColor: '#3B82F6', borderRadius: 4 }
    ]},
    options: { responsive: true, maintainAspectRatio: false }
  });
  
  // Category EBITDA
  chartInstances.catEBITDA = new Chart(document.getElementById('chartCategoryEBITDA'), {
    type: 'bar',
    data: { labels: d.by_category.map(c => c.Category), datasets: [{ label: 'Gross Profit', data: d.by_category.map(c => c.Gross_Profit), backgroundColor: '#FF6600', borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderExpertCharts() {
  const d = DASHBOARD_DATA;
  
  chartInstances.expRev = new Chart(document.getElementById('chartExpertRevenue'), {
    type: 'bar',
    data: { labels: d.by_expert.slice(0,10).map(e => e.Expert.length > 12 ? e.Expert.substring(0,12)+'...' : e.Expert), datasets: [{ label: 'Revenue', data: d.by_expert.slice(0,10).map(e => e.Revenue), backgroundColor: '#FF6600', borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
  });
  
  chartInstances.expRating = new Chart(document.getElementById('chartExpertRating'), {
    type: 'bar',
    data: { labels: d.by_expert.slice(0,10).map(e => e.Expert.length > 12 ? e.Expert.substring(0,12)+'...' : e.Expert), datasets: [{ label: 'Rating', data: d.by_expert.slice(0,10).map(e => e.Avg_Rating), backgroundColor: '#F59E0B', borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { max: 5 } } }
  });
}

function renderOpsCharts() {
  const d = DASHBOARD_DATA;
  
  chartInstances.tat = new Chart(document.getElementById('chartTAT'), {
    type: 'doughnut',
    data: { labels: d.tat.map(t => t.TAT_Status), datasets: [{ data: d.tat.map(t => t.Orders), backgroundColor: ['#22C55E','#EF4444'] }] },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderCustomerCharts() {
  const d = DASHBOARD_DATA;
  
  // Customer type breakdown from sample data
  const newCount = d.sample_data.filter(r => r.Customer_Type === 'New').length;
  const repeatCount = d.sample_data.filter(r => r.Customer_Type === 'Repeat').length;
  
  chartInstances.custType = new Chart(document.getElementById('chartCustomerType'), {
    type: 'doughnut',
    data: { labels: ['New', 'Repeat'], datasets: [{ data: [newCount, repeatCount], backgroundColor: ['#3B82F6','#FF6600'] }] },
    options: { responsive: true, maintainAspectRatio: false }
  });
  
  const discCount = d.sample_data.filter(r => r.Has_Discount === 'With Discount').length;
  const noDiscCount = d.sample_data.filter(r => r.Has_Discount === 'Without Discount').length;
  
  chartInstances.discount = new Chart(document.getElementById('chartDiscount'), {
    type: 'doughnut',
    data: { labels: ['With Discount', 'Without Discount'], datasets: [{ data: [discCount, noDiscCount], backgroundColor: ['#EF4444','#22C55E'] }] },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderFunnelCharts() {
  // Simple funnel showing all orders are COMPLETED
  chartInstances.funnel = new Chart(document.getElementById('chartFunnel'), {
    type: 'bar',
    data: { labels: ['Created', 'Assigned', 'Completed'], datasets: [{ label: 'Orders', data: [DASHBOARD_DATA.global_kpis.total_orders, DASHBOARD_DATA.global_kpis.total_orders, DASHBOARD_DATA.global_kpis.total_orders], backgroundColor: ['#9CA3AF','#F59E0B','#22C55E'], borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
  });
}

function renderCohortCharts() {
  const d = DASHBOARD_DATA;
  
  // Cohort heatmap as stacked bar
  const cohortLabels = d.cohort.map(c => c.Cohort);
  const datasets = [];
  const colors = ['#FF6600','#FF8533','#FFB366','#FFD9B3'];
  
  ['M1','M2','M3'].forEach((m, i) => {
    datasets.push({
      label: m,
      data: d.cohort.map(c => c[m] || 0),
      backgroundColor: colors[i] || colors[colors.length-1]
    });
  });
  
  chartInstances.cohort = new Chart(document.getElementById('chartCohort'), {
    type: 'bar',
    data: { labels: cohortLabels, datasets: datasets },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } } }
  });
}

// ============================================================
// TABLE RENDERERS
// ============================================================
function renderTables() {
  const d = DASHBOARD_DATA;
  
  // LMTD Table
  const lmtd = d.lmtd;
  document.getElementById('tableLMTD').innerHTML = `
    <thead><tr><th>Metric</th><th class="text-right">MTD (${lmtd.current_month})</th><th class="text-right">LMTD (${lmtd.prev_month})</th><th class="text-right">Variance</th></tr></thead>
    <tbody>
      <tr><td>Revenue</td><td class="text-right">${fmtINR(lmtd.mtd.revenue)}</td><td class="text-right">${fmtINR(lmtd.lmtd.revenue)}</td><td class="text-right ${lmtd.mtd.revenue >= lmtd.lmtd.revenue ? 'positive' : 'negative'}">${((lmtd.mtd.revenue - lmtd.lmtd.revenue) / lmtd.lmtd.revenue * 100).toFixed(1)}%</td></tr>
      <tr><td>Orders</td><td class="text-right">${fmtRound(lmtd.mtd.orders)}</td><td class="text-right">${fmtRound(lmtd.lmtd.orders)}</td><td class="text-right ${lmtd.mtd.orders >= lmtd.lmtd.orders ? 'positive' : 'negative'}">${((lmtd.mtd.orders - lmtd.lmtd.orders) / lmtd.lmtd.orders * 100).toFixed(1)}%</td></tr>
      <tr><td>Customers</td><td class="text-right">${fmtRound(lmtd.mtd.customers)}</td><td class="text-right">${fmtRound(lmtd.lmtd.customers)}</td><td class="text-right ${lmtd.mtd.customers >= lmtd.lmtd.customers ? 'positive' : 'negative'}">${((lmtd.mtd.customers - lmtd.lmtd.customers) / (lmtd.lmtd.customers || 1) * 100).toFixed(1)}%</td></tr>
      <tr><td>Gross Profit</td><td class="text-right">${fmtINR(lmtd.mtd.gross_profit)}</td><td class="text-right">${fmtINR(lmtd.lmtd.gross_profit)}</td><td class="text-right ${lmtd.mtd.gross_profit >= lmtd.lmtd.gross_profit ? 'positive' : 'negative'}">${((lmtd.mtd.gross_profit - lmtd.lmtd.gross_profit) / (lmtd.lmtd.gross_profit || 1) * 100).toFixed(1)}%</td></tr>
      <tr><td>Net Profit</td><td class="text-right">${fmtINR(lmtd.mtd.net_profit)}</td><td class="text-right">${fmtINR(lmtd.lmtd.net_profit)}</td><td class="text-right ${lmtd.mtd.net_profit >= lmtd.lmtd.net_profit ? 'positive' : 'negative'}">${((lmtd.mtd.net_profit - lmtd.lmtd.net_profit) / (lmtd.lmtd.net_profit || 1) * 100).toFixed(1)}%</td></tr>
      <tr><td>EBITDA</td><td class="text-right">${fmtINR(lmtd.mtd.ebitda)}</td><td class="text-right">${fmtINR(lmtd.lmtd.ebitda)}</td><td class="text-right ${lmtd.mtd.ebitda >= lmtd.lmtd.ebitda ? 'positive' : 'negative'}">${((lmtd.mtd.ebitda - lmtd.lmtd.ebitda) / (lmtd.lmtd.ebitda || 1) * 100).toFixed(1)}%</td></tr>
    </tbody>`;
  
  // Monthly Summary
  document.getElementById('tableMonthly').innerHTML = `
    <thead><tr><th>Month</th><th class="text-right">Orders</th><th class="text-right">Revenue</th><th class="text-right">Gross Profit</th><th class="text-right">EBITDA</th><th class="text-right">Margin</th></tr></thead>
    <tbody>${d.monthly.map(m => `<tr><td><strong>${m.Month}</strong></td><td class="text-right">${fmtRound(m.Orders)}</td><td class="text-right">${fmtINR(m.Revenue)}</td><td class="text-right">${fmtINR(m.Gross_Profit)}</td><td class="text-right">${fmtINR(m.EBITDA)}</td><td class="text-right">${((m.Gross_Profit/m.Revenue)*100).toFixed(1)}%</td></tr>`).join('')}</tbody>`;
  
  // Service P&L
  document.getElementById('tableServicePNL').innerHTML = `
    <thead><tr><th>Service Type</th><th class="text-right">Orders</th><th class="text-right">Revenue</th><th class="text-right">Gross Profit</th><th class="text-right">Net Profit</th><th class="text-right">EBITDA %</th></tr></thead>
    <tbody>${d.by_service.map(s => `<tr><td>${s.Service_Type}</td><td class="text-right">${fmtRound(s.Orders)}</td><td class="text-right">${fmtINR(s.Revenue)}</td><td class="text-right">${fmtINR(s.Gross_Profit)}</td><td class="text-right ${s.Net_Profit >= 0 ? 'positive' : 'negative'}">${fmtINR(s.Net_Profit)}</td><td class="text-right">${s.EBITDA_pct.toFixed(1)}%</td></tr>`).join('')}</tbody>`;
  
  // Expert Table
  document.getElementById('tableExperts').innerHTML = `
    <thead><tr><th>Expert</th><th class="text-right">Orders</th><th class="text-right">Revenue</th><th class="text-right">Gross Profit</th><th class="text-right">Net Profit</th><th class="text-right">Rating</th></tr></thead>
    <tbody>${d.by_expert.map(e => `<tr><td><strong>${e.Expert}</strong></td><td class="text-right">${fmtRound(e.Orders)}</td><td class="text-right">${fmtINR(e.Revenue)}</td><td class="text-right">${fmtINR(e.Gross_Profit)}</td><td class="text-right ${e.Net_Profit >= 0 ? 'positive' : 'negative'}">${fmtINR(e.Net_Profit)}</td><td class="text-right">${e.Avg_Rating ? e.Avg_Rating.toFixed(1) : '-'}</td></tr>`).join('')}</tbody>`;
  
  // Cohort Table
  document.getElementById('tableCohort').innerHTML = `
    <thead><tr><th>Cohort</th><th class="text-right">Size</th><th class="text-right">M1</th><th class="text-right">M2</th><th class="text-right">M3</th></tr></thead>
    <tbody>${d.cohort.map(c => `<tr><td><strong>${c.Cohort}</strong></td><td class="text-right">${c.Size}</td><td class="text-right">${c.M1 || '-'}</td><td class="text-right">${c.M2 || '-'}</td><td class="text-right">${c.M3 || '-'}</td></tr>`).join('')}</tbody>`;
  
  // Strategic Tables
  document.getElementById('tableGrowing').innerHTML = `<thead><tr><th>Service</th><th class="text-right">Growth %</th></tr></thead><tbody>${d.top_growing.map(r => `<tr><td>${r.Service}</td><td class="text-right positive">+${r.Growth_pct.toFixed(1)}%</td></tr>`).join('')}</tbody>`;
  document.getElementById('tableDeclining').innerHTML = `<thead><tr><th>Service</th><th class="text-right">Growth %</th></tr></thead><tbody>${d.top_declining.map(r => `<tr><td>${r.Service}</td><td class="text-right negative">${r.Growth_pct.toFixed(1)}%</td></tr>`).join('')}</tbody>`;
  document.getElementById('tableHighMargin').innerHTML = `<thead><tr><th>Service</th><th class="text-right">EBITDA %</th></tr></thead><tbody>${d.high_margin.map(r => `<tr><td>${r.Service_Type}</td><td class="text-right positive">${r.EBITDA_pct.toFixed(1)}%</td></tr>`).join('')}</tbody>`;
  document.getElementById('tableLowMargin').innerHTML = `<thead><tr><th>Service</th><th class="text-right">EBITDA %</th></tr></thead><tbody>${d.low_margin.map(r => `<tr><td>${r.Service_Type}</td><td class="text-right negative">${r.EBITDA_pct.toFixed(1)}%</td></tr>`).join('')}</tbody>`;
}

// ============================================================
// KPI CARDS
// ============================================================
function renderKPIs() {
  const k = DASHBOARD_DATA.global_kpis;
  
  // Executive KPIs
  document.getElementById('execKPIs').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Total Revenue</div><div class="kpi-value" style="color:#FF6600">${fmtINR(k.total_revenue)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Total Orders</div><div class="kpi-value">${fmtRound(k.total_orders)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Customers</div><div class="kpi-value">${fmtRound(k.total_customers)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Gross Profit</div><div class="kpi-value" style="color:#22C55E">${fmtINR(k.total_gross_profit)}</div></div>
    <div class="kpi-card"><div class="kpi-label">EBITDA</div><div class="kpi-value" style="color:#3B82F6">${fmtINR(k.total_ebitda)}</div></div>
    <div class="kpi-card"><div class="kpi-label">EBITDA %</div><div class="kpi-value" style="color:${k.ebitda_pct >= 0 ? '#22C55E' : '#EF4444'}">${fmtPct(k.ebitda_pct)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Avg Order Value</div><div class="kpi-value">${fmtINR(k.avg_order_value)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Gross Margin</div><div class="kpi-value" style="color:${k.gross_margin_pct >= 0 ? '#22C55E' : '#EF4444'}">${fmtPct(k.gross_margin_pct)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Discount %</div><div class="kpi-value" style="color:${k.discount_pct > 15 ? '#EF4444' : '#F59E0B'}">${fmtPct(k.discount_pct)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Repeat %</div><div class="kpi-value" style="color:#3B82F6">${fmtPct(k.repeat_pct)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Customer Rating</div><div class="kpi-value" style="color:${k.avg_rating >= 4 ? '#22C55E' : k.avg_rating >= 3 ? '#F59E0B' : '#EF4444'}">${k.avg_rating.toFixed(1)} / 5</div></div>
    <div class="kpi-card"><div class="kpi-label">Net Profit</div><div class="kpi-value" style="color:${k.net_margin_pct >= 0 ? '#22C55E' : '#EF4444'}">${fmtINR(k.total_net_profit)}</div></div>
  `;
  
  // EBITDA KPIs
  document.getElementById('ebitdaKPIs').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Revenue</div><div class="kpi-value" style="color:#FF6600">${fmtINR(k.total_revenue)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Gross Profit</div><div class="kpi-value" style="color:#22C55E">${fmtINR(k.total_gross_profit)}</div></div>
    <div class="kpi-card"><div class="kpi-label">EBITDA</div><div class="kpi-value" style="color:#3B82F6">${fmtINR(k.total_ebitda)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Net Profit</div><div class="kpi-value" style="color:${k.net_margin_pct >= 0 ? '#22C55E' : '#EF4444'}">${fmtINR(k.total_net_profit)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Gross Margin</div><div class="kpi-value">${fmtPct(k.gross_margin_pct)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Net Margin</div><div class="kpi-value" style="color:${k.net_margin_pct >= 0 ? '#22C55E' : '#EF4444'}">${fmtPct(k.net_margin_pct)}</div></div>
  `;
  
  // Expert KPIs
  const topExpert = DASHBOARD_DATA.by_expert[0];
  document.getElementById('expertKPIs').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Total Experts</div><div class="kpi-value">${DASHBOARD_DATA.by_expert.length}</div></div>
    <div class="kpi-card"><div class="kpi-label">Top Expert</div><div class="kpi-value" style="font-size:1.1rem">${topExpert.Expert.substring(0,15)}</div><div class="kpi-sub">${fmtINR(topExpert.Revenue)} revenue</div></div>
    <div class="kpi-card"><div class="kpi-label">Avg Expert Revenue</div><div class="kpi-value">${fmtINR(topExpert.Revenue)}</div></div>
  `;
  
  // Ops KPIs
  document.getElementById('opsKPIs').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Total Jobs</div><div class="kpi-value">${fmtRound(k.total_orders)}</div></div>
    <div class="kpi-card"><div class="kpi-label">On-Time %</div><div class="kpi-value" style="color:#22C55E">${fmtPct(DASHBOARD_DATA.tat.find(t => t.TAT_Status === 'ontime')?.Orders / k.total_orders * 100 || 0)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Late %</div><div class="kpi-value" style="color:#EF4444">${fmtPct(DASHBOARD_DATA.tat.find(t => t.TAT_Status === 'late')?.Orders / k.total_orders * 100 || 0)}</div></div>
  `;
  
  // Customer KPIs
  document.getElementById('customerKPIs').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Total Customers</div><div class="kpi-value">${fmtRound(k.total_customers)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Repeat Customers</div><div class="kpi-value" style="color:#FF6600">${fmtRound(Math.round(k.total_customers * k.repeat_pct / 100))}</div></div>
    <div class="kpi-card"><div class="kpi-label">Retention %</div><div class="kpi-value" style="color:#22C55E">${fmtPct(k.repeat_pct)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Avg Revenue/Customer</div><div class="kpi-value">${fmtINR(k.total_revenue / k.total_customers)}</div></div>
  `;
  
  // Funnel KPIs
  document.getElementById('funnelKPIs').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Total Appointments</div><div class="kpi-value">${fmtRound(k.total_orders)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Completed</div><div class="kpi-value" style="color:#22C55E">${fmtRound(k.total_orders)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Conversion %</div><div class="kpi-value" style="color:#22C55E">100%</div></div>
  `;
  
  // Cohort KPIs
  document.getElementById('cohortKPIs').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Total Cohorts</div><div class="kpi-value">${DASHBOARD_DATA.cohort.length}</div></div>
    <div class="kpi-card"><div class="kpi-label">Total Customers</div><div class="kpi-value">${fmtRound(k.total_customers)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Latest Cohort</div><div class="kpi-value">${DASHBOARD_DATA.cohort[DASHBOARD_DATA.cohort.length-1]?.Cohort || '-'}</div></div>
  `;
}

// ============================================================
// STRATEGIC INSIGHTS
// ============================================================
function renderInsights() {
  const d = DASHBOARD_DATA;
  const k = d.global_kpis;
  const insights = [];
  
  // Revenue insights
  insights.push({type:'info', title:'📊 Revenue Overview', text:`Total revenue of ${fmtINR(k.total_revenue)} from ${fmtRound(k.total_orders)} orders. Average order value is ${fmtINR(k.avg_order_value)}.`});
  
  // Margin insights
  if (k.gross_margin_pct < 30) {
    insights.push({type:'warning', title:'⚠️ Low Gross Margin', text:`Gross margin is ${fmtPct(k.gross_margin_pct)}, below 30%. Review pricing and cost structure.`});
  } else {
    insights.push({type:'success', title:'✅ Healthy Gross Margin', text:`Gross margin at ${fmtPct(k.gross_margin_pct)} is healthy.`});
  }
  
  // Discount insights
  if (k.discount_pct > 20) {
    insights.push({type:'warning', title:'⚠️ High Discount Rate', text:`Discount rate is ${fmtPct(k.discount_pct)}. Total discounts given: ${fmtINR(k.total_discount)}.`});
  }
  
  // EBITDA insights
  if (k.ebitda_pct < 0) {
    insights.push({type:'warning', title:'🚨 Negative EBITDA', text:`EBITDA is negative at ${fmtINR(k.total_ebitda)}. Immediate cost review needed.`});
  }
  
  // Rating insights
  if (k.avg_rating < 3) {
    insights.push({type:'warning', title:'⭐ Low Customer Rating', text:`Average rating is ${k.avg_rating.toFixed(1)}/5. Focus on service quality improvement.`});
  }
  
  // Top/bottom services
  if (d.top_growing.length > 0) {
    insights.push({type:'success', title:'🚀 Growing Service', text:`${d.top_growing[0].Service} is growing at +${d.top_growing[0].Growth_pct.toFixed(1)}% MoM.`});
  }
  if (d.top_declining.length > 0) {
    insights.push({type:'warning', title:'📉 Declining Service', text:`${d.top_declining[0].Service} is declining at ${d.top_declining[0].Growth_pct.toFixed(1)}% MoM.`});
  }
  
  // Expert insights
  if (d.best_experts.length > 0) {
    insights.push({type:'success', title:'🏆 Top Expert', text:`${d.best_experts[0].Expert} generated ${fmtINR(d.best_experts[0].Net_Profit)} profit.`});
  }
  if (d.worst_experts.length > 0) {
    insights.push({type:'warning', title:'⚠️ Attention Needed', text:`${d.worst_experts[0].Expert} has negative profit of ${fmtINR(d.worst_experts[0].Net_Profit)}.`});
  }
  
  document.getElementById('insightsContainer').innerHTML = insights.map(i => `
    <div class="insight-card ${i.type}">
      <div class="insight-title">${i.title}</div>
      <div class="insight-text">${i.text}</div>
    </div>
  `).join('');
}

// ============================================================
// EXPORT & REFRESH
// ============================================================
function exportPDF() {
  alert('PDF Export: Use browser print (Ctrl+P) and select "Save as PDF" for best results.');
}

function refreshData() {
  document.getElementById('loadingOverlay').classList.remove('hidden');
  setTimeout(() => {
    location.reload();
  }, 500);
}

// ============================================================
// INITIALIZATION
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('lastUpdated').textContent = new Date(DASHBOARD_DATA.timestamp).toLocaleString();
  initFilters();
  renderKPIs();
  renderTables();
  renderInsights();
  renderPageCharts('executive');
  
  setTimeout(() => {
    document.getElementById('loadingOverlay').classList.add('hidden');
  }, 800);
});
</script>
</body>
</html>'''

# Write the file
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"\n✅ Dashboard generated successfully!")
print(f"📁 Output: {OUTPUT_PATH}")
print(f"📊 Data: {len(df)} records from Revenue sheet")
print(f"🎨 Theme: Bajaj Orange (#FF6600)")
print(f"📄 Pages: 8 (Executive, EBITDA, Experts, Operations, Customers, Funnel, Strategic, Cohort)")
print(f"\nNext steps:")
print(f"  1. Open {OUTPUT_PATH} in your browser")
print(f"  2. Or upload to GitHub Pages for live access")

#!/usr/bin/env python3
"""
Eazzy Dashboard - Data Refresh Script (v4 with FOC + Franchise)
Usage: python update_dashboard.py
"""
import json, os, time, requests, pandas as pd, numpy as np
from datetime import datetime, timedelta
from operator import attrgetter

# ── CONFIG ──
BASE_URL = "https://redash.tryeazzy.in"
QUERY_ID = 17
USER_API_KEY = os.environ.get("REDASH_API_KEY", "JKLi4Tj1CDRTka1B2WsgetcE7STI7n7GvbcYV4L6")
OUTPUT_FILE = "data.js"
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        cfg = json.load(f)
    return cfg['service_prices'], cfg['manpower_costs'], cfg.get('fuel_cost_per_order', 0)

def fetch_redash():
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = "2026-04-01"
    headers = {"Authorization": f"Key {USER_API_KEY}"}
    refresh_url = f"{BASE_URL}/api/queries/{QUERY_ID}/refresh?p_start_date={start_date}&p_end_date={end_date}"
    
    print(f"🚀 Fetching Redash: {start_date} to {end_date}")
    
    for attempt in range(3):
        try:
            resp = requests.post(refresh_url, headers=headers, json={}, timeout=30)
            resp.raise_for_status()
            break
        except requests.exceptions.ConnectTimeout:
            print(f"   ⏳ Timeout (attempt {attempt+1}/3), retrying in 10s...")
            time.sleep(10)
    else:
        raise Exception("Redash connection failed after 3 attempts")
    
    job_id = resp.json()["job"]["id"]
    
    for _ in range(40):
        try:
            job = requests.get(f"{BASE_URL}/api/jobs/{job_id}?api_key={USER_API_KEY}", timeout=30).json()["job"]
        except requests.exceptions.ConnectTimeout:
            time.sleep(5)
            continue
        if job["status"] == 3:
            result_id = job["query_result_id"]
            break
        elif job["status"] == 4:
            raise Exception(f"Query failed: {job.get('error')}")
        time.sleep(3)
    else:
        raise Exception("Timeout waiting for query")
    
    data = requests.get(f"{BASE_URL}/api/query_results/{result_id}?api_key={USER_API_KEY}", timeout=30).json()
    df = pd.DataFrame(data["query_result"]["data"]["rows"])
    print(f"✅ Fetched {len(df)} rows")
    return df

def parse_time(t):
    if pd.isna(t) or t == '' or t is None:
        return None
    if isinstance(t, str):
        try:
            t = t.strip()
            parts = t.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s_part = parts[2] if len(parts) > 2 else "0"
            s_float = float(s_part)
            s = int(s_float)
            ms = int(round((s_float - s) * 1000000))
            return timedelta(hours=h, minutes=m, seconds=s, microseconds=ms)
        except:
            return None
    return None

def apply_formulas(df, service_prices, manpower_costs, fuel_cost_per_order):
    # Base calculations
    df['Consumable'] = df['Service Type'].map(service_prices).fillna(0) * df['Unique Articles'].fillna(0)
    df['Labor Cost Per Article'] = df['Service Type'].map(manpower_costs).fillna(0)
    df['Labor Cost & Travel cost'] = df['Labor Cost Per Article'] * df['Unique Articles'].fillna(0)
    df['Fuel Cost'] = fuel_cost_per_order
    
    df['Gross Profit'] = df['Net Revenue'].fillna(0) - df['Spare Input Price'].fillna(0) - df['Consumable'].fillna(0)
    df['Net Profit'] = df['Gross Profit'] - df['Labor Cost & Travel cost'] - df['Fuel Cost']
    
    # Dates
    df['Create Date'] = pd.to_datetime(df['Create Date'], errors='coerce')
    df['Post Job Done Date'] = pd.to_datetime(df['Post Job Done Date'], errors='coerce')
    df['Doorstep Reach Date'] = pd.to_datetime(df['Doorstep Reach Date'], errors='coerce')
    df['Month'] = df['Post Job Done Date'].dt.strftime('%m-%Y')
    
    # FOC Orders: coupon code contains 'FOC' anywhere (case-insensitive: FOC, foc, FOC_WARRANTY_REPEAT, etc.)
    df['FOC_Flag'] = df['Coupon Codes Used'].apply(
        lambda x: 'FOC' if pd.notna(x) and 'FOC' in str(x).upper().strip() else 'Regular'
    )
    
    # TAT Hours
    df['Post_Job_td'] = df['Post Job Done Time'].apply(parse_time)
    df['Doorstep_td'] = df['Doorstep Reach Time'].apply(parse_time)
    def tat_hours(row):
        if pd.isna(row['Post Job Done Date']) or pd.isna(row['Doorstep Reach Date']):
            return None
        if row['Post_Job_td'] is None or row['Doorstep_td'] is None:
            return None
        diff = ((row['Post Job Done Date'] + row['Post_Job_td']) - (row['Doorstep Reach Date'] + row['Doorstep_td'])).total_seconds() / 3600.0
        return diff if diff >= 0 else None
    df['TAT_Hours'] = df.apply(tat_hours, axis=1)
    
    # Late logic
    df['Appt_td'] = df['Appointment Time'].apply(parse_time)
    df['Doorstep_td2'] = df['Doorstep Reach Time'].apply(parse_time)
    def calc_late(row):
        apt = row['Appt_td']
        door = row['Doorstep_td2']
        if apt is None or door is None:
            return 'ontime'
        diff_min = (door - apt).total_seconds() / 60.0
        return 'late' if diff_min > 0 else 'ontime'
    df['TAT'] = df.apply(calc_late, axis=1)
    
    # TAT Violation %
    df['TAT_Violation_pct'] = np.where(
        df['Estimated Time (min)'].fillna(0) > 0,
        (df['Actual Time (min)'].fillna(0) - df['Estimated Time (min)'].fillna(0)) / df['Estimated Time (min)'].fillna(0) * 100,
        0
    )
    
    df['Weekend Flag'] = np.where(df['Post Job Done Date'].dt.weekday >= 5, 'Weekend', 'Weekday')
    
    # Drop temp columns
    df = df.drop(columns=['Post_Job_td', 'Doorstep_td', 'Appt_td', 'Doorstep_td2'], errors='ignore')
    
    return df

def safe_rating_avg(series):
    """Calculate average rating excluding 0s and NaNs."""
    s = pd.to_numeric(series, errors='coerce').fillna(0)
    nonzero = s[s > 0]
    return float(nonzero.mean()) if len(nonzero) > 0 else 0.0

def calc_kpis(df_month):
    total_orders = len(df_month)
    if total_orders == 0:
        return {k: 0 for k in ['total_orders','net_revenue','order_amount','discounts','tax_collected','gross_profit','labor_cost','spare_cost','fuel_cost','net_profit','gross_margin','net_margin','avg_order_value','late_orders','ontime_orders','ontime_pct','sla_breach_pct','avg_rating','avg_tat_hours','foc_orders','actual_orders','foc_pct']}
    
    nr = df_month['Net Revenue'].sum()
    gp = df_month['Gross Profit'].sum()
    np_ = df_month['Net Profit'].sum()
    
    late = len(df_month[df_month['TAT'] == 'late'])
    ontime = total_orders - late
    
    # FOC metrics
    foc_orders = len(df_month[df_month['FOC_Flag'] == 'FOC'])
    actual_orders = total_orders - foc_orders
    foc_pct = round(foc_orders / total_orders * 100, 1) if total_orders > 0 else 0
    
    return {
        'total_orders': int(total_orders),
        'net_revenue': round(float(nr), 2),
        'order_amount': round(float(df_month['Order Amount'].sum()), 2),
        'discounts': round(float(df_month['Discount'].sum()), 2),
        'tax_collected': round(float(df_month['Tax'].sum()), 2),
        'gross_profit': round(float(gp), 2),
        'labor_cost': round(float(df_month['Labor Cost & Travel cost'].sum()), 2),
        'spare_cost': round(float(df_month['Spare Input Price'].sum()), 2),
        'fuel_cost': round(float(df_month['Fuel Cost'].sum()), 2),
        'net_profit': round(float(np_), 2),
        'gross_margin': round(float(gp / nr if nr > 0 else 0), 4),
        'net_margin': round(float(np_ / nr if nr > 0 else 0), 4),
        'avg_order_value': round(float(nr / total_orders), 2),
        'late_orders': int(late),
        'ontime_orders': int(ontime),
        'ontime_pct': round(float(ontime / total_orders * 100), 2),
        'sla_breach_pct': round(float(late / total_orders * 100), 2),
        'avg_rating': round(safe_rating_avg(df_month['Ratings']), 2),
        'avg_tat_hours': round(float(df_month['TAT_Hours'].mean() if not pd.isna(df_month['TAT_Hours'].mean()) else 0), 2),
        'foc_orders': int(foc_orders),
        'actual_orders': int(actual_orders),
        'foc_pct': foc_pct,
    }

def calc_category_mix(df_month):
    if len(df_month) == 0:
        return {'Category': [], 'Orders': [], 'Net_Revenue': [], 'Gross_Profit': [], 'Net_Profit': []}
    cm = df_month.groupby('Subcat').agg({
        'Project No.': 'count', 'Net Revenue': 'sum', 'Gross Profit': 'sum', 'Net Profit': 'sum'
    }).reset_index()
    cm.columns = ['Category', 'Orders', 'Net_Revenue', 'Gross_Profit', 'Net_Profit']
    return cm.to_dict('list')

def calc_daily_perf(df_month):
    if len(df_month) == 0:
        return {'Date': [], 'Orders': [], 'Net_Revenue': [], 'Gross_Profit': [], 'Labor_Cost': [], 'Spare_Cost': [], 'Fuel_Cost': [], 'Net_Profit': [], 'Day': []}
    df_month = df_month.copy()
    df_month['Date'] = df_month['Post Job Done Date'].dt.date
    daily = df_month.groupby('Date').agg({
        'Project No.': 'count', 'Net Revenue': 'sum', 'Gross Profit': 'sum',
        'Labor Cost & Travel cost': 'sum', 'Spare Input Price': 'sum', 'Fuel Cost': 'sum', 'Net Profit': 'sum'
    }).reset_index()
    daily.columns = ['Date', 'Orders', 'Net_Revenue', 'Gross_Profit', 'Labor_Cost', 'Spare_Cost', 'Fuel_Cost', 'Net_Profit']
    daily['Day'] = pd.to_datetime(daily['Date']).dt.day_name()
    return daily.to_dict('list')

def calc_date_wise_perf(df_month):
    if len(df_month) == 0:
        return []
    df_month = df_month.copy()
    df_month['Date'] = df_month['Post Job Done Date'].dt.date
    daily = df_month.groupby('Date').agg({
        'Project No.': 'count', 'Net Revenue': 'sum', 'Gross Profit': 'sum',
        'Labor Cost & Travel cost': 'sum', 'Spare Input Price': 'sum', 'Fuel Cost': 'sum', 'Net Profit': 'sum'
    }).reset_index()
    daily.columns = ['Date', 'Orders', 'Net_Revenue', 'Gross_Profit', 'Labor_Cost', 'Spare_Cost', 'Fuel_Cost', 'Net_Profit']
    daily['Day'] = pd.to_datetime(daily['Date']).dt.day_name()
    daily['GM_pct'] = (daily['Gross_Profit'] / daily['Net_Revenue']).replace([np.inf, -np.inf], 0).fillna(0) * 100
    daily['NM_pct'] = (daily['Net_Profit'] / daily['Net_Revenue']).replace([np.inf, -np.inf], 0).fillna(0) * 100
    records = daily.to_dict('records')
    for r in records:
        r['Date'] = str(r['Date'])
    return records

def calc_service_pnl(df_month):
    if len(df_month) == 0:
        return []
    sp = df_month.groupby('Service Type').agg({
        'Project No.': 'count', 'Net Revenue': 'sum', 'Spare Input Price': 'sum',
        'Labor Cost & Travel cost': 'sum', 'Fuel Cost': 'sum', 'Gross Profit': 'sum', 'Net Profit': 'sum'
    }).reset_index()
    sp.columns = ['Service_Type', 'Orders', 'Net_Revenue', 'Spare_Cost', 'Labor_Cost', 'Fuel_Cost', 'Gross_Profit', 'Net_Profit']
    sp['GM_pct'] = (sp['Gross_Profit'] / sp['Net_Revenue']).replace([np.inf, -np.inf], 0).fillna(0)
    sp['NM_pct'] = (sp['Net_Profit'] / sp['Net_Revenue']).replace([np.inf, -np.inf], 0).fillna(0)
    return sp.to_dict('records')

def calc_expert_kpi(df_month):
    if len(df_month) == 0:
        return []
    ek = df_month.groupby('Expert Name').agg({
        'Project No.': 'count',
        'Net Revenue': 'sum',
        'Gross Profit': 'sum',
        'Net Profit': 'sum',
        'Ratings': [lambda x: pd.to_numeric(x, errors='coerce').replace(0, np.nan).mean(), lambda x: (pd.to_numeric(x, errors='coerce').fillna(0) > 0).sum()],
        'TAT': lambda x: (x == 'late').sum(),
        'TAT_Hours': 'mean',
        'FOC_Flag': lambda x: (x == 'FOC').sum(),
    }).reset_index()
    ek.columns = ['Expert_Name', 'Orders', 'Net_Revenue', 'Gross_Profit', 'Net_Profit',
                  'Avg_Rating', 'Rating_Count', 'Late', 'Avg_TAT_Hours', 'FOC_Orders']
    ek['Actual_Orders'] = ek['Orders'] - ek['FOC_Orders']
    ek['FOC_Pct'] = (ek['FOC_Orders'] / ek['Orders'] * 100).round(1)
    ek['On_Time_pct'] = (ek['Orders'] - ek['Late']) / ek['Orders'] * 100
    # Round rating to 1 decimal, replace NaN with 0
    ek['Avg_Rating'] = ek['Avg_Rating'].fillna(0).round(1)
    return ek.to_dict('records')

def calc_expert_tat(df_month):
    if len(df_month) == 0:
        return []
    et = df_month.groupby(['Expert Name', 'Weekend Flag']).agg({
        'Project No.': 'count',
        'TAT': lambda x: (x == 'late').sum(),
        'Actual Time (min)': 'mean',
        'Estimated Time (min)': 'mean',
        'TAT_Violation_pct': 'mean',
        'TAT_Hours': 'mean'
    }).reset_index()
    et.columns = ['Expert_Name', 'Weekend_Flag', 'Orders', 'Late', 'Avg_Act_Time', 'Avg_Est_Time', 'Avg_TAT_Violation_pct', 'Avg_TAT_Hours']
    et['On_Time'] = et['Orders'] - et['Late']
    et['Late_pct'] = et['Late'] / et['Orders'] * 100
    return et.to_dict('records')

def calc_discount_pnl(df_month):
    if len(df_month) == 0:
        return []
    total_orders = len(df_month)
    order_amount = df_month['Order Amount'].sum()
    discounts = df_month['Discount'].sum()
    net_revenue = df_month['Net Revenue'].sum()
    spare_cost = df_month['Spare Input Price'].sum()
    consumable = df_month['Consumable'].sum()
    labor_cost = df_month['Labor Cost & Travel cost'].sum()
    fuel_cost = df_month['Fuel Cost'].sum()
    gross_profit = df_month['Gross Profit'].sum()
    net_profit = df_month['Net Profit'].sum()
    
    no_discount_revenue = order_amount
    no_discount_gross = no_discount_revenue - spare_cost - consumable
    no_discount_net = no_discount_gross - labor_cost - fuel_cost
    
    return [
        {'Funnel_Stage': 'Total Orders', 'Current': total_orders, 'No_Discount': total_orders, 'Impact': 0},
        {'Funnel_Stage': 'Gross Service Value', 'Current': round(float(order_amount),2), 'No_Discount': round(float(order_amount),2), 'Impact': 0},
        {'Funnel_Stage': 'Less: Discount', 'Current': round(float(discounts),2), 'No_Discount': 0, 'Impact': round(float(-discounts),2)},
        {'Funnel_Stage': 'Discount %', 'Current': round(float(discounts/order_amount*100 if order_amount>0 else 0),1), 'No_Discount': 0, 'Impact': 0},
        {'Funnel_Stage': 'Revenue After Discount', 'Current': round(float(net_revenue),2), 'No_Discount': round(float(no_discount_revenue),2), 'Impact': round(float(no_discount_revenue-net_revenue),2)},
        {'Funnel_Stage': 'Less: Spare Cost', 'Current': round(float(spare_cost),2), 'No_Discount': round(float(spare_cost),2), 'Impact': 0},
        {'Funnel_Stage': 'Less: Consumable Cost', 'Current': round(float(consumable),2), 'No_Discount': round(float(consumable),2), 'Impact': 0},
        {'Funnel_Stage': 'Less: Labor & Travel Cost', 'Current': round(float(labor_cost),2), 'No_Discount': round(float(labor_cost),2), 'Impact': 0},
        {'Funnel_Stage': 'Less: Fuel Cost', 'Current': round(float(fuel_cost),2), 'No_Discount': round(float(fuel_cost),2), 'Impact': 0},
        {'Funnel_Stage': 'Gross Profit', 'Current': round(float(gross_profit),2), 'No_Discount': round(float(no_discount_gross),2), 'Impact': round(float(no_discount_gross-gross_profit),2)},
        {'Funnel_Stage': 'Net Profit', 'Current': round(float(net_profit),2), 'No_Discount': round(float(no_discount_net),2), 'Impact': round(float(no_discount_net-net_profit),2)},
        {'Funnel_Stage': 'Gross Margin %', 'Current': round(float(gross_profit/net_revenue*100 if net_revenue>0 else 0),1), 'No_Discount': round(float(no_discount_gross/no_discount_revenue*100 if no_discount_revenue>0 else 0),1), 'Impact': 0},
        {'Funnel_Stage': 'Net Margin %', 'Current': round(float(net_profit/net_revenue*100 if net_revenue>0 else 0),1), 'No_Discount': round(float(no_discount_net/no_discount_revenue*100 if no_discount_revenue>0 else 0),1), 'Impact': 0},
        {'Funnel_Stage': 'AOV', 'Current': round(float(net_revenue/total_orders if total_orders>0 else 0),2), 'No_Discount': round(float(no_discount_revenue/total_orders if total_orders>0 else 0),2), 'Impact': 0},
    ]

def calc_lmtd_mtd(df_all, current_month):
    months = sorted(df_all['Month'].unique())
    if current_month not in months or months.index(current_month) == 0:
        return []
    
    prev_month = months[months.index(current_month) - 1]
    df_current = df_all[df_all['Month'] == current_month]
    df_last_full = df_all[df_all['Month'] == prev_month]
    
    current_day = df_current['Post Job Done Date'].dt.day.max() or 1
    df_last = df_last_full[df_last_full['Post Job Done Date'].dt.day <= current_day]
    
    def calc_metrics(dfx):
        n = len(dfx)
        nr = dfx['Net Revenue'].sum()
        ratings_nonzero = pd.to_numeric(dfx['Ratings'], errors='coerce').fillna(0)
        ratings_nonzero = ratings_nonzero[ratings_nonzero > 0]
        return {
            'Orders Completed': n,
            'Gross Service Value': dfx['Order Amount'].sum(),
            'Discount Given': dfx['Discount'].sum(),
            'Discount %': dfx['Discount'].sum()/dfx['Order Amount'].sum()*100 if dfx['Order Amount'].sum()>0 else 0,
            'Revenue After Discount': nr,
            'GST Collected': dfx['Tax'].sum(),
            'Customer Billing': dfx['Order Amount'].sum(),
            'Spare Cost %': dfx['Spare Input Price'].sum()/nr*100 if nr>0 else 0,
            'Consumable Cost %': dfx['Consumable'].sum()/nr*100 if nr>0 else 0,
            'Labor & Travel Cost': dfx['Labor Cost & Travel cost'].sum()/nr*100 if nr>0 else 0,
            'Fuel Cost': dfx['Fuel Cost'].sum(),
            'Total Operating Cost': 1,
            'Gross Profit': dfx['Gross Profit'].sum(),
            'Gross Margin %': dfx['Gross Profit'].sum()/nr*100 if nr>0 else 0,
            'Net Profit': dfx['Net Profit'].sum(),
            'Net Margin %': dfx['Net Profit'].sum()/nr*100 if nr>0 else 0,
            'Avg Revenue / Order': nr/n if n>0 else 0,
            'Avg Profit / Order': dfx['Net Profit'].sum()/n if n>0 else 0,
            'Avg Discount / Order': dfx['Discount'].sum()/n if n>0 else 0,
            'Avg Rating': ratings_nonzero.mean() if len(ratings_nonzero) > 0 else 0,
            'Daily Run Rate': nr/current_day,
            'Projected Full Month Revenue': nr/current_day*31,
            'FOC Orders': (dfx['FOC_Flag'] == 'FOC').sum(),
            'FOC %': (dfx['FOC_Flag'] == 'FOC').mean() * 100 if n > 0 else 0,
        }
    
    mtd_m = calc_metrics(df_current)
    lmtd_m = calc_metrics(df_last)
    
    result = []
    for k in mtd_m:
        result.append({
            'Metric': k,
            'MTD': round(float(mtd_m[k]), 2) if isinstance(mtd_m[k], (int, float, np.floating)) else mtd_m[k],
            'LMTD': round(float(lmtd_m[k]), 2) if isinstance(lmtd_m[k], (int, float, np.floating)) else lmtd_m[k],
            'Variance': round(float(mtd_m[k] - lmtd_m[k]), 2) if isinstance(mtd_m[k], (int, float, np.floating)) else mtd_m[k] - lmtd_m[k],
            'Variance_pct': round(float((mtd_m[k] - lmtd_m[k])/lmtd_m[k]*100), 1) if lmtd_m[k] != 0 else 0
        })
    return result

def generate_insights_actions(df_month, df_all, month):
    if len(df_month) == 0:
        return [], []
    insights = []
    actions = []
    
    sp = calc_service_pnl(df_month)
    if sp:
        sp_df = pd.DataFrame(sp)
        sp_df = sp_df[sp_df['Orders'] >= 3]
        if len(sp_df) > 0:
            best = sp_df.loc[sp_df['NM_pct'].idxmax()]
            worst = sp_df.loc[sp_df['NM_pct'].idxmin()]
            insights.append(f"🏆 Best Margin: {best['Service_Type']} ({best['NM_pct']:.1%})")
            insights.append(f"⚠️ Worst Margin: {worst['Service_Type']} ({worst['NM_pct']:.1%})")
            if worst['NM_pct'] < 0:
                actions.append(f"🔴 URGENT: Review pricing for '{worst['Service_Type']}' — losing ₹{abs(worst['Net_Profit']):,.0f}")
    
    ek = calc_expert_kpi(df_month)
    if ek:
        ek_df = pd.DataFrame(ek)
        ek_df = ek_df[ek_df['Orders'] >= 5]
        if len(ek_df) > 0:
            best_e = ek_df.loc[ek_df['Net_Profit'].idxmax()]
            worst_e = ek_df.loc[ek_df['Net_Profit'].idxmin()]
            insights.append(f"⭐ Top Expert: {best_e['Expert_Name']} (₹{best_e['Net_Profit']:,.0f} profit)")
            insights.append(f"📉 Attention: {worst_e['Expert_Name']} (₹{worst_e['Net_Profit']:,.0f} profit)")
            poor = ek_df[ek_df['On_Time_pct'] < 80]
            for _, row in poor.iterrows():
                actions.append(f"🔴 Train {row['Expert_Name']} — only {row['On_Time_pct']:.1f}% on-time")
    
    total_discount = df_month['Discount'].sum()
    total_revenue = df_month['Order Amount'].sum()
    discount_pct = total_discount / total_revenue * 100 if total_revenue > 0 else 0
    insights.append(f"💰 Discount Rate: {discount_pct:.1f}% (₹{total_discount:,.0f} given)")
    if discount_pct > 30:
        actions.append(f"🟡 Consider reducing discounts — {discount_pct:.1f}% is high")
    
    late_pct = (df_month['TAT'] == 'late').mean() * 100
    insights.append(f"⏱️ Late Rate: {late_pct:.1f}%")
    if late_pct > 15:
        actions.append(f"🟡 Improve TAT — {late_pct:.1f}% orders are late")
    
    avg_rating = safe_rating_avg(df_month['Ratings'])
    insights.append(f"⭐ Avg Rating: {avg_rating:.1f}/5.0")
    if avg_rating < 4.5:
        actions.append(f"🟡 Focus on quality — rating is {avg_rating:.1f}/5.0")
    
    foc_orders = (df_month['FOC_Flag'] == 'FOC').sum()
    foc_pct = foc_orders / len(df_month) * 100 if len(df_month) > 0 else 0
    insights.append(f"🔄 FOC Orders: {foc_orders} ({foc_pct:.1f}%)")
    if foc_pct > 20:
        actions.append(f"🟡 High FOC rate — {foc_pct:.1f}% are repeat/reopened cases")
    
    return insights, actions

def calc_cohort(df_all):
    customer_first = df_all.groupby('Customer ID')['Post Job Done Date'].min().reset_index()
    customer_first.columns = ['Customer ID', 'First Order']
    customer_first['Cohort Month'] = customer_first['First Order'].dt.strftime('%m-%Y')
    df_cohort = df_all.merge(customer_first[['Customer ID', 'Cohort Month']], on='Customer ID')
    df_cohort['Period Number'] = (df_cohort['Post Job Done Date'].dt.to_period('M') - 
                                   pd.to_datetime(df_cohort['Cohort Month'], format='%m-%Y').dt.to_period('M')).apply(attrgetter('n'))
    cohort_counts = df_cohort.groupby(['Cohort Month', 'Period Number'])['Customer ID'].nunique().reset_index()
    cohort_sizes = customer_first.groupby('Cohort Month')['Customer ID'].nunique().reset_index()
    cohort_sizes.columns = ['Cohort Month', 'Size']
    cohort_table = cohort_counts.pivot(index='Cohort Month', columns='Period Number', values='Customer ID')
    cohort_table = cohort_sizes.merge(cohort_table, on='Cohort Month')
    records = cohort_table.to_dict('records')
    for r in records:
        size = r['Size']
        for key in list(r.keys()):
            if key not in ('Cohort Month', 'Size') and r[key] is not None and size > 0:
                r[key] = round(float(r[key]) / size * 100, 1)
    return records

def calc_monthly_trend(df_all):
    monthly = df_all.groupby('Month').agg({
        'Project No.': 'count', 'Net Revenue': 'sum', 'Gross Profit': 'sum',
        'Labor Cost & Travel cost': 'sum', 'Spare Input Price': 'sum', 'Fuel Cost': 'sum', 'Net Profit': 'sum'
    }).reset_index()
    monthly.columns = ['Month', 'Orders', 'Net_Revenue', 'Gross_Profit', 'Labor_Cost', 'Spare_Cost', 'Fuel_Cost', 'Net_Profit']
    return monthly.to_dict('list')

def get_filter_options(df):
    return {
        'categories': sorted(df['Subcat'].dropna().unique().tolist()),
        'services': sorted(df['Service Type'].dropna().unique().tolist()),
        'experts': sorted(df['Expert Name'].dropna().unique().tolist()),
        'franchises': sorted(df['Franchisee Name'].dropna().unique().tolist()),
    }

def generate_all_views(df, service_prices, manpower_costs, fuel_cost):
    months = sorted(df['Month'].unique())
    print(f"📅 Found months: {months}")
    views = {}
    filter_options = get_filter_options(df)
    
    for month in months:
        df_month = df[df['Month'] == month]
        print(f"  🔄 Processing {month} ({len(df_month)} orders)...")
        insights, actions = generate_insights_actions(df_month, df, month)
        views[month] = {
            'kpis': calc_kpis(df_month),
            'category_mix': calc_category_mix(df_month),
            'daily_perf': calc_daily_perf(df_month),
            'date_wise_perf': calc_date_wise_perf(df_month),
            'service_pnl': calc_service_pnl(df_month),
            'expert_kpi': calc_expert_kpi(df_month),
            'expert_tat': calc_expert_tat(df_month),
            'discount_pnl': calc_discount_pnl(df_month),
            'lmtd_mtd': calc_lmtd_mtd(df, month),
            'insights': insights,
            'action_items': actions
        }
    
    print(f"  🔄 Processing Overall ({len(df)} orders)...")
    insights_all, actions_all = generate_insights_actions(df, df, 'Overall')
    views['Overall'] = {
        'kpis': calc_kpis(df),
        'category_mix': calc_category_mix(df),
        'daily_perf': None,
        'date_wise_perf': calc_date_wise_perf(df),
        'service_pnl': calc_service_pnl(df),
        'expert_kpi': calc_expert_kpi(df),
        'expert_tat': calc_expert_tat(df),
        'discount_pnl': calc_discount_pnl(df),
        'lmtd_mtd': calc_lmtd_mtd(df, months[-1]) if len(months) >= 2 else [],
        'insights': insights_all,
        'action_items': actions_all
    }
    return views, filter_options

def save_data_js(data):
    js_content = "// Auto-generated by update_dashboard.py\n// Last updated: " + datetime.now().strftime('%Y-%m-%d %H:%M') + "\n\n"
    js_content += "const DASHBOARD_DATA = " + json.dumps(data, indent=2, default=str) + ";\n"
    with open(OUTPUT_FILE, 'w') as f:
        f.write(js_content)
    print(f"✅ Saved: {OUTPUT_FILE}")

def main():
    print("=" * 60)
    print("EAZZY DASHBOARD DATA REFRESH (v4 FOC + Franchise)")
    print("=" * 60)
    
    service_prices, manpower_costs, fuel_cost = load_config()
    print(f"📋 Config: {len(service_prices)} prices, {len(manpower_costs)} manpower, ₹{fuel_cost} fuel/order")
    
    df = fetch_redash()
    df = apply_formulas(df, service_prices, manpower_costs, fuel_cost)
    months = sorted(df['Month'].unique())
    views, filter_options = generate_all_views(df, service_prices, manpower_costs, fuel_cost)
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'months': months,
        'filter_options': filter_options,
        'monthly_trend': calc_monthly_trend(df),
        'cohort': calc_cohort(df),
        'views': views
    }
    save_data_js(result)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Records: {len(df)}")
    print(f"Months: {months}")
    print(f"Views: {len(views)}")
    latest = months[-1]
    k = views[latest]['kpis']
    print(f"\n📅 {latest}: ₹{k['net_revenue']:,.0f} revenue | ₹{k['net_profit']:,.0f} profit | {k['total_orders']} orders")
    print(f"   FOC: {k['foc_orders']} | Actual: {k['actual_orders']} | FOC%: {k['foc_pct']}%")
    print("\n🚀 Next: python build_final.py")

if __name__ == '__main__':
    main()

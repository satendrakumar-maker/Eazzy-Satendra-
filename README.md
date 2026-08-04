# 🏠 Eazzy Services - Executive Dashboard

> **Auto-generated interactive dashboard** from Redash data with **month slicer** (Overall + per-month filter). Tracks KPIs, P&L, expert performance, operations & TAT, discount analysis, LMTD vs MTD, and customer cohorts.

---

## 🆕 What's New in v2

- ✅ **Month Slicer** — Dropdown to view Overall or any specific month (Apr-Jul 2026+)
- ✅ **Editable Config** — Change service prices & manpower costs in `config.json`, no code changes needed
- ✅ **8 Interactive Tabs** — Executive, P&L, Experts, Operations, Discount, LMTD, Cohort, Insights
- ✅ **Auto Insights** — Best/worst performers, discount alerts, training needs

---

## 📁 Project Structure

```
eazzy-dashboard-github/
├── index.html              # Main dashboard (single-page app with month slicer)
├── update_dashboard.py     # Python script to refresh data from Redash
├── config.json             # ⭐ EDIT THIS to change prices & costs
├── README.md               # This file
└── assets/
    ├── styles.css          # Dashboard styles
    └── data.js             # Auto-generated dashboard data (per-month views)
```

---

## ⚙️ How to Change Service Prices / Manpower Costs

**No code changes needed!** Just edit `config.json`:

```json
{
  "service_prices": {
    "AC Gas Refill": 1050,
    "AC Installation": 100,
    ...
  },
  "manpower_costs": {
    "AC Gas Refill": 656,
    "AC Installation": 656,
    ...
  }
}
```

Then run:
```bash
python update_dashboard.py
```

The script reads `config.json`, recalculates all formulas, and regenerates `assets/data.js`.

---

## 🚀 GitHub Pages Setup (3 Steps)

### Step 1 — Create Repo
- Go to [github.com/new](https://github.com/new)
- Name: `eazzy-dashboard`
- Make it **Public**

### Step 2 — Push Files
```bash
cd eazzy-dashboard-github
git init
git remote add origin https://github.com/YOUR_USERNAME/eazzy-dashboard.git
git add .
git commit -m "Initial dashboard v2"
git push -u origin main
```

### Step 3 — Enable Pages
- Repo → **Settings** → **Pages**
- Source: **Deploy from a branch** → `main` → `/(root)`
- Your dashboard: `https://YOUR_USERNAME.github.io/eazzy-dashboard/`

---

## 📊 Dashboard Tabs

| Tab | Features |
|-----|----------|
| **📊 Executive** | 15 KPI cards, monthly trend chart, category pie chart, daily bar chart, monthly summary table |
| **💼 P&L by Service** | Service-wise P&L table + net margin bar chart |
| **👨‍🔧 Experts** | Expert KPI matrix + profit ranking + on-time % charts |
| **⏱️ Operations & TAT** | Weekend vs weekday TAT per expert |
| **💰 Discount Analysis** | Current vs no-discount scenario + pie charts |
| **📈 LMTD vs MTD** | Full comparison table + bar chart |
| **👥 Cohort** | Customer retention cohort |
| **💡 Insights** | Auto-generated insights + action items |

---

## 🔄 Daily Refresh Workflow

```bash
# 1. Update data from Redash
python update_dashboard.py

# 2. Commit and push
git add assets/data.js
git commit -m "Update data - $(date +%Y-%m-%d)"
git push

# 3. GitHub Pages auto-updates in ~1 minute
```

---

## 🔑 Redash API

Configured in `update_dashboard.py`:
```python
BASE_URL = "https://redash.tryeazzy.in"
QUERY_ID = 17
USER_API_KEY = "JKLi4Tj1CDRTka1B2WsgetcE7STI7n7GvbcYV4L6"
```

---

## 📝 License

Private — For Eazzy Services internal use.

---

**Built with** ❤️ by Kimi Work + Chart.js + GitHub Pages

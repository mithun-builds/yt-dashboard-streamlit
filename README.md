# 📊 YouTube Channel Dashboard

An interactive analytics dashboard built with **Streamlit** and **Plotly**, exploring performance data from Ken Jee's YouTube channel (data snapshot through January 2022).

🔗 **Live app:** https://yt-dashboard-app-n9iexwwyhm2xies7ewycyw.streamlit.app/

---

## Features

### 📈 Tab 1 — Aggregate Metrics
- Channel-level KPI cards: total views, watch time, revenue, subscribers gained, videos published
- Top 10 videos by views (horizontal bar chart)
- Views vs. Viewer Retention bubble chart (bubble size = watch time, colour = revenue)
- Full sortable performance table for all 223 videos
- **Channel Growth Over Time** — cumulative views or subscribers over a selectable date range

### 🎬 Tab 2 — Individual Video Deep-Dive
- Select any video from a dropdown (sorted by most-viewed)
- Per-video KPIs: views, likes, net subscribers, revenue
- Daily views over time (line chart)
- Subscriber vs. Non-Subscriber comparison: views, watch time, retention
- Top 15 countries by views

### 💬 Tab 3 — Comment Analysis
- Top 10 most liked comments
- Monthly comment volume over time
- Top 20 most frequent words across all comments

### 🎛 Sidebar
- **Date range filter** — narrows time-series charts across Tab 1 and Tab 2

---

## Data Sources

| File | Description | Rows |
|------|-------------|------|
| `Aggregated_Metrics_By_Video.csv` | Per-video totals (views, revenue, CTR, etc.) | 223 videos |
| `Aggregated_Metrics_By_Country_And_Subscriber_Status.csv` | Views by country and subscriber status | ~55k rows |
| `Video_Performance_Over_Time.csv` | Daily metrics per video | ~112k rows |
| `All_Comments_Final.csv` | YouTube comments with like/reply counts | ~10k comments |

---

## Tech Stack

| Library | Purpose |
|---------|---------|
| `streamlit` | Web app framework |
| `plotly` | Interactive charts |
| `pandas` | Data loading and cleaning |

---

## Run locally

```bash
# 1. Clone the repo
git clone https://github.com/mithun-builds/yt-dashboard-streamlit.git
cd yt-dashboard-streamlit

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`.

---

## Data cleaning applied

The raw CSVs required several fixes before use:

- Invisible soft-hyphen characters (`\xad`) stripped from column names in File 1
- `"Total"` aggregate row removed from File 1
- `"Sept"` → `"Sep"` typo fixed for date parsing in File 3 (~10,000 affected rows)
- `Average View Percentage` stored as a 0–1 fraction (not a true %) — handled accordingly
- All-zero `User Comments Added` columns dropped from Files 2 & 3
- Country code `ZZ` (YouTube's "unknown") mapped to `"Unknown"`
- Duplicate zero-view rows removed from File 2
- `Subscribers` column renamed to `subscribers_net` (it's net gained minus lost, not a total)
- `avg_view_duration` parsed manually from `H:MM:SS` string to seconds

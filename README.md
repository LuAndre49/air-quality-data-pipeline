# Philippine Weather Analytics Pipeline

An end-to-end data engineering pipeline that ingests 10+ years of daily weather data for all 83 Philippine provinces, transforms it through a multi-layer dbt model, and visualizes it in an interactive Power BI dashboard.

This project builds a complete ELT pipeline that:

- Ingests daily weather data for **83 Philippine provinces** (81 provinces + Metro Manila NCR) from **2015 to present** using the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- Orchestrates daily incremental loads and a one-time historical backfill using **Kestra**
- Stores raw data in **Google BigQuery**
- Transforms raw data into analytical models using **dbt**
- Visualizes insights in a **Power BI** dashboard with 6 analytical pages

**Key analytical questions answered:**
- Are Philippine provinces getting hotter over the past 10 years?
- Which provinces are most exposed to typhoon-force winds, extreme rainfall, and dangerous heat?
- How does weather differ between wet season (June-November) and dry season (December-May)?
- What are the monthly rainfall and temperature patterns per province?

---

## Pipeline Architecture

The pipeline follows a typical ELT workflow:

1. **Data Source**
   - Open-Meteo Archive API

2. **Orchestration**
   - Kestra workflows
   - `backup.py` handles the historical backfill through python
   - `weather_backfill.yaml` handles the historical backfill through a flow
   - `weather_backfill_auto.yaml` automatically runs backfill on specified date range
   - `weather_ingestion.yaml` runs the daily ingestion flow

3. **Data Warehouse**
   - Google BigQuery
   - Raw table: `raw_ph_weather.weather_daily`

4. **Transformation (dbt)**
   - `stg_raw_weather_data` - cleaned and typed raw data
   - `int_monthly` - monthly aggregated metrics
   - marts layer:
     - `mart_province_climate_summary`
     - `mart_monthly_patterns`
     - `mart_annual_trends`
     - `mart_season_summary`
     - `mart_weather_severity_summary`

5. **Visualization**
   - Power BI dashboard with 6 analytical pages

---

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | [Kestra](https://kestra.io/) |
| Data Warehouse | [Google BigQuery](https://cloud.google.com/bigquery) |
| Transformation | [dbt](https://www.getdbt.com/) |
| Visualization | [Power BI Desktop](https://powerbi.microsoft.com/desktop) |
| Containerization | Docker + Docker Compose |
| Data Source | [Open-Meteo Historical Weather API](https://open-meteo.com) |
| Geocoding | [Nominatim (OpenStreetMap)](https://nominatim.org/) |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.10+](https://www.python.org/downloads/)
- [Power BI Desktop](https://powerbi.microsoft.com/desktop) (Windows only)
- A [Google Cloud Platform](https://cloud.google.com/) account with billing enabled
- A GCP service account with the following roles:
  - BigQuery Data Editor
  - BigQuery Job User
  - BigQuery Data Viewer

---

## Data Sources

### Open-Meteo Historical Weather API

- **URL**: `https://archive-api.open-meteo.com/v1/archive`
- **Authentication**: None (free tier)
- **Rate limits**: 10,000 requests/day, 600 requests/minute
- **Coverage**: Global, daily aggregates from 1940 to present

**Variables extracted:**

| Variable | Description | Unit |
|---|---|---|
| temperature_2m_max | Daily maximum temperature | °C |
| temperature_2m_min | Daily minimum temperature | °C |
| temperature_2m_mean | Daily mean temperature | °C |
| rain_sum | Total daily rainfall | mm |
| precipitation_hours | Hours with rainfall | hours |
| wind_speed_10m_max | Maximum daily wind speed | km/h |
| wind_direction_10m_dominant | Dominant wind direction | ° |
| relative_humidity_2m_max | Maximum relative humidity | % |
| relative_humidity_2m_min | Minimum relative humidity | % |
| shortwave_radiation_sum | Total solar radiation | MJ/m² |
| sunshine_duration | Sunshine duration | seconds |
| et0_fao_evapotranspiration | Reference evapotranspiration | mm |

### Province Coordinates

Resolved dynamically via the **Nominatim OpenStreetMap geocoding API**. Metro Manila (NCR) uses hardcoded NAIA coordinates (14.5086, 121.0197) as the official PAGASA meteorological reference point.

---

## Transformation (dbt)

### Staging - `stg_raw_weather_data`
Casts all columns to correct types, extracts `year` and `month`, and adds `region` (Luzon/Visayas/Mindanao) and `season` (Wet/Dry) columns via macros. Materialized as a partitioned table clustered by province.

### Intermediate - `int_monthly`
Aggregates daily data to monthly totals and averages per province (avg temperature, total rainfall, peak wind speed, total sunshine, etc.).

### Marts

| Table | Grain | Purpose |
|---|---|---|
| `mart_province_climate_summary` | 1 row per province | Province overview maps and rankings |
| `mart_monthly_patterns` | Province × month | Monthly seasonality charts |
| `mart_annual_trends` | Province × year | Year-over-year trend analysis |
| `mart_season_summary` | Province × season | Wet vs dry season comparison |
| `mart_weather_severity_summary` | Province × year | PAGASA hazard day classifications |

---

## Analytical Thresholds & Methodology

All thresholds are based on official Philippine and international meteorological standards.

**Wind Signal Days** - [PAGASA Tropical Cyclone Wind Signal](https://www.pagasa.dost.gov.ph/learning-tools/tropical-cyclone-wind-signal):

| Column | Threshold | Signal |
|---|---|---|
| signal_1_wind_days | 39-61 km/h | Signal #1 |
| signal_2_wind_days | 62-88 km/h | Signal #2 |
| signal_3_wind_days | 89-117 km/h | Signal #3 |
| signal_4_wind_days | 118-184 km/h | Signal #4 |
| signal_5_wind_days | >=185 km/h | Signal #5 |

**Rainfall Hazard Days** - [PAGASA 24-HR Rainfall Advisory](https://www.facebook.com/DOST.PAGASA):

| Column | Threshold | Classification |
|---|---|---|
| moderate_to_heavy_rain_days | 50-99 mm/day | Moderate to Heavy |
| heavy_to_intense_rain_days | 100-199 mm/day | Heavy to Intense |
| intense_to_torrential_rain_days | >=200 mm/day | Intense to Torrential |

**Heat Index Days** - [PAGASA Heat Index](https://www.pagasa.dost.gov.ph/weather/heat-index), computed using the [Rothfusz regression equation (NOAA/NWS, 1990)](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml):

| Column | Threshold | Classification |
|---|---|---|
| caution_heat_index_days | 27-32°C | Caution |
| extreme_caution_heat_index_days | 33-41°C | Extreme Caution |
| danger_heat_index_days | 42-51°C | Danger |
| extreme_danger_heat_index_days | >=52°C | Extreme Danger |

---

## Dashboard

The Power BI dashboard contains 6 pages:

| Page | Description |
|---|---|
| Province Overview | Choropleth maps of average temperature and rainfall per province |
| Province Rankings | Top 10 wettest, driest, hottest, and coldest provinces |
| Monthly Trends | Average monthly rainfall, temperature, and humidity per province |
| Annual Trends | Year-over-year rainfall, temperature, and humidity with trend lines |
| Weather Risk Summary | Annual wind, rain, and heat hazard days per province |
| Season Comparison | Wet vs dry season conditions side by side per province |

### Province Overview
![Province Overview](/screenshots/Province_Overview.png)

### Province Rankings
![Province Rankings](/screenshots/Province_Rankings.png)

### Monthly Trends
![Monthly Trends](/screenshots/Monthly_Trends.png)

### Annual Trends
![Annual Trends](/screenshots/Annual_Trends.png)

### Weather Risk Summary
![Weather Risk Summary](/screenshots/Weather_Risk_Summary.png)

### Season Comparison
![Season Comparison](/screenshots/Season_Comparison.png)
---


## Setup Guide

### 1. GCP Setup

**a. Create a GCP project**

Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project named `philippine-weather-analytics`.

**b. Enable BigQuery API**

Navigate to **APIs & Services** -> **Enable APIs** -> search for **BigQuery API** and enable it.

**c. Create service accounts**

This project uses two separate service account key files - one for Kestra and one for dbt.

1. Go to **IAM & Admin** -> **Service Accounts** -> **Create Service Account**
2. Name it `weather-pipeline-sa`
3. Assign roles: **BigQuery Data Editor**, **BigQuery Job User**, **BigQuery Data Viewer**
4. Create and download a JSON key file
5. Save a copy as `kestra-service-account-key.json` in the project root (used by Docker/Kestra)
6. Save another copy as `dbt-service-account-key.json` inside `dbt/weather_pipeline/` (used by dbt)

**d. Create a BigQuery dataset**

In BigQuery, create a dataset named `raw_ph_weather` in your project.

**e. Enable billing**

Go to [Google Cloud Billing](https://console.cloud.google.com/billing) and link a billing account to your project.

---

### 2. Docker & Kestra Setup

**a. Clone the repository**

```bash
git clone https://github.com/LuAndre49/ph-weather-pipeline.git
cd ph-weather-pipeline
```

**b. Start Kestra**

```bash
docker compose up -d
```

This starts Kestra at `http://localhost:8080`. The `kestra-service-account-key.json` is mounted into the container automatically via `docker-compose.yml`.

**c. Import flows**

In the Kestra UI, go to **Flows** -> **Import** and upload the YAML files from the `kestra/` directory:
- `weather_backfill.yaml` - manual historical backfill
- `weather_backfill_auto.yaml` - automated backfill flow
- `weather_ingestion.yaml` - scheduled daily incremental load

---

### 3. Running the Backfill

The historical backfill fetches 10+ years of data (2015-present) for all 83 provinces sequentially due to Open-Meteo's free tier rate limits.

**Option A: Run via standalone Python script (recommended)**

```bash
# Install dependencies
pip install -r requirements.txt

# Set GCP credentials
# Windows PowerShell:
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\kestra-service-account-key.json"

# macOS/Linux:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/kestra-service-account-key.json"

# Run the backfill
python scripts/backup.py
```

Total runtime is approximately 15-20 minutes.

**Option B: Run via Kestra UI**

Trigger the `weather_backfill` flow manually from the Kestra UI.

---

### 4. dbt Setup

**a. Install dbt**

```bash
pip install dbt-core==1.11.7 dbt-bigquery==1.11.7
```

**b. Configure profiles.yml**

Create or update `~/.dbt/profiles.yml`:

```yaml
weather_pipeline:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: philippine-weather-analytics
      dataset: ph_transformed_weather_data
      keyfile: /absolute/path/to/dbt/weather_pipeline/dbt-service-account-key.json
      location: US
      threads: 4
      timeout_seconds: 300
```

**c. Run all models**

```bash
cd dbt/weather_pipeline
dbt debug      # verify connection
dbt build      # run models and tests
```

Expected output: `PASS=31 WARN=0 ERROR=0 SKIP=0`

---

### 5. Power BI Setup

**a.** Download [Power BI Desktop](https://powerbi.microsoft.com/desktop) (Windows only).

**b.** Open `philippine_weather_report_analytics.pbix`.

**c.** Go to **Home** -> **Transform data** -> **Data source settings**, select the BigQuery connection, and sign in with a Google account that has **BigQuery Data Viewer** access to the `philippine-weather-analytics` project.

**d.** Click **Home** -> **Refresh** to load the latest data.

---

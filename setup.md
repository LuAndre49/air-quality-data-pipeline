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

The historical backfill fetches 10+ years of data (2015–present) for all 83 provinces sequentially due to Open-Meteo's free tier rate limits.

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

Total runtime is approximately 15–20 minutes.

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
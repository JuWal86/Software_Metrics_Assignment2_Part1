# Defect Inflow Predictor & Resource Planner

A minimal, fully working measurement system to monitor **defect inflow/outflow**, derive indicators, and **predict next week's resource needs**.

## Assessed points
- **Base/Derived/Indicators (raw):**
  - Base: `data/base_measures.csv`
  - Derived: `outputs/derived_measures.csv`
  - Indicators: `outputs/indicators.csv`
- **Analysis model as config:** `config/analysis_model.yaml`
- **Add/remove input data:** edit `data/base_measures.csv` or use the GitHub fetcher.
- **Manipulate forecast horizon:** CLI `--horizon N` or `forecast.horizon_weeks` in YAML.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/cli.py --data data/base_measures.csv --config config/analysis_model.yaml --horizon 1
```

## Use with an open-source repo
```bash
export GITHUB_TOKEN=YOUR_TOKEN
python src/fetch_github.py --repo owner/name --since 2024-01-01 --until 2025-12-31 --out data/base_measures.csv
python src/cli.py --data data/base_measures.csv --config config/analysis_model.yaml --horizon 1
```

## Columns (Base Measures)
week_start, defects_inflow_total, defects_outflow_total, severity_critical_in, severity_high_in, severity_medium_in, severity_low_in, avg_resolution_time_hours, backlog_total
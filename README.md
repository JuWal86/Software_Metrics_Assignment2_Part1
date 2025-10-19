# Defect Inflow Predictor

## Overview
The **Defect Inflow Predictor** is a data-driven tool that estimates defect inflow and outflow in software repositories.  
It helps development teams monitor software quality trends, forecast future workload, and determine **optimal resource allocation** (e.g., number of engineers and QA hours).

This project combines **software metrics** and **predictive modeling** to support proactive decision-making in software maintenance.

---

## Objectives
- Monitor defect inflow and outflow trends over time  
- Predict future inflow of defects using historical data  
- Estimate required resources (engineers, QA effort)  
- Identify problematic conditions when inflow > outflow  
- Support data-informed decision-making in defect management  

---

## Key Concepts

### Defect Inflow
Number of **new defects** (bugs, issues) reported within a given period (e.g., per week or per deployment).

### Defect Outflow
Number of **resolved defects** in the same period — representing the team’s repair capacity.

### Indicator
A **metric** that signals a potential quality issue.  
> Example: “If the defect inflow consistently exceeds the outflow for more than two weeks, the backlog may grow uncontrollably.”

### Resource Estimation
Based on predicted inflow and average handling time, the system recommends:
- Estimated total hours  
- Required engineers  
- QA testing effort  

---

## ⚙️ Features
Predicts **defect inflow and outflow** using mock or real repository data  
Calculates **resource allocation needs** based on defined thresholds  
Flags **problematic conditions** (when inflow > outflow)  
Visualizes weekly or deployment-based trends  
Extensible to **GitHub API** or **CI/CD pipelines**

---

## Example Output
Applied to the *Microsoft PowerToys* repository, the system produced the following forecast:

| Metric | Value |
|--------|--------|
| **Predicted inflow** | 97 defects |
| **Predicted outflow** | 77 defects |
| **Estimated total hours** | 388 h |
| **Recommended engineers** | 13 |
| **QA effort** | 116.4 h |


 

---

## Methodology

1. **Data Generation / Collection**
   - Uses manual data from weekly inflow/outflow counts.
   - Fetches real GitHub issue statistics.

2. **Computation**
   - Detects when `inflow > outflow` for consecutive weeks.
   - Applies thresholds to determine when extra resources are needed.

3. **Forecasting**
   - Predicts upcoming inflow/outflow using linear or moving-average trends.

4. **Interpretation**
   - Produces actionable recommendations and risk indicators.

---

## Run the project

pip install -r requirements.txt

### Use with an open-source repo
```bash
export GITHUB_TOKEN=YOUR_TOKEN
python src/fetch_github.py --repo owner/name --since 2024-01-01 --until 2025-12-31 --out data/base_measures.csv
python src/cli.py --data data/base_measures.csv --config config/analysis_model.yaml --horizon 1 (horizon can be changed based on how far ehead the prediction needs to be)

For manual input, just modify the data/base_measures.csv file and then run src/cli.py```

Columns (Base Measures)

week_start, defects_inflow_total, defects_outflow_total, severity_critical_in, severity_high_in, severity_medium_in, severity_low_in, avg_resolution_time_hours, backlog_total



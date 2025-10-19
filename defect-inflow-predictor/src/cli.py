import argparse, json, math
from pathlib import Path
import pandas as pd
import numpy as np
import yaml

def load_config(path: Path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def derive_measures(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    df = df.copy()
    df["net_flow"] = df["defects_inflow_total"] - df["defects_outflow_total"]
    df["inflow_rate"] = df["defects_inflow_total"]
    df["outflow_rate"] = df["defects_outflow_total"]
    w = cfg["severity_weights"]
    df["severity_weighted_inflow"] = (
        w["critical"] * df["severity_critical_in"] +
        w["high"]     * df["severity_high_in"] +
        w["medium"]   * df["severity_medium_in"] +
        w["low"]      * df["severity_low_in"]
    )
    df["severe_inflow"] = df["severity_critical_in"] + df["severity_high_in"]
    df["mttr_hours"] = df["avg_resolution_time_hours"]
    return df

def ewma(series: pd.Series, alpha: float, horizon: int):
    forecast = series.iloc[-1]
    for _ in range(horizon):
        forecast = alpha * series.iloc[-1] + (1-alpha) * forecast
    return forecast

def linreg_forecast(y: np.ndarray, horizon: int):
    x = np.arange(len(y))
    a, b = np.polyfit(x, y, 1)
    preds = []
    for h in range(1, horizon+1):
        preds.append(a*(len(y)-1 + h) + b)
    return float(preds[-1])

def forecast_next(df: pd.DataFrame, cfg: dict, horizon: int):
    # choose method dynamically
    method = cfg.get("forecast", {}).get("method", "ewma")
    if horizon > 3 and method == "ewma":
        # automatically switch for long horizon
        print(f"(auto-switch) Using linear regression for horizon={horizon}")
        method = "linreg"

    if method == "ewma":
        alpha = float(cfg["forecast"]["ewma_alpha"])
        inflow_pred  = ewma(df["defects_inflow_total"], alpha, horizon)
        outflow_pred = ewma(df["defects_outflow_total"], alpha, horizon)
    else:
        inflow_pred  = linreg_forecast(df["defects_inflow_total"].to_numpy(), horizon)
        outflow_pred = linreg_forecast(df["defects_outflow_total"].to_numpy(), horizon)

    # compute severity mix as before
    recent = df.tail(10).mean(numeric_only=True)
    total = recent.get("defects_inflow_total", 0.0) or 1.0
    mix = {
        "critical": float(recent.get("severity_critical_in",0.0)/total),
        "high":     float(recent.get("severity_high_in",0.0)/total),
        "medium":   float(recent.get("severity_medium_in",0.0)/total),
        "low":      float(recent.get("severity_low_in",0.0)/total),
    }
    sev_pred = {k: max(0.0, round(mix[k]*inflow_pred,1)) for k in mix}
    return max(0.0, float(inflow_pred)), max(0.0, float(outflow_pred)), sev_pred


def indicators(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    th = cfg["health_thresholds"]
    df = df.copy()
    prob = []
    status = []
    for i in range(len(df)):
        wdf = df.iloc[:i+1]
        flags = []
        N = int(th["inflow_gt_outflow_consecutive_weeks"])
        if i+1 >= N and all((wdf.tail(N)["defects_inflow_total"] > wdf.tail(N)["defects_outflow_total"]).tolist()):
            flags.append("inflow>outflow")
        if df.iloc[i]["backlog_total"] > th["backlog_healthy_max"]:
            flags.append("backlog_high")
        K = int(th["critical_severe_window"])
        severe_sum = wdf.tail(K)["severe_inflow"].sum()
        if severe_sum >= th["critical_severe_min"]:
            flags.append("severe_spike")
        if "severe_spike" in flags or ("inflow>outflow" in flags and "backlog_high" in flags):
            status.append("red")
        elif flags:
            status.append("yellow")
        else:
            if df.iloc[i]["defects_inflow_total"] <= th["healthy_max_per_deployment"]:
                status.append("green")
            else:
                status.append("yellow")
        prob.append(",".join(flags) if flags else "")
    df["problem_flags"] = prob
    df["health_status"] = status
    return df

def resource_plan(next_inflow: float, sev_pred: dict, cfg: dict):
    hp = cfg["resources"]["hours_per_defect"]
    total_hours = 0.0
    for k, count in sev_pred.items():
        total_hours += hp[k] * float(count)
    cap = float(cfg["resources"]["engineer_capacity_hours_per_week"])
    engineers = int(np.ceil(total_hours / cap)) if cap>0 else 0
    qa_hours = total_hours * float(cfg["resources"]["qa_share"])
    return {
        "predicted_inflow": round(next_inflow,1),
        "estimated_total_hours": round(total_hours,1),
        "recommended_engineers": int(engineers),
        "recommended_qa_hours": round(qa_hours,1),
        "hours_per_defect": hp
    }

def main():
    ap = argparse.ArgumentParser(description="Defect Inflow Predictor & Resource Planner")
    ap.add_argument("--data", default="data/base_measures.csv")
    ap.add_argument("--config", default="config/analysis_model.yaml")
    ap.add_argument("--horizon", type=int, default=None)
    ap.add_argument("--outdir", default="outputs")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    horizon = args.horizon or int(cfg["forecast"]["horizon_weeks"])
    df = pd.read_csv(args.data)
    dfd = derive_measures(df, cfg)
    dfi = indicators(dfd, cfg)
    inflow_pred, outflow_pred, sev_pred = forecast_next(dfd, cfg, horizon)
    plan = resource_plan(inflow_pred, sev_pred, cfg)

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    dfd.to_csv(outdir/"derived_measures.csv", index=False)
    dfi.to_csv(outdir/"indicators.csv", index=False)
    with open(outdir/"forecast_and_plan.json","w") as f:
        json.dump({
            "horizon_weeks": horizon,
            "forecast": {
                "inflow_total": round(inflow_pred,1),
                "outflow_total": round(outflow_pred,1),
                "severity_breakdown_inflow": sev_pred
            },
            "resource_plan": plan
        }, f, indent=2)

    print("# Forecast (", horizon, "week ahead )")
    print("Predicted inflow:", round(inflow_pred,1), "Predicted outflow:", round(outflow_pred,1))
    print("Severity mix (inflow):", sev_pred)
    print("\n# Resource plan")
    import json as _j
    print(_j.dumps(plan, indent=2))
    print("\nWrote:", outdir/"derived_measures.csv", outdir/"indicators.csv", outdir/"forecast_and_plan.json")

if __name__ == "__main__":
    main()
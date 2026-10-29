"""Analysis functions over the yfinance CSV files (annual and quarterly)."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Metrics to compare. True = higher is better, False = lower is better.
METRICS = {
    "gross_margin": True,
    "operating_margin": True,
    "profit_margin": True,
    "roe": True,
    "roa": True,
    "revenue_growth_yoy": True,
    "debt_to_equity": False,
    "current_ratio": True,
}


# ---------- Loading ----------
def load_annual() -> pd.DataFrame:
    """Read the annual financials CSV."""
    return pd.read_csv(
        DATA_DIR / "financieros_anuales.csv", parse_dates=["period_end"]
    )


def load_quarterly() -> pd.DataFrame:
    """Read the quarterly financials CSV."""
    return pd.read_csv(
        DATA_DIR / "financieros_trimestrales.csv", parse_dates=["period_end"]
    )


# ---------- Cleaning ----------
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Drop empty rows returned by Yahoo and flag negative stockholders' equity."""
    df = df.dropna(subset=["Total Revenue"]).copy()

    # With equity <= 0, ROE and debt/equity are not interpretable (e.g. Dell)
    df["negative_equity"] = df["Stockholders Equity"] <= 0
    df.loc[df["negative_equity"], ["roe", "debt_to_equity"]] = np.nan

    return df.sort_values(["ticker", "period_end"]).reset_index(drop=True)


# ---------- Queries ----------
def latest_period(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent row available for each company."""
    return df.sort_values("period_end").groupby("ticker").tail(1).reset_index(drop=True)


def trend(df: pd.DataFrame, metric: str, axis: str = "period") -> pd.DataFrame:
    """Period x company table, ready to plot one line per company."""
    return df.pivot(index=axis, columns="ticker", values=metric).sort_index()


def ranking(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Rank companies on a metric using each one's latest period."""
    latest = latest_period(df)[["ticker", "period", metric]].dropna(subset=[metric])
    higher_is_better = METRICS.get(metric, True)
    latest["rank"] = (
        latest[metric].rank(ascending=not higher_is_better, method="min").astype(int)
    )
    return latest.sort_values("rank").reset_index(drop=True)


def hpe_summary(df: pd.DataFrame, company: str = "HPE") -> pd.DataFrame:
    """Compare one company against the average of its peers (latest period)."""
    latest = latest_period(df).set_index("ticker")
    cols = [m for m in METRICS if m in latest.columns]

    focus = latest.loc[company, cols]
    peers = latest.drop(index=company)[cols].mean()

    out = pd.DataFrame({company: focus, "peer_average": peers})
    out["difference"] = out[company] - out["peer_average"]
    return out


# ---------- Validation ----------
def validate_data(df: pd.DataFrame, tol: float = 0.005) -> pd.DataFrame:
    """Return rows with consistency problems (empty result = everything OK)."""
    issues = []

    def check(mask: pd.Series, reason: str) -> None:
        if mask.any():
            bad = df.loc[mask, ["ticker", "period"]].copy()
            bad["issue"] = reason
            issues.append(bad)

    check(df["Total Revenue"] <= 0, "Revenue <= 0")
    check(df["Total Assets"] <= 0, "Total assets <= 0")
    check(df["Gross Profit"] > df["Total Revenue"], "Gross profit > revenue")

    for m in ["gross_margin", "operating_margin", "profit_margin"]:
        check(df[m].notna() & ~df[m].between(-1, 1), f"{m} out of range")

    recomputed = df["Operating Income"] / df["Total Revenue"]
    diff = (recomputed - df["operating_margin"]).abs()
    check(diff > tol, "operating_margin does not match recomputed value")

    check(df.duplicated(["ticker", "period"], keep=False), "Duplicated period")

    if not issues:
        return pd.DataFrame(columns=["ticker", "period", "issue"])
    return pd.concat(issues, ignore_index=True)
"""
Extrae estados financieros trimestrales y anuales desde yfinance
para HPE y competidores, calcula métricas por periodo y guarda CSVs.

Uso:
    pip install yfinance pandas
    python extraer_financieros.py
"""
from pathlib import Path

import pandas as pd
import yfinance as yf

TICKERS = ["HPE", "DELL", "IBM", "CSCO"]
START = "2020-01-01"
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

# Filas de Yahoo que necesitamos (si no existen, quedan en NaN)
COLS = [
    "Total Revenue", "Gross Profit", "Operating Income", "Net Income", "EBITDA",
    "Total Debt", "Stockholders Equity", "Total Assets",
    "Current Assets", "Current Liabilities", "Ordinary Shares Number",
]


def get_financials(symbol: str, freq: str = "quarterly") -> pd.DataFrame:
    t = yf.Ticker(symbol)
    if freq == "quarterly":
        inc, bal = t.quarterly_income_stmt, t.quarterly_balance_sheet
    else:
        inc, bal = t.income_stmt, t.balance_sheet

    if inc is None or inc.empty or bal is None or bal.empty:
        print(f"[!] Sin datos {freq} para {symbol}")
        return pd.DataFrame()

    # Yahoo devuelve fechas como columnas -> transponemos
    df = pd.concat([inc.T, bal.T], axis=1)
    df = df.loc[:, ~df.columns.duplicated()]
    df.index = pd.to_datetime(df.index)
    df = df.sort_index().reindex(columns=COLS)

    # Métricas calculadas
    df["gross_margin"] = df["Gross Profit"] / df["Total Revenue"]
    df["operating_margin"] = df["Operating Income"] / df["Total Revenue"]
    df["profit_margin"] = df["Net Income"] / df["Total Revenue"]
    df["roe"] = df["Net Income"] / df["Stockholders Equity"]
    df["roa"] = df["Net Income"] / df["Total Assets"]
    df["debt_to_equity"] = df["Total Debt"] / df["Stockholders Equity"]
    df["current_ratio"] = df["Current Assets"] / df["Current Liabilities"]

    # Crecimiento YoY: 4 periodos atrás si es trimestral, 1 si es anual
    lag = 4 if freq == "quarterly" else 1
    df["revenue_growth_yoy"] = df["Total Revenue"].pct_change(lag, fill_method=None)

    # Etiquetas de periodo (trimestre CALENDARIO de la fecha de cierre)
    df["year"] = df.index.year
    if freq == "quarterly":
        df["quarter"] = df.index.quarter
        df["period"] = df.index.to_period("Q").astype(str)
    else:
        df["quarter"] = pd.NA
        df["period"] = df.index.year.astype(str)

    # Métricas de mercado: precio al cierre del periodo x acciones
    px = t.history(start=START, auto_adjust=False)["Close"]
    if not px.empty:
        px.index = px.index.tz_localize(None)
        df["price"] = [
            px.loc[:d].iloc[-1] if len(px.loc[:d]) else None for d in df.index
        ]
    else:
        df["price"] = None
    df["market_cap"] = df["price"] * df["Ordinary Shares Number"]

    df["ticker"] = symbol
    return df[df.index >= START].reset_index(names="period_end")


def main():
    q = pd.concat(
        [get_financials(s, "quarterly") for s in TICKERS], ignore_index=True
    )
    a = pd.concat(
        [get_financials(s, "annual") for s in TICKERS], ignore_index=True
    )

    q.to_csv(OUT / "financieros_trimestrales.csv", index=False)
    a.to_csv(OUT / "financieros_anuales.csv", index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    # 1) Cobertura real que entrega Yahoo
    print("\n=== COBERTURA TRIMESTRAL ===")
    print(q.groupby("ticker")["period_end"].agg(["min", "max", "count"]))
    print("\n=== COBERTURA ANUAL ===")
    print(a.groupby("ticker")["period_end"].agg(["min", "max", "count"]))

    # 2) Último trimestre por empresa
    cols = ["ticker", "period", "Total Revenue", "gross_margin",
            "operating_margin", "profit_margin", "roe", "debt_to_equity"]
    print("\n=== ÚLTIMO TRIMESTRE POR EMPRESA ===")
    print(q.sort_values("period_end").groupby("ticker").tail(1)[cols])

    # 3) Tendencia anual de margen operativo
    print("\n=== MARGEN OPERATIVO ANUAL ===")
    print(a.pivot(index="period", columns="ticker", values="operating_margin"))

    # 4) Revisar huecos (NaN) por columna
    print("\n=== NaN POR COLUMNA (trimestral) ===")
    print(q[COLS].isna().sum())


if __name__ == "__main__":
    main()

"""Funciones de análisis sobre los CSV de yfinance (anual y trimestral)."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Métricas que se comparan y si "más alto = mejor"
METRICAS = {
    "gross_margin": True,
    "operating_margin": True,
    "profit_margin": True,
    "roe": True,
    "roa": True,
    "revenue_growth_yoy": True,
    "debt_to_equity": False,  # menos deuda = mejor
    "current_ratio": True,
}


# ---------- Carga ----------
def cargar_anual() -> pd.DataFrame:
    return pd.read_csv(
        DATA_DIR / "financieros_anuales.csv", parse_dates=["period_end"]
    )


def cargar_trimestral() -> pd.DataFrame:
    return pd.read_csv(
        DATA_DIR / "financieros_trimestrales.csv", parse_dates=["period_end"]
    )


# ---------- Limpieza ----------
def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Quita filas vacías de Yahoo y marca capital contable negativo."""
    df = df.dropna(subset=["Total Revenue"]).copy()

    # Con capital <= 0, ROE y deuda/capital no son interpretables (ej. Dell)
    df["equity_negativo"] = df["Stockholders Equity"] <= 0
    df.loc[df["equity_negativo"], ["roe", "debt_to_equity"]] = np.nan

    return df.sort_values(["ticker", "period_end"]).reset_index(drop=True)


# ---------- Consultas ----------
def ultimo_periodo(df: pd.DataFrame) -> pd.DataFrame:
    """Última fila disponible por empresa."""
    return df.sort_values("period_end").groupby("ticker").tail(1).reset_index(drop=True)


def tendencia(df: pd.DataFrame, metrica: str, eje: str = "period") -> pd.DataFrame:
    """Tabla periodo x empresa, lista para graficar una línea por empresa."""
    return df.pivot(index=eje, columns="ticker", values=metrica).sort_index()


def ranking(df: pd.DataFrame, metrica: str) -> pd.DataFrame:
    """Ranking de empresas en su último periodo para una métrica."""
    ult = ultimo_periodo(df)[["ticker", "period", metrica]].dropna(subset=[metrica])
    mejor_alto = METRICAS.get(metrica, True)
    ult["posicion"] = ult[metrica].rank(ascending=not mejor_alto, method="min").astype(int)
    return ult.sort_values("posicion").reset_index(drop=True)


def resumen_hpe(df: pd.DataFrame, empresa: str = "HPE") -> pd.DataFrame:
    """HPE vs promedio de competidores en el último periodo de cada una."""
    ult = ultimo_periodo(df).set_index("ticker")
    cols = [m for m in METRICAS if m in ult.columns]

    hpe = ult.loc[empresa, cols]
    pares = ult.drop(index=empresa)[cols].mean()

    out = pd.DataFrame({empresa: hpe, "promedio_competidores": pares})
    out["diferencia"] = out[empresa] - out["promedio_competidores"]
    return out


# ---------- Validación ----------
def validar_datos(df: pd.DataFrame, tol: float = 0.005) -> pd.DataFrame:
    """Devuelve las filas con problemas de coherencia (vacío = todo OK)."""
    problemas = []

    def revisar(mask: pd.Series, motivo: str) -> None:
        if mask.any():
            malo = df.loc[mask, ["ticker", "period"]].copy()
            malo["problema"] = motivo
            problemas.append(malo)

    revisar(df["Total Revenue"] <= 0, "Ingresos <= 0")
    revisar(df["Total Assets"] <= 0, "Activos <= 0")
    revisar(df["Gross Profit"] > df["Total Revenue"], "Gross Profit > Revenue")

    for m in ["gross_margin", "operating_margin", "profit_margin"]:
        revisar(df[m].notna() & ~df[m].between(-1, 1), f"{m} fuera de rango")

    recalculo = df["Operating Income"] / df["Total Revenue"]
    dif = (recalculo - df["operating_margin"]).abs()
    revisar(dif > tol, "operating_margin no coincide con el recálculo")

    revisar(df.duplicated(["ticker", "period"], keep=False), "Periodo duplicado")

    if not problemas:
        return pd.DataFrame(columns=["ticker", "period", "problema"])
    return pd.concat(problemas, ignore_index=True)
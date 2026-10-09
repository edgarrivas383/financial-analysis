from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "metricas_financieras.csv"


def cargar_datos(path=DATA_PATH):
    return pd.read_csv(path)


def limpiar_datos(df):
    """Convierte porcentajes y redondea valores para display."""
    df = df.copy()

    cols_porcentaje = [
        "Margen Neto",
        "Margen Bruto",
        "Margen Operativo",
        "ROE",
        "ROA",
        "Crecimiento Ingresos"
    ]

    for col in cols_porcentaje:
        if col in df.columns:
            df[col] = (df[col] * 100).round(2)

    for col in ["Market Cap", "Ingresos Totales"]:
        if col in df.columns:
            df[col] = (df[col] / 1e9).round(2)

    df = df.round(2)

    return df


def ranking(df, metrica, ascendente=False):
    """Regresa el DataFrame ordenado por una métrica."""
    return (
        df[["Empresa", "Ticker", metrica]]
        .sort_values(metrica, ascending=ascendente)
        .reset_index(drop=True)
    )


def resumen_hpe(df):
    """Extrae solo la fila de HPE para comparar contra el promedio."""
    promedio = df.select_dtypes(include="number").mean().round(2)
    hpe = df[df["Ticker"] == "HPE"].squeeze()

    comparacion = pd.DataFrame({
        "HPE": hpe[promedio.index],
        "Promedio Competidores": promedio
    })

    return comparacion

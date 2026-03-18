
import yfinance as yf
import pandas as pd
import os

TICKERS = ["HPE", "DELL", "IBM", "CSCO", "NTAP"]

METRICAS = {
    "shortName": "Empresa",
    "marketCap": "Market Cap",
    "trailingPE": "P/E Ratio",
    "forwardPE": "P/E Forward",
    "priceToBook": "P/B Ratio",
    "enterpriseToEbitda": "EV/EBITDA",
    "profitMargins": "Margen Neto",
    "grossMargins": "Margen Bruto",
    "operatingMargins": "Margen Operativo",
    "returnOnEquity": "ROE",
    "returnOnAssets": "ROA",
    "revenueGrowth": "Crecimiento Ingresos",
    "totalRevenue": "Ingresos Totales",
    "debtToEquity": "Deuda/Capital",
    "currentRatio": "Razón Corriente",
}

def obtener_datos(tickers=TICKERS):
    """Descarga métricas financieras de una lista de tickers."""
    resultados = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            fila = {"Ticker": ticker}
            for key, nombre in METRICAS.items():
                fila[nombre] = info.get(key, None)
            resultados.append(fila)
            print(f"[OK] {ticker} descargado")
        except Exception as e:
            print(f"[ERROR] Error con {ticker}: {e}")
    return pd.DataFrame(resultados)

if __name__ == "__main__":
    # Creamos la carpeta data si no existe (ahora sí la encontrará)
    os.makedirs("data", exist_ok=True)

    df = obtener_datos()
    df.to_csv("data/metricas_financieras.csv", index=False)
    print("\n Proceso completado. Archivo guardado en data/metricas_financieras.csv")

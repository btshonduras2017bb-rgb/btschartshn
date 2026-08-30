import io
import pandas as pd
import requests
import streamlit as st


# Función mejorada para obtener datos de Kworb
def get_kworb_data(url):
  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    # Convertimos el contenido a StringIO para evitar avisos de deprecación en pandas
    dfs = pd.read_html(io.StringIO(response.text))
    return dfs[0]
  except Exception as e:
    return pd.DataFrame({"Error": [f"No se pudieron cargar los datos: {e}"]})

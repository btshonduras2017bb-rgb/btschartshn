import io
import re
import pandas as pd
import requests
import streamlit as st


# Función para obtener y filtrar datos de Kworb
def get_kworb_data(url):
  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    dfs = pd.read_html(io.StringIO(response.text))
    df = dfs[0]

    # Lista de nombres/términos a buscar (insensible a mayúsculas/minúsculas)
    # Incluye nombres artísticos, nombres reales y combinaciones habituales
    bts_keywords = [
        r"\bbts\b",
        r"\brm\b",
        r"\bkim namjoon\b",
        r"\bjin\b",
        r"\bkim seokjin\b",
        r"\bsuga\b",
        r"\bagust d\b",
        r"\bmin yoongi\b",
        r"\bj-hope\b",
        r"\bjhope\b",
        r"\bjung hoseok\b",
        r"\bjimin\b",
        r"\bpark jimin\b",
        r"\b\bv\b\b",  # Coincide únicamente con la letra 'V' como palabra completa
        r"\bkim taehyung\b",
        r"\bjung kook\b",
        r"\bjungkook\b",
        r"\bjeon jungkook\b",
    ]

    # Crear una sola expresión regular uniendo todas las palabras
    pattern = "|".join(bts_keywords)

    # Identificar las columnas donde suele venir el artista o el título del tema
    # Kworb suele usar columnas como 'Artist', 'Artist and Title' o 'Track'
    text_columns = [
        col
        for col in df.columns
        if df[col].dtype == "object" or col.lower() in ["artist", "title", "track"]
    ]

    if text_columns:
      # Filtrar filas donde al menos una columna de texto coincida con los integrantes o BTS
      mask = pd.Series(False, index=df.index)
      for col in text_columns:
        mask |= df[col].astype(str).str.contains(pattern, case=False, regex=True)

      df_filtered = df[mask]

      if df_filtered.empty:
        return pd.DataFrame({
            "Información": [
                "No se encontraron canciones de BTS o sus solistas en este"
                " chart actualmente."
            ]
        })

      return df_filtered
    else:
      return df

  except Exception as e:
    return pd.DataFrame({"Error": [f"No se pudieron cargar los datos: {e}"]})


# Configuración de la página
st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

# Encabezado principal
st.title("💜 BTS Honduras Charts")
st.write(
    "¡Revisa en tiempo real las posiciones de BTS y sus integrantes en solo!"
)

# Banner principal
st.image(
    "https://pbs.twimg.com/media/HQyPXMUboAAvvBx?format=jpg&name=4096x4096",
    use_container_width=True,
)

# Menú lateral
st.sidebar.title("Navegación")
opcion = st.sidebar.radio(
    "Ir a:",
    [
        "Inicio",
        "Spotify",
        "Apple Music",
        "Youtube Music",
        "Deezer",
        "Redes Sociales",
    ],
)

if opcion == "Inicio":
  st.header("Sobre Nosotros")
  st.write(
      "Aquí encontrarás las novedades, proyectos de streaming y estadísticas"
      " exclusivas de BTS y sus solistas en Honduras."
  )

elif opcion == "Spotify":
  st.header("🎧 Spotify Charts (Filtro BTS & Solistas)")

  st.subheader("Honduras 🇭🇳")
  c1, c2 = st.columns(2)
  with c1:
    st.markdown("**Top Diario Honduras**")
    df_hd = get_kworb_data("https://kworb.net/spotify/country/hn_daily.html")
    st.dataframe(df_hd, hide_index=True, use_container_width=True, height=500)
  with c2:
    st.markdown("**Top Semanal Honduras**")
    df_hw = get_kworb_data("https://kworb.net/spotify/country/hn_weekly.html")
    st.dataframe(df_hw, hide_index=True, use_container_width=True, height=500)

  st.divider()

  st.subheader("Global 🌍")
  c3, c4 = st.columns(2)
  with c3:
    st.markdown("**Top Diario Global**")
    df_gd = get_kworb_data(
        "https://kworb.net/spotify/country/global_daily.html"
    )
    st.dataframe(df_gd, hide_index=True, use_container_width=True, height=500)
  with c4:
    st.markdown("**Top Semanal Global**")
    df_gw = get_kworb_data(
        "https://kworb.net/spotify/country/global_weekly.html"
    )
    st.dataframe(df_gw, hide_index=True, use_container_width=True, height=500)

elif opcion == "Apple Music":
  st.header("📊 Apple Music")
  st.write("Sección de Apple Music en construcción.")

elif opcion == "Youtube Music":
  st.header("📊 Youtube Music")
  st.write("Sección de YouTube Music en construcción.")

elif opcion == "Deezer":
  st.header("📊 Deezer")
  st.write("Sección de Deezer en construcción.")

elif opcion == "Redes Sociales":
  st.header("Síguenos")
  st.markdown("[X / Twitter](https://x.com) | [Instagram](https://instagram.com)")

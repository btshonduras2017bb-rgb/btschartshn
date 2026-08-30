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

    # Lista de nombres/términos a buscar
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
        r"\bv\b",  # Corregido: Coincide solo con 'V' como palabra independiente
        r"\bkim taehyung\b",
        r"\bjung kook\b",
        r"\bjungkook\b",
        r"\bjeon jungkook\b",
    ]

    pattern = "|".join(bts_keywords)

    # Buscar en la columna que contiene Artista y Título
    target_col = None
    for col in df.columns:
      if "artist" in str(col).lower() or "title" in str(col).lower():
        target_col = col
        break

    if target_col is None:
      # Si no detecta la columna por nombre, toma la primera columna con texto
      text_cols = [c for c in df.columns if df[c].dtype == "object"]
      if text_cols:
        target_col = text_cols[0]

    if target_col:
      # Filtrar las filas que contengan a BTS o sus integrantes
      mask = df[target_col].astype(str).str.contains(pattern, case=False, regex=True)
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

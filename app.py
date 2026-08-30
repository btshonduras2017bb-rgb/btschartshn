import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

# Integrantes y nombres de BTS
SOLO_BTS = [
    "BTS",
    "JUNG KOOK",
    "JUNGKOOK",
    "JIMIN",
    "SUGA",
    "J-HOPE",
    "JHOPE",
    "RM",
    "JIN",
    "AGUST D",
    "V",
]


def es_bts(texto):
  if not texto:
    return False
  txt = str(texto).upper()
  return any(m in txt for m in SOLO_BTS)


@st.cache_data(ttl=1800, show_spinner=False)
def get_spotify_official_chart(region="HN", period="daily"):
  """Obtiene el chart oficial de Spotify (Top Canciones).

  region: 'hn' para Honduras, 'global' para Global. period: 'daily' o 'weekly'.
  """
  url = f"https://charts-spotify-com-service.spotify.com/public/v10/charts/regional-{region}-{period}/latest"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  try:
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code != 200:
      # Fallback al CSV oficial si el JSON cambia
      return pd.DataFrame({"Aviso": ["No se pudo conectar a Spotify Charts."]}), ""

    data = res.json()
    chart_date = data.get("chartEntry", {}).get("chartDate", "")
    entries = (
        data.get("chartEntry", {})
        .get("textEntries", {})
        .get("textChartEntries", [])
    )

    rows = []
    for item in entries:
      puesto = item.get("chartPosition")
      mov_type = item.get("chartPositionEntry", {}).get("entryStatus", "")
      mov_num = item.get("chartPositionEntry", {}).get("ranksChanged", 0)

      # Formatear movimiento
      if mov_type == "NEW":
        mov = f"🟦 N#{puesto}"
      elif mov_type == "RE_ENTRY":
        mov = "🔄 Re-Entry"
      elif mov_num > 0:
        mov = f"🟩 +{mov_num}"
      elif mov_num < 0:
        mov = f"🟥 {mov_num}"
      else:
        mov = "➡️ ="

      track_name = item.get("trackMetadata", {}).get("trackName", "")
      artists = [
          a.get("name", "")
          for a in item.get("trackMetadata", {}).get("artists", [])
      ]
      artist_str = ", ".join(artists)
      full_title = f"{artist_str} - {track_name}"

      if es_bts(full_title) or any(es_bts(a) for a in artists):
        streams = item.get("chartPositionEntry", {}).get("streamCount", 0)
        rows.append({
            "Posición": f"#{puesto}",
            "Cambio": mov,
            "Artista & Canción": full_title,
            "Streams": f"{streams:,}",
        })

    df = pd.DataFrame(rows)
    if df.empty:
      return (
          pd.DataFrame({
              "Información": [
                  "No hay entradas de BTS en el Top 200 de esta lista."
              ]
          }),
          chart_date,
      )

    return df, chart_date
  except Exception as e:
    return (
        pd.DataFrame(
            {"Aviso": ["Error al procesar los datos de Spotify Charts."]}
        ),
        "",
    )


# --- Interfaz Streamlit ---
st.title("💜 BTS Honduras Charts (Datos Oficiales Spotify)")

tab_hn, tab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

with tab_hn:
  st.subheader("Spotify Top Canciones - Honduras")
  col1, col2 = st.columns(2)

  with col1:
    df_d, fecha_d = get_spotify_official_chart("hn", "daily")
    st.markdown(f"**Diario Oficial** `{fecha_d}`")
    st.dataframe(df_d, hide_index=True, use_container_width=True)

  with col2:
    df_w, fecha_w = get_spotify_official_chart("hn", "weekly")
    st.markdown(f"**Semanal Oficial** `{fecha_w}`")
    st.dataframe(df_w, hide_index=True, use_container_width=True)

with tab_global:
  st.subheader("Spotify Top Canciones - Global")
  col3, col4 = st.columns(2)

  with col3:
    df_gd, fecha_gd = get_spotify_official_chart("global", "daily")
    st.markdown(f"**Diario Global Oficial** `{fecha_gd}`")
    st.dataframe(df_gd, hide_index=True, use_container_width=True)

  with col4:
    df_gw, fecha_gw = get_spotify_official_chart("global", "weekly")
    st.markdown(f"**Semanal Global Oficial** `{fecha_gw}`")
    st.dataframe(df_gw, hide_index=True, use_container_width=True)

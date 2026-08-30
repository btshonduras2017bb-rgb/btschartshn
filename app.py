import random
import re
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# Configuración e Interfaz Streamlit
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

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
]


def icon_mov(val):
  try:
    val = str(val).strip()
    if val in ["=", "0", ""]:
      return "➡️ ="
    if "+" in val or val.startswith("+"):
      return f"🟩 {val}"
    if "-" in val or val.startswith("-"):
      return f"🟥 {val}"
    if val.isdigit():
      return f"🟦 N{val}"
    return f"➡️ {val}"
  except Exception:
    return "➡️ ="


def es_artista_valido(text_completo):
  try:
    text_upper = str(text_completo).upper()
    exclusiones = [
        "BAD BUNNY",
        "DEI V",
        "OMAR COURTZ",
        "TITO DOUBLE P",
        "MUSA ELEVA",
    ]
    if any(exc in text_upper for exc in exclusiones):
      return False

    if any(
        re.search(rf"\b{re.escape(member)}\b", text_upper)
        for member in SOLO_BTS
    ):
      return True

    if re.search(r"\bV\b", text_upper):
      if any(k in text_upper for k in ["BTS", "FEAT. V", "FT. V"]):
        return True
      partes = text_upper.split(" - ")
      if len(partes) > 0 and re.search(r"^\bV\b", partes[0].strip()):
        return True

    return False
  except Exception:
    return False


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_spotify_charts_api(region="hn", period="daily", chart_type="regional"):
  """Consulta directa a la infraestructura pública de Spotify Charts."""
  # regional: canciones | artist: artistas
  url = f"https://charts-spotify-com-service.spotify.com/public/v10/charts/{chart_type}-{region}-{period}/latest"

  headers = {
      "User-Agent": random.choice(USER_AGENTS),
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
      "Origin": "https://charts.spotify.com",
      "Referer": "https://charts.spotify.com/",
  }

  try:
    session = requests.Session()
    res = session.get(url, headers=headers, timeout=10)

    if res.status_code == 200:
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

        if chart_type == "regional":
          track_name = item.get("trackMetadata", {}).get("trackName", "")
          artists = [
              a.get("name", "")
              for a in item.get("trackMetadata", {}).get("artists", [])
          ]
          artist_str = ", ".join(artists)
          full_title = f"{artist_str} - {track_name}"

          if es_artista_valido(full_title) or any(
              es_artista_valido(a) for a in artists
          ):
            streams = item.get("chartPositionEntry", {}).get("streamCount", 0)
            rows.append({
                "Posición": f"#{puesto}",
                "Cambio": mov,
                "Artista & Canción": full_title,
                "Streams": f"{streams:,}" if streams else "N/A",
            })
        else:
          artist_name = item.get("artistMetadata", {}).get("artistName", "")
          if es_artista_valido(artist_name):
            rows.append({
                "Posición": f"#{puesto}",
                "Artista": artist_name,
                "Cambio": mov,
            })

      df = pd.DataFrame(rows)
      if df.empty:
        return (
            pd.DataFrame({
                "Información": [
                    "Sin entradas de BTS en la lista oficial de hoy."
                ]
            }),
            chart_date,
        )

      return df, chart_date
  except Exception:
    pass

  return (
      pd.DataFrame({
          "Aviso": [
              "Spotify Charts se está actualizando. Vuelve a intentar en unos"
              " minutos."
          ]
      }),
      "",
  )


@st.cache_data(ttl=1800, show_spinner=False)
def get_deezer_chart(url):
  headers = {"User-Agent": random.choice(USER_AGENTS)}
  try:
    res = requests.get(url, headers=headers, timeout=8)
    if res.status_code != 200:
      return pd.DataFrame({"Aviso": ["No disponible por el momento."]})

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table")
    if not table:
      return pd.DataFrame({"Información": ["Sin datos."]})

    rows = []
    for tr in table.find_all("tr")[1:]:
      cols = tr.find_all("td")
      if len(cols) < 3:
        continue

      puesto = cols[0].text.strip()
      mov = icon_mov(cols[1].text.strip())
      full_text = cols[2].get_text(separator=" ").strip()

      if es_artista_valido(full_text):
        rows.append({
            "Posición": f"#{puesto}",
            "Cambio": mov,
            "Artista & Canción": full_text,
        })

    df = pd.DataFrame(rows)
    return (
        df
        if not df.empty
        else pd.DataFrame({"Información": ["Sin coincidencias en Deezer."]})
    )
  except Exception:
    return pd.DataFrame({"Aviso": ["Error al cargar Deezer."]})


# --- Estructura Principal ---
st.title("💜 BTS Honduras Charts")
st.write(
    "¡Revisa en tiempo real las posiciones oficiales de BTS y sus integrantes"
    " en solo!"
)

(
    tab_inicio,
    tab_spotify,
    tab_apple,
    tab_yt,
    tab_deezer,
    tab_redes,
) = st.tabs([
    "🏠 Inicio",
    "🎧 Spotify",
    "📊 Apple Music",
    "▶️ YouTube Music",
    "🔊 Deezer",
    "🌐 Redes Sociales",
])

with tab_inicio:
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.image(
        "https://pbs.twimg.com/media/HQyPXMUboAAvvBx?format=jpg&name=4096x4096",
        width=450,
    )

  st.header("Sobre Nosotros")
  st.write(
      "Aquí encontrarás las novedades, proyectos de streaming y estadísticas"
      " exclusivas de BTS y sus solistas en Honduras."
  )

with tab_spotify:
  st.header("🎧 Spotify Official Charts (Directo de Spotify)")
  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      c1, c2 = st.columns(2)
      with c1:
        df_hn_d, fecha_hn_d = fetch_spotify_charts_api(
            "hn", "daily", "regional"
        )
        st.markdown(
            f"**Diario Oficial** `{fecha_hn_d}`"
            if fecha_hn_d
            else "**Diario Oficial**"
        )
        st.dataframe(
            df_hn_d, hide_index=True, use_container_width=True, height=500
        )
      with c2:
        df_hn_w, fecha_hn_w = fetch_spotify_charts_api(
            "hn", "weekly", "regional"
        )
        st.markdown(
            f"**Semanal Oficial** `{fecha_hn_w}`"
            if fecha_hn_w
            else "**Semanal Oficial**"
        )
        st.dataframe(
            df_hn_w, hide_index=True, use_container_width=True, height=500
        )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      df_art_hn, fecha_art_hn = fetch_spotify_charts_api("hn", "daily", "artist")
      if fecha_art_hn:
        st.caption(f"Fecha del reporte oficial: {fecha_art_hn}")
      st.dataframe(
          df_art_hn, hide_index=True, use_container_width=True, height=500
      )

  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(["🎵 Top Canciones", "👤 Top Artistas"])

    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      c3, c4 = st.columns(2)
      with c3:
        df_g_d, fecha_g_d = fetch_spotify_charts_api(
            "global", "daily", "regional"
        )
        st.markdown(
            f"**Diario Global** `{fecha_g_d}`"
            if fecha_g_d
            else "**Diario Global**"
        )
        st.dataframe(
            df_g_d, hide_index=True, use_container_width=True, height=500
        )
      with c4:
        df_g_w, fecha_g_w = fetch_spotify_charts_api(
            "global", "weekly", "regional"
        )
        st.markdown(
            f"**Semanal Global** `{fecha_g_w}`"
            if fecha_g_w
            else "**Semanal Global**"
        )
        st.dataframe(
            df_g_w, hide_index=True, use_container_width=True, height=500
        )

    with tab_g_artists:
      st.subheader("Top Artistas Global 🌍")
      df_art_g, fecha_art_g = fetch_spotify_charts_api(
          "global", "daily", "artist"
      )
      if fecha_art_g:
        st.caption(f"Fecha del reporte oficial: {fecha_art_g}")
      st.dataframe(
          df_art_g, hide_index=True, use_container_width=True, height=500
      )

with tab_apple:
  st.header("📊 Apple Music")
  st.write("Sección de Apple Music en construcción.")

with tab_yt:
  st.header("📊 Youtube Music")
  st.write("Sección de YouTube Music en construcción.")

with tab_deezer:
  st.header("🔊 Deezer Charts")
  cd1, cd2 = st.columns(2)
  with cd1:
    st.subheader("Honduras 🇭🇳")
    st.dataframe(
        get_deezer_chart("https://kworb.net/charts/deezer/hn.html"),
        hide_index=True,
        use_container_width=True,
        height=600,
    )
  with cd2:
    st.subheader("Global 🌍")
    st.dataframe(
        get_deezer_chart("https://kworb.net/charts/deezer/ww.html"),
        hide_index=True,
        use_container_width=True,
        height=600,
    )

with tab_redes:
  st.header("Síguenos")
  st.markdown(
      "[X / Twitter](https://x.com) | [Instagram](https://instagram.com)"
  )

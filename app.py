import datetime
import random
import re
import pandas as pd
import requests
import spotipy
import streamlit as st
from bs4 import BeautifulSoup
from spotipy.oauth2 import SpotifyClientCredentials

st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

# --- CONFIGURACIÓN Y CONSTANTES ---
MIEMBROS_BTS = {
    "BTS": "BTS",
    "Jung Kook": "Jung Kook",
    "Jimin": "Jimin",
    "V": "V",
    "RM": "RM",
    "Jin": "Jin",
    "SUGA": "Agust D",
    "j-hope": "j-hope",
}

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
        " (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
]


# --- CONEXIÓN API OFICIAL SPOTIFY ---
def get_spotify_client():
  try:
    client_id = st.secrets.get(
        "SPOTIPY_CLIENT_ID", "9823fd0dcfb740ad94eb5c7ceb1d4809"
    )
    client_secret = st.secrets.get(
        "SPOTIPY_CLIENT_SECRET", "896a2fd912e24a22b8560bbf15d07200"
    )

    if client_id and client_secret:
      auth_manager = SpotifyClientCredentials(
          client_id=str(client_id).strip(),
          client_secret=str(client_secret).strip(),
      )
      return spotipy.Spotify(auth_manager=auth_manager)
  except Exception as e:
    st.error(f"Error de conexión con Spotify API: {e}")
  return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_spotify_api_tracks(artist_query, market="HN"):
  sp = get_spotify_client()
  if not sp:
    return pd.DataFrame(), datetime.datetime.now().strftime("%Y-%m-%d")

  try:
    # Corrección de parámetros para evitar 'Invalid limit'
    results = sp.search(
        q=f'artist:"{artist_query}"', type="track", limit=20, market=str(market)
    )
    items = results.get("tracks", {}).get("items", [])

    if not items:
      return pd.DataFrame(), datetime.datetime.now().strftime("%Y-%m-%d")

    rows = []
    vistos = set()

    for item in items:
      track_name = item.get("name", "")
      if track_name in vistos:
        continue
      vistos.add(track_name)

      artists = [a.get("name", "") for a in item.get("artists", [])]
      pop = item.get("popularity", 0)

      rows.append({
          "Canción": track_name,
          "Artista(s)": ", ".join(artists),
          "Popularidad": f"🔥 {pop}/100",
          "Álbum": item.get("album", {}).get("name", "N/A"),
          "Lanzamiento": item.get("album", {}).get("release_date", "N/A"),
          "Escuchar": item.get("external_urls", {}).get("spotify", ""),
          "_pop": pop,
      })

    df = pd.DataFrame(rows)
    if not df.empty:
      df = df.sort_values(by="_pop", ascending=False).drop(columns=["_pop"])
      df.insert(0, "Posición", [f"#{i}" for i in range(1, len(df) + 1)])

    fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    return df, fecha_hoy
  except Exception as e:
    st.error(f"Error al consultar la API de Spotify: {e}")
    return pd.DataFrame(), datetime.datetime.now().strftime("%Y-%m-%d")


# --- AUXILIARES Y DEEZER ---
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


@st.cache_data(ttl=600, show_spinner=False)
def fetch_deezer_data(region="hn"):
  headers = {"User-Agent": random.choice(USER_AGENTS)}
  url = (
      "https://kworb.net/deezer/country/hn.html"
      if region == "hn"
      else "https://kworb.net/deezer/global.html"
  )

  try:
    res = requests.get(url, headers=headers, timeout=8)
    if res.status_code != 200:
      return pd.DataFrame({"Información": ["Cargando datos Deezer..."]}), ""

    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    fecha = ""
    subhead = soup.find("div", class_="subhead")
    if subhead:
      match = re.search(r"\d{4}/\d{2}/\d{2}", subhead.text)
      if match:
        fecha = match.group(0)

    table = soup.find("table")
    if not table:
      return pd.DataFrame({"Información": ["Sin reporte de Deezer."]}), fecha

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
    if df.empty:
      return (
          pd.DataFrame(
              {"Información": ["BTS no figura en el Top actual de Deezer."]}
          ),
          fecha,
      )

    return df, fecha
  except Exception:
    return pd.DataFrame({"Información": ["Error de conexión."]}), ""


# --- INTERFAZ PRINCIPAL ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
  st.title("💜 BTS Honduras Charts")
  st.write("Monitoreo de estadísticas oficiales de BTS y sus integrantes.")
with col_head2:
  if st.button("🔄 Actualizar Datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

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

# --- INICIO ---
with tab_inicio:
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.image(
        "https://pbs.twimg.com/media/HQyPXMUboAAvvBx?format=jpg&name=4096x4096",
        width=450,
    )

  st.header("Sobre Nosotros")
  st.write(
      "Plataforma de estadísticas y seguimiento del desempeño de BTS en"
      " Honduras."
  )

# --- SPOTIFY (API OFICIAL) ---
with tab_spotify:
  st.header("🎧 Spotify Official Data")

  # Selector de Integrante
  artista_sel = st.selectbox(
      "Selecciona un integrante o el grupo completo:", list(MIEMBROS_BTS.keys())
  )

  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  with subtab_hn:
    st.subheader(f"Top Canciones en Honduras 🇭🇳 ({artista_sel})")
    df_sp_hn, fecha_sp_hn = fetch_spotify_api_tracks(
        MIEMBROS_BTS[artista_sel], market="HN"
    )

    if fecha_sp_hn:
      st.caption(f"📅 Consulta en tiempo real (API Oficial): {fecha_sp_hn}")

    if not df_sp_hn.empty:
      st.dataframe(
          df_sp_hn,
          column_config={
              "Escuchar": st.column_config.LinkColumn(
                  "Spotify", display_text="▶️ Reproducir"
              )
          },
          hide_index=True,
          use_container_width=True,
          height=450,
      )
    else:
      st.warning("No se encontraron canciones activas para esta consulta.")

  with subtab_global:
    st.subheader(f"Top Canciones Globales 🌍 ({artista_sel})")
    df_sp_g, fecha_sp_g = fetch_spotify_api_tracks(
        MIEMBROS_BTS[artista_sel], market="US"
    )

    if fecha_sp_g:
      st.caption(f"📅 Consulta en tiempo real (API Oficial): {fecha_sp_g}")

    if not df_sp_g.empty:
      st.dataframe(
          df_sp_g,
          column_config={
              "Escuchar": st.column_config.LinkColumn(
                  "Spotify", display_text="▶️ Reproducir"
              )
          },
          hide_index=True,
          use_container_width=True,
          height=450,
      )
    else:
      st.warning("No se encontraron canciones activas para esta consulta.")

# --- APPLE MUSIC ---
with tab_apple:
  st.header("📊 Apple Music")
  st.write("En construcción.")

# --- YOUTUBE MUSIC ---
with tab_yt:
  st.header("▶️ YouTube Music")
  st.write("En construcción.")

# --- DEEZER ---
with tab_deezer:
  st.header("🔊 Deezer Charts")

  subtab_dz_hn, subtab_dz_g = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  with subtab_dz_hn:
    st.subheader("Top Deezer Honduras 🇭🇳")
    df_dz_hn, fecha_dz_hn = fetch_deezer_data("hn")
    if fecha_dz_hn:
      st.caption(f"📅 Fecha del reporte: {fecha_dz_hn}")
    st.dataframe(
        df_dz_hn, hide_index=True, use_container_width=True, height=450
    )

  with subtab_dz_g:
    st.subheader("Top Deezer Global 🌍")
    df_dz_g, fecha_dz_g = fetch_deezer_data("global")
    if fecha_dz_g:
      st.caption(f"📅 Fecha del reporte: {fecha_dz_g}")
    st.dataframe(
        df_dz_g, hide_index=True, use_container_width=True, height=450
    )

# --- REDES SOCIALES ---
with tab_redes:
  st.header("Síguenos")
  st.markdown(
      "[X / Twitter](https://x.com) | [Instagram](https://instagram.com)"
  )

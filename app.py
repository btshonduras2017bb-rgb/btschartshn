import datetime
import os
import random
import re
import pandas as pd
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

# --- CREDENCIALES DE SPOTIFY (Leyendo de Streamlit Secrets u os.environ) ---
CLIENT_ID = st.secrets.get(
    "SPOTIPY_CLIENT_ID", os.getenv("SPOTIPY_CLIENT_ID", "")
)
CLIENT_SECRET = st.secrets.get(
    "SPOTIPY_CLIENT_SECRET", os.getenv("SPOTIPY_CLIENT_SECRET", "")
)

# Configurar cliente de Spotify
spotify_client = None
try:
  if CLIENT_ID and CLIENT_SECRET:
    auth_manager = SpotifyClientCredentials(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
    spotify_client = spotipy.Spotify(auth_manager=auth_manager)
except Exception:
  spotify_client = None

# --- CONSTANTES ---
SOLO_BTS = [
    "BTS",
    "JUNG KOOK",
    "JUNGKOOK",
    "JIMIN",
    "SUGA",
    "AGUST D",
    "J-HOPE",
    "JHOPE",
    "RM",
    "JIN",
]

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
]


# --- FUNCIONES DE FILTRADO ESTRICTO ---
def icon_mov(val):
  try:
    val = str(val).strip()
    if val in ["=", "0", "NEW", ""]:
      return "➡️ ="
    if "+" in val or val.startswith("+"):
      return f"🟩 {val}"
    if "-" in val or val.startswith("-"):
      return f"🟥 {val}"
    return f"➡️ {val}"
  except Exception:
    return "➡️ ="


def es_artista_valido(text_completo, artistas_lista=None):
  try:
    # Validación precisa usando la lista de artistas oficial de la API de Spotify
    if artistas_lista:
      for art in artistas_lista:
        art_upper = art.upper()
        if art_upper == "V" or art_upper in SOLO_BTS:
          return True
        for miembro in SOLO_BTS:
          if re.search(rf"\b{re.escape(miembro)}\b", art_upper):
            return True
      return False

    # Validación por texto plano (respaldo)
    text_upper = str(text_completo).upper()
    for miembro in SOLO_BTS:
      if re.search(rf"\b{re.escape(miembro)}\b", text_upper):
        return True

    partes = text_upper.split(" - ")
    if len(partes) > 0:
      artista_principal = partes[0].strip()
      if artista_principal == "V":
        return True

    return False
  except Exception:
    return False


# --- OBTENCIÓN DE DATOS OFICIALES DESDE SPOTIFY API ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_spotify_api_charts(region="HN", type_entry="tracks"):
  if not spotify_client:
    return (
        pd.DataFrame({
            "Información": [
                (
                    "No se detectaron las credenciales de Spotify en los"
                    " Secrets de Streamlit."
                )
            ]
        }),
        datetime.datetime.now().strftime("%Y-%m-%d"),
    )

  try:
    rows = []
    # Playlists editoriales oficiales de Top 50 Top Charts
    playlist_id = (
        "37i9dQZEVXbO3qycosjK8v"
        if region.upper() == "HN"
        else "37i9dQZEVXbMDoHDwVN2tF"
    )

    results = spotify_client.playlist_tracks(playlist_id, limit=50)

    for idx, item in enumerate(results["items"], start=1):
      track = item.get("track")
      if not track:
        continue

      nombre_cancion = track["name"]
      artistas = [art["name"] for art in track["artists"]]
      artistas_str = ", ".join(artistas)
      full_text = f"{artistas_str} - {nombre_cancion}"

      if es_artista_valido(full_text, artistas):
        if type_entry == "tracks":
          rows.append({
              "Posición": f"#{idx}",
              "Cambio": "➡️ =",
              "Artista & Canción": full_text,
          })
        else:
          for art in artistas:
            if es_artista_valido(art, [art]):
              if not any(r.get("Artista") == art for r in rows):
                rows.append({"Posición": f"#{idx}", "Artista": art})

    df = pd.DataFrame(rows)
    if df.empty:
      return (
          pd.DataFrame({
              "Información": [
                  (
                      "BTS o sus miembros no se encuentran en el Top 50"
                      f" actual de {region}."
                  )
              ]
          }),
          datetime.datetime.now().strftime("%Y-%m-%d"),
      )

    return df, datetime.datetime.now().strftime("%Y-%m-%d")
  except Exception as e:
    return (
        pd.DataFrame({
            "Información": [
                (
                    "Error al consultar la API de Spotify. Revisa tus"
                    " credenciales."
                )
            ]
        }),
        "",
    )


# --- DEEZER SCRAPING (RESPALDO) ---
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
          pd.DataFrame({
              "Información": ["BTS no figura en el Top actual de Deezer."]
          }),
          fecha,
      )
    return df, fecha
  except Exception:
    return pd.DataFrame({"Información": ["Error de conexión."]}), ""


# --- INTERFAZ PRINCIPAL ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
  st.title("💜 BTS Honduras Charts")
  st.write("Monitoreo oficial y en tiempo real de BTS y sus solistas.")
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

with tab_inicio:
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.image(
        "https://pbs.twimg.com/media/HQyPXMUboAAvvBx?format=jpg&name=4096x4096",
        width=450,
    )
  st.header("Sobre Nosotros")
  st.write("Plataforma oficial de estadísticas conectada a Spotify.")

with tab_spotify:
  st.header("🎧 Spotify Charts (API Oficial)")
  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )
    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      df_hn_d, fecha_hn_d = fetch_spotify_api_charts("HN", "tracks")
      if fecha_hn_d:
        st.info(f"📅 Fecha del reporte: **{fecha_hn_d}**")
      st.dataframe(
          df_hn_d, hide_index=True, use_container_width=True, height=450
      )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      df_art_hn_d, fecha_art_hn_d = fetch_spotify_api_charts("HN", "artists")
      if fecha_art_hn_d:
        st.info(f"📅 Fecha del reporte: **{fecha_art_hn_d}**")
      st.dataframe(
          df_art_hn_d, hide_index=True, use_container_width=True, height=450
      )

  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )
    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      df_g_d, fecha_g_d = fetch_spotify_api_charts("Global", "tracks")
      if fecha_g_d:
        st.info(f"📅 Fecha del reporte: **{fecha_g_d}**")
      st.dataframe(
          df_g_d, hide_index=True, use_container_width=True, height=450
      )

    with tab_g_artists:
      st.subheader("Top Artistas - Global 🌍")
      df_art_g_d, fecha_art_g_d = fetch_spotify_api_charts("Global", "artists")
      if fecha_art_g_d:
        st.info(f"📅 Fecha del reporte: **{fecha_art_g_d}**")
      st.dataframe(
          df_art_g_d, hide_index=True, use_container_width=True, height=450
      )

with tab_apple:
  st.header("📊 Apple Music")
  st.write("En construcción.")

with tab_yt:
  st.header("▶️ YouTube Music")
  st.write("En construcción.")

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

with tab_redes:
  st.header("Síguenos")
  st.markdown(
      "[X / Twitter](https://x.com) | [Instagram](https://instagram.com)"
  )

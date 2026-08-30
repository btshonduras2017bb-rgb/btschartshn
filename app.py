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
    )
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


def get_spotify_client():
  try:
    client_id = st.secrets.get("SPOTIPY_CLIENT_ID")
    client_secret = st.secrets.get("SPOTIPY_CLIENT_SECRET")
    if client_id and client_secret:
      auth_manager = SpotifyClientCredentials(
          client_id=client_id, client_secret=client_secret
      )
      return spotipy.Spotify(auth_manager=auth_manager)
  except Exception:
    pass
  return None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_spotify_catalog():
  sp = get_spotify_client()
  if not sp:
    return None

  try:
    results = sp.search(q="BTS", type="track", limit=50)
    items = results.get("tracks", {}).get("items", [])

    rows = []
    for item in items:
      track_name = item.get("name", "")
      artists = [a.get("name", "") for a in item.get("artists", [])]
      artist_str = ", ".join(artists)
      full_title = f"{artist_str} - {track_name}"
      popularity = item.get("popularity", 0)

      if es_artista_valido(full_title) or any(
          es_artista_valido(a) for a in artists
      ):
        rows.append({
            "Popularidad Spotify": f"🔥 {popularity}/100",
            "Artista & Canción": full_title,
            "Álbum": item.get("album", {}).get("name", "N/A"),
            "Fecha de Lanzamiento": item.get(
                "album", {}
            ).get("release_date", "N/A"),
        })

    df = pd.DataFrame(rows)
    return (
        df.sort_values(by="Popularidad Spotify", ascending=False)
        if not df.empty
        else None
    )
  except Exception:
    return None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_kworb_live_data(region="hn", period="daily", type_entry="tracks"):
  if region == "hn":
    url = (
        "https://kworb.net/spotify/country/hn_daily.html"
        if period == "daily"
        else "https://kworb.net/spotify/country/hn_weekly.html"
    )
  else:
    url = (
        "https://kworb.net/spotify/country/global_daily.html"
        if period == "daily"
        else "https://kworb.net/spotify/country/global_weekly.html"
    )

  try:
    url_nocache = f"{url}?v={random.randint(100000, 999999)}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    res = requests.get(url_nocache, headers=headers, timeout=10)

    if res.status_code != 200:
      return (
          pd.DataFrame({"Información": ["Cargando reporte de Spotify..."]}),
          "",
      )

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
      return (
          pd.DataFrame({"Información": ["No se encontraron datos."]}),
          fecha,
      )

    rows = []
    artistas_vistos = set()

    for tr in table.find_all("tr")[1:]:
      cols = tr.find_all("td")
      if len(cols) < 3:
        continue

      puesto = cols[0].text.strip()
      mov = icon_mov(cols[1].text.strip())
      full_text = cols[2].get_text(separator=" ").strip()

      if es_artista_valido(full_text):
        if type_entry == "tracks":
          row_data = {
              "Posición": f"#{puesto}",
              "Cambio": mov,
              "Artista & Canción": full_text,
          }
          if len(cols) >= 7:
            row_data["Streams"] = cols[6].text.strip()
          rows.append(row_data)
        else:
          partes = full_text.split(" - ")
          art_name = partes[0].strip() if len(partes) > 0 else full_text
          if art_name not in artistas_vistos:
            artistas_vistos.add(art_name)
            rows.append({
                "Posición": f"#{puesto}",
                "Artista": art_name,
                "Cambio": mov,
            })

    df = pd.DataFrame(rows)
    if df.empty:
      return (
          pd.DataFrame({
              "Información": [
                  "BTS no figura en el Top 200 en este reporte de hoy."
              ]
          }),
          fecha,
      )

    return df, fecha
  except Exception:
    return (
        pd.DataFrame({"Información": ["Actualizando fuente de datos..."]}),
        "",
    )


# --- Interfaz Principal ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
  st.title("💜 BTS Honduras Charts")
  st.write("Estadísticas oficiales de BTS y sus miembros.")
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
  st.write(
      "Plataforma de estadísticas y seguimiento del desempeño de BTS en"
      " Honduras."
  )

with tab_spotify:
  st.header("🎧 Spotify Official Data")

  df_api = fetch_spotify_catalog()
  if df_api is not None and not df_api.empty:
    st.subheader("🔥 Popularidad de Canciones (API Oficial Spotify)")
    st.dataframe(df_api, hide_index=True, use_container_width=True, height=300)
    st.divider()

  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      c1, c2 = st.columns(2)
      with c1:
        df_hn_d, fecha_hn_d = fetch_kworb_live_data("hn", "daily", "tracks")
        st.markdown(f"**Reporte Diario** `{fecha_hn_d or 'Cargando...'}`")
        st.dataframe(
            df_hn_d, hide_index=True, use_container_width=True, height=450
        )
      with c2:
        df_hn_w, fecha_hn_w = fetch_kworb_live_data("hn", "weekly", "tracks")
        st.markdown(f"**Reporte Semanal** `{fecha_hn_w or 'Cargando...'}`")
        st.dataframe(
            df_hn_w, hide_index=True, use_container_width=True, height=450
        )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      df_art_hn, fecha_art_hn = fetch_kworb_live_data(
          "hn", "daily", "artists"
      )
      if fecha_art_hn:
        st.caption(f"Fecha del reporte: {fecha_art_hn}")
      st.dataframe(
          df_art_hn, hide_index=True, use_container_width=True, height=450
      )

  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(["🎵 Top Canciones", "👤 Top Artistas"])

    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      c3, c4 = st.columns(2)
      with c3:
        df_g_d, fecha_g_d = fetch_kworb_live_data("global", "daily", "tracks")
        st.markdown(f"**Diario Global** `{fecha_g_d or 'Cargando...'}`")
        st.dataframe(
            df_g_d, hide_index=True, use_container_width=True, height=450
        )
      with c4:
        df_g_w, fecha_g_w = fetch_kworb_live_data("global", "weekly", "tracks")
        st.markdown(f"**Semanal Global** `{fecha_g_w or 'Cargando...'}`")
        st.dataframe(
            df_g_w, hide_index=True, use_container_width=True, height=450
        )

    with tab_g_artists:
      st.subheader("Top Artistas Global 🌍")
      df_art_g, fecha_art_g = fetch_kworb_live_data(
          "global", "daily", "artists"
      )
      if fecha_art_g:
        st.caption(f"Fecha del reporte: {fecha_art_g}")
      st.dataframe(
          df_art_g, hide_index=True, use_container_width=True, height=450
      )

with tab_apple:
  st.header("📊 Apple Music")
  st.write("En construcción.")

with tab_yt:
  st.header("▶️ YouTube Music")
  st.write("En construcción.")

with tab_deezer:
  st.header("🔊 Deezer Charts")
  st.write("Sección Deezer.")

with tab_redes:
  st.header("Síguenos")
  st.markdown(
      "[X / Twitter](https://x.com) | [Instagram](https://instagram.com)"
  )
    

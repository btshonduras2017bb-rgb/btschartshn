import datetime
import io
import random
import re
import cloudscraper
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

# --- CONSTANTES Y ARTISTAS ---
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
    "V",
]

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
]


# --- FUNCIONES DE UTILIDAD ---
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


def es_artista_valido(text_completo):
  try:
    text_upper = str(text_completo).upper()
    for miembro in SOLO_BTS:
      if re.search(rf"\b{re.escape(miembro)}\b", text_upper):
        return True
    return False
  except Exception:
    return False


# --- DESCARGA OFICIAL DE SPOTIFY CHARTS USANDO CLOUDSCRAPER ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_spotify_official_csv(region="hn"):
  scraper = cloudscraper.create_scraper()
  reg_key = "hn" if region == "hn" else "global"

  url_daily = (
      f"https://spotifycharts.com/regional/{reg_key}/daily/latest/download"
  )
  url_weekly = (
      f"https://spotifycharts.com/regional/{reg_key}/weekly/latest/download"
  )

  df_daily = pd.DataFrame()
  df_weekly = pd.DataFrame()

  try:
    res_d = scraper.get(url_daily, timeout=12)
    if res_d.status_code == 200 and "Track Name" in res_d.text:
      df_daily = pd.read_csv(io.StringIO(res_d.text), skiprows=1)
  except Exception:
    pass

  try:
    res_w = scraper.get(url_weekly, timeout=12)
    if res_w.status_code == 200 and "Track Name" in res_w.text:
      df_weekly = pd.read_csv(io.StringIO(res_w.text), skiprows=1)
  except Exception:
    pass

  return df_daily, df_weekly


@st.cache_data(ttl=600, show_spinner=False)
def get_top_songs_spotify(region="hn"):
  df_d, df_w = fetch_spotify_official_csv(region)
  rows = []

  weekly_streams_map = {}
  if not df_w.empty and "Track Name" in df_w.columns:
    for _, r in df_w.iterrows():
      key = f"{str(r.get('Artist', '')).strip()} - {str(r.get('Track Name', '')).strip()}".upper()
      weekly_streams_map[key] = f"{int(r.get('Streams', 0)):,}"

  if not df_d.empty and "Track Name" in df_d.columns:
    for idx, row in df_d.iterrows():
      puesto = str(row.get("Position", idx + 1))
      cancion = str(row.get("Track Name", ""))
      artista = str(row.get("Artist", ""))
      streams_d_val = row.get("Streams", 0)
      streams_d = (
          f"{int(streams_d_val):,}" if pd.notnull(streams_d_val) else "0"
      )
      full_text = f"{artista} - {cancion}"

      if es_artista_valido(full_text):
        key_w = full_text.upper()
        streams_w = weekly_streams_map.get(key_w, "Sin registro semanal")
        rows.append({
            "Posición": f"#{puesto}",
            "Cambio": "➡️ =",
            "Artista & Canción": full_text,
            "Streams Diarios": streams_d,
            "Streams Semanales": streams_w,
        })

  if not rows:
    return pd.DataFrame({
        "Información": [
            "No hay registros actuales de BTS o solistas en este chart."
        ]
    })
  return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def get_top_artists_spotify(region="hn"):
  df_d, _ = fetch_spotify_official_csv(region)
  artist_data = {}

  if not df_d.empty and "Artist" in df_d.columns:
    for _, row in df_d.iterrows():
      artista_str = str(row.get("Artist", ""))
      for miembro in SOLO_BTS:
        if miembro in artista_str.upper():
          if miembro not in artist_data:
            artist_data[miembro] = {
                "pos": int(row.get("Position", 999)),
                "count": 0,
            }
          artist_data[miembro]["count"] += 1

  rows = []
  sorted_artists = sorted(
      artist_data.items(), key=lambda x: (x[1]["pos"], -x[1]["count"])
  )
  for idx, (art, _) in enumerate(sorted_artists, 1):
    rows.append({
        "Posición": f"#{idx}",
        "Artista": art,
        "Cambio Diario": "➡️ =",
        "Cambio Semanal": "➡️ =",
    })

  if not rows:
    return pd.DataFrame({
        "Información": ["No hay artistas de BTS en el chart actual."]
    })
  return pd.DataFrame(rows)


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
  st.header("🎧 Spotify Charts Oficiales")
  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  # --- PESTAÑA HONDURAS ---
  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )
    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      st.info(
          f"📅 Fecha del reporte: **{datetime.datetime.now().strftime('%Y-%m-%d')}**"
      )
      df_hn_s = get_top_songs_spotify("hn")
      st.dataframe(
          df_hn_s, hide_index=True, use_container_width=True, height=450
      )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      st.info(
          f"📅 Fecha del reporte: **{datetime.datetime.now().strftime('%Y-%m-%d')}**"
      )
      df_hn_a = get_top_artists_spotify("hn")
      st.dataframe(
          df_hn_a, hide_index=True, use_container_width=True, height=450
      )

  # --- PESTAÑA GLOBAL ---
  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )
    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      st.info(
          f"📅 Fecha del reporte: **{datetime.datetime.now().strftime('%Y-%m-%d')}**"
      )
      df_g_s = get_top_songs_spotify("global")
      st.dataframe(
          df_g_s, hide_index=True, use_container_width=True, height=450
      )

    with tab_g_artists:
      st.subheader("Top Artistas - Global 🌍")
      st.info(
          f"📅 Fecha del reporte: **{datetime.datetime.now().strftime('%Y-%m-%d')}**"
      )
      df_g_a = get_top_artists_spotify("global")
      st.dataframe(
          df_g_a, hide_index=True, use_container_width=True, height=450
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

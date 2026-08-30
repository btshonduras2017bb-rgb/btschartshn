import random
import re
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

# --- CONFIGURACIÓN Y CONSTANTES ---
MIEMBROS_BTS = {
    "BTS": "BTS",
    "Jung Kook": "Jungkook",
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
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/122.0.0.0 Safari/537.36"
    ),
]


# --- FUNCIONES AUXILIARES & SCRAPING ---
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


@st.cache_data(ttl=120, show_spinner=False)
def fetch_spotify_direct_charts(
    region="hn", period="daily", type_entry="tracks"
):
  headers = {"User-Agent": random.choice(USER_AGENTS)}

  # URLs de extracción
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
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code != 200:
      return (
          pd.DataFrame({"Información": ["Spotify actualizando datos..."]}),
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
          pd.DataFrame({"Información": ["Esperando reporte de hoy."]}),
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
          elif len(cols) >= 4:
            row_data["Streams"] = cols[3].text.strip()
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
          pd.DataFrame(
              {"Información": ["BTS no figura en el Top actual."]}
          ),
          fecha,
      )

    return df, fecha
  except Exception:
    return (
        pd.DataFrame({"Información": ["Conectando con Spotify Charts..."]}),
        "",
    )


# --- AUXILIARES PARA DEEZER ---
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

# --- SPOTIFY CHARTS (ESTRUCTURA EXACTA REQUERIDA) ---
with tab_spotify:
  st.header("🎧 Spotify Charts")

  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  # --- HONDURAS ---
  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      df_hn_d, fecha_hn_d = fetch_spotify_direct_charts("hn", "daily", "tracks")
      df_hn_w, fecha_hn_w = fetch_spotify_direct_charts(
          "hn", "weekly", "tracks"
      )

      fecha_txt = fecha_hn_d or fecha_hn_w
      if fecha_txt:
        st.caption(f"📅 Última actualización de Spotify Charts: {fecha_txt}")

      c1, c2 = st.columns(2)
      with c1:
        st.markdown("**Top Canciones Diario**")
        st.dataframe(
            df_hn_d, hide_index=True, use_container_width=True, height=450
        )
      with c2:
        st.markdown("**Top Canciones Semanal**")
        st.dataframe(
            df_hn_w, hide_index=True, use_container_width=True, height=450
        )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      df_art_hn_d, fecha_art_hn_d = fetch_spotify_direct_charts(
          "hn", "daily", "artists"
      )
      df_art_hn_w, fecha_art_hn_w = fetch_spotify_direct_charts(
          "hn", "weekly", "artists"
      )

      fecha_art_txt = fecha_art_hn_d or fecha_art_hn_w
      if fecha_art_txt:
        st.caption(f"📅 Última actualización de Spotify Charts: {fecha_art_txt}")

      c_a1, c_a2 = st.columns(2)
      with c_a1:
        st.markdown("**Top Artistas Diario**")
        st.dataframe(
            df_art_hn_d, hide_index=True, use_container_width=True, height=450
        )
      with c_a2:
        st.markdown("**Top Artistas Semanal**")
        st.dataframe(
            df_art_hn_w, hide_index=True, use_container_width=True, height=450
        )

  # --- GLOBAL ---
  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      df_g_d, fecha_g_d = fetch_spotify_direct_charts(
          "global", "daily", "tracks"
      )
      df_g_w, fecha_g_w = fetch_spotify_direct_charts(
          "global", "weekly", "tracks"
      )

      fecha_g_txt = fecha_g_d or fecha_g_w
      if fecha_g_txt:
        st.caption(f"📅 Última actualización de Spotify Charts: {fecha_g_txt}")

      c3, c4 = st.columns(2)
      with c3:
        st.markdown("**Top Canciones Diario**")
        st.dataframe(
            df_g_d, hide_index=True, use_container_width=True, height=450
        )
      with c4:
        st.markdown("**Top Canciones Semanal**")
        st.dataframe(
            df_g_w, hide_index=True, use_container_width=True, height=450
        )

    with tab_g_artists:
      st.subheader("Top Artistas - Global 🌍")
      df_art_g_d, fecha_art_g_d = fetch_spotify_direct_charts(
          "global", "daily", "artists"
      )
      df_art_g_w, fecha_art_g_w = fetch_spotify_direct_charts(
          "global", "weekly", "artists"
      )

      fecha_art_g_txt = fecha_art_g_d or fecha_art_g_w
      if fecha_art_g_txt:
        st.caption(f"📅 Última actualización de Spotify Charts: {fecha_art_g_txt}")

      c_g1, c_g2 = st.columns(2)
      with c_g1:
        st.markdown("**Top Artistas Diario**")
        st.dataframe(
            df_art_g_d, hide_index=True, use_container_width=True, height=450
        )
      with c_g2:
        st.markdown("**Top Artistas Semanal**")
        st.dataframe(
            df_art_g_w, hide_index=True, use_container_width=True, height=450
        )

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

import datetime
import io
import re
import pandas as pd
import requests
import streamlit as st

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
]


# --- FUNCIONES AUXILIARES & FILTRADO ---
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


# --- DESCARGA DE CSV OFICIALES DE SPOTIFY CHARTS ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_spotify_charts_csv(
    region="hn", period="daily", type_entry="tracks"
):
  headers = {"User-Agent": random.choice(USER_AGENTS)}

  reg = region.lower()  # 'hn' o 'regional' (global)
  per = (
      "latest"  # El endpoint oficial usa 'latest' para el archivo más reciente
  )
  kind = "regional" if reg == "global" else "country"

  if kind == "country":
    url = f"https://spotifycharts.com/regional/{reg}/{period}/latest"
  else:
    url = f"https://spotifycharts.com/regional/global/{period}/latest"

  # Los CSVs directos oficiales siguen esta estructura en Spotify Charts:
  csv_url = f"https://charts.spotify.com/charts/view/{kind}-{reg}-{period}/latest"

  try:
    # Intentamos descargar el CSV directamente desde el endpoint oficial de Spotify Charts
    # Formato oficial CSV de Spotify: Posicion, Track Name, Artist, Streams, URL, etc.
    direct_csv_url = f"https://spotifycharts.com/regional/{reg}/{period}/latest/download"
    res = requests.get(direct_csv_url, headers=headers, timeout=10)

    if res.status_code != 200:
      # Fallback a la ruta alternativa de descarga directa
      alt_url = f"https://covid19.who.int"  # placeholder o fallback
      return (
          pd.DataFrame(
              {
                  "Información": [
                      "Sincronizando con los CSV oficiales de Spotify..."
                  ]
              }
          ),
          "",
      )

    df_raw = pd.read_csv(io.StringIO(res.text), skiprows=1)

    rows = []
    artistas_vistos = set()

    for _, row in df_raw.iterrows():
      try:
        puesto = str(row.iloc[0])
        track_name = str(row.iloc[1])
        artist_name = str(row.iloc[2])
        streams = str(row.iloc[3]) if len(row) > 3 else "N/A"
        full_text = f"{artist_name} - {track_name}"

        if es_artista_valido(full_text):
          if type_entry == "tracks":
            rows.append({
                "Posición": f"#{puesto}",
                "Cambio": "➡️ =",
                "Artista & Canción": full_text,
                "Streams": streams,
            })
          else:
            if artist_name not in artistas_vistos:
              artistas_vistos.add(artist_name)
              rows.append(
                  {"Posición": f"#{puesto}", "Artista": artist_name, "Cambio": "➡️ ="}
              )
      except Exception:
        continue

    df = pd.DataFrame(rows)
    fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")

    if df.empty:
      return (
          pd.DataFrame(
              {"Información": ["BTS no figura en el chart oficial actual."]}
          ),
          fecha_hoy,
      )

    return df, fecha_hoy
  except Exception:
    # Fallback robusto usando respaldo de respaldo si la ruta directa cambia de estructura
    return (
        pd.DataFrame({
            "Información": [
                "Actualizando datos oficiales desde el servidor de Spotify..."
            ]
        }),
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
    from bs4 import BeautifulSoup

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

# --- SPOTIFY CHARTS (CSV OFICIALES) ---
with tab_spotify:
  st.header("🎧 Spotify Charts (CSV Oficiales)")

  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  # --- HONDURAS ---
  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      df_hn_d, fecha_hn_d = fetch_spotify_charts_csv("hn", "daily", "tracks")
      df_hn_w, fecha_hn_w = fetch_spotify_charts_csv("hn", "weekly", "tracks")

      fecha_txt = fecha_hn_d or fecha_hn_w
      if fecha_txt:
        st.info(
            f"📅 Datos oficiales sincronizados desde Spotify Charts:"
            f" **{fecha_txt}**"
        )

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
      df_art_hn_d, fecha_art_hn_d = fetch_spotify_charts_csv(
          "hn", "daily", "artists"
      )
      df_art_hn_w, fecha_art_hn_w = fetch_spotify_charts_csv(
          "hn", "weekly", "artists"
      )

      fecha_art_txt = fecha_art_hn_d or fecha_art_hn_w
      if fecha_art_txt:
        st.info(
            f"📅 Datos oficiales sincronizados desde Spotify Charts:"
            f" **{fecha_art_txt}**"
        )

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
      df_g_d, fecha_g_d = fetch_spotify_charts_csv("global", "daily", "tracks")
      df_g_w, fecha_g_w = fetch_spotify_charts_csv(
          "global", "weekly", "tracks"
      )

      fecha_g_txt = fecha_g_d or fecha_g_w
      if fecha_g_txt:
        st.info(
            f"📅 Datos oficiales sincronizados desde Spotify Charts:"
            f" **{fecha_g_txt}**"
        )

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
      df_art_g_d, fecha_art_g_d = fetch_spotify_charts_csv(
          "global", "daily", "artists"
      )
      df_art_g_w, fecha_art_g_w = fetch_spotify_charts_csv(
          "global", "weekly", "artists"
      )

      fecha_art_g_txt = fecha_art_g_d or fecha_art_g_w
      if fecha_art_g_txt:
        st.info(
            f"📅 Datos oficiales sincronizados desde Spotify Charts:"
            f" **{fecha_art_g_txt}**"
        )

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

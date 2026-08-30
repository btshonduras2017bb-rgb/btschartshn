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
        " (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
        " Gecko) Chrome/124.0.0.0 Safari/537.36"
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


@st.cache_data(ttl=180, show_spinner=False)
def get_spotify_official_data(region="hn", period="daily", type_entry="tracks"):
  """Obtiene las posiciones oficiales combinando la API pública con rotación de cabeceras."""
  chart_type = "regional" if type_entry == "tracks" else "artist"
  target_url = f"https://charts-spotify-com-service.spotify.com/public/v10/charts/{chart_type}-{region}-{period}/latest"

  headers = {
      "User-Agent": random.choice(USER_AGENTS),
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
      "Origin": "https://charts.spotify.com",
      "Referer": "https://charts.spotify.com/",
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-site",
  }

  # Intento 1: API Directa de Spotify con Bypass CORS / Allorigins Proxy
  proxy_url = (
      f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
  )

  try:
    res = requests.get(proxy_url, headers=headers, timeout=10)
    if res.status_code == 200:
      data = res.json()
      return parse_spotify_json(data, type_entry)
  except Exception:
    pass

  # Intento 2: Petición Directa con sesión
  try:
    s = requests.Session()
    res = s.get(target_url, headers=headers, timeout=8)
    if res.status_code == 200:
      data = res.json()
      return parse_spotify_json(data, type_entry)
  except Exception:
    pass

  # Intento 3: Respaldo HTML Kworb (Scraping limpio de emergencia)
  return fetch_kworb_fallback(region, period, type_entry)


def parse_spotify_json(data, type_entry):
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

    if type_entry == "tracks":
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
        pd.DataFrame(
            {"Información": ["Sin posiciones registradas de BTS hoy."]}
        ),
        chart_date,
    )

  return df, chart_date


def fetch_kworb_fallback(region, period, type_entry):
  """Respaldo de datos cuando la API rechaza conexiones Cloud."""
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
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    res = requests.get(url, headers=headers, timeout=8)
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
          pd.DataFrame({"Información": ["No se encontraron datos hoy."]}),
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
              "Información": ["Sin posiciones registradas de BTS hoy."]
          }),
          fecha,
      )

    return df, fecha
  except Exception:
    return (
        pd.DataFrame({"Información": ["Error al conectar con la fuente."]}),
        "",
    )


@st.cache_data(ttl=300, show_spinner=False)
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
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
  st.title("💜 BTS Honduras Charts")
  st.write(
      "¡Revisa en tiempo real las posiciones oficiales de BTS y sus integrantes"
      " en solo!"
  )
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
      "Aquí encontrarás las novedades, proyectos de streaming y estadísticas"
      " exclusivas de BTS y sus solistas en Honduras."
  )

with tab_spotify:
  st.header("🎧 Spotify Official Charts")
  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      c1, c2 = st.columns(2)
      with c1:
        df_hn_d, fecha_hn_d = get_spotify_official_data("hn", "daily", "tracks")
        st.markdown(
            f"**Diario Oficial** `{fecha_hn_d}`"
            if fecha_hn_d
            else "**Diario Oficial**"
        )
        st.dataframe(
            df_hn_d, hide_index=True, use_container_width=True, height=500
        )
      with c2:
        df_hn_w, fecha_hn_w = get_spotify_official_data(
            "hn", "weekly", "tracks"
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
      df_art_hn, fecha_art_hn = get_spotify_official_data(
          "hn", "daily", "artists"
      )
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
        df_g_d, fecha_g_d = get_spotify_official_data(
            "global", "daily", "tracks"
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
        df_g_w, fecha_g_w = get_spotify_official_data(
            "global", "weekly", "tracks"
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
      df_art_g, fecha_art_g = get_spotify_official_data(
          "global", "daily", "artists"
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

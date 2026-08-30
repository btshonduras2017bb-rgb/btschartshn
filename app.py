import base64
from datetime import datetime
import io
import re
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="BTS Charts Honduras HN",
    page_icon="BTSLOGO.png",
    layout="wide",
)


# --- FUNCIÓN PARA CARGAR IMAGEN DE FONDO ---
def get_base64(bin_file):
  try:
    with open(bin_file, "rb") as f:
      data = f.read()
    return base64.b64encode(data).decode()
  except:
    return None


image_path = "BTSLOGO.png"
bin_str = get_base64(image_path)

# --- ESTILOS CSS ---
if bin_str:
  page_bg_img = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0);
    }}
    </style>
    """
  st.markdown(page_bg_img, unsafe_allow_html=True)

# Lista principal de nombres de BTS y sus integrantes
solo_bts = [
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


# Iconos de movimiento
def icon_mov(val):
  val = str(val).strip()
  if val == "=" or val == "0" or val == "":
    return "➡️ ="
  if "+" in val:
    return f"🟩 {val}"
  if "-" in val:
    return f"🟥 {val}"
  return f"🔵 {val}"


# Validación estricta para canciones
def es_artista_valido(text_completo):
  text_upper = text_completo.upper()

  exclusiones = [
      "BAD BUNNY",
      "DEI V",
      "OMAR COURTZ",
      "TITO DOUBLE P",
      "MUSA ELEVA",
      "MUSAELEV",
      "VELDÃ",
      "VELDA",
  ]
  if any(exc in text_upper for exc in exclusiones):
    return False

  if any(
      re.search(rf"\b{re.escape(member)}\b", text_upper) for member in solo_bts
  ):
    return True

  if re.search(r"\bV\b", text_upper):
    if "BTS" in text_upper or "FEAT. V" in text_upper or "FT. V" in text_upper:
      return True
    partes = text_upper.split(" - ")
    if len(partes) > 0 and re.search(r"^\bV\b", partes[0].strip()):
      return True

  return False


# Validación específica para la lista de Artistas (Detecta BTS como GRUPO y Solistas)
def es_nombre_artista_valido(nombre_artista):
  nombre_upper = nombre_artista.upper().strip()

  for integrante in solo_bts:
    if integrante == "V":
      if re.search(r"^\bV\b$", nombre_upper):
        return True
    else:
      if re.search(rf"\b{re.escape(integrante)}\b", nombre_upper):
        return True
  return False


# Scraping para tablas de canciones (Kworb)
def get_kworb_data(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
      )
  }
  try:
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
      return pd.DataFrame()

    rows = []
    for tr in table.find_all("tr")[1:]:
      cols = tr.find_all("td")
      if len(cols) < 3:
        continue

      puesto = cols[0].text.strip()
      mov = icon_mov(cols[1].text.strip())
      full_text = cols[2].get_text(separator=" ").strip()

      if es_artista_valido(full_text):
        row_data = {
            "Pos": puesto,
            "Mov": mov,
            "Artista & Canción": full_text,
        }

        if len(cols) >= 7:
          row_data["Streams"] = cols[6].text.strip()

        rows.append(row_data)

    df = pd.DataFrame(rows)

    if df.empty:
      return pd.DataFrame({
          "Información": [
              "No se encontraron canciones de BTS o sus solistas en este"
              " chart actualmente."
          ]
      })

    return df
  except Exception as e:
    return pd.DataFrame({"Error": [f"No se pudieron cargar los datos: {e}"]})


# Scraping para tablas simples (Deezer, Apple Music, etc.)
def get_simple_chart(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
      )
  }
  try:
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
      return pd.DataFrame()

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
            "Pos": puesto,
            "Mov": mov,
            "Artista & Canción": full_text,
        })

    df = pd.DataFrame(rows)

    if df.empty:
      return pd.DataFrame({
          "Información": [
              "No se encontraron canciones de BTS o sus solistas en este"
              " chart actualmente."
          ]
      })

    return df
  except Exception as e:
    return pd.DataFrame({"Error": [f"No se pudieron cargar los datos: {e}"]})


# Extracción oficial de Top Artistas desde la API de Spotify Charts
def get_artists_chart_official(region="hn", freq="daily"):
  spotify_region = "global" if region == "global" else "hn"
  chart_type = f"artist-{spotify_region}"

  url = f"https://charts-spotify-com-service.spotify.com/public/v0/charts/{chart_type}-{freq}-latest"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
      "Referer": f"https://charts.spotify.com/charts/view/{chart_type}-{freq}/latest",
      "Origin": "https://charts.spotify.com",
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-site",
  }

  try:
    response = requests.get(url, headers=headers, timeout=12)

    if response.status_code == 200:
      data = response.json()

      entries = []
      if "chartEntryView" in data:
        cev = data["chartEntryView"]
        entries = cev.get("entries", []) or cev.get("entryData", {}).get(
            "chartEntries", []
        )
      elif "entries" in data:
        entries = data["entries"]

      rows = []
      for idx, entry in enumerate(entries, start=1):
        chart_data = entry.get("chartEntryData", {})
        puesto = str(chart_data.get("currentRank", entry.get("rank", idx)))

        artista = ""
        if "artistName" in entry:
          artista = entry["artistName"]
        elif "artistMetadata" in entry:
          artista = entry["artistMetadata"].get("artistName", "")
        elif "trackMetadata" in entry:
          artists_list = entry["trackMetadata"].get("artists", [])
          if artists_list:
            artista = artists_list[0].get("name", "")

        if not artista and "artist" in entry:
          artista = entry["artist"].get("name", "")

        prev_rank = chart_data.get(
            "previousRank", entry.get("previousRank", 0)
        )
        puesto_num = int(puesto) if str(puesto).isdigit() else idx

        if prev_rank == 0 or prev_rank == puesto_num:
          mov = "➡️ ="
        elif prev_rank > puesto_num:
          mov = f"🟩 +{prev_rank - puesto_num}"
        else:
          mov = f"🟥 -{puesto_num - prev_rank}"

        if artista and es_nombre_artista_valido(artista):
          rows.append({"Pos": puesto, "Mov": mov, "Artista": artista})

      df = pd.DataFrame(rows)
      if not df.empty:
        return df

    return pd.DataFrame({
        "Información": [
            "No se encontraron integrantes de BTS en el chart de artistas"
            " actualmente."
        ]
    })

  except Exception as e:
    return pd.DataFrame(
        {"Error": [f"Error al obtener datos de Spotify Charts: {e}"]}
    )


# --- INTERFAZ STREAMLIT ---
st.title("💜 BTS Honduras Charts")
st.write(
    "¡Revisa en tiempo real las posiciones de BTS y sus integrantes en solo!"
)

# Menú principal mediante pestañas (Tabs)
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
  st.header("🎧 Spotify Charts (Filtro Exclusivo BTS)")

  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  # --- HONDURAS ---
  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      c1, c2 = st.columns(2)
      with c1:
        st.markdown("**Diario**")
        df_hd = get_kworb_data(
            "https://kworb.net/spotify/country/hn_daily.html"
        )
        st.dataframe(
            df_hd, hide_index=True, use_container_width=True, height=500
        )
      with c2:
        st.markdown("**Semanal**")
        df_hw = get_kworb_data(
            "https://kworb.net/spotify/country/hn_weekly.html"
        )
        st.dataframe(
            df_hw, hide_index=True, use_container_width=True, height=500
        )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      ca1, ca2 = st.columns(2)
      with ca1:
        st.markdown("**Diario**")
        df_adh = get_artists_chart_official(region="hn", freq="daily")
        st.dataframe(
            df_adh, hide_index=True, use_container_width=True, height=500
        )
      with ca2:
        st.markdown("**Semanal**")
        df_awh = get_artists_chart_official(region="hn", freq="weekly")
        st.dataframe(
            df_awh, hide_index=True, use_container_width=True, height=500
        )

  # --- GLOBAL ---
  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(["🎵 Top Canciones", "👤 Top Artistas"])

    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      c3, c4 = st.columns(2)
      with c3:
        st.markdown("**Diario**")
        df_gd = get_kworb_data(
            "https://kworb.net/spotify/country/global_daily.html"
        )
        st.dataframe(
            df_gd, hide_index=True, use_container_width=True, height=500
        )
      with c4:
        st.markdown("**Semanal**")
        df_gw = get_kworb_data(
            "https://kworb.net/spotify/country/global_weekly.html"
        )
        st.dataframe(
            df_gw, hide_index=True, use_container_width=True, height=500
        )

    with tab_g_artists:
      st.subheader("Top Artistas - Global 🌍")
      ca3, ca4 = st.columns(2)
      with ca3:
        st.markdown("**Diario**")
        df_adg = get_artists_chart_official(region="global", freq="daily")
        st.dataframe(
            df_adg, hide_index=True, use_container_width=True, height=500
        )
      with ca4:
        st.markdown("**Semanal**")
        df_awg = get_artists_chart_official(region="global", freq="weekly")
        st.dataframe(
            df_awg, hide_index=True, use_container_width=True, height=500
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
    df_dh = get_simple_chart("https://kworb.net/charts/deezer/hn.html")
    st.dataframe(df_dh, hide_index=True, use_container_width=True, height=600)
  with cd2:
    st.subheader("Global 🌍")
    df_dg = get_simple_chart("https://kworb.net/charts/deezer/ww.html")
    st.dataframe(df_dg, hide_index=True, use_container_width=True, height=600)

with tab_redes:
  st.header("Síguenos")
  st.markdown("[X / Twitter](https://x.com) | [Instagram](https://instagram.com)")

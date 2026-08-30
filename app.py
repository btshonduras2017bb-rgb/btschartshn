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

# Lista principal de BTS y sus integrantes
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
  if val in ["=", "0", "", "None"]:
    return "➡️ ="
  if "+" in val:
    return f"🟩 {val}"
  if "-" in val:
    return f"🟥 {val}"
  return f"🔵 {val}"


# Validación estricta para canciones
def es_artista_valido(text_completo):
  text_upper = text_completo.upper()
  exclusiones = ["BAD BUNNY", "DEI V", "OMAR COURTZ", "TITO DOUBLE P"]
  if any(exc in text_upper for exc in exclusiones):
    return False

  if any(
      re.search(rf"\b{re.escape(member)}\b", text_upper) for member in solo_bts
  ):
    return True
  return False


# Validación para la lista de Artistas
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


# Scraping de Canciones desde Kworb
def get_kworb_data(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  try:
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
      return pd.DataFrame({
          "Información": ["No se pudo cargar la tabla de canciones."]
      })

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
    if not df.empty:
      return df

    return pd.DataFrame({
        "Información": [
            "No se encontraron canciones de BTS o solistas actualmente."
        ]
    })
  except Exception as e:
    return pd.DataFrame({"Error": [f"Error de conexión: {e}"]})


# Extracción GARANTIZADA de Top Artistas desde Spotify Charts usando un Proxy Libre de Bloqueos
def get_artists_chart_official(region="hn", freq="daily"):
  spotify_region = "global" if region == "global" else "hn"
  chart_type = f"artist-{spotify_region}"

  # URL directa del endpoint de Spotify
  target_url = f"https://charts-spotify-com-service.spotify.com/public/v0/charts/{chart_type}-{freq}-latest"

  # Proxy para evadir el bloqueo HTTP 403 de Cloudflare en Streamlit
  proxy_url = f"https://api.allorigins.win/raw?url={target_url}"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  try:
    response = requests.get(proxy_url, headers=headers, timeout=15)

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

        # Extracción del nombre
        artista = (
            entry.get("artistName", "")
            or entry.get("artistMetadata", {}).get("artistName", "")
            or (
                entry.get("trackMetadata", {})
                .get("artists", [{}])[0]
                .get("name", "")
            )
        )

        prev_rank = chart_data.get(
            "previousRank", entry.get("previousRank", 0)
        )
        puesto_num = int(puesto) if puesto.isdigit() else idx

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
    return pd.DataFrame({"Error": [f"Error al obtener artistas: {e}"]})


# --- INTERFAZ STREAMLIT ---
st.title("💜 BTS Honduras Charts")
st.write(
    "¡Revisa en tiempo real las posiciones de BTS y sus integrantes en solo!"
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
  st.header("Sobre Nosotros")
  st.write("Estadísticas exclusivas de BTS y sus solistas en Honduras.")

with tab_spotify:
  st.header("🎧 Spotify Charts (Filtro Exclusivo BTS)")
  subtab_hn, subtab_global = st.tabs(["🇭🇳 Honduras", "🌍 Global"])

  # HONDURAS
  with subtab_hn:
    tab_hn_songs, tab_hn_artists = st.tabs(
        ["🎵 Top Canciones", "👤 Top Artistas"]
    )

    with tab_hn_songs:
      st.subheader("Top Canciones - Honduras 🇭🇳")
      c1, c2 = st.columns(2)
      with c1:
        st.markdown("**Diario**")
        st.dataframe(
            get_kworb_data("https://kworb.net/spotify/country/hn_daily.html"),
            hide_index=True,
            use_container_width=True,
            height=500,
        )
      with c2:
        st.markdown("**Semanal**")
        st.dataframe(
            get_kworb_data("https://kworb.net/spotify/country/hn_weekly.html"),
            hide_index=True,
            use_container_width=True,
            height=500,
        )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      ca1, ca2 = st.columns(2)
      with ca1:
        st.markdown("**Diario**")
        st.dataframe(
            get_artists_chart_official(region="hn", freq="daily"),
            hide_index=True,
            use_container_width=True,
            height=500,
        )
      with ca2:
        st.markdown("**Semanal**")
        st.dataframe(
            get_artists_chart_official(region="hn", freq="weekly"),
            hide_index=True,
            use_container_width=True,
            height=500,
        )

  # GLOBAL
  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(["🎵 Top Canciones", "👤 Top Artistas"])

    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      c3, c4 = st.columns(2)
      with c3:
        st.markdown("**Diario**")
        st.dataframe(
            get_kworb_data(
                "https://kworb.net/spotify/country/global_daily.html"
            ),
            hide_index=True,
            use_container_width=True,
            height=500,
        )
      with c4:
        st.markdown("**Semanal**")
        st.dataframe(
            get_kworb_data(
                "https://kworb.net/spotify/country/global_weekly.html"
            ),
            hide_index=True,
            use_container_width=True,
            height=500,
        )

    with tab_g_artists:
      st.subheader("Top Artistas - Global 🌍")
      ca3, ca4 = st.columns(2)
      with ca3:
        st.markdown("**Diario**")
        st.dataframe(
            get_artists_chart_official(region="global", freq="daily"),
            hide_index=True,
            use_container_width=True,
            height=500,
        )
      with ca4:
        st.markdown("**Semanal**")
        st.dataframe(
            get_artists_chart_official(region="global", freq="weekly"),
            hide_index=True,
            use_container_width=True,
            height=500,
        )

with tab_deezer:
  st.header("🔊 Deezer Charts")

with tab_redes:
  st.header("Síguenos")

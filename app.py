import io
import re
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

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


# Validación específica para la lista de Artistas
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


# Fetch auxiliar para Kworb y Deezer
def fetch_soup(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }
  try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
      return None
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")
  except Exception:
    return None


# Scraping para tablas de canciones (Kworb)
def get_kworb_data(url):
  try:
    soup = fetch_soup(url)
    if not soup:
      return pd.DataFrame(
          {"Información": ["Este chart no está disponible actualmente."]}
      )

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


# Scraping para Deezer
def get_simple_chart(url):
  try:
    soup = fetch_soup(url)
    if not soup:
      return pd.DataFrame(
          {"Información": ["Este chart no está disponible actualmente."]}
      )

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


# Consulta de reportes CSV de Spotify Charts con manejo de sesión
def get_spotify_official_artists(csv_url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      ),
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
      ),
      "Referer": "https://charts.spotify.com/",
  }

  try:
    response = requests.get(csv_url, headers=headers, timeout=10)

    if response.status_code != 200:
      return pd.DataFrame({
          "Información": [
              "Spotify Charts requiere credenciales para descargar este reporte"
              " directo."
          ]
      })

    csv_data = io.StringIO(response.text)
    df = pd.read_csv(csv_data)

    if "rank" in df.columns and "artist_names" in df.columns:
      df_filtrado = df[
          df["artist_names"].apply(
              lambda x: es_nombre_artista_valido(str(x))
          )
      ].copy()

      if df_filtrado.empty:
        return pd.DataFrame({
            "Información": [
                "No se encontraron integrantes de BTS en el top de artistas"
                " de este ranking."
            ]
        })

      df_final = pd.DataFrame({
          "Pos": df_filtrado["rank"],
          "Artista": df_filtrado["artist_names"],
      })

      if "previous_rank" in df_filtrado.columns:

        def calcular_mov(row):
          prev = row["previous_rank"]
          curr = row["rank"]
          if pd.isna(prev) or prev == -1:
            return "🆕 Nueva"
          diff = int(prev) - int(curr)
          if diff > 0:
            return f"🟩 +{diff}"
          elif diff < 0:
            return f"🟥 {diff}"
          return "➡️ ="

        df_final["Mov"] = df_filtrado.apply(calcular_mov, axis=1)

      return df_final

    return pd.DataFrame({
        "Información": ["Estructura de datos oficial no reconocida."]
    })

  except Exception as e:
    return pd.DataFrame({"Error": [f"No se pudieron obtener los datos: {e}"]})


# Configuración de la interfaz en Streamlit
st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

st.title("💜 BTS Honduras Charts")
st.write(
    "¡Revisa en tiempo real las posiciones de BTS y sus integrantes en solo!"
)

# Menú por Pestañas
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
      st.subheader("Top Artistas - Honduras 🇭🇳 (Datos Oficiales)")
      ca1, ca2 = st.columns(2)
      with ca1:
        st.markdown("**Diario**")
        df_adh = get_spotify_official_artists(
            "https://charts-spotify-com-service.spotify.com/public/v2/charts/csv/artist-hn-daily/latest"
        )
        st.dataframe(
            df_adh, hide_index=True, use_container_width=True, height=500
        )
      with ca2:
        st.markdown("**Semanal**")
        df_awh = get_spotify_official_artists(
            "https://charts-spotify-com-service.spotify.com/public/v2/charts/csv/artist-hn-weekly/latest"
        )
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
      st.subheader("Top Artistas - Global 🌍 (Datos Oficiales)")
      ca3, ca4 = st.columns(2)
      with ca3:
        st.markdown("**Diario Global**")
        df_adg = get_spotify_official_artists(
            "https://charts-spotify-com-service.spotify.com/public/v2/charts/csv/artist-global-daily/latest"
        )
        st.dataframe(
            df_adg, hide_index=True, use_container_width=True, height=500
        )
      with ca4:
        st.markdown("**Semanal Global**")
        df_awg = get_spotify_official_artists(
            "https://charts-spotify-com-service.spotify.com/public/v2/charts/csv/artist-global-weekly/latest"
        )
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

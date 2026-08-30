import random
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

# Lista de User-Agents para evitar bloqueos por IP/Patrón
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
        " Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101"
        " Firefox/123.0"
    ),
]


def icon_mov(val):
  val = str(val).strip()
  if val in ["=", "0", ""]:
    return "➡️ ="
  if "+" in val:
    return f"🟩 {val}"
  if "-" in val:
    return f"🟥 {val}"
  return f"🔵 {val}"


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
    if any(k in text_upper for k in ["BTS", "FEAT. V", "FT. V"]):
      return True
    partes = text_upper.split(" - ")
    if len(partes) > 0 and re.search(r"^\bV\b", partes[0].strip()):
      return True

  return False


def detectar_integrante(text_completo):
  text_upper = text_completo.upper()
  for member in solo_bts:
    if member == "V":
      if re.search(r"\bV\b", text_upper):
        return "V"
    else:
      if re.search(rf"\b{re.escape(member)}\b", text_upper):
        return member
  return "BTS"


def fetch_soup(url):
  headers = {
      "User-Agent": random.choice(USER_AGENTS),
      "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
  }
  try:
    response = requests.get(url, headers=headers, timeout=8)
    if response.status_code != 200:
      return None
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")
  except Exception:
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_kworb_data(url):
  soup = fetch_soup(url)
  if not soup:
    return pd.DataFrame({
        "Estado": [
            "Actualización en pausa temporal. Reintentando en unos minutos."
        ]
    })

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
      row_data = {"Pos": puesto, "Mov": mov, "Artista & Canción": full_text}
      if len(cols) >= 7:
        row_data["Streams"] = cols[6].text.strip()
      rows.append(row_data)

  df = pd.DataFrame(rows)
  if df.empty:
    return pd.DataFrame({
        "Información": [
            "No se encontraron canciones de BTS en este chart actualmente."
        ]
    })

  return df


@st.cache_data(ttl=3600, show_spinner=False)
def get_artists_from_songs(url):
  soup = fetch_soup(url)
  if not soup:
    return pd.DataFrame({
        "Estado": [
            "Actualización en pausa temporal. Reintentando en unos minutos."
        ]
    })

  table = soup.find("table")
  if not table:
    return pd.DataFrame()

  artistas_dict = {}
  for tr in table.find_all("tr")[1:]:
    cols = tr.find_all("td")
    if len(cols) < 3:
      continue

    try:
      puesto = int(cols[0].text.strip())
    except ValueError:
      continue

    full_text = cols[2].get_text(separator=" ").strip()

    if es_artista_valido(full_text):
      integrante = detectar_integrante(full_text)
      if integrante not in artistas_dict:
        artistas_dict[integrante] = puesto
      else:
        artistas_dict[integrante] = min(artistas_dict[integrante], puesto)

  if not artistas_dict:
    return pd.DataFrame({
        "Información": ["No se encontraron solistas o BTS en este listado."]
    })

  filas = [
      {"Mejor Posición Canción": f"#{pos}", "Artista": art}
      for art, pos in sorted(artistas_dict.items(), key=lambda x: x[1])
  ]
  return pd.DataFrame(filas)


@st.cache_data(ttl=3600, show_spinner=False)
def get_simple_chart(url):
  soup = fetch_soup(url)
  if not soup:
    return pd.DataFrame({
        "Estado": [
            "Actualización en pausa temporal. Reintentando en unos minutos."
        ]
    })

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
      rows.append({"Pos": puesto, "Mov": mov, "Artista & Canción": full_text})

  df = pd.DataFrame(rows)
  if df.empty:
    return pd.DataFrame({
        "Información": [
            "No se encontraron canciones de BTS en este chart actualmente."
        ]
    })

  return df


# Configuración e Interfaz Streamlit
st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="wide"
)

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
        st.markdown("**Resumen Diario**")
        st.dataframe(
            get_artists_from_songs(
                "https://kworb.net/spotify/country/hn_daily.html"
            ),
            hide_index=True,
            use_container_width=True,
            height=500,
        )
      with ca2:
        st.markdown("**Resumen Semanal**")
        st.dataframe(
            get_artists_from_songs(
                "https://kworb.net/spotify/country/hn_weekly.html"
            ),
            hide_index=True,
            use_container_width=True,
            height=500,
        )

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
        st.markdown("**Resumen Diario Global**")
        st.dataframe(
            get_artists_from_songs(
                "https://kworb.net/spotify/country/global_daily.html"
            ),
            hide_index=True,
            use_container_width=True,
            height=500,
        )
      with ca4:
        st.markdown("**Resumen Semanal Global**")
        st.dataframe(
            get_artists_from_songs(
                "https://kworb.net/spotify/country/global_weekly.html"
            ),
            hide_index=True,
            use_container_width=True,
            height=500,
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
        get_simple_chart("https://kworb.net/charts/deezer/hn.html"),
        hide_index=True,
        use_container_width=True,
        height=600,
    )
  with cd2:
    st.subheader("Global 🌍")
    st.dataframe(
        get_simple_chart("https://kworb.net/charts/deezer/ww.html"),
        hide_index=True,
        use_container_width=True,
        height=600,
    )

with tab_redes:
  st.header("Síguenos")
  st.markdown("[X / Twitter](https://x.com) | [Instagram](https://instagram.com)")

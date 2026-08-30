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

# Integrantes y nombres de BTS
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


def detectar_integrante(text_completo):
  try:
    text_upper = str(text_completo).upper()
    for member in SOLO_BTS:
      if member == "V":
        if re.search(r"\bV\b", text_upper):
          return "V"
      else:
        if re.search(rf"\b{re.escape(member)}\b", text_upper):
          return member
    return "BTS"
  except Exception:
    return "BTS"


def fetch_soup(url):
  headers = {"User-Agent": random.choice(USER_AGENTS)}
  try:
    response = requests.get(url, headers=headers, timeout=8)
    if response.status_code != 200:
      return None, ""
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    # Extraer la fecha oficial del reporte de Kworb
    fecha = ""
    subhead = soup.find("div", class_="subhead")
    if subhead:
      match = re.search(r"\d{4}/\d{2}/\d{2}", subhead.text)
      if match:
        fecha = match.group(0)

    return soup, fecha
  except Exception:
    return None, ""


@st.cache_data(ttl=1800, show_spinner=False)
def get_kworb_data(url):
  try:
    soup, fecha = fetch_soup(url)
    if not soup:
      return (
          pd.DataFrame({
              "Aviso": [
                  "Acceso limitado temporalmente por el proveedor."
                  " Reintentando..."
              ]
          }),
          "",
      )

    table = soup.find("table")
    if not table:
      return (
          pd.DataFrame({
              "Información": ["No hay datos disponibles en este momento."]
          }),
          fecha,
      )

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
            "Posición": f"#{puesto}",
            "Cambio": mov,
            "Artista & Canción": full_text,
        }
        if len(cols) >= 7:
          row_data["Streams"] = cols[6].text.strip()
        rows.append(row_data)

    df = pd.DataFrame(rows)
    if df.empty:
      return (
          pd.DataFrame({
              "Información": [
                  "No se encontraron canciones de BTS en este chart actualmente."
              ]
          }),
          fecha,
      )

    return df, fecha
  except Exception:
    return (
        pd.DataFrame({
            "Aviso": ["No se pudieron procesar los datos en este momento."]
        }),
        "",
    )


@st.cache_data(ttl=1800, show_spinner=False)
def get_official_kworb_artists(
    url="https://kworb.net/spotify/artists.html",
):
  try:
    soup, fecha = fetch_soup(url)
    if not soup:
      return (
          pd.DataFrame({
              "Aviso": [
                  "Acceso limitado temporalmente por el proveedor."
                  " Reintentando..."
              ]
          }),
          "",
      )

    table = soup.find("table")
    if not table:
      return (
          pd.DataFrame({"Información": ["No hay datos de artistas."]}),
          fecha,
      )

    rows = []
    for tr in table.find_all("tr")[1:]:
      cols = tr.find_all("td")
      if len(cols) < 2:
        continue

      puesto = cols[0].text.strip()

      if "artists.html" in url:
        nombre_artista = cols[1].text.strip()
        if es_artista_valido(nombre_artista):
          row_data = {"Posición": f"#{puesto}", "Artista": nombre_artista}
          if len(cols) >= 3:
            row_data["Streams Totales / Oyentes"] = cols[2].text.strip()
          rows.append(row_data)
      else:
        if len(cols) >= 3:
          mov = icon_mov(cols[1].text.strip())
          full_text = cols[2].get_text(separator=" ").strip()
          if es_artista_valido(full_text):
            integrante = detectar_integrante(full_text)
            row_data = {
                "Posición": f"#{puesto}",
                "Artista": integrante,
                "Cambio": mov,
                "Canción Encontrada": full_text,
            }
            rows.append(row_data)

    df = pd.DataFrame(rows)
    if df.empty:
      return (
          pd.DataFrame({
              "Información": [
                  "No se encontraron integrantes de BTS en el ranking actual."
              ]
          }),
          fecha,
      )

    df = df.drop_duplicates(subset=["Artista"], keep="first")
    return df, fecha
  except Exception:
    return (
        pd.DataFrame({
            "Aviso": ["Error al procesar el ranking de artistas."]
        }),
        "",
    )


@st.cache_data(ttl=1800, show_spinner=False)
def get_simple_chart(url):
  try:
    soup, fecha = fetch_soup(url)
    if not soup:
      return pd.DataFrame({
          "Aviso": [
              "Acceso limitado temporalmente por el proveedor. Reintentando..."
          ]
      })

    table = soup.find("table")
    if not table:
      return pd.DataFrame({
          "Información": ["No hay datos disponibles en este momento."]
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
        rows.append({
            "Posición": f"#{puesto}",
            "Cambio": mov,
            "Artista & Canción": full_text,
        })

    df = pd.DataFrame(rows)
    if df.empty:
      return pd.DataFrame({
          "Información": [
              "No se encontraron canciones de BTS en este chart actualmente."
          ]
      })

    return df
  except Exception:
    return pd.DataFrame({
        "Aviso": ["No se pudieron procesar los datos en este momento."]
    })


# --- Estructura Principal ---
st.title("💜 BTS Honduras Charts")
st.write(
    "¡Revisa en tiempo real las posiciones oficiales de BTS y sus integrantes"
    " en solo!"
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
        df_hn_d, fecha_hn_d = get_kworb_data(
            "https://kworb.net/spotify/country/hn_daily.html"
        )
        if fecha_hn_d:
          st.markdown(f"**Diario** `{fecha_hn_d}`")
        else:
          st.markdown("**Diario**")
        st.dataframe(
            df_hn_d, hide_index=True, use_container_width=True, height=500
        )
      with c2:
        df_hn_w, fecha_hn_w = get_kworb_data(
            "https://kworb.net/spotify/country/hn_weekly.html"
        )
        if fecha_hn_w:
          st.markdown(f"**Semanal** `{fecha_hn_w}`")
        else:
          st.markdown("**Semanal**")
        st.dataframe(
            df_hn_w, hide_index=True, use_container_width=True, height=500
        )

    with tab_hn_artists:
      st.subheader("Top Artistas - Honduras 🇭🇳")
      df_art_hn, fecha_art_hn = get_official_kworb_artists(
          "https://kworb.net/spotify/country/hn_daily.html"
      )
      if fecha_art_hn:
        st.caption(f"Actualizado al: {fecha_art_hn}")
      st.dataframe(
          df_art_hn, hide_index=True, use_container_width=True, height=500
      )

  with subtab_global:
    tab_g_songs, tab_g_artists = st.tabs(["🎵 Top Canciones", "👤 Top Artistas"])

    with tab_g_songs:
      st.subheader("Top Canciones - Global 🌍")
      c3, c4 = st.columns(2)
      with c3:
        df_g_d, fecha_g_d = get_kworb_data(
            "https://kworb.net/spotify/country/global_daily.html"
        )
        if fecha_g_d:
          st.markdown(f"**Diario** `{fecha_g_d}`")
        else:
          st.markdown("**Diario**")
        st.dataframe(
            df_g_d, hide_index=True, use_container_width=True, height=500
        )
      with c4:
        df_g_w, fecha_g_w = get_kworb_data(
            "https://kworb.net/spotify/country/global_weekly.html"
        )
        if fecha_g_w:
          st.markdown(f"**Semanal** `{fecha_g_w}`")
        else:
          st.markdown("**Semanal**")
        st.dataframe(
            df_g_w, hide_index=True, use_container_width=True, height=500
        )

    with tab_g_artists:
      st.subheader("Top Artistas Global 🌍")
      df_art_g, fecha_art_g = get_official_kworb_artists(
          "https://kworb.net/spotify/artists.html"
      )
      if fecha_art_g:
        st.caption(f"Actualizado al: {fecha_art_g}")
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
  st.markdown(
      "[X / Twitter](https://x.com) | [Instagram](https://instagram.com)"
  )

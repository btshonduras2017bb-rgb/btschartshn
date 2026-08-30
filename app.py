import base64
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

# Lista de BTS y solistas
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


def icon_mov(val):
  val = str(val).strip()
  if val in ["=", "0", "", "None"]:
    return "➡️ ="
  if "+" in val:
    return f"🟩 {val}"
  if "-" in val:
    return f"🟥 {val}"
  return f"🔵 {val}"


def es_artista_valido(text_completo):
  text_upper = text_completo.upper()
  exclusiones = ["BAD BUNNY", "DEI V", "OMAR COURTZ", "TITO DOUBLE P"]
  if any(exc in text_upper for exc in exclusiones):
    return False
  return any(
      re.search(rf"\b{re.escape(member)}\b", text_upper) for member in solo_bts
  )


# --- EXTRACCIÓN RÁPIDA CON CACHÉ (Evita lentitud) ---
@st.cache_data(ttl=1800)  # Se actualiza cada 30 minutos de forma automática
def get_kworb_cached(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  try:
    response = requests.get(url, headers=headers, timeout=8)
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

      row_data = {
          "Pos": puesto,
          "Mov": mov,
          "Artista & Canción": full_text,
          "Es_BTS": es_artista_valido(full_text),
      }
      if len(cols) >= 7:
        row_data["Streams"] = cols[6].text.strip()
      rows.append(row_data)

    return pd.DataFrame(rows)
  except:
    return pd.DataFrame()


# --- INTERFAZ STREAMLIT ---
st.title("💜 BTS Honduras Charts")
st.write(
    "Visualización instantánea de los charts musicales con opción de filtrado"
    " rápido."
)

tab_inicio, tab_spotify, tab_redes = st.tabs(
    ["🏠 Inicio", "🎧 Spotify", "🌐 Redes Sociales"]
)

with tab_inicio:
  st.header("Sobre Nosotros")
  st.write("Estadísticas de BTS y sus solistas optimizadas para velocidad.")

with tab_spotify:
  st.header("🎧 Spotify Daily Top Songs")

  # Selector de vista estilo Botones (BTS only / Full chart)
  modo_filtro = st.radio(
      "Filtro de visualización", ["BTS only", "Full chart"], horizontal=True
  )

  url_chart = "https://kworb.net/spotify/country/hn_daily.html"
  df = get_kworb_cached(url_chart)

  if not df.empty:
    if modo_filtro == "BTS only":
      df_final = df[df["Es_BTS"] == True].drop(columns=["Es_BTS"])
      if df_final.empty:
        st.info(
            "No hay canciones de BTS o solistas en el chart actual en este"
            " momento."
        )
      else:
        st.dataframe(df_final, hide_index=True, use_container_width=True)
    else:
      df_final = df.drop(columns=["Es_BTS"])
      st.dataframe(df_final, hide_index=True, use_container_width=True)
  else:
    st.error(
        "No se pudo conectar con el servidor o la página tardó demasiado en"
        " responder."
    )

with tab_redes:
  st.header("Síguenos en nuestras redes")

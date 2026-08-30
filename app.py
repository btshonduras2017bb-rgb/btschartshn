import pandas as pd
import requests
import streamlit as st


# Función para obtener datos de Kworb
def get_kworb_data(url, table_id):
  try:
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    dfs = pd.read_html(res.text)
    return dfs[0]
  except Exception as e:
    return pd.DataFrame({"Error": [str(e)]})


# Configuración de la página
st.set_page_config(
    page_title="BTS Honduras Charts", page_icon="💜", layout="centered"
)

# Encabezado principal
st.title("💜 BTS Honduras Charts")
st.write("¡Revisa en tiempo real los charts de BTS!")

# Banner principal
st.image(
    "https://pbs.twimg.com/media/HQyPXMUboAAvvBx?format=jpg&name=4096x4096",
    use_container_width=True,
)

# Menú lateral
st.sidebar.title("Navegación")
opcion = st.sidebar.radio(
    "Ir a:",
    [
        "Inicio",
        "Spotify",
        "Apple Music",
        "Youtube Music",
        "Deezer",
        "Redes Sociales",
    ],
)

if opcion == "Inicio":
  st.header("Sobre Nosotros")
  st.write(
      "Aquí encontrarás las novedades, proyectos de streaming y estadísticas de"
      " BTS en Honduras."
  )

elif opcion == "Spotify":
  st.header("🎧 Spotify Charts")

  st.subheader("Honduras 🇭🇳")
  c1, c2 = st.columns(2)
  with c1:
    st.markdown("**Top Diario Honduras**")
    df_hd = get_kworb_data(
        "https://kworb.net/spotify/country/hn_daily.html", "spotifydaily"
    )
    st.dataframe(
        df_hd, hide_index=True, use_container_width=True, height=600
    )
  with c2:
    st.markdown("**Top Semanal Honduras**")
    df_hw = get_kworb_data(
        "https://kworb.net/spotify/country/hn_weekly.html", "spotifyweekly"
    )
    st.dataframe(
        df_hw, hide_index=True, use_container_width=True, height=600
    )

  st.divider()

  st.subheader("Global 🌍")
  c3, c4 = st.columns(2)
  with c3:
    st.markdown("**Top Diario Global**")
    df_gd = get_kworb_data(
        "https://kworb.net/spotify/country/global_daily.html", "spotifydaily"
    )
    st.dataframe(
        df_gd, hide_index=True, use_container_width=True, height=600
    )
  with c4:
    st.markdown("**Top Semanal Global**")
    df_gw = get_kworb_data(
        "https://kworb.net/spotify/country/global_weekly.html", "spotifyweekly"
    )
    st.dataframe(
        df_gw, hide_index=True, use_container_width=True, height=600
    )

elif opcion == "Apple Music":
  st.header("📊 Apple Music")
  st.write("Sección de Apple Music en construcción.")

elif opcion == "Youtube Music":
  st.header("📊 Youtube Music")
  st.write("Sección de YouTube Music en construcción.")

elif opcion == "Deezer":
  st.header("📊 Deezer")
  st.write("Sección de Deezer en construcción.")

elif opcion == "Redes Sociales":
  st.header("Síguenos")
  st.markdown("[X / Twitter](https://x.com) | [Instagram](https://instagram.com)")

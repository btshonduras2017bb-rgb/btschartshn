import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="BTS Honduras Charts",
    page_icon="💜",
    layout="centered"
)

# Encabezado principal
st.title("💜 BTS Honduras Charts & Fanbase")
st.write("¡Bienvenid@ a la plataforma oficial de fans de BTS en Honduras!")

# Banner principal
st.image("https://images.unsplash.com/photo-1514525253161-7a46d19cd819", use_container_width=True)

# Menú lateral
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["Inicio", "Charts", "Proyectos", "Redes Sociales"])

if opcion == "Inicio":
    st.header("Sobre Nosotros")
    st.write("Aquí encontrarás las novedades, proyectos de streaming y estadísticas de BTS en Honduras.")

elif opcion == "Charts":
    st.header("📊 Streaming Charts")
    st.info("Próximamente actualizaremos los datos de streaming en Spotify y YouTube.")

elif opcion == "Proyectos":
    st.header("🎉 Próximos Proyectos")
    st.write("Proyectos de cumpleaños, cup sleeves y metas de streaming.")

elif opcion == "Redes Sociales":
    st.header("Síguenos")
    st.markdown("[X / Twitter](https://x.com) | [Instagram](https://instagram.com)")

import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Bogota")

# MongoDB connection
client = MongoClient(st.secrets["mongo_uri"])
db = client["rutina_vital"]
col_comidas = db["comidas"]
col_sueno = db["sueno"]
col_trabajo = db["trabajo"]
col_youtube = db["youtube_abstinencia"]

# Session state initialization
def init_session():
    for key in ["inicio_comida", "tipo_comida", "cronometro_comida", "inicio_sueno", "cronometro_sueno", "inicio_trabajo", "cronometro_trabajo"]:
        if key not in st.session_state:
            st.session_state[key] = None

init_session()

# App title
st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

# Tabs
secciones = st.tabs(["🍽️ Comidas", "🛌 Sueño", "🏢 Trabajo", "📵 YouTube"])

with secciones[0]:
    st.header("🍽️ Comidas con cronómetro")

    comida_en_progreso = col_comidas.find_one({"en_progreso": True})
    if comida_en_progreso and not st.session_state.cronometro_comida:
        if "inicio" in comida_en_progreso:
            st.session_state.tipo_comida = comida_en_progreso["tipo"]
            st.session_state.inicio_comida = datetime.strptime(comida_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
            st.session_state.cronometro_comida = True

    if not st.session_state.cronometro_comida:
        tipo = st.selectbox("Selecciona tipo de comida para iniciar cronómetro:", ["--", "Desayuno", "Almuerzo", "Cena", "Snack", "Break"])
        if tipo != "--":
            with st.spinner("Iniciando cronómetro..."):
                inicio = datetime.now(ZONA)
                st.session_state.inicio_comida = inicio
                st.session_state.tipo_comida = tipo
                st.session_state.cronometro_comida = True
                col_comidas.insert_one({"tipo": tipo, "inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
            st.success(f"{tipo} iniciado a las {inicio.strftime('%H:%M:%S')}")

    if st.session_state.cronometro_comida:
        tiempo_transcurrido = datetime.now(ZONA) - st.session_state.inicio_comida
        minutos, segundos = divmod(tiempo_transcurrido.seconds, 60)
        horas, minutos = divmod(minutos, 60)
        st.markdown(f"🕰️ Tiempo transcurrido: **{horas:02d}:{minutos:02d}:{segundos:02d}**")

        if st.button("Finalizar comida"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_comida).total_seconds() / 60
            resultado = col_comidas.update_one(
                {"en_progreso": True, "tipo": st.session_state.tipo_comida},
                {"$set": {
                    "fin": fin.strftime('%Y-%m-%d %H:%M:%S'),
                    "duracion_min": round(duracion, 2),
                    "en_progreso": False
                }}
            )
            if resultado.modified_count > 0:
                st.success(f"{st.session_state.tipo_comida} finalizado a las {fin.strftime('%H:%M:%S')} - Duración: {duracion:.1f} minutos")
            st.session_state.inicio_comida = None
            st.session_state.tipo_comida = None
            st.session_state.cronometro_comida = False

    st.subheader("📊 Historial de comidas")
    comidas = list(col_comidas.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    if comidas:
        st.dataframe(comidas)
    else:
        st.info("No hay registros de comidas finalizadas.")

with secciones[1]:
    st.header("🛌 Registro de sueño")

    sueno_en_progreso = col_sueno.find_one({"en_progreso": True})
    if sueno_en_progreso and not st.session_state.cronometro_sueno:
        if "inicio" in sueno_en_progreso:
            st.session_state.inicio_sueno = datetime.strptime(sueno_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
            st.session_state.cronometro_sueno = True

    if not st.session_state.cronometro_sueno:
        if st.button("Iniciar sueño"):
            inicio = datetime.now(ZONA)
            st.session_state.inicio_sueno = inicio
            st.session_state.cronometro_sueno = True
            col_sueno.insert_one({"inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
            st.success(f"Sueño iniciado a las {inicio.strftime('%H:%M:%S')}")

    if st.session_state.cronometro_sueno:
        tiempo_transcurrido = datetime.now(ZONA) - st.session_state.inicio_sueno
        minutos, segundos = divmod(tiempo_transcurrido.seconds, 60)
        horas, minutos = divmod(minutos, 60)
        st.markdown(f"⏳ Duración del sueño: **{horas:02d}:{minutos:02d}:{segundos:02d}**")

        if st.button("Finalizar sueño"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_sueno).total_seconds() / 3600
            resultado = col_sueno.update_one(
                {"en_progreso": True},
                {"$set": {
                    "fin": fin.strftime('%Y-%m-%d %H:%M:%S'),
                    "duracion_horas": round(duracion, 2),
                    "en_progreso": False
                }}
            )
            if resultado.modified_count > 0:
                st.success(f"🔚 Sueño finalizado a las {fin.strftime('%H:%M:%S')} - Dormiste {duracion:.2f} horas")
            st.session_state.inicio_sueno = None
            st.session_state.cronometro_sueno = False

    st.subheader("📊 Historial de sueño")
    suenos = list(col_sueno.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    if suenos:
        st.dataframe(suenos)
    else:
        st.info("No hay registros de sueño finalizados.")

with secciones[2]:
    st.header("🏢 Registro de trabajo")

    trabajo_en_progreso = col_trabajo.find_one({"en_progreso": True})
    if trabajo_en_progreso and not st.session_state.cronometro_trabajo:
        if "salida" in trabajo_en_progreso:
            st.session_state.inicio_trabajo = datetime.strptime(trabajo_en_progreso["salida"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
            st.session_state.cronometro_trabajo = True

    if not st.session_state.cronometro_trabajo:
        if st.button("Registrar salida de casa"):
            salida = datetime.now(ZONA)
            st.session_state.inicio_trabajo = salida
            st.session_state.cronometro_trabajo = True
            col_trabajo.insert_one({"salida": salida.strftime('%Y-%m-%d %H:%M:%S'), "fecha": salida.strftime('%Y-%m-%d'), "en_progreso": True})
            st.success(f"🛎️ Salida registrada a las {salida.strftime('%H:%M:%S')}")

    if st.session_state.cronometro_trabajo:
        tiempo_transcurrido = datetime.now(ZONA) - st.session_state.inicio_trabajo
        minutos, segundos = divmod(tiempo_transcurrido.seconds, 60)
        horas, minutos = divmod(minutos, 60)
        st.markdown(f"🛎️ Tiempo desde salida: **{horas:02d}:{minutos:02d}:{segundos:02d}**")

        if st.button("Registrar llegada al trabajo"):
            llegada = datetime.now(ZONA)
            diferencia = (llegada - st.session_state.inicio_trabajo).total_seconds() / 60
            resultado = col_trabajo.update_one(
                {"en_progreso": True},
                {"$set": {
                    "llegada": llegada.strftime('%Y-%m-%d %H:%M:%S'),
                    "duracion_min": round(diferencia, 2),
                    "en_progreso": False
                }}
            )
            if resultado.modified_count > 0:
                st.success(f"🏁 Llegada registrada a las {llegada.strftime('%H:%M:%S')} - Duración: {diferencia:.1f} minutos")
            st.session_state.inicio_trabajo = None
            st.session_state.cronometro_trabajo = False

    st.subheader("📊 Historial de trabajo")
    trabajos = list(col_trabajo.find({"en_progreso": False}, {"_id": 0}).sort("salida", -1))
    if trabajos:
        st.dataframe(trabajos)
    else:
        st.info("No hay registros de trabajo finalizados.")

with secciones[3]:
    st.header("📵 Abstinencia de YouTube")

    abstinencia = st.checkbox("Tuve ganas de entrar a YouTube y me abstuve")

    if abstinencia and st.button("Registrar abstinencia"):
        evento = {
            "fecha": datetime.now(ZONA).strftime('%Y-%m-%d'),
            "hora": datetime.now(ZONA).strftime('%H:%M:%S'),
            "mensaje": "Abstinencia registrada"
        }
        col_youtube.insert_one(evento)
        st.success(f"✅ Registrado: {evento['fecha']} a las {evento['hora']}")

    st.subheader("📊 Historial de abstinencia")
    abstinencias = list(col_youtube.find({}, {"_id": 0}).sort("fecha", -1))
    if abstinencias:
        st.dataframe(abstinencias)
    else:
        st.info("No hay registros aún.")

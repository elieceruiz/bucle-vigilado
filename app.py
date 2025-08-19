import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh

# === CONFIGURACIÓN ===
st.set_page_config(page_title="BucleVigiladoApp", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_hitos = db["hitos"]
coleccion_visual = db["log_visual"]
coleccion_intentos = db["intentos_iniciativa"]   # nueva colección

# === DEFINICIONES DE EVENTO ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial completo": "historial",
    f"✊🏽 {evento_a}": evento_a,
    f"💸 {evento_b}": evento_b,
}

# === ESTADO INICIAL ===
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# === UI PRINCIPAL ===
st.title("BucleVigilado")
seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

# 🧹 Limpieza de estado al cambiar vista
if opcion != "reflexion":
    for key in ["texto_reflexion", "emociones_reflexion", "limpiar_reflexion", "📝 Guardar reflexión"]:
        st.session_state.pop(key, None)

# === FUNCIONES ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({"evento": nombre_evento, "fecha_hora": fecha_hora})
    st.session_state[nombre_evento] = fecha_hora

def registrar_intento(nombre_evento, decision, fecha_hora):
    coleccion_intentos.insert_one({
        "evento": nombre_evento,
        "decision": decision,  # "si" o "no"
        "fecha_hora": fecha_hora
    })

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

def registrar_hito(evento, hito, desde, fecha):
    if not coleccion_hitos.find_one({"evento": evento, "hito": hito, "desde": desde}):
        coleccion_hitos.insert_one({
            "evento": evento,
            "hito": hito,
            "desde": desde,
            "fecha_registro": fecha
        })

def registrar_log_visual(evento, meta, desde, minutos, porcentaje):
    if not coleccion_visual.find_one({"evento": evento, "meta_activada": meta, "desde": desde}):
        coleccion_visual.insert_one({
            "evento": evento,
            "meta_activada": meta,
            "desde": desde,
            "fecha_registro": datetime.now(colombia),
            "progreso_minutos": minutos,
            "porcentaje_meta": porcentaje
        })

# === NUEVO: TABLA DE INTENTOS ===
def obtener_intentos(nombre_evento):
    intentos = list(coleccion_intentos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    total = len(intentos)
    for i, e in enumerate(intentos):
        fecha = e["fecha_hora"].astimezone(colombia)
        filas.append({
            "N°": total - i,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Decisión": "✅ Sí" if e["decision"] == "si" else "❌ No"
        })
    return pd.DataFrame(filas)

# === (resto de funciones de racha, obtener_registros, obtener_reflexiones igual que tu código) ===
# ... no toqué nada en esas, las dejo como están ...

# === MÓDULO EVENTO ===
if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento: {seleccion}")
    fecha_hora_evento = datetime.now(colombia)

    if opcion == evento_a:
        st.info("👉 Antes de registrar, decidí si realmente querés hacerlo.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sí, registrar"):
                registrar_intento(evento_a, "si", fecha_hora_evento)
                registrar_evento(evento_a, fecha_hora_evento)
                st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")
        with col2:
            if st.button("❌ No, cancelar"):
                registrar_intento(evento_a, "no", fecha_hora_evento)
                st.warning("Intento registrado como NO")

    else:
        if st.button("☠️ ¿Registrar?"):
            registrar_evento(opcion, fecha_hora_evento)
            st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")

    mostrar_racha(opcion, seleccion.split()[0])

# === MÓDULO HISTORIAL COMPLETO ===
elif opcion == "historial":
    st.header("📑 Historial completo")
    tabs = st.tabs([
        "🧠 Reflexiones",
        "✊🏽 Iniciativa Aquella",
        "💸 Iniciativa de Pago",
        "👀 Intentos Iniciativa Aquella"
    ])

    with tabs[0]:
        st.subheader("📍 Historial de reflexiones")
        df_r = obtener_reflexiones()
        for i, row in df_r.iterrows():
            with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
                st.write(row["Reflexión"])

    def mostrar_tabla_eventos(nombre_evento):
        st.subheader(f"📍 Registros de {nombre_evento}")
        mostrar = st.checkbox("Ver/Ocultar registros", value=False, key=f"mostrar_{nombre_evento}")
        df = obtener_registros(nombre_evento)
        if mostrar:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            df_oculto = df.copy()
            df_oculto["Fecha"] = "••••-••-••"
            df_oculto["Hora"] = "••:••"
            df_oculto["Duración sin caer"] = "••a ••m ••d ••h ••m"
            st.dataframe(df_oculto, use_container_width=True, hide_index=True)
            st.caption("🔒 Registros ocultos. Activá el check para visualizar.")

    with tabs[1]:
        mostrar_tabla_eventos(evento_a)
    with tabs[2]:
        mostrar_tabla_eventos(evento_b)
    with tabs[3]:
        st.subheader("📍 Intentos de acceso")
        df_i = obtener_intentos(evento_a)
        if not df_i.empty:
            st.dataframe(df_i, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No hay intentos registrados todavía.")
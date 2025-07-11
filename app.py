import streamlit as st
st.set_page_config(page_title="BucleVigiladoApp", layout="centered")

from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh

# Timezone
colombia = pytz.timezone("America/Bogota")

# Auto-refresh
st_autorefresh(interval=1000, key="refresh")

# MongoDB connection
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion = db["eventos"]

# Event names
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# Session state initialization
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# Emotions list
emociones_opciones = [
    "😰 Ansioso",
    "😡 Irritado / Rabia contenida",
    "💪 Firme / Decidido",
    "😌 Aliviado / Tranquilo",
    "😓 Culpable",
    "🥱 Apático / Cansado",
    "😔 Triste"
]

# Register event
def registrar_evento(nombre_evento, fecha_hora, emociones=None, reflexion=None):
    doc = {
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    }
    if emociones:
        doc["emociones"] = [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones]
    if reflexion:
        doc["reflexion"] = reflexion.strip()
    coleccion.insert_one(doc)
    st.session_state[nombre_evento] = fecha_hora

# UI
st.title("BucleVigilado")

st.subheader("Registrar evento")

col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽", value=False)
with col2:
    check_b = st.checkbox("💸", value=False)

usar_fecha_hora_manual = st.checkbox("Ingresar fecha y hora manualmente")
fecha_hora = None

if usar_fecha_hora_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora_texto = st.text_input("Hora (HH:MM, formato 24h)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora = datetime.combine(fecha, hora)
        fecha_hora = colombia.localize(fecha_hora)
    except ValueError:
        st.error("Formato de hora no válido. Usa HH:MM en formato 24h.")
else:
    fecha_hora = datetime.now(colombia)

# Emotions + Reflection
emociones_seleccionadas = []
reflexion = ""

if check_a or check_b:
    emociones_seleccionadas = st.multiselect(
        "¿Cómo te sentías en ese momento?",
        emociones_opciones
    )
    reflexion = st.text_area(
        "¿Querés decir algo más sobre lo que sentiste o pensaste?",
        height=150
    )
    if reflexion.strip():
        palabras = len(reflexion.strip().split())
        st.caption(f"📝 Palabras: {palabras}")

# Register button
if st.button("Registrar"):
    if fecha_hora:
        if check_a:
            registrar_evento(evento_a, fecha_hora, emociones_seleccionadas, reflexion)
            st.success("✊🏽 Evento registrado")
        if check_b:
            registrar_evento(evento_b, fecha_hora, emociones_seleccionadas, reflexion)
            st.success("💸 Evento registrado")
        if not check_a and not check_b:
            st.warning("Selecciona al menos un evento para registrar.")

# Current streak
st.subheader("⏱️ Racha actual")
col3, col4 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ahora = datetime.now(colombia)
        ultimo = st.session_state[nombre_evento]
        delta = ahora - ultimo
        minutos = int(delta.total_seconds() // 60)
        rdelta = relativedelta(ahora, ultimo)
        detalle = f"{rdelta.years} años, {rdelta.months} meses, {rdelta.days} días, {rdelta.hours} h, {rdelta.minutes} min, {rdelta.seconds} s"
        st.metric(emoji, f"{minutos} minutos")
        st.caption(detalle)
    else:
        st.metric(emoji, "0 minutos")
        st.caption("0 años, 0 meses, 0 días, 0 h, 0 min, 0 s")

with col3:
    mostrar_racha(evento_a, "✊🏽")
with col4:
    mostrar_racha(evento_b, "💸")

# History tabs
st.subheader("📑 Historial de registros")
tab1, tab2, tab3 = st.tabs(["✊🏽", "💸", "📂 Reflexiones y Descargas"])

def obtener_registros(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{
        "N°": total - i,
        "Fecha": f.date(),
        "Hora": f.strftime("%H:%M"),
        "Emociones": ", ".join([f'{emo["emoji"]} {emo["nombre"]}' for emo in eventos[i].get("emociones", [])]),
        "Reflexión": eventos[i].get("reflexion", "")
    } for i, f in enumerate(fechas)])

with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)

# 📂 Reflexiones completas y descarga
with tab3:
    st.subheader("🧠 Reflexiones completas y análisis")

    def traer_registros():
        eventos = list(coleccion.find().sort("fecha_hora", -1))
        filas = []
        for i, e in enumerate(eventos):
            fecha_hora = e["fecha_hora"].astimezone(colombia)
            emociones = ", ".join([f'{emo["emoji"]} {emo["nombre"]}' for emo in e.get("emociones", [])])
            reflexion = e.get("reflexion", "")
            palabras = len(reflexion.strip().split()) if reflexion.strip() else 0
            filas.append({
                "N°": len(eventos) - i,
                "Evento": e["evento"],
                "Fecha": fecha_hora.date(),
                "Hora": fecha_hora.strftime("%H:%M"),
                "Emociones": emociones,
                "Reflexión completa": reflexion,
                "Palabras": palabras
            })
        return pd.DataFrame(filas)

    df_reflexiones = traer_registros()

    for _, row in df_reflexiones.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Evento']} — {row['Emociones']}"):
            st.write(row["Reflexión completa"])
            st.caption(f"📝 Palabras: {row['Palabras']}")

    st.markdown("---")
    csv = df_reflexiones.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📄 Descargar reflexiones como CSV",
        data=csv,
        file_name="reflexiones_completas.csv",
        mime="text/csv"
    )
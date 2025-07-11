import streamlit as st
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
import pytz
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh

# Timezone
colombia = pytz.timezone("America/Bogota")

# Auto-refresh
st_autorefresh(interval=1000, key="refresh")

# MongoDB setup
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion = db["eventos"]

# Event labels
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# Initialize session
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# Emotion options
emociones_opciones = [
    "😰 Ansioso",
    "😡 Irritado / Rabia contenida",
    "💪 Firme / Decidido",
    "😌 Aliviado / Tranquilo",
    "😓 Culpable",
    "🥱 Apático / Cansado",
    "😔 Triste"
]

# Function to register events
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

# UI: Event Registration
st.title("BucleVigilado")
st.subheader("Register Event")

col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽", value=False)
with col2:
    check_b = st.checkbox("💸", value=False)

manual = st.checkbox("Enter date and time manually")
fecha_hora = None

if manual:
    fecha = st.date_input("Date", datetime.now(colombia).date())
    hora_texto = st.text_input("Time (HH:MM, 24h)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora = datetime.combine(fecha, hora)
        fecha_hora = colombia.localize(fecha_hora)
    except ValueError:
        st.error("Invalid format. Use HH:MM in 24h.")
else:
    fecha_hora = datetime.now(colombia)

emociones_seleccionadas = []
reflexion = ""

if check_a or check_b:
    emociones_seleccionadas = st.multiselect("How were you feeling?", emociones_opciones)
    reflexion = st.text_area("Anything else you want to write?", height=150)
    if reflexion.strip():
        st.caption(f"📝 Word count: {len(reflexion.strip().split())}")

if st.button("Register"):
    if fecha_hora:
        if check_a:
            registrar_evento(evento_a, fecha_hora, emociones_seleccionadas, reflexion)
            st.success("✊🏽 Event registered")
        if check_b:
            registrar_evento(evento_b, fecha_hora, emociones_seleccionadas, reflexion)
            st.success("💸 Event registered")
        if not check_a and not check_b:
            st.warning("Please select at least one event.")

# Independent reflection block
st.subheader("🧠 Save Reflection Only (does NOT affect streaks)")

emociones_sueltas = st.multiselect(
    "How are you feeling?",
    emociones_opciones,
    key="emociones_sueltas"
)

reflexion_suelta = st.text_area(
    "Write what's on your mind...",
    height=150,
    key="reflexion_suelta"
)

if reflexion_suelta.strip():
    palabras_suelta = len(reflexion_suelta.strip().split())
    st.caption(f"📝 Word count: {palabras_suelta}")

if st.button("Save Reflection Only"):
    doc = {
        "evento": "Solo Reflexión",
        "fecha_hora": datetime.now(colombia),
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones_sueltas],
        "reflexion": reflexion_suelta.strip()
    }
    coleccion.insert_one(doc)
    st.success("🧠 Reflection saved without affecting streaks.")

# Current streaks
st.subheader("⏱️ Current Streak")

col3, col4 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ahora = datetime.now(colombia)
        ultimo = st.session_state[nombre_evento]
        delta = ahora - ultimo
        minutos = int(delta.total_seconds() // 60)
        rdelta = relativedelta(ahora, ultimo)
        detalle = f"{rdelta.years}y {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        st.metric(emoji, f"{minutos} min")
        st.caption(detalle)
    else:
        st.metric(emoji, "0 min")
        st.caption("No records yet")

with col3:
    mostrar_racha(evento_a, "✊🏽")
with col4:
    mostrar_racha(evento_b, "💸")

# Event history tabs
st.subheader("📑 Event History")
tab1, tab2, tab3 = st.tabs(["✊🏽", "💸", "📂 Reflections"])

def obtener_registros(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{
        "N°": total - i,
        "Date": f.date(),
        "Time": f.strftime("%H:%M"),
        "Emotions": ", ".join([f'{emo["emoji"]} {emo["nombre"]}' for emo in eventos[i].get("emociones", [])]),
        "Reflection": eventos[i].get("reflexion", "")
    } for i, f in enumerate(fechas)])

with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)

# Tab 3: Reflections and export
with tab3:
    st.subheader("🧠 Complete Reflections and Analysis")

    def traer_solo_reflexiones():
        eventos = list(coleccion.find({"reflexion": {"$exists": True, "$ne": ""}}).sort("fecha_hora", -1))
        filas = []
        for i, e in enumerate(eventos):
            fecha_hora = e["fecha_hora"].astimezone(colombia)
            emociones = ", ".join([f'{emo["emoji"]} {emo["nombre"]}' for emo in e.get("emociones", [])])
            reflexion = e.get("reflexion", "")
            palabras = len(reflexion.strip().split())
            filas.append({
                "N°": len(eventos) - i,
                "Event": e["evento"],
                "Date": fecha_hora.date(),
                "Time": fecha_hora.strftime("%H:%M"),
                "Emotions": emociones,
                "Full Reflection": reflexion,
                "Words": palabras
            })
        return pd.DataFrame(filas)

    df_reflexiones = traer_solo_reflexiones()
    total_r = len(df_reflexiones)
    total_p = df_reflexiones["Words"].sum()
    st.caption(f"📌 Total Reflections: {total_r} | ✍️ Total Words: {total_p}")

    emociones_unicas = sorted(set(e for sublist in df_reflexiones["Emotions"].str.split(", ") for e in sublist if e))
    emocion_filtrada = st.selectbox("🔍 Filter by emotion", ["All"] + emociones_unicas)

    if emocion_filtrada != "All":
        df_mostrar = df_reflexiones[df_reflexiones["Emotions"].str.contains(emocion_filtrada)]
    else:
        df_mostrar = df_reflexiones

    for _, row in df_mostrar.iterrows():
        with st.expander(f"{row['Date']} {row['Time']} — {row['Event']} — {row['Emotions']}"):
            st.write(row["Full Reflection"])
            st.caption(f"📝 Words: {row['Words']}")

    csv = df_mostrar.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📄 Download reflections as CSV",
        data=csv,
        file_name="filtered_reflections.csv",
        mime="text/csv"
    )
import streamlit as st
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
import pytz
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh

# Zona horaria
colombia = pytz.timezone("America/Bogota")

# Recarga automática cada segundo
st_autorefresh(interval=1000, key="refresh")

# Conexión MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion = db["eventos"]

# Eventos
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# Inicializar sesión
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# Lista de emociones
emociones_opciones = [
    "😰 Ansioso",
    "😡 Irritado / Rabia contenida",
    "💪 Firme / Decidido",
    "😌 Aliviado / Tranquilo",
    "😓 Culpable",
    "🥱 Apático / Cansado",
    "😔 Triste"
]

# Función para registrar evento
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

# Registro de evento
st.subheader("Registrar evento")

col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽", value=False)
with col2:
    check_b = st.checkbox("💸", value=False)

usar_manual = st.checkbox("Ingresar fecha y hora manualmente")
fecha_hora = None

if usar_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora_texto = st.text_input("Hora (HH:MM, 24h)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora = datetime.combine(fecha, hora)
        fecha_hora = colombia.localize(fecha_hora)
    except ValueError:
        st.error("Formato inválido. Usa HH:MM en 24h.")
else:
    fecha_hora = datetime.now(colombia)

# Emociones + reflexión
emociones_seleccionadas = []
reflexion = ""

if check_a or check_b:
    emociones_seleccionadas = st.multiselect("¿Cómo te sentías en ese momento?", emociones_opciones)
    reflexion = st.text_area("¿Querés decir algo más sobre lo que sentiste o pensaste?", height=150)
    if reflexion.strip():
        st.caption(f"📝 Palabras: {len(reflexion.strip().split())}")

# Botón de registro
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

# Rachas
st.subheader("⏱️ Racha actual")
col3, col4 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ahora = datetime.now(colombia)
        ultimo = st.session_state[nombre_evento]
        delta = ahora - ultimo
        minutos = int(delta.total_seconds() // 60)
        rdelta = relativedelta(ahora, ultimo)
        detalle = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        st.metric(emoji, f"{minutos} min")
        st.caption(detalle)
    else:
        st.metric(emoji, "0 min")
        st.caption("Sin registros")

with col3:
    mostrar_racha(evento_a, "✊🏽")
with col4:
    mostrar_racha(evento_b, "💸")

# Tabs de historial
st.subheader("📑 Historial de registros")
tab1, tab2, tab3 = st.tabs(["✊🏽", "💸", "📂 Reflexiones"])

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

# TAB 3: Reflexiones completas y descarga
with tab3:
    st.subheader("🧠 Reflexiones completas y análisis")

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
                "Evento": e["evento"],
                "Fecha": fecha_hora.date(),
                "Hora": fecha_hora.strftime("%H:%M"),
                "Emociones": emociones,
                "Reflexión completa": reflexion,
                "Palabras": palabras
            })
        return pd.DataFrame(filas)

    df_reflexiones = traer_solo_reflexiones()

    # Estadísticas
    total_r = len(df_reflexiones)
    total_p = df_reflexiones["Palabras"].sum()
    st.caption(f"📌 Reflexiones: {total_r} | ✍️ Palabras totales: {total_p}")

    # Filtro por emoción
    emociones_unicas = sorted(set(e for sublist in df_reflexiones["Emociones"].str.split(", ") for e in sublist if e))
    emocion_filtrada = st.selectbox("🔍 Filtrar por emoción", ["Todas"] + emociones_unicas)

    if emocion_filtrada != "Todas":
        df_mostrar = df_reflexiones[df_reflexiones["Emociones"].str.contains(emocion_filtrada)]
    else:
        df_mostrar = df_reflexiones

    for _, row in df_mostrar.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Evento']} — {row['Emociones']}"):
            st.write(row["Reflexión completa"])
            st.caption(f"📝 Palabras: {row['Palabras']}")

    # Exportar CSV
    st.markdown("---")
    csv = df_mostrar.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📄 Descargar reflexiones como CSV",
        data=csv,
        file_name="reflexiones_filtradas.csv",
        mime="text/csv"
    )
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
coleccion_intentos = db["intentos_ingreso"]

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

def registrar_intento(evento, decision, fecha_hora):
    coleccion_intentos.insert_one({"evento": evento, "decision": decision, "fecha_hora": fecha_hora})

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

def mostrar_racha(nombre_evento, emoji):
    clave_estado = f"mostrar_racha_{nombre_evento}"
    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = False

    mostrar = st.checkbox("Ver/ocultar racha", value=st.session_state[clave_estado], key=f"check_{nombre_evento}")
    st.session_state[clave_estado] = mostrar

    st.markdown("### ⏱️ Racha")

    if nombre_evento in st.session_state:
        st_autorefresh(interval=1000, limit=None, key=f"auto_{nombre_evento}")

        ultimo = st.session_state[nombre_evento]
        ahora = datetime.now(colombia)
        delta = ahora - ultimo
        detalle = relativedelta(ahora, ultimo)
        minutos = int(delta.total_seconds() // 60)
        tiempo = f"{detalle.years}a {detalle.months}m {detalle.days}d {detalle.hours}h {detalle.minutes}m {detalle.seconds}s"

        if mostrar:
            st.metric("Duración", f"{minutos:,} min", tiempo)
            st.caption(f"🔴 Última recaída: {ultimo.strftime('%Y-%m-%d %H:%M:%S')}")

            if nombre_evento == "La Iniciativa Aquella":
                registros = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
                record = max([(registros[i - 1]["fecha_hora"] - registros[i]["fecha_hora"])
                              for i in range(1, len(registros))], default=delta)
                record_str = str(record).split('.')[0]
                fecha_inicio = registros[0]["fecha_hora"].astimezone(colombia)

                umbral = timedelta(days=3)
                meta_5 = timedelta(days=5)
                meta_21 = timedelta(days=21)

                if delta > umbral:
                    st.success("✅ Superaste la zona crítica de las 72 horas.")
                    registrar_hito(nombre_evento, "3 días", fecha_inicio, ahora)
                if delta > meta_5:
                    st.success("🌱 ¡Sostenés 5 días! Se está instalando un nuevo hábito.")
                    registrar_hito(nombre_evento, "5 días", fecha_inicio, ahora)
                if delta > meta_21:
                    st.success("🏗️ 21 días: ya creaste una estructura sólida.")
                    registrar_hito(nombre_evento, "21 días", fecha_inicio, ahora)

                if delta < umbral:
                    meta_actual = umbral
                    label_meta = "zona crítica (3 días)"
                elif delta < meta_5:
                    meta_actual = meta_5
                    label_meta = "meta base (5 días)"
                elif delta < meta_21:
                    meta_actual = meta_21
                    label_meta = "meta sólida (21 días)"
                elif delta < record:
                    meta_actual = record
                    label_meta = "tu récord"
                else:
                    meta_actual = delta
                    label_meta = "¡Nuevo récord!"

                progreso_visual = min(delta.total_seconds() / meta_actual.total_seconds(), 1.0)
                porcentaje_record = (delta.total_seconds() / record.total_seconds()) * 100

                registrar_log_visual(nombre_evento, label_meta, fecha_inicio, minutos, round(progreso_visual * 100, 1))

                st.markdown(f"🏅 **Récord personal:** `{record_str}`")
                st.markdown(f"📊 **Progreso hacia {label_meta}:** `{progreso_visual*100:.1f}%`")
                st.progress(progreso_visual)
                st.markdown(f"📈 **Progreso frente al récord:** `{porcentaje_record:.1f}%`")
        else:
            st.metric("Duración", "•••••• min", "••a ••m ••d ••h ••m ••s")
            st.caption("🔒 Información sensible oculta. Activá la casilla para visualizar.")
    else:
        st.metric("Duración", "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    total = len(eventos)
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos) else None
        diferencia = ""
        if anterior:
            detalle = relativedelta(fecha, anterior)
            diferencia = f"{detalle.years}a {detalle.months}m {detalle.days}d {detalle.hours}h {detalle.minutes}m"
        filas.append({
            "N°": total - i,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Duración sin caer": diferencia
        })
    return pd.DataFrame(filas)

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
        emociones = ", ".join([e["nombre"] for e in d.get("emociones", [])])
        rows.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Emociones": emociones,
            "Reflexión": d.get("reflexion", "")
        })
    return pd.DataFrame(rows)

def obtener_intentos():
    docs = list(coleccion_intentos.find({}).sort("fecha_hora", -1))
    filas = []
    for i, d in enumerate(docs):
        fecha = d["fecha_hora"].astimezone(colombia)
        filas.append({
            "N°": i+1,
            "Evento": d["evento"],
            "Decisión": d["decision"],
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
        })
    return pd.DataFrame(filas)

# === MÓDULO EVENTO ===
if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento: {seleccion}")
    fecha_hora_evento = datetime.now(colombia)

    if opcion == evento_a:
        st.subheader("🔐 Acceso a contenido sensible")

        if "decision_actual" not in st.session_state:
            st.session_state["decision_actual"] = None

        decision = st.radio("¿Querés ingresar?", ["Sí", "No"], horizontal=True, key="radio_decision")

        if st.button("Confirmar decisión"):
            registrar_intento(opcion, decision.lower(), datetime.now(colombia))
            st.session_state["decision_actual"] = decision
            if decision == "Sí":
                st.success("✅ Acceso autorizado")
            else:
                st.warning("⛔ Decidiste no ingresar. Quedó registrado tu rechazo.")

        if st.session_state.get("decision_actual") == "Sí":
            mostrar_racha(opcion, seleccion.split()[0])

    else:
        if st.button("☠️ ¿Registrar?"):
            registrar_evento(opcion, fecha_hora_evento)
            st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")
        mostrar_racha(opcion, seleccion.split()[0])

# === MÓDULO REFLEXIÓN ===
elif opcion == "reflexion":
    st.header("🧠 Registrar reflexión")

    if st.session_state.get("limpiar_reflexion"):
        st.session_state["texto_reflexion"] = ""
        st.session_state["emociones_reflexion"] = []
        st.session_state["limpiar_reflexion"] = False

    ultima = coleccion_reflexiones.find_one({}, sort=[("fecha_hora", -1)])
    if ultima:
        fecha = ultima["fecha_hora"].astimezone(colombia)
        st.caption(f"📌 Última registrada: {fecha.strftime('%Y-%m-%d %H:%M:%S')}")

    fecha_hora_reflexion = datetime.now(colombia)
    emociones_opciones = [
        "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
        "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
    ]
    emociones = st.multiselect("¿Cómo te sentías?", emociones_opciones, key="emociones_reflexion", placeholder="Seleccioná una o varias emociones")
    texto_reflexion = st.text_area("¿Querés dejar algo escrito?", height=150, key="texto_reflexion")

    puede_guardar = texto_reflexion.strip() or emociones
    if puede_guardar:
        if st.button("📝 Guardar reflexión"):
            guardar_reflexion(fecha_hora_reflexion, emociones, texto_reflexion)
            st.toast("🧠 Reflexión guardada", icon="💾")
            st.session_state["limpiar_reflexion"] = True
            st.rerun()
    st.markdown("<div style='margin-bottom: 300px;'></div>", unsafe_allow_html=True)

# === MÓDULO HISTORIAL COMPLETO ===
elif opcion == "historial":
    st.header("📑 Historial completo")
    tabs = st.tabs(["🧠 Reflexiones", "✊🏽 Iniciativa Aquella", "💸 Iniciativa de Pago", "🔐 Intentos de acceso"])

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
        # --- Portero integrado en la pestaña ---
        if "acceso_iniciativa_historial" not in st.session_state:
            st.session_state["acceso_iniciativa_historial"] = None

        if st.session_state["acceso_iniciativa_historial"] is None:
            st.markdown("🔐 Acceso a contenido sensible")
            decision = st.radio("¿Querés ingresar?", ["Sí", "No"], horizontal=True, key="radio_iniciativa_historial")
            if st.button("Confirmar decisión", key="btn_iniciativa_historial"):
                st.session_state["acceso_iniciativa_historial"] = decision
                registrar_intento(evento_a, decision.lower(), datetime.now(colombia))
                st.experimental_rerun()

        if st.session_state["acceso_iniciativa_historial"] == "Sí":
            mostrar_racha(evento_a, "✊🏽")
        elif st.session_state["acceso_iniciativa_historial"] == "No":
            st.warning("⛔ Decidiste no ingresar. Quedó registrado tu rechazo.")

        mostrar_tabla_eventos(evento_a)

    with tabs[2]:
        mostrar_tabla_eventos(evento_b)

    with tabs[3]:
        st.subheader("📍 Intentos de acceso a contenido sensible")
        df_i = obtener_intentos()
        st.dataframe(df_i, use_container_width=True, hide_index=True)
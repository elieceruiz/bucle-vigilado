import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI

# === CONFIGURACIÓN ===
st.set_page_config(page_title="Reinicia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_hitos = db["hitos"]
coleccion_visual = db["log_visual"]

# === OPENAI CLIENTE ===
openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# === DEFINICIONES DE EVENTO ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial completo": "historial",
    "✊🏽": evento_a,
    "💸": evento_b,
}

# === SISTEMA CATEGORIAL ===
sistema_categorial = {
    "1.1": {"categoria": "Dinámicas cotidianas", "subcategoria": "Organización del tiempo", "descriptor": "Cómo el sujeto distribuye y gestiona su tiempo en relación con sus prácticas sexuales e intimidad.", "observable": "Manejo de rutinas y distribución del día; relatos sobre horarios de trabajo, estudio, ocio y tiempo dedicado a la intimidad."},
    "1.2": {"categoria": "Dinámicas cotidianas", "subcategoria": "Relaciones sociales", "descriptor": "Interacciones y conexiones que influyen en las prácticas sexuales.", "observable": "Narraciones sobre aprobación o desaprobación de pareja, familiares, amigos."},
    "1.3": {"categoria": "Dinámicas cotidianas", "subcategoria": "Contextos de intimidad", "descriptor": "Espacios físicos, emocionales y simbólicos donde se desarrollan relaciones sexuales y afectivas.", "observable": "Lugares como casa, moteles, internet; condiciones de privacidad."},
    "1.4": {"categoria": "Dinámicas cotidianas", "subcategoria": "Factores emocionales", "descriptor": "Emociones y estados anímicos que acompañan las prácticas sexuales y la vida íntima.", "observable": "Estados afectivos vinculados, expresiones de ansiedad, deseo, culpa."},
    "2.1": {"categoria": "Consumo de sexo pago", "subcategoria": "Motivaciones", "descriptor": "Razones personales, sociales y económicas para consumir servicios sexuales pagados.", "observable": "Búsqueda de placer, compañía, evasión, curiosidad, necesidad de afecto."},
    "2.2": {"categoria": "Consumo de sexo pago", "subcategoria": "Prácticas asociadas", "descriptor": "Conductas, rituales y formas de interacción durante el consumo de sexo pago.", "observable": "Formas de acceso, frecuencia, monto pagado, modalidades y lugares."},
    "2.3": {"categoria": "Consumo de sexo pago", "subcategoria": "Representaciones", "descriptor": "Imágenes, discursos y estigmas sobre el sexo pago.", "observable": "Términos como tabú, normal, peligroso; narrativas de aceptación o estigma."},
    "2.4": {"categoria": "Consumo de sexo pago", "subcategoria": "Efectos en la trayectoria íntima", "descriptor": "Influencia en la evolución de la vida sexual y afectiva.", "observable": "Relatos de aprendizaje, arrepentimiento, gratificación."},
    "3.1": {"categoria": "Masturbación", "subcategoria": "Prácticas de autocuidado", "descriptor": "Uso de la masturbación como cuidado personal y bienestar emocional.", "observable": "Relatos sobre relajación, control del estrés, conciliación del sueño."},
    "3.2": {"categoria": "Masturbación", "subcategoria": "Placer y exploración del cuerpo", "descriptor": "Búsqueda de placer a través de la autoexploración corporal.", "observable": "Fantasías, técnicas usadas, experimentación, referencias a placer físico."},
    "3.3": {"categoria": "Masturbación", "subcategoria": "Relación con la intimidad", "descriptor": "Vínculo entre masturbación, privacidad y expresión del deseo.", "observable": "Rituales íntimos, momentos en soledad, ocultamiento social."},
    "3.4": {"categoria": "Masturbación", "subcategoria": "Representaciones culturales", "descriptor": "Creencias, tabúes y normas que afectan la aceptación social.", "observable": "Sentimientos de culpa, vergüenza, libertad; términos religiosos."},
}

# === ESTADO INICIAL ===
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({"evento": nombre_evento, "fecha_hora": fecha_hora})
    st.session_state[nombre_evento] = fecha_hora

def clasificar_reflexion_openai(texto_reflexion: str) -> str:
    prompt = f"""\
Sistema categorial para clasificar reflexiones:
1.1 Organización del tiempo
1.2 Relaciones sociales
1.3 Contextos de intimidad
1.4 Factores emocionales
2.1 Motivaciones
2.2 Prácticas asociadas
2.3 Representaciones
2.4 Efectos en la trayectoria íntima
3.1 Prácticas de autocuidado
3.2 Placer y exploración del cuerpo
3.3 Relación con la intimidad
3.4 Representaciones culturales
Por favor indica el código de la categoría/subcategoría que mejor describe esta reflexión:
Reflexión: \"\"\"{texto_reflexion}\"\"\"
Respuesta con sólo el código, por ejemplo: 1.4
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5,
    )
    return response.choices[0].message.content.strip()

def guardar_reflexion(fecha_hora, emociones, reflexion):
    categoria_auto = clasificar_reflexion_openai(reflexion)
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip(),
        "categoria_categorial": categoria_auto
    }
    coleccion_reflexiones.insert_one(doc)
    return categoria_auto

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
        emociones = ", ".join([e.get("nombre", "") for e in d.get("emociones", [])])
        cat_key = d.get("categoria_categorial", "")
        info = sistema_categorial.get(cat_key, {
            "categoria": "Sin categoría",
            "subcategoria": "Sin subcategoría",
            "descriptor": "No asignado",
            "observable": "No asignado",
        })
        rows.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Emociones": emociones,
            "Categoría": info["categoria"],
            "Subcategoría": info["subcategoria"],
            "Descriptor": info["descriptor"],
            "Observable": info["observable"],
            "Reflexión": d.get("reflexion", ""),
        })
    return pd.DataFrame(rows)

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
                record = max([(registros[i - 1]["fecha_hora"] - registros[i]["fecha_hora"]) for i in range(1, len(registros))], default=delta)
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

# === UI PRINCIPAL ===
st.title("Reinicia")
seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

# 🧹 Limpieza de estado al cambiar vista
if opcion != "reflexion":
    for key in ["texto_reflexion", "emociones_reflexion", "limpiar_reflexion", "📝 Guardar reflexión"]:
        st.session_state.pop(key, None)

# === MÓDULO EVENTO ===
if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento: {seleccion}")
    fecha_hora_evento = datetime.now(colombia)
    if st.button("☠️ ¿Registrar?"):
        registrar_evento(opcion, fecha_hora_evento)
        st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")
    mostrar_racha(opcion, seleccion.split()[0])

# === MÓDULO REFLEXIÓN ===
elif opcion == "reflexion":
    st.header("🧠 Registrar reflexión")
    ultima = coleccion_reflexiones.find_one({}, sort=[("fecha_hora", -1)])
    if ultima:
        st.caption(f"📌 Última registrada: {ultima['fecha_hora'].astimezone(colombia).strftime('%Y-%m-%d %H:%M:%S')}")
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
            categoria_asignada = guardar_reflexion(fecha_hora_reflexion, emociones, texto_reflexion)
            st.success(f"Reflexión guardada con categoría: {categoria_asignada}")
            st.session_state["limpiar_reflexion"] = True
            st.experimental_rerun()

# === MÓDULO HISTORIAL COMPLETO ===
elif opcion == "historial":
    st.header("📑 Historial completo")
    tabs = st.tabs(["🧠 Reflexiones", "✊🏽", "💸"])
    with tabs[0]:
        st.subheader("📍 Historial de reflexiones")
        df_r = obtener_reflexiones()
        for i, row in df_r.iterrows():
            with st.expander(f"{row['Fecha']} {row['Hora']} - {row['Categoría']} / {row['Subcategoría']}"):
                st.markdown(f"**Descriptor:** {row['Descriptor']}")
                st.markdown(f"**Observable:** {row['Observable']}")
                st.markdown(f"**Emociones:** {row['Emociones']}")
                st.markdown(f"**Reflexión:** {row['Reflexión']}")
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

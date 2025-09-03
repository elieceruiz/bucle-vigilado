import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI

# Configuración general y zona horaria local
st.set_page_config(page_title="Reinicia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# Traducción días semana para mostrar UI en español
dias_semana_es = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}
dias_semana_3letras = {
    0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"
}

# Conexión a MongoDB y definición de colecciones usadas
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_hitos = db["hitos"]
coleccion_visual = db["log_visual"]

# Cliente OpenAI configurado
openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# Constantes con nombres de eventos claves
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial completo": "historial",
    "✊🏽": evento_a,
    "💸": evento_b,
}

# Sistema categorial para clasificar reflexiones
sistema_categorial = {
    "1.1": {"categoria": "Dinámicas cotidianas", "subcategoria": "Organización del tiempo",
            "descriptor": "Manejo de rutinas y distribución del día",
            "observable": "Relatos sobre horarios de trabajo, estudio, momentos de ocio, tiempo dedicado a la intimidad."},
    # Resto omitido por brevedad
}

# Inicializa en session_state las últimas fechas de eventos para eventos clave
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# Función para obtener la categoría automática de la reflexión via OpenAI
def clasificar_reflexion_openai(texto_reflexion: str) -> str:
    prompt = f"""Sistema categorial para clasificar reflexiones:

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
Respuesta sólo con el código, ejemplo: 1.4
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5,
    )
    return response.choices[0].message.content.strip()

# Guarda la reflexión en la base con categoría automática
def guardar_reflexion(fecha_hora, emociones, reflexion):
    categoria_auto = clasificar_reflexion_openai(reflexion)
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip(),
        "categoria_categorial": categoria_auto if categoria_auto else ""
    }
    coleccion_reflexiones.insert_one(doc)
    return categoria_auto

# Inserta evento nuevo en base y actualiza session_state con rerun
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({"evento": nombre_evento, "fecha_hora": fecha_hora})
    st.session_state[nombre_evento] = fecha_hora
    st.rerun()

# Obtiene DataFrame de los registros formateados, con diferencia en "Sin recaída" en días, horas y minutos o "0"
def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos) else None

        if anterior:
            diff = fecha - anterior
            if diff.total_seconds() <= 0:
                diferencia = "0"
            else:
                dias = diff.days
                horas = (diff.seconds // 3600) % 24
                minutos = (diff.seconds % 3600) // 60
                diferencia = f"{dias}d {horas}h {minutos}m"
        else:
            diferencia = "0"

        dia_semana = dias_semana_3letras[fecha.weekday()]
        filas.append({
            "Día": dia_semana,
            "Fecha": fecha.strftime("%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Sin recaída": diferencia
        })
    return pd.DataFrame(filas)

# Obtiene las reflexiones almacenadas con detalles
def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
        emojis = " ".join([e["emoji"] for e in d.get("emociones", [])])
        emociones = ", ".join([e["nombre"] for e in d.get("emociones", [])])
        codigo_cat = d.get("categoria_categorial", "")
        info_cat = sistema_categorial.get(codigo_cat, {
            "categoria": "Sin categoría",
            "subcategoria": "",
            "descriptor": "",
            "observable": ""
        })
        rows.append({
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Emojis": emojis,
            "Emociones": emociones,
            "Categoría": info_cat["categoria"],
            "Subcategoría": info_cat["subcategoria"],
            "Descriptor": info_cat.get("descriptor", ""),
            "Observable": info_cat.get("observable", ""),
            "Reflexión": d.get("reflexion", "")
        })
    return pd.DataFrame(rows)

# Muestra cronómetro (racha) con actualización periódica solo si checkbox está activo
def mostrar_racha(nombre_evento, emoji):
    clave_estado = f"mostrar_racha_{nombre_evento}"
    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = False

    mostrar = st.checkbox("Ver/ocultar racha", key=f"check_{nombre_evento}")

    st.markdown("### ⏱️ Racha")

    if nombre_evento not in st.session_state:
        st.metric("Duración", "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")
        return

    if mostrar:
        st_autorefresh(interval=1000, limit=None, key=f"autorefresh_{nombre_evento}")

    ultimo = st.session_state[nombre_evento]
    ahora = datetime.now(colombia)
    delta = ahora - ultimo
    detalle = relativedelta(ahora, ultimo)
    minutos = int(delta.total_seconds() // 60)
    tiempo = f"{detalle.years}a {detalle.months}m {detalle.days}d {detalle.hours}h {detalle.minutes}m {detalle.seconds}s"
    dia = ultimo.strftime('%A')
    dia_es = dias_semana_es.get(dia, dia)

    if mostrar:
        st.metric("Duración", f"{minutos:,} min", tiempo)
        st.caption(f"🔴 Última recaída: {dia_es} {ultimo.strftime('%m-%d %H:%M:%S')}")

        if nombre_evento == evento_a:
            registros = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
            record = max([(registros[i - 1]["fecha_hora"] - registros[i]["fecha_hora"]) for i in range(1, len(registros))], default=delta) if len(registros) > 1 else delta
            total_dias = record.days
            horas = record.seconds // 3600
            minutos_rec = (record.seconds % 3600) // 60
            segundos = record.seconds % 60
            record_str = f"{total_dias} días, {horas:02d}:{minutos_rec:02d}:{segundos:02d}"

            umbral = timedelta(days=3)
            meta_5 = timedelta(days=5)
            meta_21 = timedelta(days=21)

            if delta > umbral:
                st.success("✅ Superaste la zona crítica de las 72 horas.")
            if delta > meta_5:
                st.success("🌱 ¡Sostenés 5 días! Se está instalando un nuevo hábito.")
            if delta > meta_21:
                st.success("🏗️ 21 días: ya creaste una estructura sólida.")

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

            st.markdown(f"🏅 **Récord personal:** `{record_str}`")
            st.markdown(f"📊 **Progreso hacia {label_meta}:** `{progreso_visual * 100:.1f}%`")
            st.progress(progreso_visual)
            st.markdown(f"📈 **Progreso frente al récord:** `{porcentaje_record:.1f}%`")

    else:
        st.metric("Duración", "•••••• min", "••a ••m ••d ••h ••m ••s")
        st.caption("🔒 Información sensible oculta. Activá la casilla para visualizar.")

# Mostrar tabla de registros con opción ocultar/mostrar
def mostrar_tabla_eventos(nombre_evento):
    st.subheader(f"📍 Registros")
    df = obtener_registros(nombre_evento)
    total_registros = len(df)

    def ocultar_numero_con_punticos(numero):
        return "•" * len(str(numero))

    mostrar = st.checkbox("Ver/Ocultar registros", value=False, key=f"mostrar_{nombre_evento}")
    total_mostrar = str(total_registros) if mostrar else ocultar_numero_con_punticos(total_registros)
    st.markdown(f"**Total de registros:** {total_mostrar}")

    if mostrar:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        df_oculto = pd.DataFrame({
            "Día": ["•••"] * total_registros,
            "Fecha": ["••-••-••"] * total_registros,
            "Hora": ["••:••"] * total_registros,
            "Sin recaída": ["••d ••h ••m"] * total_registros
        })
        st.dataframe(df_oculto, use_container_width=True, hide_index=True)
        st.caption("🔒 Registros ocultos. Activá la casilla para visualizar.")

# INTERFAZ PRINCIPAL
st.title("Reinicia")
seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

# Mostrar advertencias para recaídas en día actual
if opcion in [evento_a, evento_b]:
    dia_semana_hoy = dias_semana_es[datetime.now(colombia).strftime('%A')]
    df_registros = obtener_registros(opcion)
    df_dia = df_registros[df_registros["Día"] == dias_semana_3letras[datetime.now(colombia).weekday()]]
    recaidas_hoy = len(df_dia)
    if recaidas_hoy == 1:
        hora_unica = df_dia.iloc[0]["Hora"]
        st.error(f"❗ Atención: hay 1 recaída registrada para un día como hoy {dia_semana_hoy} a las {hora_unica}.")
    elif recaidas_hoy > 1:
        hora_min = df_dia["Hora"].min()
        hora_max = df_dia["Hora"].max()
        st.error(f"❗ Atención: hay {recaidas_hoy} recaídas registradas para un día como hoy {dia_semana_hoy} entre las {hora_min} y las {hora_max}.")
    else:
        st.success(f"Hoy es: {dia_semana_hoy}\n ➔ Recaídas: 0\n ➔ Sin registros para mostrar rango horario.")

if opcion != "reflexion":
    for key in ["texto_reflexion", "emociones_reflexion", "reset_reflexion"]:
        if key in st.session_state:
            del st.session_state[key]

if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento")
    fecha_hora_evento = datetime.now(colombia)

    if st.button("☠️ ¿Registrar?"):
        registrar_evento(opcion, fecha_hora_evento)
        st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")
        st.rerun()

    mostrar_racha(opcion, seleccion.split()[0])

elif opcion == "reflexion":
    st.header("🧠 Registrar reflexión")

    if st.session_state.get("reset_reflexion", False):
        st.session_state["texto_reflexion"] = ""
        st.session_state["emociones_reflexion"] = []
        st.session_state["reset_reflexion"] = False
        st.rerun()

    ultima = coleccion_reflexiones.find_one({}, sort=[("fecha_hora", -1)])
    if ultima:
        fecha = ultima["fecha_hora"].astimezone(colombia)
        st.caption(f"📌 Última registrada: {fecha.strftime('%d-%m-%y %H:%M:%S')}")

    fecha_hora_reflexion = datetime.now(colombia)

    emociones_opciones = [
        "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
        "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
    ]

    emociones = st.multiselect(
        "¿Cómo te sentías?",
        emociones_opciones,
        key="emociones_reflexion",
        placeholder="Seleccioná una o varias emociones"
    )
    texto_reflexion = st.text_area("¿Querés dejar algo escrito?", height=150, key="texto_reflexion")

    puede_guardar = texto_reflexion.strip() or emociones

    if puede_guardar:
        if st.button("📝 Guardar reflexión"):
            categoria_asignada = guardar_reflexion(fecha_hora_reflexion, emociones, texto_reflexion)
            st.success(f"Reflexión guardada con categoría: {categoria_asignada}")
            st.session_state["reset_reflexion"] = True
            st.rerun()

elif opcion == "historial":
    st.header("📑 Historial completo")
    tabs = st.tabs(["🧠 Reflexiones", "✊🏽", "💸"])

    with tabs[0]:
        st.subheader("📍 Historial de reflexiones")
        df_r = obtener_reflexiones()
        for i, row in df_r.iterrows():
            with st.expander(f"{row['Fecha']} {row['Emojis']} {row['Hora']}"):
                st.write(row['Reflexión'])
                st.markdown("---")
                st.write(f"**Estados de ánimo:** {row['Emociones']}")
                st.markdown(f"**Categoría:** {row['Categoría']}")
                st.markdown(f"**Subcategoría:** {row['Subcategoría']}")
                if row['Descriptor']:
                    st.markdown(f"**Descriptor:** {row['Descriptor']}")
                if row['Observable']:
                    st.markdown(f"**Observable:** {row['Observable']}")

    with tabs[1]:
        mostrar_tabla_eventos(evento_a)

    with tabs[2]:
        mostrar_tabla_eventos(evento_b)

# Función para mostrar tabla de eventos con opción de ocultar
def mostrar_tabla_eventos(nombre_evento):
    st.subheader(f"📍 Registros")
    df = obtener_registros(nombre_evento)
    total_registros = len(df)

    def ocultar_numero_con_punticos(numero):
        return "•" * len(str(numero))

    mostrar = st.checkbox("Ver/Ocultar registros", value=False, key=f"mostrar_{nombre_evento}")
    total_mostrar = str(total_registros) if mostrar else ocultar_numero_con_punticos(total_registros)
    st.markdown(f"**Total de registros:** {total_mostrar}")

    if mostrar:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        df_oculto = pd.DataFrame({
            "Día": ["•••"] * total_registros,
            "Fecha": ["••-••-••"] * total_registros,
            "Hora": ["••:••"] * total_registros,
            "Sin recaída": ["••d ••h ••m"] * total_registros
        })
        st.dataframe(df_oculto, use_container_width=True, hide_index=True)
        st.caption("🔒 Registros ocultos. Activá la casilla para visualizar.")

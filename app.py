import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI

# Configuración inicial de la página Streamlit
st.set_page_config(page_title="Reinicia", layout="centered")

# Zona horaria Colombia para manejo local de fechas
colombia = pytz.timezone("America/Bogota")

# Mapas de días para mostrar en español formato palabra y abreviado
dias_semana_es = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}
dias_semana_3letras = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}

# Conexión MongoDB (URI en secrets)
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# Cliente OpenAI configurado con API Key
openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# Definición nombres de eventos principales
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial completo": "historial",
    "✊🏽": evento_a,
    "💸": evento_b,
}

# Carga última fecha de eventos para poner en estado inicial
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        ultimo = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if ultimo:
            st.session_state[key] = ultimo["fecha_hora"].astimezone(colombia)

# Función para clasificar reflexión usando OpenAI
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

# Guardar reflexión en MongoDB y devolver categoría asignada
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

# Registrar evento en MongoDB y actualizar estado local con st.rerun()
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({"evento": nombre_evento, "fecha_hora": fecha_hora})
    st.session_state[nombre_evento] = fecha_hora
    st.rerun()  # Para refrescar app con nuevo estado

# Obtener DataFrame con registros de eventos desde MongoDB
def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos) else None
        diferencia = ""
        if anterior:
            detalle = relativedelta(fecha, anterior)
            partes = []
            for attr in ["years", "months", "days", "hours", "minutes"]:
                valor = getattr(detalle, attr)
                if valor:
                    partes.append(f"{valor}{attr[0]}")
            diferencia = " ".join(partes)
        dia_semana = dias_semana_3letras[fecha.weekday()]
        filas.append({
            "Día": dia_semana,
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Sin recaída": diferencia
        })
    return pd.DataFrame(filas)

# Obtener DataFrame con reflexiones desde MongoDB
def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
        emojis = " ".join([e["emoji"] for e in d.get("emociones", [])])
        emociones = ", ".join([e["nombre"] for e in d.get("emociones", [])])
        categoria = d.get("categoria_categorial", "")
        rows.append({
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Emojis": emojis,
            "Emociones": emociones,
            "Categoría": categoria,
            "Reflexión": d.get("reflexion", "")
        })
    return pd.DataFrame(rows)

# Función para mostrar cronómetro actualizado en tiempo real
def mostrar_racha(nombre_evento):
    clave_estado = "mostrar_racha"
    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = False

    # Checkbox controla mostrar/ocultar cronómetro
    mostrar = st.checkbox("Ver/ocultar racha", key=clave_estado)

    # Reservar espacio fijo para evitar cambios en diseño
    placeholder = st.empty()

    if nombre_evento not in st.session_state:
        placeholder.markdown("No hay evento registrado.")
        return

    inicio = st.session_state[nombre_evento]

    if mostrar:
        # Refresca la app cada 1 segundo para actualizar cronómetro
        st_autorefresh(interval=1000, key="refrescar_cronometro")

        delta = datetime.now(colombia) - inicio
        duracion_str = str(timedelta(seconds=int(delta.total_seconds())))

        # Actualiza solo el texto del cronómetro dentro del espacio reservado
        placeholder.markdown(f"### ⏱️ Tiempo transcurrido: {duracion_str}")
    else:
        delta = datetime.now(colombia) - inicio
        duracion_str = str(timedelta(seconds=int(delta.total_seconds())))
        placeholder.markdown(f"### ⏱️ Tiempo transcurrido (pausado): {duracion_str}")

# Mostrar tabla de eventos con control de visibilidad
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
            "Sin recaída": ["••a ••m ••d ••h ••m"] * total_registros
        })
        st.dataframe(df_oculto, use_container_width=True, hide_index=True)
        st.caption("🔒 Registros ocultos. Activá la casilla para visualizar.")

# INTERFAZ PRINCIPAL
st.title("Reinicia")
seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

# Mostrar advertencias según eventos el día actual
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

    mostrar_racha(opcion)

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
    with tabs[1]:
        mostrar_tabla_eventos(evento_a)
    with tabs[2]:
        mostrar_tabla_eventos(evento_b)

# Función para mostrar tabla de eventos con opción de ocultar registros
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
            "Sin recaída": ["••a ••m ••d ••h ••m"] * total_registros
        })
        st.dataframe(df_oculto, use_container_width=True, hide_index=True)
        st.caption("🔒 Registros ocultos. Activá la casilla para visualizar.")

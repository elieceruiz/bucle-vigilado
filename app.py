import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI
from math import sqrt
from collections import Counter

# Configuración de la página y zona horaria para Colombia
st.set_page_config(page_title="Reinicia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# Configuración y conexión a base de datos MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_hitos = db["hitos"]
coleccion_visual = db["log_visual"]

# Cliente OpenAI para clasificación automática de reflexiones
openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# Definición de eventos importantes que el sistema registrará
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial completo": "historial",
    "✊🏽": evento_a,
    "💸": evento_b,
}

# Sistema categorial estructurado para clasificar reflexiones de forma detallada
sistema_categorial = {
    "1.1": {"categoria": "Dinámicas cotidianas", "subcategoria": "Organización del tiempo",
            "descriptor": "Manejo de rutinas y distribución del día",
            "observable": "Relatos sobre horarios de trabajo, estudio, momentos de ocio, tiempo dedicado a la intimidad."},
    "1.2": {"categoria": "Dinámicas cotidianas", "subcategoria": "Relaciones sociales",
            "descriptor": "Interacciones que influyen en la vida íntima.",
            "observable": "Narraciones sobre pareja, amigos, familia; menciones de aprobación o desaprobación social."},
    "1.3": {"categoria": "Dinámicas cotidianas", "subcategoria": "Contextos de intimidad",
            "descriptor": "Espacios físicos y virtuales donde se desarrollan las prácticas.",
            "observable": "Lugares mencionados (casa, moteles, internet, calle), dispositivos usados, condiciones de privacidad."},
    "1.4": {"categoria": "Dinámicas cotidianas", "subcategoria": "Factores emocionales",
            "descriptor": "Estados afectivos vinculados al ejercicio de la sexualidad.",
            "observable": "Expresiones de soledad, ansiedad, deseo, satisfacción o culpa."},
    "2.1": {"categoria": "Consumo de sexo pago", "subcategoria": "Motivaciones",
            "descriptor": "Razones personales y sociales para pagar por sexo.",
            "observable": "Relatos de búsqueda de placer, compañía, evasión, curiosidad, necesidad de afecto."},
    "2.2": {"categoria": "Consumo de sexo pago", "subcategoria": "Prácticas asociadas",
            "descriptor": "Formas de acceder y realizar el consumo.",
            "observable": "Lugares (bares, calles, plataformas digitales), frecuencia, monto pagado, modalidades de encuentro."},
    "2.3": {"categoria": "Consumo de sexo pago", "subcategoria": "Representaciones",
            "descriptor": "Significados culturales y personales del sexo pago.",
            "observable": "Uso de términos como tabú, normal, peligroso, necesario, transgresión; narrativas de estigma o aceptación."},
    "2.4": {"categoria": "Consumo de sexo pago", "subcategoria": "Efectos en la trayectoria íntima",
            "descriptor": "Impacto en la experiencia personal y en la memoria íntima.",
            "observable": "Relatos de aprendizaje, arrepentimiento, culpa, gratificación, comparación con otras prácticas sexuales."},
    "3.1": {"categoria": "Masturbación", "subcategoria": "Prácticas de autocuidado",
            "descriptor": "Uso de la masturbación como estrategia de bienestar.",
            "observable": "Relatos sobre relajación, control del estrés, conciliación del sueño, cuidado de la salud sexual."},
    "3.2": {"categoria": "Masturbación", "subcategoria": "Placer y exploración del cuerpo",
            "descriptor": "Búsqueda de satisfacción personal y autoconocimiento.",
            "observable": "Narrativas sobre fantasías, técnicas usadas, experimentación, referencias a placer físico."},
    "3.3": {"categoria": "Masturbación", "subcategoria": "Relación con la intimidad",
            "descriptor": "Vínculo entre la masturbación y la privacidad del sujeto.",
            "observable": "Relatos de momentos en soledad, rituales íntimos, ocultamiento frente a otros."},
    "3.4": {"categoria": "Masturbación", "subcategoria": "Representaciones culturales",
            "descriptor": "Significados sociales y personales atribuidos a la masturbación.",
            "observable": "Expresiones de libertad, vergüenza, culpa, normalización; uso de términos religiosos o morales."},
}

# Inicializar en session_state los últimos eventos registrados para cada evento principal
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)


def mensaje_personalizado(nombre_evento):
    """Función para generar un mensaje sencillo y claro sobre riesgo de recaída,
    basado en todo el historial, días de la semana en que ha habido recaídas,
    rango horario común, y cantidad de registros."""
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}))
    total = len(eventos)
    if total == 0:
        return "No hay registros aún para evaluar riesgo.", "info"

    # Obtiene la frecuencia de recaídas por días de la semana
    dias = [ev["fecha_hora"].astimezone(colombia).weekday() for ev in eventos]
    cuenta_dias = Counter(dias)

    # Obtiene la frecuencia por hora del día
    horas = [ev["fecha_hora"].astimezone(colombia).hour for ev in eventos]
    cuenta_horas = Counter(horas)

    hoy = datetime.now(colombia).weekday()
    ahora = datetime.now(colombia).hour

    # Proporción histórica de recaídas en el día actual
    propor_dia = cuenta_dias[hoy] / total if hoy in cuenta_dias else 0

    # Definir rango horario típico entre percentiles 10 y 90 de horas de recaídas
    horas_ordenadas = sorted(horas)
    if len(horas_ordenadas) >= 10:
        idx_min = int(0.1 * len(horas_ordenadas))
        idx_max = int(0.9 * len(horas_ordenadas))
        hora_min = horas_ordenadas[idx_min]
        hora_max = horas_ordenadas[idx_max]
    else:
        hora_min = min(horas_ordenadas) if horas_ordenadas else 0
        hora_max = max(horas_ordenadas) if horas_ordenadas else 23

    # Genera un mensaje simple basado en la probabilidad y hora actual
    if propor_dia > 0.2 and (hora_min <= ahora <= hora_max):
        mensaje = "Alerta: hoy y en esta hora, según tu historial, la probabilidad de recaída es alta. ¡Cuidate mucho!"
        nivel = "error"
    elif propor_dia > 0.1:
        mensaje = "Precaución: hoy es un día con cierta probabilidad moderada de recaída según tu historial."
        nivel = "warning"
    else:
        mensaje = "Probabilidad baja de recaída hoy, seguí así."
        nivel = "success"

    return mensaje, nivel


def clasificar_reflexion_openai(texto_reflexion: str) -> str:
    """Clasifica una reflexión utilizando un prompt para modelo OpenAI en base al sistema categorial."""
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


def guardar_reflexion(fecha_hora, emociones, reflexion):
    """Guarda una reflexión en la colección de MongoDB junto con clasificación automática."""
    categoria_auto = clasificar_reflexion_openai(reflexion)
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip(),
        "categoria_categorial": categoria_auto if categoria_auto else ""
    }
    coleccion_reflexiones.insert_one(doc)
    return categoria_auto


def registrar_evento(nombre_evento, fecha_hora):
    """Registra un evento con fecha y hora en MongoDB y actualiza session_state."""
    coleccion_eventos.insert_one({"evento": nombre_evento, "fecha_hora": fecha_hora})
    st.session_state[nombre_evento] = fecha_hora


def mostrar_racha(nombre_evento, emoji):
    """Muestra la racha de días sin evento registrado, progreso y métricas con opción de ocultar."""
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

        dias_semana_es = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        dia = ultimo.strftime('%A')
        dia_es = dias_semana_es.get(dia, dia)

        if mostrar:
            st.metric("Duración", f"{minutos:,} min", tiempo)
            st.caption(f"🔴 Última recaída: {dia_es} {ultimo.strftime('%d-%m-%y %H:%M:%S')}")

            if nombre_evento == evento_a:
                registros = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
                record = max([(registros[i - 1]["fecha_hora"] - registros[i]["fecha_hora"])
                              for i in range(1, len(registros))], default=delta)
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
    else:
        st.metric("Duración", "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")


def obtener_registros(nombre_evento):
    """Obtiene registros ordenados de eventos y calcula intervalo entre ellos para mostrar en tabla."""
    letras_dia = {0: "L", 1: "M", 2: "X", 3: "J", 4: "V", 5: "S", 6: "D"}
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []

    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos) else None
        diferencia = ""

        if anterior:
            detalle = relativedelta(fecha, anterior)
            partes = []
            if detalle.years:
                partes.append(f"{detalle.years}a")
            if detalle.months:
                partes.append(f"{detalle.months}m")
            if detalle.days:
                partes.append(f"{detalle.days}d")
            if detalle.hours:
                partes.append(f"{detalle.hours}h")
            if detalle.minutes:
                partes.append(f"{detalle.minutes}m")
            diferencia = " ".join(partes)

        dia_semana = letras_dia[fecha.weekday()]

        filas.append({
            "Día": dia_semana,
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Sin recaída": diferencia
        })
    return pd.DataFrame(filas)


def obtener_reflexiones():
    """Extrae todas las reflexiones desde la base ordenadas y construye dataframe con su info categorial."""
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


def mostrar_tabla_eventos(nombre_evento):
    """Muestra la tabla con registros del evento seleccionado con opción de ocultar datos sensibles."""
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
            "Día": ["•"] * total_registros,
            "Fecha": ["••-••-••"] * total_registros,
            "Hora": ["••:••"] * total_registros,
            "Sin recaída": ["••a ••m ••d ••h ••m"] * total_registros
        })
        st.dataframe(df_oculto, use_container_width=True, hide_index=True)
        st.caption("🔒 Registros ocultos. Activá la casilla para visualizar.")


# Interfaz Principal de la aplicación
st.title("Reinicia")

seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

# Limpieza de estados para reflexión si no es el módulo actual seleccionado
if opcion != "reflexion":
    for key in ["texto_reflexion", "emociones_reflexion", "reset_reflexion"]:
        if key in st.session_state:
            del st.session_state[key]

# Módulo para registrar eventos importantes
if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento")
    fecha_hora_evento = datetime.now(colombia)

    # Muestra mensaje personalizado basado en historial para advertir riesgo
    mensaje, nivel = mensaje_personalizado(opcion)
    if nivel == "error":
        st.error(mensaje)
    elif nivel == "warning":
        st.warning(mensaje)
    else:
        st.success(mensaje)

    # Botón para registrar evento y reiniciar app para refrescar estado
    if st.button("☠️ ¿Registrar?"):
        registrar_evento(opcion, fecha_hora_evento)
        st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")
        st.rerun()

    # Mostrar racha con estadísticas y progreso
    mostrar_racha(opcion, seleccion.split()[0])

# Módulo para registrar reflexiones con emociones y texto
elif opcion == "reflexion":
    st.header("🧠 Registrar reflexión")

    # Limpieza y reinicio de estado para nueva reflexión
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

    # Botón para guardar reflexión y reiniciar app para refrescar estado
    if puede_guardar:
        if st.button("📝 Guardar reflexión"):
            categoria_asignada = guardar_reflexion(fecha_hora_reflexion, emociones, texto_reflexion)
            st.success(f"Reflexión guardada con categoría: {categoria_asignada}")
            st.session_state["reset_reflexion"] = True
            st.rerun()

# Módulo para mostrar historial completo de reflexiones y eventos
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

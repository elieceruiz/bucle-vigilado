# servicios.py

from datetime import datetime, timedelta
import pandas as pd
import requests

from config import colombia, EVENTO_B
from db import coleccion_capital_b
from helpers import minutos_a_tiempo_humano

import streamlit as st

# =========================
# PARSEAR COP
# =========================
def parsear_y_formatear_cop(valor_str):
    limpio = "".join(filter(str.isdigit, valor_str))
    if not limpio:
        return 0.00, "0,00"

    valor = int(limpio) / 100
    formateado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return valor, formateado


# =========================
# MINUTOS EVENTO B
# =========================
def obtener_minutos_evento_b():
    if EVENTO_B not in st.session_state:
        return 0

    inicio = st.session_state[EVENTO_B]
    ahora = datetime.now(colombia)

    return int((ahora - inicio).total_seconds() // 60)


# =========================
# HISTORIAL CAPITAL
# =========================
def obtener_historial_capital_b():
    registros = list(coleccion_capital_b.find().sort("fecha_registro", -1))

    filas = []

    for r in registros:
        fecha_reg = r["fecha_registro"].astimezone(colombia)
        fecha_fut = r["fecha_futura"].astimezone(colombia)

        filas.append({
            "Actual": fecha_reg.strftime("%d-%m-%y %H:%M"),
            "Adelantado": fecha_fut.strftime("%d-%m-%y %H:%M"),
            "COP": f"{r['monto']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        })

    return pd.DataFrame(filas)


# =========================
# YNAB API
# =========================
YNAB_TOKEN = st.secrets["ynab_token"]
YNAB_BUDGET_ID = st.secrets["ynab_budget_id"]

headers_ynab = {
    "Authorization": f"Bearer {YNAB_TOKEN}"
}


def obtener_capital_desde_ynab():
    url = f"https://api.youneedabudget.com/v1/budgets/{YNAB_BUDGET_ID}/categories"

    r = requests.get(url, headers=headers_ynab)

    if r.status_code != 200:
        return 0, 0, 0

    data = r.json()

    for grupo in data["data"]["category_groups"]:
        if grupo["name"] == "Savings":

            for cat in grupo["categories"]:
                if cat["name"] == "💜 1 min 1 COP 💸":

                    balance = cat["balance"] / 1000
                    target = (cat.get("goal_target") or 0) / 1000
                    progress = cat.get("goal_percentage_complete") or 0

                    return balance, target, progress

    return 0, 0, 0

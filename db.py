# db.py

import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def get_db():
    try:
        uri = st.secrets.get("mongo_uri")

        if not uri:
            return None, "❌ Falta mongo_uri en secrets"

        client = MongoClient(uri, serverSelectionTimeoutMS=5000)

        client.admin.command("ping")

        db = client["registro_bucle"]

        return db, None

    except Exception as e:
        return None, str(e)


db, error_db = get_db()

if db:
    coleccion_eventos = db["eventos"]
    coleccion_reflexiones = db["reflexiones"]
    coleccion_capital_b = db["capitalizacion_b"]
else:
    coleccion_eventos = None
    coleccion_reflexiones = None
    coleccion_capital_b = None
import streamlit as st
from pymongo import MongoClient

MONGO_URI = st.secrets.get("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["registro_bucle"]

coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_capital_b = db["capitalizacion_b"]
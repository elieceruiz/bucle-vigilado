# db.py

from pymongo import MongoClient
import streamlit as st

client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]

coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_capital_b = db["capitalizacion_b"]

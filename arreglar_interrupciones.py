from db import coleccion_eventos
from config import colombia

# traer registros ordenados
registros = list(
    coleccion_eventos.find({"evento": "interrupcion"})
    .sort("fecha_hora", 1)
)

anterior_fin = None

for r in registros:

    _id = r["_id"]
    inicio = r.get("inicio")
    fin = r.get("fin")

    gap = None

    # calcular gap correcto
    if anterior_fin and inicio:
        try:
            gap = int((inicio - anterior_fin).total_seconds() // 60)

            if gap < 0:
                gap = None
        except:
            gap = None

    # limpiar campo viejo
    coleccion_eventos.update_one(
        {"_id": _id},
        {"$unset": {"desde_anterior_min": ""}}
    )

    # guardar solo si es válido
    if gap is not None:
        coleccion_eventos.update_one(
            {"_id": _id},
            {"$set": {"desde_anterior_min": gap}}
        )

    # actualizar referencia
    if fin:
        anterior_fin = fin
    elif r.get("fecha_hora"):
        anterior_fin = r["fecha_hora"]

print("✔ Listo, datos corregidos")
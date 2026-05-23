from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

#os.environ para despliegue. Descomente cuando ya probó todo local.
#client = MongoClient(os.environ["MONGO_URI"])

# TODO: conectarse al cluster Admonsis  
# client = MongoClient("mongodb://<usuario>:<contraseña>@157.253.236.88:8087")
client = MongoClient("mongodb://ISIS2304I03202610:zRrlxLM4A0Vl@157.253.236.88:8087")
# TODO: conectarse a la base de datos Admonsis  
# = client["ISIS2304"]
db = client["ISIS2304I03202610"]
reseñas = db["reseñas"]

@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}

@app.get("/hoteles/{hotel_id}/reseñas")
def get_reseñas(hotel_id: int, orden: str = "fecha"):
    sort_field = "fecha_creacion" if orden == "fecha" else "votos_count"
    
    # Primero las destacadas, luego el resto ordenado
    resultado = list(reseñas.find(
        {"hotel_id": hotel_id, "estado": "publicada"},
        {"_id": 0}
    ).sort([("destacada", -1), (sort_field, -1)]))
    
    return resultado

@app.post("/hoteles/{hotel_id}/reseñas")
def crear_reseña(hotel_id: int, datos: dict):
    datos["hotel_id"] = hotel_id
    datos["fecha_creacion"] = datetime.now().isoformat()
    datos["estado"] = "publicada"
    datos["destacada"] = False
    datos["respuesta_admin"] = None
    datos["votos_count"] = 0
    datos["votantes"] = []
    reseñas.insert_one(datos)
    datos.pop("_id", None)
    return {"mensaje": "Reseña creada", "reseña": datos}

@app.put("/reseñas/{reserva_id}")
def editar_reseña(reserva_id: int, datos: dict):
    resultado = reseñas.update_one(
        {"reserva_id": reserva_id},
        {"$set": {
            "texto": datos.get("texto"),
            "calificacion": datos.get("calificacion")
        }}
    )
    if resultado.matched_count == 0:
        return {"error": "Reseña no encontrada"}
    return {"mensaje": "Reseña actualizada"}

@app.delete("/reseñas/{reserva_id}")
def eliminar_reseña(reserva_id: int):
    reseñas.update_one(
        {"reserva_id": reserva_id},
        {"$set": {"estado": "eliminada"}}
    )
    return {"mensaje": "Reseña eliminada"}

@app.post("/reseñas/{reserva_id}/voto")
def votar_reseña(reserva_id: int, datos: dict):
    cliente_id = datos.get("cliente_id")
    # Verificar que no haya votado antes
    reseña = reseñas.find_one({"reserva_id": reserva_id})
    if not reseña:
        return {"error": "Reseña no encontrada"}
    if cliente_id in reseña.get("votantes", []):
        return {"error": "Ya votaste esta reseña"}
    reseñas.update_one(
        {"reserva_id": reserva_id},
        {
            "$inc": {"votos_count": 1},
            "$push": {"votantes": cliente_id}
        }
    )
    return {"mensaje": "Voto registrado"}

@app.post("/reseñas/{reserva_id}/respuesta")
def responder_reseña(reserva_id: int, datos: dict):
    reseñas.update_one(
        {"reserva_id": reserva_id},
        {"$set": {
            "respuesta_admin": {
                "texto": datos.get("texto"),
                "fecha": datetime.now().isoformat(),
                "admin_id": datos.get("admin_id")
            }
        }}
    )
    return {"mensaje": "Respuesta guardada"}

@app.post("/reseñas/{reserva_id}/destacar")
def destacar_reseña(reserva_id: int, datos: dict):
    hotel_id = datos.get("hotel_id")
    # Quitar destacada anterior del mismo hotel
    reseñas.update_many(
        {"hotel_id": hotel_id},
        {"$set": {"destacada": False}}
    )
    # Destacar la nueva
    reseñas.update_one(
        {"reserva_id": reserva_id},
        {"$set": {"destacada": True}}
    )
    return {"mensaje": "Reseña destacada"}

@app.get("/clientes/{cliente_id}/reseñas")
def historial_reseñas(cliente_id: int, orden: str = "fecha"):
    sort_field = "fecha_creacion" if orden == "fecha" else "hotel_id"
    resultado = list(reseñas.find(
        {"cliente_id": cliente_id},
        {"_id": 0}
    ).sort(sort_field, -1))
    return resultado
# LOS RFC

@app.get("/rfc/top-hoteles")
def top_hoteles(fecha_inicio: str, fecha_fin: str):
    pipeline = [
        {"$match": {
            "estado": "publicada",
            "fecha_creacion": {"$gte": fecha_inicio, "$lte": fecha_fin}
        }},
        {"$group": {
            "_id": "$hotel_id",
            "calificacion_promedio": {"$avg": "$calificacion"},
            "total_reseñas": {"$sum": 1}
        }},
        {"$addFields": {
            "calificacion_promedio": {"$round": ["$calificacion_promedio", 2]}
        }},
        {"$sort": {"calificacion_promedio": -1}},
        {"$limit": 10},
        {"$project": {
            "_id": 0,
            "hotel_id": "$_id",
            "calificacion_promedio": 1,
            "total_reseñas": 1
        }}
    ]
    return list(reseñas.aggregate(pipeline))

@app.get("/rfc/evolucion/{hotel_id}")
def evolucion_hotel(hotel_id: int, año: int):
    fecha_inicio = f"{año}-01-01T00:00:00"
    fecha_fin = f"{año}-12-31T23:59:59"
    pipeline = [
        {"$match": {
            "hotel_id": hotel_id,
            "estado": "publicada",
            "fecha_creacion": {"$gte": fecha_inicio, "$lte": fecha_fin}
        }},
        {"$addFields": {
            "mes": {"$substr": ["$fecha_creacion", 5, 2]}
        }},
        {"$group": {
            "_id": "$mes",
            "calificacion_promedio": {"$avg": "$calificacion"},
            "total_reseñas": {"$sum": 1}
        }},
        {"$project": {
            "_id": 0,
            "mes": "$_id",
            "calificacion_promedio": {"$round": ["$calificacion_promedio", 2]},
            "total_reseñas": 1
        }},
        {"$sort": {"mes": 1}}
    ]
    return list(reseñas.aggregate(pipeline))

@app.get("/rfc/comparativo")
def comparativo_ciudad(hotel_ids: str):
    # hotel_ids llega como string separado por comas: "12,5,8,23"
    ids = [int(i) for i in hotel_ids.split(",")]
    pipeline = [
        {"$match": {
            "hotel_id": {"$in": ids},
            "estado": "publicada"
        }},
        {"$group": {
            "_id": "$hotel_id",
            "calificacion_promedio": {"$avg": "$calificacion"},
            "total_reseñas": {"$sum": 1},
            "con_respuesta": {"$sum": {"$cond": [{"$ne": ["$respuesta_admin", None]}, 1, 0]}},
            "destacadas": {"$sum": {"$cond": ["$destacada", 1, 0]}}
        }},
        {"$addFields": {
            "calificacion_promedio": {"$round": ["$calificacion_promedio", 2]},
            "pct_con_respuesta": {"$round": [
                {"$multiply": [{"$divide": ["$con_respuesta", "$total_reseñas"]}, 100]}, 1
            ]},
            "pct_destacadas": {"$round": [
                {"$multiply": [{"$divide": ["$destacadas", "$total_reseñas"]}, 100]}, 1
            ]}
        }},
        {"$project": {
            "_id": 0,
            "hotel_id": "$_id",
            "calificacion_promedio": 1,
            "total_reseñas": 1,
            "pct_con_respuesta": 1,
            "pct_destacadas": 1
        }},
        {"$sort": {"calificacion_promedio": -1}}
    ]
    return list(reseñas.aggregate(pipeline))
db.runCommand({
  collMod: "reseñas",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["hotel_id", "cliente_id", "reserva_id", "calificacion", "texto", "fecha_creacion", "estado"],
      properties: {
        hotel_id: {
          bsonType: "string",
         pattern: "^HOT[0-9]+$"
        },
        cliente_id: {
          bsonType: "string",
         pattern: "^USR[0-9]+$"
        },
        reserva_id: {
          bsonType: "string",
         pattern: "^RES[0-9]+$"
        },
        calificacion: {
          bsonType: "int",
          minimum: 1,
          maximum: 5,
        },
        texto: {
          bsonType: "string",
          minLength: 1,
        },
        fecha_creacion: {
          bsonType: "string",
        },
        estado: {
          bsonType: "string",
          enum: ["publicada", "eliminada"],
        },
        destacada: {
          bsonType: "bool",
        },
        respuesta_admin: {
          bsonType: ["object", "null"],
          properties: {
            texto: { bsonType: "string" },
            fecha: { bsonType: "string" },
            admin_id: { bsonType: "string"}
          },
        },
        votos_count: {
          bsonType: "int",
          minimum: 0,
        },
        votantes: {
          bsonType: "array",
          items: { bsonType: "string", pattern: "^USR[0-9]+$", },
        }
      }
    }
  },
})

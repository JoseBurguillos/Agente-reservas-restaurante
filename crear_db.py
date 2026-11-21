import sqlite3

conexion = sqlite3.connect("restaurante.db")   # abre el archivo (si no existe, lo crea)
cursor = conexion.cursor()

# 1. Crear la tabla (solo si no existe)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        dia TEXT NOT NULL,
        hora TEXT NOT NULL,
        personas INTEGER NOT NULL
    )
""")

# 2. Insertar las reservas de ejemplo
cursor.execute(
    "INSERT INTO reservas (nombre, dia, hora, personas) VALUES (?, ?, ?, ?)",
    ("Laura Martín", "viernes", "21:00", 2)
)
cursor.execute(
    "INSERT INTO reservas (nombre, dia, hora, personas) VALUES (?, ?, ?, ?)",
    ("Carlos Ruiz", "sábado", "14:00", 4)
)
cursor.execute(
    "INSERT INTO reservas (nombre, dia, hora, personas) VALUES (?, ?, ?, ?)",
    ("Marta López", "sábado", "21:30", 6)
)

conexion.commit()   # GUARDA los cambios (sin esto, no se guarda nada)
conexion.close()
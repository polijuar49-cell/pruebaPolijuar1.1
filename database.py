import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    """Inicializa la base de datos, crea las tablas y precarga datos iniciales."""
    conn = sqlite3.connect('productos.db')
    c = conn.cursor()
    
    # Crear tabla productos si no existe
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            descripcion TEXT NOT NULL,
            foto TEXT,
            precio REAL NOT NULL
        )
    ''')
    
    # Crear tabla usuarios si no existe
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('admin', 'user'))
        )
    ''')
    
    # Precargar usuarios si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_iniciales = [
            ('admin', generate_password_hash('admin123'), 'admin'),
            ('user', generate_password_hash('user123'), 'user')
        ]
        c.executemany(
            "INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
            usuarios_iniciales
        )
    
    # Precargar 5 productos si la tabla productos está vacía (con URLs de placeholders)
    c.execute("SELECT COUNT(*) FROM productos")
    if c.fetchone()[0] == 0:
        productos_iniciales = [
            ('VAS001', 'Vasos desechables de 200ml', 'https://via.placeholder.com/100x100/FF6B6B/FFFFFF?text=Vasos', 0.50),
            ('PLA001', 'Platos desechables redondos', 'https://via.placeholder.com/100x100/4ECDC4/FFFFFF?text=Platos', 0.30),
            ('SERV001', 'Paquete de servilletas desechables', 'https://via.placeholder.com/100x100/45B7D1/FFFFFF?text=Servilletas', 0.20),
            ('CUB001', 'Cubiertos plásticos desechables (tenedor, cuchillo, cuchara)', 'https://via.placeholder.com/100x100/96CEB4/FFFFFF?text=Cubiertos', 0.25),
            ('BOL001', 'Bolsas desechables para basura', 'https://via.placeholder.com/100x100/FECA57/FFFFFF?text=Bolsas', 0.15)
        ]
        c.executemany(
            "INSERT INTO productos (codigo, descripcion, foto, precio) VALUES (?, ?, ?, ?)",
            productos_iniciales
        )
    
    conn.commit()
    conn.close()

def get_connection():
    """Retorna una conexión a la base de datos."""
    return sqlite3.connect('productos.db')
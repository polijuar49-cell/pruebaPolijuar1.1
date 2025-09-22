from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import check_password_hash
import sqlite3
from datetime import datetime
import urllib.parse  # Para codificar mensaje de WhatsApp
import database

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret') 

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Clase Usuario para Flask-Login
class Usuario(UserMixin):
    def __init__(self, id, username, rol):
        self.id = id
        self.username = username
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    """Carga el usuario desde la DB por ID."""
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, rol FROM usuarios WHERE id=?", (user_id,))
    user_row = c.fetchone()
    conn.close()
    if user_row:
        return Usuario(user_row[0], user_row[1], user_row[2])
    return None

# Inicializar DB al arrancar la app
database.init_db()

def admin_required(f):
    """Decorator para requerir rol 'admin'."""
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso denegado. Solo administradores pueden realizar esta acción.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def user_required(f):
    """Decorator para requerir rol 'user' (para carrito)."""
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'user':
            flash('Acceso denegado. Esta función es solo para usuarios.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def inicializar_carrito():
    """Inicializa el carrito en sesión si no existe."""
    if 'carrito' not in session:
        session['carrito'] = []

@app.route('/')
@login_required
def index():
    """Lista todos los productos."""
    inicializar_carrito()
    total_items = sum(item['cantidad'] for item in session['carrito']) if session['carrito'] else 0
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos ORDER BY id")
    productos = c.fetchall()
    conn.close()
    return render_template('index.html', productos=productos, total_items=total_items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Formulario y procesamiento de login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = database.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, username, password, rol FROM usuarios WHERE username=?", (username,))
        user_row = c.fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row[2], password):
            user = Usuario(user_row[0], user_row[1], user_row[3])
            login_user(user)
            inicializar_carrito()  # Inicializar carrito al login
            flash(f'Bienvenido, {username}! ({user.rol})')
            return redirect(url_for('index'))
        else:
            flash('Credenciales inválidas. Intenta de nuevo.')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Cierra la sesión y limpia carrito."""
    session.pop('carrito', None)
    logout_user()
    flash('Sesión cerrada exitosamente.')
    return redirect(url_for('login'))

# Rutas CRUD (solo admin)
@app.route('/add', methods=['GET'])
@admin_required
def add():
    return render_template('add.html')

@app.route('/insert', methods=['POST'])
@admin_required
def insert():
    codigo = request.form['codigo']
    descripcion = request.form['descripcion']
    foto = request.form['foto']
    try:
        precio = float(request.form['precio'])
    except ValueError:
        flash('Error: El precio debe ser un número válido.')
        return redirect(url_for('add'))
    
    conn = database.get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO productos (codigo, descripcion, foto, precio) VALUES (?, ?, ?, ?)", (codigo, descripcion, foto, precio))
        conn.commit()
        flash('Producto agregado exitosamente.')
    except sqlite3.IntegrityError:
        flash('Error: El código ya existe. Debe ser único.')
    except Exception as e:
        flash(f'Error al agregar: {str(e)}')
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<codigo>', methods=['GET'])
@admin_required
def edit(codigo):
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE codigo=?", (codigo,))
    producto = c.fetchone()
    conn.close()
    if producto:
        return render_template('edit.html', producto=producto)
    flash('Producto no encontrado.')
    return redirect(url_for('index'))

@app.route('/update/<codigo>', methods=['POST'])
@admin_required
def update(codigo):
    descripcion = request.form['descripcion']
    foto = request.form['foto']
    try:
        precio = float(request.form['precio'])
    except ValueError:
        flash('Error: El precio debe ser un número válido.')
        return redirect(url_for('edit', codigo=codigo))
    
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("UPDATE productos SET descripcion=?, foto=?, precio=? WHERE codigo=?", (descripcion, foto, precio, codigo))
    if c.rowcount > 0:
        conn.commit()
        flash('Producto actualizado exitosamente.')
    else:
        flash('Producto no encontrado.')
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<codigo>')
@admin_required
def delete(codigo):
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM productos WHERE codigo=?", (codigo,))
    if c.rowcount > 0:
        conn.commit()
        flash('Producto eliminado exitosamente.')
    else:
        flash('Producto no encontrado.')
    conn.close()
    return redirect(url_for('index'))

# Rutas Carrito (solo user)
@app.route('/agregar_carrito/<int:producto_id>', methods=['POST'])
@user_required
def agregar_carrito(producto_id):
    inicializar_carrito()
    cantidad_str = request.form.get('cantidad')
    try:
        cantidad = int(cantidad_str)
        if cantidad < 1:
            flash('Error: La cantidad debe ser al menos 1.')
            return redirect(url_for('index'))
    except ValueError:
        flash('Error: La cantidad debe ser un número entero.')
        return redirect(url_for('index'))
    
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE id=?", (producto_id,))
    producto = c.fetchone()
    conn.close()
    
    if not producto:
        flash('Producto no encontrado.')
        return redirect(url_for('index'))
    
    # Buscar si ya existe en carrito (actualizar cantidad)
    for item in session['carrito']:
        if item['id'] == producto_id:
            item['cantidad'] += cantidad
            flash(f'Cantidad actualizada para {item["descripcion"]}: {item["cantidad"]} unidades.')
            session.modified = True
            return redirect(url_for('index'))
    
    # Agregar nuevo item
    item = {
        'id': producto[0],
        'codigo': producto[1],
        'descripcion': producto[2],
        'foto': producto[3],
        'precio': float(producto[4]),
        'cantidad': cantidad
    }
    session['carrito'].append(item)
    session.modified = True
    flash(f'Producto agregado: {producto[2]} (x{cantidad})')
    return redirect(url_for('index'))

@app.route('/carrito')
@user_required
def carrito():
    inicializar_carrito()
    total_items = sum(item['cantidad'] for item in session['carrito']) if session['carrito'] else 0
    total = sum(item['precio'] * item['cantidad'] for item in session['carrito'])
    return render_template('carrito.html', carrito=session['carrito'], total_items=total_items, total=total)

@app.route('/enviar_whatsapp')
@user_required
def enviar_whatsapp():
    inicializar_carrito()
    if not session['carrito']:
        flash('No hay items en el carrito.')
        return redirect(url_for('carrito'))
    
    # Formatear mensaje
    mensaje = f"Pedido de productos descartables - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    total = 0.0
    for item in session['carrito']:
        subtotal = item['precio'] * item['cantidad']
        mensaje += f"- {item['cantidad']} x {item['descripcion']}: S/ {subtotal:.2f}\n"
        total += subtotal
    mensaje += f"\nTotal a abonar: S/ {total:.2f}\n\n¡Gracias por tu pedido!"
    
    # Codificar y generar URL
    mensaje_codificado = urllib.parse.quote(mensaje)
    numero_whatsapp = "+543517594749"
    url_whatsapp = f"https://wa.me/{numero_whatsapp}?text={mensaje_codificado}"
    
    flash('¡Pedido enviado a WhatsApp! Revisa la app.')
    return redirect(url_whatsapp)

if __name__ == '__main__':
    # Replit (y muchos hosts) provee la variable de entorno PORT.
    port = int(os.environ.get('PORT', 5000))
    # host 0.0.0.0 para que Replit exponga la app públicamente
    app.run(host='0.0.0.0', port=port, debug=False)

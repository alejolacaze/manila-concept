import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
 
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///manila.db"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # Máximo 5MB por archivo
 
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static")
ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
 
db = SQLAlchemy(app)
 
# --- CREDENCIALES ADMIN (idealmente mover a variables de entorno) ---
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "manila2026"))
 
 
# --- MODELOS ---
 
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(500), nullable=False)
    talles = db.Column(db.String(50), nullable=False, default="S,M,L,XL")
 
 
with app.app_context():
    db.drop_all()
    db.create_all()
    if Producto.query.count() == 0:
        productos_iniciales = [
            Producto(nombre="Remera Boxy - Staff Members", precio=47500, imagen="boxy.jpeg", descripcion="Remera corte boxy fit de actitu street, con calce amplio y caida pesada. Confeccionada en algodon premium, pensada para bancarse el uso diario.", talles="S,M,L,XL"),
            Producto(nombre="Short - Logo Bear", precio=38000, imagen="short.jpeg", descripcion="Short de diseño minimalista, confeccionado en tejido suave y resistente, ideal para uso diario y tiempo libre. Presenta corte comodo y moderno, con terminaciones prolijas y un bordado lateral distintivo de la marca Manila con ilustración Bear.", talles="S,M,L,XL"),
            Producto(nombre="Remera Oversize - Summer 2025", precio=45000, imagen="remera.jpeg", descripcion="Remera de corte oversize pensada para un outfit relajado y actual. Confeccionada en algodón 20.1 premium de tacto suave, con una combinación de estampas DTG y detalles bordados.", talles="S,M,L,XL"),
            Producto(nombre="Musculosa Oversize - My Mum Says", precio=36000, imagen="musculosa.jpeg", descripcion="Musculosa de corte relajado confeccionada en algodón suave 20.1 premium, pensada para maxima comodidad y un look descontracturado.", talles="S,M,L,XL"),
        ]
        db.session.add_all(productos_iniciales)
        db.session.commit()
 
 
# --- HELPERS ---
 
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
 
def login_requerido(f):
    """Decorador para proteger rutas de admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Tenés que iniciar sesión para acceder al panel.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated
 
 
# --- RUTAS PÚBLICAS ---
 
@app.route("/")
def inicio():
    productos = Producto.query.all()
    carrito = session.get("carrito", [])
    return render_template("index.html", productos=productos, total_carrito=len(carrito))
 
@app.route("/producto/<int:id>")
def producto(id):
    item = db.session.get(Producto, id)
    if item is None:
        return render_template("404.html"), 404
    carrito = session.get("carrito", [])
    return render_template("producto.html", producto=item, total_carrito=len(carrito))
 
@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    mensaje_enviado = False
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        mensaje = request.form.get("mensaje", "").strip()
        if nombre and email and mensaje:
            # TODO: integrar Flask-Mail o SendGrid para envío real
            print(f"Mensaje de {nombre} ({email}): {mensaje}")
            mensaje_enviado = True
        else:
            flash("Por favor completá todos los campos.", "error")
    return render_template("contacto.html", mensaje_enviado=mensaje_enviado)
 
 
# --- CARRITO ---
 
@app.route("/agregar/<int:id>", methods=["POST"])
def agregar_carrito(id):
    item = db.session.get(Producto, id)
    if item is None:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("inicio"))
 
    talle = request.form.get("talle", "").strip()
    if not talle:
        flash("Seleccioná un talle antes de agregar al carrito.", "error")
        return redirect(url_for("producto", id=id))
 
    carrito = session.get("carrito", [])
    # Buscar si ya existe el mismo producto con el mismo talle
    for item_carrito in carrito:
        if item_carrito["id"] == id and item_carrito["talle"] == talle:
            item_carrito["cantidad"] += 1
            break
    else:
        carrito.append({"id": id, "talle": talle, "cantidad": 1})
 
    session["carrito"] = carrito
    session.modified = True
    return redirect(url_for("inicio"))
 
@app.route("/carrito")
def carrito():
    items_carrito = session.get("carrito", [])
    productos_carrito = []
    total = 0
    for entry in items_carrito:
        p = db.session.get(Producto, entry["id"])
        if p:
            subtotal = p.precio * entry["cantidad"]
            total += subtotal
            productos_carrito.append({
                "producto": p,
                "talle": entry["talle"],
                "cantidad": entry["cantidad"],
                "subtotal": subtotal,
            })
    return render_template("carrito.html", productos=productos_carrito, total=total)
 
@app.route("/eliminar-carrito/<int:index>")
def eliminar_carrito(index):
    carrito = session.get("carrito", [])
    if 0 <= index < len(carrito):
        carrito.pop(index)
    session["carrito"] = carrito
    session.modified = True
    return redirect(url_for("carrito"))
 
@app.route("/vaciar-carrito")
def vaciar_carrito():
    session["carrito"] = []
    return redirect(url_for("carrito"))
 
 
# --- ADMIN: LOGIN ---
 
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("admin_login.html")
 
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("inicio"))
 
 
# --- ADMIN: PANEL ---
 
@app.route("/admin")
@login_requerido
def admin():
    productos = Producto.query.all()
    return render_template("admin.html", productos=productos)
 
@app.route("/admin/editar/<int:id>", methods=["GET", "POST"])
@login_requerido
def editar(id):
    item = db.session.get(Producto, id)
    if item is None:
        return render_template("404.html"), 404
    if request.method == "POST":
        item.nombre = request.form.get("nombre", "").strip()
        item.descripcion = request.form.get("descripcion", "").strip()
        item.imagen = request.form.get("imagen", item.imagen).strip()
        try:
            item.precio = int(request.form["precio"])
        except (ValueError, KeyError):
            flash("El precio debe ser un número válido.", "error")
            return render_template("editar.html", producto=item)
        db.session.commit()
        flash("Producto actualizado correctamente.", "success")
        return redirect(url_for("admin"))
    return render_template("editar.html", producto=item)
 
@app.route("/admin/eliminar/<int:id>")
@login_requerido
def eliminar(id):
    item = db.session.get(Producto, id)
    if item is None:
        return render_template("404.html"), 404
    db.session.delete(item)
    db.session.commit()
    flash("Producto eliminado.", "success")
    return redirect(url_for("admin"))
 
@app.route("/admin/agregar", methods=["GET", "POST"])
@login_requerido
def agregar():
    if request.method == "POST":
        archivo = request.files.get("imagen")
        if archivo and allowed_file(archivo.filename):
            filename = secure_filename(archivo.filename)
            archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        else:
            filename = "placeholder.jpeg"
 
        try:
            precio = int(request.form["precio"])
        except (ValueError, KeyError):
            flash("El precio debe ser un número válido.", "error")
            return render_template("agregar.html")
 
        nuevo = Producto(
            nombre=request.form.get("nombre", "").strip(),
            precio=precio,
            imagen=filename,
            descripcion=request.form.get("descripcion", "").strip(),
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Producto agregado correctamente.", "success")
        return redirect(url_for("admin"))
    return render_template("agregar.html")
 
 
if __name__ == "__main__":
    app.run(debug=True)
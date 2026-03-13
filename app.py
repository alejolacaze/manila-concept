import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "manila2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///manila.db"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static")
ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(500), nullable=False)
    talles = db.Column(db.String(50), nullable=False, default="S,M,L,XL")

with app.app_context():
    db.create_all()
    if Producto.query.count() == 0:
        productos_iniciales = [
            Producto(nombre="Remera Boxy - Staff Members", precio=47500, imagen="boxy.jpeg", descripcion="Remera corte boxy fit de actitu street, con calce amplio y caida pesada. Confeccionada en algodon premium, pensada para bancarse el uso diario."),
            Producto(nombre="Short - Logo Bear", precio=38000, imagen="short.jpeg", descripcion="Short de diseño minimalista, confeccionado en tejido suave y resistente, ideal para uso diario y tiempo libre. Presenta corte comodo y moderno, con terminaciones prolijas y un bordado lateral distintivo de la marca Manila con ilustración Bear."),
            Producto(nombre="Remera Oversize - Summer 2025", precio=45000, imagen="remera.jpeg", descripcion="Remera de corte oversize pensada para un outfit relajado y actual. Confeccionada en algodón 20.1 premium de tacto suave, ocn una combinación de estampas DTG y detalles bordados."),
            Producto(nombre="Musculosa Oversize - My Mum Says", precio=36000, imagen="musculosa.jpeg", descripcion="Musculosa de corte relajado confeccionada en algodón suave 20.1 premium, pensada para maxima comodidad y un look descontracturado."),
        ]
        db.session.add_all(productos_iniciales)
        db.session.commit()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def inicio():
    productos = Producto.query.all()
    carrito = session.get("carrito", [])
    return render_template("index.html", productos=productos, total_carrito=len(carrito))

@app.route("/producto/<int:id>")
def producto(id):
    item = Producto.query.get_or_404(id)
    carrito = session.get("carrito", [])
    return render_template("producto.html", producto=item, total_carrito=len(carrito))

@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    mensaje_enviado = False
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        mensaje = request.form["mensaje"]
        print(f"Mensaje de {nombre} ({email}): {mensaje}")
        mensaje_enviado = True
    return render_template("contacto.html", mensaje_enviado=mensaje_enviado)

# --- CARRITO ---

@app.route("/agregar/<int:id>")
def agregar_carrito(id):
    carrito = session.get("carrito", [])
    carrito.append(id)
    session["carrito"] = carrito
    return redirect(url_for("inicio"))

@app.route("/carrito")
def carrito():
    ids = session.get("carrito", [])
    productos = [Producto.query.get(id) for id in ids]
    total = sum(p.precio for p in productos if p)
    return render_template("carrito.html", productos=productos, total=total)

@app.route("/eliminar-carrito/<int:index>")
def eliminar_carrito(index):
    carrito = session.get("carrito", [])
    if 0 <= index < len(carrito):
        carrito.pop(index)
    session["carrito"] = carrito
    return redirect(url_for("carrito"))

@app.route("/vaciar-carrito")
def vaciar_carrito():
    session["carrito"] = []
    return redirect(url_for("carrito"))

# --- ADMIN ---

@app.route("/admin")
def admin():
    productos = Producto.query.all()
    return render_template("admin.html", productos=productos)

@app.route("/admin/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    item = Producto.query.get_or_404(id)
    if request.method == "POST":
        item.nombre = request.form["nombre"]
        item.precio = request.form["precio"]
        item.imagen = request.form["imagen"]
        item.descripcion = request.form["descripcion"]
        db.session.commit()
        return redirect(url_for("admin"))
    return render_template("editar.html", producto=item)

@app.route("/admin/eliminar/<int:id>")
def eliminar(id):
    item = Producto.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        archivo = request.files.get("imagen")
        if archivo and allowed_file(archivo.filename):
            filename = secure_filename(archivo.filename)
            archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        else:
            filename = "placeholder.jpeg"

        nuevo = Producto(
            nombre=request.form["nombre"],
            precio=request.form["precio"],
            imagen=filename,
            descripcion=request.form["descripcion"]
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for("admin"))
    return render_template("agregar.html")

if __name__ == "__main__":
    app.run(debug=True)
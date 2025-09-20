import sqlite3
import os
from flask import Flask, request, jsonify, session, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path("data.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["JSON_AS_ASCII"] = False


def init_db():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
        """
        )
        con.commit()


def get_user_by_username(username: str):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario = ?", (username,))
        return cur.fetchone()


@app.post("/registro")
def registro():
    data = request.get_json(silent=True) or {}
    usuario = data.get("usuario", "").strip()
    contrasena = (
        data.get("contraseña") or data.get("contrasena") or data.get("password")
    )
    if not usuario or not contrasena:
        return (
            jsonify(error="Solicitud inválida, se requieren 'usuario' y 'contraseña'."),
            400,
        )

    if get_user_by_username(usuario):
        return jsonify(error="Usuario ya registrado."), 409

    password_hash = generate_password_hash(contrasena)
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
            (usuario, password_hash),
        )
        con.commit()

    return jsonify(message="Registro exitoso."), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    usuario = data.get("usuario", "").strip()
    contrasena = (
        data.get("contraseña") or data.get("contrasena") or data.get("password")
    )
    row = get_user_by_username(usuario)
    if not row or not check_password_hash(row["password_hash"], contrasena):
        return jsonify(error="Credenciales inválidas."), 401

    session["user_id"] = row["id"]
    session["usuario"] = row["usuario"]
    return jsonify(message="Login exitoso."), 200


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


def login_required():
    return "user_id" in session


@app.get("/tareas")
def tareas():
    if not login_required():
        return render_template("unauthorized.html", logged_in=False), 401
    return render_template(
        "tareas.html", usuario=session.get("usuario"), logged_in=True
    )


@app.get("/")
def root():
    if login_required():
        return redirect("/tareas")
    return render_template("home.html", logged_in=login_required())


@app.get("/login_home")
def login_home_form():
    return render_template("login.html", logged_in=login_required())


@app.post("/login_home")
def login_home_submit():
    usuario = request.form.get("usuario", "").strip()
    contrasena = request.form.get("contraseña", "")
    row = get_user_by_username(usuario)
    if not row or not check_password_hash(row["password_hash"], contrasena):
        return render_template("unauthorized.html"), 401
    session["user_id"] = row["id"]
    session["usuario"] = row["usuario"]
    return redirect("/tareas")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)

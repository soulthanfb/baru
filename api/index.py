from flask import Flask, request, jsonify, render_template_string, session, redirect
from supabase import create_client
import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("sb_secret_6_L3yoF7V21-8xVkrjkoog_Pa-wldbA", "default-secret")

# ======================
# SUPABASE CONFIG
# ======================
SUPABASE_URL = os.environ.get("https://lmcxzdumzyvgobjpqopr.supabase.co")
SUPABASE_KEY = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3h6ZHVtenl2Z29ianBxb3ByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NTM0MjIsImV4cCI6MjA4MTUyOTQyMn0.9F3aqni686QeiLE3z3NtpOBfyIkLVjI93gaA3ejYwOw")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# HEARTBEAT
# ======================
last_heartbeat_time = None

# ======================
# HTML
# ======================

LOGIN_HTML = """
<h2>Login Admin</h2>
<form method="POST">
<input name="email" placeholder="Email" required><br><br>
<input type="password" name="password" placeholder="Password" required><br><br>
<button>Login</button>
</form>
<p>
<a href="/register">Register</a> |
<a href="/forgot">Lupa Password</a>
</p>
"""

REGISTER_HTML = """
<h2>Register Admin</h2>
<form method="POST">
<input name="email" placeholder="Email" required><br><br>
<input type="password" name="password" placeholder="Password" required><br><br>
<button>Register</button>
</form>
<a href="/login">Login</a>
"""

FORGOT_HTML = """
<h2>Lupa Password</h2>
<form method="POST">
<input name="email" placeholder="Email" required><br><br>
<button>Kirim Reset Link</button>
</form>
<a href="/login">Login</a>
"""

DASHBOARD_HTML = """
<h2>Dashboard Admin RFID</h2>
<a href="/logout">Logout</a>
<hr>
<form method="POST" action="/api/register">
UID: <input name="uid" required><br><br>
Nama: <input name="nama" required><br><br>
<button>Simpan</button>
</form>
"""

# ======================
# AUTH
# ======================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            res = supabase.auth.sign_in_with_password({
                "email": request.form["email"],
                "password": request.form["password"]
            })
            session["admin"] = res.user.id
            return redirect("/")
        except:
            return "Login gagal"
    return render_template_string(LOGIN_HTML)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        supabase.auth.sign_up({
            "email": request.form["email"],
            "password": request.form["password"]
        })
        return "Registrasi berhasil, cek email"
    return render_template_string(REGISTER_HTML)


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        supabase.auth.reset_password_email(request.form["email"])
        return "Link reset dikirim"
    return render_template_string(FORGOT_HTML)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def dashboard():
    if "admin" not in session:
        return redirect("/login")
    return render_template_string(DASHBOARD_HTML)

# ======================
# RFID API
# ======================

@app.route("/api/ping", methods=["GET", "POST"])
def ping():
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()
    return jsonify({"pong": True})


@app.route("/api/register", methods=["POST"])
def register_card():
    if "admin" not in session:
        return "Unauthorized", 403

    supabase.table("users").upsert({
        "uid": request.form["uid"].upper(),
        "nama": request.form["nama"]
    }).execute()

    return "UID tersimpan"


@app.route("/api/akses", methods=["POST"])
def akses():
    uid = request.json.get("uid")

    user = supabase.table("users").select("*").eq("uid", uid).execute()
    if not user.data:
        return jsonify({"akses": False}), 403

    last = supabase.table("logs").select("status").eq("uid", uid).order("id", desc=True).limit(1).execute()
    status = "Masuk" if not last.data or last.data[0]["status"] == "Keluar" else "Keluar"

    supabase.table("logs").insert({
        "uid": uid,
        "nama": user.data[0]["nama"],
        "status": status,
        "waktu": datetime.datetime.now().isoformat()
    }).execute()

    return jsonify({"akses": True, "status": status})

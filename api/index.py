from flask import Flask, request, jsonify, render_template_string, session, redirect
from supabase import create_client
import datetime

app = Flask(__name__)
app.secret_key = "GANTI_SECRET_KEY_KAMU"

# ======================
# SUPABASE CONFIG
# ======================
SUPABASE_URL = "https://lmcxzdumzyvgobjpqopr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3h6ZHVtenl2Z29ianBxb3ByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NTM0MjIsImV4cCI6MjA4MTUyOTQyMn0.9F3aqni686QeiLE3z3NtpOBfyIkLVjI93gaA3ejYwOw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# HEARTBEAT
# ======================
last_heartbeat_time = None

# ======================
# TEMPLATE LOGIN
# ======================
LOGIN_HTML = """
<h2>Login Admin</h2>
<form method="POST">
  <input name="email" placeholder="Email" required><br><br>
  <input type="password" name="password" placeholder="Password" required><br><br>
  <button>Login</button>
</form>
<a href="/register">Register</a> | <a href="/forgot">Lupa Password</a>
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
  <button>Kirim Link Reset</button>
</form>
<a href="/login">Login</a>
"""

# ======================
# DASHBOARD (RFID)
# ======================
DASHBOARD_HTML = """
<h2>Dashboard RFID</h2>
<a href="/logout">Logout</a>
<hr>
<form action="/api/register" method="POST">
  UID: <input name="uid" required>
  Nama: <input name="nama" required>
  <button>Simpan</button>
</form>
"""

# ======================
# AUTH ROUTES
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            session["admin"] = res.user.id
            return redirect("/")
        except:
            return "Login gagal"

    return render_template_string(LOGIN_HTML)


@app.route("/register", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        return "Registrasi berhasil, cek email"

    return render_template_string(REGISTER_HTML)


@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        supabase.auth.reset_password_email(email)
        return "Link reset dikirim ke email"

    return render_template_string(FORGOT_HTML)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ======================
# PROTECTED DASHBOARD
# ======================
@app.route("/")
def dashboard():
    if "admin" not in session:
        return redirect("/login")
    return render_template_string(DASHBOARD_HTML)

# ======================
# RFID & API (TETAP)
# ======================
@app.route("/api/ping", methods=["POST", "GET"])
def ping():
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()
    return jsonify({"pong": True})


@app.route("/api/status-alat")
def status_alat():
    if not last_heartbeat_time:
        return jsonify({"status": "OFFLINE"})

    delta = (datetime.datetime.now() - last_heartbeat_time).total_seconds()
    return jsonify({"status": "ONLINE" if delta < 10 else "OFFLINE"})


@app.route("/api/register", methods=["POST"])
def register_card():
    if "admin" not in session:
        return "Unauthorized", 403

    uid = request.form["uid"].upper()
    nama = request.form["nama"]
    supabase.table("users").upsert({
        "uid": uid,
        "nama": nama
    }).execute()
    return "Berhasil simpan UID"


@app.route("/api/akses", methods=["POST"])
def cek_akses():
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()

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


# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

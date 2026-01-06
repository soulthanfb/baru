from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, flash
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)

# --- KONFIGURASI PENTING ---
app.secret_key = "rahasia_negara_super_aman" 
MASTER_KEY = "admin123" 

# --- KONFIGURASI SUPABASE ---
SUPABASE_URL = "https://lmcxzdumzyvgobjpqopr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3h6ZHVtenl2Z29ianBxb3ByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NTM0MjIsImV4cCI6MjA4MTUyOTQyMn0.9F3aqni686QeiLE3z3NtpOBfyIkLVjI93gaA3ejYwOw" 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- VARIABEL STATE (JEMBATAN ARDUINO & WEB) ---
last_heartbeat_time = None

# Variable ini menyimpan status apakah alat boleh aktif atau tidak
# Default: False (Terkunci)
DEVICE_STATE = {
    "active": False,
    "operator": ""
}

# ==========================================
#  BAGIAN DESAIN HTML (CSS & TEMPLATE)
# ==========================================

COMMON_STYLE = """
<style>
    body { font-family: 'Poppins', sans-serif; background: linear-gradient(120deg, #84fab0 0%, #8fd3f4 100%); min-height: 100vh; margin: 0; display: flex; align-items: center; justify-content: center; color: #444; }
    .card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
    h2 { color: #333; margin-bottom: 20px; }
    input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    button { width: 100%; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 10px; transition: 0.3s; }
    .btn-primary { background: #00c6ff; color: white; background: linear-gradient(to right, #00c6ff, #0072ff); }
    .btn-primary:hover { transform: scale(1.02); }
    .btn-secondary { background: #f0f0f0; color: #555; margin-top: 10px; display: inline-block; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; }
    .alert { padding: 10px; background: #ffcccc; color: #cc0000; border-radius: 5px; margin-bottom: 15px; font-size: 14px; }
    .success { background: #d4edda; color: #155724; }
    .links { margin-top: 20px; font-size: 14px; }
    .links a { color: #0072ff; text-decoration: none; margin: 0 5px; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
"""

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
    """ + COMMON_STYLE + """
</head>
<body>
    <div class="card">
        <h2>{{ title }}</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            
            {% if mode == 'reset' %}
                <input type="text" name="master_key" placeholder="Masukkan Master Key" required>
            {% endif %}

            <input type="password" name="password" placeholder="{% if mode == 'reset' %}Password Baru{% else %}Password{% endif %}" required>
            
            <button type="submit" class="btn-primary">
                {% if mode == 'login' %} MASUK {% elif mode == 'register' %} DAFTAR {% else %} UBAH PASSWORD {% endif %}
            </button>
        </form>

        <div class="links">
            {% if mode == 'login' %}
                <a href="/register">Buat Akun</a> | <a href="/reset">Lupa Password?</a>
            {% elif mode == 'register' %}
                Already have account? <a href="/login">Login</a>
            {% else %}
                <a href="/login">Kembali ke Login</a>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard Garasi</title>
    """ + COMMON_STYLE + """
    <style>
        .card { max-width: 900px; padding: 30px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .logout-btn { background: #ff4757; color: white; text-decoration: none; padding: 8px 15px; border-radius: 5px; font-size: 14px; }
        
        .status-bar { background: #f8f9fa; padding: 10px 20px; border-radius: 50px; display: inline-flex; align-items: center; gap: 10px; font-weight: 600; font-size: 14px; margin-bottom: 20px; }
        .status-indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
        .st-offline { background-color: #ff4757; box-shadow: 0 0 8px #ff4757; }
        .st-online { background-color: #2ed573; box-shadow: 0 0 8px #2ed573; }

        .container-grid { display: grid; grid-template-columns: 1fr; gap: 30px; text-align: left; }
        .form-section { border-bottom: 1px dashed #ccc; padding-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; }
        th { background: #f1f1f1; color: #555; }
        .badge { padding: 4px 10px; border-radius: 20px; color: white; font-size: 12px; }
        .bg-green { background: #28a745; } .bg-red { background: #dc3545; }
        
        @media (min-width: 768px) { .container-grid { grid-template-columns: 1fr 1.5fr; border-bottom: none; } .form-section { border-bottom: none; border-right: 1px dashed #ccc; padding-right: 30px; } }
    </style>
</head>
<body>

    <div class="card">
        <div class="header">
            <h3>Hi, {{ username }}! 👋</h3>
            <a href="/logout" class="logout-btn">Keluar</a>
        </div>

        <div style="text-align: left;">
            <div class="status-bar">
                <span id="statusDot" class="status-indicator st-offline"></span>
                <span id="statusText">Menunggu WiFi...</span>
            </div>
            <div class="status-bar">
                <span class="status-indicator st-online"></span>
                <span style="color:#2ed573">Mode Kontrol: AKTIF (Unlock)</span>
            </div>
        </div>

        <div class="container-grid">
            <div class="form-section">
                <h4>Tambah Kartu Baru</h4>
                <div style="background:#e3f2fd; color:#0d47a1; padding:10px; border-radius:8px; font-size:13px; margin-bottom:15px;">
                    📡 Tempelkan kartu di alat, UID otomatis muncul.
                </div>
                <form action="/api/register" method="POST">
                    <label>UID Kartu</label>
                    <input type="text" id="uidField" name="uid" placeholder="Menunggu scan..." required readonly>
                    <label>Nama Pemilik</label>
                    <input type="text" name="nama" placeholder="Contoh: Budi" required>
                    <button type="submit" class="btn-primary">Simpan Data</button>
                </form>
            </div>

            <div>
                <h4>Riwayat Akses</h4>
                <div style="overflow-x:auto;">
                    <table>
                        <thead><tr><th>Waktu</th><th>Nama / UID</th><th>Status</th></tr></thead>
                        <tbody id="logTableBody"><tr><td colspan="3" style="text-align:center;">Memuat...</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function updateStatus() {
            try {
                let res = await fetch('/api/status-alat');
                let data = await res.json();
                let dot = document.getElementById('statusDot');
                let text = document.getElementById('statusText');
                if(data.status === 'ONLINE'){
                    dot.className = 'status-indicator st-online'; text.innerText = 'Alat Terhubung'; text.style.color = '#2ed573';
                } else {
                    dot.className = 'status-indicator st-offline'; text.innerText = 'Alat Offline'; text.style.color = '#ff4757';
                }
            } catch(e){}
        }
        async function cekScan() {
            try {
                let res = await fetch('/api/last-scan');
                let data = await res.json();
                let input = document.getElementById('uidField');
                if(data.uid && data.uid !== "BELUM ADA" && input.value !== data.uid){
                    input.value = data.uid;
                    input.style.background = "#d4edda";
                    setTimeout(() => input.style.background = "#fff", 1000);
                }
            } catch(e){}
        }
        async function loadLogs() {
            try {
                let res = await fetch('/api/get-logs');
                let logs = await res.json();
                let html = '';
                logs.forEach(l => {
                   let time = l.waktu.replace('T', ' ').substring(0,19);
                   let badge = l.status == 'Masuk' ? 'bg-green' : 'bg-red';
                   html += `<tr><td><small>${time}</small></td><td><b>${l.nama}</b><br><small>${l.uid}</small></td><td><span class="badge ${badge}">${l.status}</span></td></tr>`;
                });
                document.getElementById('logTableBody').innerHTML = html;
            } catch(e){}
        }
        setInterval(updateStatus, 2000);
        setInterval(cekScan, 1500);
        setInterval(loadLogs, 2000);
        loadLogs();
    </script>
</body>
</html>
"""

SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<body style="display:flex;justify-content:center;align-items:center;height:100vh;background:#e0f7fa;font-family:sans-serif;">
    <div style="background:white;padding:40px;border-radius:20px;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.1);">
        <h1 style="color:#00c853;">✔ Berhasil!</h1>
        <p>Kartu <b>{{ nama }}</b> ({{ uid }}) tersimpan.</p>
        <a href="/" style="background:#00c853;color:white;padding:10px 30px;text-decoration:none;border-radius:50px;">OK</a>
    </div>
</body>
</html>
"""

# ==========================================
#  ROUTES AUTH (LOGIN / REGISTER / RESET)
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_data = supabase.table("admins").select("*").eq("username", username).execute()
        
        if user_data.data:
            user = user_data.data[0]
            if check_password_hash(user['password'], password):
                session['user'] = username
                
                # --- [PENTING] AKTIFKAN ALAT KARENA SUDAH LOGIN ---
                DEVICE_STATE["active"] = True
                DEVICE_STATE["operator"] = username
                
                return redirect('/')
            else:
                flash('Password salah!', 'error')
        else:
            flash('Username tidak ditemukan!', 'error')

    return render_template_string(AUTH_TEMPLATE, title="Login Admin", mode="login")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cek_user = supabase.table("admins").select("username").eq("username", username).execute()
        if cek_user.data:
            flash('Username sudah dipakai, pilih yang lain.', 'error')
        else:
            hashed_pw = generate_password_hash(password)
            supabase.table("admins").insert({"username": username, "password": hashed_pw}).execute()
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect('/login')

    return render_template_string(AUTH_TEMPLATE, title="Daftar Admin Baru", mode="register")

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        username = request.form['username']
        master_key = request.form['master_key']
        new_password = request.form['password']
        
        if master_key != MASTER_KEY:
            flash('Master Key salah!', 'error')
        else:
            cek_user = supabase.table("admins").select("id").eq("username", username).execute()
            if cek_user.data:
                new_hash = generate_password_hash(new_password)
                supabase.table("admins").update({"password": new_hash}).eq("username", username).execute()
                flash('Password berhasil direset!', 'success')
                return redirect('/login')
            else:
                flash('Username tidak ditemukan.', 'error')

    return render_template_string(AUTH_TEMPLATE, title="Reset Password", mode="reset")

@app.route('/logout')
def logout():
    session.pop('user', None)
    
    # --- [PENTING] NON-AKTIFKAN ALAT SAAT LOGOUT ---
    DEVICE_STATE["active"] = False
    DEVICE_STATE["operator"] = ""
    
    return redirect('/login')

# ==========================================
#  ROUTES UTAMA & API ARDUINO
# ==========================================

@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template_string(DASHBOARD_TEMPLATE, username=session['user'])

# --- [BARU] API KHUSUS ARDUINO UNTUK CEK STATUS LOGIN ---
@app.route('/api/device/status', methods=['GET'])
def check_device_status():
    if DEVICE_STATE["active"]:
        return jsonify({
            "status": "active",
            "user": DEVICE_STATE["operator"]
        })
    else:
        return jsonify({
            "status": "inactive",
            "user": None
        })

@app.route('/api/ping', methods=['GET'])
def ping():
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()
    return jsonify({"msg": "pong"})

@app.route('/api/status-alat', methods=['GET'])
def get_status_alat():
    global last_heartbeat_time
    if last_heartbeat_time is None: return jsonify({"status": "OFFLINE"})
    delta = (datetime.datetime.now() - last_heartbeat_time).total_seconds()
    return jsonify({"status": "ONLINE" if delta < 10 else "OFFLINE"})

@app.route('/api/last-scan', methods=['GET'])
def get_last_scan():
    scan = supabase.table("temp_scan").select("*").eq("id", 1).execute()
    if scan.data: return jsonify(scan.data[0])
    return jsonify({"uid": "BELUM ADA"})

@app.route('/api/get-logs', methods=['GET'])
def api_get_logs():
    try:
        logs = supabase.table("logs").select("*").order("id", desc=True).limit(10).execute()
        return jsonify(logs.data)
    except: return jsonify([])

@app.route('/api/register', methods=['POST'])
def register_card():
    uid = request.form.get('uid').upper()
    nama = request.form.get('nama')
    try:
        supabase.table("users").upsert({"uid": uid, "nama": nama}).execute()
        if 'user' in session: 
            return render_template_string(SUCCESS_TEMPLATE, nama=nama, uid=uid)
        return "OK"
    except Exception as e: return f"Error: {str(e)}"

@app.route('/api/akses', methods=['POST'])
def cek_akses():
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()
    
    # --- [TAMBAHAN KEAMANAN] ---
    # Jika device tidak aktif (belum login), tolak request scan
    if not DEVICE_STATE["active"]:
        return jsonify({"akses": False, "pesan": "Device Locked"}), 403

    data = request.json
    uid = data.get('uid')
    
    try: supabase.table("temp_scan").update({"uid": uid, "waktu": datetime.datetime.now().isoformat()}).eq("id", 1).execute()
    except: pass
    
    user = supabase.table("users").select("nama").eq("uid", uid).execute()
    if not user.data: return jsonify({"akses": False}), 403
    
    nama = user.data[0]['nama']
    log = supabase.table("logs").select("status").eq("uid", uid).order("id", desc=True).limit(1).execute()
    status = "Keluar" if (log.data and log.data[0]['status'] == "Masuk") else "Masuk"
    
    supabase.table("logs").insert({"uid": uid, "nama": nama, "status": status, "waktu": datetime.datetime.now().isoformat()}).execute()
    return jsonify({"akses": True, "nama": nama, "status": status}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

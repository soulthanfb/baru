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

# --- VARIABEL HEARTBEAT (Boleh di RAM karena update tiap detik) ---
last_heartbeat_time = None

# ==========================================
#  DESAIN HTML (SAMA SEPERTI SEBELUMNYA)
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
    .alert { padding: 10px; background: #ffcccc; color: #cc0000; border-radius: 5px; margin-bottom: 15px; font-size: 14px; }
    .success { background: #d4edda; color: #155724; }
    .links { margin-top: 20px; font-size: 14px; }
    .links a { color: #0072ff; text-decoration: none; margin: 0 5px; }
</style>
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
                <input type="text" name="master_key" placeholder="Master Key" required>
            {% endif %}
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit" class="btn-primary">
                {% if mode == 'login' %} MASUK {% elif mode == 'register' %} DAFTAR {% else %} UBAH PASSWORD {% endif %}
            </button>
        </form>
        <div class="links">
            {% if mode == 'login' %} <a href="/register">Daftar</a> | <a href="/reset">Lupa Password?</a> {% else %} <a href="/login">Kembali</a> {% endif %}
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
    <title>Dashboard</title>
    """ + COMMON_STYLE + """
    <style>
        .card { max-width: 800px; padding: 30px; }
        .header { display: flex; justify-content: space-between; margin-bottom: 20px; }
        .logout-btn { background: #ff4757; color: white; padding: 8px 15px; border-radius: 5px; text-decoration: none; }
        .status-bar { background: #f8f9fa; padding: 10px 20px; border-radius: 50px; display: inline-flex; align-items: center; gap: 10px; margin-bottom: 10px; font-weight:bold;}
        .st-on { color: #2ed573; } .st-off { color: #ff4757; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; text-align: left; }
        th, td { padding: 10px; border-bottom: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h3>Hi, {{ username }}!</h3>
            <a href="/logout" class="logout-btn">Keluar (Matikan Alat)</a>
        </div>

        <div style="text-align: left;">
            <div class="status-bar">
                Status WiFi Alat: <span id="wifiStatus" class="st-off">OFFLINE</span>
            </div>
            <div class="status-bar">
                Mode Keamanan: <span class="st-on">AKTIF (UNLOCKED)</span>
            </div>
        </div>

        <hr>
        <h4>Tambah Kartu & Log</h4>
        <form action="/api/register" method="POST">
            <input type="text" id="uidField" name="uid" placeholder="Tempel Kartu..." readonly>
            <input type="text" name="nama" placeholder="Nama Pemilik" required>
            <button type="submit" class="btn-primary">Simpan</button>
        </form>

        <div style="max-height: 200px; overflow-y: auto; margin-top: 20px;">
            <table>
                <thead><tr><th>Waktu</th><th>User</th><th>Status</th></tr></thead>
                <tbody id="logBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        async function updateData() {
            // Cek Status WiFi
            let resStatus = await fetch('/api/status-alat');
            let dStatus = await resStatus.json();
            document.getElementById('wifiStatus').innerText = dStatus.status;
            document.getElementById('wifiStatus').className = dStatus.status == 'ONLINE' ? 'st-on' : 'st-off';

            // Cek Scan Baru
            let resScan = await fetch('/api/last-scan');
            let dScan = await resScan.json();
            let inp = document.getElementById('uidField');
            if(dScan.uid && dScan.uid !== "BELUM ADA" && inp.value !== dScan.uid) {
                inp.value = dScan.uid;
                inp.style.background = "#d4edda";
            }

            // Cek Log
            let resLog = await fetch('/api/get-logs');
            let dLog = await resLog.json();
            let html = '';
            dLog.forEach(l => {
                html += `<tr><td>${l.waktu.substring(11,19)}</td><td>${l.nama}</td><td>${l.status}</td></tr>`;
            });
            document.getElementById('logBody').innerHTML = html;
        }
        setInterval(updateData, 2000);
        updateData();
    </script>
</body>
</html>
"""

# ==========================================
#  LOGIN & LOGOUT (DENGAN UPDATE DB)
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
                
                # [PERBAIKAN] Update Status ke Supabase (Permanen)
                try:
                    supabase.table("device_config").update({"is_active": True, "operator": username}).eq("id", 1).execute()
                except:
                    pass # Abaikan jika gagal update, tetap login
                
                return redirect('/')
            else:
                flash('Password salah!', 'error')
        else:
            flash('Username tidak ditemukan!', 'error')

    return render_template_string(AUTH_TEMPLATE, title="Login Admin", mode="login")

@app.route('/logout')
def logout():
    session.pop('user', None)
    
    # [PERBAIKAN] Matikan alat di Supabase
    try:
        supabase.table("device_config").update({"is_active": False, "operator": ""}).eq("id", 1).execute()
    except:
        pass
        
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = generate_password_hash(password)
        try:
            supabase.table("admins").insert({"username": username, "password": hashed}).execute()
            flash('Berhasil daftar!', 'success')
            return redirect('/login')
        except:
            flash('Gagal, username mungkin ada.', 'error')
    return render_template_string(AUTH_TEMPLATE, title="Register", mode="register")

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        if request.form['master_key'] == MASTER_KEY:
            hashed = generate_password_hash(request.form['password'])
            supabase.table("admins").update({"password": hashed}).eq("username", request.form['username']).execute()
            flash('Password direset.', 'success')
            return redirect('/login')
        flash('Master Key salah.', 'error')
    return render_template_string(AUTH_TEMPLATE, title="Reset", mode="reset")

# ==========================================
#  ROUTES API (ARDUINO & DASHBOARD)
# ==========================================

@app.route('/')
def home():
    if 'user' not in session: return redirect('/login')
    return render_template_string(DASHBOARD_TEMPLATE, username=session['user'])

# [PENTING] API Status sekarang baca dari Database, bukan variabel RAM
@app.route('/api/device/status', methods=['GET'])
def check_device_status():
    try:
        res = supabase.table("device_config").select("*").eq("id", 1).execute()
        if res.data and res.data[0]['is_active']:
            return jsonify({
                "status": "active",
                "user": res.data[0]['operator']
            })
    except:
        pass
    
    return jsonify({"status": "inactive", "user": None})

@app.route('/api/akses', methods=['POST'])
def cek_akses():
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()

    # [PENTING] Cek Status Keamanan dari DB sebelum izinkan scan
    try:
        conf = supabase.table("device_config").select("is_active").eq("id", 1).execute()
        if not conf.data or not conf.data[0]['is_active']:
             return jsonify({"akses": False, "pesan": "Device Locked"}), 403
    except:
        return jsonify({"akses": False}), 403

    # Logika Scan Normal
    data = request.json
    uid = data.get('uid')
    
    # Update temp scan untuk dashboard
    try: supabase.table("temp_scan").update({"uid": uid, "waktu": datetime.datetime.now().isoformat()}).eq("id", 1).execute()
    except: pass
    
    user = supabase.table("users").select("nama").eq("uid", uid).execute()
    if not user.data: return jsonify({"akses": False}), 403
    
    nama = user.data[0]['nama']
    log = supabase.table("logs").select("status").eq("uid", uid).order("id", desc=True).limit(1).execute()
    status = "Keluar" if (log.data and log.data[0]['status'] == "Masuk") else "Masuk"
    
    supabase.table("logs").insert({"uid": uid, "nama": nama, "status": status, "waktu": datetime.datetime.now().isoformat()}).execute()
    return jsonify({"akses": True, "nama": nama, "status": status}), 200

# Helper API lainnya
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
    return jsonify({"status": "ONLINE" if delta < 15 else "OFFLINE"})

@app.route('/api/last-scan', methods=['GET'])
def get_last_scan():
    res = supabase.table("temp_scan").select("*").eq("id", 1).execute()
    return jsonify(res.data[0] if res.data else {"uid": "BELUM ADA"})

@app.route('/api/get-logs', methods=['GET'])
def api_get_logs():
    res = supabase.table("logs").select("*").order("id", desc=True).limit(10).execute()
    return jsonify(res.data)

@app.route('/api/register', methods=['POST'])
def register_card():
    uid = request.form.get('uid').upper()
    nama = request.form.get('nama')
    try:
        supabase.table("users").upsert({"uid": uid, "nama": nama}).execute()
        if 'user' in session: return render_template_string(SUCCESS_TEMPLATE, nama=nama, uid=uid)
        return "OK"
    except Exception as e: return f"Error: {str(e)}"

# Template Sukses
SUCCESS_TEMPLATE = """
<!DOCTYPE html><html><body style="display:flex;justify-content:center;align-items:center;height:100vh;background:#e0f7fa;font-family:sans-serif;">
<div style="background:white;padding:40px;border-radius:20px;text-align:center;">
<h1 style="color:#00c853;">✔ Berhasil!</h1><p>Kartu tersimpan.</p><a href="/" style="background:#00c853;color:white;padding:10px 30px;text-decoration:none;border-radius:50px;">OK</a>
</div></body></html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

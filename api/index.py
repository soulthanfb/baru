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

last_heartbeat_time = None

# ==========================================
#  DESAIN BARU (MODERN UI WITH TAILWIND)
# ==========================================

# Kita gunakan Tailwind CSS lewat CDN agar ringan dan cepat
BASE_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
    body { font-family: 'Inter', sans-serif; }
    .glass { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }
</style>
"""

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <title>{{ title }}</title>
    """ + BASE_HEAD + """
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen bg-[url('https://source.unsplash.com/random/1920x1080/?technology')] bg-cover bg-center">
    <div class="absolute inset-0 bg-black bg-opacity-50"></div>
    
    <div class="relative z-10 w-full max-w-md p-8 glass rounded-2xl shadow-2xl transform transition-all">
        <div class="text-center mb-8">
            <div class="mx-auto w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-4 shadow-lg">
                <i class="fas fa-shield-alt text-2xl text-white"></i>
            </div>
            <h2 class="text-2xl font-bold text-gray-800">{{ title }}</h2>
            <p class="text-gray-500 text-sm">Sistem Keamanan IoT RFID</p>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-4 p-4 rounded-lg text-sm font-semibold {{ 'bg-red-100 text-red-700' if category == 'error' else 'bg-green-100 text-green-700' }}">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" class="space-y-5">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <div class="relative">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400"><i class="fas fa-user"></i></span>
                    <input type="text" name="username" class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" placeholder="Masukkan username" required>
                </div>
            </div>

            {% if mode == 'reset' %}
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Master Key</label>
                <div class="relative">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400"><i class="fas fa-key"></i></span>
                    <input type="text" name="master_key" class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Kode Rahasia" required>
                </div>
            </div>
            {% endif %}

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <div class="relative">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400"><i class="fas fa-lock"></i></span>
                    <input type="password" name="password" class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Masukkan password" required>
                </div>
            </div>

            <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-indigo-700 text-white font-bold py-3 rounded-lg hover:shadow-lg hover:scale-[1.02] transition-transform duration-200">
                {% if mode == 'login' %} MASUK DASHBOARD {% elif mode == 'register' %} DAFTAR AKUN {% else %} RESET PASSWORD {% endif %}
            </button>
        </form>

        <div class="mt-6 text-center text-sm text-gray-600 space-x-2">
            {% if mode == 'login' %}
                <a href="/register" class="hover:text-blue-600 font-medium">Buat Akun</a>
                <span class="text-gray-300">|</span>
                <a href="/reset" class="hover:text-blue-600 font-medium">Lupa Password?</a>
            {% else %}
                <a href="/login" class="text-blue-600 hover:underline font-medium">Kembali ke Login</a>
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
    <title>Dashboard Admin IoT</title>
    """ + BASE_HEAD + """
</head>
<body class="bg-slate-50 min-h-screen text-slate-800">

    <nav class="bg-white shadow-sm sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center gap-3">
                    <div class="bg-blue-600 text-white p-2 rounded-lg">
                        <i class="fas fa-microchip"></i>
                    </div>
                    <span class="font-bold text-xl tracking-tight text-slate-800">SmartGate<span class="text-blue-600">IoT</span></span>
                </div>
                <div class="flex items-center gap-4">
                    <div class="hidden md:flex flex-col text-right">
                        <span class="text-xs text-gray-500">Login sebagai</span>
                        <span class="text-sm font-semibold">{{ username }}</span>
                    </div>
                    <a href="/logout" class="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-100 transition flex items-center gap-2">
                        <i class="fas fa-power-off"></i> <span class="hidden sm:inline">Logout</span>
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                <div>
                    <p class="text-sm text-gray-500 font-medium mb-1">Status Perangkat</p>
                    <h3 id="wifiText" class="text-2xl font-bold text-gray-800">Menunggu...</h3>
                </div>
                <div id="wifiIconBg" class="p-4 bg-gray-100 rounded-full text-gray-400">
                    <i class="fas fa-wifi text-xl"></i>
                </div>
            </div>

            <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                <div>
                    <p class="text-sm text-gray-500 font-medium mb-1">Mode Keamanan</p>
                    <h3 class="text-2xl font-bold text-green-600">UNLOCKED</h3>
                    <p class="text-xs text-green-500">Perangkat dapat digunakan</p>
                </div>
                <div class="p-4 bg-green-50 rounded-full text-green-600">
                    <i class="fas fa-unlock-alt text-xl"></i>
                </div>
            </div>

            <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                <div>
                    <p class="text-sm text-gray-500 font-medium mb-1">Scan Terakhir</p>
                    <h3 id="lastScanText" class="text-lg font-bold text-gray-800 break-all">Belum Ada</h3>
                    <p id="lastScanTime" class="text-xs text-gray-400 mt-1">-</p>
                </div>
                <div class="p-4 bg-blue-50 rounded-full text-blue-600">
                    <i class="fas fa-id-card text-xl"></i>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            <div class="lg:col-span-1">
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden sticky top-24">
                    <div class="bg-gray-50 px-6 py-4 border-b border-gray-100">
                        <h3 class="font-bold text-gray-800"><i class="fas fa-user-plus mr-2 text-blue-500"></i> Register Kartu</h3>
                    </div>
                    <div class="p-6">
                        <div class="bg-blue-50 text-blue-700 text-sm p-3 rounded-lg mb-4 flex items-start gap-2">
                            <i class="fas fa-info-circle mt-0.5"></i>
                            <span>Tempelkan kartu RFID pada alat, UID akan otomatis muncul di bawah ini.</span>
                        </div>

                        <form action="/api/register" method="POST" class="space-y-4">
                            <div>
                                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">UID Kartu</label>
                                <div class="relative">
                                    <input type="text" id="uidField" name="uid" placeholder="Menunggu Scan..." 
                                        class="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5 pl-10 font-mono transition-colors" readonly required>
                                    <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                                        <i class="fas fa-barcode text-gray-400"></i>
                                    </div>
                                </div>
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Nama Pemilik</label>
                                <input type="text" name="nama" placeholder="Contoh: Soulthan" 
                                    class="w-full bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5" required>
                            </div>
                            <button type="submit" class="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center flex justify-center items-center gap-2 transition">
                                <i class="fas fa-save"></i> Simpan Data
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <div class="lg:col-span-2">
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div class="bg-gray-50 px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                        <h3 class="font-bold text-gray-800"><i class="fas fa-history mr-2 text-gray-500"></i> Riwayat Akses</h3>
                        <span class="text-xs bg-gray-200 text-gray-600 py-1 px-2 rounded">Real-time</span>
                    </div>
                    
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm text-left text-gray-500">
                            <thead class="text-xs text-gray-700 uppercase bg-gray-50 border-b">
                                <tr>
                                    <th scope="col" class="px-6 py-3">Waktu</th>
                                    <th scope="col" class="px-6 py-3">User</th>
                                    <th scope="col" class="px-6 py-3">UID</th>
                                    <th scope="col" class="px-6 py-3">Status</th>
                                </tr>
                            </thead>
                            <tbody id="logBody" class="divide-y divide-gray-100">
                                <tr><td colspan="4" class="text-center py-4">Memuat data...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <footer class="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-gray-400">
        &copy; 2026 Admin Dashboard System. Created with Python Flask & Tailwind. Developed by Soulthan and Team
    </footer>

    <script>
        async function updateData() {
            // 1. UPDATE STATUS WIFI
            try {
                let res = await fetch('/api/status-alat');
                let data = await res.json();
                let wifiText = document.getElementById('wifiText');
                let wifiBg = document.getElementById('wifiIconBg');
                
                if(data.status === 'ONLINE') {
                    wifiText.innerText = 'Terhubung';
                    wifiText.className = 'text-2xl font-bold text-green-600';
                    wifiBg.className = 'p-4 bg-green-100 rounded-full text-green-600 animate-pulse';
                } else {
                    wifiText.innerText = 'Offline';
                    wifiText.className = 'text-2xl font-bold text-red-500';
                    wifiBg.className = 'p-4 bg-red-100 rounded-full text-red-500';
                }
            } catch(e) {}

            // 2. UPDATE SCAN BARU DI FORM
            try {
                let res = await fetch('/api/last-scan');
                let data = await res.json();
                let input = document.getElementById('uidField');
                let lastText = document.getElementById('lastScanText');
                let lastTime = document.getElementById('lastScanTime');

                if(data.uid && data.uid !== "BELUM ADA") {
                    // Update Card Scan Terakhir
                    lastText.innerText = data.uid;
                    lastTime.innerText = new Date(data.waktu).toLocaleTimeString();

                    // Masukkan ke Form Input jika input kosong atau beda
                    if(input.value !== data.uid) {
                        input.value = data.uid;
                        // Efek visual kedip hijau
                        input.classList.remove('bg-gray-50');
                        input.classList.add('bg-green-100', 'text-green-800');
                        setTimeout(() => {
                            input.classList.remove('bg-green-100', 'text-green-800');
                            input.classList.add('bg-gray-50');
                        }, 1000);
                    }
                }
            } catch(e) {}

            // 3. UPDATE TABEL LOG
            try {
                let res = await fetch('/api/get-logs');
                let logs = await res.json();
                let html = '';
                
                logs.forEach(l => {
                    let timeObj = new Date(l.waktu);
                    let dateStr = timeObj.toLocaleDateString('id-ID', {day: 'numeric', month: 'short'});
                    let timeStr = timeObj.toLocaleTimeString('id-ID', {hour: '2-digit', minute:'2-digit'});
                    
                    let statusBadge = l.status === 'Masuk' 
                        ? '<span class="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded border border-green-400">Masuk</span>'
                        : '<span class="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded border border-red-400">Keluar</span>';

                    html += `
                    <tr class="bg-white hover:bg-gray-50 transition">
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div class="text-sm font-medium text-gray-900">${timeStr}</div>
                            <div class="text-xs text-gray-400">${dateStr}</div>
                        </td>
                        <td class="px-6 py-4 font-medium text-gray-900">${l.nama}</td>
                        <td class="px-6 py-4 font-mono text-xs text-gray-500">${l.uid}</td>
                        <td class="px-6 py-4">${statusBadge}</td>
                    </tr>`;
                });
                document.getElementById('logBody').innerHTML = html;
            } catch(e) {}
        }

        // Jalankan setiap 2 detik
        setInterval(updateData, 2000);
        updateData();
    </script>
</body>
</html>
"""

# ==========================================
#  LOGIN & LOGIC (SAMA SEPERTI SEBELUMNYA)
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
                try:
                    supabase.table("device_config").update({"is_active": True, "operator": username}).eq("id", 1).execute()
                except: pass
                return redirect('/')
            else:
                flash('Password salah!', 'error')
        else:
            flash('Username tidak ditemukan!', 'error')

    return render_template_string(AUTH_TEMPLATE, title="Login Dashboard", mode="login")

@app.route('/logout')
def logout():
    session.pop('user', None)
    try:
        supabase.table("device_config").update({"is_active": False, "operator": ""}).eq("id", 1).execute()
    except: pass
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = generate_password_hash(password)
        try:
            supabase.table("admins").insert({"username": username, "password": hashed}).execute()
            flash('Akun berhasil dibuat!', 'success')
            return redirect('/login')
        except:
            flash('Username sudah digunakan.', 'error')
    return render_template_string(AUTH_TEMPLATE, title="Register Admin", mode="register")

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        if request.form['master_key'] == MASTER_KEY:
            hashed = generate_password_hash(request.form['password'])
            supabase.table("admins").update({"password": hashed}).eq("username", request.form['username']).execute()
            flash('Password berhasil direset.', 'success')
            return redirect('/login')
        flash('Master Key salah.', 'error')
    return render_template_string(AUTH_TEMPLATE, title="Reset Password", mode="reset")

# ==========================================
#  API ROUTES (SAMA PERSIS - TIDAK PERLU UBAH ARDUINO)
# ==========================================

@app.route('/')
def home():
    if 'user' not in session: return redirect('/login')
    return render_template_string(DASHBOARD_TEMPLATE, username=session['user'])

@app.route('/api/device/status', methods=['GET'])
def check_device_status():
    try:
        res = supabase.table("device_config").select("*").eq("id", 1).execute()
        if res.data and res.data[0]['is_active']:
            return jsonify({"status": "active", "user": res.data[0]['operator']})
    except: pass
    return jsonify({"status": "inactive", "user": None})

@app.route('/api/akses', methods=['POST'])
def cek_akses():
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()
    try:
        conf = supabase.table("device_config").select("is_active").eq("id", 1).execute()
        if not conf.data or not conf.data[0]['is_active']:
             return jsonify({"akses": False, "pesan": "Device Locked"}), 403
    except: return jsonify({"akses": False}), 403

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
        if 'user' in session: 
            return render_template_string(
                """<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head>
                <body class="bg-green-50 flex items-center justify-center h-screen">
                <div class="bg-white p-8 rounded-xl shadow-lg text-center max-w-sm">
                <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4"><i class="fas fa-check text-2xl text-green-600"></i></div>
                <h2 class="text-2xl font-bold text-gray-800 mb-2">Berhasil!</h2>
                <p class="text-gray-600 mb-6">Kartu milik <b>{{nama}}</b> telah disimpan.</p>
                <a href="/" class="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 transition">Kembali ke Dashboard</a>
                </div><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"></body></html>""", 
                nama=nama)
        return "OK"
    except Exception as e: return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



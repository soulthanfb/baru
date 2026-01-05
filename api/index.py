from flask import Flask, request, jsonify, render_template_string
from supabase import create_client
import datetime

app = Flask(__name__)

# --- KONFIGURASI SUPABASE ---
SUPABASE_URL = "https://lmcxzdumzyvgobjpqopr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3h6ZHVtenl2Z29ianBxb3ByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NTM0MjIsImV4cCI6MjA4MTUyOTQyMn0.9F3aqni686QeiLE3z3NtpOBfyIkLVjI93gaA3ejYwOw" 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- VARIABEL HEARTBEAT ---
# Menyimpan waktu terakhir Arduino lapor diri
last_heartbeat_time = None

# --- TEMPLATE HTML (Sama seperti sebelumnya) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Sistem Garasi Pintar</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Poppins', sans-serif; background: linear-gradient(120deg, #84fab0 0%, #8fd3f4 100%); min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 40px 20px; margin: 0; color: #444; }
        
        /* Status Bar */
        .status-bar { background: white; padding: 10px 25px; border-radius: 50px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 10px; margin-bottom: 20px; font-weight: 600; font-size: 14px; transition: all 0.3s ease; }
        .status-indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
        .st-offline { background-color: #ff4757; box-shadow: 0 0 10px #ff4757; }
        .st-online { background-color: #2ed573; box-shadow: 0 0 10px #2ed573; }

        .main-container { background: rgba(255, 255, 255, 0.95); padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); width: 100%; max-width: 900px; display: grid; grid-template-columns: 1fr; gap: 40px; }
        .form-section { border-bottom: 2px dashed #e0e0e0; padding-bottom: 30px; margin-bottom: 10px; }
        .scan-box { background: #e3f2fd; border: 2px solid #bbdefb; color: #1976d2; padding: 15px; border-radius: 10px; text-align: center; font-size: 14px; margin-bottom: 25px; }
        
        label { font-weight: 600; color: #555; display: block; margin-bottom: 8px; font-size: 14px; }
        input[type="text"] { width: 100%; padding: 15px; margin-bottom: 20px; border: 2px solid #eee; border-radius: 12px; font-size: 16px; box-sizing: border-box; }
        input[readonly] { background-color: #f9f9f9; color: #888; cursor: not-allowed; }
        button { width: 100%; padding: 15px; background: linear-gradient(to right, #43e97b 0%, #38f9d7 100%); color: white; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; }
        
        .table-wrapper { overflow-x: auto; border-radius: 12px; border: 1px solid #eee; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #f0f0f0; }
        th { background-color: #f8f9fa; color: #666; font-size: 13px; text-transform: uppercase; font-weight: 600; }
        .badge { padding: 6px 12px; border-radius: 50px; color: white; font-size: 12px; font-weight: 600; }
        .bg-green { background-color: #00c853; } .bg-red { background-color: #ff3d00; }
        .loading { text-align: center; color: #999; font-style: italic; padding: 20px; }
        
        h2 { margin: 0 0 20px 0; color: #333; font-weight: 600; text-align: center; }
        @media (min-width: 768px) {
            .main-container { grid-template-columns: 1fr 1.5fr; align-items: start; }
            .form-section { border-bottom: none; border-right: 2px dashed #e0e0e0; padding-bottom: 0; padding-right: 30px; margin-bottom: 0; }
            h2 { text-align: left; }
        }
    </style>
</head>
<body>

    <div class="status-bar">
        <span id="statusDot" class="status-indicator st-offline"></span>
        <span id="statusText">Menunggu Koneksi WiFi...</span>
    </div>

    <div class="main-container">
        <div class="form-section">
            <h2>Kartu Baru</h2>
            <div class="scan-box">📡 Tempelkan kartu pada alat reader</div>
            <form action="/api/register" method="POST">
                <label>UID Kartu</label>
                <input type="text" id="uidField" name="uid" placeholder="Menunggu scan..." required readonly>
                <label>Nama Pemilik</label>
                <input type="text" name="nama" placeholder="Contoh: Budi Santoso" required>
                <button type="submit">Simpan Data</button>
            </form>
        </div>

        <div class="log-section">
            <h2>Riwayat Akses</h2>
            <div class="table-wrapper">
                <table>
                    <thead><tr><th>Waktu</th><th>Nama / UID</th><th>Status</th></tr></thead>
                    <tbody id="logTableBody"><tr><td colspan="3" class="loading">Memuat data log...</td></tr></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // LOGIKA STATUS ONLINE/OFFLINE
        async function checkSystemStatus() {
            try {
                const response = await fetch('/api/status-alat');
                const data = await response.json();
                
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                
                if (data.status === "ONLINE") {
                    statusDot.className = "status-indicator st-online";
                    statusText.innerText = "Alat Online (WiFi Terhubung)";
                    statusText.style.color = "#2ed573";
                } else {
                    statusDot.className = "status-indicator st-offline";
                    statusText.innerText = "Alat Offline / Mati";
                    statusText.style.color = "#ff4757";
                }
            } catch (error) { console.error("Gagal cek status:", error); }
        }

        async function checkLatestScan() {
            try {
                const response = await fetch('/api/last-scan');
                const data = await response.json();
                const inputField = document.getElementById('uidField');
                if (data.uid && data.uid !== "BELUM ADA") {
                    if(inputField.value !== data.uid) {
                        inputField.value = data.uid;
                        inputField.style.borderColor = "#43e97b"; inputField.style.backgroundColor = "#e8f5e9";
                        setTimeout(() => { inputField.style.borderColor = "#eee"; inputField.style.backgroundColor = "#f9f9f9"; }, 1000);
                    }
                }
            } catch (error) { }
        }

        async function refreshLogs() {
            try {
                const response = await fetch('/api/get-logs'); 
                const logs = await response.json();
                const tableBody = document.getElementById('logTableBody');
                if (logs.length === 0) { tableBody.innerHTML = '<tr><td colspan="3" class="loading">Belum ada riwayat</td></tr>'; return; }
                let htmlContent = '';
                logs.forEach(log => {
                    let cleanTime = log.waktu.replace('T', ' ').substring(0, 19);
                    let badgeClass = (log.status === 'Masuk') ? 'bg-green' : 'bg-red';
                    htmlContent += `<tr><td style="font-size:13px;color:#666;">${cleanTime}</td><td><div><b>${log.nama}</b></div><div style="font-size:11px;color:#999;">${log.uid}</div></td><td><span class="badge ${badgeClass}">${log.status}</span></td></tr>`;
                });
                tableBody.innerHTML = htmlContent;
            } catch (error) { }
        }

        setInterval(checkSystemStatus, 2000); // Cek status tiap 2 detik
        setInterval(checkLatestScan, 1500); 
        setInterval(refreshLogs, 2000);     
        refreshLogs();
    </script>
</body>
</html>
"""

# --- TEMPLATE SUKSES ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Berhasil</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); height: 100vh; margin: 0; display: flex; justify-content: center; align-items: center; }
        .card { background: white; padding: 40px; border-radius: 25px; box-shadow: 0 20px 50px rgba(0,0,0,0.1); text-align: center; width: 90%; max-width: 380px; animation: popIn 0.5s ease; }
        .btn { background: #009688; color: white; text-decoration: none; padding: 12px 30px; border-radius: 50px; display: inline-block; margin-top: 20px; }
        @keyframes popIn { 0% { transform: scale(0.5); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
    </style>
</head>
<body>
    <div class="card">
        <h1 style="color:#009688;">✔ Sukses!</h1>
        <p>Kartu <b>{{ nama }}</b><br>({{ uid }})<br>berhasil disimpan.</p>
        <a href="/" class="btn">OK</a>
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

# [PENTING] Endpoint Heartbeat: Dipanggil Arduino setiap 5 detik
@app.route('/api/ping', methods=['GET', 'POST'])
def ping():
    global last_heartbeat_time
    # Update waktu terakhir alat "melapor"
    last_heartbeat_time = datetime.datetime.now()
    return jsonify({"message": "pong", "server_time": last_heartbeat_time.isoformat()})

# Endpoint Status: Mengecek apakah alat masih hidup
@app.route('/api/status-alat', methods=['GET'])
def get_status_alat():
    global last_heartbeat_time
    
    if last_heartbeat_time is None:
        return jsonify({"status": "OFFLINE"})
    
    # Hitung selisih waktu sekarang dengan heartbeat terakhir
    now = datetime.datetime.now()
    selisih = (now - last_heartbeat_time).total_seconds()
    
    # Jika sudah lebih dari 10 detik tidak ada kabar, anggap OFFLINE
    if selisih > 10:
        return jsonify({"status": "OFFLINE"})
    else:
        return jsonify({"status": "ONLINE"})

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
    data = {"uid": uid, "nama": nama}
    try:
        supabase.table("users").upsert(data).execute()
        return render_template_string(SUCCESS_TEMPLATE, nama=nama, uid=uid)
    except Exception as e: return f"Error: {str(e)}"

@app.route('/api/last-scan', methods=['GET'])
def get_last_scan():
    scan = supabase.table("temp_scan").select("*").eq("id", 1).execute()
    if scan.data: return jsonify(scan.data[0])
    return jsonify({"uid": "BELUM ADA"})

@app.route('/api/akses', methods=['POST'])
def cek_akses():
    # Update heartbeat juga saat ada akses, biar status tetap online
    global last_heartbeat_time
    last_heartbeat_time = datetime.datetime.now()

    data = request.json
    uid_kartu = data.get('uid')
    try: supabase.table("temp_scan").update({"uid": uid_kartu, "waktu": datetime.datetime.now().isoformat()}).eq("id", 1).execute()
    except: pass

    user_query = supabase.table("users").select("nama").eq("uid", uid_kartu).execute()
    if not user_query.data: return jsonify({"akses": False, "pesan": "Tidak Terdaftar"}), 403

    nama_user = user_query.data[0]['nama']
    log_query = supabase.table("logs").select("status").eq("uid", uid_kartu).order("id", desc=True).limit(1).execute()
    status_baru = "Masuk"
    if log_query.data and log_query.data[0]['status'] == "Masuk": status_baru = "Keluar"

    log_data = {"uid": uid_kartu, "nama": nama_user, "status": status_baru, "waktu": datetime.datetime.now().isoformat()}
    supabase.table("logs").insert(log_data).execute()
    return jsonify({"akses": True, "nama": nama_user, "status": status_baru}), 200

if __name__ == '__main__':
    # Pastikan host='0.0.0.0' agar bisa diakses dari perangkat lain (Arduino)
    app.run(host='0.0.0.0', port=5000, debug=True)

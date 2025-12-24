from flask import Flask, request, jsonify, render_template_string
from supabase import create_client
import datetime

app = Flask(__name__)

SUPABASE_URL = "https://lmcxzdumzyvgobjpqopr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3h6ZHVtenl2Z29ianBxb3ByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NTM0MjIsImV4cCI6MjA4MTUyOTQyMn0.9F3aqni686QeiLE3z3NtpOBfyIkLVjI93gaA3ejYwOw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- HALAMAN WEBSITE (FRONTEND) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pendaftaran Kartu Garasi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; padding: 20px; background: #f4f4f9; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #218838; }
        h2 { color: #333; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Daftar Kartu Baru</h2>
        <form action="/api/register" method="POST">
            <label>UID Kartu (Contoh: B2 BF F1 05)</label>
            <input type="text" name="uid" placeholder="Masukkan UID dari Serial Monitor" required>
            <label>Nama Pemilik</label>
            <input type="text" name="nama" placeholder="Masukkan Nama" required>
            <button type="submit">Daftarkan Kartu</button>
        </form>
        <hr>
        <p><a href="/api/logs">Lihat Log Riwayat Akses</a></p>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/register', methods=['POST'])
def register_card():
    uid = request.form.get('uid').upper()
    nama = request.form.get('nama')
    
    # Simpan ke tabel 'users' di Supabase
    data = {"uid": uid, "nama": nama}
    try:
        supabase.table("users").upsert(data).execute()
        return f"<h3>Sukses! Kartu {nama} berhasil didaftarkan.</h3><a href='/'>Kembali</a>"
    except Exception as e:
        return f"Error: {str(e)}"

# --- API UNTUK ESP8266 ---
@app.route('/api/akses', methods=['POST'])
def cek_akses():
    # ... (sama seperti kode sebelumnya) ...
    data = request.json
    uid_kartu = data.get('uid')
    
    user_query = supabase.table("users").select("nama").eq("uid", uid_kartu).execute()
    
    if not user_query.data:
        return jsonify({"akses": False}), 403

    nama_user = user_query.data[0]['nama']
    log_query = supabase.table("logs").select("status").eq("uid", uid_kartu).order("id", desc=True).limit(1).execute()
    
    status_baru = "Masuk"
    if log_query.data and log_query.data[0]['status'] == "Masuk":
        status_baru = "Keluar"

    log_data = {"uid": uid_kartu, "nama": nama_user, "status": status_baru, "waktu": datetime.datetime.now().isoformat()}
    supabase.table("logs").insert(log_data).execute()

    return jsonify({"akses": True, "nama": nama_user, "status": status_baru}), 200

# API untuk melihat log sederhana
@app.route('/api/logs')
def view_logs():
    logs = supabase.table("logs").select("*").order("id", desc=True).limit(20).execute()
    return jsonify(logs.data)
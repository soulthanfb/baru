from flask import Flask, request, jsonify, render_template_string
from supabase import create_client
import datetime

app = Flask(__name__)

# --- KONFIGURASI SUPABASE ---
# HARAP DIGANTI JIKA DI-DEPLOY KE PUBLIK (Saat ini terekspos)
SUPABASE_URL = "https://lmcxzdumzyvgobjpqopr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3h6ZHVtenl2Z29ianBxb3ByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NTM0MjIsImV4cCI6MjA4MTUyOTQyMn0.9F3aqni686QeiLE3z3NtpOBfyIkLVjI93gaA3ejYwOw" 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- TEMPLATE HTML (FRONTEND) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Sistem Garasi Pintar</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; flex-direction: column; align-items: center; padding: 20px; margin: 0; }
        .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 500px; margin-bottom: 20px; }
        h2 { text-align: center; color: #333; margin-bottom: 20px; }
        
        /* Form Styles */
        label { font-weight: bold; color: #555; display: block; margin-top: 15px; }
        input[type="text"] { width: 100%; padding: 12px; margin-top: 5px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        input[type="text"]:focus { border-color: #28a745; outline: none; }
        button { width: 100%; padding: 12px; background-color: #28a745; color: white; border: none; border-radius: 6px; font-size: 16px; margin-top: 20px; cursor: pointer; transition: background 0.3s; }
        button:hover { background-color: #218838; }
        
        /* Table Styles */
        .table-container { width: 100%; max-width: 800px; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background-color: #007bff; color: white; text-transform: uppercase; font-size: 14px; letter-spacing: 0.5px; }
        tr:hover { background-color: #f1f1f1; }
        .badge { padding: 5px 10px; border-radius: 20px; color: white; font-size: 12px; font-weight: bold; }
        .bg-green { background-color: #28a745; }
        .bg-red { background-color: #dc3545; }
        
        .status-box { background: #e9ecef; padding: 10px; border-radius: 6px; text-align: center; margin-bottom: 15px; font-size: 14px; color: #495057;}
        .loading { color: #888; font-style: italic; text-align: center; padding: 20px; }
    </style>
</head>
<body>

    <div class="container">
        <h2>Daftar Kartu Baru</h2>
        
        <div class="status-box">
            Tempelkan kartu ke alat, UID akan muncul otomatis di bawah ini.
        </div>

        <form action="/api/register" method="POST">
            <label>UID Kartu</label>
            <input type="text" id="uidField" name="uid" placeholder="Menunggu scan..." required readonly>
            
            <label>Nama Pemilik</label>
            <input type="text" name="nama" placeholder="Masukkan Nama Anda" required>
            
            <button type="submit">Simpan Kartu</button>
        </form>
    </div>

    <div class="table-container">
        <h2 style="margin-top: 30px;">Riwayat Akses (Real-time)</h2>
        <table>
            <thead>
                <tr>
                    <th>Waktu</th>
                    <th>Nama</th>
                    <th>UID</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="logTableBody">
                <tr><td colspan="4" class="loading">Memuat data...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        // --- 1. FUNGSI AUTO-FILL UID (Registrasi) ---
        async function checkLatestScan() {
            try {
                const response = await fetch('/api/last-scan');
                const data = await response.json();
                
                const inputField = document.getElementById('uidField');
                
                if (data.uid && data.uid !== "BELUM ADA") {
                    if(inputField.value !== data.uid) {
                        inputField.value = data.uid;
                        inputField.style.backgroundColor = "#e8f0fe"; 
                        setTimeout(() => { inputField.style.backgroundColor = "white"; }, 500);
                    }
                }
            } catch (error) {
                console.error("Gagal mengambil scan:", error);
            }
        }

        // --- 2. FUNGSI AUTO-REFRESH TABEL LOGS ---
        async function refreshLogs() {
            try {
                // Panggil API baru khusus JSON
                const response = await fetch('/api/get-logs'); 
                const logs = await response.json();
                
                const tableBody = document.getElementById('logTableBody');
                
                // Jika data kosong
                if (logs.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="4" class="loading">Belum ada riwayat akses</td></tr>';
                    return;
                }

                // Bangun HTML baris tabel
                let htmlContent = '';
                logs.forEach(log => {
                    // Format waktu agar rapi (buang huruf T)
                    let cleanTime = log.waktu.replace('T', ' ').substring(0, 19);
                    
                    // Tentukan warna badge
                    let badgeClass = (log.status === 'Masuk') ? 'bg-green' : 'bg-red';
                    
                    htmlContent += `
                        <tr>
                            <td>${cleanTime}</td>
                            <td><b>${log.nama}</b></td>
                            <td><code>${log.uid}</code></td>
                            <td>
                                <span class="badge ${badgeClass}">
                                    ${log.status}
                                </span>
                            </td>
                        </tr>
                    `;
                });

                // Update isi tabel
                tableBody.innerHTML = htmlContent;

            } catch (error) {
                console.error("Gagal refresh logs:", error);
            }
        }

        // Jalankan interval
        setInterval(checkLatestScan, 2000); // Cek UID tiap 2 detik
        setInterval(refreshLogs, 2000);     // Refresh tabel tiap 2 detik
        
        // Panggil sekali saat halaman pertama dimuat
        refreshLogs();
    </script>

</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    # Tidak perlu passing data logs di sini lagi, karena akan diambil via JS
    return render_template_string(HTML_TEMPLATE)

# [BARU] Endpoint khusus untuk memberikan data Logs dalam bentuk JSON ke JavaScript
@app.route('/api/get-logs', methods=['GET'])
def api_get_logs():
    try:
        # Ambil 10 log terakhir
        logs = supabase.table("logs").select("*").order("id", desc=True).limit(10).execute()
        return jsonify(logs.data)
    except Exception as e:
        return jsonify([])

@app.route('/api/register', methods=['POST'])
def register_card():
    uid = request.form.get('uid').upper()
    nama = request.form.get('nama')
    
    data = {"uid": uid, "nama": nama}
    try:
        supabase.table("users").upsert(data).execute()
        return f"""
        <script>
            alert('Sukses! Kartu {nama} ({uid}) berhasil didaftarkan.');
            window.location.href = '/';
        </script>
        """
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/api/last-scan', methods=['GET'])
def get_last_scan():
    scan = supabase.table("temp_scan").select("*").eq("id", 1).execute()
    if scan.data:
        return jsonify(scan.data[0])
    return jsonify({"uid": "BELUM ADA"})

@app.route('/api/akses', methods=['POST'])
def cek_akses():
    data = request.json
    uid_kartu = data.get('uid')
    
    # Update temp_scan
    try:
        supabase.table("temp_scan").update({"uid": uid_kartu, "waktu": datetime.datetime.now().isoformat()}).eq("id", 1).execute()
    except Exception as e:
        print("Error update temp scan:", e)

    # Cek user
    user_query = supabase.table("users").select("nama").eq("uid", uid_kartu).execute()
    
    if not user_query.data:
        return jsonify({"akses": False, "pesan": "Tidak Terdaftar"}), 403

    # Logika Masuk/Keluar
    nama_user = user_query.data[0]['nama']
    log_query = supabase.table("logs").select("status").eq("uid", uid_kartu).order("id", desc=True).limit(1).execute()
    
    status_baru = "Masuk"
    if log_query.data and log_query.data[0]['status'] == "Masuk":
        status_baru = "Keluar"

    # Simpan Log
    log_data = {"uid": uid_kartu, "nama": nama_user, "status": status_baru, "waktu": datetime.datetime.now().isoformat()}
    supabase.table("logs").insert(log_data).execute()

    return jsonify({"akses": True, "nama": nama_user, "status": status_baru}), 200

if __name__ == '__main__':
    app.run(debug=True)

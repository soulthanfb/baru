from flask import Flask, request, jsonify, render_template_string
from supabase import create_client
import datetime

app = Flask(__name__)

# --- KONFIGURASI SUPABASE ---
SUPABASE_URL = "https://lmcxzdumzyvgobjpqopr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtY3h6ZHVtenl2Z29ianBxb3ByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NTM0MjIsImV4cCI6MjA4MTUyOTQyMn0.9F3aqni686QeiLE3z3NtpOBfyIkLVjI93gaA3ejYwOw" 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- TEMPLATE 1: DASHBOARD UTAMA (DENGAN ANIMASI WIFI) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Sistem Garasi Pintar</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(120deg, #84fab0 0%, #8fd3f4 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
            margin: 0;
            color: #444;
        }

        /* --- NOTIFIKASI WIFI (ANIMASI) --- */
        .wifi-toast {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px); /* Mulai dari atas layar (tersembunyi) */
            background: white;
            padding: 12px 25px;
            border-radius: 50px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 1000;
            transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.5s;
            font-weight: 600;
            font-size: 14px;
            opacity: 0;
        }
        
        .wifi-toast.show {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }

        .wifi-toast.hidden {
            transform: translateX(-50%) translateY(-100px);
            opacity: 0;
        }

        /* Ikon WiFi */
        .wifi-icon { font-size: 18px; }
        
        .status-connecting { color: #f39c12; }
        .status-connected { color: #2ecc71; }
        
        .spin { animation: spin 1s linear infinite; display: inline-block; }
        @keyframes spin { 100% { transform: rotate(360deg); } }


        /* --- CONTAINER UTAMA --- */
        .main-container {
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 900px;
            display: grid;
            grid-template-columns: 1fr;
            gap: 40px;
            margin-top: 20px; /* Beri jarak untuk notifikasi wifi */
        }

        h2 { margin: 0 0 20px 0; color: #333; font-weight: 600; text-align: center; }
        
        /* Form Section */
        .form-section { border-bottom: 2px dashed #e0e0e0; padding-bottom: 30px; margin-bottom: 10px; }
        
        .scan-box {
            background: #e3f2fd;
            border: 2px solid #bbdefb;
            color: #1976d2;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-size: 14px;
            margin-bottom: 25px;
            animation: pulse 2s infinite;
        }
        
        label { font-weight: 600; color: #555; display: block; margin-bottom: 8px; font-size: 14px; }
        
        input[type="text"] {
            width: 100%;
            padding: 15px;
            margin-bottom: 20px;
            border: 2px solid #eee;
            border-radius: 12px;
            font-size: 16px;
            font-family: inherit;
            transition: all 0.3s;
            box-sizing: border-box;
        }
        
        input[type="text"]:focus { border-color: #84fab0; outline: none; box-shadow: 0 0 10px rgba(132, 250, 176, 0.2); }
        input[readonly] { background-color: #f9f9f9; color: #888; cursor: not-allowed; }

        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(to right, #43e97b 0%, #38f9d7 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(56, 249, 215, 0.4); }

        /* Table Section */
        .table-wrapper { overflow-x: auto; border-radius: 12px; border: 1px solid #eee; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #f0f0f0; }
        th { background-color: #f8f9fa; color: #666; font-size: 13px; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }
        tr:last-child td { border-bottom: none; }
        tr:hover { background-color: #fafafa; }

        .badge { padding: 6px 12px; border-radius: 50px; color: white; font-size: 12px; font-weight: 600; display: inline-block; }
        .bg-green { background-color: #00c853; box-shadow: 0 2px 5px rgba(0,200,83,0.2); }
        .bg-red { background-color: #ff3d00; box-shadow: 0 2px 5px rgba(255,61,0,0.2); }
        
        .loading { text-align: center; color: #999; font-style: italic; padding: 20px; }

        @keyframes pulse { 0% { opacity: 0.8; } 50% { opacity: 1; } 100% { opacity: 0.8; } }

        /* Responsive Layout */
        @media (min-width: 768px) {
            .main-container { grid-template-columns: 1fr 1.5fr; align-items: start; }
            .form-section { border-bottom: none; border-right: 2px dashed #e0e0e0; padding-bottom: 0; padding-right: 30px; margin-bottom: 0; }
            h2 { text-align: left; }
        }
    </style>
</head>
<body>

    <div id="wifiToast" class="wifi-toast">
        <span id="wifiIcon" class="wifi-icon spin">🔄</span>
        <span id="wifiText" class="status-connecting">Menghubungkan WiFi...</span>
    </div>

    <div class="main-container">
        <div class="form-section">
            <h2>Kartu Baru</h2>
            <div class="scan-box">
                📡 Tempelkan kartu pada alat reader, UID akan terisi otomatis.
            </div>

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
                    <thead>
                        <tr>
                            <th>Waktu</th>
                            <th>Nama / UID</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="logTableBody">
                        <tr><td colspan="3" class="loading">Memuat data log...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // --- ANIMASI KONEKSI WIFI ---
        window.addEventListener('load', function() {
            const toast = document.getElementById('wifiToast');
            const icon = document.getElementById('wifiIcon');
            const text = document.getElementById('wifiText');

            // 1. Munculkan Toast (Loading)
            setTimeout(() => {
                toast.classList.add('show');
            }, 500); // Muncul setengah detik setelah buka web

            // 2. Ubah jadi Terhubung setelah 2.5 detik
            setTimeout(() => {
                icon.classList.remove('spin');
                icon.innerHTML = '✅'; // Ganti ikon loading jadi centang
                text.innerHTML = 'WiFi Terhubung!';
                text.className = 'status-connected';
            }, 3000);

            // 3. Hilangkan Notifikasi setelah 6 detik
            setTimeout(() => {
                toast.classList.remove('show');
                toast.classList.add('hidden');
            }, 6000);
        });

        // 1. Script Auto-Fill UID dari Alat
        async function checkLatestScan() {
            try {
                const response = await fetch('/api/last-scan');
                const data = await response.json();
                const inputField = document.getElementById('uidField');
                
                if (data.uid && data.uid !== "BELUM ADA") {
                    if(inputField.value !== data.uid) {
                        inputField.value = data.uid;
                        // Efek visual kedip saat UID masuk
                        inputField.style.borderColor = "#43e97b";
                        inputField.style.backgroundColor = "#e8f5e9";
                        setTimeout(() => { 
                            inputField.style.borderColor = "#eee"; 
                            inputField.style.backgroundColor = "#f9f9f9";
                        }, 1000);
                    }
                }
            } catch (error) { console.error("Error scan:", error); }
        }

        // 2. Script Auto-Refresh Tabel
        async function refreshLogs() {
            try {
                const response = await fetch('/api/get-logs'); 
                const logs = await response.json();
                const tableBody = document.getElementById('logTableBody');
                
                if (logs.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="3" class="loading">Belum ada riwayat akses</td></tr>';
                    return;
                }

                let htmlContent = '';
                logs.forEach(log => {
                    let cleanTime = log.waktu.replace('T', ' ').substring(0, 19); 
                    let badgeClass = (log.status === 'Masuk') ? 'bg-green' : 'bg-red';
                    let userInfo = `<b>${log.nama}</b>`;
                    
                    htmlContent += `
                        <tr>
                            <td style="font-size: 13px; color: #666;">${cleanTime}</td>
                            <td>
                                <div>${userInfo}</div>
                                <div style="font-size: 11px; color: #999; margin-top: 2px;">ID: ${log.uid}</div>
                            </td>
                            <td><span class="badge ${badgeClass}">${log.status}</span></td>
                        </tr>
                    `;
                });
                tableBody.innerHTML = htmlContent;
            } catch (error) { console.error("Error logs:", error); }
        }

        setInterval(checkLatestScan, 1500); 
        setInterval(refreshLogs, 2000);     
        refreshLogs();
    </script>

</body>
</html>
"""

# --- TEMPLATE 2: HALAMAN SUKSES ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Berhasil Didaftarkan</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            height: 100vh;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .card {
            background: white;
            padding: 50px 40px;
            border-radius: 25px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.1);
            text-align: center;
            width: 90%;
            max-width: 380px;
            animation: popIn 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }
        .icon-circle {
            width: 80px;
            height: 80px;
            background: #e0f2f1;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 25px auto;
        }
        svg { width: 40px; height: 40px; stroke: #009688; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; fill: none; animation: drawCheck 0.5s 0.6s forwards; stroke-dasharray: 50; stroke-dashoffset: 50; }
        
        h1 { color: #333; margin: 0 0 10px 0; font-size: 24px; }
        p { color: #666; margin-bottom: 30px; line-height: 1.6; font-size: 15px; }
        
        .uid-badge { background: #f0f0f0; padding: 4px 10px; border-radius: 6px; font-weight: bold; color: #555; font-family: monospace; }

        .btn {
            background: #009688;
            color: white;
            text-decoration: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-weight: 600;
            display: inline-block;
            box-shadow: 0 10px 20px rgba(0, 150, 136, 0.3);
            transition: all 0.3s;
        }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 15px 25px rgba(0, 150, 136, 0.4); background: #00796b; }

        @keyframes popIn { 0% { transform: scale(0.5); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes drawCheck { to { stroke-dashoffset: 0; } }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-circle">
            <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>
        </div>
        <h1>Pendaftaran Berhasil!</h1>
        <p>
            Kartu atas nama <b>{{ nama }}</b><br>
            telah berhasil disimpan.<br><br>
            <span class="uid-badge">{{ uid }}</span>
        </p>
        <a href="/" class="btn">KEMBALI KE HOME</a>
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/get-logs', methods=['GET'])
def api_get_logs():
    try:
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
        return render_template_string(SUCCESS_TEMPLATE, nama=nama, uid=uid)
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
    
    try:
        supabase.table("temp_scan").update({"uid": uid_kartu, "waktu": datetime.datetime.now().isoformat()}).eq("id", 1).execute()
    except Exception as e:
        print("Error update temp scan:", e)

    user_query = supabase.table("users").select("nama").eq("uid", uid_kartu).execute()
    
    if not user_query.data:
        return jsonify({"akses": False, "pesan": "Tidak Terdaftar"}), 403

    nama_user = user_query.data[0]['nama']
    log_query = supabase.table("logs").select("status").eq("uid", uid_kartu).order("id", desc=True).limit(1).execute()
    
    status_baru = "Masuk"
    if log_query.data and log_query.data[0]['status'] == "Masuk":
        status_baru = "Keluar"

    log_data = {"uid": uid_kartu, "nama": nama_user, "status": status_baru, "waktu": datetime.datetime.now().isoformat()}
    supabase.table("logs").insert(log_data).execute()

    return jsonify({"akses": True, "nama": nama_user, "status": status_baru}), 200

if __name__ == '__main__':
    app.run(debug=True)

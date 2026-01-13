from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import datetime
import os

app = Flask(__name__)
DB_NAME = "database.db"
SESSION_LIMIT_SECONDS = 2 * 60 * 60  # 2 Hours (matches your frontend timer)

# --- Database Setup ---
def init_db():
    """Initializes the database with the sessions table + visible column."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Added 'visible' column: 1 = Show on Dashboard, 0 = Hidden (Archived for Print)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            section TEXT,
            pc_number TEXT NOT NULL,
            teacher TEXT,
            room TEXT,
            login_time TIMESTAMP,
            logout_time TIMESTAMP,
            visible INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on start
init_db()

# --- Routes for HTML Pages ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/print.html')
def print_page():
    return render_template('print.html')

@app.route('/<page_name>.html')
def render_page(page_name):
    try:
        return render_template(f'{page_name}.html')
    except:
        return "Page not found", 404

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# --- API: Student Login ---
@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.json
    
    student_id = data.get('id')
    section = data.get('section')
    pc_number = data.get('pc')
    teacher = data.get('teacher')
    room = data.get('room')
    login_time = datetime.datetime.now()

    if not student_id or not pc_number:
        return jsonify({"message": "Missing Student ID or PC Number"}), 400

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if this PC is already active
        cursor.execute('''
            SELECT * FROM sessions 
            WHERE pc_number = ? AND logout_time IS NULL
        ''', (pc_number,))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({"message": f"PC {pc_number} is already in use!"}), 409

        # Insert new session (visible defaults to 1)
        cursor.execute('''
            INSERT INTO sessions (student_id, section, pc_number, teacher, room, login_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, section, pc_number, teacher, room, login_time))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Login Success: {student_id} on PC {pc_number}")
        return jsonify({"message": "Session started successfully", "status": "success"}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

# --- API: Student Logout ---
@app.route('/api/logout', methods=['POST'])
def logout_api():
    data = request.json
    student_id = data.get('id')
    pc_number = data.get('pc')
    logout_time = datetime.datetime.now()

    if not student_id or not pc_number:
        return jsonify({"message": "Missing info"}), 400

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Find the ACTIVE session
        cursor.execute('''
            SELECT id FROM sessions 
            WHERE student_id = ? AND pc_number = ? AND logout_time IS NULL
        ''', (student_id, pc_number))
        
        record = cursor.fetchone()

        if not record:
            conn.close()
            return jsonify({"message": "No active session found."}), 404

        # Update logout time
        session_id = record[0]
        cursor.execute('''
            UPDATE sessions 
            SET logout_time = ? 
            WHERE id = ?
        ''', (logout_time, session_id))
        
        conn.commit()
        conn.close()

        print(f"🚪 Logout Success: {student_id} from PC {pc_number}")
        return jsonify({"message": "Logged out successfully", "status": "success"}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

# --- API: Fetch Logs (For Dashboard - ONLY VISIBLE ITEMS) ---
@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get all records where visible = 1 (Active on Dashboard)
    cursor.execute('SELECT * FROM sessions WHERE visible = 1 ORDER BY login_time DESC')
    rows = cursor.fetchall()
    conn.close()

    logs = []
    current_time = datetime.datetime.now()

    for row in rows:
        try:
            t_in = datetime.datetime.fromisoformat(str(row[6]))
            time_in_str = t_in.strftime("%I:%M %p")
            date_str = t_in.strftime("%Y-%m-%d")
        except:
            t_in = None
            time_in_str = "Error"
            date_str = ""

        time_out_str = "-"
        status = "Active"

        # Check Status
        if row[7]: # If logout_time exists
            try:
                t_out = datetime.datetime.fromisoformat(str(row[7]))
                time_out_str = t_out.strftime("%I:%M %p")
                status = "Completed"
            except:
                pass
        else:
            # Check for Timeout
            if t_in and (current_time - t_in).total_seconds() > SESSION_LIMIT_SECONDS:
                status = "Timeout"

        logs.append({
            "id": row[1],
            "section": row[2],
            "pc": row[3],
            "teacher": row[4],
            "timeIn": time_in_str,
            "timeOut": time_out_str,
            "date": date_str,
            "status": status
        })

    return jsonify(logs)

# --- API: Fetch PRINT Logs (Gets EVERYTHING, even hidden ones) ---
@app.route('/api/print_logs', methods=['GET'])
def get_print_logs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get ALL records regardless of 'visible' status
    cursor.execute('SELECT * FROM sessions ORDER BY login_time DESC')
    rows = cursor.fetchall()
    conn.close()

    logs = []
    current_time = datetime.datetime.now()

    # Reuse same logic for formatting
    for row in rows:
        try:
            t_in = datetime.datetime.fromisoformat(str(row[6]))
            time_in_str = t_in.strftime("%I:%M %p")
            date_str = t_in.strftime("%Y-%m-%d")
        except:
            t_in = None
            time_in_str = "Error"
            date_str = ""

        time_out_str = "-"
        status = "Active"

        if row[7]: 
            try:
                t_out = datetime.datetime.fromisoformat(str(row[7]))
                time_out_str = t_out.strftime("%I:%M %p")
                status = "Completed"
            except:
                pass
        else:
            if t_in and (current_time - t_in).total_seconds() > SESSION_LIMIT_SECONDS:
                status = "Timeout"

        logs.append({
            "id": row[1],
            "section": row[2],
            "pc": row[3],
            "teacher": row[4],
            "timeIn": time_in_str,
            "timeOut": time_out_str,
            "date": date_str,
            "status": status
        })

    return jsonify(logs)

# --- API: Force Logout ---
@app.route('/api/force_logout', methods=['POST'])
def force_logout():
    data = request.json
    student_id = data.get('id')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE sessions SET logout_time = ? 
        WHERE student_id = ? AND logout_time IS NULL
    ''', (datetime.datetime.now(), student_id))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"message": "Student is not currently active."}), 400
        
    conn.commit()
    conn.close()
    print(f"⚠️ Teacher Forced Logout: {student_id}")
    return jsonify({"message": "Session ended successfully."}), 200

# --- API: Clear Logs (HIDES them, does not delete) ---
@app.route('/api/clear_logs', methods=['POST'])
def clear_logs():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Soft Delete: Update 'visible' to 0 instead of deleting
        cursor.execute('UPDATE sessions SET visible = 0 WHERE visible = 1')
        
        conn.commit()
        conn.close()
        
        print("Logs hidden from dashboard (Archived for Print).")
        return jsonify({"message": "Dashboard cleared successfully"}), 200
        
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
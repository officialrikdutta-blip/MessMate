import os
import sqlite3
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import mysql.connector
    HAS_MYSQL = True
except:
    HAS_MYSQL = False

app = Flask(__name__)
app.secret_key = 'mess_mate_secret_key_123'

USERS = {
    "riya": "riya123", "aman": "aman123", "priya": "priya456",
    "rohit": "rohit789", "sneha": "sneha123", "vikas": "vikas123",
    "ananya": "ananya123", "karan": "karan123", "pooja": "pooja123", "rahul": "rahul123" ,
    "rik": "rik789", "anshu": "anshu123", "yoshita": "yoshi123","shouvik": "shouvik123", "ridhibrata": "ridhi123" ,"soumoda":"dada420",
    "manishda": "dadabolekotha", "shreyanks": "shrey696969"
    
}
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

def get_db_connection():
    if HAS_MYSQL:
        try:
            host = os.environ.get('DB_HOST')
            user = os.environ.get('DB_USER')
            password = os.environ.get('DB_PASSWORD')
            port = os.environ.get('DB_PORT')
            database = os.environ.get('DB_NAME')

            # Agar Render pe 5 variables hai toh Aiven connect karega
            if host and user and password and database:
                print(f"--> Trying Aiven MySQL: {host}")
                return mysql.connector.connect(
                    host=host,
                    user=user,
                    password=password,
                    port=int(port) if port else 21156,
                    database=database,
                    autocommit=True
                )
        except Exception as e:
            print(f"MySQL Cloud Connection Failed: {e}")

    print("--> Using Local SQLite (Fallback)")
    conn = sqlite3.connect('messmate.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def is_sqlite_conn(db):
    return isinstance(db, sqlite3.Connection)

def execute_query(cur, query, params=None, db=None):
    if db and is_sqlite_conn(db):
        query = query.replace("%s", "?")
    if params:
        cur.execute(query, params)
    else:
        cur.execute(query)

def init_db():
    db = get_db_connection()
    sqlite = is_sqlite_conn(db)
    cur = db.cursor()

    if sqlite:
        cur.execute('''CREATE TABLE IF NOT EXISTS menus (day TEXT PRIMARY KEY, breakfast TEXT, lunch TEXT, dinner TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS votes (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, choice TEXT, date TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, message TEXT, date TEXT)''')
    else:
        cur.execute('''CREATE TABLE IF NOT EXISTS menus (day VARCHAR(20) PRIMARY KEY, breakfast VARCHAR(100), lunch VARCHAR(100), dinner VARCHAR(100))''')
        cur.execute('''CREATE TABLE IF NOT EXISTS votes (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100), choice VARCHAR(10), date VARCHAR(20))''')
        cur.execute('''CREATE TABLE IF NOT EXISTS feedback (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), message TEXT, date VARCHAR(50))''')

    cur.execute("SELECT COUNT(*) FROM menus")
    count = cur.fetchone()[0]
    if count == 0:
        default_menus = [
            ("Monday", "Puri Sabji", "Rajma Chawal", "Paneer + Roti"),
            ("Tuesday", "Idli Sambhar", "Chole Bhature", "Fried Rice"),
            ("Wednesday", "Poha", "Dal Makhni + Naan", "Chicken Curry"),
            ("Thursday", "Aloo Paratha", "Kadhi Chawal", "Egg Curry"),
            ("Friday", "Upma", "Veg Biryani", "Matar Paneer"),
            ("Saturday", "Dosa", "Pav Bhaji", "Veg Pulao"),
            ("Sunday", "Chole Bhature", "Chicken Biryani", "Special Thali")
        ]
        q = "INSERT INTO menus VALUES (?,?,?,?)" if sqlite else "INSERT INTO menus VALUES (%s,%s,%s,%s)"
        cur.executemany(q, default_menus)
    db.commit()
    cur.close()
    db.close()

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username').lower().strip()
        pwd = request.form.get('password')
        if user in USERS and USERS[user] == pwd:
            session['student'] = True
            session['username'] = user
            return redirect('/')
        else:
            return "<h3>Galat ID / Password</h3><a href='/login'>Try Again</a>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
def index():
    if 'student' not in session and 'admin' not in session:
        return redirect('/login')
    name = session.get('username', 'Admin').capitalize() if 'student' in session else 'Admin'
    return render_template('index.html', user=name)

@app.route('/menu')
def menu():
    if 'student' not in session and 'admin' not in session:
        return redirect('/login')
    db = get_db_connection()
    sqlite = is_sqlite_conn(db)
    cur = db.cursor()
    cur.execute("SELECT * FROM menus")
    rows = cur.fetchall()
    cur.close()
    db.close()
    order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    def get_day(r):
        return r['day'] if sqlite else r[0]
    rows = sorted(rows, key=lambda x: order.index(get_day(x)) if get_day(x) in order else 99)
    weekly_menu = {}
    for row in rows:
        if sqlite:
            weekly_menu[row['day']] = {"breakfast": row['breakfast'], "lunch": row['lunch'], "dinner": row['dinner']}
        else:
            weekly_menu[row[0]] = {"breakfast": row[1], "lunch": row[2], "dinner": row[3]}
    today_name = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A")
    today_menu = weekly_menu.get(today_name)
    name = session.get('username', 'Admin').capitalize() if 'student' in session else 'Admin'
    return render_template('menu.html', today_name=today_name, today_menu=today_menu, full_menu=weekly_menu, user=name)

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'student' not in session and 'admin' not in session:
        return redirect('/login')
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y")
    username = session.get('username', 'admin')
    db = get_db_connection()
    cur = db.cursor()
    execute_query(cur, "SELECT * FROM votes WHERE username=%s AND date=%s", (username, today), db)
    already = cur.fetchone()
    cur.close()
    db.close()
    if already:
        return render_template('already_voted.html', user=username.capitalize())
    if request.method == 'POST':
        choice = request.form.get('choice')
        db = get_db_connection()
        cur = db.cursor()
        execute_query(cur, "INSERT INTO votes (username, choice, date) VALUES (%s, %s, %s)", (username, choice, today), db)
        db.commit()
        cur.close()
        db.close()
        return redirect('/vote-result')
    return render_template('vote.html', user=username.capitalize())

@app.route('/vote-result')
def vote_result():
    if 'student' not in session and 'admin' not in session:
        return redirect('/login')
    db = get_db_connection()
    cur = db.cursor()
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y")
    execute_query(cur, "SELECT COUNT(*) FROM votes WHERE date=%s AND choice='Yes'", (today,), db)
    yes = cur.fetchone()[0]
    execute_query(cur, "SELECT COUNT(*) FROM votes WHERE date=%s AND choice='No'", (today,), db)
    no = cur.fetchone()[0]
    cur.close()
    db.close()
    return render_template('result.html', yes=yes, no=no)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'student' not in session and 'admin' not in session:
        return redirect('/login')
    name = session.get('username', '').capitalize()
    if request.method == 'POST':
        msg = request.form.get('message')
        today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y %H:%M")
        db = get_db_connection()
        cur = db.cursor()
        execute_query(cur, "INSERT INTO feedback (name, message, date) VALUES (%s, %s, %s)", (name, msg, today), db)
        db.commit()
        cur.close()
        db.close()
        return render_template('feedback.html', user=name)
    return render_template('feedback.html', user=name)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/feedback')
        else:
            return "<h3>Galat Admin Password</h3><a href='/admin/login'>Try Again</a>"
    return render_template('admin_login.html')

@app.route('/admin/menu', methods=['GET', 'POST'])
def admin_menu_edit():
    if 'admin' not in session:
        return redirect('/admin/login')
    db = get_db_connection()
    cur = db.cursor()
    if request.method == 'POST':
        day = request.form.get('day')
        b = request.form.get('breakfast')
        l = request.form.get('lunch')
        d = request.form.get('dinner')
        execute_query(cur, "UPDATE menus SET breakfast=%s, lunch=%s, dinner=%s WHERE day=%s", (b,l,d,day), db)
        db.commit()
    cur.execute("SELECT * FROM menus")
    rows = cur.fetchall()
    cur.close()
    db.close()
    weekly_menu_db = {}
    for row in rows:
        # Handle both sqlite Row and mysql tuple
        try:
            weekly_menu_db[row[0]] = {"breakfast": row[1], "lunch": row[2], "dinner": row[3]}
        except:
            weekly_menu_db[row['day']] = {"breakfast": row['breakfast'], "lunch": row['lunch'], "dinner": row['dinner']}
    return render_template('admin_menu.html', full_menu=weekly_menu_db)

@app.route('/admin/feedback')
def admin_feedback():
    if 'admin' not in session:
        return redirect('/admin/login')
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT * FROM feedback ORDER BY id DESC")
    feedbacks = cur.fetchall()
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y")
    execute_query(cur, "SELECT * FROM votes WHERE date=%s ORDER BY id DESC", (today,), db)
    votes = cur.fetchall()
    cur.close()
    db.close()
    return render_template('admin_feedback.html', feedbacks=feedbacks, votes=votes)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

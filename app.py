from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import bcrypt
from functools import wraps

app = Flask(__name__)
app.secret_key = "secret-key-123"  # ganti dengan string random

# --- Koneksi Database ---
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",   # ganti password mysql kamu
    database="payment_db"
)
cursor = db.cursor(dictionary=True)


# --- Decorator untuk proteksi login ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            flash("Harap login terlebih dahulu!", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# --- Login Admin ---
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password'].encode('utf-8')  # encode input user

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        print("DEBUG login - user result:", user)  # debugging

        if user:
            stored_hash = user['password'].encode('utf-8')
            if bcrypt.checkpw(password, stored_hash):
                session['admin'] = user['username']
                flash("Login berhasil!", "success")
                return redirect(url_for("admin"))
            else:
                session.pop('admin', None)
                flash("Password salah!", "danger")
        else:
            session.pop('admin', None)
            flash("Username tidak ditemukan!", "danger")

    return render_template("login.html")


# --- Register Admin ---
@app.route('/register_admin', methods=["GET", "POST"])
@login_required
def register_admin():
    if request.method == "POST":
        username = request.form['username']
        raw_password = request.form['password'].encode('utf-8')
        hashed = bcrypt.hashpw(raw_password, bcrypt.gensalt()).decode('utf-8')

        # cek username sudah ada atau belum
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing = cursor.fetchone()

        if existing:
            flash("Username sudah terdaftar, gunakan nama lain!", "danger")
            return redirect(url_for("register_admin"))

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            db.commit()
            flash("Admin baru berhasil dibuat!", "success")
            return redirect(url_for("admin"))
        except mysql.connector.Error as e:
            flash(f"Gagal membuat admin: {e}", "danger")

    return render_template("register_admin.html")


# --- Logout ---
@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash("Berhasil logout.", "info")
    return redirect(url_for("login"))


# --- Dashboard Admin ---
@app.route("/admin")
@login_required
def admin():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    status = request.args.get("status")

    query = "SELECT * FROM transactions WHERE 1=1"
    values = []

    if start_date:
        query += " AND created_at >= %s"
        values.append(start_date)
    if end_date:
        query += " AND created_at <= %s"
        values.append(end_date)
    if status:
        query += " AND status = %s"
        values.append(status)

    cursor.execute(query, tuple(values))
    transactions = cursor.fetchall()

    # data untuk chart
    labels = [t['customer_name'] for t in transactions]
    amounts = [t['amount'] for t in transactions]

    return render_template(
        "admin.html",
        transactions=transactions,
        labels=labels,
        amounts=amounts,
        request=request
    )


# --- Halaman Form Pembayaran ---
@app.route('/')
def index():
    return render_template("index.html")


@app.route('/pay', methods=['POST'])
def pay():
    name = request.form.get("name")
    email = request.form.get("email")
    try:
        amount = float(request.form.get("amount"))
    except:
        return render_template("error.html", message="Jumlah tidak valid")

    # Simulasi data kartu
    card_number = request.form.get("card_number")
    expiry = request.form.get("expiry")
    cvv = request.form.get("cvv")

    # Aturan simulasi: kalau amount > 0 maka success
    status = "success" if amount > 0 else "failed"

    sql = "INSERT INTO transactions (customer_name, customer_email, amount, status) VALUES (%s, %s, %s, %s)"
    values = (name, email, amount, status)
    cursor.execute(sql, values)
    db.commit()

    tx_id = cursor.lastrowid

    if status == "success":
        return redirect(url_for("success", tx_id=tx_id))
    else:
        return render_template("error.html", message="Pembayaran gagal")


@app.route('/success')
def success():
    tx_id = request.args.get("tx_id")
    cursor.execute("SELECT * FROM transactions WHERE id=%s", (tx_id,))
    tx = cursor.fetchone()
    if not tx:
        return render_template("error.html", message="Transaksi tidak ditemukan")
    return render_template("success.html", tx=tx)


# --- Route Tambah Admin Otomatis (testing awal) ---
@app.route('/create_admin')
def create_admin():
    username = "admin"
    raw_password = "admin123".encode('utf-8')
    hashed = bcrypt.hashpw(raw_password, bcrypt.gensalt()).decode('utf-8')

    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
    db.commit()
    return f"User {username} berhasil dibuat dengan password 'admin123' (hashed)."


# --- Run App ---
if __name__ == "__main__":
    app.run(debug=True)

import pymysql
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = "7d441f27d441f27567d441f2b6176a"

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'serverkey2020@gmail.com'
app.config['MAIL_PASSWORD'] = 'vpcm xdyk dayy oluj'

mail = Mail(app)

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="Food_Alert_System",
        charset="utf8",
        cursorclass=pymysql.cursors.DictCursor
    )

def send_expiry_alerts():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()

        tomorrow = date.today() + timedelta(days=1)

        cursor.execute("""
            SELECT p.*, m.email AS manufacturer_email
            FROM product p
            JOIN manufacturer m ON p.manufacturer_id = m.id
            WHERE p.expiry_date = %s AND p.alert_count < 3
        """, (tomorrow,))

        products = cursor.fetchall()

        for p in products:
            product_id = p["id"]

            try:
                msg = Message(
                    subject="Product Expiry Alert",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[p["manufacturer_email"]]
                )
                msg.body = f'Product "{p["product_name"]}" will expire tomorrow.'
                mail.send(msg)
            except Exception as e:
                print("Error:", e)

            cursor.execute("""
                SELECT DISTINCT u.email
                FROM orders o
                JOIN user u ON o.user_id = u.id
                WHERE o.product_id = %s
            """, (product_id,))

            users = cursor.fetchall()

            for u in users:
                try:
                    msg = Message(
                        subject="Expiry Notice",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[u["email"]]
                    )
                    msg.body = f'Product "{p["product_name"]}" expires tomorrow.'
                    mail.send(msg)
                except Exception as e:
                    print("Error:", e)

            cursor.execute("""
                UPDATE product SET alert_count = alert_count + 1
                WHERE id = %s
            """, (product_id,))

        conn.commit()
        conn.close()

scheduler = BackgroundScheduler()
scheduler.add_job(func=send_expiry_alerts, trigger="interval", minutes=1)
scheduler.start()

@app.route("/")
def index():
    return render_template("index.html")

#-------------------------------------------ADMIN----------------------------------------------

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin":
            session["admin"] = True
            flash("Login successful!", "success")
            return redirect(url_for("admin_home"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("admin_login.html")

@app.route("/admin_home")
def admin_home():
    return render_template("admin_home.html")

@app.route("/admin_add_manufacturer", methods=["GET", "POST"])
def admin_add_manufacturer():
    if request.method == "POST":
        name = request.form["name"]
        contact = request.form["contact"]
        email = request.form["email"]
        address = request.form["address"]
        password = request.form["password"]

        image_file = request.files["image"]

        if image_file and image_file.filename != "":
            image_name = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_name)
            image_file.save(image_path)
        else:
            image_name = None

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO manufacturer
                (name, contact, email, address, image, password)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, contact, email, address, image_name, password))

            conn.commit()
            flash("Manufacturer added successfully!", "success")

        except Exception as e:
            conn.rollback()
            flash("Error: Email may already exist!", "danger")

        finally:
            conn.close()

        return redirect(url_for("admin_add_manufacturer"))

    return render_template("admin_add_manufacturer.html")

@app.route("/admin_view_manufacturer")
def admin_view_manufacturer():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM manufacturer")
    manufacturers = cursor.fetchall()

    conn.close()

    return render_template("admin_view_manufacturer.html", manufacturers=manufacturers)

@app.route("/admin_edit_manufacturer/<int:id>", methods=["GET", "POST"])
def admin_edit_manufacturer(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        contact = request.form["contact"]
        email = request.form["email"]
        address = request.form["address"]

        image_file = request.files["image"]

        cursor.execute("SELECT image FROM manufacturer WHERE id=%s", (id,))
        old_data = cursor.fetchone()
        old_image = old_data["image"]

        if image_file and image_file.filename != "":
            image_name = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_name)
            image_file.save(image_path)
        else:
            image_name = old_image

        cursor.execute("""
            UPDATE manufacturer 
            SET name=%s, contact=%s, email=%s, address=%s, image=%s
            WHERE id=%s
        """, (name, contact, email, address, image_name, id))

        conn.commit()
        flash("Updated successfully!", "success")
        return redirect(url_for("admin_view_manufacturer"))

    cursor.execute("SELECT * FROM manufacturer WHERE id=%s", (id,))
    manufacturer = cursor.fetchone()
    conn.close()

    return render_template("admin_edit_manufacturer.html", manufacturer=manufacturer)

@app.route("/delete_manufacturer/<int:id>")
def delete_manufacturer(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM manufacturer WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    flash("Manufacturer deleted successfully!", "success")
    return redirect(url_for("admin_view_manufacturer"))

@app.route("/admin_view_user")
def admin_view_user():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()

    conn.close()

    return render_template("admin_view_user.html", users=users)

@app.route("/admin_expired_food_details")
def admin_expired_food_details():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            p.*, 
            m.name AS manufacturer_name,
            m.email,
            m.contact,
            m.address,
            m.image AS manufacturer_image,
            DATEDIFF(DATE(p.expiry_date), CURDATE()) AS days_left
        FROM product p
        JOIN manufacturer m ON p.manufacturer_id = m.id
        WHERE DATE(p.expiry_date) >= CURDATE()
        ORDER BY p.expiry_date ASC
    """)

    expired_products = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_expired_food_details.html",
        expired_products=expired_products
    )

#-------------------------------------------MANUFACTURER----------------------------------------------

@app.route("/manufacturer_login", methods=["GET", "POST"])
def manufacturer_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM  manufacturer
            WHERE email=%s AND password=%s
        """, (email, password))

        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Login successful!", "success")
            return redirect(url_for("manufacturer_home"))
        else:
            flash("Invalid email or password", "danger")

    return render_template("manufacturer_login.html")

@app.route("/manufacturer_home")
def manufacturer_home():
    return render_template("manufacturer_home.html")

@app.route("/manufacturer_add_product", methods=["GET", "POST"])
def manufacturer_add_product():
    if "user_id" not in session:
        return redirect(url_for("manufacturer_login"))

    if request.method == "POST":
        product_name = request.form["product_name"]
        rate = request.form["rate"]
        stock = request.form["stock"]
        unit_type = request.form["unit_type"]
        manufacture_date = request.form["manufacture_date"]
        expiry_date = request.form["expiry_date"]

        image_file = request.files["image"]

        if image_file and image_file.filename != "":
            image_name = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_name)
            image_file.save(image_path)
        else:
            image_name = None

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO product
                (manufacturer_id, product_name, rate, stock, unit_type, manufacture_date, expiry_date, image)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session["user_id"],
                product_name,
                rate,
                stock,
                unit_type,
                manufacture_date,
                expiry_date,
                image_name
            ))

            conn.commit()
            flash("Product added successfully!", "success")

        except Exception as e:
            conn.rollback()
            flash("Error adding product!", "danger")

        finally:
            conn.close()

        return redirect(url_for("manufacturer_add_product"))

    return render_template("manufacturer_add_product.html")

@app.route("/manufacturer_view_orders")
def manufacturer_view_orders():
    if "user_id" not in session:
        return redirect(url_for("manufacturer_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            o.*, 
            u.name AS user_name,
            u.email,
            u.phone,
            p.product_name,
            p.image
        FROM orders o
        JOIN user u ON o.user_id = u.id
        JOIN product p ON o.product_id = p.id
        WHERE p.manufacturer_id = %s
        ORDER BY o.order_date DESC
    """, (session["user_id"],))

    orders = cursor.fetchall()
    conn.close()

    return render_template("manufacturer_view_orders.html", orders=orders)

@app.route("/manufacturer_view_expired_details")
def manufacturer_view_expired_details():
    if "user_id" not in session:
        return redirect(url_for("manufacturer_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            p.*, 
            DATEDIFF(DATE(p.expiry_date), CURDATE()) AS days_left
        FROM product p
        WHERE p.manufacturer_id = %s
        ORDER BY p.expiry_date ASC
    """, (session["user_id"],))

    products = cursor.fetchall()
    conn.close()

    return render_template(
        "manufacturer_view_expired_details.html",
        products=products
    )

#-------------------------------------------USER----------------------------------------------

@app.route("/user_register", methods=["GET", "POST"])
def user_register():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        address = request.form["address"]
        password = request.form["password"]

        image_file = request.files["image"]

        if image_file and image_file.filename != "":
            image_name = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_name)
            image_file.save(image_path)
        else:
            image_name = None

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO user 
                (name, phone, email, dob, gender, address, password, image)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, phone, email, dob, gender, address, password, image_name))

            conn.commit()
            flash("Registration successful!", "success")
            return redirect(url_for("user_login"))

        except Exception as e:
            conn.rollback()
            flash("Error: Email may already exist!", "danger")

        finally:
            conn.close()

    return render_template("user_register.html")

@app.route("/user_login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM user
            WHERE email=%s AND password=%s
        """, (email, password))

        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Login successful!", "success")
            return redirect(url_for("user_home"))
        else:
            flash("Invalid email or password", "danger")

    return render_template("user_login.html")

@app.route("/user_home")
def user_home():
    return render_template("user_home.html")

@app.route("/user_view_product")
def user_view_product():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*, m.name AS manufacturer_name
        FROM product p
        JOIN manufacturer m ON p.manufacturer_id = m.id
    """)

    products = cursor.fetchall()
    conn.close()

    return render_template("user_view_product.html", products=products)

@app.route("/buy_product/<int:product_id>", methods=["GET", "POST"])
def buy_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("user_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM product WHERE id=%s", (product_id,))
    product = cursor.fetchone()

    if request.method == "POST":
        quantity = int(request.form["quantity"])

        if quantity > product["stock"]:
            flash("Not enough stock!", "danger")
            return redirect(url_for("user_view_product"))

        total_price = quantity * float(product["rate"])

        cursor.execute("""
            INSERT INTO orders (user_id, product_id, quantity, total_price)
            VALUES (%s, %s, %s, %s)
        """, (session["user_id"], product_id, quantity, total_price))

        cursor.execute("""
            UPDATE product SET stock = stock - %s WHERE id=%s
        """, (quantity, product_id))

        conn.commit()
        conn.close()

        flash("Order placed successfully!", "success")
        return redirect(url_for("user_view_product"))

    conn.close()
    return render_template("buy_product.html", product=product)

@app.route("/user_view_expired_details")
def user_view_expired_details():
    if "user_id" not in session:
        return redirect(url_for("user_login"))

    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            p.*,
            o.quantity,
            o.order_date,
            DATEDIFF(DATE(p.expiry_date), CURDATE()) AS days_left
        FROM orders o
        JOIN product p ON o.product_id = p.id
        WHERE o.user_id = %s
    """

    params = [session["user_id"]]

    if search:
        query += " AND p.product_name LIKE %s"
        params.append(f"%{search}%")

    query += " ORDER BY p.expiry_date ASC"

    cursor.execute(query, params)
    products = cursor.fetchall()
    conn.close()

    return render_template(
        "user_view_expired_details.html",
        products=products
    )

if __name__ == "__main__":
    if not scheduler.running:
        scheduler.start()

    app.run(debug=True, use_reloader=False, host="0.0.0.0")
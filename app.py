from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from werkzeug.security import check_password_hash
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "defaultsecretkey")

# --- DB Connection ---
def get_db_connection():
    import psycopg2
    import psycopg2.extras
    import os

    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# --- Login Required Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return redirect(url_for('admin_properties'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/admin/dashboard')
        else:
            flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template('dashboard.html')

@app.route('/admin/properties')
@login_required
def admin_properties():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties")
    properties = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_properties.html', properties=properties)

@app.route('/admin/properties/add', methods=['GET', 'POST'])
@login_required
def add_property():
    if request.method == 'POST':
        state = request.form['state']
        location = request.form['location']
        name = request.form['name']
        bedrooms = request.form['bedrooms']
        guests = request.form['guests']
        beds = request.form['beds']
        baths = request.form['baths']
        price = request.form['price']
        short_description = request.form['short_description']
        visible = 'visible' in request.form

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO properties (state, location, name, bedrooms, guests, beds, baths, price_per_night, short_description, visible)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (state, location, name, bedrooms, guests, beds, baths, price, short_description, visible))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_properties'))
    return render_template('add_property.html')

@app.route('/admin/edit_property/<int:property_id>', methods=['GET', 'POST'])
@login_required
def edit_property(property_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        state = request.form['state']
        location = request.form['location']
        name = request.form['name']
        bedrooms = request.form['bedrooms']
        guests = request.form['guests']
        beds = request.form['beds']
        baths = request.form['baths']
        price = request.form['price']
        short_description = request.form['short_description']
        visible = 'visible' in request.form

        cursor.execute("""
            UPDATE properties SET state=%s, location=%s, name=%s, bedrooms=%s,
            guests=%s, beds=%s, baths=%s, price_per_night=%s, short_description=%s, visible=%s
            WHERE id=%s
        """, (state, location, name, bedrooms, guests, beds, baths, price, short_description, visible, property_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_properties'))
    else:
        cursor.execute("SELECT * FROM properties WHERE id = %s", (property_id,))
        prop = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_property.html', prop=prop)

@app.route('/admin/delete_property/<int:property_id>')
@login_required
def delete_property(property_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM properties WHERE id = %s", (property_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_properties'))

@app.route('/admin/destinations')
@login_required
def view_destinations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations")
    destinations = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_destinations.html', destinations=destinations)

@app.route('/admin/destinations/add', methods=['GET', 'POST'])
@login_required
def add_destination():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        more_info = request.form['more_info']
        visible = 'visible' in request.form

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO destinations (name, description, more_info, visible)
            VALUES (%s, %s, %s, %s)
        """, (name, description, more_info, visible))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_destinations'))
    return render_template('add_destination.html')

@app.route('/admin/destinations/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_destination(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        more_info = request.form['more_info']
        visible = 'visible' in request.form

        cursor.execute("""
            UPDATE destinations SET name=%s, description=%s, more_info=%s, visible=%s WHERE id=%s
        """, (name, description, more_info, visible, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_destinations'))
    else:
        cursor.execute("SELECT * FROM destinations WHERE id = %s", (id,))
        dest = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_destination.html', dest=dest)

@app.route('/admin/destinations/delete/<int:id>')
@login_required
def delete_destination(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM destinations WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('view_destinations'))

@app.route('/admin/cruises')
@login_required
def view_cruises():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cruises")
    cruises = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_cruises.html', cruises=cruises)

@app.route('/admin/cruises/add', methods=['GET', 'POST'])
@login_required
def add_cruise():
    if request.method == 'POST':
        name = request.form['name']
        short_description = request.form['short_description']
        visible = 'visible' in request.form

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cruises (name, short_description, visible)
            VALUES (%s, %s, %s)
        """, (name, short_description, visible))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_cruises'))
    return render_template('add_cruise.html')

@app.route('/admin/cruises/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cruise(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        short_description = request.form['short_description']
        visible = 'visible' in request.form

        cursor.execute("""
            UPDATE cruises SET name=%s, short_description=%s, visible=%s WHERE id=%s
        """, (name, short_description, visible, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_cruises'))
    else:
        cursor.execute("SELECT * FROM cruises WHERE id = %s", (id,))
        cruise = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_cruise.html', cruise=cruise)

@app.route('/admin/cruises/delete/<int:id>')
@login_required
def delete_cruise(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cruises WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('view_cruises'))

if __name__ == '__main__':
    app.run(debug=True)

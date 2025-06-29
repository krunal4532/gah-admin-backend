from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from functools import wraps
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.secret_key = 'GAH@LWR2025'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Reusable DB connection
def get_db_connection():
    return psycopg2.connect(
        host="your_host",
        database="your_db",
        user="admin",
        password="admin123",
        port=5432,
        sslmode="require",
        cursor_factory=psycopg2.extras.RealDictCursor  # ✅ Add this
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print("Form username:", username)
        print("Form password:", password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        # ✅ Add debug info after fetching user
        print("DB username:", user['username'] if user else None)
        print("Hash matches:", check_password_hash(user['password_hash'], password) if user else None)

        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/admin/dashboard')
        else:
            flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/')
def home():
    return redirect(url_for('admin_properties'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/properties')
@login_required
def admin_properties():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties")
    properties = cursor.fetchall()
    for prop in properties:
        cursor.execute("SELECT image_filename FROM property_images WHERE property_id = %s", (prop['id'],))
        prop['images'] = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/properties.html', properties=properties)

@app.route('/admin/properties/<int:property_id>/toggle', methods=['POST'])
def toggle_visibility(property_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT visible FROM properties WHERE id = %s", (property_id,))
    current = cursor.fetchone()
    new_value = not current['visible']
    cursor.execute("UPDATE properties SET visible = %s WHERE id = %s", (new_value, property_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_properties'))

@app.route('/admin/properties/add', methods=['GET', 'POST'])
def add_property():
    if request.method == 'POST':
        state = request.form['state']
        location = request.form['location']
        name = request.form['name']
        bedrooms = request.form['bedrooms']
        visible = 'visible' in request.form

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO properties (state, location, name, bedrooms, visible)
            VALUES (%s, %s, %s, %s, %s)
        """, (state, location, name, bedrooms, visible))
        property_id = cursor.lastrowid

        images = request.files.getlist('images')
        for image in images:
            if image.filename != '':
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute("""
    UPDATE properties 
    SET state=%s, location=%s, name=%s, bedrooms=%s, guests=%s, beds=%s, baths=%s, price=%s, short_description=%s, visible=%s 
    WHERE id=%s
""", (state, location, name, bedrooms, guests, beds, baths, price, short_description, visible, property_id))


        conn.commit()
        cursor.close()
        conn.close()
        flash("Property added successfully!")
        return redirect(url_for('admin_properties'))

    return render_template('admin/add_property.html')

@app.route('/admin/edit_property/<int:property_id>', methods=['GET', 'POST'])
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
        price_per_night = request.form['price_per_night']
        short_description = request.form['short_description']
        visible = 'visible' in request.form

        cursor.execute("""
            UPDATE properties 
            SET state=%s, location=%s, name=%s, bedrooms=%s, guests=%s, beds=%s, baths=%s,
                price_per_night=%s, short_description=%s, visible=%s
            WHERE id=%s
        """, (state, location, name, bedrooms, guests, beds, baths, price_per_night, short_description, visible, property_id))

        # Handle new image uploads
        images = request.files.getlist('images')
        for image in images:
            if image.filename:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute("INSERT INTO property_images (property_id, image_filename) VALUES (%s, %s)", (property_id, filename))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_properties'))

    cursor.execute("SELECT * FROM properties WHERE id=%s", (property_id,))
    property_data = cursor.fetchone()
    cursor.execute("SELECT * FROM property_images WHERE property_id=%s", (property_id,))
    images = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/edit_property.html', property=property_data, images=images)

@app.route('/admin/delete_property/<int:property_id>')
def delete_property(property_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image_filename FROM property_images WHERE property_id=%s", (property_id,))
    images = cursor.fetchall()
    for img in images:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img['image_filename']))
        except:
            pass
    cursor.execute("DELETE FROM properties WHERE id=%s", (property_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_properties'))

@app.route('/admin/delete_image/<int:image_id>/<int:property_id>')
def delete_image(image_id, property_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image_filename FROM property_images WHERE id=%s", (image_id,))
    img = cursor.fetchone()
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img['image_filename']))
    except:
        pass
    cursor.execute("DELETE FROM property_images WHERE id=%s", (image_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('edit_property', property_id=property_id))

# Other routes (destinations, cruises, APIs) should also be updated to use get_db_connection() the same way.
# Let me know if you'd like me to continue with those.


# View all destinations
@app.route('/admin/destinations')
@login_required
def view_destinations():
    conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='Krunal@4532',  # Replace with your actual password
    database='greataccess_db'  # Replace with your database name
)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations")
    destinations = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/destinations.html', destinations=destinations)


# Add destination
@app.route('/admin/destinations/add', methods=['GET', 'POST'])
def add_destination():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        more_info = request.form['more_info']
        visible = 'visible' in request.form

        image = request.files['image']
        filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cursor.execute("""
    INSERT INTO destinations (name, description, image_filename, visible, more_info)
    VALUES (%s, %s, %s, %s, %s)
""", (name, description, filename, visible, more_info))
        conn.commit()
        return redirect(url_for('view_destinations'))

    return render_template('admin/add_destination.html')

# Edit destination
@app.route('/admin/destinations/edit/<int:id>', methods=['GET', 'POST'])
def edit_destination(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        more_info = request.form['more_info']
        visible = 'visible' in request.form

        image = request.files['image']
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute("UPDATE destinations SET image_filename=%s WHERE id=%s", (filename, id))
        cursor.execute("""
            UPDATE destinations
            SET name=%s, description=%s, more_info=%s, visible=%s
            WHERE id=%s
        """, (name, description, more_info, visible, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_destinations'))

    cursor.execute("SELECT * FROM destinations WHERE id=%s", (id,))
    destination = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('admin/edit_destination.html', destination=destination)


    cursor.execute("SELECT * FROM destinations WHERE id=%s", (id,))
    destination = cursor.fetchone()
    return render_template('admin/edit_destination.html', destination=destination)

# Delete destination
@app.route('/admin/destinations/delete/<int:id>')
def delete_destination(id):
    cursor.execute("SELECT image_filename FROM destinations WHERE id=%s", (id,))
    image = cursor.fetchone()
    if image and image['image_filename']:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image['image_filename']))
        except:
            pass

    cursor.execute("DELETE FROM destinations WHERE id=%s", (id,))
    conn.commit()
    return redirect(url_for('view_destinations'))

# Toggle visibility
@app.route('/admin/destinations/toggle/<int:id>', methods=['POST'])
def toggle_destination_visibility(id):
    cursor.execute("SELECT visible FROM destinations WHERE id=%s", (id,))
    current = cursor.fetchone()
    new_value = not current['visible']
    cursor.execute("UPDATE destinations SET visible = %s WHERE id = %s", (new_value, id))
    conn.commit()
    return redirect(url_for('view_destinations'))
    
    # View all cruises
@app.route('/admin/cruises')
@login_required
def view_cruises():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cruises")
    cruises = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/cruises.html', cruises=cruises)


# Add cruise
@app.route('/admin/cruises/add', methods=['GET', 'POST'])
def add_cruise():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        visible = 'visible' in request.form

        image = request.files['image']
        filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cursor.execute("""
            INSERT INTO cruises (name, description, image_filename, visible)
            VALUES (%s, %s, %s, %s)
        """, (name, description, filename, visible))
        conn.commit()
        return redirect(url_for('view_cruises'))

    return render_template('admin/add_cruise.html')

# Edit cruise
@app.route('/admin/cruises/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cruise(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        visible = 'visible' in request.form

        image = request.files['image']
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute("UPDATE cruises SET image_filename=%s WHERE id=%s", (filename, id))

        cursor.execute("""
            UPDATE cruises
            SET name=%s, description=%s, visible=%s
            WHERE id=%s
        """, (name, description, visible, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_cruises'))

    cursor.execute("SELECT * FROM cruises WHERE id=%s", (id,))
    cruise = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('admin/edit_cruise.html', cruise=cruise)


# Delete cruise
@app.route('/admin/cruises/delete/<int:id>')
def delete_cruise(id):
    cursor.execute("SELECT image_filename FROM cruises WHERE id=%s", (id,))
    image = cursor.fetchone()
    if image and image['image_filename']:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image['image_filename']))
        except:
            pass

    cursor.execute("DELETE FROM cruises WHERE id=%s", (id,))
    conn.commit()
    return redirect(url_for('view_cruises'))

# Toggle visibility
@app.route('/admin/cruises/toggle/<int:id>', methods=['POST'])
def toggle_cruise_visibility(id):
    cursor.execute("SELECT visible FROM cruises WHERE id=%s", (id,))
    current = cursor.fetchone()
    new_value = not current['visible']
    cursor.execute("UPDATE cruises SET visible = %s WHERE id = %s", (new_value, id))
    conn.commit()
    return redirect(url_for('view_cruises'))

# API: Properties
@app.route('/api/properties')
def api_properties():
    cursor.execute("SELECT * FROM properties WHERE visible = TRUE")
    properties = cursor.fetchall()
    for prop in properties:
        cursor.execute("SELECT image_filename FROM property_images WHERE property_id = %s", (prop['id'],))
        prop['images'] = [img['image_filename'] for img in cursor.fetchall()]
    return jsonify(properties)

# API: Destinations
@app.route('/api/destinations')
def api_destinations():
    cursor.execute("SELECT * FROM destinations WHERE visible = TRUE")
    return jsonify(cursor.fetchall())

# API: Cruises
@app.route('/api/cruises')
def api_cruises():
    cursor.execute("SELECT * FROM cruises WHERE visible = TRUE")
    return jsonify(cursor.fetchall())
    
print("Registered routes:")
print(app.url_map)

# This file is served by Gunicorn when deployed on Render
# Don't run the app directly here in production

    
    

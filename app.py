import os
from decimal import Decimal
from functools import wraps
import uuid
from flask import Flask, flash, redirect, render_template, request, session, url_for, send_from_directory
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-change-me')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'project_shop',
    'port': 3306,
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {'current_user_id': session.get('user_id'), 'current_user_name': session.get('user_name')}


@app.route('/')
def home():
    category_id = request.args.get('category', type=int)
    query = request.args.get('q', '').strip()
    location_query = request.args.get('location', "").strip()

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute('SELECT id, name FROM categories ORDER BY name')
    categories = cur.fetchall()

    sql = '''
    SELECT l.id, l.title, l.price, l.location, l.status, l.created_at,
           c.name AS category_name, u.name AS seller_name,
           (
               SELECT li.image_path
               FROM listing_images li
               WHERE li.listing_id = l.id
               ORDER BY li.id
               LIMIT 1
           ) AS cover_image
    FROM listings l
    JOIN categories c ON l.category_id = c.id
    JOIN users u ON l.user_id = u.id
    WHERE 1=1
'''
    params = []

    if category_id:
        sql += ' AND l.category_id = %s'
        params.append(category_id)
    if query:
        sql += ' AND (l.title LIKE %s OR l.description LIKE %s OR l.location LIKE %s)'
        like = f'%{query}%'
        params.extend([like, like, like])
    if location_query:
        sql += ' AND l.location LIKE %s'
        params.append(f'%{location_query}%')

    sql += ' ORDER BY l.created_at DESC'
    cur.execute(sql, params)
    listings = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('home.html', listings=listings, categories=categories, selected_category=category_id, q=query, location_query=location_query)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if not name or not email or not password:
            flash('All fields are required.')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO users (name, email, password) VALUES (%s, %s, %s)',
                (name, email, password_hash)
            )
            conn.commit()
            flash('Account created. Please log in.')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('That email is already in use.')
        finally:
            cur.close()
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT id, name, password FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or not check_password_hash(user['password'], password):
            flash('Invalid email or password.')
            return render_template('login.html')

        session['user_id'] = user['id']
        session['user_name'] = user['name']
        flash('Logged in successfully.')
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('home'))


@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        '''
        SELECT l.*, c.name AS category_name, u.name AS seller_name, u.id AS seller_id
        FROM listings l
        JOIN categories c ON l.category_id = c.id
        JOIN users u ON l.user_id = u.id
        WHERE l.id = %s
        ''',
        (listing_id,)
    )
    listing = cur.fetchone()

    image = None
    if listing:
        cur.execute('SELECT image_path FROM listing_images WHERE listing_id = %s ORDER BY id LIMIT 1', (listing_id,))
        image = cur.fetchone()

    cur.close()
    conn.close()

    if not listing:
        flash('Listing not found.')
        return redirect(url_for('home'))

    return render_template('listing_detail.html', listing=listing, image=image)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_listing():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute('SELECT id, name FROM categories ORDER BY name')
    categories = cur.fetchall()

    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form.get('description', '').strip()
        price_raw = request.form['price'].strip()
        location = request.form.get('location', '').strip()
        item_condition = request.form.get('item_condition', '').strip()
        category_id = request.form.get('category_id', type=int)

        if not title or not price_raw or not category_id:
            flash('Title, price, and category are required.')
            cur.close()
            conn.close()
            return render_template('create_listing.html', categories=categories)

        try:
            price = Decimal(price_raw)
        except Exception:
            flash('Enter a valid price.')
            cur.close()
            conn.close()
            return render_template('create_listing.html', categories=categories)

        cur2 = conn.cursor()
        cur2.execute(
            '''
            INSERT INTO listings (user_id, category_id, title, description, price, location, item_condition)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''',
            (session['user_id'], category_id, title, description, price, location, item_condition)
        )
        new_id = cur2.lastrowid
        files = request.files.getlist('images')
        for file in files:
            if file and file.filename:
                if allowed_file(file.filename):
                    safe_name = secure_filename(file.filename)
                    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                    file.save(save_path)

                    cur2.execute(
                        '''
                        INSERT INTO listing_images (listing_id, image_path)
                        VALUES (%s, %s)
                        ''',
                        (new_id, unique_name)
                    )
                else:
                    flash(f'File type not allowed: {file.filename}')

        conn.commit()
        cur2.close()
        cur.close()
        conn.close()
        flash('Listing created.')
        return redirect(url_for('listing_detail', listing_id=new_id))

    cur.close()
    conn.close()
    return render_template('create_listing.html', categories=categories)


@app.route('/my-listings')
@login_required
def my_listings():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
    '''
    SELECT l.id, l.title, l.price, l.status, c.name AS category_name, l.created_at,
           (
               SELECT li.image_path
               FROM listing_images li
               WHERE li.listing_id = l.id
               ORDER BY li.id
               LIMIT 1
           ) AS cover_image
    FROM listings l
    JOIN categories c ON l.category_id = c.id
    WHERE l.user_id = %s
    ORDER BY l.created_at DESC
    ''',
    (session['user_id'],)
)
    listings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('my_listings.html', listings=listings)


if __name__ == '__main__':
    app.run(debug=True)

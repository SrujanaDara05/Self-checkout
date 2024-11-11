from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create a folder to store the database file if it doesn't exist
if not os.path.exists('db'):
    os.makedirs('db')

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('db/receipts.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to create the database table if it doesn't exist
def init_db():
    conn = get_db_connection()
    with app.open_resource('schema.sql', mode='r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# Initialize the database if it doesn't exist
if not os.path.exists('db/receipts.db'):
    init_db()

# Sample barcode-to-item mapping
barcode_to_item = {
    '123456789012': ('Apple', 50),
    '987654321098': ('Banana', 30),
    '111213141516': ('Orange', 80),
    '171819202122': ('Grapes', 50),
    '232425262728': ('Milk', 20)
}

# Initialize global variables
items = []
itemQuantities = []
itemPrices = []
total = 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            flash('You have successfully signed up! You can now log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    global items, itemQuantities, itemPrices
    if request.method == 'POST':
        if len(items) >= 5:
            flash("You can only purchase up to 5 items.")
            return redirect(url_for('add_item'))

        barcode = request.form.get('barcode')
        quantity = request.form.get('quantity')
        
        if not barcode or not quantity:
            flash("Please enter both barcode and quantity.")
            return redirect(url_for('add_item'))
        
        if not quantity.isdigit() or int(quantity) <= 0:
            flash("Please enter a valid positive quantity.")
            return redirect(url_for('add_item'))
        
        if len(barcode) != 12 or not barcode.isdigit():
            flash("Invalid barcode. Please enter a 12-digit numeric barcode.")
            return redirect(url_for('add_item'))
        
        if barcode not in barcode_to_item:
            flash("Invalid barcode.")
            return redirect(url_for('add_item'))
        
        item, price = barcode_to_item[barcode]
        items.append(item.capitalize())
        itemQuantities.append(int(quantity))
        itemPrices.append(float(price))
        flash(f"Added {quantity} x {item.capitalize()} at ₹{price} each to cart.")
        return redirect(url_for('add_item'))
    
    return render_template('add_item.html', items=items, itemQuantities=itemQuantities, itemPrices=itemPrices, zip=zip)

@app.route('/cart')
def view_cart():
    global items, itemQuantities, itemPrices
    return render_template('cart.html', items=items, itemQuantities=itemQuantities, itemPrices=itemPrices, enumerate=enumerate, zip=zip)

@app.route('/remove_item/<int:index>', methods=['POST'])
def remove_item(index):
    global items, itemQuantities, itemPrices
    try:
        items.pop(index)
        itemQuantities.pop(index)
        itemPrices.pop(index)
        flash("Item removed successfully.")
    except IndexError:
        flash("Error removing item.")
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    global items, itemQuantities, itemPrices, total
    total = calculate_total()
    if request.method == 'POST':
        upi_id = request.form.get('upi_id')
        if not upi_id:
            flash("Please enter your UPI ID.")
            return redirect(url_for('checkout'))
        flash(f"UPI payment initiated for {upi_id}. Please complete the payment using your UPI app.")
        save_receipt(items, itemQuantities, total, upi_id)
        return redirect(url_for('receipt', upi_id=upi_id))
    
    return render_template('checkout.html', total=total)

@app.route('/receipt')
def receipt():
    global items, itemQuantities, itemPrices, total
    upi_id = request.args.get('upi_id')
    purchased_items = zip(items, itemQuantities, itemPrices)
    items = []
    itemQuantities = []
    itemPrices = []
    return render_template('receipt.html', total=total, purchased_items=purchased_items, payment_method='UPI', upi_id=upi_id)

def calculate_total():
    global itemQuantities, itemPrices
    subtotal = sum(q * p for q, p in zip(itemQuantities, itemPrices))
    sales_tax = 0.13 * subtotal
    total = subtotal + sales_tax
    return round(total, 2)

def save_receipt(items, quantities, total, upi_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items_str = ', '.join(items)
    quantities_str = ', '.join(map(str, quantities))
    conn = get_db_connection()
    conn.execute("INSERT INTO receipts (items, quantities, total, upi_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (items_str, quantities_str, total, upi_id, timestamp))
    conn.commit()
    conn.close()

@app.route('/init_db')
def init_database():
    try:
        init_db()
        return 'Database initialized successfully!'
    except Exception as e:
        return f'Error initializing database: {str(e)}'

if __name__ == '__main__':
    app.run(debug=True)

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
    '232425262728': ('Milk', 20),
    '333444555666': ('Bread', 40),
    '444555666777': ('Butter', 60),
    '555666777888': ('Cheese', 70),
    '666777888999': ('Juice', 90),
    '777888999000': ('Eggs', 120)
}

# Initialize global variables
items = []
itemQuantities = []
itemPrices = []
total = 0

@app.route('/')
def home():
    return render_template('Home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        phone = request.form['phone']

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db_connection()
        conn.execute("INSERT INTO users (username, password, phone) VALUES (?, ?, ?)", (username, hashed_password, phone))
        conn.commit()
        conn.close()

        
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/checkperson')
def checkperson():
    return render_template('checkperson.html')

@app.route('/receipts_list')
def receipts_list():
    current_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    receipts = conn.execute("SELECT * FROM receipts WHERE DATE(timestamp) = ?", (current_date,)).fetchall()
    conn.close()
    return render_template('receipts_list.html', receipts=receipts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
           
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/index')
def index():
    return render_template('index.html')

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
            flash("Enter a valid barcode.")
            return redirect(url_for('add_item'))
        
        # Check if the item is already in the cart and if it's the first item
        if itemQuantities and int(quantity) != itemQuantities[0]:
            flash("Cannot add more than five items.")
            return redirect(url_for('add_item'))
        
        item, price = barcode_to_item[barcode]
        items.append(item.capitalize())
        itemQuantities.append(int(quantity))
        itemPrices.append(float(price))
        
        flash(f"Added {quantity} x {item.capitalize()} at ₹{price} each to cart.")
        return redirect(url_for('add_item'))
    
    return render_template('add_item.html', items=items, itemQuantities=itemQuantities, itemPrices=itemPrices, zip=zip, barcode_to_item=barcode_to_item)

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
        
        # Simulate payment confirmation logic
        # Here you might have actual payment processing code
        
        # Assuming payment confirmation is successful, save receipt
        save_receipt(items, itemQuantities, total, upi_id)
        
        # Redirect to receipt page with UPI ID as a query parameter
        return redirect(url_for('receipt', upi_id=upi_id))
    
    return render_template('checkout.html', total=total)

@app.route('/receipt')
def receipt():
    global items, itemQuantities, itemPrices, total
    upi_id = request.args.get('upi_id')
    purchased_items = list(zip(items, itemQuantities, itemPrices))
    items = []  # Clear items after displaying receipt
    itemQuantities = []
    itemPrices = []
    return render_template('receipt.html', total=total, purchased_items=purchased_items, payment_method='UPI', upi_id=upi_id)

@app.route('/receipt_details/<int:receipt_id>')
def receipt_details(receipt_id):
    conn = get_db_connection()
    receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
    conn.close()
    if receipt is None:
        flash('Receipt not found!')
        return redirect(url_for('Home'))
    return render_template('receipt_details.html', receipt=receipt)

@app.route('/delete_receipt/<int:receipt_id>', methods=['POST'])
def delete_receipt(receipt_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM receipts WHERE id = ?', (receipt_id,))
    conn.commit()
    conn.close()
    flash('Receipt deleted successfully.')
    return render_template('receipts_list.html', receipts=receipts)

def calculate_total():
    global itemQuantities, itemPrices
    subtotal = sum(q * p for q, p in zip(itemQuantities, itemPrices))
    sales_tax = 0.02 * subtotal
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

if __name__ == '__main__':
    app.run(debug=True)
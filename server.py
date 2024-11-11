from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('db/receipts_server.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to create the database table if it doesn't exist
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS received_receipts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        upi_id TEXT NOT NULL,
                        total REAL NOT NULL,
                        items TEXT NOT NULL,
                        quantities TEXT NOT NULL,
                        timestamp DATETIME NOT NULL)''')
    conn.commit()
    conn.close()

# Initialize the database if it doesn't exist
if not os.path.exists('db'):
    os.makedirs('db')

if not os.path.exists('db/receipts_server.db'):
    init_db()

@app.route('/receive-receipt', methods=['POST'])
def receive_receipt():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid data'}), 400

    upi_id = data.get('upi_id')
    total = data.get('total')
    items = data.get('items')
    quantities = data.get('quantities')
    timestamp = data.get('timestamp')

    conn = get_db_connection()
    conn.execute("INSERT INTO received_receipts (upi_id, total, items, quantities, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (upi_id, total, items, quantities, timestamp))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(port=5001, debug=True)

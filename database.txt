import sqlite3
from tabulate import tabulate

# Connect to SQLite database
conn = sqlite3.connect('db/receipts.db')
cursor = conn.cursor()

# Example: Fetch data from users table
cursor.execute("SELECT * FROM users;")
users_data = cursor.fetchall()

# Print data as a table using tabulate
print(tabulate(users_data, headers=['ID', 'Username', 'Password', 'Phone']))

# Example: Fetch data from receipts table
cursor.execute("SELECT * FROM receipts;")
receipts_data = cursor.fetchall()

# Print data as a table using tabulate
print(tabulate(receipts_data, headers=['ID', 'Items', 'Quantities', 'Total', 'UPI ID', 'Timestamp']))

# Close database connection
conn.close()

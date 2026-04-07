import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'users.db')
print(f"Looking for database at: {db_path}")

if not os.path.exists(db_path):
    print("File not found.")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

cursor.execute("SELECT * FROM user;")
rows = cursor.fetchall()
print("\nUser table data:")
for row in rows:
    print(row)

conn.close()
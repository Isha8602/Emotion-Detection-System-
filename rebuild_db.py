import sqlite3
import os
from werkzeug.security import generate_password_hash

db_path = os.path.join(os.path.dirname(__file__), 'users.db')
print(f"Creating database at: {db_path}")

# Remove existing file if present
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create user table (matches your Flask model)
cursor.execute('''
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Insert default users
cursor.execute('''
INSERT INTO user (name, email, password_hash, role)
VALUES (?, ?, ?, ?)
''', ('Default Agent', 'agent@example.com', generate_password_hash('agent123'), 'agent'))

cursor.execute('''
INSERT INTO user (name, email, password_hash, role)
VALUES (?, ?, ?, ?)
''', ('Default Supervisor', 'supervisor@example.com', generate_password_hash('sup456'), 'supervisor'))

conn.commit()
conn.close()
print("Database created and populated.")
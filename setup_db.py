import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "users.db")}'

if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create users table (must be plural to match model)
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create call_report table
cursor.execute('''
CREATE TABLE call_report (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    agent_name TEXT,
    customer_name TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration INTEGER,
    overall_sentiment TEXT,
    emotion_peaks TEXT,
    emotion_events TEXT,
    FOREIGN KEY (agent_id) REFERENCES users (id)
)
''')

# Insert default users
cursor.execute('''
INSERT INTO users (name, email, password_hash, role)
VALUES (?, ?, ?, ?)
''', ('Default Agent', 'agent@example.com', generate_password_hash('agent123'), 'agent'))

cursor.execute('''
INSERT INTO users (name, email, password_hash, role)
VALUES (?, ?, ?, ?)
''', ('Default Supervisor', 'supervisor@example.com', generate_password_hash('sup456'), 'supervisor'))

conn.commit()
conn.close()
print("Database created and populated.")
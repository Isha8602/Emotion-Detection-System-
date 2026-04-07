import os
import pickle
import io
import base64
import json
import secrets
from datetime import datetime

import torch
import numpy as np
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ----- Import your custom modules -----
from model.model import EmotionCNN_LSTM
from utils.audio_processing import process_audio

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----- Database setup (single instance) -----
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ----- User Model -----
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ----- Call Report Model -----
class CallReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    agent_name = db.Column(db.String(100))
    customer_name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer)
    overall_sentiment = db.Column(db.String(50))
    emotion_peaks = db.Column(db.String(100))
    emotion_events = db.Column(db.Text)

# ----- Create tables and default users -----
with app.app_context():
    db.create_all()
    # Add 'name' column if missing (for existing SQLite databases)
    from sqlalchemy import inspect, text
    def column_exists(table_name, column_name):
        insp = inspect(db.engine)
        columns = [col['name'] for col in insp.get_columns(table_name)]
        return column_name in columns

    if not column_exists('users', 'name'):
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE users ADD COLUMN name TEXT'))
            conn.commit()
        print("Added 'name' column to users table.")

    # Create default users if none exist
    if User.query.count() == 0:
        print("Creating default users...")
        agent = User(name="Default Agent", email='agent@example.com', role='agent')
        agent.set_password('agent123')
        supervisor = User(name="Default Supervisor", email='supervisor@example.com', role='supervisor')
        supervisor.set_password('sup456')
        db.session.add(agent)
        db.session.add(supervisor)
        db.session.commit()
        print("Default users created.")

# ----- Load Emotion Model -----
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

with open('emotion_labels.pkl', 'rb') as f:
    emotion_labels = pickle.load(f)
num_classes = len(emotion_labels)

input_dim = 384   # adjust based on your model's input dimension
model = EmotionCNN_LSTM(input_dim=input_dim, hidden_dim=128, num_layers=2,
                        num_classes=num_classes, dropout=0.4)
model.load_state_dict(torch.load('model/best_model.pth', map_location=device))
model.to(device)
model.eval()
print(f"Model loaded. Device: {device}")

# ----- Active calls store -----
active_calls = {}

# ----- Helper functions -----
def broadcast_active_calls():
    """Emit active calls to all connected supervisors."""
    socketio.emit('active_calls_update', list(active_calls.values()), broadcast=True)

# ----- SocketIO Events -----
@socketio.on('start_call')
def handle_start_call(data):
    call_id = data.get('call_id')
    agent = data.get('agent')
    customer = data.get('customer', 'Unknown')
    active_calls[call_id] = {
        'call_id': call_id,
        'agent': agent,
        'customer': customer,
        'duration': 0,
        'emotion': 'neutral',
        'start_time': datetime.utcnow().isoformat()
    }
    socketio.emit('new_call', active_calls[call_id], broadcast=True)
    broadcast_active_calls()

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    call_id = data.get('call_id')
    audio_b64 = data.get('audio')
    if not audio_b64:
        return
    try:
        audio_bytes = base64.b64decode(audio_b64)
        audio_file = io.BytesIO(audio_bytes)
        features = process_audio(audio_file)   # expects a feature vector
        input_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(input_tensor)
            _, predicted = torch.max(output, 1)
            emotion = emotion_labels[predicted.item()]
    except Exception as e:
        print(f"Error processing audio: {e}")
        emotion = 'neutral'

    if call_id in active_calls:
        active_calls[call_id]['emotion'] = emotion
        active_calls[call_id]['duration'] += 1   # assuming 1-second chunks
        socketio.emit('emotion_update', {
            'call_id': call_id,
            'emotion': emotion,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)

        # Alert for negative emotions
        if emotion in ['angry', 'frustrated', 'sad']:
            alert_msg = f"⚠️ Alert: {emotion.upper()} detected on call {call_id} (Agent: {active_calls[call_id]['agent']})"
            socketio.emit('alert', {'message': alert_msg, 'call_id': call_id}, broadcast=True)

@socketio.on('end_call')
def handle_end_call(data):
    call_id = data.get('call_id')
    if call_id in active_calls:
        del active_calls[call_id]
        socketio.emit('call_ended', {'call_id': call_id}, broadcast=True)
        broadcast_active_calls()

@socketio.on('connect')
def handle_connect():
    print('Client connected')

# ----- Flask Routes -----
@app.route('/')
def index():
    print(f"Index called. Session: {session}")
    if 'email' in session:
        print(f"User email: {session['email']}, role: {session['role']}")
        if session['role'] == 'agent':
            return redirect(url_for('agent_dashboard'))
        elif session['role'] == 'supervisor':
            return redirect(url_for('supervisor_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if user and user.check_password(password):
            session['email'] = user.email
            session['role'] = user.role
            if is_ajax:
                return jsonify({'success': True, 'redirect': url_for('index')})
            return redirect(url_for('index'))
        else:
            if is_ajax:
                return jsonify({'error': 'Invalid email or password'}), 401
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', '')

    # Validation
    if not all([name, email, password, role]):
        if is_ajax:
            return jsonify({'error': 'All fields are required'}), 400
        return render_template('register.html', error='All fields are required')

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        if is_ajax:
            return jsonify({'error': 'Email already registered'}), 409
        return render_template('register.html', error='Email already registered')

    # Create new user (use set_password to hash)
    new_user = User(name=name, email=email, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    if is_ajax:
        return jsonify({'success': True, 'redirect': url_for('login')})
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----- Agent & Supervisor Pages -----
@app.route('/agent')
def agent_dashboard():
    if 'email' not in session or session['role'] != 'agent':
        return redirect(url_for('login'))
    user = User.query.filter_by(email=session['email']).first()
    return render_template('agent_dashboard.html',
                           emotion_labels=emotion_labels,
                           agent_name=user.name or user.email)

@app.route('/supervisor')
def supervisor_dashboard():
    if 'email' not in session or session['role'] != 'supervisor':
        return redirect(url_for('login'))
    return render_template('supervisor_dashboard.html')

@app.route('/analytics')
def analytics():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('analytics.html')

# ----- API Endpoints -----
@app.route('/api/users', methods=['GET'])
def get_users():
    if 'email' not in session or session['role'] != 'supervisor':
        return jsonify({'error': 'Unauthorized'}), 401
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{
        'id': u.id,
        'name': u.name,
        'email': u.email,
        'role': u.role,
        'created_at': u.created_at.isoformat() if u.created_at else None
    } for u in users])

@app.route('/api/save_report', methods=['POST'])
def save_report():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    user = User.query.filter_by(email=session['email']).first()
    report = CallReport(
        agent_id=user.id,
        agent_name=user.name or user.email,
        customer_name=data['customer'],
        duration=data['duration'],
        overall_sentiment=data['overallSentiment'],
        emotion_peaks=data.get('emotionPeaks', ''),
        emotion_events=json.dumps(data.get('emotionEvents', []))
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/reports', methods=['GET'])
def get_reports():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    reports = CallReport.query.order_by(CallReport.start_time.desc()).all()
    return jsonify([{
        'id': r.id,
        'agent_name': r.agent_name,
        'customer_name': r.customer_name,
        'start_time': r.start_time.isoformat(),
        'duration': r.duration,
        'overall_sentiment': r.overall_sentiment,
        'emotion_peaks': r.emotion_peaks,
        'emotion_events': r.emotion_events
    } for r in reports])

@app.route('/api/agent_performance', methods=['GET'])
def agent_performance():
    if 'email' not in session or session['role'] != 'supervisor':
        return jsonify({'error': 'Unauthorized'}), 401
    from sqlalchemy import func
    agents = db.session.query(
        CallReport.agent_name,
        func.count(CallReport.id).label('total_calls'),
        func.avg(CallReport.duration).label('avg_duration')
    ).group_by(CallReport.agent_name).all()
    performance = [{
        'name': name,
        'total_calls': total_calls,
        'avg_duration': round(avg_duration, 2) if avg_duration else 0
    } for name, total_calls, avg_duration in agents]
    return jsonify(performance)

@app.route('/api/emotion_distribution', methods=['GET'])
def emotion_distribution():
    if 'email' not in session or session['role'] != 'supervisor':
        return jsonify({'error': 'Unauthorized'}), 401
    from sqlalchemy import func
    counts = db.session.query(
        CallReport.overall_sentiment,
        func.count(CallReport.id)
    ).group_by(CallReport.overall_sentiment).all()
    distribution = {sentiment: count for sentiment, count in counts}
    return jsonify(distribution)

@app.route('/api/active_calls', methods=['GET'])
def get_active_calls():
    if 'email' not in session or session['role'] != 'supervisor':
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(list(active_calls.values()))

if __name__ == '__main__':
    socketio.run(app, debug=True)
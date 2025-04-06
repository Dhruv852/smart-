from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
import pandas as pd
import numpy as np
import google.generativeai as genai
import plotly.express as px
import json
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Configure Gemini API with hardcoded key
genai.configure(api_key='AIzaSyD4OuyUUsUWEc1V6B4T3LEuUuNS8t0jtHE')
model = genai.GenerativeModel('gemini-2.0-flash', generation_config={"temperature": 0.7})

# Database initialization
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL)''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect('users.db', timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    if conn is not None:
        conn.close()

# Authentication middleware
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# In-memory storage for device data
device_data = []

def load_and_process_data():
    try:
        df = pd.read_csv('data/smart_home_energy_consumption_large.csv')
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def generate_sample_data():
    # Generate sample data for the last 7 days
    devices = ['Refrigerator', 'Air Conditioner', 'Washing Machine', 'TV', 'Laptop']
    sample_data = []
    
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        for device in devices:
            # Generate random consumption between 0.5 and 5 kWh
            consumption = round(np.random.uniform(0.5, 5.0), 2)
            # Generate random hour between 0 and 23
            hour = np.random.randint(0, 24)
            timestamp = date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            sample_data.append({
                'device': device,
                'power_consumption': consumption,
                'timestamp': timestamp.isoformat()
            })
    
    return sample_data

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = None
        try:
            db = get_db()
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password')
        except sqlite3.Error as e:
            flash('Database error occurred. Please try again.')
            print(f'Database error: {str(e)}')
        finally:
            close_db(db)
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        db = None
        try:
            db = get_db()
            db.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                      (username, generate_password_hash(password), email))
            db.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash('Username or email already exists')
        except sqlite3.Error as e:
            db.rollback()
            flash('Database error occurred. Please try again.')
            print(f'Database error: {str(e)}')
        finally:
            close_db(db)
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/consumption')
@login_required
def get_consumption_data():
    df = load_and_process_data()
    if df is None:
        return jsonify({'error': 'Failed to load data'}), 500
    
    # Get daily consumption
    daily_consumption = df.groupby(df['timestamp'].dt.date)['power_consumption'].sum().reset_index()
    daily_consumption.columns = ['date', 'consumption']
    
    # Get device-wise consumption
    device_consumption = df.groupby('device')['power_consumption'].sum().reset_index()
    
    return jsonify({
        'daily_consumption': daily_consumption.to_dict('records'),
        'device_consumption': device_consumption.to_dict('records')
    })

@app.route('/api/sample-data')
@login_required
def get_sample_data():
    return jsonify(generate_sample_data())

@app.route('/api/analysis', methods=['POST'])
@login_required
def analyze_data():
    try:
        data = request.get_json()
        
        if not data or 'device_data' not in data:
            return jsonify({'error': 'No device data provided'}), 400

        device_data = data['device_data']
        total_consumption = sum(item['power_consumption'] for item in device_data)
        dates = set(item['timestamp'].split('T')[0] for item in device_data)
        avg_daily = total_consumption / len(dates) if dates else 0

        # Calculate peak hours
        peak_hours = {}
        for item in device_data:
            hour = datetime.fromisoformat(item['timestamp']).hour
            peak_hours[hour] = peak_hours.get(hour, 0) + item['power_consumption']

        # Prepare data for AI analysis
        analysis_prompt = f"""
        Based on this energy data:
        Total: {total_consumption:.2f} kWh
        Daily avg: {avg_daily:.2f} kWh
        Peak hours: {peak_hours}
        Devices: {json.dumps(device_data, indent=2)}

        Give 3 very short energy-saving tips (max 10 words each).
        """

        # Get AI suggestions
        response = model.generate_content(analysis_prompt)
        suggestions = response.text

        return jsonify({
            'suggestions': suggestions,
            'analysis': {
                'total': f"{total_consumption:.1f} kWh",
                'daily': f"{avg_daily:.1f} kWh",
                'peak': max(peak_hours.items(), key=lambda x: x[1])[0] if peak_hours else 0
            }
        })
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
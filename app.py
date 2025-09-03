#!/usr/bin/env python3
"""
Sample web application with intentional bugs for demonstration
"""

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import hashlib
import os
import time
from functools import wraps

app = Flask(__name__)

# In-memory storage for demo purposes
users = {}
sessions = {}

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using MD5 (intentionally weak for demo)"""
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get('session_id')
        if not session_id or session_id not in sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Home page"""
    return render_template_string('''
    <html>
    <head><title>Bug Demo App</title></head>
    <body>
        <h1>Welcome to Bug Demo App</h1>
        <p><a href="/login">Login</a> | <a href="/register">Register</a></p>
        <p><a href="/users">View Users (requires auth)</a></p>
    </body>
    </html>
    ''')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration endpoint"""
    if request.method == 'GET':
        return render_template_string('''
        <html>
        <head><title>Register</title></head>
        <body>
            <h1>Register</h1>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required><br><br>
                <input type="email" name="email" placeholder="Email" required><br><br>
                <input type="password" name="password" placeholder="Password" required><br><br>
                <button type="submit">Register</button>
            </form>
        </body>
        </html>
        ''')
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'All fields required'}), 400
    
    # Check if user exists
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Fixed: Use parameterized query to prevent SQL injection
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Username already exists'}), 400
    
    # Create user
    password_hash = hash_password(password)
    cursor.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", 
                   (username, password_hash, email))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'User created successfully'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if request.method == 'GET':
        return render_template_string('''
        <html>
        <head><title>Login</title></head>
        <body>
            <h1>Login</h1>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required><br><br>
                <input type="password" name="password" placeholder="Password" required><br><br>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        ''')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # BUG 1: Logic error - incorrect password verification
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Fixed: Now properly verifies password against stored hash
    if verify_password(password, result[0]):
        # Create session
        session_id = hashlib.md5(f"{username}{time.time()}".encode()).hexdigest()
        sessions[session_id] = username
        
        response = jsonify({'message': 'Login successful'})
        response.set_cookie('session_id', session_id)
        return response
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/users')
@require_auth
def get_users():
    """Get all users - requires authentication"""
    # Fixed: Single query to get all user data at once
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Get all user data in a single query
    cursor.execute("SELECT username, email, created_at FROM users")
    user_rows = cursor.fetchall()
    
    users_data = []
    for user_data in user_rows:
        users_data.append({
            'username': user_data[0],
            'email': user_data[1],
            'created_at': user_data[2]
        })
    
    conn.close()
    return jsonify({'users': users_data})

@app.route('/logout')
def logout():
    """Logout endpoint"""
    session_id = request.cookies.get('session_id')
    if session_id in sessions:
        del sessions[session_id]
    return jsonify({'message': 'Logged out successfully'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
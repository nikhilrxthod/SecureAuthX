from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_session import Session
from config.database_config import mysql, app
from email_sender import send_unlock_email
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import re
# import os # not necessary if we dont use the debug command where os is used (see at last)
from pathlib import Path

# Get the absolute path to the current directory
current_dir = Path(__file__).parent

# Explicitly set template and static folders
app.template_folder = str(current_dir / 'templates')
app.static_folder = str(current_dir / 'static')

bcrypt = Bcrypt(app)
app.secret_key = '7f9d2a4b8c1e3f6d0b2a9c5e1f8d7a3b'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)  # Session expires after 10 minutes
Session(app)

s = URLSafeTimedSerializer(app.secret_key)

# --- Regex patterns ---
EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$')

# --- Rate Limiting Constants ---
RATE_LIMIT = 3
COOLDOWN_MINUTES = 1
MAX_ROUNDS = 3  # Maximum number of cooldown rounds before lockout
ATTEMPT_TIMEOUT_MINUTES = 5  # Timeout for individual failed attempts

# --- Helper Functions ---
def get_user_by_email(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, password_hash, is_locked, created_at FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    return user

def get_login_attempts(ip_address, user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, ip_address, user_id, failed_attempts, last_failed_attempt, cooldown_round FROM login_attempts WHERE ip_address=%s AND user_id=%s", (ip_address, user_id))
    attempt = cur.fetchone()
    cur.close()
    return attempt

def create_login_attempt(ip_address, user_id):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO login_attempts (ip_address, user_id) VALUES (%s, %s)", (ip_address, user_id))
    mysql.connection.commit()
    cur.close()

def update_login_attempts(attempt_id, failed_attempts, last_attempt, cooldown_round):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE login_attempts SET failed_attempts=%s, last_failed_attempt=%s, cooldown_round=%s WHERE id=%s",
                (failed_attempts, last_attempt, cooldown_round, attempt_id))
    mysql.connection.commit()
    cur.close()

def reset_login_attempts(attempt_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE login_attempts SET failed_attempts=0, cooldown_round=0, last_failed_attempt=NULL WHERE id=%s", (attempt_id,))
    mysql.connection.commit()
    cur.close()

def lock_user_account(user_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_locked=TRUE WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()

def save_unlock_token(user_id, token):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO unlock_tokens (user_id, token) VALUES (%s, %s)", (user_id, token))
    mysql.connection.commit()
    cur.close()

def is_valid_email(email):
    return EMAIL_REGEX.match(email)

def is_valid_password(password):
    return PASSWORD_REGEX.match(password)

def reset_attempts_if_expired(login_attempt, now):
    """Reset failed attempts if individual attempts have expired (more than 5 minutes between attempts)"""
    attempt_id, ip_address, user_id, failed_attempts, last_attempt, cooldown_round = login_attempt
    
    if last_attempt and failed_attempts > 0:
        attempt_timeout = last_attempt + timedelta(minutes=ATTEMPT_TIMEOUT_MINUTES)
        
        # Reset failed attempts if last attempt was more than 5 minutes ago
        if now > attempt_timeout:
            reset_login_attempts(attempt_id)
            return True
    
    return False

def reset_cooldown_if_expired(login_attempt, now):
    """Reset failed attempts after cooldown period ends"""
    attempt_id, ip_address, user_id, failed_attempts, last_attempt, cooldown_round = login_attempt
    
    if last_attempt and failed_attempts >= RATE_LIMIT:
        cooldown_end = last_attempt + timedelta(minutes=COOLDOWN_MINUTES)
        
        # Reset failed attempts after cooldown period ends
        if now > cooldown_end:
            update_login_attempts(attempt_id, 0, last_attempt, cooldown_round)
            return True
    
    return False

def reset_cooldown_round_if_expired(login_attempt, now):
    """Reset cooldown round if user didn't make any attempts within 5 minutes after cooldown ended"""
    attempt_id, ip_address, user_id, failed_attempts, last_attempt, cooldown_round = login_attempt
    
    if last_attempt and cooldown_round > 0 and failed_attempts == 0:
        cooldown_end = last_attempt + timedelta(minutes=COOLDOWN_MINUTES)
        cooldown_reset_time = cooldown_end + timedelta(minutes=ATTEMPT_TIMEOUT_MINUTES)
        
        # Reset cooldown round if user didn't make any attempts within 5 minutes after cooldown ended
        if now > cooldown_reset_time:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE login_attempts SET cooldown_round=0 WHERE id=%s", (attempt_id,))
            mysql.connection.commit()
            cur.close()
            return True
    
    return False

def is_in_cooldown_period(login_attempt, now):
    """Check if user is still in cooldown period for this IP"""
    attempt_id, ip_address, user_id, failed_attempts, last_attempt, cooldown_round = login_attempt
    
    if last_attempt and failed_attempts >= RATE_LIMIT:
        cooldown_end = last_attempt + timedelta(minutes=COOLDOWN_MINUTES)
        return now <= cooldown_end
    
    return False

# --- Routes ---
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Backend email validation
        if not is_valid_email(email):
            flash("Invalid email format", "error")
            return redirect(url_for('register'))

        # Password complexity validation
        if not is_valid_password(password):
            flash("Password must be at least 8 characters with uppercase, lowercase, digit, and special character.", "error")
            return redirect(url_for('register'))

        # Backend Confirm password validation, error mssg shows only when attacker capture request and modify credentials
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for('register'))

        # Duplicate account prevention
        if get_user_by_email(email):
            flash("Email ID already exists. Please use a different email.", "error")
            return redirect(url_for('register'))

        # Hash & store password
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, pw_hash))
        mysql.connection.commit()
        cur.close()

        flash("Registered successfully! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# --- Login & Rate Limiting ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        ip_address = request.remote_addr

        # Backend email validation
        if not is_valid_email(email):
            flash("Invalid email format", "error")
            return redirect(url_for('login'))

        # Backend password minimum length check (login)
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for('login'))

        user = get_user_by_email(email)
        
        # Check if account exists FIRST - before any rate limiting logic
        if not user:
            flash("Account not found. Please register for a new account.", "error")
            return redirect(url_for('login'))

        user_id, email, pw_hash, is_locked, created_at = user
        now = datetime.now()

        # Check if account is locked
        if is_locked:
            token = s.dumps(email)
            save_unlock_token(user_id, token)
            unlock_link = url_for('unlock_account', token=token, _external=True)
            send_unlock_email(email, unlock_link)
            flash("Your account is temporarily blocked. We have sent an unlock link to your registered email.", "error")                                            
            return redirect(url_for('login'))

        # Get or create login attempt record for this IP and user
        login_attempt = get_login_attempts(ip_address, user_id)
        if not login_attempt:
            create_login_attempt(ip_address, user_id)
            login_attempt = get_login_attempts(ip_address, user_id)
        
        attempt_id, ip_addr, user_id_attempt, failed_attempts, last_attempt, cooldown_round = login_attempt

        # Check if individual attempts have expired (more than 5 minutes between attempts)
        reset_attempts_if_expired(login_attempt, now)

        # Check if cooldown period ended and reset failed attempts
        reset_cooldown_if_expired(login_attempt, now)

        # Check if cooldown round should be reset
        reset_cooldown_round_if_expired(login_attempt, now)

        # Refresh login attempt after reset checks
        login_attempt = get_login_attempts(ip_address, user_id)
        attempt_id, ip_addr, user_id_attempt, failed_attempts, last_attempt, cooldown_round = login_attempt

        # Cooldown check - if user is still in cooldown period for this IP
        if is_in_cooldown_period(login_attempt, now):
            cooldown_end = last_attempt + timedelta(minutes=COOLDOWN_MINUTES)
            remaining = (cooldown_end - now).seconds
            flash(f"Too many attempts from your IP. Wait {remaining // 60}:{remaining % 60:02d} before trying again.", "error")
            return redirect(url_for('login'))

        # Verify password
        if bcrypt.check_password_hash(pw_hash, password):
            # Reset failed attempts for this IP on successful login
            reset_login_attempts(attempt_id)
            session['user_id'] = user_id
            session.permanent = True  # Enable permanent sessions with expiration
            return redirect(url_for('dashboard'))
        else:
            failed_attempts += 1

            # If limit reached (3 failed attempts within 5 minutes from this IP)
            if failed_attempts >= RATE_LIMIT:
                # Increment cooldown round only when reaching the limit
                cooldown_round += 1
                update_login_attempts(attempt_id, failed_attempts, now, cooldown_round)

                if cooldown_round >= MAX_ROUNDS:
                    # Lock the account globally (not just for this IP)
                    lock_user_account(user_id)
                    token = s.dumps(email)
                    save_unlock_token(user_id, token)
                    unlock_link = url_for('unlock_account', token=token, _external=True)
                    send_unlock_email(email, unlock_link)
                    flash("Your account has been temporarily locked. Unlock link sent to your registered email.", "error")                                     
                    return redirect(url_for('login'))
                else:
                    flash(f"Too many failed attempts from your IP. Please wait {COOLDOWN_MINUTES} minutes.", "error")
                    return redirect(url_for('login'))
            else:
                update_login_attempts(attempt_id, failed_attempts, now, cooldown_round)

            flash("Invalid password", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# --- Unlock Account ---
@app.route('/unlock/<token>')
def unlock_account(token):
    try:
        email = s.loads(token, max_age=900)
        user = get_user_by_email(email)
        if user:
            user_id, email, pw_hash, is_locked, created_at = user
            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET is_locked=FALSE WHERE id=%s", (user_id,))
            
            # Also reset all login attempts for this user across all IPs
            cur.execute("DELETE FROM login_attempts WHERE user_id=%s", (user_id,))
            
            mysql.connection.commit()
            cur.close()
            flash("Your account has been successfully unlocked.", "success")
            return redirect(url_for('login'))
        else:
            flash("Invalid unlock link.", "error")
            return redirect(url_for('login'))
    except:
        flash("Unlock link has expired. Please request a new unlock link.", "error")
        return redirect(url_for('login'))

# --- Dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- Logout ---
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# --- Run App ---
if __name__ == '__main__':
    # Debug information     # not necessary below 3 lines
   # print(f"Template folder path: {app.template_folder}")
   # print(f"Static folder path: {app.static_folder}")
   # print(f"Files in template folder: {os.listdir(app.template_folder)}")
     app.run(host='0.0.0.0', port=5000, debug=True)                                   #app.run(debug=True)                                                                                # app.run(host='0.0.0.0', port=5000, debug=True)
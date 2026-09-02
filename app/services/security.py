from cryptography.fernet import Fernet
import hashlib
import base64
import os
from functools import wraps
from flask import session, redirect, url_for, flash

# Generate a key for encryption (in production, store this securely)
_encryption_key = None

def get_encryption_key():
    global _encryption_key
    if _encryption_key is None:
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            # Generate a key if not set (for development only)
            # Store it in a file so it persists across restarts
            key_file = 'instance/.encryption_key'
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    _encryption_key = f.read()
            else:
                _encryption_key = Fernet.generate_key()
                os.makedirs('instance', exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(_encryption_key)
                print(f"WARNING: Generated new encryption key. Set ENCRYPTION_KEY in .env for production!")
        else:
            _encryption_key = key.encode()
    return _encryption_key

def get_cipher():
    key = get_encryption_key()
    return Fernet(key)

def encrypt_data(data):
    """Encrypt sensitive data using AES encryption"""
    if not data:
        return None
    cipher = get_cipher()
    encrypted = cipher.encrypt(data.encode())
    return encrypted.decode()

def decrypt_data(encrypted_data):
    """Decrypt sensitive data"""
    if not encrypted_data:
        return None
    try:
        cipher = get_cipher()
        decrypted = cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def hash_vote(voter_id, candidate_id, timestamp):
    """Create an anonymous hash for a vote"""
    vote_string = f"{voter_id}_{candidate_id}_{timestamp}"
    return hashlib.sha256(vote_string.encode()).hexdigest()

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session or not session.get('admin_authenticated'):
            flash('Please login as admin to access this page.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

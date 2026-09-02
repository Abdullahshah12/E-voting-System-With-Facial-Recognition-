from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class Voter(db.Model):
    __tablename__ = 'voters'

    id = db.Column(db.Integer, primary_key=True)
    cnic = db.Column(db.String(15), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)  # Extracted from CNIC
    encrypted_cnic = db.Column(db.Text, nullable=False)
    encrypted_mobile = db.Column(db.Text, nullable=False)
    cnic_image_path = db.Column(db.String(255), nullable=True)  # Path to CNIC image
    face_encoding = db.Column(db.Text, nullable=True)  # JSON string of face encoding
    face_image_path = db.Column(db.String(255), nullable=True)  # Path to saved face image
    registered_at = db.Column(db.DateTime, default=datetime.now)
    has_voted = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Voter {self.cnic}>'

class Candidate(db.Model):
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    photo_path = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    assembly_type = db.Column(db.String(10), nullable=True)  # 'NA' or 'PA'
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)
    
    votes = db.relationship('Vote', backref='candidate', lazy=True)
    
    def __repr__(self):
        return f'<Candidate {self.name}>'
    
    def vote_count(self):
        return Vote.query.filter_by(candidate_id=self.id).count()

class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voters.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    vote_hash = db.Column(db.String(64), unique=True, nullable=False)  # SHA-256 hash for anonymity
    cast_at = db.Column(db.DateTime, default=datetime.now)
    
    voter = db.relationship('Voter', backref='vote')
    
    def __repr__(self):
        return f'<Vote {self.id}>'

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_logged_in = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.email}>'

class AdminOTP(db.Model):
    __tablename__ = 'admin_otps'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    admin = db.relationship('Admin', backref='otps')
    
    def __repr__(self):
        return f'<AdminOTP {self.otp}>'

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON string for additional details
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    admin = db.relationship('Admin', backref='activity_logs')
    
    def __repr__(self):
        return f'<ActivityLog {self.action}>'

import sys
import os
import base64

# Add app and services directories to sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, 'app'))
sys.path.append(os.path.join(base_dir, 'app', 'services'))

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_mail import Mail
from models import db, Voter, Candidate, Vote, Admin, AdminOTP, ActivityLog
from security import encrypt_data, decrypt_data, hash_vote, admin_required
from biometric import encode_face_from_frame, compare_faces, save_face_encoding, load_face_encoding, detect_face_in_frame
from email_service import mail, generate_otp, send_otp_email, send_login_alert_email
from datetime import datetime, timedelta
import cv2
import numpy as np
import json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
# Use absolute path for database to avoid path issues
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'evoting.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'instance/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

db.init_app(app)
mail.init_app(app)

# Create necessary directories
os.makedirs('instance/uploads', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('static/images', exist_ok=True)
os.makedirs('templates/admin', exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_activity(action, details=None, admin_id=None, ip_address=None):
    """Log admin activity"""
    log = ActivityLog(
        action=action,
        details=json.dumps(details) if details else None,
        admin_id=admin_id,
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()

# ==================== VOTER ROUTES ====================

@app.route('/')
def home():
    """Home page"""
    return render_template('home.html')

@app.route('/help')
def help_page():
    """Help and Support page"""
    return render_template('help.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Enhanced voter registration with CNIC verification and age validation"""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        cnic = request.form.get('cnic', '').strip()
        mobile = request.form.get('mobile', '').strip()
        cnic_image = request.files.get('cnic_image')

        # Validation
        if not full_name or not cnic or not mobile:
            flash('Please fill in all fields.', 'error')
            return render_template('register.html')
        
        if not cnic_image:
            flash('Please upload your CNIC image.', 'error')
            return render_template('register.html')
        
        # Validate file type
        if not allowed_file(cnic_image.filename):
            flash('Invalid file type. Please upload an image file (PNG, JPG, JPEG, GIF).', 'error')
            return render_template('register.html')

        # Check for duplicate CNIC
        if Voter.query.filter_by(cnic=cnic).first():
            flash('This CNIC is already registered.', 'error')
            return render_template('register.html')
        
        # Check for duplicate mobile number
        if Voter.query.filter_by(mobile=mobile).first():
            flash('This phone number is already registered.', 'error')
            return render_template('register.html')

        # Save CNIC image
        filename = secure_filename(f"{cnic.replace('-', '')}_{cnic_image.filename}")
        cnic_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cnic_image.save(cnic_image_path)

        # Import CNIC OCR service
        from cnic_ocr import extract_cnic_data
        
        # Extract CNIC data from image
        cnic_data = extract_cnic_data(cnic_image_path)
        
        if not cnic_data['success']:
            # Delete uploaded file if OCR fails
            if os.path.exists(cnic_image_path):
                os.remove(cnic_image_path)
            flash(cnic_data['error'], 'error')
            return render_template('register.html')
        
        extracted_cnic = cnic_data['cnic_number']
        date_of_birth = cnic_data['date_of_birth']
        age = cnic_data['age']
        
        # CNIC Number Verification
        if extracted_cnic != cnic:
            # Delete uploaded file
            if os.path.exists(cnic_image_path):
                os.remove(cnic_image_path)
            flash('CNIC number does not match the uploaded CNIC image. Please upload the correct CNIC.', 'error')
            return render_template('register.html')
        
        # Age Verification
        if not date_of_birth:
            # Delete uploaded file
            if os.path.exists(cnic_image_path):
                os.remove(cnic_image_path)
            flash('Could not extract date of birth from CNIC. Please ensure the image is clear.', 'error')
            return render_template('register.html')
        
        if age is None or age < 18:
            # Delete uploaded file
            if os.path.exists(cnic_image_path):
                os.remove(cnic_image_path)
            flash('You must be at least 18 years old to register for voting.', 'error')
            return render_template('register.html')

        # Encrypt sensitive data
        encrypted_cnic = encrypt_data(cnic)
        encrypted_mobile = encrypt_data(mobile)

        # Create voter (without face encoding yet - will be added after biometric verification)
        voter = Voter(
            full_name=full_name,
            cnic=cnic,
            mobile=mobile,
            date_of_birth=date_of_birth,
            encrypted_cnic=encrypted_cnic,
            encrypted_mobile=encrypted_mobile,
            cnic_image_path=cnic_image_path
        )
        db.session.add(voter)
        db.session.commit()

        # Store voter info in session for biometric verification
        session['voter_id'] = voter.id
        session['cnic_image_path'] = cnic_image_path
        
        flash('CNIC verified successfully! Please proceed to facial verification.', 'success')
        return redirect(url_for('biometric_verification'))

    return render_template('register.html')

@app.route('/biometric')
def biometric_verification():
    """Biometric verification page"""
    if 'voter_id' not in session:
        flash('Please register first.', 'warning')
        return redirect(url_for('register'))
    
    voter_id = session['voter_id']
    voter = Voter.query.get(voter_id)
    
    if not voter:
        flash('Voter not found.', 'error')
        return redirect(url_for('register'))
    
    if voter.has_voted:
        flash('You have already voted.', 'info')
        return redirect(url_for('vote_success'))
    
    return render_template('biometric.html', voter_id=voter_id)

@app.route('/api/verify_face', methods=['POST'])
def verify_face():
    """Enhanced API endpoint for face verification - compares CNIC face with live face"""
    if 'voter_id' not in session:
        return jsonify({'success': False, 'message': 'Session expired'}), 401
    
    voter_id = session['voter_id']
    cnic_image_path = session.get('cnic_image_path')
    
    voter = Voter.query.get(voter_id)
    
    if not voter:
        return jsonify({'success': False, 'message': 'Voter not found'}), 404
    
    if not cnic_image_path or not os.path.exists(cnic_image_path):
        return jsonify({'success': False, 'message': 'CNIC image not found. Please register again.'}), 400
    
    # Get image data from request
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No image selected'}), 400
    
    # Read live camera image
    file.seek(0)
    nparr = np.frombuffer(file.read(), np.uint8)
    live_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if live_frame is None:
        return jsonify({'success': False, 'message': 'Invalid image'}), 400
    
    # Detect face in live frame
    face_detected, face_locations = detect_face_in_frame(live_frame)
    if not face_detected:
        return jsonify({'success': False, 'message': 'No face detected. Please ensure your face is visible and well-lit.'}), 400
    
    # Encode live face
    live_encoding = encode_face_from_frame(live_frame)
    if not live_encoding:
        return jsonify({'success': False, 'message': 'Could not process face. Please try again with better lighting.'}), 400
    
    # Check for duplicate face in database (prevent same person registering twice)
    all_voters = Voter.query.filter(Voter.id != voter_id, Voter.face_encoding.isnot(None)).all()
    for existing_voter in all_voters:
        existing_encoding = load_face_encoding(existing_voter.face_encoding)
        if existing_encoding and compare_faces(existing_encoding, live_encoding, tolerance=0.6):
            return jsonify({'success': False, 'message': 'This face is already registered. Duplicate registrations are not allowed.'}), 400
    
    # Import biometric comparison function
    from biometric import compare_cnic_face_with_live
    
    # Compare CNIC face with live face
    match, confidence, error = compare_cnic_face_with_live(cnic_image_path, live_frame, tolerance=0.6)
    
    if error:
        return jsonify({'success': False, 'message': error}), 400
    
    if not match:
        return jsonify({'success': False, 'message': 'Face does not match the CNIC. Registration rejected.'}), 400
    
    # Face matched! Save face encoding and image
    voter.face_encoding = save_face_encoding(live_encoding)
    
    # Save the live face image
    filename = secure_filename(f"{datetime.utcnow().timestamp()}_{voter_id}_face.jpg")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cv2.imwrite(filepath, live_frame)
    voter.face_image_path = f"uploads/{filename}"
    
    db.session.commit()
    
    # Mark as verified and auto-login
    session['face_verified'] = True
    session['logged_in'] = True
    
    # Clear temporary session data
    session.pop('cnic_image_path', None)
    
    return jsonify({
        'success': True, 
        'message': f'Identity verified successfully! Match confidence: {confidence:.1%}',
        'confidence': confidence
    })

@app.route('/candidates')
def candidates():
    """Candidate selection page"""
    if 'voter_id' not in session or not session.get('face_verified'):
        flash('Please complete biometric verification first.', 'warning')
        return redirect(url_for('biometric_verification'))
    
    voter_id = session['voter_id']
    voter = Voter.query.get(voter_id)
    
    if voter and voter.has_voted:
        flash('You have already voted.', 'info')
        return redirect(url_for('vote_success'))
    
    candidates = Candidate.query.filter_by(is_active=True).all()
    return render_template('candidates.html', candidates=candidates)

@app.route('/vote', methods=['POST'])
def vote():
    """Cast a vote"""
    if 'voter_id' not in session or not session.get('face_verified'):
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    voter_id = session['voter_id']
    candidate_id = request.json.get('candidate_id')
    
    if not candidate_id:
        return jsonify({'success': False, 'message': 'Please select a candidate'}), 400
    
    voter = Voter.query.get(voter_id)
    candidate = Candidate.query.get(candidate_id)
    
    if not voter or not candidate:
        return jsonify({'success': False, 'message': 'Invalid voter or candidate'}), 404
    
    if voter.has_voted:
        return jsonify({'success': False, 'message': 'You have already voted'}), 400
    
    if not candidate.is_active:
        return jsonify({'success': False, 'message': 'Candidate is not active'}), 400
    
    # Create vote hash for anonymity
    vote_hash = hash_vote(voter_id, candidate_id, datetime.utcnow().isoformat())
    
    # Check for duplicate vote hash (extremely unlikely but check anyway)
    if Vote.query.filter_by(vote_hash=vote_hash).first():
        return jsonify({'success': False, 'message': 'Vote processing error. Please try again.'}), 500
    
    # Create vote
    vote = Vote(
        voter_id=voter_id,
        candidate_id=candidate_id,
        vote_hash=vote_hash
    )
    db.session.add(vote)
    
    # Mark voter as voted
    voter.has_voted = True
    db.session.commit()
    
    # Clear session
    session.pop('face_verified', None)
    
    return jsonify({'success': True, 'message': 'Vote cast successfully!', 'redirect': url_for('vote_success')})

@app.route('/api/public/stats')
def public_stats():
    """Public API for real-time voting statistics"""
    candidates = Candidate.query.filter_by(is_active=True).all()
    total_votes = Vote.query.count()
    
    stats = []
    for candidate in candidates:
        vote_count = candidate.vote_count()
        percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
        stats.append({
            'name': candidate.name,
            'party': candidate.party,
            'photo_path': candidate.photo_path,
            'votes': vote_count,
            'percentage': round(percentage, 1)
        })
    
    # Sort by vote count descending
    stats.sort(key=lambda x: x['votes'], reverse=True)
    
    return jsonify({
        'success': True,
        'total_votes': total_votes,
        'candidates': stats
    })

@app.route('/vote_success')
def vote_success():
    """Vote success page"""
    return render_template('vote_success.html')

# ==================== ADMIN ROUTES ====================

@app.route('/admin')
def admin_login():
    """Admin login page"""
    return render_template('admin/login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    """Handle admin login"""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not email or not password:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('admin_login'))

    admin = Admin.query.filter_by(email=email).first()

    if not admin or not admin.check_password(password):
        flash('Invalid email or password.', 'error')
        return redirect(url_for('admin_login'))

    # Check if another admin is already logged in
    logged_in_admin = Admin.query.filter_by(is_logged_in=True).first()
    if logged_in_admin and logged_in_admin.id != admin.id:
        # Send alert email
        send_login_alert_email(logged_in_admin.email, request.remote_addr)
        flash('Another admin is already logged in. An alert has been sent.', 'warning')
        return redirect(url_for('admin_login'))

    # Login successful
    admin.is_logged_in = True
    admin.last_login = datetime.now()
    db.session.commit()

    session['admin_authenticated'] = True
    session['admin_id'] = admin.id

    log_activity('Admin Login', {'email': admin.email}, admin.id, request.remote_addr)

    flash('Login successful!', 'success')
    return redirect(url_for('admin_dashboard'))


# Face verification routes removed - admin login now uses password only
# @app.route('/admin/face_verification')
# @app.route('/admin/face_verify_process', methods=['POST'])
# @app.route('/admin/face_analyze_frame', methods=['POST'])


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with CNIC verification statistics"""
    total_voters = Voter.query.count()
    total_candidates = Candidate.query.filter_by(is_active=True).count()
    total_votes = Vote.query.count()
    voted_count = Voter.query.filter_by(has_voted=True).count()
    
    # CNIC verification statistics
    verified_voters = Voter.query.filter(Voter.cnic_image_path.isnot(None)).count()
    biometric_verified = Voter.query.filter(Voter.face_encoding.isnot(None)).count()
    age_verified = Voter.query.filter(Voter.date_of_birth.isnot(None)).count()
    
    stats = {
        'total_voters': total_voters,
        'total_candidates': total_candidates,
        'total_votes': total_votes,
        'voted_count': voted_count,
        'voting_percentage': (voted_count / total_voters * 100) if total_voters > 0 else 0,
        'verified_voters': verified_voters,
        'biometric_verified': biometric_verified,
        'age_verified': age_verified
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/logout')
@admin_required
def admin_logout():
    """Admin logout"""
    admin_id = session.get('admin_id')
    if admin_id:
        admin = Admin.query.get(admin_id)
        if admin:
            admin.is_logged_in = False
            db.session.commit()
        log_activity('Admin Logout', {}, admin_id, request.remote_addr)
    
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/voters')
@admin_required
def admin_voters():
    """View all voters with CNIC verification details"""
    voters = Voter.query.order_by(Voter.registered_at.desc()).all()
    return render_template('admin/voters.html', voters=voters, now=datetime.now().date())

@app.route('/admin/candidates', methods=['GET', 'POST'])
@admin_required
def admin_candidates():
    """Manage candidates"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name', '').strip()
            party = request.form.get('party', '').strip()
            description = request.form.get('description', '').strip()
            city = request.form.get('city', '').strip()
            assembly_type = request.form.get('assembly_type', '').strip()
            
            if not name:
                flash('Candidate name is required.', 'error')
                return redirect(url_for('admin_candidates'))
            
            # Handle file upload (cropped or original)
            photo_path = None
            cropped_image = request.form.get('cropped_image')
            
            if cropped_image:
                # Handle base64 cropped image
                try:
                    # Remove data URL prefix if present
                    if ',' in cropped_image:
                        cropped_image = cropped_image.split(',')[1]
                    
                    image_data = base64.b64decode(cropped_image)
                    filename = f"{datetime.now().timestamp()}_cropped.jpg"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(image_data)
                    
                    photo_path = f"uploads/{filename}"
                except Exception as e:
                    print(f"Error saving cropped image: {e}")
                    flash('Error processing cropped image.', 'error')
                    return redirect(url_for('admin_candidates'))
            elif 'photo' in request.files:
                # Handle regular file upload
                file = request.files['photo']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    photo_path = f"uploads/{filename}"
            
            candidate = Candidate(
                name=name,
                party=party,
                description=description,
                photo_path=photo_path,
                city=city,
                assembly_type=assembly_type
            )
            db.session.add(candidate)
            db.session.commit()
            
            log_activity('Add Candidate', {'candidate_id': candidate.id, 'name': name}, 
                        session.get('admin_id'), request.remote_addr)
            flash('Candidate added successfully.', 'success')
        
        elif action == 'edit':
            candidate_id = request.form.get('candidate_id')
            candidate = Candidate.query.get(candidate_id)
            
            if candidate:
                candidate.name = request.form.get('name', '').strip()
                candidate.party = request.form.get('party', '').strip()
                candidate.description = request.form.get('description', '').strip()
                candidate.city = request.form.get('city', '').strip()
                candidate.assembly_type = request.form.get('assembly_type', '').strip()
                
                # Handle cropped or regular image upload
                cropped_image = request.form.get('cropped_image')
                
                if cropped_image:
                    # Handle base64 cropped image
                    try:
                        # Delete old photo if exists
                        if candidate.photo_path:
                            old_path = os.path.join('instance', candidate.photo_path)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        # Remove data URL prefix if present
                        if ',' in cropped_image:
                            cropped_image = cropped_image.split(',')[1]
                        
                        image_data = base64.b64decode(cropped_image)
                        filename = f"{datetime.now().timestamp()}_cropped.jpg"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(image_data)
                        
                        candidate.photo_path = f"uploads/{filename}"
                    except Exception as e:
                        print(f"Error saving cropped image: {e}")
                        flash('Error processing cropped image.', 'error')
                        return redirect(url_for('admin_candidates'))
                elif 'photo' in request.files:
                    # Handle regular file upload
                    file = request.files['photo']
                    if file and file.filename != '' and allowed_file(file.filename):
                        # Delete old photo if exists
                        if candidate.photo_path:
                            old_path = os.path.join('instance', candidate.photo_path)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        candidate.photo_path = f"uploads/{filename}"
                
                db.session.commit()
                log_activity('Edit Candidate', {'candidate_id': candidate_id}, 
                            session.get('admin_id'), request.remote_addr)
                flash('Candidate updated successfully.', 'success')
        
        elif action == 'delete':
            candidate_id = request.form.get('candidate_id')
            candidate = Candidate.query.get(candidate_id)
            
            if candidate:
                # Delete photo file if exists
                if candidate.photo_path:
                    photo_file = os.path.join('instance', candidate.photo_path)
                    if os.path.exists(photo_file):
                        os.remove(photo_file)
                # Hard delete
                db.session.delete(candidate)
                db.session.commit()
                log_activity('Delete Candidate', {'candidate_id': candidate_id}, 
                            session.get('admin_id'), request.remote_addr)
                flash('Candidate deleted successfully.', 'success')
        
        return redirect(url_for('admin_candidates'))
    
    candidates = Candidate.query.filter_by(is_active=True).order_by(Candidate.created_at.desc()).all()
    pakistan_cities = [
        'Abbottabad', 'Attock', 'Awaran', 'Badin', 'Bahawalnagar', 'Bahawalpur',
        'Bannu', 'Batagram', 'Bhalwal', 'Bhimber', 'Burewala', 'Chakwal',
        'Chaman', 'Charsadda', 'Chiniot', 'Chishtian', 'Dadu', 'Dera Ghazi Khan',
        'Dera Ismail Khan', 'Faisalabad', 'Ghotki', 'Gilgit', 'Gojra', 'Gujranwala',
        'Gujrat', 'Gwadar', 'Hafizabad', 'Haripur', 'Hub', 'Hyderabad',
        'Islamabad', 'Jacobabad', 'Jhelum', 'Jhang', 'Kamalia', 'Karachi',
        'Kasur', 'Khanewal', 'Kharian', 'Khushab', 'Khuzdar', 'Kohat',
        'Kohlu', 'Kot Addu', 'Kotli', 'Lahore', 'Larkana', 'Layyah',
        'Lodhran', 'Loralai', 'Malakand', 'Mandi Bahauddin', 'Mansehra',
        'Mardan', 'Mastung', 'Mianwali', 'Mingora', 'Mirpur', 'Mirpur Khas',
        'Multan', 'Murree', 'Muzaffarabad', 'Muzaffargarh', 'Narowal',
        'Nawabshah', 'Nowshera', 'Okara', 'Pakpattan', 'Peshawar', 'Pishin',
        'Quetta', 'Rahim Yar Khan', 'Rajanpur', 'Rawalpindi', 'Sahiwal',
        'Sargodha', 'Shahdadkot', 'Sheikhupura', 'Shikarpur', 'Sialkot',
        'Sibi', 'Sukkur', 'Swabi', 'Swat', 'Tank', 'Tando Adam',
        'Tando Allahyar', 'Toba Tek Singh', 'Turbat', 'Vehari', 'Wah Cantt',
        'Zhob'
    ]
    return render_template('admin/candidates.html', candidates=candidates, pakistan_cities=pakistan_cities)

@app.route('/admin/statistics')
@admin_required
def admin_statistics():
    """View voting statistics"""
    candidates = Candidate.query.filter_by(is_active=True).all()
    vote_stats = []
    
    for candidate in candidates:
        vote_count = candidate.vote_count()
        vote_stats.append({
            'candidate': candidate,
            'vote_count': vote_count
        })
    
    total_votes = Vote.query.count()
    
    # Sort by vote count
    vote_stats.sort(key=lambda x: x['vote_count'], reverse=True)
    
    return render_template('admin/statistics.html', vote_stats=vote_stats, total_votes=total_votes)

@app.route('/api/admin/statistics')
@admin_required
def api_admin_statistics():
    """API endpoint for voting statistics"""
    candidates = Candidate.query.filter_by(is_active=True).all()
    vote_stats = []
    total_votes = Vote.query.count()
    
    for candidate in candidates:
        vote_count = candidate.vote_count()
        vote_stats.append({
            'candidate_id': candidate.id,
            'name': candidate.name,
            'vote_count': vote_count,
            'percentage': (vote_count / total_votes * 100) if total_votes > 0 else 0
        })
    
    # Sort by vote count per UI expectations
    vote_stats.sort(key=lambda x: x['vote_count'], reverse=True)
    
    return jsonify({
        'success': True,
        'vote_stats': vote_stats,
        'total_votes': total_votes
    })

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """View activity logs"""
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return render_template('admin/logs.html', logs=logs)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory('instance/uploads', filename)

# ==================== STATIC FILE CACHE CONTROL ====================

@app.after_request
def add_header(response):
    """Add cache control headers to static files"""
    if 'static' in request.path:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ==================== INITIALIZATION ====================

def init_db():
    """Initialize database tables and default admin"""
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if not Admin.query.filter_by(email=admin_email).first():
            admin = Admin(email=admin_email)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"Default admin created: {admin_email} / {admin_password}")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)

from flask_mail import Mail, Message
from flask import current_app
import random
import string
from datetime import datetime, timedelta

mail = Mail()

def generate_otp(length=6):
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(admin_email, otp):
    """Send OTP to admin email"""
    try:
        # Check if mail is configured
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            print(f"\n{'='*60}")
            print(f"EMAIL NOT CONFIGURED - OTP for {admin_email}: {otp}")
            print(f"{'='*60}\n")
            return False
        
        msg = Message(
            subject='E-Voting System - Admin Login OTP',
            recipients=[admin_email],
            body=f'''
Your OTP for admin login is: {otp}

This OTP will expire in 10 minutes.

If you did not request this OTP, please ignore this email or contact the system administrator.

E-Voting System
            ''',
            html=f'''
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #2c3e50;">E-Voting System - Admin Login OTP</h2>
                <p>Your OTP for admin login is:</p>
                <h1 style="color: #3498db; font-size: 32px; letter-spacing: 5px;">{otp}</h1>
                <p>This OTP will expire in <strong>10 minutes</strong>.</p>
                <p style="color: #7f8c8d; font-size: 12px;">If you did not request this OTP, please ignore this email or contact the system administrator.</p>
                <hr>
                <p style="color: #95a5a6; font-size: 11px;">E-Voting System</p>
            </body>
            </html>
            '''
        )
        mail.send(msg)
        print(f"OTP email sent successfully to {admin_email}")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"\n{'='*60}")
        print(f"ERROR SENDING EMAIL: {error_msg}")
        print(f"\nOTP for {admin_email}: {otp}")
        print(f"{'='*60}\n")
        
        # Common error messages
        if "authentication failed" in error_msg.lower() or "535" in error_msg:
            print("TIP: Gmail requires an App Password, not your regular password.")
            print("Get one at: https://myaccount.google.com/apppasswords")
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            print("TIP: Check your internet connection and firewall settings.")
        
        return False

def send_login_alert_email(admin_email, ip_address):
    """Send alert email when another login attempt occurs"""
    try:
        msg = Message(
            subject='E-Voting System - Security Alert',
            recipients=[admin_email],
            body=f'''
SECURITY ALERT

A login attempt was made to your admin account while you are already logged in.

IP Address: {ip_address}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

If this was not you, please change your password immediately and contact the system administrator.

E-Voting System
            ''',
            html=f'''
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #e74c3c;">SECURITY ALERT</h2>
                <p>A login attempt was made to your admin account while you are already logged in.</p>
                <p><strong>IP Address:</strong> {ip_address}</p>
                <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p style="color: #e74c3c;">If this was not you, please change your password immediately and contact the system administrator.</p>
                <hr>
                <p style="color: #95a5a6; font-size: 11px;">E-Voting System</p>
            </body>
            </html>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending alert email: {e}")
        return False

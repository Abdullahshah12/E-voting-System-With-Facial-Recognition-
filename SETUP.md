# Quick Setup Guide

## Windows Setup

1. **Install Python 3.8+** from python.org

2. **Install CMake** (required for face-recognition):
   - Download from https://cmake.org/download/
   - Add to PATH during installation

3. **Open PowerShell/CMD in project directory**:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install CMake and dlib (this may take 10-15 minutes)
pip install cmake
pip install dlib

# Install other dependencies
pip install -r requirements.txt
```

4. **Create `.env` file**:
```
SECRET_KEY=dev-secret-key-12345
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
```

5. **Run the application**:
```powershell
python app.py
```

6. **Access the application**:
   - Voter Portal: http://localhost:5000
   - Admin Portal: http://localhost:5000/admin
   - Default Admin: Use ADMIN_EMAIL and ADMIN_PASSWORD from .env

## Troubleshooting

### face-recognition installation fails
- Try installing Visual Studio Build Tools
- Or use conda: `conda install -c conda-forge dlib`
- Or temporarily disable face recognition for testing

### Email not working
- Check Gmail app password settings
- Verify MAIL_USERNAME and MAIL_PASSWORD in .env
- Check firewall/antivirus blocking SMTP

### Camera not working
- Grant camera permissions in browser
- Check if camera is being used by another application
- Try different browser (Chrome recommended)

## Testing Without Email

For testing without email setup, you can modify the code to print OTP to console instead of sending email.

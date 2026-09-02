"""
Installation script for CNIC Verification feature
Checks dependencies and provides installation guidance
"""

import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_package(package_name, import_name=None):
    """Check if a Python package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✅ {package_name} is installed")
        return True
    except ImportError:
        print(f"❌ {package_name} is NOT installed")
        return False

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ Tesseract OCR is installed: {version_line}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("❌ Tesseract OCR is NOT installed")
    return False

def print_installation_guide():
    """Print installation instructions based on OS"""
    os_name = platform.system()
    
    print("\n" + "="*60)
    print("INSTALLATION GUIDE")
    print("="*60)
    
    print("\n1. Install Python packages:")
    print("   pip install -r requirements.txt")
    
    print("\n2. Install Tesseract OCR:")
    if os_name == "Windows":
        print("   - Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   - Run the installer (tesseract-ocr-w64-setup-v5.x.x.exe)")
        print("   - Add to PATH or set in code:")
        print("     pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")
    elif os_name == "Linux":
        print("   sudo apt-get update")
        print("   sudo apt-get install tesseract-ocr")
    elif os_name == "Darwin":  # macOS
        print("   brew install tesseract")
    
    print("\n3. Install face-recognition (optional but recommended):")
    if os_name == "Windows":
        print("   - Install Visual Studio Build Tools")
        print("   - Install CMake")
        print("   - pip install dlib")
        print("   - pip install face-recognition")
    else:
        print("   pip install dlib")
        print("   pip install face-recognition")
    
    print("\n4. Database Migration:")
    print("   python clear_database.py  # For fresh start")
    print("   python app.py             # Start application")
    
    print("\n" + "="*60)

def main():
    """Main installation check"""
    print("="*60)
    print("CNIC VERIFICATION FEATURE - DEPENDENCY CHECK")
    print("="*60)
    print()
    
    all_ok = True
    
    # Check Python version
    if not check_python_version():
        all_ok = False
    print()
    
    # Check required packages
    print("Checking Python packages...")
    packages = [
        ('Flask', 'flask'),
        ('Flask-SQLAlchemy', 'flask_sqlalchemy'),
        ('Flask-Mail', 'flask_mail'),
        ('OpenCV', 'cv2'),
        ('NumPy', 'numpy'),
        ('Pillow', 'PIL'),
        ('cryptography', 'cryptography'),
        ('python-dotenv', 'dotenv'),
        ('bcrypt', 'bcrypt'),
        ('pytesseract', 'pytesseract'),
    ]
    
    for package_name, import_name in packages:
        if not check_package(package_name, import_name):
            all_ok = False
    
    # Check optional packages
    print("\nChecking optional packages...")
    check_package('face-recognition', 'face_recognition')
    check_package('dlib', 'dlib')
    
    print()
    
    # Check Tesseract
    print("Checking external dependencies...")
    if not check_tesseract():
        all_ok = False
    
    print()
    
    # Summary
    if all_ok:
        print("="*60)
        print("✅ ALL REQUIRED DEPENDENCIES ARE INSTALLED!")
        print("="*60)
        print("\nYou can now run the application:")
        print("  python app.py")
        print("\nFor first-time setup, run:")
        print("  python clear_database.py")
        print("  python app.py")
    else:
        print("="*60)
        print("❌ SOME DEPENDENCIES ARE MISSING")
        print("="*60)
        print_installation_guide()
    
    print()

if __name__ == "__main__":
    main()

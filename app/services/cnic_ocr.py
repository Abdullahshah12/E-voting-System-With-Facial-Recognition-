"""
CNIC OCR Service
Extracts CNIC number and Date of Birth from CNIC card images using OCR
"""

import re
import cv2
import numpy as np
from PIL import Image
from datetime import datetime

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def preprocess_cnic_image(image_path):
    """
    Preprocess CNIC image for better OCR accuracy
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    # Upscale for better OCR
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

    # Apply adaptive thresholding (better than Otsu for uneven lighting)
    thresh = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 2)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)

    return denoised


def extract_cnic_number(text):
    """
    Extract CNIC number from OCR text
    CNIC format: 12345-1234567-1
    """
    # Fix common OCR misreads: O->0, I/l->1, S->5, B->8, Z->2
    ocr_fixes = str.maketrans('OoIlSsBbZz', '0011558822')
    fixed_text = text.translate(ocr_fixes)

    print(f"[DEBUG] OCR raw text:\n{text}")
    print(f"[DEBUG] OCR fixed text:\n{fixed_text}")

    # Pattern 1: standard CNIC with hyphens (may have spaces around hyphens)
    pattern1 = r'(\d{5})\s*[-—]\s*(\d{7})\s*[-—]\s*(\d{1})'
    match = re.search(pattern1, fixed_text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    # Pattern 2: 13 consecutive digits (no hyphens)
    pattern2 = r'\b(\d{13})\b'
    match = re.search(pattern2, fixed_text)
    if match:
        cnic = match.group(1)
        return f"{cnic[0:5]}-{cnic[5:12]}-{cnic[12]}"

    # Pattern 3: digits with spaces instead of hyphens e.g. "12345 1234567 1"
    pattern3 = r'(\d{5})\s+(\d{7})\s+(\d{1})\b'
    match = re.search(pattern3, fixed_text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    # Pattern 4: strip everything non-digit and try 13 digits
    digits_only = re.sub(r'\D', '', fixed_text)
    match = re.search(r'(\d{13})', digits_only)
    if match:
        cnic = match.group(1)
        return f"{cnic[0:5]}-{cnic[5:12]}-{cnic[12]}"

    return None


def extract_date_of_birth(text):
    """
    Extract date of birth from OCR text
    Common formats: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
    """
    # Pattern for various date formats
    patterns = [
        r'\b(\d{2})[\./-](\d{2})[\./-](\d{4})\b',  # DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
        r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b',  # DD Month YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                if len(match.groups()) == 3:
                    if match.group(2).isalpha():
                        # Month name format
                        date_str = f"{match.group(1)} {match.group(2)} {match.group(3)}"
                        dob = datetime.strptime(date_str, "%d %b %Y")
                    else:
                        # Numeric format
                        day, month, year = match.group(1), match.group(2), match.group(3)
                        dob = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
                    
                    return dob.date()
            except ValueError:
                continue
    
    return None


def calculate_age(date_of_birth):
    """
    Calculate age from date of birth
    """
    if not date_of_birth:
        return None
    
    today = datetime.today().date()
    age = today.year - date_of_birth.year
    
    # Adjust if birthday hasn't occurred this year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    
    return age


def extract_cnic_data(image_path):
    """
    Main function to extract CNIC number and DOB from CNIC image
    Returns: dict with 'cnic_number', 'date_of_birth', 'age', 'success', 'error'
    """
    if not TESSERACT_AVAILABLE:
        return {
            'success': False,
            'error': 'OCR library not available. Please install pytesseract.',
            'cnic_number': None,
            'date_of_birth': None,
            'age': None
        }
    
    try:
        # Preprocess image
        processed_img = preprocess_cnic_image(image_path)

        # Tesseract config: treat as single block, digits+symbols
        custom_config = r'--oem 3 --psm 6'

        # Perform OCR on preprocessed image
        text = pytesseract.image_to_string(processed_img, lang='eng', config=custom_config)

        # Also try on original image with different PSM
        original_text = pytesseract.image_to_string(image_path, lang='eng', config=r'--oem 3 --psm 3')

        # Combine both texts for better extraction
        combined_text = text + "\n" + original_text
        
        # Extract CNIC number
        cnic_number = extract_cnic_number(combined_text)
        
        # Extract date of birth
        date_of_birth = extract_date_of_birth(combined_text)
        
        # Calculate age
        age = calculate_age(date_of_birth) if date_of_birth else None
        
        if not cnic_number:
            return {
                'success': False,
                'error': 'Could not extract CNIC number from image. Please ensure the image is clear and readable.',
                'cnic_number': None,
                'date_of_birth': date_of_birth,
                'age': age
            }
        
        return {
            'success': True,
            'error': None,
            'cnic_number': cnic_number,
            'date_of_birth': date_of_birth,
            'age': age
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Error processing CNIC image: {str(e)}',
            'cnic_number': None,
            'date_of_birth': None,
            'age': None
        }


def extract_face_from_cnic(image_path):
    """
    Extract face region from CNIC image for facial verification
    Returns the face region as a numpy array or None
    """
    try:
        # Load the cascade classifier for face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Read image
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) == 0:
            return None
        
        # Get the largest face (assuming it's the main face on CNIC)
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face
        
        # Extract face region
        face_img = img[y:y+h, x:x+w]
        
        return face_img
    
    except Exception as e:
        print(f"Error extracting face from CNIC: {str(e)}")
        return None

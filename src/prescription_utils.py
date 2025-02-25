import sqlite3
from datetime import datetime
import os
import pdfplumber
import pytesseract
import google.generativeai as genai
import pandas as pd  # if needed for get_medicine_recommendations

def init_db(db_path="data/pharmacy.db"):
    """
    Initialize the pharmacy database if it doesn't exist.
    Creates 'medicines' and 'orders' tables and inserts sample data.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create 'medicines' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            dosage TEXT,
            quantity INTEGER,
            price REAL
        )
    ''')
    
    # Create 'orders' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            medicine_name TEXT NOT NULL,
            quantity INTEGER,
            patient_name TEXT,
            doctor_name TEXT,
            date TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # Insert sample data if empty
    c.execute("SELECT COUNT(*) FROM medicines")
    if c.fetchone()[0] == 0:
        sample_medicines = [
            ('Amoxicillin', '500mg', 100, 12.99),
            ('Lisinopril', '10mg', 50, 15.50),
            ('Metformin', '850mg', 60, 8.75),
            ('Atorvastatin', '20mg', 30, 22.00),
            ('Sertraline', '50mg', 45, 18.25)
        ]
        c.executemany(
            "INSERT INTO medicines (name, dosage, quantity, price) VALUES (?, ?, ?, ?)",
            sample_medicines
        )
    
    conn.commit()
    conn.close()

def extract_prescription_text(image):
    """
    Attempt to extract text from an image using Gemini first, then fallback to Tesseract OCR.
    Note: This function expects genai.configure(api_key=...) to be called beforehand if using Gemini.
    """
    # Convert RGBA to RGB if needed
    if image.mode == "RGBA":
        image = image.convert("RGB")
    
    import io
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='JPEG')
    image_bytes = image_bytes.getvalue()

    try:
        model = genai.GenerativeModel('gemini-pro-vision')
        prompt = """
        Please analyze this prescription image and extract the following information in this exact format:
        
        Patient: [Patient Name]
        Doctor: [Doctor Name]
        Medicine: [Medicine Name]
        Dosage: [Dosage]
        Quantity: [Quantity]
        Instructions: [Instructions if any]
        
        If any field is not visible or unclear, use "Not found" for that field.
        """
        response = model.generate_content([prompt, image_bytes])
        return response.text
    except Exception as e:
        print(f"Gemini API failed: {e}. Falling back to Tesseract OCR.")
        return pytesseract.image_to_string(image)

def parse_prescription(text):
    """
    Parse text from Gemini or Tesseract to extract relevant fields.
    Returns a dict with keys:
        patient_name, doctor_name, medicine_name, dosage, quantity, instructions
    """
    result = {
        "patient_name": "Not found",
        "doctor_name": "Not found",
        "medicine_name": "Not found",
        "dosage": "Not found",
        "quantity": 0,
        "instructions": "Not found"
    }

    lines = text.strip().split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if 'patient' in key and value != "[Patient Name]":
                result["patient_name"] = value
            elif 'doctor' in key and value != "[Doctor Name]":
                result["doctor_name"] = value
            elif 'medicine' in key and value != "[Medicine Name]":
                result["medicine_name"] = value
            elif 'dosage' in key and value != "[Dosage]":
                result["dosage"] = value
            elif 'quantity' in key and value != "[Quantity]":
                try:
                    result["quantity"] = int(value)
                except:
                    result["quantity"] = value
            elif 'instructions' in key and value != "[Instructions if any]":
                result["instructions"] = value

    return result

def check_medicine_in_db(medicine_name, db_path="data/pharmacy.db"):
    """
    Returns (found_bool, row) indicating if the medicine exists and the DB row if found.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM medicines WHERE name LIKE ?", (f"%{medicine_name}%",))
    result = c.fetchone()
    conn.close()
    return (result is not None, result)

def create_medicine_order(medicine_name, quantity, patient_name, doctor_name, db_path="data/pharmacy.db"):
    """
    Insert a new order into the 'orders' table. Return the newly created order ID.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    current_date = datetime.now().strftime("%Y-%m-%d")

    if isinstance(quantity, str):
        try:
            quantity = int(quantity)
        except:
            quantity = 1

    c.execute("""
        INSERT INTO orders (medicine_name, quantity, patient_name, doctor_name, date)
        VALUES (?, ?, ?, ?, ?)
    """, (medicine_name, quantity, patient_name, doctor_name, current_date))

    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_context(text, keyword):
    """
    Return some context around the keyword from the given text, or None if not found.
    """
    keyword_pos = text.lower().find(keyword.lower())
    if keyword_pos >= 0:
        start = max(0, keyword_pos - 50)
        end = min(len(text), keyword_pos + len(keyword) + 50)
        snippet = text[start:end]
        return f"...{snippet}..."
    return None

def search_pdf_reports(keyword, pdf_dir="pdf_reports"):
    """
    Basic PDF search for a keyword. Creates 'pdf_reports' dir if needed.
    Returns a list of dicts with filename, page, path.
    """
    results = []
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)

    for filename in os.listdir(pdf_dir):
        if filename.endswith(".pdf"):
            file_path = os.path.join(pdf_dir, filename)
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        if keyword.lower() in text.lower():
                            results.append({
                                "filename": filename,
                                "page": i + 1,
                                "path": file_path
                            })
            except Exception as e:
                print(f"Could not process {filename}: {e}")
    return results

def get_medicine_recommendations(medicine_name, db_path="data/pharmacy.db"):
    """
    Use gemini-pro to find similar medicines from the DB.
    """
    try:
        conn = sqlite3.connect(db_path)
        medicines_df = pd.read_sql("SELECT name, dosage FROM medicines", conn)
        conn.close()

        medicine_list = medicines_df.to_dict('records')
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Based on the medicine "{medicine_name}", suggest 3 alternatives or similar medications from this list:
        {medicine_list}

        For each suggestion, explain why it's an alternative (e.g., same drug class, similar effects, etc.).
        Only suggest from the provided list and respond in this format:

        1. [Medicine Name] ([Dosage]): [Reason for recommendation]
        2. [Medicine Name] ([Dosage]): [Reason for recommendation]
        3. [Medicine Name] ([Dosage]): [Reason for recommendation]

        If no alternatives can be found, respond with "No similar medications found in the database."
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Could not generate recommendations: {e}"

Pharmacist Assistant: AI-Powered Prescription Management
An AI-driven application that scans prescription images, manages a local medicine database, tracks orders, searches PDF reports, and generates PDF forms for unavailable medicines. Built using Streamlit, SQLite, Tesseract OCR, and Google Generative AI (Gemini).


Table of Contents
1. Project Overview
2. Environment Setup
3. How to Run
4. Code Structure
5. Usage Guide
6. Additional Details

Project Overview
Goal: Demonstrate how AI can streamline pharmacy workflows by extracting prescription details automatically, storing data in a local database, generating orders, and searching PDF reports for relevant info.

Key Features:
Prescription Scanning (Gemini Vision + Tesseract fallback)
Medicine Database (View/Add medicines in SQLite)
Order Management (Create & track orders)
PDF Report Search (Upload & keyword search)
Generate PDF Order Forms (For unavailable medicines)

Environment Setup:-

Clone this repository:
git clone https://github.com/pri998/Pharmacist_Assistant.git
cd Pharmacist_Assistant

Install all dependencies:
pip install -r requirements.txt

Install Tesseract (for OCR fallback):
Windows: UB Mannheim Tesseract Installer
macOS: brew install tesseract
Linux (Debian/Ubuntu): sudo apt-get install tesseract-ocr


How to Run:
Navigate to the project folder:
cd Pharmacist_Assistant
Launch the Streamlit app:
streamlit run app.py
Open your browser to http://localhost:8501 (or the URL displayed in your terminal).


Code Structure
Copy
Pharmacist_Assistant/
├── .streamlit/
│   └── secrets.toml         # Stores GEMINI_API_KEY
├── data/
│   └── pharmacy.db          # Local SQLite database (created automatically)
├── src/
│   ├── prescription_utils.py  # AI (Gemini/Tesseract) + DB logic
│   └── pdf_utils.py           # PDF generation logic
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
└── README.md               # This file


Key Files
app.py: Single entry point for the Streamlit UI.
prescription_utils.py:
init_db(): Sets up the DB and inserts sample medicines.
extract_prescription_text(): Attempts Gemini Vision, then falls back to Tesseract.
parse_prescription(): Parses text for patient, doctor, medicine, etc.
create_medicine_order(): Inserts a new order into the DB.
search_pdf_reports(): Searches PDFs for a keyword.
pdf_utils.py:
generate_pdf(medicine_data): Creates a PDF with the provided medicines, quantities, and reasons.


Usage Guide:
After launching the app, use the sidebar to select tasks:

Prescription Scanning

Upload an image (.jpg, .png).
The app extracts text using Gemini or Tesseract.
Displays parsed data.
If medicine is not in the DB, optionally create an order.
Medicine Database

View current medicines (name, dosage, quantity, price).
Add new medicines via a form.
Order Management

View all orders, update status (Pending, Processing, Completed, Cancelled).
Create new orders manually.
PDF Report Search

Upload PDF reports to pdf_reports/.
Search by keyword.
Displays file/page matches.
Generate Order PDF

Enter a list of unavailable medicines (name, quantity, reason).
Creates a PDF form for ordering them.


Additional Details
Fallback OCR: If Gemini Vision fails, you’ll see a console message “Falling back to Tesseract OCR.” The extracted text might be partial or garbled if Tesseract can’t read the handwriting.
Local DB: The pharmacy.db file is created automatically in data/.
Sample Data: If no medicines exist, the app seeds 5 example entries (Amoxicillin, Lisinopril, etc.).
Extending: For advanced features (drug interaction checks, allergy warnings, scheduling, dashboards), see the Potential Enhancements in the code comments or in issues/pull requests.


Enjoy using the Pharmacist Assistant! If you have questions, feel free to open an issue or submit a pull request.
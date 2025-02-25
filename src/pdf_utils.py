import tempfile
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_pdf(medicine_data):
    """
    Creates a PDF order form for the given list of (name, quantity, reason).
    Returns the path to the generated PDF file.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_file.name
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "Medicine Order Form")
    
    c.setFont("Helvetica", 12)
    y_position = height - 100
    
    for i, (name, quantity, reason) in enumerate(medicine_data):
        c.drawString(50, y_position, f"{i+1}. Medicine Name: {name}")
        c.drawString(50, y_position - 20, f"   Quantity: {quantity}")
        c.drawString(50, y_position - 40, f"   Reason: {reason}")
        y_position -= 70
    
    c.save()
    return pdf_path

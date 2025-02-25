import streamlit as st
import pandas as pd
import os
from PIL import Image
import sqlite3
import google.generativeai as genai

# Import your utility modules from the 'src' folder
from src.prescription_utils import (
    init_db, extract_prescription_text, parse_prescription,
    check_medicine_in_db, create_medicine_order,
    search_pdf_reports, get_medicine_recommendations
)
from src.pdf_utils import generate_pdf

# IMPORTANT: set_page_config must be the first Streamlit command
st.set_page_config(page_title="Pharmacist Assistant", page_icon="💊", layout="wide")

def main():
    # Configure Gemini with the secret
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        gemini_status = "✅ Configured"
    except:
        gemini_status = "⚠️ Not Configured"
    
    st.title("Pharmacist Assistant App")

    st.sidebar.write(f"Gemini API: {gemini_status}")

    # Initialize DB
    init_db("data/pharmacy.db")

    # Sidebar nav
    page = st.sidebar.selectbox("Choose a task", 
                                ["Prescription Scanning", 
                                 "Medicine Database", 
                                 "Order Management",
                                 "PDF Report Search",
                                 "Generate Order PDF"])

    if page == "Prescription Scanning":
        st.header("Prescription Scanning")
        uploaded_file = st.file_uploader("Upload a prescription image", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Prescription", width=400)
            
            if st.button("Process Prescription"):
                with st.spinner("Extracting..."):
                    text = extract_prescription_text(image)
                    st.subheader("Raw Extracted Text")
                    st.text(text)

                    parsed = parse_prescription(text)
                    st.subheader("Parsed Prescription Data")
                    st.write(parsed)

                    # Check DB
                    med_exists, med_details = check_medicine_in_db(parsed["medicine_name"], "data/pharmacy.db")
                    if med_exists:
                        st.success("Medicine found in database!")
                        st.write({
                            "id": med_details[0],
                            "name": med_details[1],
                            "dosage": med_details[2],
                            "available_quantity": med_details[3],
                            "price": med_details[4]
                        })
                    else:
                        st.warning("Medicine not found in DB")
                        if st.button("Create Order"):
                            order_id = create_medicine_order(
                                parsed["medicine_name"],
                                parsed["quantity"],
                                parsed["patient_name"],
                                parsed["doctor_name"],
                                db_path="data/pharmacy.db"
                            )
                            st.success(f"Order created! ID: {order_id}")

    elif page == "Medicine Database":
        st.header("Medicine Database")
        # Show existing medicines
        conn = sqlite3.connect("data/pharmacy.db")
        df = pd.read_sql("SELECT * FROM medicines", conn)
        conn.close()

        st.subheader("Current Inventory")
        st.dataframe(df)

        # Add new medicine form
        st.subheader("Add New Medicine")
        with st.form("add_medicine_form"):
            name = st.text_input("Medicine Name")
            dosage = st.text_input("Dosage")
            quantity = st.number_input("Quantity", min_value=1, value=50)
            price = st.number_input("Price", min_value=0.01, value=10.00, format="%.2f")
            submit = st.form_submit_button("Add Medicine")

            if submit and name:
                conn = sqlite3.connect("data/pharmacy.db")
                c = conn.cursor()
                c.execute("""
                    INSERT INTO medicines (name, dosage, quantity, price)
                    VALUES (?, ?, ?, ?)
                """, (name, dosage, quantity, price))
                conn.commit()
                conn.close()
                st.success(f"Added {name} to the database!")
                st.experimental_rerun()

    elif page == "Order Management":
        st.header("Order Management")
        conn = sqlite3.connect("data/pharmacy.db")
        orders_df = pd.read_sql("SELECT * FROM orders ORDER BY date DESC", conn)
        conn.close()

        if not orders_df.empty:
            st.subheader("Current Orders")
            st.dataframe(orders_df)

            order_ids = orders_df['id'].tolist()
            selected_order = st.selectbox("Select Order to Update", order_ids)
            new_status = st.selectbox("Update Status", ["Pending", "Processing", "Completed", "Cancelled"])

            if st.button("Update Order Status"):
                conn = sqlite3.connect("data/pharmacy.db")
                c = conn.cursor()
                c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, selected_order))
                conn.commit()
                conn.close()
                st.success(f"Updated order #{selected_order} to {new_status}")
                st.experimental_rerun()
        else:
            st.info("No orders in the system yet")

        # Create new order
        st.subheader("Create New Order")
        with st.form("create_order_form"):
            med_name = st.text_input("Medicine Name")
            qty = st.number_input("Quantity", min_value=1, value=1)
            patient_nm = st.text_input("Patient Name")
            doc_nm = st.text_input("Doctor Name")
            submit_order = st.form_submit_button("Create Order")

            if submit_order and med_name and patient_nm:
                new_id = create_medicine_order(med_name, qty, patient_nm, doc_nm, "data/pharmacy.db")
                st.success(f"Order created! ID: {new_id}")
                st.experimental_rerun()

    elif page == "PDF Report Search":
        st.header("PDF Report Search")
        # Upload PDF
        st.subheader("Upload PDF Report")
        pdf_file = st.file_uploader("Upload a PDF report", type=["pdf"])
        if pdf_file is not None:
            pdf_dir = "pdf_reports"
            if not os.path.exists(pdf_dir):
                os.makedirs(pdf_dir)
            file_path = os.path.join(pdf_dir, pdf_file.name)
            with open(file_path, "wb") as f:
                f.write(pdf_file.getvalue())
            st.success(f"Uploaded {pdf_file.name}")

        # Search
        st.subheader("Search PDFs")
        keyword = st.text_input("Enter search keyword")
        if st.button("Search PDFs"):
            results = search_pdf_reports(keyword, pdf_dir="pdf_reports")
            if results:
                st.success(f"Found {len(results)} results for '{keyword}'")
                for i, r in enumerate(results):
                    with st.expander(f"Result {i+1}: {r['filename']} (Page {r['page']})"):
                        st.write(r)
            else:
                st.info(f"No results found for '{keyword}'")

    elif page == "Generate Order PDF":
        st.header("Generate PDF for Unavailable Medicines")

        num_meds = st.number_input("Number of medicines", min_value=1, max_value=10, value=1)
        medicine_data = []
        for i in range(num_meds):
            name = st.text_input(f"Medicine {i+1} Name")
            qty = st.number_input(f"Quantity for {name}", min_value=1, value=1, key=f"qty_{i}")
            reason = st.text_area(f"Reason for unavailability of {name}", key=f"reason_{i}")
            if name:
                medicine_data.append((name, qty, reason))

        if st.button("Generate PDF"):
            if medicine_data:
                pdf_path = generate_pdf(medicine_data)
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button("Download PDF", data=pdf_bytes, file_name="Medicine_Order.pdf", mime="application/pdf")
                os.remove(pdf_path)
            else:
                st.error("No medicine data entered.")

if __name__ == "__main__":
    main()

import os
from datetime import datetime
from fpdf import FPDF
import pandas as pd
import qrcode

INVOICE_DIR = "invoices"
REPORT_DIR = "reports"

os.makedirs(INVOICE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


def open_file_automatically(filepath):
    try:
        os.startfile(os.path.abspath(filepath))
    except Exception:
        pass


def generate_pdf_invoice(sale_data):
    """Scannable QR Code එකක් සහිත Professional PDF Invoice එකක් හදනවා"""
    pdf = FPDF()
    pdf.add_page()

    # --- Header Banner ---
    pdf.set_fill_color(20, 33, 61)
    pdf.rect(0, 0, 210, 35, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(10, 8)
    pdf.cell(120, 10, "NEXAPOS PRO")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(10, 19)
    pdf.cell(120, 6, "Enterprise Billing & Inventory System | Colombo, Sri Lanka")

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(140, 11)
    pdf.cell(60, 10, "TAX INVOICE", align="R")

    # --- Invoice Meta Details ---
    pdf.set_text_color(30, 30, 30)
    pdf.set_y(43)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 7, f"Invoice No: {sale_data['invoice_no']}")
    pdf.cell(90, 7, f"Date: {sale_data['sale_date']}", align="R")
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(100, 7, f"Customer: {sale_data['customer_name']}")
    pdf.cell(90, 7, f"Payment Method: {sale_data['payment_method']}", align="R")
    pdf.ln(12)

    # --- Items Table Header ---
    pdf.set_fill_color(230, 236, 245)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(15, 9, "#", border=1, align="C", fill=True)
    pdf.cell(85, 9, "Product Description", border=1, align="L", fill=True)
    pdf.cell(20, 9, "Qty", border=1, align="C", fill=True)
    pdf.cell(35, 9, "Unit Price (LKR)", border=1, align="R", fill=True)
    pdf.cell(35, 9, "Line Total (LKR)", border=1, align="R", fill=True)
    pdf.ln(9)

    # --- Items Table Rows ---
    pdf.set_font("Helvetica", "", 10)
    for idx, item in enumerate(sale_data["items"], start=1):
        line_total = item["qty"] * item["sell_price"]
        pdf.cell(15, 8, str(idx), border=1, align="C")
        pdf.cell(85, 8, str(item["name"])[:42], border=1, align="L")
        pdf.cell(20, 8, str(item["qty"]), border=1, align="C")
        pdf.cell(35, 8, f"{item['sell_price']:,.2f}", border=1, align="R")
        pdf.cell(35, 8, f"{line_total:,.2f}", border=1, align="R")
        pdf.ln(8)

    pdf.ln(6)
    summary_start_y = pdf.get_y()

    # --- QR Code Generation (Left Side of Summary) ---
    qr_payload = (
        f"NexaPOS Verified Receipt\n"
        f"Invoice: {sale_data['invoice_no']}\n"
        f"Customer: {sale_data['customer_name']}\n"
        f"Total: LKR {sale_data['total']:,.2f}\n"
        f"Date: {sale_data['sale_date']}"
    )
    qr_img = qrcode.make(qr_payload)
    qr_temp_path = os.path.join(INVOICE_DIR, f"qr_{sale_data['invoice_no']}.png")
    qr_img.save(qr_temp_path)

    pdf.image(qr_temp_path, x=12, y=summary_start_y, w=32)
    pdf.set_xy(12, summary_start_y + 33)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(32, 4, "Scan to Verify", align="C")

    # --- Totals Summary Box (Right Side) ---
    pdf.set_text_color(30, 30, 30)
    pdf.set_y(summary_start_y)

    def add_summary_row(label, value, bold=False, highlight=False):
        pdf.set_x(120)
        pdf.set_font("Helvetica", "B" if bold else "", 11 if bold else 10)
        if highlight:
            pdf.set_fill_color(20, 33, 61)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(40, 9, label, border=1, align="L", fill=True)
            pdf.cell(40, 9, value, border=1, align="R", fill=True)
            pdf.set_text_color(30, 30, 30)
            pdf.ln(9)
        else:
            pdf.cell(40, 7, label, border=0, align="L")
            pdf.cell(40, 7, value, border=0, align="R")
            pdf.ln(7)

    add_summary_row("Subtotal:", f"LKR {sale_data['subtotal']:,.2f}")
    add_summary_row("Discount:", f"- LKR {sale_data['discount']:,.2f}")
    add_summary_row("Tax:", f"+ LKR {sale_data['tax']:,.2f}")
    add_summary_row("GRAND TOTAL:", f"LKR {sale_data['total']:,.2f}", bold=True, highlight=True)

    # --- Footer ---
    pdf.set_y(-28)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "Thank you for your business! Powered by NexaPOS Pro.", align="C")
    pdf.ln(5)
    pdf.cell(0, 6, "Goods sold are exchangeable within 7 days with original receipt.", align="C")

    filename = f"{sale_data['invoice_no']}.pdf"
    filepath = os.path.join(INVOICE_DIR, filename)
    pdf.output(filepath)

    # Temp QR image delete කිරීම
    if os.path.exists(qr_temp_path):
        os.remove(qr_temp_path)

    open_file_automatically(filepath)
    return filepath


def export_sales_to_excel(sales_list):
    if not sales_list:
        return None
    df = pd.DataFrame(sales_list)
    df.rename(columns={
        "id": "ID", "invoice_no": "Invoice No", "customer_name": "Customer",
        "subtotal": "Subtotal (LKR)", "discount": "Discount (LKR)", "tax": "Tax (LKR)",
        "total": "Grand Total (LKR)", "profit": "Net Profit (LKR)",
        "payment_method": "Payment Method", "sale_date": "Date & Time"
    }, inplace=True)
    filepath = os.path.join(REPORT_DIR, f"Sales_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    df.to_excel(filepath, index=False, engine="openpyxl")
    open_file_automatically(filepath)
    return filepath


def export_inventory_to_excel(products_list):
    if not products_list:
        return None
    df = pd.DataFrame(products_list)
    df["Stock Status"] = df.apply(lambda r: "LOW STOCK" if r["stock"] <= r["min_stock"] else "IN STOCK", axis=1)
    df["Stock Value (LKR)"] = df["stock"] * df["cost_price"]
    filepath = os.path.join(REPORT_DIR, f"Inventory_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    df.to_excel(filepath, index=False, engine="openpyxl")
    open_file_automatically(filepath)
    return filepath
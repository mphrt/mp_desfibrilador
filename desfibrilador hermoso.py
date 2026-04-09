import streamlit as st
from fpdf import FPDF
import datetime
import io
import tempfile
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image

# ========= Configuración y Constantes =========
FOOTER_LINES = [
    "PAUTA MANTENIMIENTO PREVENTIVO MONITOR/DESFIBRILADOR (Ver 2)",
    "UNIDAD DE INGENIERÍA CLÍNICA",
    "HOSPITAL REGIONAL DE TALCA",
]

MARCAS_BASE = ["", "NIHON KOHDEN", "ZOLL MEDICAL", "ADVANCED", "MINDRAY"]
MODELOS_BASE = [
    "", "TEC5521K", "M-SERIES", "PD-1400", "D-1000", "TEC7631G", 
    "CARDIOLIFE", "BENEHEART D3", "TEC-5531E", "CU-HD1", 
    "TEC-5631E", "TEC3521K", "R-SERIES", "C1A"
]

# ========= Clase PDF =========
class PDF(FPDF):
    def __init__(self, *args, footer_lines=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._footer_lines = footer_lines or []

    def footer(self):
        if not self._footer_lines:
            return
        self.set_y(-15)
        # Usamos helvetica que es el estándar compatible
        self.set_font("helvetica", "B", 6)
        self.cell(0, 4, self._footer_lines[0], ln=1, align="L")
        self.set_font("helvetica", "", 6)
        for line in self._footer_lines[1:]:
            self.cell(0, 3, line, ln=1, align="L")

# ========= Utilidades de Procesamiento (Sin cambios mayores) =========
def _crop_signature(canvas_result):
    if canvas_result.image_data is None:
        return None
    img_array = canvas_result.image_data.astype(np.uint8)
    img = Image.fromarray(img_array)
    gray_img = img.convert('L')
    threshold = 230
    coords = np.argwhere(np.array(gray_img) < threshold)
    if coords.size == 0:
        return None
    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)
    cropped_img = img.crop((min_x, min_y, max_x + 1, max_y + 1))
    if cropped_img.mode == 'RGBA':
        cropped_img = cropped_img.convert('RGB')
    img_byte_arr = io.BytesIO()
    cropped_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def add_signature_to_pdf(pdf_obj, canvas_result, x, y, w=40, h=15):
    img_buf = _crop_signature(canvas_result)
    if img_buf:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(img_buf.read())
            pdf_obj.image(tmp.name, x=x, y=y, w=w, h=h)

# ========= Funciones de Dibujo PDF =========
def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w):
    row_h = 4
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("helvetica", "B", 7)
    pdf.cell(item_w, row_h, section_title, border=1, fill=True)
    pdf.cell(col_w, row_h, "OK", border=1, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    
    pdf.set_font("helvetica", "", 6.5)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(item_w, row_h, item, border=1)
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, align="C", ln=1)

def checklist(title, items):
    st.subheader(title)
    respuestas = []
    for item in items:
        col1, col2 = st.columns([5, 3])
        with col1: st.write(item)
        with col2:
            seleccion = st.radio("Estado", ["OK", "NO", "N/A"], horizontal=True, key=f"check_{item}", label_visibility="collapsed")
        respuestas.append((item, seleccion))
    return respuestas

# ========= App Principal =========
def main():
    st.title("Pauta de Mantenimiento - Monitor/Desfibrilador")

    with st.expander("Datos del Equipo", expanded=True):
        col1, col2 = st.columns(2)
        ideq = col1.text_input("IDEQ")
        sn = col2.text_input("Número de Serie")
        
        marca_sel = col1.selectbox("Marca", MARCAS_BASE + ["+ Añadir nueva marca..."])
        marca = st.text_input("Nueva Marca") if marca_sel == "+ Añadir nueva marca..." else marca_sel
        
        modelo_sel = col2.selectbox("Modelo", MODELOS_BASE + ["+ Añadir nuevo modelo..."])
        modelo = st.text_input("Nuevo Modelo") if modelo_sel == "+ Añadir nuevo modelo..." else modelo_sel

    chequeo_visual = checklist("1. Inspección y limpieza", ["1.1. Inspección general", "1.2. Limpieza de contactos", "1.4. Revisión accesorios"])
    
    st.subheader("Firmas")
    c1, c2 = st.columns(2)
    with c1:
        st.write("Firma Técnico")
        canvas_tec = st_canvas(stroke_width=2, height=100, width=200, key="c_tec")
    with c2:
        st.write("Firma Clínica")
        canvas_cli = st_canvas(stroke_width=2, height=100, width=200, key="c_cli")

    if st.button("Generar PDF"):
        pdf = PDF('P', 'mm', 'A4', footer_lines=FOOTER_LINES)
        pdf.add_page()
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "INFORME DE MANTENIMIENTO", ln=1, align="C")
        
        pdf.set_font("helvetica", "", 9)
        pdf.cell(0, 7, f"IDEQ: {ideq} | Marca: {marca} | Modelo: {modelo} | S/N: {sn}", ln=1)
        pdf.ln(5)
        
        # Dibujar tablas
        create_checkbox_table(pdf, "1. INSPECCIÓN", chequeo_visual, 10, 140, 15)
        
        # Dibujar Firmas
        y_firma = pdf.get_y() + 20
        add_signature_to_pdf(pdf, canvas_tec, 20, y_firma)
        add_signature_to_pdf(pdf, canvas_cli, 110, y_firma)
        
        # Generar descarga
        pdf_output = pdf.output()
        st.download_button(
            label="Descargar PDF",
            data=pdf_output,
            file_name=f"MP_{ideq}.pdf",
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()

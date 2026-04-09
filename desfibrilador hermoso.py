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

# Listas base (Ordenadas alfabéticamente)
MARCAS_BASE = sorted(["NIHON KOHDEN", "ZOLL MEDICAL", "ADVANCED", "MINDRAY"])
MODELOS_BASE = sorted([
    "TEC5521K", "M-SERIES", "PD-1400", "D-1000", "TEC7631G", 
    "CARDIOLIFE", "BENEHEART D3", "TEC-5531E", "CU-HD1", 
    "TEC-5631E", "TEC3521K", "R-SERIES", "C1A"
])

# ========= Clase PDF =========
class PDF(FPDF):
    def __init__(self, *args, footer_lines=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._footer_lines = footer_lines or []

    def footer(self):
        if not self._footer_lines:
            return
        self.set_y(-15)
        subtitle_fs = 6.2
        line_h = 3.4
        self.set_font("Arial", "B", subtitle_fs)
        first_line = self._footer_lines[0]
        text_w = self.get_string_width(first_line)
        self.line(self.l_margin, self.get_y(), self.l_margin + text_w, self.get_y())
        self.ln(1.6)
        self.cell(0, line_h, first_line, ln=1, align="L")
        self.set_font("Arial", "", subtitle_fs)
        for line in self._footer_lines[1:]:
            self.cell(0, line_h, line, ln=1, align="L")

# ========= Utilidades de Procesamiento =========
def _crop_signature(canvas_result):
    if canvas_result.image_data is None:
        return None
    img_array = canvas_result.image_data.astype(np.uint8)
    img = Image.fromarray(img_array)
    gray_img = img.convert('L')
    coords = np.argwhere(np.array(gray_img) < 230)
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
    img_data = _crop_signature(canvas_result)
    if img_data:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(img_data.read())
            pdf_obj.image(tmp.name, x=x, y=y, w=w, h=h)

def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w):
    row_h = 4
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 7)
    pdf.set_x(x_pos)
    pdf.cell(item_w, row_h, section_title, border=1, fill=True)
    for h in ["OK", "NO", "N/A"]:
        pdf.cell(col_w, row_h, h, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 6.5)
    for item, val in items:
        pdf.set_x(x_pos)
        pdf.cell(item_w, row_h, item, border=1)
        for h in ["OK", "NO", "N/A"]:
            mark = "X" if val == h else ""
            pdf.cell(col_w, row_h, mark, border=1, align="C")
        pdf.ln()

def checklist(title, items):
    st.subheader(title)
    respuestas = []
    for item in items:
        col1, col2 = st.columns([5, 3])
        with col1: st.write(item)
        with col2: sel = st.radio("Acción", ["OK", "NO", "N/A"], horizontal=True, key=item, label_visibility="collapsed")
        respuestas.append((item, sel))
    return respuestas

# ========= App Principal =========
def main():
    st.title("Pauta de Mantenimiento Preventivo")

    # Datos
    ideq = st.text_input("IDEQ")
    m_list = [""] + MARCAS_BASE + ["+ Añadir nueva marca..."]
    marca_sel = st.selectbox("Marca", m_list)
    marca = st.text_input("Escribe la marca") if marca_sel == "+ Añadir nueva marca..." else marca_sel
    
    mod_list = [""] + MODELOS_BASE + ["+ Añadir nuevo modelo..."]
    modelo_sel = st.selectbox("Modelo", mod_list)
    modelo = st.text_input("Escribe el modelo") if modelo_sel == "+ Añadir nuevo modelo..." else modelo_sel
    
    sn = st.text_input("Número de Serie")
    fecha = st.date_input("Fecha", value=datetime.date.today())

    # Checklists
    c1 = checklist("1. Inspección y limpieza", ["1.1 Inspección general", "1.2 Limpieza contactos", "1.3 Limpieza cabezal"])
    c2 = checklist("2. Seguridad eléctrica", ["2.1 Corrientes fuga normal", "2.2 Neutro abierto"])

    # Firmas
    st.subheader("Firmas")
    col_t, col_i = st.columns(2)
    with col_t:
        st.write("Técnico:")
        can_t = st_canvas(stroke_width=2, stroke_color="#000", background_color="#EEE", height=100, width=200, key="ct")
    with col_i:
        st.write("Ingeniería:")
        can_i = st_canvas(stroke_width=2, stroke_color="#000", background_color="#EEE", height=100, width=200, key="ci")

    if st.button("Generar PDF"):
        pdf = PDF('P', 'mm', 'A4', footer_lines=FOOTER_LINES)
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "INFORME DE MANTENIMIENTO", ln=1, align="C")
        
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 7, f"IDEQ: {ideq} | MARCA: {marca} | MODELO: {modelo}", ln=1)
        pdf.cell(0, 7, f"S/N: {sn} | FECHA: {fecha}", ln=1)
        pdf.ln(5)

        # Tablas
        create_checkbox_table(pdf, "1. Inspección", c1, 10, 80, 15)
        pdf.ln(5)
        create_checkbox_table(pdf, "2. Seguridad", c2, 10, 80, 15)
        
        # Dibujar firmas
        curr_y = pdf.get_y() + 10
        pdf.text(10, curr_y, "Firma Técnico:")
        pdf.text(110, curr_y, "Firma Ingeniería:")
        add_signature_to_pdf(pdf, can_t, 10, curr_y + 2)
        add_signature_to_pdf(pdf, can_i, 110, curr_y + 2)

        # Output
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        st.download_button("Descargar PDF", pdf_bytes, file_name=f"MP_{ideq}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()

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

# Listas base ordenadas alfabéticamente
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
        y = self.get_y()
        subtitle_fs = 6.2
        line_h = 3.4
        first_line = self._footer_lines[0]
        self.set_font("Arial", "B", subtitle_fs)
        text_w = self.get_string_width(first_line)
        x_left = self.l_margin
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.2)
        self.line(x_left, y, x_left + text_w, y)
        self.ln(1.6)
        self.set_x(self.l_margin)
        self.cell(0, line_h, first_line, ln=1, align="L")
        self.set_font("Arial", "", subtitle_fs)
        for line in self._footer_lines[1:]:
            self.set_x(self.l_margin)
            self.cell(0, line_h, line, ln=1, align="L")

# ========= Utilidades de Procesamiento =========
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

def add_signature_inline(pdf_obj, canvas_result, x, y, w_mm=60, h_mm=15):
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w = w_mm
        img_h = (img.height / img.width) * img_w
        if img_h > h_mm:
            img_h = h_mm
            img_w = (img.width / img.height) * img_h
        pdf_obj.image(tmp_path, x=x, y=y, w=img_w, h=img_h)
    except Exception:
        pass

# ========= Funciones de Dibujo PDF =========
def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w, row_h=3.4):
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 7.2)
    pdf.cell(item_w, row_h, f"  {section_title}", border=1, ln=0, fill=True)
    pdf.cell(col_w, row_h, "OK", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", 6.2)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(item_w, row_h, f"   {item}", border=1, ln=0)
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, ln=1, align="C")
    pdf.ln(1.5)

def checklist_ui(title, items):
    st.subheader(title)
    respuestas = []
    for item in items:
        col1, col2 = st.columns([5, 3])
        with col1: st.write(item)
        with col2: sel = st.radio("Respuesta", ["OK", "NO", "N/A"], horizontal=True, key=item, label_visibility="collapsed")
        respuestas.append((item, sel))
    return respuestas

# ========= App Principal =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Monitor/Desfibrilador")

    # --- DATOS DEL EQUIPO (ORDEN ANTIGUO) ---
    col_a, col_b = st.columns(2)
    with col_a:
        ideq = st.text_input("IDEQ")
        
        m_list = [""] + MARCAS_BASE + ["+ Añadir nueva marca..."]
        marca_sel = st.selectbox("Marca", m_list)
        marca = st.text_input("Escribe el nombre de la nueva marca") if marca_sel == "+ Añadir nueva marca..." else marca_sel

        mod_list = [""] + MODELOS_BASE + ["+ Añadir nuevo modelo..."]
        modelo_sel = st.selectbox("Modelo", mod_list)
        modelo = st.text_input("Escribe el nombre del nuevo modelo") if modelo_sel == "+ Añadir nuevo modelo..." else modelo_sel

    with col_b:
        sn = st.text_input("Número de Serie")
        inventario = st.text_input("Número de Inventario")
        fecha = st.date_input("Fecha", value=datetime.date.today())
        ubicacion = st.text_input("Ubicación")

    # --- LISTAS DE CHEQUEO ---
    c1 = checklist_ui("1. Inspección y limpieza", ["1.1. Inspección general", "1.2. Limpieza de contactos", "1.3. Limpieza cabezal termo-inscriptor", "1.4. Revisión accesorios", "1.5. Revisión panel", "1.6. Conexiones eléctricas"])
    c2 = checklist_ui("2. Seguridad eléctrica", ["2.1. Medición corrientes fuga normal", "2.2. Medición corrientes fuga neutro abierto"])
    c3 = checklist_ui("3. Accesorios del equipo", ["3.1. Cable de poder", "3.2. Cable paciente", "3.3. Cable de interfaz", "3.4. Cable tierra", "3.5. Palas desfibriladoras"])

    # --- OBSERVACIONES Y OPERATIVIDAD ---
    st.subheader("Finalización")
    obs = st.text_area("Observaciones")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"], horizontal=True)
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    # --- FIRMAS ---
    st.subheader("Firmas")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.write("Firma Técnico Encargado:")
        canvas_t = st_canvas(stroke_width=2, stroke_color="#000", background_color="#EEE", height=120, width=300, key="c_tec")
    with col_f2:
        st.write("Firma Ingeniería Clínica / Personal:")
        canvas_i = st_canvas(stroke_width=2, stroke_color="#000", background_color="#EEE", height=120, width=300, key="c_ing")

    # --- GENERACIÓN PDF ---
    if st.button("Generar PDF"):
        pdf = PDF('L', 'mm', 'A4', footer_lines=FOOTER_LINES)
        pdf.set_margins(10, 10, 10)
        pdf.add_page()
        
        # Encabezado
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "PAUTA DE MANTENIMIENTO PREVENTIVO - MONITOR/DESFIBRILADOR", ln=1, align="C")
        pdf.ln(2)

        # Bloque de Datos (Dos columnas en el PDF)
        pdf.set_font("Arial", "B", 8)
        # Columna 1
        pdf.text(10, 25, f"IDEQ: {ideq}")
        pdf.text(10, 30, f"MARCA: {marca}")
        pdf.text(10, 35, f"MODELO: {modelo}")
        # Columna 2
        pdf.text(110, 25, f"N° SERIE: {sn}")
        pdf.text(110, 30, f"FECHA: {fecha}")
        pdf.text(110, 35, f"UBICACIÓN: {ubicacion}")
        pdf.ln(18)

        # Tablas (Lado izquierdo)
        col_width_items = 80
        col_width_chk = 12
        
        create_checkbox_table(pdf, "1. INSPECCIÓN Y LIMPIEZA", c1, 10, col_width_items, col_width_chk)
        create_checkbox_table(pdf, "2. SEGURIDAD ELÉCTRICA", c2, 10, col_width_items, col_width_chk)
        create_checkbox_table(pdf, "3. ACCESORIOS DEL EQUIPO", c3, 10, col_width_items, col_width_chk)

        # Observaciones y Firmas (Lado derecho / abajo)
        pdf.set_xy(130, 45)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "OBSERVACIONES:", ln=1)
        pdf.set_x(130)
        pdf.set_font("Arial", "", 8)
        pdf.multi_cell(0, 4, obs if obs else "Sin observaciones.")
        
        pdf.ln(5)
        pdf.set_x(130)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, f"EQUIPO OPERATIVO: {operativo}", ln=1)
        pdf.set_x(130)
        pdf.cell(0, 5, f"TÉCNICO: {tecnico}", ln=1)
        pdf.set_x(130)
        pdf.cell(0, 5, f"EMPRESA: {empresa}", ln=1)

        # Espacio para firmas
        y_firma = pdf.get_y() + 5
        pdf.text(130, y_firma, "Firma Técnico:")
        add_signature_inline(pdf, canvas_t, 130, y_firma + 2, 50, 20)
        
        pdf.text(210, y_firma, "Firma Receptor:")
        add_signature_inline(pdf, canvas_i, 210, y_firma + 2, 50, 20)

        # Salida
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        st.download_button("Descargar Reporte PDF", pdf_bytes, file_name=f"MP_{sn}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()

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

# Listas base (se ordenan alfabéticamente, manteniendo el espacio vacío al inicio)
MARCAS_BASE = sorted(["NIHON KOHDEN", "ZOLL MEDICAL", "ADVANCED", "MINDRAY"])
MARCAS_MENU = [""] + MARCAS_BASE + ["+ Añadir nueva marca..."]

MODELOS_BASE = sorted([
    "TEC5521K", "M-SERIES", "PD-1400", "D-1000", "TEC7631G", 
    "CARDIOLIFE", "BENEHEART D3", "TEC-5531E", "CU-HD1", 
    "TEC-5631E", "TEC3521K", "R-SERIES", "C1A"
])
MODELOS_MENU = [""] + MODELOS_BASE + ["+ Añadir nuevo modelo..."]

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

# ========= Utilidades (Firma y Dibujo) =========
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

def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w):
    row_h = 3.4
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 7.2)
    pdf.cell(item_w, row_h, f"    {section_title}", border=1, ln=0, fill=True)
    pdf.cell(col_w, row_h, "OK", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", 6.2)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(item_w, row_h, f"     {item}", border=0, ln=0)
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, ln=1, align="C")
    pdf.ln(1.6)

# ========= App Principal =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Monitor/Desfibrilador")

    # --- DATOS DEL EQUIPO ---
    col1, col2 = st.columns(2)
    with col1:
        ideq = st.text_input("IDEQ")
        
        # Selección de Marca (Alfabética)
        marca_sel = st.selectbox("Marca", MARCAS_MENU, index=0)
        if marca_sel == "+ Añadir nueva marca...":
            marca = st.text_input("Escribe el nombre de la nueva marca", key="input_marca_custom")
        else:
            marca = marca_sel

        # Selección de Modelo (Alfabética)
        modelo_sel = st.selectbox("Modelo", MODELOS_MENU, index=0)
        if modelo_sel == "+ Añadir nuevo modelo...":
            modelo = st.text_input("Escribe el nombre del nuevo modelo", key="input_modelo_custom")
        else:
            modelo = modelo_sel

    with col2:
        sn = st.text_input("Número de Serie")
        inventario = st.text_input("Número de Inventario")
        fecha = st.date_input("Fecha", value=datetime.date.today())
        ubicacion = st.text_input("Ubicación")

    # --- SECCIONES DE CHEQUEO ---
    def checklist_ui(title, items):
        st.subheader(title)
        res = []
        for i in items:
            c1, c2 = st.columns([5, 3])
            val = c2.radio("", ["OK", "NO", "N/A"], horizontal=True, key=i)
            c1.write(i)
            res.append((i, val))
        return res

    inspeccion = checklist_ui("1. Inspección y limpieza", ["1.1. Inspección general", "1.2. Limpieza de contactos", "1.3. Limpieza de cabezal termo-inscriptor", "1.4. Revisión de accesorios", "1.5. Revisión del panel", "1.6. Conexiones eléctricas"])
    seguridad = checklist_ui("2. Seguridad eléctrica", ["2.1. Corrientes de fuga (Normal)", "2.2. Corrientes de fuga (Neutro Abierto)"])
    accesorios = checklist_ui("3. Accesorios", ["3.1. Cable de poder", "3.2. Cable paciente", "3.3. Cable interfaz", "3.4. Cable tierra", "3.5. Palas desfibriladoras"])

    # --- FIRMAS ---
    st.subheader("Firmas de Conformidad")
    c_firm1, c_firm2 = st.columns(2)
    with c_firm1:
        st.write("Firma Técnico:")
        canvas_tecnico = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=100, width=300, key="canvas_t")
    with c_firm2:
        tecnico_nombre = st.text_input("Nombre del Técnico")
        empresa = st.text_input("Empresa")

    # --- GENERAR PDF ---
    if st.button("Generar y Descargar Reporte PDF"):
        pdf = PDF('L', 'mm', 'A4', footer_lines=FOOTER_LINES)
        pdf.set_margins(10, 10, 10)
        pdf.add_page()
        
        # Cabecera Simple
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "REPORTE DE MANTENIMIENTO PREVENTIVO", ln=1, align="C")
        
        # Datos Equipo
        pdf.set_font("Arial", "", 8)
        pdf.cell(0, 5, f"IDEQ: {ideq} | MARCA: {marca} | MODELO: {modelo} | S/N: {sn}", ln=1)
        pdf.cell(0, 5, f"UBICACIÓN: {ubicacion} | FECHA: {fecha}", ln=1)
        pdf.ln(5)

        # Tablas
        create_checkbox_table(pdf, "INSPECCIÓN Y LIMPIEZA", inspeccion, 10, 80, 15)
        create_checkbox_table(pdf, "SEGURIDAD ELÉCTRICA", seguridad, 10, 80, 15)
        create_checkbox_table(pdf, "ACCESORIOS", accesorios, 10, 80, 15)

        # Firma en el PDF
        pdf.ln(10)
        pdf.cell(0, 5, f"Técnico Responsable: {tecnico_nombre}", ln=1)
        pdf.cell(0, 5, f"Empresa: {empresa}", ln=1)
        y_firma = pdf.get_y()
        add_signature_inline(pdf, canvas_tecnico, 10, y_firma + 2, 50, 20)

        # Descarga
        out = pdf.output(dest="S")
        if isinstance(out, str): out = out.encode("latin1")
        st.download_button("Click aquí para descargar", out, file_name=f"MP_{ideq}_{sn}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()

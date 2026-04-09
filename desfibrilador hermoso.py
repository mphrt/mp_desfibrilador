import streamlit as st
from fpdf import FPDF
import datetime
import io
import tempfile
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image

# ========= Pie de página =========
FOOTER_LINES = [
    "PAUTA MANTENIMIENTO PREVENTIVO MONITOR/DESFIBRILADOR (Ver 2)",
    "UNIDAD DE INGENIERÍA CLÍNICA",
    "HOSPITAL REGIONAL DE TALCA",
]

# ========= Configuración de Marcas y Modelos =========
MARCAS_BASE = ["", "NIHON KOHDEN", "ZOLL MEDICAL", "ADVANCED", "MINDRAY"]
MODELOS_BASE = [
    "", "TEC5521K", "M-SERIES", "PD-1400", "D-1000", "TEC7631G", 
    "CARDIOLIFE", "BENEHEART D3", "TEC-5531E", "CU-HD1", 
    "TEC-5631E", "TEC3521K", "R-SERIES", "C1A"
]

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

# ========= Utilidades =========
def _crop_signature(canvas_result):
    if canvas_result.image_data is None:
        return None
    img_array = canvas_result.image_data.astype(np.uint8)
    img = Image.fromarray(img_array)
    gray_img = img.convert("L")
    threshold = 230
    coords = np.argwhere(np.array(gray_img) < threshold)
    if coords.size == 0:
        return None
    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)
    cropped_img = img.crop((min_x, min_y, max_x + 1, max_y + 1))
    if cropped_img.mode == "RGBA":
        cropped_img = cropped_img.convert("RGB")
    img_byte_arr = io.BytesIO()
    cropped_img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr

def add_signature_inline(pdf_obj, canvas_result, x_target_center, y, max_w=65, max_h=20, centered=True):
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w, img_h = img.size
        ratio = min(max_w / img_w, max_h / img_h)
        final_w = img_w * ratio
        final_h = img_h * ratio
        x_pos = x_target_center - (final_w / 2) if centered else x_target_center
        pdf_obj.image(tmp_path, x=x_pos, y=y, w=final_w, h=final_h)
    except Exception:
        pass

def draw_si_no_boxes(pdf, x, y, selected, size=4.5, gap=4, text_gap=1.5, label_w=36):
    pdf.set_font("Arial", "", 7.5)
    pdf.set_xy(x, y)
    pdf.cell(label_w, size, "EQUIPO OPERATIVO:", 0, 0)
    x_box_si = x + label_w + 2
    pdf.rect(x_box_si, y, size, size)
    pdf.set_xy(x_box_si, y); pdf.cell(size, size, "X" if selected == "SI" else "", 0, 0, "C")
    pdf.set_xy(x_box_si + size + text_gap, y); pdf.cell(6, size, "SI", 0, 0)
    x_box_no = x_box_si + size + text_gap + 6 + gap
    pdf.rect(x_box_no, y, size, size)
    pdf.set_xy(x_box_no, y); pdf.cell(size, size, "X" if selected == "NO" else "", 0, 0, "C")
    pdf.set_xy(x_box_no + size + text_gap, y); pdf.cell(6, size, "NO", 0, 1)

def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w, row_h=3.4, head_fs=7.2, cell_fs=6.2, indent_w=5.0, title_tab_spaces=2):
    title_prefix = " " * (title_tab_spaces * 2)
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230); pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", head_fs)
    pdf.cell(item_w, row_h, f"{title_prefix}{section_title}", border=1, ln=0, align="L", fill=True)
    pdf.set_font("Arial", "B", cell_fs)
    pdf.cell(col_w, row_h, "OK", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", cell_fs)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(indent_w, row_h, "", border=0, ln=0)
        pdf.cell(max(1, item_w - indent_w), row_h, item, border=0, ln=0, align="L")
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, ln=1, align="C")
    pdf.ln(1.6)

def create_power_table(pdf, x_pos, items, row_h=3.4, head_fs=7.2, cell_fs=6.2):
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", head_fs)
    headers = ["PRUEBA", "RITMO", "AMPL", "LOAD", "E. SET", "E. RESULT (J)"]
    widths = [15, 15, 15, 15, 20, 25] 
    for i, header in enumerate(headers):
        pdf.cell(widths[i], row_h, header, border=1, align="C", fill=True)
    pdf.ln(row_h)
    pdf.set_font("Arial", "", cell_fs)
    for i, item in enumerate(items):
        pdf.set_x(x_pos)
        values = [str(i + 1), "80BPM", "1.0mV", "50ohm", item[0], item[1]]
        for j, val in enumerate(values):
            pdf.cell(widths[j], row_h, val, border=1, align="C")
        pdf.ln(row_h)
    pdf.ln(2)

def draw_boxed_text_auto(pdf, x, y, w, min_h, title, text, head_h=4.6, fs_head=7.2, fs_body=7.0, body_line_h=3.2, padding=1.2):
    pdf.set_xy(x, y)
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", fs_head)
    pdf.cell(w, head_h, title, border=1, ln=1, align="L", fill=True)
    y_body = pdf.get_y()
    pdf.set_font("Arial", "", fs_body)
    pdf.set_xy(x + padding, y_body + padding)
    if text:
        pdf.multi_cell(w - 2*padding, body_line_h, text, border=0, align="L")
    end_y = pdf.get_y()
    content_h = max(min_h, (end_y - y_body) + padding)
    pdf.rect(x, y_body, w, content_h)
    pdf.set_y(y_body + content_h)

def draw_analisis_columns(pdf, x_start, y_start, col_w, data_list):
    row_h_field = 3.4
    label_w = 28.0
    text_w = col_w - label_w - 3.0
    TAB = "  " * 2
    def draw_column_no_lines(x, y, data):
        yy = y
        for lbl, key in [("EQUIPO", "equipo"), ("MARCA", "marca"), ("MODELO", "modelo"), ("NÚMERO SERIE", "serie")]:
            pdf.set_xy(x, yy); pdf.set_font("Arial", "", 6.2)
            pdf.cell(label_w, row_h_field, f"{TAB}{lbl}", 0, 0)
            pdf.set_xy(x + label_w + 2, yy)
            pdf.cell(text_w, row_h_field, f": {data.get(key, '')}", 0, 1)
            yy += row_h_field
        return yy
    
    y_current = y_start
    if len(data_list) > 0:
        y_left = draw_column_no_lines(x_start, y_current, data_list[0])
        if len(data_list) > 1:
            col_w2 = (col_w - 6) / 2.0
            draw_column_no_lines(x_start + col_w2 + 6, y_current, data_list[1])
        y_current = pdf.get_y() + 2
    return y_current

def checklist_ui(title, items):
    st.subheader(title)
    respuestas = []
    for item in items:
        col1, col2 = st.columns([5, 3])
        with col1: st.markdown(item)
        with col2: seleccion = st.radio("", ["OK", "NO", "N/A"], horizontal=True, key=item)
        respuestas.append((item, seleccion))
    return respuestas

# ========= App Principal =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Monitor/Desfibrilador")

    # --- DATOS DEL EQUIPO ---
    ideq = st.text_input("IDEQ")
    col1, col2 = st.columns(2)
    with col1:
        marca_sel = st.selectbox("Marca", MARCAS_BASE + ["+ Añadir nueva marca..."])
        marca = st.text_input("Nueva Marca") if marca_sel == "+ Añadir nueva marca..." else marca_sel
    with col2:
        modelo_sel = st.selectbox("Modelo", MODELOS_BASE + ["+ Añadir nuevo modelo..."])
        modelo = st.text_input("Nuevo Modelo") if modelo_sel == "+ Añadir nuevo modelo..." else modelo_sel

    sn = st.text_input("Número de Serie")
    inventario = st.text_input("Número de Inventario")
    fecha = st.date_input("Fecha", value=datetime.date.today())
    ubicacion = st.text_input("Ubicación")

    chequeo_visual = checklist_ui("1. Inspección y limpieza", ["1.1. Inspección general", "1.2. Limpieza de contactos", "1.3. Limpieza de cabezal termo-inscriptor", "1.4. Revisión del estado de los accesorios", "1.5. Revisión del panel", "1.6. Revisión del conexiones eléctricas"])
    seguridad_electrica = checklist_ui("2. Seguridad eléctrica", ["2.1. Medición de corrientes de fuga normal condición", "2.2. Medición de corrientes de fuga con neutro abierto"])
    accesorios_equipo = checklist_ui("3. Accesorios del equipo", ["3.1. Cable de poder", "3.2. Cable paciente", "3.3. Cable de interfaz", "3.4. Cable de tierra fuente de poder", "3.5. Palas desfibriladoras"])

    st.subheader("4. Medición de potencias")
    potencias_valores = []
    energia_set = [5, 15, 20, 50, 75, 100, 200]
    cols_p = st.columns(len(energia_set))
    for i, energia in enumerate(energia_set):
        with cols_p[i]:
            val = st.text_input(f"{energia}J", key=f"pot_{i}")
            potencias_valores.append((f"{energia} J", val))

    st.subheader("5. Instrumentos de análisis")
    if 'analisis_equipos' not in st.session_state: st.session_state.analisis_equipos = [{}, {}]
    for i in range(len(st.session_state.analisis_equipos)):
        st.markdown(f"**Equipo {i+1}**")
        st.session_state.analisis_equipos[i]['equipo'] = st.text_input("EQUIPO", key=f"eq_{i}")
        st.session_state.analisis_equipos[i]['marca'] = st.text_input("MARCA", key=f"ma_{i}")
        st.session_state.analisis_equipos[i]['modelo'] = st.text_input("MODELO", key=f"mo_{i}")
        st.session_state.analisis_equipos[i]['serie'] = st.text_input("NÚMERO SERIE", key=f"se_{i}")

    observaciones = st.text_area("Observaciones")
    observaciones_interno = st.text_area("Observaciones (uso interno)")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    col_t, col_i, col_c = st.columns(3)
    with col_t: canvas_tecnico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=100, width=200, key="c_t")
    with col_i: canvas_ingenieria = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=100, width=200, key="c_i")
    with col_c: canvas_clinico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=100, width=200, key="c_c")

    if st.button("Generar PDF"):
        SIDE_MARGIN, TOP_MARGIN = 9, 4
        pdf = PDF('L', 'mm', 'A4', footer_lines=FOOTER_LINES)
        pdf.set_margins(SIDE_MARGIN, TOP_MARGIN, SIDE_MARGIN)
        pdf.add_page()
        
        page_w = pdf.w
        usable_w = page_w - 2 * SIDE_MARGIN
        col_w = (usable_w - 6) / 2.0
        SECOND_COL_L = SIDE_MARGIN + col_w + 6

        # Encabezado
        try: pdf.image("logo_hrt_final.jpg", x=2, y=2, w=50)
        except: pass
        
        pdf.set_font("Arial", "B", 8)
        id_txt = f"IDEQ: {ideq}"
        pdf.set_xy(page_w - SIDE_MARGIN - 40, 4)
        pdf.cell(40, 5, id_txt, 1, 1, "C", fill=True)
        
        pdf.set_xy(60, 15)
        pdf.cell(col_w, 6, "PAUTA MANTENCIÓN MONITOR/DESFIBRILADOR", 1, 1, "C", fill=True)

        # Columna Izquierda
        pdf.set_y(30)
        pdf.set_font("Arial", "B", 7.5)
        pdf.cell(30, 4, f"FECHA: {fecha.strftime('%d/%m/%Y')}", 0, 1)
        
        def quick_field(l, v):
            pdf.set_font("Arial", "", 7.5)
            pdf.cell(35, 3.8, l, 0, 0)
            pdf.cell(5, 3.8, ":", 0, 0)
            pdf.cell(0, 3.8, str(v), 0, 1)

        quick_field("MARCA", marca)
        quick_field("MODELO", modelo)
        quick_field("NÚMERO SERIE", sn)
        quick_field("N/INVENTARIO", inventario)
        quick_field("UBICACIÓN", ubicacion)
        
        pdf.ln(2)
        ITEM_W = col_w - 36
        create_checkbox_table(pdf, "1. Inspección y limpieza", chequeo_visual, SIDE_MARGIN, ITEM_W, 12)
        create_checkbox_table(pdf, "2. Seguridad eléctrica", seguridad_electrica, SIDE_MARGIN, ITEM_W, 12)
        create_checkbox_table(pdf, "3. Accesorios", accesorios_equipo, SIDE_MARGIN, ITEM_W, 12)
        
        pdf.set_fill_color(230,230,230); pdf.set_font("Arial", "B", 7.2)
        pdf.cell(col_w, 4, "    4. Medición de potencias", 1, 1, fill=True)
        create_power_table(pdf, SIDE_MARGIN + 5, potencias_valores)

        # Columna Derecha
        pdf.set_y(30)
        draw_boxed_text_auto(pdf, SECOND_COL_L, pdf.get_y(), col_w, 15, "Observaciones", observaciones)
        pdf.ln(2)
        draw_si_no_boxes(pdf, SECOND_COL_L, pdf.get_y(), operativo)
        pdf.ln(2)
        pdf.set_x(SECOND_COL_L)
        pdf.cell(0, 4, f"TÉCNICO: {tecnico}", 0, 1)
        y_f = pdf.get_y()
        pdf.set_x(SECOND_COL_L); pdf.cell(15, 10, "FIRMA: ")
        add_signature_inline(pdf, canvas_tecnico, SECOND_COL_L + 30, y_f, 40, 12, False)
        
        pdf.set_y(y_f + 12)
        pdf.set_x(SECOND_COL_L); pdf.cell(0, 4, f"EMPRESA: {empresa}", 0, 1)
        pdf.ln(2)
        draw_boxed_text_auto(pdf, SECOND_COL_L, pdf.get_y(), col_w, 10, "Uso Interno", observaciones_interno)
        
        pdf.ln(15)
        y_sigs = pdf.get_y()
        add_signature_inline(pdf, canvas_ingenieria, SECOND_COL_L + 20, y_sigs - 12, 30, 12)
        add_signature_inline(pdf, canvas_clinico, SECOND_COL_L + col_w - 20, y_sigs - 12, 30, 12)
        
        pdf.line(SECOND_COL_L + 5, y_sigs, SECOND_COL_L + 45, y_sigs)
        pdf.line(SECOND_COL_L + col_w - 45, y_sigs, SECOND_COL_L + col_w - 5, y_sigs)
        pdf.set_xy(SECOND_COL_L + 5, y_sigs + 1); pdf.multi_cell(40, 3, "ING. CLÍNICA", 0, "C")
        pdf.set_xy(SECOND_COL_L + col_w - 45, y_sigs + 1); pdf.multi_cell(40, 3, "PERS. CLÍNICO", 0, "C")

        out = pdf.output(dest="S")
        st.download_button("Descargar PDF", bytes(out), file_name=f"MP_{sn}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()

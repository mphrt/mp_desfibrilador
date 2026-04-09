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

# Listas base
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

def add_signature_centered(pdf_obj, canvas_result, line_x_start, line_w, y_top, max_w=50, max_h=15):
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w = max_w
        img_h = (img.height / img.width) * img_w
        if img_h > max_h:
            img_h = max_h
            img_w = (img.width / img.height) * img_h
        center_x = line_x_start + (line_w / 2)
        final_x = center_x - (img_w / 2)
        pdf_obj.image(tmp_path, x=final_x, y=y_top, w=img_w, h=img_h)
    except Exception:
        pass

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

def draw_boxed_text_auto(pdf, x, y, w, min_h, title, text, head_h=4.6, fs_head=7.2, fs_body=7.0, body_line_h=3.2, padding=1.2):
    pdf.set_xy(x, y)
    pdf.set_fill_color(230, 230, 230); pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", fs_head)
    pdf.cell(w, head_h, title, border=1, ln=1, align="L", fill=True)
    y_body = y + head_h
    x_text = x + padding
    w_text = max(1, w - 2*padding)
    pdf.set_xy(x_text, y_body + padding)
    pdf.set_font("Arial", "", fs_body)
    if text:
        pdf.multi_cell(w_text, body_line_h, text, border=0, align="L")
    end_y = pdf.get_y()
    content_h = max(min_h, (end_y - (y_body + padding)) + padding)
    pdf.rect(x, y_body, w, content_h)
    pdf.set_y(y_body + content_h)

def create_power_table(pdf, x_pos, y_pos, items, row_h=3.4, head_fs=7.2, cell_fs=6.2, indent_w=5.0):
    pdf.set_xy(x_pos, y_pos)
    pdf.set_fill_color(230, 230, 230); pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", head_fs)
    headers = ["PRUEBA", "RITMO", "AMPL", "LOAD", "ENERGY SET", "ENERGY RESULT (J)"]
    widths = [22, 18, 18, 18, 22, 28] 
    pdf.set_x(x_pos + indent_w)
    for i, header in enumerate(headers):
        pdf.cell(widths[i], row_h, header, border=1, ln=0, align="C", fill=True)
    pdf.ln(row_h)
    pdf.set_font("Arial", "", cell_fs)
    for i, item in enumerate(items):
        pdf.set_x(x_pos + indent_w)
        values = [str(i + 1), "80BPM", "1,0mV", "50ohm", item[0], item[1]]
        for j, value in enumerate(values):
            pdf.cell(widths[j], row_h, value, border=1, ln=0, align="C")
        pdf.ln(row_h)
    pdf.ln(2.6)

def draw_analisis_columns(pdf, x_start, y_start, col_w, data_list):
    row_h_field = 3.4
    label_w = 28.0
    text_w = col_w - label_w - 3.0
    def draw_column_no_lines(x, y, data):
        yy = y
        def field(lbl, val=""):
            nonlocal yy
            pdf.set_xy(x, yy); pdf.set_font("Arial", "", 6.2); pdf.cell(label_w, row_h_field, f"{lbl}", border=0, ln=0)
            pdf.set_xy(x + label_w, yy); pdf.cell(text_w, row_h_field, f" : {val}", border=0, ln=1)
            yy += row_h_field
        field("EQUIPO",  data.get('equipo', ''))
        field("MARCA",  data.get('marca', ''))
        field("MODELO",  data.get('modelo', ''))
        field("NÚMERO SERIE", data.get('serie', ''))
        return yy
    num_equipos = len(data_list)
    y_current = y_start
    if num_equipos == 1:
        draw_column_no_lines(x_start, y_current, data_list[0])
        y_current = pdf.get_y() + 2
    elif num_equipos >= 2:
        gap_cols = 6
        col_w2 = (col_w - gap_cols) / 2.0
        left_x = x_start
        right_x = x_start + col_w2 + gap_cols
        end_left = draw_column_no_lines(left_x, y_current, data_list[0])
        end_right = draw_column_no_lines(right_x, y_current, data_list[1])
        y_current = max(end_left, end_right) + 2
    return y_current

def checklist(title, items):
    st.subheader(title)
    respuestas = []
    for item in items:
        with st.container():
            col1, col2 = st.columns([5, 3])
            with col1:
                st.markdown(item)
            with col2:
                seleccion = st.radio("", ["OK", "NO", "N/A"], horizontal=True, key=item)
        respuestas.append((item, seleccion))
    return respuestas

# ========= App Principal =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Monitor/Desfibrilador")

    # --- DATOS DEL EQUIPO ---
    ideq = st.text_input("IDEQ")
    
    # --- MARCA CON NOMBRE CAMBIADO ---
    marca_sel = st.selectbox("Marca", MARCAS_BASE + ["+ Añadir nueva marca..."], index=0)
    if marca_sel == "+ Añadir nueva marca...":
        marca = st.text_input("Escribe el nombre del nuevo modelo", key="input_marca_custom")
    else:
        marca = marca_sel

    # --- MODELO ---
    modelo_sel = st.selectbox("Modelo", MODELOS_BASE + ["+ Añadir nuevo modelo..."], index=0)
    if modelo_sel == "+ Añadir nuevo modelo...":
        modelo = st.text_input("Escribe el nombre del nuevo modelo", key="input_modelo_custom")
    else:
        modelo = modelo_sel

    sn = st.text_input("Número de Serie")
    inventario = st.text_input("Número de Inventario")
    fecha = st.date_input("Fecha", value=datetime.date.today())
    ubicacion = st.text_input("Ubicación")

    # --- LISTAS DE CHEQUEO ---
    chequeo_visual = checklist("1. Inspección y limpieza", [
        "1.1. Inspección general", "1.2. Limpieza de contactos", "1.3. Limpieza de cabezal termo-inscriptor",
        "1.4. Revisión del estado de los accesorios", "1.5. Revisión del panel", "1.6. Revisión del conexiones eléctricas"
    ])
    seguridad_electrica = checklist("2. Seguridad eléctrica", [
        "2.1. Medición de corrientes de fuga normal condición", "2.2. Medición de corrientes de fuga con neutro abierto"
    ])
    accesorios_equipo = checklist("3. Accesorios del equipo", [
        "3.1. Cable de poder", "3.2. Cable paciente", "3.3. Cable de interfaz",
        "3.4. Cable de tierra fuente de poder", "3.5. Palas desfibriladoras"
    ])

    st.subheader("4. Medición de potencias")
    potencias_valores = []
    energia_set = [5, 15, 20, 50, 75, 100, 200]
    for i, energia in enumerate(energia_set):
        valor_medido = st.text_input(f"Energía de ajuste: {energia} J", key=f"potencia_{i}")
        potencias_valores.append((f"{energia} J", valor_medido))

    st.subheader("5. Instrumentos de análisis")
    if 'analisis_equipos' not in st.session_state: st.session_state.analisis_equipos = [{}]
    def add_equipo(): st.session_state.analisis_equipos.append({})
    for i in range(len(st.session_state.analisis_equipos)):
        st.markdown(f"**Equipo {i+1}**")
        col_eq, col_btn = st.columns([0.9, 0.1])
        with col_eq:
            st.session_state.analisis_equipos[i]['equipo'] = st.text_input("EQUIPO", value=st.session_state.analisis_equipos[i].get('equipo', ''), key=f"equipo_{i}")
            st.session_state.analisis_equipos[i]['marca'] = st.text_input("MARCA", value=st.session_state.analisis_equipos[i].get('marca', ''), key=f"marca_inst_{i}")
            st.session_state.analisis_equipos[i]['modelo'] = st.text_input("MODELO", value=st.session_state.analisis_equipos[i].get('modelo', ''), key=f"modelo_an_{i}")
            st.session_state.analisis_equipos[i]['serie'] = st.text_input("NÚMERO SERIE", value=st.session_state.analisis_equipos[i].get('serie', ''), key=f"serie_{i}")
        if i > 0:
            with col_btn:
                st.write("")
                if st.button("−", key=f"remove_btn_{i}"):
                    st.session_state.analisis_equipos.pop(i)
                    st.rerun()
    st.button("Agregar Equipo +", on_click=add_equipo)

    observaciones = st.text_area("Observaciones")
    observaciones_interno = st.text_area("Observaciones (uso interno)")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    col_tecnico, col_ingenieria, col_clinico = st.columns(3)
    with col_tecnico:
        st.write("Técnico Encargado:")
        canvas_result_tecnico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="canvas_tecnico")
    with col_ingenieria:
        st.write("Ingeniería Clínica:")
        canvas_result_ingenieria = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="canvas_ingenieria")
    with col_clinico:
        st.write("Personal Clínico:")
        canvas_result_clinico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="canvas_clinico")

    # --- GENERACIÓN PDF ---
    if st.button("Generar PDF"):
        SIDE_MARGIN, TOP_MARGIN = 9, 4
        pdf = PDF('L', 'mm', 'A4', footer_lines=FOOTER_LINES)
        pdf.set_margins(SIDE_MARGIN, TOP_MARGIN, SIDE_MARGIN)
        pdf.add_page()

        page_w = pdf.w
        usable_w = page_w - 2 * SIDE_MARGIN
        COL_GAP = 6
        col_total_w = (usable_w - COL_GAP) / 2.0
        COL_W, ITEM_W = 12.0, max(62.0, col_total_w - 36.0)
        SECOND_COL_LEFT = SIDE_MARGIN + col_total_w + COL_GAP

        # LOGO E IDENTIFICACIÓN
        LOGO_W = 60
        try:
            pdf.image("logo_hrt_final.jpg", x=SIDE_MARGIN, y=2, w=LOGO_W)
            logo_h = 15
        except Exception: logo_h = 10

        pdf.set_font("Arial", "B", 8)
        pdf.set_xy(page_w - SIDE_MARGIN - 25, 4)
        pdf.cell(25, 4.5, f"IDEQ: {ideq}", border=1, ln=1, align="C", fill=True)

        pdf.set_xy(SIDE_MARGIN + LOGO_W + 5, logo_h - 3)
        pdf.set_font("Arial", "B", 7)
        pdf.cell(col_total_w - LOGO_W, 5.0, "PAUTA MANTENIMIENTO MONITOR/DESFIBRILADOR", border=1, align="C", fill=True)

        content_y = logo_h + 8
        pdf.set_y(content_y)

        # CAMPOS BÁSICOS
        def pdf_field(lbl, val):
            pdf.set_font("Arial", "B", 7.5); pdf.cell(28, 4.4, f"{lbl}", 0, 0)
            pdf.set_font("Arial", "", 7.5); pdf.cell(0, 4.4, f" : {val}", 0, 1)

        pdf_field("MARCA", marca)
        pdf_field("MODELO", modelo)
        pdf_field("NÚMERO SERIE", sn)
        pdf_field("N° INVENTARIO", inventario)
        pdf_field("UBICACIÓN", ubicacion)

        # TABLAS
        pdf.ln(2)
        create_checkbox_table(pdf, "1. Inspección y limpieza", chequeo_visual, SIDE_MARGIN, ITEM_W, COL_W)
        create_checkbox_table(pdf, "2. Seguridad eléctrica", seguridad_electrica, SIDE_MARGIN, ITEM_W, COL_W)
        create_checkbox_table(pdf, "3. Accesorios del equipo", accesorios_equipo, SIDE_MARGIN, ITEM_W, COL_W)
        
        pdf.set_font("Arial", "B", 7.5); pdf.cell(col_total_w, 4.0, "      4. Medición de potencias", border=1, ln=1, fill=True)
        create_power_table(pdf, SIDE_MARGIN, pdf.get_y()+1, potencias_valores)
        
        pdf.set_font("Arial", "B", 7.5); pdf.cell(col_total_w, 4.0, "      5. Instrumentos de análisis", border=1, ln=1, fill=True)
        draw_analisis_columns(pdf, SIDE_MARGIN, pdf.get_y()+1, col_total_w, st.session_state.analisis_equipos)

        # SECCIÓN DERECHA
        pdf.set_y(content_y)
        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, 15, "   Observaciones", observaciones)
        pdf.ln(2); pdf.set_x(SECOND_COL_LEFT)
        draw_si_no_boxes(pdf, SECOND_COL_LEFT, pdf.get_y(), operativo)
        
        pdf.ln(8); pdf.set_x(SECOND_COL_LEFT)
        pdf.cell(0, 4, f"TÉCNICO: {tecnico}", 0, 1)
        add_signature_inline(pdf, canvas_result_tecnico, SECOND_COL_LEFT + 20, pdf.get_y())
        
        pdf.ln(18); pdf.set_x(SECOND_COL_LEFT)
        pdf.cell(0, 4, f"EMPRESA: {empresa}", 0, 1)
        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y()+2, col_total_w, 15, "   Uso interno", observaciones_interno)

        # FIRMAS FINALES
        y_f = pdf.get_y() + 10
        add_signature_centered(pdf, canvas_result_ingenieria, SECOND_COL_LEFT + 5, 45, y_f)
        add_signature_centered(pdf, canvas_result_clinico, SECOND_COL_LEFT + col_total_w - 50, 45, y_f)

        out = pdf.output(dest="S").encode("latin1")
        st.download_button("Descargar PDF", out, file_name=f"MP_{sn}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()

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

# ========= Configuración de Marcas y Modelos (ORDENADOS ALFABÉTICAMENTE) =========
# Se mantiene el primer elemento vacío para selección manual
MARCAS_BASE = [""] + sorted(["NIHON KOHDEN", "ZOLL MEDICAL", "ADVANCED", "MINDRAY"])
MODELOS_BASE = [""] + sorted([
    "TEC5521K", "M-SERIES", "PD-1400", "D-1000", "TEC7631G", 
    "CARDIOLIFE", "BENEHEART D3", "TEC-5531E", "CU-HD1", 
    "TEC-5631E", "TEC3521K", "R-SERIES", "C1A"
])

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

# ========= Utilidades de Firma e Interfaz =========
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

def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w, row_h=3.4):
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230); pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 7.2)
    pdf.cell(item_w, row_h, f"    {section_title}", border=1, ln=0, align="L", fill=True)
    pdf.cell(col_w, row_h, "OK", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", 6.2)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(5.0, row_h, "", border=0, ln=0)
        pdf.cell(max(1, item_w - 5.0), row_h, item, border=0, ln=0, align="L")
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, ln=1, align="C")
    pdf.ln(1.6)

def create_power_table(pdf, x_pos, items, row_h=3.4):
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.2)
    headers = ["PRUEBA", "RITMO", "AMPL", "LOAD", "ENERGY SET", "ENERGY RESULT (J)"]
    widths = [22, 18, 18, 18, 22, 28] 
    for i, header in enumerate(headers):
        pdf.cell(widths[i], row_h, header, border=1, ln=0, align="C", fill=True)
    pdf.ln(row_h)
    pdf.set_font("Arial", "", 6.2)
    for i, item in enumerate(items):
        pdf.set_x(x_pos)
        values = [str(i + 1), "80BPM", "1,0mV", "50ohm", item[0], item[1]]
        for j, val in enumerate(values):
            pdf.cell(widths[j], row_h, val, border=1, ln=0, align="C")
        pdf.ln(row_h)
    pdf.ln(2.6)

def draw_boxed_text_auto(pdf, x, y, w, min_h, title, text):
    pdf.set_xy(x, y)
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.2)
    pdf.cell(w, 4.6, title, border=1, ln=1, align="L", fill=True)
    y_body = y + 4.6
    pdf.set_xy(x + 1.2, y_body + 1.2)
    pdf.set_font("Arial", "", 7.0)
    if text:
        pdf.multi_cell(w - 2.4, 3.2, text, border=0, align="L")
    content_h = max(min_h, (pdf.get_y() - y_body) + 1.2)
    pdf.rect(x, y_body, w, content_h)
    pdf.set_y(y_body + content_h)

def draw_analisis_columns(pdf, x_start, y_start, col_w, data_list):
    row_h_field = 3.4
    label_w = 28.0
    text_w = col_w - label_w - 3.0
    for i, data in enumerate(data_list):
        curr_x = x_start if i == 0 else x_start + (col_w / 2) + 3
        yy = y_start
        for lbl, key in [("EQUIPO", "equipo"), ("MARCA", "marca"), ("MODELO", "modelo"), ("NÚMERO SERIE", "serie")]:
            pdf.set_xy(curr_x, yy); pdf.set_font("Arial", "", 6.2)
            pdf.cell(label_w, row_h_field, f"    {lbl}", border=0)
            pdf.cell(text_w, row_h_field, f": {data.get(key, '')}", border=0, ln=1)
            yy += row_h_field
    return y_start + (row_h_field * 4) + 2

# ========= App Streamlit =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Monitor/Desfibrilador")

    ideq = st.text_input("IDEQ")
    
    # Menús despegables con ORDEN ALFABÉTICO y opción de añadir nuevo
    marca_sel = st.selectbox("MARCA", MARCAS_BASE + ["+ Añadir nueva marca..."], index=0)
    marca = st.text_input("Escribe el nombre de la nueva marca") if marca_sel == "+ Añadir nueva marca..." else marca_sel

    modelo_sel = st.selectbox("MODELO", MODELOS_BASE + ["+ Añadir nuevo modelo..."], index=0)
    modelo = st.text_input("Escribe el nombre del nuevo modelo") if modelo_sel == "+ Añadir nuevo modelo..." else modelo_sel

    sn = st.text_input("NÚMERO DE SERIE")
    inventario = st.text_input("NÚMERO DE INVENTARIO")
    fecha = st.date_input("FECHA", value=datetime.date.today())
    ubicacion = st.text_input("UBICACIÓN")

    # Checklists
    c1 = [("1.1. Inspección general", "1.1"), ("1.2. Limpieza de contactos", "1.2"), ("1.3. Limpieza de cabezal termo-inscriptor", "1.3"), ("1.4. Revisión del estado de los accesorios", "1.4"), ("1.5. Revisión del panel", "1.5"), ("1.6. Revisión del conexiones eléctricas", "1.6")]
    c2 = [("2.1. Medición de corrientes de fuga normal condición", "2.1"), ("2.2. Medición de corrientes de fuga con neutro abierto", "2.2")]
    c3 = [("3.1. Cable de poder", "3.1"), ("3.2. Cable paciente", "3.2"), ("3.3. Cable de interfaz", "3.4"), ("3.4. Cable de tierra fuente de poder", "3.5"), ("3.5. Palas desfibriladoras", "3.6")]

    def render_checklist(title, items):
        st.subheader(title)
        res = []
        for label, key in items:
            col1, col2 = st.columns([5, 3])
            val = col2.radio("", ["OK", "NO", "N/A"], horizontal=True, key=f"check_{key}")
            col1.markdown(label)
            res.append((label, val))
        return res

    resp_c1 = render_checklist("1. Inspección y limpieza", c1)
    resp_c2 = render_checklist("2. Seguridad eléctrica", c2)
    resp_c3 = render_checklist("3. Accesorios del equipo", c3)

    st.subheader("4. Medición de potencias")
    pot_val = []
    for en in [5, 15, 20, 50, 75, 100, 200]:
        val = st.text_input(f"Energía de ajuste: {en} J", key=f"p_{en}")
        pot_val.append((f"{en} J", val))

    st.subheader("5. Instrumentos de análisis")
    an_eqs = [{}, {}]
    for i in range(2):
        st.markdown(f"**Equipo {i+1}**")
        an_eqs[i] = {
            "equipo": st.text_input("Equipo", key=f"ae_{i}"),
            "marca": st.text_input("Marca", key=f"am_{i}"),
            "modelo": st.text_input("Modelo", key=f"amo_{i}"),
            "serie": st.text_input("Número de Serie", key=f"as_{i}")
        }

    observaciones = st.text_area("Observaciones")
    observaciones_interno = st.text_area("Observaciones (uso interno)")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    colA, colB, colC = st.columns(3)
    can_t = colA.write("Técnico Encargado:") or st_canvas(stroke_width=3, height=150, width=250, key="c_t")
    can_i = colB.write("Ingeniería Clínica:") or st_canvas(stroke_width=3, height=150, width=250, key="c_i")
    can_c = colC.write("Personal Clínico:") or st_canvas(stroke_width=3, height=150, width=250, key="c_c")

    if st.button("Generar PDF"):
        pdf = PDF("L", "mm", "A4", footer_lines=FOOTER_LINES)
        pdf.set_margins(9, 4, 9)
        pdf.add_page()
        
        usable_w = pdf.w - 18
        col_w = (usable_w - 6) / 2
        
        # Logo e IDEQ (Igual al 2do código)
        try: pdf.image("logo_hrt_final.jpg", x=2, y=2, w=60)
        except: pass
        
        pdf.set_font("Arial", "B", 8)
        ideq_txt = f"IDEQ: {ideq}"
        ideq_w = pdf.get_string_width(ideq_txt) + 4
        pdf.set_xy(pdf.w - 9 - ideq_w, 4)
        pdf.cell(ideq_w, 4.5, ideq_txt, border=1, align="C", fill=True)

        pdf.set_xy(66, 18); pdf.set_font("Arial", "B", 7)
        pdf.cell(col_w - 5, 5.0, "PAUTA MANTENCIÓN MONITOR/DESFIBRILADOR", border=1, align="C", fill=True)

        # Fecha y Datos Izquierda
        pdf.set_y(29)
        pdf.set_xy(9 + col_w - 33, 29)
        pdf.set_font("Arial", "B", 7.5); pdf.cell(13, 3.4, "FECHA:", 0, 0, "R")
        pdf.cell(11, 3.4, f"{fecha.day:02d}", 1, 0, "C")
        pdf.cell(11, 3.4, f"{fecha.month:02d}", 1, 0, "C")
        pdf.cell(11, 3.4, f"{fecha.year:04d}", 1, 1, "C")

        def add_field(l, v):
            pdf.set_x(9); pdf.set_font("Arial", "", 7.5)
            pdf.cell(35, 3.4, l, 0, 0); pdf.cell(2, 3.4, ":", 0, 0); pdf.cell(0, 3.4, str(v), 0, 1)

        add_field("MARCA", marca); add_field("MODELO", modelo); add_field("NÚMERO DE SERIE", sn)
        add_field("N/INVENTARIO", inventario); add_field("UBICACIÓN", ubicacion)

        pdf.ln(2.6)
        create_checkbox_table(pdf, "1. Inspección y limpieza", resp_c1, 9, col_w - 36, 12)
        create_checkbox_table(pdf, "2. Seguridad eléctrica", resp_c2, 9, col_w - 36, 12)
        create_checkbox_table(pdf, "3. Accesorios del equipo", resp_c3, 9, col_w - 36, 12)
        
        pdf.set_x(9); pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.5)
        pdf.cell(col_w, 4, "    4. Medición de potencias", border=1, ln=1, fill=True)
        create_power_table(pdf, 14, pot_val)

        pdf.set_x(9); pdf.cell(col_w, 4, "    5. Instrumentos de análisis", border=1, ln=1, fill=True)
        draw_analisis_columns(pdf, 9, pdf.get_y()+1, col_w, an_eqs)

        # Columna Derecha
        pdf.set_y(39)
        draw_boxed_text_auto(pdf, 9 + col_w + 6, 39, col_w, 20, "Observaciones", observaciones)
        pdf.ln(2); draw_si_no_boxes(pdf, 15 + col_w, pdf.get_y(), operativo, label_w=40)
        
        pdf.ln(2); pdf.set_x(15 + col_w)
        pdf.cell(0, 4.6, f"NOMBRE TÉCNICO/INGENIERO: {tecnico}", 0, 1)
        y_f = pdf.get_y() + 4
        pdf.set_xy(15 + col_w, y_f); pdf.cell(14, 4.6, "FIRMA:", 0, 0)
        add_signature_inline(pdf, can_t, 35 + col_w, y_f, 55, 18, centered=False)
        
        pdf.set_y(y_f + 20); pdf.set_x(15 + col_w)
        pdf.cell(0, 4, f"EMPRESA RESPONSABLE: {empresa}", 0, 1)
        pdf.ln(2); draw_boxed_text_auto(pdf, 9 + col_w + 6, pdf.get_y(), col_w, 15, "Observaciones (uso interno)", observaciones_interno)

        # Firmas Recepción
        pdf.ln(10); y_sigs = pdf.get_y()
        x_start = 9 + col_w + 6 + (col_w / 2) - 44
        pdf.line(x_start, y_sigs + 15, x_start + 40, y_sigs + 15)
        pdf.line(x_start + 48, y_sigs + 15, x_start + 88, y_sigs + 15)
        pdf.set_font("Arial", "B", 6.5)
        pdf.set_xy(x_start, y_sigs + 16); pdf.multi_cell(40, 3.5, "RECEPCIÓN CONFORME\nINGENIERÍA CLÍNICA", 0, "C")
        pdf.set_xy(x_start + 48, y_sigs + 16); pdf.multi_cell(40, 3.5, "RECEPCIÓN CONFORME\nPERSONAL CLÍNICO", 0, "C")
        add_signature_inline(pdf, can_i, x_start + 20, y_sigs - 2, 35, 15)
        add_signature_inline(pdf, can_c, x_start + 68, y_sigs - 2, 35, 15)

        fname = f"{ideq}_MP_Monitor_{sn}.pdf" if ideq else f"MP_Monitor_{sn}.pdf"
        st.download_button("Descargar PDF", pdf.output(dest="S"), file_name=fname, mime="application/pdf")

if __name__ == "__main__":
    main()

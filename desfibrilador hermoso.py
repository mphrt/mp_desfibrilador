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

# ========= Configuración de Marcas y Modelos (ORDEN ALFABÉTICO) =========
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

# ========= Utilidades de Firma =========
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
    except:
        pass

# ========= Funciones de Dibujo (Tablas y Recuadros) =========
def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w, row_h=3.4):
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 7.2)
    pdf.cell(item_w, row_h, f"    {section_title}", border=1, ln=0, align="L", fill=True)
    pdf.cell(col_w, row_h, "OK", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", 6.2)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(5.0, row_h, "", border=0)
        pdf.cell(max(1, item_w - 5.0), row_h, item, border=0, align="L")
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, ln=1, align="C")
    pdf.ln(1.6)

def create_power_table(pdf, x_pos, items, row_h=3.4):
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.2)
    headers = ["PRUEBA", "RITMO", "AMPL", "LOAD", "ENERGY SET", "ENERGY RESULT (J)"]
    widths = [22, 18, 18, 18, 22, 28] 
    for i, h in enumerate(headers):
        pdf.cell(widths[i], row_h, h, border=1, align="C", fill=True)
    pdf.ln(row_h)
    pdf.set_font("Arial", "", 6.2)
    for i, item in enumerate(items):
        pdf.set_x(x_pos)
        v = [str(i + 1), "80BPM", "1,0mV", "50ohm", item[0], item[1]]
        for j, val in enumerate(v):
            pdf.cell(widths[j], row_h, val, border=1, align="C")
        pdf.ln(row_h)
    pdf.ln(2.6)

def draw_boxed_text_auto(pdf, x, y, w, min_h, title, text):
    pdf.set_xy(x, y)
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.2)
    pdf.cell(w, 4.6, title, border=1, ln=1, fill=True)
    y_body = pdf.get_y()
    pdf.set_font("Arial", "", 7.0)
    pdf.set_xy(x + 1.2, y_body + 1.2)
    if text:
        pdf.multi_cell(w - 2.4, 3.2, text, border=0)
    final_h = max(min_h, (pdf.get_y() - y_body) + 1.2)
    pdf.rect(x, y_body, w, final_h)
    pdf.set_y(y_body + final_h)

def main():
    st.title("Pauta de Mantenimiento Preventivo - Monitor/Desfibrilador")

    # --- DATOS DE CABECERA ---
    ideq = st.text_input("IDEQ")
    m_sel = st.selectbox("MARCA", MARCAS_BASE + ["+ Añadir nueva marca..."])
    marca = st.text_input("Escribe el nombre de la nueva marca") if m_sel == "+ Añadir nueva marca..." else m_sel
    
    mod_sel = st.selectbox("MODELO", MODELOS_BASE + ["+ Añadir nuevo modelo..."])
    modelo = st.text_input("Escribe el nombre del nuevo modelo") if mod_sel == "+ Añadir nuevo modelo..." else mod_sel

    sn = st.text_input("NÚMERO DE SERIE")
    inv = st.text_input("NÚMERO DE INVENTARIO")
    fecha = st.date_input("FECHA", value=datetime.date.today())
    ubic = st.text_input("UBICACIÓN")

    # --- CHECKLISTS ---
    def checklist_section(title, items):
        st.subheader(title)
        res = []
        for label in items:
            c1, c2 = st.columns([5, 3])
            val = c2.radio("", ["OK", "NO", "N/A"], horizontal=True, key=label)
            c1.markdown(label)
            res.append((label, val))
        return res

    res1 = checklist_section("1. Inspección y limpieza", ["1.1. Inspección general", "1.2. Limpieza de contactos", "1.3. Limpieza de cabezal termo-inscriptor", "1.4. Revisión del estado de los accesorios", "1.5. Revisión del panel", "1.6. Revisión del conexiones eléctricas"])
    res2 = checklist_section("2. Seguridad eléctrica", ["2.1. Medición de corrientes de fuga normal condición", "2.2. Medición de corrientes de fuga con neutro abierto"])
    res3 = checklist_section("3. Accesorios del equipo", ["3.1. Cable de poder", "3.2. Cable paciente", "3.3. Cable de interfaz", "3.4. Cable de tierra fuente de poder", "3.5. Palas desfibriladoras"])

    st.subheader("4. Medición de potencias")
    pots = []
    for en in [5, 15, 20, 50, 75, 100, 200]:
        val = st.text_input(f"Energía de ajuste: {en} J", key=f"en_{en}")
        pots.append((f"{en} J", val))

    st.subheader("5. Instrumentos de análisis")
    inst = [{}, {}]
    for i in range(2):
        st.write(f"Instrumento {i+1}")
        inst[i] = {
            "equipo": st.text_input("Equipo", key=f"e_{i}"),
            "marca": st.text_input("Marca", key=f"m_{i}"),
            "modelo": st.text_input("Modelo", key=f"mo_{i}"),
            "serie": st.text_input("Número Serie", key=f"s_{i}")
        }

    obs = st.text_area("Observaciones")
    obs_int = st.text_area("Observaciones (uso interno)")
    op = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tec = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    emp = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    cA, cB, cC = st.columns(3)
    cA.write("Técnico Encargado:")
    can_t = st_canvas(stroke_width=3, height=150, width=250, key="ct")
    cB.write("Ingeniería Clínica:")
    can_i = st_canvas(stroke_width=3, height=150, width=250, key="ci")
    cC.write("Personal Clínico:")
    can_c = st_canvas(stroke_width=3, height=150, width=250, key="cc")

    if st.button("Generar PDF"):
        pdf = PDF("L", "mm", "A4", footer_lines=FOOTER_LINES)
        pdf.set_margins(9, 4, 9)
        pdf.add_page()
        
        usable_w = pdf.w - 18
        col_w = (usable_w - 6) / 2
        
        # --- POSICIONAMIENTO IDENTICO AL SEGUNDO CODIGO ---
        try: pdf.image("logo_hrt_final.jpg", x=2, y=2, w=60)
        except: pass
        
        # IDEQ (Arriba Derecha)
        pdf.set_font("Arial", "B", 8)
        ideq_txt = f"IDEQ: {ideq}"
        ideq_w = pdf.get_string_width(ideq_txt) + 4
        pdf.set_xy(pdf.w - 9 - ideq_w, 4)
        pdf.cell(ideq_w, 4.5, ideq_txt, border=1, align="C", fill=True)

        # TITULO
        pdf.set_xy(65, 18); pdf.set_font("Arial", "B", 7)
        pdf.cell(col_w, 5.0, "PAUTA MANTENCIÓN MONITOR/DESFIBRILADOR", border=1, align="C", fill=True)

        # FECHA (Recuadros)
        pdf.set_xy(9 + col_w - 33, 29)
        pdf.set_font("Arial", "B", 7.5); pdf.cell(13, 3.4, "FECHA:", 0, 0, "R")
        pdf.cell(11, 3.4, f"{fecha.day:02d}", 1, 0, "C")
        pdf.cell(11, 3.4, f"{fecha.month:02d}", 1, 0, "C")
        pdf.cell(11, 3.4, f"{fecha.year:04d}", 1, 1, "C")

        # Datos Generales (Izquierda)
        def field(l, v):
            pdf.set_x(9); pdf.set_font("Arial", "", 7.5)
            pdf.cell(35, 3.4, l, 0, 0); pdf.cell(2, 3.4, ":", 0, 0); pdf.cell(0, 3.4, str(v), 0, 1)

        pdf.set_y(29)
        field("MARCA", marca); field("MODELO", modelo); field("NÚMERO DE SERIE", sn)
        field("N/INVENTARIO", inv); field("UBICACIÓN", ubic)

        # Tablas (Izquierda)
        pdf.ln(2.6)
        create_checkbox_table(pdf, "1. Inspección y limpieza", res1, 9, col_w - 36, 12)
        create_checkbox_table(pdf, "2. Seguridad eléctrica", res2, 9, col_w - 36, 12)
        create_checkbox_table(pdf, "3. Accesorios del equipo", res3, 9, col_w - 36, 12)
        
        pdf.set_x(9); pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.5)
        pdf.cell(col_w, 4, "    4. Medición de potencias", border=1, ln=1, fill=True)
        create_power_table(pdf, 14, pots)

        pdf.set_x(9); pdf.cell(col_w, 4, "    5. Instrumentos de análisis", border=1, ln=1, fill=True)
        pdf.ln(1)
        for i, d in enumerate(inst):
            pdf.set_x(9 if i==0 else 9 + (col_w/2) + 3)
            curr_x = pdf.get_x()
            for l, k in [("EQUIPO","equipo"),("MARCA","marca"),("MODELO","modelo"),("SERIE","serie")]:
                pdf.set_x(curr_x); pdf.set_font("Arial", "", 6.2)
                pdf.cell(25, 3.2, f"    {l}", 0); pdf.cell(0, 3.2, f": {d[k]}", 0, 1)
            pdf.set_y(pdf.get_y() - 12.8 if i==0 else pdf.get_y())

        # Columna Derecha
        pdf.set_y(39)
        draw_boxed_text_auto(pdf, 9 + col_w + 6, 39, col_w, 20, "Observaciones", obs)
        
        pdf.ln(2); pdf.set_x(9 + col_w + 6)
        pdf.set_font("Arial", "", 7.5); pdf.cell(40, 4.5, "EQUIPO OPERATIVO:", 0)
        pdf.rect(pdf.get_x(), pdf.get_y(), 4.5, 4.5)
        pdf.cell(4.5, 4.5, "X" if op=="SI" else "", 0, 0, "C"); pdf.cell(6, 4.5, "SI")
        pdf.set_x(pdf.get_x() + 4)
        pdf.rect(pdf.get_x(), pdf.get_y(), 4.5, 4.5)
        pdf.cell(4.5, 4.5, "X" if op=="NO" else "", 0, 0, "C"); pdf.cell(6, 4.5, "NO", 0, 1)
        
        pdf.ln(2); pdf.set_x(9 + col_w + 6)
        pdf.cell(0, 4.6, f"NOMBRE TÉCNICO/INGENIERO: {tec}", 0, 1)
        y_f = pdf.get_y() + 2
        pdf.set_xy(9 + col_w + 6, y_f); pdf.cell(15, 4.6, "FIRMA:")
        add_signature_inline(pdf, can_t, 9 + col_w + 25, y_f, 50, 15, centered=False)
        
        pdf.set_y(y_f + 16); pdf.set_x(9 + col_w + 6)
        pdf.cell(0, 4, f"EMPRESA RESPONSABLE: {emp}", 0, 1)
        pdf.ln(2)
        draw_boxed_text_auto(pdf, 9 + col_w + 6, pdf.get_y(), col_w, 15, "Observaciones (uso interno)", obs_int)

        # Firmas de Recepción (Al centro de la col derecha)
        pdf.ln(8); y_sigs = pdf.get_y()
        mid_x = 9 + col_w + 6 + (col_w/2)
        pdf.line(mid_x - 45, y_sigs + 15, mid_x - 5, y_sigs + 15)
        pdf.line(mid_x + 5, y_sigs + 15, mid_x + 45, y_sigs + 15)
        pdf.set_font("Arial", "B", 6)
        pdf.set_xy(mid_x - 45, y_sigs + 16); pdf.multi_cell(40, 3, "RECEPCIÓN CONFORME\nINGENIERÍA CLÍNICA", 0, "C")
        pdf.set_xy(mid_x + 5, y_sigs + 16); pdf.multi_cell(40, 3, "RECEPCIÓN CONFORME\nPERSONAL CLÍNICO", 0, "C")
        add_signature_inline(pdf, can_i, mid_x - 25, y_sigs - 2, 35, 12)
        add_signature_inline(pdf, can_c, mid_x + 25, y_sigs - 2, 35, 12)

        # --- NOMBRE DEL ARCHIVO SOLICITADO ---
        filename = f"{ideq}_MP_Desfibrilador_{sn}.pdf"
        st.download_button("Descargar PDF", pdf.output(dest="S"), file_name=filename, mime="application/pdf")

if __name__ == "__main__":
    main()

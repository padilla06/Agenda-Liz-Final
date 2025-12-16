import flet as ft
import sqlite3
import datetime
import calendar
import os

# --- CONFIGURACIÓN DE COLORES ---
TEMAS = {
    "oscuro": {
        "fondo": "#121212", "superficie": "#1E1E1E", "acento": "#D4AF37", 
        "texto": "#FFFFFF", "texto_sec": "#AAAAAA", "borde": "#333333", 
        "icono": "light_mode", "modo": ft.ThemeMode.DARK,
        "rojo": "#c62828", "verde": "#2e7d32", "amarillo": "#fbc02d",
        "celda_cal": "#2C2C2C"
    },
    "claro": {
        "fondo": "#F5F5F5", "superficie": "#FFFFFF", "acento": "#607D8B", 
        "texto": "#212121", "texto_sec": "#757575", "borde": "#E0E0E0", 
        "icono": "dark_mode", "modo": ft.ThemeMode.LIGHT,
        "rojo": "#ff5252", "verde": "#4caf50", "amarillo": "#ffeb3b",
        "celda_cal": "#FFFFFF"
    }
}

estado_tema = {"actual": "oscuro"}

def main(page: ft.Page):
    # --- 1. CONFIGURACIÓN PÁGINA ---
    page.title = "Agenda Liz"
    page.window_width = 450
    page.window_height = 800
    page.padding = 0 
    
# --- 2. BASE DE DATOS (MODIFICADA PARA ANDROID) ---
    def inicializar_bd():
        # Definir ruta de la BD según el dispositivo
        nombre_bd = "citas.db"
        
        try:
            # Intentamos obtener la ruta de documentos (Android/iOS)
            path = page.client_storage.get("path_documents") # Flet a veces guarda esto
            if not path:
                # Si falla o estamos en PC, usamos ruta local
                db_path = nombre_bd
            else:
                db_path = os.path.join(path, nombre_bd)
        except:
            # Fallback seguro para PC
            db_path = nombre_bd

        # NOTA: Para Flet en Android, usamos una ruta absoluta segura
        # Sin embargo, la forma más robusta en Flet puro sin plugins externos 
        # es confiar en que sqlite3 creará el archivo en el 'app_doc_dir' 
        # que Flet asigna automáticamente al compilar.
        
        # Simplemente usaremos el nombre directo, pero nos aseguramos 
        # que la compilación maneje los permisos.
        
        conn = sqlite3.connect(nombre_bd) 
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT, costo TEXT, fecha TEXT, 
                hora_inicio TEXT, hora_fin TEXT, imagen TEXT
            )
        """)
        conn.commit()
        conn.close()
    inicializar_bd()

    # --- 3. VARIABLES DE ESTADO ---
    id_en_edicion = [None] 
    fecha_elegida = [datetime.datetime.now().strftime('%d/%m/%Y')]
    hora_inicio = [None]
    hora_fin = [None]
    ruta_imagen = [None]
    filtro_fecha = [None]
    
    # ESTADO DE LOS SERVICIOS (Chips)
    sel_diseno = [False]
    sel_pedi = [False]
    sel_cejas = [False]
    
    hoy = datetime.datetime.now()
    cal_estado = {"mes": hoy.month, "anio": hoy.year}
    cal_grande_estado = {"mes": hoy.month, "anio": hoy.year}

    # --- 4. CONTROLES UI ---
    
    # LOGO (Busca 'logo.png' en la carpeta assets)
    # Nota: Si falla la carga, muestra un icono por defecto para no romper la app
    logo_img = ft.Image(src="logo.png", width=50, height=50, fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(name="broken_image"))

    titulo_app = ft.Text("L I Z   M A N I C U R I S T A", weight="bold", size=20)
    btn_tema = ft.IconButton(icon="light_mode", tooltip="Cambiar Tema")

    # Formulario Inputs
    txt_cliente = ft.TextField(label="Cliente", prefix_icon="person", border_radius=10, content_padding=15)
    txt_costo = ft.TextField(label="Costo", prefix_icon="attach_money", keyboard_type=ft.KeyboardType.NUMBER, border_radius=10, content_padding=15)
    
    # --- CHIPS DE SERVICIOS ---
    ref_chip_diseno = ft.Ref[ft.Container]()
    ref_chip_pedi = ft.Ref[ft.Container]()
    ref_chip_cejas = ft.Ref[ft.Container]()

    # Función auxiliar para crear la estructura del chip
    def crear_chip(ref, texto, estado_var):
         return ft.Container(
            ref=ref,
            content=ft.Text(texto, size=12, weight="bold", text_align="center"),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=20,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
            on_click=lambda _: toggle_servicio(estado_var),
        )

    chip_diseno = crear_chip(ref_chip_diseno, "Diseño Dificil", sel_diseno)
    chip_pedi = crear_chip(ref_chip_pedi, "PediSpa", sel_pedi)
    chip_cejas = crear_chip(ref_chip_cejas, "Cejas", sel_cejas)

    # Resto del formulario
    txt_hora_display = ft.Text("Selecciona hora...", size=14)
    lbl_imagen = ft.Text("Sin diseño", size=12)
    icono_img = ft.Icon(name="image")
    
    # Lista y Calendarios
    txt_titulo_lista = ft.Text("CITAS AGENDADAS", size=12, weight="bold")
    btn_ver_todas = ft.TextButton("Ver Todas", icon="list", visible=False, height=30)
    grid_citas = ft.GridView(expand=1, runs_count=5, max_extent=180, child_aspect_ratio=0.85, spacing=10, run_spacing=10, padding=15)
    txt_mes_anio_grande = ft.Text(size=18, weight="bold", text_align="center")
    grid_cal_grande = ft.GridView(expand=1, runs_count=7, spacing=2, run_spacing=2, padding=5, child_aspect_ratio=0.6) 
    cont_dias_cal = ft.GridView(runs_count=7, spacing=2, run_spacing=2, padding=10)
    txt_mes_anio = ft.Text(size=16, weight="bold", text_align="center")

    # --- 5. LÓGICA PRINCIPAL ---
    
    def obtener_tema():
        return TEMAS[estado_tema["actual"]]

    def mostrar_alerta(titulo, msg, es_error=False):
        c = obtener_tema()
        icon = "error" if es_error else "check_circle"
        color = "red" if es_error else c["acento"]
        dlg = ft.AlertDialog(
            bgcolor=c["fondo"],
            title=ft.Row([ft.Icon(icon, color=color), ft.Text(titulo, color=c["texto"])]),
            content=ft.Text(msg, color=c["texto_sec"]),
            actions=[ft.TextButton("OK", on_click=lambda e: page.close(dlg))]
        )
        page.open(dlg)

    def limpiar_formulario():
        c = obtener_tema()
        txt_cliente.value = ""
        txt_costo.value = ""
        sel_diseno[0] = False; sel_pedi[0] = False; sel_cejas[0] = False
        
        txt_hora_display.value = "Selecciona hora..."
        txt_hora_display.color = c["texto_sec"]
        lbl_imagen.value = "Sin diseño"
        lbl_imagen.color = c["texto_sec"]
        icono_img.color = c["acento"]
        id_en_edicion[0] = None
        ruta_imagen[0] = None
        hora_inicio[0] = None
        btn_guardar.text = "AGENDAR"
        btn_guardar.icon = "check"
        btn_cancelar.visible = False
        btn_sugerencia.visible = False 
        page.update()
        actualizar_estilos() 
        actualizar_sugerencia()

    def refrescar_todo():
        cargar_citas_en_grid()
        construir_cal_grande()
        actualizar_sugerencia()

    def verificar_choque(fecha, ini, fin, id_actual=None):
        fmt = "%I:%M %p"
        try:
            n_ini = datetime.datetime.strptime(ini, fmt)
            n_fin = datetime.datetime.strptime(fin, fmt)
            conn = sqlite3.connect("citas.db")
            cur = conn.cursor()
            cur.execute("SELECT id, hora_inicio, hora_fin FROM citas WHERE fecha=?", (fecha,))
            for cita in cur.fetchall():
                if id_actual is not None and cita[0] == id_actual: continue
                c_ini = datetime.datetime.strptime(cita[1], fmt)
                c_fin = datetime.datetime.strptime(cita[2], fmt)
                if n_ini < c_fin and n_fin > c_ini: return True
            return False
        except: return False

    # --- LÓGICA DE TIEMPO Y SERVICIOS ---
    
    def recalcular_finalizacion():
        if not hora_inicio[0]: return
        fmt = "%I:%M %p"
        try:
            dt_ini = datetime.datetime.strptime(hora_inicio[0], fmt)
            ahora = datetime.datetime.now()
            dt_ini = dt_ini.replace(year=ahora.year, month=ahora.month, day=ahora.day)
            
            duracion = 90
            if sel_diseno[0]: duracion += 60
            if sel_pedi[0]: duracion += 45
            if sel_cejas[0]: duracion += 60
            
            dt_fin = dt_ini + datetime.timedelta(minutes=duracion)
            hora_fin[0] = dt_fin.strftime(fmt)
            
            c = obtener_tema()
            txt_hora_display.value = f"{hora_inicio[0]} - {hora_fin[0]}"
            txt_hora_display.color = c["acento"]
            txt_hora_display.update()
        except: pass

    def toggle_servicio(estado_var):
        # 1. Cambiar estado
        estado_var[0] = not estado_var[0]
        
        # 2. Actualizar visualmente INMEDIATAMENTE
        actualizar_estilos() 
        page.update() # Forzar pintado antes de calcular
        
        # 3. Lógica de tiempo
        if hora_inicio[0]:
            recalcular_finalizacion()
        else:
            actualizar_sugerencia()

    def buscar_hueco(fecha):
        fmt = "%I:%M %p"
        try:
            conn = sqlite3.connect("citas.db")
            cur = conn.cursor()
            cur.execute("SELECT hora_inicio, hora_fin FROM citas WHERE fecha=?", (fecha,))
            citas = cur.fetchall()
            conn.close()
            
            duracion = 90
            if sel_diseno[0]: duracion += 60
            if sel_pedi[0]: duracion += 45
            if sel_cejas[0]: duracion += 60

            hora_test = datetime.datetime.strptime("07:00 AM", fmt)
            fin = datetime.datetime.strptime("10:00 PM", fmt)
            
            while hora_test + datetime.timedelta(minutes=duracion) <= fin:
                p_ini = hora_test
                p_fin = hora_test + datetime.timedelta(minutes=duracion)
                choca = False
                for c_ini, c_fin in citas:
                    try:
                        ci = datetime.datetime.strptime(c_ini, fmt)
                        cf = datetime.datetime.strptime(c_fin, fmt)
                        if p_ini < cf and p_fin > ci: choca = True; break
                    except: continue
                if not choca: return p_ini, p_fin
                hora_test += datetime.timedelta(minutes=30)
        except: pass
        return None, None

    def actualizar_sugerencia():
        if hora_inicio[0] is not None: 
            btn_sugerencia.visible = False
            btn_sugerencia.update()
            return

        ini, fin = buscar_hueco(fecha_elegida[0])
        c = obtener_tema()
        if ini:
            s_ini = ini.strftime("%I:%M %p")
            s_fin = fin.strftime("%I:%M %p")
            btn_sugerencia.text = f"✨ Recomendado: {s_ini}"
            btn_sugerencia.data = (s_ini, s_fin)
            btn_sugerencia.visible = True
            btn_sugerencia.style = ft.ButtonStyle(side=ft.BorderSide(1, c["acento"]))
            btn_sugerencia.color = c["acento"]
        else:
            btn_sugerencia.visible = False
        btn_sugerencia.update()

    def aplicar_sugerencia(e):
        ini, fin = e.control.data
        c = obtener_tema()
        hora_inicio[0] = ini
        hora_fin[0] = fin
        txt_hora_display.value = f"{ini} - {fin}"
        txt_hora_display.color = c["acento"]
        btn_sugerencia.visible = False 
        page.update()

    # --- CRUD ---
    def guardar_accion(e):
        if not txt_cliente.value: mostrar_alerta("Error", "Falta nombre", True); return
        if not hora_inicio[0]: mostrar_alerta("Error", "Falta hora", True); return
        if verificar_choque(fecha_elegida[0], hora_inicio[0], hora_fin[0], id_en_edicion[0]):
            mostrar_alerta("Ocupado", "Horario no disponible", True); return

        try:
            conn = sqlite3.connect("citas.db")
            cur = conn.cursor()
            img = ruta_imagen[0] if ruta_imagen[0] else ""
            if id_en_edicion[0] is None:
                cur.execute("INSERT INTO citas (cliente, costo, fecha, hora_inicio, hora_fin, imagen) VALUES (?, ?, ?, ?, ?, ?)",
                           (txt_cliente.value, txt_costo.value, fecha_elegida[0], hora_inicio[0], hora_fin[0], img))
                msg = "Agendado"
            else:
                cur.execute("UPDATE citas SET cliente=?, costo=?, fecha=?, hora_inicio=?, hora_fin=?, imagen=? WHERE id=?", 
                           (txt_cliente.value, txt_costo.value, fecha_elegida[0], hora_inicio[0], hora_fin[0], img, id_en_edicion[0]))
                msg = "Actualizado"
            conn.commit(); conn.close()
            
            limpiar_formulario()
            filtro_fecha[0] = fecha_elegida[0]
            refrescar_todo()
            mostrar_alerta("Éxito", msg, False)
        except Exception as ex: mostrar_alerta("Error", str(ex), True)

    def eliminar_accion(e):
        conn = sqlite3.connect("citas.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM citas WHERE id=?", (e.control.data,))
        conn.commit(); conn.close()
        refrescar_todo()
        mostrar_alerta("Listo", "Cita eliminada", False)

    def editar_accion(e):
        datos = e.control.data
        c = obtener_tema()
        id_en_edicion[0] = datos[0]
        txt_cliente.value = datos[1]
        txt_costo.value = datos[2]
        fecha_elegida[0] = datos[3]
        btn_fecha.text = datos[3]
        hora_inicio[0] = datos[4]; hora_fin[0] = datos[5]
        txt_hora_display.value = f"{datos[4]} - {datos[5]}"
        txt_hora_display.color = c["acento"]
        ruta_imagen[0] = datos[6]
        if datos[6]: lbl_imagen.value = "Diseño OK"; lbl_imagen.color = c["acento"]
        
        sel_diseno[0] = False; sel_pedi[0] = False; sel_cejas[0] = False
        
        btn_guardar.text = "ACTUALIZAR"; btn_guardar.icon = "update"
        btn_cancelar.visible = True
        btn_sugerencia.visible = False
        tabs_control.selected_index = 0
        tabs_control.update()
        page.update()
        actualizar_estilos()

    def ver_detalle(e):
        datos = e.control.data
        c = obtener_tema()
        img_w = ft.Icon("image_not_supported", size=50, color=c["texto_sec"])
        if datos[6] and os.path.exists(datos[6]):
            img_w = ft.Image(src=datos[6], width=300, height=300, fit=ft.ImageFit.CONTAIN)
        dlg = ft.AlertDialog(
            bgcolor=c["superficie"],
            title=ft.Text(datos[1], color=c["texto"], weight="bold", text_align="center"),
            content=ft.Column([
                ft.Container(img_w, alignment=ft.alignment.center),
                ft.Text(f"📅 {datos[3]}", color=c["texto_sec"]),
                ft.Text(f"⏰ {datos[4]} - {datos[5]}", color=c["texto_sec"]),
                ft.Text(f"💰 ${datos[2]}", color=c["acento"], weight="bold", size=20)
            ], height=350, width=300, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: page.close(dlg))]
        )
        page.open(dlg)

    def cargar_citas_en_grid():
        grid_citas.controls.clear()
        c = obtener_tema()
        conn = sqlite3.connect("citas.db")
        cur = conn.cursor()
        if filtro_fecha[0]:
            cur.execute("SELECT * FROM citas WHERE fecha=? ORDER BY id DESC", (filtro_fecha[0],))
            txt_titulo_lista.value = f"CITAS DEL {filtro_fecha[0]}"
            btn_ver_todas.visible = True
        else:
            cur.execute("SELECT * FROM citas ORDER BY id DESC")
            txt_titulo_lista.value = "TODAS LAS CITAS"
            btn_ver_todas.visible = False
        datos = cur.fetchall()
        if not datos and filtro_fecha[0]:
             grid_citas.controls.append(ft.Text("Sin citas este día", color=c["texto_sec"], italic=True))
        for fila in datos:
            tarjeta = ft.Container(
                bgcolor=c["superficie"], padding=12, border_radius=10,
                border=ft.border.all(1, c["borde"]),
                content=ft.Column([
                    ft.Container(
                        data=fila, on_click=ver_detalle,
                        content=ft.Column([
                            ft.Text(fila[1], weight="bold", color=c["texto"]),
                            ft.Text(f"📅 {fila[3]}", size=11, color=c["texto_sec"]),
                            ft.Text(f"⏰ {fila[4]} - {fila[5]}", size=11, color=c["acento"])
                        ])
                    ),
                    ft.Divider(height=5, color=c["borde"]),
                    ft.Row([
                        ft.IconButton("edit", icon_color=c["texto_sec"], icon_size=18, data=fila, on_click=editar_accion),
                        ft.IconButton("delete", icon_color="red", icon_size=18, data=fila[0], on_click=eliminar_accion)
                    ], alignment="spaceBetween")
                ])
            )
            grid_citas.controls.append(tarjeta)
        conn.close()
        txt_titulo_lista.color = c["texto_sec"]
        btn_ver_todas.style = ft.ButtonStyle(color=c["acento"])
        grid_citas.update()

    def resetear_filtro(e):
        filtro_fecha[0] = None
        cargar_citas_en_grid()
        page.update()

    # --- CALENDARIO GRANDE ---
    def construir_cal_grande():
        c = obtener_tema()
        grid_cal_grande.controls.clear()
        citas_mes = {}
        try:
            conn = sqlite3.connect("citas.db")
            cur = conn.cursor()
            patron = f"%/{cal_grande_estado['mes']:02d}/{cal_grande_estado['anio']}"
            cur.execute("SELECT fecha, cliente FROM citas WHERE fecha LIKE ?", (patron,))
            for f, nombre in cur.fetchall():
                if f not in citas_mes: citas_mes[f] = []
                citas_mes[f].append(nombre)
            conn.close()
        except: pass

        for d in ["L", "M", "M", "J", "V", "S", "D"]:
            grid_cal_grande.controls.append(ft.Container(content=ft.Text(d, color=c["acento"], weight="bold"), alignment=ft.alignment.center))

        cal = calendar.monthcalendar(cal_grande_estado['anio'], cal_grande_estado['mes'])
        for semana in cal:
            for dia in semana:
                if dia == 0:
                    grid_cal_grande.controls.append(ft.Container())
                else:
                    fecha_str = f"{dia:02d}/{cal_grande_estado['mes']:02d}/{cal_grande_estado['anio']}"
                    lista_nombres = citas_mes.get(fecha_str, [])
                    contenido_celda = ft.Column(spacing=2)
                    contenido_celda.controls.append(ft.Container(content=ft.Text(str(dia), weight="bold", color=c["texto"]), alignment=ft.alignment.center))
                    for nombre in lista_nombres:
                        nombre_corto = (nombre[:8] + '..') if len(nombre) > 8 else nombre
                        etiqueta = ft.Container(content=ft.Text(nombre_corto, size=10, color="black", no_wrap=True), bgcolor=c["acento"], border_radius=3, padding=2, alignment=ft.alignment.center)
                        contenido_celda.controls.append(etiqueta)
                    borde_celda = ft.border.all(1, c["borde"])
                    if fecha_str == datetime.datetime.now().strftime('%d/%m/%Y'):
                        borde_celda = ft.border.all(2, c["acento"])
                    celda = ft.Container(content=contenido_celda, bgcolor=c["celda_cal"], border=borde_celda, border_radius=5, padding=2, on_click=lambda e, f=fecha_str: ir_a_agenda_dia(f))
                    grid_cal_grande.controls.append(celda)
        
        nombres_mes = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        txt_mes_anio_grande.value = f"{nombres_mes[cal_grande_estado['mes']]} {cal_grande_estado['anio']}"
        txt_mes_anio_grande.color = c["texto"]
        grid_cal_grande.update(); txt_mes_anio_grande.update()

    def mover_cal_grande(delta):
        cal_grande_estado['mes'] += delta
        if cal_grande_estado['mes'] > 12: cal_grande_estado['mes']=1; cal_grande_estado['anio']+=1
        elif cal_grande_estado['mes'] < 1: cal_grande_estado['mes']=12; cal_grande_estado['anio']-=1
        construir_cal_grande()

    def ir_a_agenda_dia(fecha):
        filtro_fecha[0] = fecha
        cargar_citas_en_grid()
        tabs_control.selected_index = 0
        tabs_control.update()
        page.update()

    # --- CALENDARIO PEQUEÑO ---
    def construir_cal_peque():
        c = obtener_tema()
        cont_dias_cal.controls.clear()
        conteos = {}
        try:
            conn = sqlite3.connect("citas.db")
            cur = conn.cursor()
            patron = f"%/{cal_estado['mes']:02d}/{cal_estado['anio']}"
            cur.execute("SELECT fecha, COUNT(*) FROM citas WHERE fecha LIKE ? GROUP BY fecha", (patron,))
            conteos = {f[0]: f[1] for f in cur.fetchall()}
            conn.close()
        except: pass

        for d in ["L","M","M","J","V","S","D"]:
            cont_dias_cal.controls.append(ft.Container(content=ft.Text(d, color=c["texto_sec"], size=12, weight="bold"), alignment=ft.alignment.center))
        
        cal = calendar.monthcalendar(cal_estado['anio'], cal_estado['mes'])
        for sem in cal:
            for dia in sem:
                if dia == 0:
                    cont_dias_cal.controls.append(ft.Container())
                else:
                    f_str = f"{dia:02d}/{cal_estado['mes']:02d}/{cal_estado['anio']}"
                    cant = conteos.get(f_str, 0)
                    bg, tc = c["superficie"], c["texto"]
                    if cant >= 6: bg, tc = c["rojo"], "white"
                    elif cant >= 4: bg, tc = c["amarillo"], "black"
                    elif cant >= 1: bg, tc = c["verde"], "white"
                    bord = ft.border.all(2, c["acento"]) if f_str == fecha_elegida[0] else None
                    contenido_celda = ft.Column([ft.Text(str(dia), color=tc, weight="bold")], alignment="center", spacing=0)
                    if cant > 0: contenido_celda.controls.append(ft.Text(f"{cant} citas", color=tc, size=8))
                    cont_dias_cal.controls.append(ft.Container(content=contenido_celda, bgcolor=bg, border_radius=10, alignment=ft.alignment.center, height=45, width=45, border=bord, on_click=lambda e, f=f_str: seleccionar_fecha(f)))
        
        nom = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        txt_mes_anio.value = f"{nom[cal_estado['mes']]} {cal_estado['anio']}"
        txt_mes_anio.color = c["acento"]
    
    def mover_cal_peque(delta):
        cal_estado['mes'] += delta
        if cal_estado['mes'] > 12: cal_estado['mes']=1; cal_estado['anio']+=1
        elif cal_estado['mes'] < 1: cal_estado['mes']=12; cal_estado['anio']-=1
        construir_cal_peque()
        page.dialog.update()

    def seleccionar_fecha(f):
        fecha_elegida[0] = f
        btn_fecha.text = f
        filtro_fecha[0] = f
        cargar_citas_en_grid()
        page.dialog.open = False
        actualizar_sugerencia()
        page.update()

    def abrir_cal_peque(e):
        c = obtener_tema()
        construir_cal_peque()
        dlg = ft.AlertDialog(
            bgcolor=c["fondo"], content_padding=10,
            title=ft.Row([
                ft.IconButton("arrow_back_ios", icon_color=c["acento"], icon_size=15, on_click=lambda _: mover_cal_peque(-1)),
                txt_mes_anio,
                ft.IconButton("arrow_forward_ios", icon_color=c["acento"], icon_size=15, on_click=lambda _: mover_cal_peque(1))
            ], alignment="spaceBetween"),
            content=ft.Container(width=320, height=350, content=cont_dias_cal)
        )
        page.dialog = dlg
        page.open(dlg)

    # --- TIEMPO ---
    def calcular_horas(hora_obj):
        ahora = datetime.datetime.now()
        dt_inicio = datetime.datetime.combine(ahora.date(), hora_obj)
        
        duracion = 90
        if sel_diseno[0]: duracion += 60
        if sel_pedi[0]: duracion += 45
        if sel_cejas[0]: duracion += 60
        
        dt_fin = dt_inicio + datetime.timedelta(minutes=duracion)
        return dt_inicio.strftime("%I:%M %p"), dt_fin.strftime("%I:%M %p")

    def al_cambiar_hora(e):
        if time_picker.value:
            c = obtener_tema(); i, f = calcular_horas(time_picker.value)
            hora_inicio[0] = i; hora_fin[0] = f
            txt_hora_display.value = f"{i} - {f}"; txt_hora_display.color = c["acento"]
            page.update()
            
    def al_cambiar_opciones(e):
        if time_picker.value: al_cambiar_hora(None)
        if hora_inicio[0] is None: actualizar_sugerencia()

    def al_cargar_imagen(e):
        if e.files:
            c = obtener_tema(); ruta_imagen[0] = e.files[0].path
            lbl_imagen.value = "Diseño OK"; lbl_imagen.color = c["acento"]
            icono_img.color = c["acento"]; page.update()

    # --- BOTONES ---
    time_picker = ft.TimePicker(on_change=al_cambiar_hora, time_picker_entry_mode="dial")
    file_picker = ft.FilePicker(on_result=al_cargar_imagen)
    page.overlay.extend([time_picker, file_picker])

    btn_sugerencia = ft.ElevatedButton(text="Sugerir Hora", icon="auto_awesome", visible=False, on_click=aplicar_sugerencia)
    btn_fecha = ft.ElevatedButton(text=fecha_elegida[0], icon="calendar_month", height=45, on_click=abrir_cal_peque)
    btn_hora = ft.ElevatedButton("Hora", icon="access_time", height=45, on_click=lambda _: page.open(time_picker))
    btn_imagen = ft.Container(content=ft.Row([icono_img, lbl_imagen], alignment="center"), padding=10, border_radius=10, on_click=lambda _: file_picker.pick_files())
    btn_guardar = ft.ElevatedButton("AGENDAR", icon="check", height=50, on_click=guardar_accion)
    btn_cancelar = ft.TextButton("Cancelar", visible=False, icon="close", on_click=lambda _: limpiar_formulario())
    
    btn_ver_todas.on_click = resetear_filtro

    # --- TABS ---
    tabs_control = ft.Tabs(
        selected_index=0, animation_duration=300,
        tabs=[
            ft.Tab(
                text="AGENDAR", icon="edit_calendar",
                content=ft.Container(
                    padding=10,
                    content=ft.Column([
                        ft.Container(padding=20, content=ft.Column([
                            txt_cliente, txt_costo,
                            # Chips en Fila con ajuste automático y centrado
                            ft.Row([chip_diseno, chip_pedi, chip_cejas], wrap=True, spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                            
                            ft.Row([btn_fecha, btn_hora], alignment="spaceBetween"),
                            ft.Container(txt_hora_display, alignment=ft.alignment.center),
                            ft.Container(btn_sugerencia, alignment=ft.alignment.center),
                            ft.Divider(height=5, color="transparent"),
                            btn_imagen,
                            ft.Divider(height=10, color="transparent"),
                            ft.Column([btn_guardar, btn_cancelar], horizontal_alignment="stretch")
                        ])),
                        ft.Container(padding=ft.padding.symmetric(horizontal=25), content=ft.Row([txt_titulo_lista, btn_ver_todas], alignment="spaceBetween")),
                        grid_citas
                    ], scroll=ft.ScrollMode.AUTO)
                )
            ),
            ft.Tab(
                text="CALENDARIO", icon="calendar_month",
                content=ft.Container(
                    padding=10,
                    content=ft.Column([
                        ft.Row([
                            ft.IconButton("arrow_back_ios", on_click=lambda _: mover_cal_grande(-1)),
                            txt_mes_anio_grande,
                            ft.IconButton("arrow_forward_ios", on_click=lambda _: mover_cal_grande(1)),
                        ], alignment="center"),
                        grid_cal_grande
                    ])
                )
            ),
        ], expand=1
    )

    # --- ESTILOS ---
    def actualizar_estilos():
        c = obtener_tema()
        page.bgcolor = c["fondo"]; page.theme_mode = c["modo"]
        titulo_app.color = c["acento"]; btn_tema.icon = c["icono"]; btn_tema.icon_color = c["texto"]
        
        for t in [txt_cliente, txt_costo]:
            t.bgcolor = c["superficie"]; t.color = c["texto"]
            t.cursor_color = c["acento"]; t.focused_border_color = c["acento"]
            t.label_style = ft.TextStyle(color=c["texto_sec"]); t.prefix_icon_color = c["texto"]
            t.border_color = "transparent"
        
        # Estilos Chips Interactivos
        chips = [(ref_chip_diseno.current, sel_diseno[0]), (ref_chip_pedi.current, sel_pedi[0]), (ref_chip_cejas.current, sel_cejas[0])]
        for container, seleccionado in chips:
            if container:
                if seleccionado:
                    container.bgcolor = c["acento"]
                    container.content.color = "black" if estado_tema["actual"] == "oscuro" else "white"
                    container.border = None
                else:
                    container.bgcolor = "transparent"
                    container.content.color = c["texto"]
                    container.border = ft.border.all(1, c["acento"])

        txt_hora_display.color = c["acento"] if hora_inicio[0] else c["texto_sec"]
        lbl_imagen.color = c["acento"] if ruta_imagen[0] else c["texto_sec"]; icono_img.color = c["acento"]
        
        estilo_sec = ft.ButtonStyle(bgcolor=c["superficie"], color=c["acento"], shape=ft.RoundedRectangleBorder(radius=10))
        btn_fecha.style = estilo_sec; btn_hora.style = estilo_sec; btn_imagen.bgcolor = c["superficie"]
        btn_sugerencia.style = ft.ButtonStyle(side=ft.BorderSide(1, c["acento"])); btn_sugerencia.color = c["acento"]; btn_sugerencia.bgcolor = c["superficie"]
        btn_guardar.bgcolor = c["acento"]; btn_guardar.color = "black" if estado_tema["actual"] == "oscuro" else "white"
        btn_cancelar.style = ft.ButtonStyle(color=c["texto"])
        
        tabs_control.label_color = c["acento"]; tabs_control.unselected_label_color = c["texto_sec"]
        tabs_control.indicator_color = c["acento"]; tabs_control.divider_color = "transparent"
        page.theme = ft.Theme(color_scheme=ft.ColorScheme(primary=c["acento"], surface=c["superficie"], background=c["fondo"]), use_material3=True)

    def cambiar_tema_accion(e):
        estado_tema["actual"] = "claro" if estado_tema["actual"] == "oscuro" else "oscuro"
        actualizar_estilos(); refrescar_todo(); page.update()

    btn_tema.on_click = cambiar_tema_accion

    # --- MONTAJE ---
    actualizar_estilos()
    page.add(ft.Column([
        ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            content=ft.Row([
                logo_img, 
                titulo_app, 
                btn_tema
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        ),
        tabs_control
    ], expand=True))

    # Importante: llamar a actualizar_estilos DESPUÉS de añadir a la página para que las referencias funcionen
    actualizar_estilos()
    refrescar_todo()

# --- FIX FINAL PARA THREADS ---
if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
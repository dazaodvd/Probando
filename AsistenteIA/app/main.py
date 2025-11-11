import flet as ft
from .config import Config
from .ia_core import IACore
from .voice_module import VoiceModule
import threading
import asyncio # Se usa para el sleep asíncrono en los diálogos
import string # Se usa para limpiar el prompt del usuario

# Inicializar módulos
config = Config()
# NOTA: La inicialización de la IA Core puede tomar tiempo o fallar si la clave es incorrecta.
try:
    # Intenta inicializar el IACore
    ai_core = IACore() 
    print("✅ Módulo de IA Core inicializado.")
except Exception as e:
    print(f"Error al inicializar IACore: {e}")
    ai_core = None # Marcar como fallido
    
voice_module = VoiceModule()


# Definir colores de fallback (para burbujas si el esquema falla)
DEFAULT_USER_COLOR = ft.Colors.BLUE_GREY_600
DEFAULT_ASSISTANT_COLOR = ft.Colors.BLUE_GREY_800


# --- REFERENCIAS GLOBALES (SOLO PARA LOS CAMPOS DE TEXTO) ---
txt_assistant_name_ref = ft.Ref[ft.TextField]()
txt_gemini_key_ref = ft.Ref[ft.TextField]()
txt_ai_model_ref = ft.Ref[ft.TextField]()


def main(page: ft.Page):
    """Función principal que crea la interfaz Flet."""
    
    # 1. Configuración de Ventana y Tema Base 
    page.title = config.ASSISTANT_NAME 
    page.window_width = 400
    page.window_height = 700
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    
    # Definir temas
    page.theme = ft.Theme(color_scheme_seed="blue")
    page.dark_theme = ft.Theme(color_scheme_seed="blue_grey")
    page.theme_mode = ft.ThemeMode.DARK if config.THEME == "dark" else ft.ThemeMode.LIGHT
    
    # 2. Inicializar la página para cargar los temas antes de leerlos (SOLUCIÓN AL AttributeError)
    page.update() 
    
    # 3. OBTENER EL ESQUEMA DE COLOR ACTIVO CON FALLBACK SEGURO
    current_theme = page.dark_theme if page.theme_mode == ft.ThemeMode.DARK else page.theme
    
    # Definir variables de color seguro (Fallback)
    scheme_primary = ft.Colors.BLUE 
    scheme_surface = ft.Colors.GREY_900 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.WHITE
    scheme_input = ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_200
    scheme_primary_container = ft.Colors.BLUE_GREY_700
    scheme_secondary_container = ft.Colors.GREY_700
    
    try:
        current_scheme = current_theme.color_scheme
        scheme_primary = current_scheme.primary
        scheme_surface = current_scheme.surface
        scheme_input = current_scheme.surface_container_low
        scheme_primary_container = current_scheme.primary_container
        scheme_secondary_container = current_scheme.secondary_container
    except AttributeError:
        pass # Usamos los fallbacks si el esquema no carga a tiempo.

    # --- Funciones de Configuración y Diálogo ---
    
    def change_theme(e):
        """Cambia el modo de tema, lo guarda en config.py y actualiza la página."""
        new_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        page.theme_mode = new_mode
        config.THEME = "dark" if new_mode == ft.ThemeMode.DARK else "light"
        config.save_config()
        page.drawer.open = False
        page.update() 
        
    def open_drawer(e):
        """Abre el panel de configuración."""
        page.drawer.open = True
        page.update()
        
    def close_drawer(e):
        """Cierra el drawer para la opción 'Acerca de...'"""
        page.drawer.open = False
        page.update()
        
    def close_bottom_sheet(e):
        """Cierra el BottomSheet y actualiza la página."""
        page.bottom_sheet.open = False
        page.update()
        
    # --- LÓGICA DE GUARDADO DEL DIÁLOGO ---
    settings_dialog_title_control = ft.Text("Ajustes del Asistente") 

    def save_settings(e):
        """Guarda los valores del diálogo, actualiza la IA y cierra el BottomSheet."""
        
        # 1. Obtener valores de los campos
        new_key = txt_gemini_key_ref.current.value.strip()
        new_model = txt_ai_model_ref.current.value.strip()
        new_name = txt_assistant_name_ref.current.value.strip()
        
        if not new_key or len(new_key) < 5: 
            # Actualiza el control de título en el diálogo
            settings_dialog_title_control.value = "❌ Clave Requerida"
            settings_dialog_title_control.color = ft.Colors.RED
            page.update()
            return
            
        # 2. Intentar actualizar la IA y la configuración
        success = config.update_ai_core(new_name, new_key, new_model, ai_core)
        
        if success:
            # 3. Cerrar diálogo (Bottom Sheet) y actualizar UI
            page.bottom_sheet.open = False 
            page.appbar.title = ft.Text(new_name, weight=ft.FontWeight.BOLD)
            page.update()
        else:
            # 4. Mostrar error si la clave es inválida
            settings_dialog_title_control.value = "❌ Clave Inválida. Verifique la API."
            settings_dialog_title_control.color = ft.Colors.RED
            page.update()
            
    # --- DEFINICIÓN DEL CONTENIDO DE AJUSTES (REUTILIZADO) ---
    dialog_content = ft.Container(
        ft.Column(
            [
                ft.Text("Nombre del Asistente:"),
                ft.TextField(ref=txt_assistant_name_ref),
                
                ft.Text("Clave de Gemini API:"),
                ft.TextField(ref=txt_gemini_key_ref, password=True, can_reveal_password=True),
                
                ft.Text("Modelo de IA:"),
                ft.TextField(ref=txt_ai_model_ref),
            ],
            tight=True,
            scroll=ft.ScrollMode.ADAPTIVE
        )
    )
    
    # --- COMPONENTE CREATIVO: BottomSheet (Reemplaza a ft.AlertDialog) ---
    settings_bottom_sheet = ft.BottomSheet(
        content=ft.Container(
            ft.Column(
                [
                    # TÍTULO DEL DIÁLOGO (Ahora dentro del BottomSheet)
                    ft.Row(
                        [
                            settings_dialog_title_control,
                            # ÍCONO DE CERRAR USANDO CADENA DE TEXTO
                            ft.IconButton(
                                icon="close", 
                                on_click=close_bottom_sheet 
                            ) 
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Divider(),
                    
                    dialog_content, # Contenido de los campos de texto
                    
                    # ACCIONES / BOTONES
                    ft.Row(
                        [
                            ft.TextButton("Cancelar", on_click=close_bottom_sheet),
                            ft.TextButton("Guardar y Aplicar", on_click=save_settings)
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    )
                ],
                tight=True
            ),
            padding=20,
            width=min(page.window_width, 600) 
        ),
    )


    # Función que cierra el menú lateral y abre el diálogo. (CON PAUSA MÍNIMA)
    async def close_drawer_and_open_settings(e):
        page.drawer.open = False
        page.update() 
    
        # 2. Pausa asíncrona: Permite que el cierre del Drawer se complete sin bloquear la UI.
        await asyncio.sleep(0.05) # <--- Uso de la pausa asíncrona correcta
    
        # 3. Abre el diálogo
        await open_settings_dialog(e)
    
        
    async def open_settings_dialog(e): 
     """Muestra el BottomSheet de configuración con un solo update para mayor estabilidad."""
    
     # 1. Resetear el título (si hay errores previos)
     settings_dialog_title_control.value = "Ajustes del Asistente"
     settings_dialog_title_control.color = None
    
     # 2. ASIGNAR el BottomSheet a la página. ESTO ES CRUCIAL.
     page.bottom_sheet = settings_bottom_sheet 
    
     # 3. Abrir el BottomSheet.
     page.bottom_sheet.open = True

     # 4. ÚNICO UPDATE: Renderiza el BottomSheet y hace accesibles las referencias (ft.Ref.current)
     page.update() 
    
     # 5. Cargar valores DESPUÉS DEL PRIMER UPDATE: Ya es seguro acceder a los ft.Ref
     # Esta debe ser la última acción de carga.
     txt_assistant_name_ref.current.value = config.ASSISTANT_NAME
     txt_gemini_key_ref.current.value = config.GEMINI_API_KEY
     txt_ai_model_ref.current.value = config.AI_MODEL
    
     # 6. SEGUNDO UPDATE (Solo para mostrar los valores cargados)
     page.update()
        
    # --- CONTENEDOR DE CHAT (DEFINICIÓN FALTANTE) ---
    chat_container = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
    )
    # ----------------------------------------------------------------
    
    thinking_indicator = ft.ProgressRing(width=16, height=16, visible=False)

    listening_indicator = ft.Text(
        "Escuchando...",
        visible=False,
        weight=ft.FontWeight.BOLD,
        color=scheme_primary 
    )
    
    # Función para añadir mensajes
    def add_message(text, is_user, speak_message=True):
        bubble_color = scheme_secondary_container
        
        if is_user:
            bubble_color = scheme_primary_container

        message_bubble = ft.Container(
            content=ft.Text(text, selectable=True),
            padding=10,
            border_radius=ft.border_radius.all(15), 
            bgcolor=bubble_color,
            width=300,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                offset=ft.Offset(0, 1),
                blur_style=ft.ShadowBlurStyle.NORMAL,
            ),
        )
        
        if is_user:
            avatar = ft.CircleAvatar(content=ft.Text("TÚ"), bgcolor=ft.Colors.CYAN_800)
            chat_content = [message_bubble, avatar]
            alignment = ft.MainAxisAlignment.END
        else:
            # USO LA CADENA DE TEXTO EN EL ICONO DEL ASISTENTE
            avatar = ft.CircleAvatar(content=ft.Icon("smart_toy"), color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_700)
            chat_content = [avatar, message_bubble]
            alignment = ft.MainAxisAlignment.START

        chat_container.controls.append(
            ft.Row(
                chat_content,
                alignment=alignment,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        )
        page.update()
        page.scroll_to(offset=-1)
        
        if not is_user and speak_message:
            voice_module.speak(text)

    # Funciones de Lógica de Chat y Voz
    def process_message(user_input):
     if not user_input: return

     # 1. Mostrar el mensaje del usuario (usando el texto original)
     add_message(user_input, is_user=True, speak_message=False)
     text_input.value = ""
     page.update()
    
     thinking_indicator.visible = True
     page.update()

     # --- LÓGICA DE LIMPIEZA CLAVE ---
     # Convertir a minúsculas y eliminar puntuación para que coincida con actions.py
     # IMPORTANTE: No se aplica limpieza si se detecta una ruta de archivo
     is_file_command = user_input.lower().startswith("carga documento") or user_input.lower().startswith("aprende de")
     
     if is_file_command:
        cleaned_input = user_input # Se pasa la ruta tal cual
     else:
        cleaned_input = user_input.lower().translate(str.maketrans('', '', string.punctuation)).strip()

     # Usar el texto limpio para la lógica de la IA/Comandos
     assistant_response = ai_core.get_response(cleaned_input) 
        
     add_message(assistant_response, is_user=False, speak_message=True)
        
     thinking_indicator.visible = False
     page.update()

    def send_message_click(e):
        user_input = text_input.value.strip()
        threading.Thread(target=process_message, args=(user_input,)).start()

    def listen_and_send(e):
        # USO LA CADENA DE TEXTO EN EL ICONO DEL MIC
        mic_button.icon = "mic_none" 
        listening_indicator.visible = True 
        page.update()
        
        def run_voice_input():
            mic_button.disabled = True
            page.update()
            
            recognized_text = voice_module.listen()
            
            # USO LA CADENA DE TEXTO EN EL ICONO DEL MIC
            mic_button.icon = "mic_sharp"
            mic_button.disabled = False
            listening_indicator.visible = False
            
            if recognized_text and recognized_text not in ["No se pudo entender el audio.", "Error en el servicio de reconocimiento de voz:"]:
                process_message(recognized_text)
            elif "No se pudo entender" in recognized_text:
                 add_message("Lo siento, no logré entender lo que dijiste.", is_user=False, speak_message=False)
            
            page.update()

        threading.Thread(target=run_voice_input).start()

    # Interfaz de entrada (TextField y Botones)
    text_input = ft.TextField(
        hint_text="Escribe tu mensaje o comando...",
        expand=True,
        border=ft.InputBorder.NONE,
        content_padding=ft.padding.only(left=10),
        on_submit=send_message_click 
    )

    mic_button = ft.IconButton(
        icon="mic_sharp", # <-- CORRECCIÓN A STRING
        on_click=listen_and_send
    )

    # --- LÓGICA DE SELECCIÓN DE ARCHIVOS (FilePicker) ---
    
    def pick_files_result(e: ft.FilePickerResultEvent):
        """Maneja el resultado del diálogo de selección de archivos."""
        if e.files:
            # Obtenemos la ruta del primer archivo seleccionado
            file_path = e.files[0].path
            
            # Formateamos el mensaje para el IACore
            command_prompt = f"carga documento \"{file_path}\"" 
            
            # Establecemos el texto de entrada y llamamos a la función de envío
            text_input.value = command_prompt
            send_message_click(None) # Enviar el comando automáticamente
            
            page.update()
            
    # Configuración del diálogo de archivos (No visible, solo se muestra al llamar)
    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    
    # Añadir el diálogo de archivos a la página (es un control de superposición)
    page.overlay.append(pick_files_dialog)
    
    # --- Panel de Configuración Lateral (ft.Drawer) y AppBar ---
    
    page.drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(height=12),
            ft.Container(
                content=ft.Text("⚙️ Configuración del Asistente", size=18, weight=ft.FontWeight.BOLD),
                padding=ft.padding.only(left=15, top=5, bottom=5)
            ),
            ft.Divider(),
            # Opción de cambio de tema
            ft.ListTile(
                leading=ft.Icon("brightness_4_outlined"), 
                title=ft.Text("Cambiar Tema"),
                subtitle=ft.Text(f"Modo actual: {'Oscuro' if page.theme_mode == ft.ThemeMode.DARK else 'Claro'}"),
                on_click=change_theme
            ),
            # Opción de Ajustes Avanzados
            ft.ListTile(
                leading=ft.Icon("settings"), 
                title=ft.Text("Ajustes Avanzados"),
                on_click=close_drawer_and_open_settings,
            ),
            # Opción de Acerca de
            ft.ListTile(
                leading=ft.Icon("info_outline"), 
                title=ft.Text("Acerca de..."),
                on_click=close_drawer,
            ),
        ]
    )
    
    page.appbar = ft.AppBar(
        title=ft.Text(config.ASSISTANT_NAME, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=scheme_surface,
        actions=[
            ft.IconButton(
                icon="settings",
                tooltip="Configuración",
                on_click=open_drawer 
            )
        ]
    )

    # --- Contenedor estilizado para la fila de entrada ---
    input_row = ft.Container(
        content=ft.Row(
            controls=[
                # --- BOTÓN DE ARCHIVO CORREGIDO: Usando cadena de texto ---
                ft.IconButton(
                    icon="attach_file", # <--- CORRECCIÓN CLAVE: Usamos cadena de texto para compatibilidad
                    tooltip="Cargar documento (PDF/TXT) para Aprendizaje Local",
                    on_click=lambda _: pick_files_dialog.pick_files(
                        allow_multiple=False, # Solo un archivo a la vez
                        allowed_extensions=["pdf", "txt"], # Filtro de extensiones
                        dialog_title="Seleccionar documento para el asistente"
                    ),
                    icon_color=scheme_primary
                ),
                mic_button,
                text_input,
                ft.IconButton(
                    icon="send", # <--- CORRECCIÓN A STRING
                    on_click=send_message_click
                )
            ],
            spacing=5,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        padding=ft.padding.only(left=5, right=5, top=2, bottom=2),
        margin=ft.margin.only(bottom=10),
        bgcolor=scheme_input, # Color seguro
        border_radius=ft.border_radius.all(25),
        width=page.window_width - 20
    )
    
    # Añadir todos los componentes a la página
    page.add(
        ft.Container(
            content=chat_container,
            padding=ft.padding.only(top=0, left=10, right=10, bottom=0),
            expand=True
        ),
        ft.Column(
            [
                ft.Row( 
                    [
                        listening_indicator
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                ft.Row( 
                    [
                        thinking_indicator,
                        input_row
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

if __name__ == "__main__":
    if ai_core:
        ft.app(
            target=main, 
            view=ft.AppView.FLET_APP 
        )
    else:
        print("La aplicación Flet no puede iniciar debido a un error de inicialización de la IA.")
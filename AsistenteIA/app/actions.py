import subprocess
import platform
import os 
import time

class SystemActions:
    """Maneja la ejecución de comandos locales basados en el texto del usuario."""

    def __init__(self):
        self.os_name = platform.system()
        print(f"Sistema Operativo detectado: {self.os_name}") 

    def execute_command(self, command_text: str) -> bool:
        """
        Intenta mapear y ejecutar un comando de acción local.
        Devuelve True si se ejecutó una acción local, False en caso contrario.
        """
        command_text = command_text.lower().strip()

        # ---COMANDOS DE ABRIR APLICACIONES---
        # El orden es importante. Las frases más específicas deben ir primero.

        if "abre la calculadora" in command_text:
            # Comando para Windows (calc), Linux (gnome-calculator), macOS (open -a Calculator)
            return self._open_app("Calculadora", ["calc", "gnome-calculator", "open -a Calculator"])
        
        elif "abre el navegador" in command_text or "abre chrome" in command_text:
            return self._open_app("Navegador Web", ["start chrome", "google-chrome", "open -a 'Google Chrome'"])

        elif "abre word" in command_text or "abre microsoft word" in command_text:
            return self._open_app("Microsoft Word", ["winword", "libreoffice --writer", "open -a 'Microsoft Word'"])

        elif "abre excel" in command_text or "abre microsoft excel" in command_text:
            return self._open_app("Microsoft Excel", ["excel", "libreoffice --calc", "open -a 'Microsoft Excel'"])

        elif "abre el explorador de archivos" in command_text or "abre mis documentos" in command_text:
            return self._open_app("Explorador de Archivos", ["explorer", "nautilus", "open -a Finder"])
        
        elif "abre el bloc de notas" in command_text or "abre notepad" in command_text:
            return self._open_app("Bloc de Notas", ["notepad", "gedit", "open -a TextEdit"])
        
        elif "abre la terminal" in command_text or "abre cmd" in command_text:
            # Usar 'start' es esencial para abrir una nueva ventana de terminal
            return self._open_app("Terminal", ["start cmd", "gnome-terminal", "open -a Terminal"])

        # --- 2. COMANDOS DE CONFIGURACIÓN DE WINDOWS (ms-settings) ---
        # Estos comandos solo funcionan en Windows.
        if self.os_name == "Windows":
            if "abre la configuración de red" in command_text or "ajustes de wifi" in command_text:
                return self._open_settings("Configuración de Red", "ms-settings:network") 

            elif "abre la configuración de bluetooth" in command_text or "ajustes de bluetooth" in command_text:
                return self._open_settings("Configuración de Bluetooth", "ms-settings:bluetooth") 

            elif "abre la configuración de pantalla" in command_text or "ajustes de pantalla" in command_text:
                return self._open_settings("Configuración de Pantalla", "ms-settings:display") 

            elif "abre la configuración de sonido" in command_text or "ajustes de sonido" in command_text:
                return self._open_settings("Configuración de Sonido", "ms-settings:sound") 

            elif "abre la configuración" in command_text or "abre los ajustes" in command_text:
                # Este es el comando genérico y debe ir al final de las configuraciones
                return self._open_settings("Configuración general", "ms-settings:") 
            

   
     # --- FUNCIONES AUXILIARES ---
    def _open_app(self, app_name: str, commands: list) -> bool:
        """Intenta abrir una aplicación y devuelve True si la ejecución fue iniciada."""
        
        cmd = ""
        # Asignación del comando basado en el OS (commands[0]=Win, [1]=Lin, [2]=Mac)
        if self.os_name == "Windows":
            cmd_base = commands[0] 
        
            cmd = f"start {cmd_base}" 
            # os.system es más confiable en Windows para comandos simples
            execution_method = lambda: os.system(cmd)
        
        elif self.os_name == "Linux":
            cmd = commands[1]
            execution_method = lambda: subprocess.Popen(cmd.split(), start_new_session=True)
        
        elif self.os_name == "Darwin": # macOS
            cmd = commands[2]
            execution_method = lambda: subprocess.Popen(cmd.split(), start_new_session=True)
        
        else:
            print(f"Sistema operativo '{self.os_name}' no soportado para esta aplicación.")
            return False

        # Ejecución del comando
        try:
            execution_method()
            print(f"✅ COMANDO LOCAL EJECUTADO: Abriendo {app_name} con '{cmd}'")
            return True 
            
        except FileNotFoundError:
            # Fallo en encontrar el ejecutable (ej: no tienes Word instalado)
            print(f"❌ ERROR: Aplicación no encontrada en la ruta. Comando: '{cmd}'.")
            return False 
        except Exception as e:
            print(f"❌ ERROR al ejecutar el comando '{cmd}': {e}")
            return False

    def _open_settings(self, setting_name: str, ms_settings_command: str):
        """
        Abre una sección específica de configuración en Windows usando el protocolo ms-settings.
        """
        # Esta función solo se usa desde el bloque 'if self.os_name == "Windows":'
        cmd = f"start {ms_settings_command}"
        try:
            os.system(cmd)
            print(f"✅ COMANDO LOCAL EJECUTADO: Abriendo {setting_name} con '{cmd}'")
            return True
        except Exception as e:
            print(f"❌ ERROR al ejecutar el ajuste '{cmd}': {e}")
            return False
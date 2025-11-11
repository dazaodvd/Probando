import pyttsx3
import speech_recognition as sr
import threading
import time 


class VoiceModule:
    def __init__(self):
        # 1. Configuración de parámetros
        self.rate = 150
        self.volume = 1.0
        self.language = "es" 
        self.voice_gender = "male" 

        # 2. Inicialización SÓLO del reconocedor (STT)
        self.recognizer = sr.Recognizer()
        
    def _configure_engine(self, engine):
        """Configura un motor TTS recién inicializado."""
        engine.setProperty('rate', self.rate)
        engine.setProperty('volume', self.volume)
        
        voices = engine.getProperty('voices')
        selected_voice = None
        
        for voice in voices:
            if self.language in voice.languages and self.voice_gender in voice.id.lower():
                selected_voice = voice
                break
        
        if selected_voice is None:
            for voice in voices:
                if any(self.language in lang for lang in voice.languages):
                    selected_voice = voice
                    break
        
        if selected_voice:
            engine.setProperty('voice', selected_voice.id)
        else:
            print(f"Advertencia: Voz no encontrada para {self.voice_gender} en {self.language}. Usando la voz por defecto.")

    # --- FUNCIÓN CRÍTICA 1: Hilo de un solo uso (TTS) ---
    def _speak_in_thread(self, text):
        """
        Inicializa el motor, dice el texto y lo destruye. 
        Esto se ejecuta en un hilo nuevo por cada mensaje.
        """
        try:
            # 1. Inicializar el motor TTS (dentro del hilo)
            engine = pyttsx3.init()
            self._configure_engine(engine)
            
            # 2. Decir el mensaje
            engine.say(text)
            
            # 3. Bloquear y reproducir (solo afecta a este hilo)
            engine.runAndWait()
            
        except Exception as e:
            print(f"Error fatal en el hilo de voz TTS: {e}")
        finally:
            # 4. Destruir el motor para liberar recursos
            try:
                engine.stop()
                engine.endLoop() # Asegura que se limpie la cola de eventos
            except:
                pass

    # --- FUNCIÓN CRÍTICA 2: El método speak (Iniciador) ---
    def speak(self, text):
        """Crea un hilo temporal para reproducir el texto sin bloquear la interfaz."""
        if text:
            # Creamos un hilo nuevo para cada mensaje que va a hablar
            tts_thread = threading.Thread(target=self._speak_in_thread, args=(text,))
            tts_thread.daemon = True
            tts_thread.start()

    # --- El método listen() se mantiene estable ---
    def listen(self):
        """Escucha la entrada de micrófono y la convierte en texto."""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("Escuchando...")
            try:
                # Aumentamos el timeout para un comportamiento más robusto
                audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=15) 
            except sr.WaitTimeoutError:
                return "No se pudo detectar voz en el tiempo límite."
            except Exception as e:
                return f"Error al escuchar: {e}"

        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
            print(f"Usuario dijo: {text}")
            return text
        except sr.UnknownValueError:
            return "No se pudo entender el audio."
        except sr.RequestError as e:
            return f"Error en el servicio de reconocimiento de voz: {e}"
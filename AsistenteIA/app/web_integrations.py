import requests
from .config import Config

class WebIntegrations:
    """Maneja las conexiones con APIs web externas (Clima, etc.)."""
    
    def __init__(self):
        self.config = Config()

    def get_weather(self, city: str) -> str:
        """Consulta la API del clima para la ciudad especificada."""
        api_key = self.config.WEATHER_API_KEY
        base_url = self.config.WEATHER_BASE_URL
        
        if not api_key:
            return "Lo siento, la clave API del clima no está configurada en .env."

        params = {
            'q': city,
            'appid': api_key,
            'units': 'metric', 
            'lang': self.config.LANGUAGE
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data and data.get("main"):
                temp = data['main']['temp']
                desc = data['weather'][0]['description']
                
                return (f"El clima actual en {city} es de {temp}°C, "
                        f"con {desc}.")
            else:
                return f"No pude encontrar información del clima para {city}."
                
        except requests.exceptions.HTTPError as err:
            if response.status_code == 404:
                return f"No se encontró la ciudad '{city}'."
            return f"Error HTTP al obtener el clima: {err}"
        except Exception as e:
            return f"Ocurrió un error inesperado al consultar el clima: {e}"
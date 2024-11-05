import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración del bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("No se encontró TELEGRAM_TOKEN en variables de entorno")

# Configuración de Bitso
DEFAULT_PAIRS = ['btc_mxn', 'eth_mxn', 'xrp_mxn']
UPDATE_INTERVAL = 60  # minutos

# Configuración de la API
BITSO_API_URL = "https://api.bitso.com/v3"

# Modo debug
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
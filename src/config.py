import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    """Configuración relacionada con el bot de Telegram"""
    token: str
    welcome_message: str = """
¡Hola! 👋 Soy el Bot de test de rama de precios de Bitso

Comandos disponibles:
/precio - Ver precios actuales 💰
/activar - Activar actualizaciones automáticas ⚡
/desactivar - Desactivar actualizaciones 🚫
/ayuda - Mostrar este mensaje de ayuda ℹ️
    """

@dataclass
class BitsoConfig:
    """Configuración relacionada con la API de Bitso"""
    api_base_url: str
    trading_pairs: List[str]
    update_interval: int 

@dataclass
class Config:
    """Configuración global de la aplicación"""
    bot: BotConfig
    bitso: BitsoConfig
    debug: bool

def load_config() -> Config:
    """
    Carga y valida la configuración desde variables de entorno
    
    Returns:
        Config: Objeto con toda la configuración validada
    
    Raises:
        ValueError: Si falta alguna variable de entorno requerida
    """
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        raise ValueError("No se encontró TELEGRAM_TOKEN en variables de entorno")

    bot_config = BotConfig(
        token=token
    )

    # Configuración de Bitso
    bitso_config = BitsoConfig(
        api_base_url="https://api.bitso.com/v3",
        trading_pairs=['btc_mxn', 'eth_mxn', 'xrp_mxn', 'sol_mxn', 'usdt_mxn'],
        update_interval=int(os.getenv('UPDATE_INTERVAL', '1'))  
    )

    # Configuración global
    return Config(
        bot=bot_config,
        bitso=bitso_config,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )

config = load_config()
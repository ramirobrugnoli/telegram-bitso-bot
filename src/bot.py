import logging
from typing import Set, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import requests
import threading
import schedule
import time
from telegram.ext import Updater, CommandHandler
from .config import config

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if not config.debug else logging.DEBUG
)
logger = logging.getLogger(__name__)

@dataclass
class PriceInfo:
    """Almacena información sobre el precio de una criptomoneda"""
    current_price: float
    last_price: Optional[float]
    last_update: datetime

class BitsoPriceClient:
    """Cliente para obtener precios de Bitso"""
    
    def __init__(self):
        self.base_url = config.bitso.api_base_url
        self.price_history: Dict[str, PriceInfo] = {}
        
    def get_price(self, book: str) -> Optional[PriceInfo]:
        """Obtiene el precio actual y lo compara con el anterior"""
        try:
            response = requests.get(f"{self.base_url}/ticker/", params={'book': book})
            response.raise_for_status()
            data = response.json()
            
            if data['success']:
                current_price = float(data['payload']['last'])
                
                # Obtener información anterior del precio
                last_info = self.price_history.get(book)
                
                # Crear nueva información de precio
                new_info = PriceInfo(
                    current_price=current_price,
                    last_price=last_info.current_price if last_info else None,
                    last_update=datetime.now()
                )
                
                # Actualizar historial
                self.price_history[book] = new_info
                
                return new_info
            
            logger.error(f"Error en respuesta de Bitso: {data}")
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo precio de {book}: {str(e)}")
            return None

class BitsoTelegramBot:
    """Bot de Telegram para mostrar precios de Bitso"""
    
    def __init__(self):
        """Inicializa el bot con la configuración"""
        self.price_client = BitsoPriceClient()
        self.updater = Updater(config.bot.token, use_context=True)
        self.dp = self.updater.dispatcher
        self.chats_activos: Set[int] = set()
        
        # Registrar manejadores de comandos
        self._register_handlers()
        
    def _register_handlers(self):
        """Registra todos los manejadores de comandos"""
        commands = {
            'start': self.cmd_start,
            'ayuda': self.cmd_start,  # Mismo manejador que start
            'precio': self.cmd_precio,
            'activar': self.cmd_activar,
            'desactivar': self.cmd_desactivar
        }
        
        for command, callback in commands.items():
            self.dp.add_handler(CommandHandler(command, callback))
    
    def get_price_change_emoji(self, price_info: PriceInfo) -> tuple[str, str, str]:
        """
        Determina el emoji, texto de variación y color según el cambio de precio
        
        Returns:
            tuple[str, str, str]: (emoji, texto de variación, emoji de tendencia)
        """
        if not price_info or not price_info.last_price:
            return "🆕","",""
            
        change = ((price_info.current_price - price_info.last_price) / price_info.last_price) * 100
        
        # Si el cambio es muy cercano a 0 (menos de 0.01%), lo tratamos como sin cambio
        if abs(change) < 0.01:
            return "→", "(0.00%)", ""
            
        # Tendencia para cambios significativos
        trend_emoji = "📈" if change > 0 else "📉"
        
        if abs(change) < 0.1:
            return "→", f"({change:+.2f}%)", trend_emoji
        elif change > 0:
            if change > 5:
                return "⤊", f"({change:+.2f}%)", trend_emoji
            else:
                return "↗️", f"({change:+.2f}%)", trend_emoji
        else:
            if change < -5:
                return "⤋", f"({change:.2f}%)", trend_emoji
            else:
                return "↘️", f"({change:.2f}%)", trend_emoji

    def format_price_message(self) -> str:
        """Formatea el mensaje con los precios actuales y sus variaciones"""
        crypto_emojis = {
            'BTC': '₿',
            'ETH': '⟠',
            'XRP': '✘',
            'MANA': '🌐',
            'ADA': '⟁',
            'SOL': '◎',
            'USDT': '₮',
            'DOT': '●',
            'MATIC': '⬡',
            'USDC': '₵'
        }

        mensaje = "💰 Precios actuales en Bitso:\n\n"
        
        for pair in config.bitso.trading_pairs:
            price_info = self.price_client.get_price(pair)
            if price_info:
                crypto = pair.split('_')[0].upper()
                emoji = crypto_emojis.get(crypto, '🪙')
                
                # Obtener emoji, texto de variación y tendencia
                change_emoji, change_text, trend_emoji = self.get_price_change_emoji(price_info)
                
                # Solo agregar el emoji de tendencia si hay un cambio significativo
                trend_display = f" {trend_emoji}" if trend_emoji else ""
                
                mensaje += (
                    f"{crypto} {emoji}: ${price_info.current_price:,.2f} MXN "
                    f"{change_emoji}{trend_display}{change_text}\n"
                )
            else:
                crypto = pair.split('_')[0].upper()
                emoji = crypto_emojis.get(crypto, '🪙')
                mensaje += f"{emoji} {crypto}: No disponible ❌\n"
        
        mensaje += f"\nÚltima actualización: {datetime.now().strftime('%H:%M:%S')}"
        return mensaje
    
    def cmd_start(self, update, context):
        """Maneja los comandos /start y /ayuda"""
        update.message.reply_text(config.bot.welcome_message)
        
    def cmd_precio(self, update, context):
        """Maneja el comando /precio"""
        mensaje = self.format_price_message()
        update.message.reply_text(mensaje)
        
    def cmd_activar(self, update, context):
        """Maneja el comando /activar"""
        chat_id = update.effective_chat.id
        
        if chat_id in self.chats_activos:
            update.message.reply_text("⚠️ Las actualizaciones automáticas ya están activadas.")
            return
            
        self.chats_activos.add(chat_id)
        update.message.reply_text(
            f"✅ Actualizaciones automáticas activadas.\n"
            f"Recibirás precios cada {config.bitso.update_interval} minutos."
        )
        
    def cmd_desactivar(self, update, context):
        """Maneja el comando /desactivar"""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.chats_activos:
            update.message.reply_text("⚠️ Las actualizaciones automáticas ya están desactivadas.")
            return
            
        self.chats_activos.discard(chat_id)
        update.message.reply_text("❌ Actualizaciones automáticas desactivadas.")
        
    def enviar_actualizacion(self):
        """Envía actualizaciones de precios a todos los chats activos"""
        if not self.chats_activos:
            return
            
        mensaje = self.format_price_message()
        
        for chat_id in list(self.chats_activos):  # Usar lista para evitar modificación durante iteración
            try:
                self.updater.bot.send_message(chat_id=chat_id, text=mensaje)
                logger.debug(f"Actualización enviada a {chat_id}")
            except Exception as e:
                logger.error(f"Error enviando mensaje a {chat_id}: {str(e)}")
                # Si el chat ya no existe o el bot fue expulsado, lo removemos
                if "bot was blocked by the user" in str(e) or "chat not found" in str(e):
                    self.chats_activos.discard(chat_id)
                    
    def run_schedule(self):
        """Ejecuta el planificador de tareas en un hilo separado"""
        schedule.every(config.bitso.update_interval).minutes.do(self.enviar_actualizacion)
        
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    def run(self):
        """Inicia el bot"""
        try:
            logger.info("Iniciando bot...")
            
            # Iniciar planificador en un hilo separado
            threading.Thread(target=self.run_schedule, daemon=True).start()
            
            # Iniciar el bot
            self.updater.start_polling()
            logger.info("Bot iniciado exitosamente!")
            
            # Mantener el bot corriendo
            self.updater.idle()
            
        except Exception as e:
            logger.error(f"Error al iniciar el bot: {str(e)}")
            raise

def main():
    """Función principal"""
    bot = BitsoTelegramBot()
    bot.run()

if __name__ == '__main__':
    main()
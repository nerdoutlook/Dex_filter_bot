
import os
import re
import asyncio
import logging
import time
import random
from typing import Dict, List, Callable, Awaitable, Optional

from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from dotenv import load_dotenv

from models import MonitoringSource

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramMonitor:
    def __init__(self):
        self.api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        self.api_hash = os.getenv("TELEGRAM_API_HASH", "")
        self.phone = os.getenv("TELEGRAM_PHONE", "")
        self.session_path = os.path.join(os.path.dirname(__file__), "solana_token_hawk.session")

        if not self.api_id or not self.api_hash or not self.phone:
            logger.error("Telegram API credentials not set in .env file")
            self.client = None
            return

        try:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
            logger.info(f"Telegram client initialized with session: {self.session_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            self.client = None

        self.sources: Dict[str, MonitoringSource] = {}
        self.source_entities: Dict[str, any] = {}
        self.token_pattern = re.compile(r'([A-HJ-NP-Za-km-z1-9]{32,44})')
        self.token_handler: Optional[Callable[[str, str], Awaitable[None]]] = None
        self.found_tokens = set()
        self.connection_requests: Dict[str, Dict] = {}

    async def start(self):
        """Start the Telegram client and monitoring"""
        if not self.client:
            logger.error("Telegram client not initialized")
            return

        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                logger.info(f"Authorization required for {self.phone}")
                await self._authorize_client_interactively()
            else:
                logger.info("Telegram client already authorized")

            @self.client.on(events.NewMessage)
            async def message_handler(event):
                entity = await event.get_chat()
                source_id = self.get_source_id_from_entity(entity)
                if not source_id or self.sources[source_id].status != "active":
                    return
                await self.check_message_for_tokens(event.text, self.sources[source_id].name)

            logger.info("Message handler registered")

            for source_id, source in self.sources.items():
                if source.status == "active":
                    await self.connect_to_source(source_id, source)

            await self.client.run_until_disconnected()
        except FloodWaitError as e:
            retry_time = time.strftime('%H:%M:%S UTC', time.gmtime(time.time() + e.seconds))
            logger.error(f"Rate limit hit: Waiting {e.seconds} seconds until {retry_time} before retrying")
            await asyncio.sleep(e.seconds)
            await self.start()
        except Exception as e:
            logger.error(f"Error starting Telegram monitor: {e}")

    async def _authorize_client_interactively(self):
        """Handle Telegram client authorization interactively"""
        try:
            sent_code = await self.client.send_code_request(self.phone)
            code = input(f"Enter the code sent to {self.phone}: ").strip()
            try:
                await self.client.sign_in(self.phone, code, phone_code_hash=sent_code.phone_code_hash)
                logger.info("Telegram client authorized successfully")
            except SessionPasswordNeededError:
                password = input(f"Two-step verification enabled. Enter your password for {self.phone}: ").strip()
                await self.client.sign_in(password=password)
                logger.info("Telegram client authorized successfully with password")
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            raise

    async def stop(self):
        """Disconnect the Telegram client"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("Telegram client disconnected")

    def set_token_handler(self, handler: Callable[[str, str], Awaitable[None]]):
        self.token_handler = handler

    def add_source(self, source: MonitoringSource):
        self.sources[source.id] = source
        if self.client and self.client.is_connected():
            asyncio.create_task(self.connect_to_source(source.id, source))

    def remove_source(self, source_id: str):
        if source_id in self.sources:
            del self.sources[source_id]
        if source_id in self.source_entities:
            del self.source_entities[source_id]

    def update_source_status(self, source_id: str, active: bool):
        if source_id in self.sources:
            self.sources[source_id].status = "active" if active else "paused"

    async def connect_to_source(self, source_id: str, source: MonitoringSource):
        try:
            entity = await self.client.get_entity(source.name)
            self.source_entities[source_id] = entity
            logger.info(f"Connected to source: {source.name}")
        except ValueError as e:
            logger.error(f"Invalid Telegram handle {source.name}: {e}")
        except Exception as e:
            logger.error(f"Error connecting to source {source.name}: {e}")

    async def check_message_for_tokens(self, text: str, source_name: str):
        if not text:
            return
        matches = self.token_pattern.findall(text)
        for token_address in matches:
            if token_address in self.found_tokens:
                continue
            from solders.pubkey import Pubkey
            try:
                Pubkey.from_string(token_address)
            except ValueError:
                logger.warning(f"Invalid token address found: {token_address} in {source_name}")
                continue
            logger.info(f"Found potential token address: {token_address} in {source_name}")
            self.found_tokens.add(token_address)
            if self.token_handler:
                await self.token_handler(token_address, source_name)

    def get_source_id_from_entity(self, entity) -> Optional[str]:
        for source_id, source_entity in self.source_entities.items():
            if entity.id == source_entity.id:
                return source_id
        return None

    async def connect_api(self, api_id: str, api_hash: str, phone_number: str, user_id: str) -> Dict:
        try:
            session_name = f'user_{user_id}_{int(time.time())}'
            client = TelegramClient(session_name, int(api_id), api_hash)
            await client.connect()
            phone_code_hash = await client.send_code_request(phone_number)
            self.connection_requests[user_id] = {
                "client": client,
                "phone": phone_number,
                "phone_code_hash": phone_code_hash.phone_code_hash,
                "session": session_name
            }
            return {
                "success": True,
                "message": "Verification code sent to your phone",
                "phone_code_hash": phone_code_hash.phone_code_hash
            }
        except Exception as e:
            logger.error(f"Error in connect_api: {e}")
            return {"success": False, "message": str(e)}

    async def verify_code(self, code: str, phone_code_hash: str, user_id: str) -> Dict:
        if user_id not in self.connection_requests:
            return {"success": False, "message": "No active connection request found"}
        request_data = self.connection_requests[user_id]
        client = request_data["client"]
        phone = request_data["phone"]
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            me = await client.get_me()
            self.connection_requests[user_id]["me"] = me
            return {
                "success": True,
                "message": "Successfully connected to Telegram",
                "user": {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name
                }
            }
        except SessionPasswordNeededError:
            return {"success": False, "message": "Two-step verification required"}
        except Exception as e:
            logger.error(f"Error in verify_code: {e}")
            return {"success": False, "message": str(e)}

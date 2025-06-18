import os
import json
import asyncio
import aiohttp
import logging
from cachetools import TTLCache
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)

AUTH_URL = os.getenv("AUTH_URL", "https://jwtxthug.up.railway.app/token")
CACHE_DURATION = timedelta(hours=7).seconds
TOKEN_REFRESH_THRESHOLD = timedelta(hours=6).seconds

class TokenCache:
    def __init__(self, servers_config: dict):
        self.cache = TTLCache(maxsize=100, ttl=CACHE_DURATION)
        self.last_refresh = {}
        self.servers_config = servers_config
        self.lock = asyncio.Lock()

    async def get_tokens(self, server_key: str):
        async with self.lock:
            now = datetime.utcnow().timestamp()
            needs_refresh = (
                server_key not in self.cache or
                server_key not in self.last_refresh or
                (now - self.last_refresh.get(server_key, 0)) > TOKEN_REFRESH_THRESHOLD
            )

            if needs_refresh:
                await self._refresh_tokens(server_key)
                self.last_refresh[server_key] = now

            return self.cache.get(server_key, [])

    async def _refresh_tokens(self, server_key: str):
        try:
            creds = await self._load_credentials(server_key)
            tokens = []

            async with aiohttp.ClientSession() as session:
                tasks = []
                for user in creds:
                    params = {'uid': user['uid'], 'password': user['password']}
                    url = f"{AUTH_URL}?uid={user['uid']}&password={user['password']}"
                    tasks.append(self._fetch_token(session, url, user['uid'], server_key))

                results = await asyncio.gather(*tasks)
                tokens = [token for token in results if token]

            if tokens:
                self.cache[server_key] = tokens
                logger.info(f"✅ {server_key}: {len(tokens)} টি টোকেন সফলভাবে রিফ্রেশ হয়েছে।")
            else:
                logger.warning(f"⚠️ {server_key}: কোনো টোকেন পাওয়া যায়নি। cache খালি করা হচ্ছে।")
                self.cache[server_key] = []

        except Exception as e:
            logger.error(f"❌ Token refresh error for {server_key}: {str(e)}")
            if server_key not in self.cache:
                self.cache[server_key] = []

    async def _fetch_token(self, session, url, uid, server_key):
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("token")
                else:
                    logger.warning(f"🔴 {uid} ({server_key}): Token fetch failed ({response.status})")
        except Exception as e:
            logger.error(f"❌ Error fetching token for {uid} ({server_key}): {str(e)}")
        return None

    async def _load_credentials(self, server_key: str):
        try:
            # Priority 1: ENVIRONMENT VARIABLE
            config_data = os.getenv(f"{server_key}_CONFIG")
            if config_data:
                return json.loads(config_data)

            # Priority 2: Local config file
            base_path = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(base_path, 'config', f'{server_key.lower()}_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"⚠️ Config not found for {server_key}: {config_path}")
                return []
        except Exception as e:
            logger.error(f"❌ Credential load error for {server_key}: {str(e)}")
            return []

def get_headers(token: str):
    return {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB49"
    }

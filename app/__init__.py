# app/__init__.py

import os
import logging
from flask import Flask, request

from .token_manager import TokenCache
from .like_routes import initialize_routes

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app init
app = Flask(__name__)

# Server config
SERVERS = {
    "EUROPE": os.getenv("EUROPE_SERVER", "https://clientbp.ggblueshark.com"),
    "IND": os.getenv("IND_SERVER", "https://client.ind.freefiremobile.com"),
    "BR": os.getenv("BR_SERVER", "https://client.us.freefiremobile.com"),
}

# Token manager init (now fully async-compatible if token_manager is async)
token_cache = TokenCache(servers_config=SERVERS)

# Optional: handle chunked transfer for some hostings like Vercel
@app.before_request
def handle_chunking():
    if "chunked" in request.headers.get("Transfer-Encoding", "").lower():
        request.environ["wsgi.input_terminated"] = True

# ❌ Removed preload_tokens() to avoid cold-start timeout in Render/Vercel

# ✅ Initialize routes
initialize_routes(app, SERVERS, token_cache)

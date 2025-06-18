# app/__init__.py

from flask import Flask, request
import os
import logging
from datetime import timedelta

from .token_manager import TokenCache
from .like_routes import like_bp, initialize_routes

# Flask app init
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server config
SERVERS = {
    "EUROPE": os.getenv("EUROPE_SERVER", "https://clientbp.ggblueshark.com"),
    "IND": os.getenv("IND_SERVER", "https://client.ind.freefiremobile.com"),
    "BR": os.getenv("BR_SERVER", "https://client.us.freefiremobile.com"),
}

# Token manager init
token_cache = TokenCache(servers_config=SERVERS)

# Optional: handle chunked transfer
@app.before_request
def handle_chunking():
    if "chunked" in request.headers.get("Transfer-Encoding", "").lower():
        request.environ["wsgi.input_terminated"] = True

# ❌ Remove preload_tokens() to avoid timeout on cold start
# def preload_tokens():
#     for server in SERVERS:
#         token_cache.get_tokens(server)

# preload_tokens()  <-- timeout dey

# Initialize routes
initialize_routes(app, SERVERS, token_cache)

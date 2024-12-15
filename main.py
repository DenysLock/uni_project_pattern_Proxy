from fastapi import FastAPI, HTTPException
import requests
import redis
from datetime import datetime

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0)

BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price?symbol="
CACHE_EXPIRY = 10
LOG_FILE = "crypto_requests.log"


def log_event(event: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {event}\n")


@app.get("/crypto/{symbol}")
async def get_crypto_price(symbol: str):
    symbol = symbol.upper()
    cache_key = f"crypto:{symbol}"

    cached_price = redis_client.get(cache_key)
    if cached_price:
        log_event(f"Returned cached price for {symbol}: {cached_price.decode()}")
        return {"symbol": symbol, "price": cached_price.decode(), "source": "cache"}

    try:
        response = requests.get(BINANCE_API_URL + symbol)
        response.raise_for_status()
        price_data = response.json()
        price = price_data.get("price")

        if not price:
            raise HTTPException(status_code=404, detail="Price not found")

        redis_client.setex(cache_key, CACHE_EXPIRY, price)

        log_event(f"Requested price for {symbol} from Binance: {price}")

        return {"symbol": symbol, "price": price, "source": "binance"}

    except requests.RequestException as e:
        log_event(f"Failed to fetch price for {symbol} from Binance: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch price from Binance")

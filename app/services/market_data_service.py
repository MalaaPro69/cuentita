import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


CRYPTO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "USDT": "tether",
    "USDC": "usd-coin",
}


def _get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Cuentita/1.0"})
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def obtener_cotizacion(simbolo: str) -> dict | None:
    """Obtiene una cotizacion en USD; devuelve None si el proveedor no reconoce el activo."""
    codigo = simbolo.strip().upper()
    if not codigo:
        return None

    try:
        if codigo in CRYPTO_IDS:
            crypto_id = quote(CRYPTO_IDS[codigo])
            data = _get_json(
                "https://api.coingecko.com/api/v3/simple/price"
                f"?ids={crypto_id}&vs_currencies=usd&include_24hr_change=true"
            )
            quote_data = data.get(CRYPTO_IDS[codigo])
            if quote_data and quote_data.get("usd") is not None:
                return {
                    "simbolo": codigo,
                    "precio_usd": float(quote_data["usd"]),
                    "variacion_24h": quote_data.get("usd_24h_change"),
                    "proveedor": "CoinGecko",
                }

        data = _get_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(codigo)}?range=1d&interval=1d"
        )
        result = data.get("chart", {}).get("result", [])
        meta = result[0].get("meta", {}) if result else {}
        if meta.get("currency") not in (None, "USD"):
            return None
        precio = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
        anterior = meta.get("chartPreviousClose")
        if precio is not None:
            variacion = ((float(precio) - float(anterior)) / float(anterior) * 100) if anterior else None
            return {
                "simbolo": codigo,
                "precio_usd": float(precio),
                "variacion_24h": variacion,
                "proveedor": "Yahoo Finance",
            }
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError, json.JSONDecodeError):
        return None

    return None

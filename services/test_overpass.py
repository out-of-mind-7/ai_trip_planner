import httpx

urls = [
    "https://overpass.kumi.systems/api/status",
    "https://overpass-api.de/api/status",
    "https://overpass.nchc.org.tw/api/status",
    "https://overpass.private.coffee/api/status",
]

for url in urls:
    try:
        response = httpx.get(url, timeout=10)
        print(url, response.status_code)
        print(response.text[:150])
    except httpx.RequestError as error:
        print(url, type(error).__name__, str(error))
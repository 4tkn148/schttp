# schttp
This library is not meant for production use.
 
```bash
pip install -U git+https://github.com/h0nde/schttp
```

```python
from schttp import HTTPClient

with HTTPClient(timeout=5) as http:
    resp = http.request("GET", "https://httpbin.org/get")
    print(
        f"Status: {resp.status}\n"
        f"Message: {resp.message}\n"
        f"Body length: {len(resp.body)}\n"
        f"Headers: {', '.join(resp.headers.keys())}"
    )
```

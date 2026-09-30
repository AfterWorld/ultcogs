"""Maintainer utility: download original, unmodified Commons photos."""
import hashlib
import json
import runpy
import urllib.request
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).parent
candies = runpy.run_path(str(root / "content.py"))["CANDIES"]
(root / "photos").mkdir(exist_ok=True)
credits = []
for key, candy in candies.items():
    filename = candy["source"].replace(" ", "_")
    digest = hashlib.md5(filename.encode()).hexdigest()
    url = f"https://upload.wikimedia.org/wikipedia/commons/{digest[0]}/{digest[:2]}/{quote(filename)}"
    destination = root / "photos" / candy["file"]
    if destination.exists():
        data = destination.read_bytes()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "GuessCandyCog/1.0 (real-photo Discord candy game)"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    if not data.startswith(b"\xff\xd8\xff"):
        raise ValueError(f"Expected JPEG for {key}")
    destination.write_bytes(data)
    credits.append(dict(candy=key, filename=candy["file"], original=url,
                        source="https://commons.wikimedia.org/wiki/File:" + quote(candy["source"]),
                        author=candy["author"], license=candy["license"],
                        license_url=candy.get("license_url"), changes="None; original bytes preserved",
                        sha256=hashlib.sha256(data).hexdigest()))
    print(f"{key}: {len(data)} bytes")
(root / "photos" / "credits.json").write_text(json.dumps(credits, indent=2), encoding="utf-8")

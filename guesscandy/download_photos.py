"""Maintainer utility: download original, unmodified Commons photos."""
import hashlib
import json
import html
import re
import runpy
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).parent
candies = runpy.run_path(str(root / "content.py"))["CANDIES"]
(root / "photos").mkdir(exist_ok=True)
credits = []
previous_path = root / "photos" / "credits.json"
previous = {item["filename"]: item for item in json.loads(previous_path.read_text(encoding="utf-8"))}
addition_ids = {row[0] for row in runpy.run_path(str(root / "content.py"))["ADDITIONS"]}


def fetch(url):
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "GuessCandyCog/1.1 (Discord candy game; Wikimedia photo attribution)"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 502, 503) or attempt == 3:
                raise
            time.sleep(15 * (attempt + 1))


for key, candy in candies.items():
    filename = candy["source"].replace(" ", "_")
    digest = hashlib.md5(filename.encode()).hexdigest()
    url = f"https://upload.wikimedia.org/wikipedia/commons/{digest[0]}/{digest[:2]}/{quote(filename)}"
    original_url = url
    destination = root / "photos" / candy["file"]
    source = "https://commons.wikimedia.org/wiki/File:" + quote(candy["source"])
    actual_license = candy["license"]
    license_url = candy.get("license_url")
    changes = "None; original bytes preserved"
    if key in addition_ids:
        page = html.unescape(fetch(source).decode())
        licenses = re.findall(r'class="licensetpl_short"[^>]*>(.*?)</span>', page, re.S)
        licenses = [re.sub(r'<[^>]+>', '', value).strip() for value in licenses]
        supported = ("Public domain", "CC0", "CC BY-SA 3.0")
        if "Evan-Amos" not in page or not any(value in supported for value in licenses):
            raise ValueError(f"Unverified author/license for {key}: {licenses}")
        actual_license = next(value for value in supported if value in licenses)
        license_url = {"CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
                       "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/"}.get(actual_license)
        thumbnails = re.findall(r'(?:href|src)="(https://[^\"]*960px-[^\"]+)"', page)
        if not destination.exists():
            if not thumbnails:
                raise ValueError(f"No standard 960px preview available for {key}")
            url = thumbnails[0]
            changes = "Wikimedia 960px preview; resized from original, no other edits"
        time.sleep(1)
    if destination.exists():
        data = destination.read_bytes()
        if candy["file"] in previous:
            changes = previous[candy["file"]]["changes"]
            url = previous[candy["file"]].get("download", previous[candy["file"]]["original"])
        elif len(data) < 200000 and key in addition_ids:
            changes = "Wikimedia 960px preview; resized from original, no other edits"
            url = thumbnails[0]
    else:
        data = fetch(url)
    if not data.startswith(b"\xff\xd8\xff"):
        raise ValueError(f"Expected JPEG for {key}")
    destination.write_bytes(data)
    credits.append(dict(candy=key, filename=candy["file"], original=original_url, download=url,
                        source=source, author=candy["author"], license=actual_license,
                        license_url=license_url, changes=changes,
                        sha256=hashlib.sha256(data).hexdigest()))
    print(f"{key}: {len(data)} bytes; {actual_license}", flush=True)
    previous[candy["file"]] = credits[-1]
    previous_path.write_text(json.dumps(list(previous.values()), indent=2) + "\n", encoding="utf-8", newline="\n")
(root / "photos" / "credits.json").write_text(json.dumps(credits, indent=2) + "\n", encoding="utf-8", newline="\n")

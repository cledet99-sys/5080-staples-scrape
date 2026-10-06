# Staples RTX 5080 Stock Monitor

This monitors Staples item **24764611**, the Zotac SOLID OC RTX 5080 White Edition:

https://www.staples.com/zotac-solid-oc-nvidia-geforce-rtx-5080-pci-express-5-0-16gb-gddr7-gaming-graphics-card-2640mhz-white-zt-b50800q-10a/product_24764611

It uses Playwright because Staples renders parts of the product page dynamically.

## What it does

- Checks the exact product page every 2 minutes by default.
- Looks for a real purchase control such as **Add to cart**.
- Requires that the page is not simultaneously reporting **Out of stock**.
- Saves the last state locally.
- Sends a push notification only when the state changes from unavailable -> available.
- Includes the Staples product link in the notification.

## Phone notifications with ntfy

1. Install the **ntfy** app on your phone.
2. Pick a long, hard-to-guess topic name, e.g. a random 30+ character string.
3. Subscribe to that topic in the app.
4. Set the same topic as an environment variable on the computer running the scraper:

macOS/Linux:
```bash
export NTFY_TOPIC="your-long-random-topic"
python staples_5080_monitor.py
```

Windows PowerShell:
```powershell
$env:NTFY_TOPIC="your-long-random-topic"
python staples_5080_monitor.py
```

Do not use a public/easy-to-guess topic name.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Then:

```bash
python staples_5080_monitor.py
```

## Change the checking frequency

The default is 120 seconds:

```bash
export CHECK_INTERVAL_SECONDS=60
```

I would start at 120 seconds rather than hammering Staples with requests.

## Run continuously

### macOS/Linux

Use `screen`, `tmux`, or a system service. For a simple overnight run:

```bash
nohup python staples_5080_monitor.py > monitor.log 2>&1 &
```

### Important

Retail sites can change their HTML or deploy anti-bot protections. If Staples changes the product-page controls, the detection rules in `check_page()` may need to be updated.

# NetShow

[![CI](https://github.com/imrezafattahi/NetShow/actions/workflows/ci.yml/badge.svg)](https://github.com/imrezafattahi/NetShow/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Ping, HTTP, TLS certificates and host resources, watched by one small Python service.

**[English](#english) · [فارسی](#فارسی) · [Setup guide / راهنمای نصب](https://imrezafattahi.github.io/NetShow/)**

---

## English

NetShow checks a handful of hosts and websites every minute, stores the results in SQLite, and serves them as JSON plus a single-page dashboard. The whole interface, and this README, exist in English and Persian, and you can switch language while using it.

### What it watches

| Check | Reports |
| --- | --- |
| Ping (ICMP) | Latency and packet loss |
| HTTP / HTTPS | Status code and response time |
| TLS | Days left before the certificate expires |
| Host | Processor, memory, disk, network throughput |
| Alerts | Optional Telegram message on outage, recovery and certificate warnings |

### Quick start

```bash
git clone https://github.com/imrezafattahi/NetShow.git
cd NetShow
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open <http://127.0.0.1:8000>. On Windows activate with `.venv\Scripts\activate`.

### Configuration

Edit `config.json`. A ping target needs `host`, an HTTP target needs `url`.

```json
{
  "interval_seconds": 60,
  "history_days": 7,
  "targets": [
    { "name": "Home router", "kind": "ping", "host": "192.168.1.1" },
    { "name": "My site", "kind": "http", "url": "https://example.com" }
  ],
  "alerts": { "fail_threshold": 2, "ssl_warn_days": 14 }
}
```

TLS expiry is checked automatically for every `https` URL. Telegram credentials are read from the environment, never from the config file:

```bash
export NETSHOW_TELEGRAM_TOKEN="123456:AA..."
export NETSHOW_TELEGRAM_CHAT_ID="987654321"
```

### API

| Endpoint | Returns |
| --- | --- |
| `GET /api/health` | Service liveness and version |
| `GET /api/status` | Full snapshot: system metrics, targets with recent history, latest events |
| `GET /api/history?target=NAME&hours=24` | Raw samples for one target |
| `GET /api/events?limit=50` | Outages, recoveries, certificate warnings |
| `POST /api/run` | Force a check cycle now |

FastAPI also generates interactive docs at `/docs` while the service runs.

### Docker

```bash
docker compose up -d
```

The image installs `iputils-ping` so ICMP checks work inside the container.

### Tests

```bash
pytest -q
```

GitHub Actions runs the same suite on Python 3.11 and 3.12 for every push.

### Layout

```
app/main.py        FastAPI app and API routes
app/config.py      config.json and environment variables
app/db.py          SQLite storage and queries
app/scheduler.py   the check loop
app/alerts.py      Telegram notifications
app/checks/        ping, http, tls, host metrics
app/static/        the dashboard
docs/index.html    setup guide, published with GitHub Pages
tests/             pytest suite
```

Licensed under MIT.

---

## فارسی

<div dir="rtl">

NetShow یک سرویس کوچک پایتونی است که هر دقیقه چند سرور و وب‌سایت را بررسی می‌کند، نتیجه را در SQLite ذخیره می‌کند و آن را هم به شکل JSON و هم به شکل یک داشبورد تک‌صفحه‌ای ارائه می‌دهد. کل رابط کاربری و همین فایل، فارسی و انگلیسی دارند و زبان را می‌توانید در حین استفاده عوض کنید.

### چه چیزهایی پایش می‌شود

| بررسی | خروجی |
| --- | --- |
| پینگ (ICMP) | تأخیر و افت بسته |
| HTTP / HTTPS | کد پاسخ و زمان پاسخ |
| TLS | روزهای باقی‌مانده تا انقضای گواهی |
| میزبان | پردازنده، حافظه، دیسک، ترافیک شبکه |
| هشدار | پیام تلگرام اختیاری برای قطعی، بازگشت و نزدیک شدن انقضای گواهی |

### شروع سریع

</div>

```bash
git clone https://github.com/imrezafattahi/NetShow.git
cd NetShow
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

<div dir="rtl">

سپس آدرس <http://127.0.0.1:8000> را باز کنید. در ویندوز برای فعال‌سازی محیط مجازی از `.venv\Scripts\activate` استفاده کنید.

### تنظیمات

فایل `config.json` را ویرایش کنید. هدف پینگ به `host` نیاز دارد و هدف HTTP به `url`. انقضای گواهی TLS برای هر آدرس `https` خودکار بررسی می‌شود.

توکن تلگرام فقط از متغیرهای محیطی خوانده می‌شود و هرگز نباید در فایل تنظیمات یا مخزن قرار بگیرد:

</div>

```bash
export NETSHOW_TELEGRAM_TOKEN="123456:AA..."
export NETSHOW_TELEGRAM_CHAT_ID="987654321"
```

<div dir="rtl">

### مسیرهای API

| مسیر | خروجی |
| --- | --- |
| `GET /api/health` | زنده بودن سرویس و نسخه |
| `GET /api/status` | وضعیت کامل: منابع سیستم، اهداف با تاریخچه‌ی اخیر، آخرین رخدادها |
| `GET /api/history?target=NAME&hours=24` | نمونه‌های خام یک هدف |
| `GET /api/events?limit=50` | قطعی‌ها، بازگشت‌ها و هشدارهای گواهی |
| `POST /api/run` | اجرای فوری یک چرخه‌ی بررسی |

### داکر و تست

با `docker compose up -d` پروژه بالا می‌آید؛ ایمیج پکیج `iputils-ping` را نصب می‌کند تا بررسی ICMP داخل کانتینر کار کند. تست‌ها با `pytest -q` اجرا می‌شوند و GitHub Actions همان تست‌ها را روی پایتون ۳.۱۱ و ۳.۱۲ اجرا می‌کند.



</div>

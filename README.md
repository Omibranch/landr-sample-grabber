# LANDR Sample Grabber

<p align="center">
  <img src="https://i.imgur.com/7up7x8N.jpeg" alt="LANDR Sample Grabber" width="480"/>
</p>

**English** | [Русский](#русский)

---

## English

A Playwright-based scraper that automates downloading sample packs from [LANDR Samples](https://samples.landr.com). It clicks every Play button across all paginated pages, intercepts the 206 audio stream, and saves each file under its real name as shown on the site.

### Features

- Extracts real filenames from `span[data-original]` — no more `drums (1).mp3`
- Automatically detects file extension (`.mp3` / `.wav` / `.flac`) from the stream URL
- Full pagination support
- Resume support — skips already-downloaded files via `_manifest.json`
- Unique filename collision handling (`Name (1).mp3`, `Name (2).mp3` …)
- Retry logic — 3 attempts per stream + 3 attempts per download
- End-of-run stats: `downloaded / skipped / failed`
- Proxy support (HTTP with auth)

### Requirements

```
python >= 3.10
playwright
python-dotenv
```

```bash
pip install playwright python-dotenv
playwright install chromium
```

### Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```ini
# .env
PROXY_SERVER=http://host:port   # leave empty to connect directly
PROXY_USER=username
PROXY_PASS=password
```

Other settings are at the top of `main.py`:

| Variable | Default | Description |
|---|---|---|
| `DOWNLOAD_DIR` | `landr_samples` | Output folder |
| `PAGE_LOAD_DELAY` | `8000` | Wait after page load (ms) |
| `SAMPLE_CLICK_DELAY` | `0.3` | Pause between clicks (s) |
| `MAX_RETRIES` | `3` | Retry attempts |
| `TEST_MODE_2_ONLY` | `False` | Download only 2 files (debug) |

### Usage

```bash
python main.py
# Enter the LANDR Pack URL: https://samples.landr.com/packs/ambient-drum-loops
```

Files are saved to `landr_samples/`. A `_manifest.json` is written alongside them — delete it to force a full re-download.

---

## Русский

<a id="русский"></a>

Скрипт на Playwright для автоматической загрузки сэмпл-паков с [LANDR Samples](https://samples.landr.com). Нажимает каждую кнопку Play на всех страницах пагинации, перехватывает 206 аудиопоток и сохраняет файлы с реальными именами как на сайте.

### Возможности

- Берёт реальные имена файлов из `span[data-original]` — никакого `drums (1).mp3`
- Автоматически определяет расширение (`.mp3` / `.wav` / `.flac`) из URL потока
- Полная поддержка пагинации
- Возобновление — уже скачанные файлы пропускаются через `_manifest.json`
- Разрешение коллизий имён (`Name (1).mp3`, `Name (2).mp3` …)
- Ретрай — 3 попытки поймать поток + 3 попытки скачать файл
- Статистика в конце: `downloaded / skipped / failed`
- Поддержка HTTP-прокси с авторизацией

### Требования

```
python >= 3.10
playwright
python-dotenv
```

```bash
pip install playwright python-dotenv
playwright install chromium
```

### Настройка

Скопируй `.env.example` в `.env` и заполни:

```bash
cp .env.example .env
```

```ini
# .env
PROXY_SERVER=http://host:port   # оставь пустым для прямого подключения
PROXY_USER=username
PROXY_PASS=password
```

Остальные настройки — в начале `main.py`:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DOWNLOAD_DIR` | `landr_samples` | Папка для файлов |
| `PAGE_LOAD_DELAY` | `8000` | Ожидание загрузки страницы (мс) |
| `SAMPLE_CLICK_DELAY` | `0.3` | Пауза между кликами (с) |
| `MAX_RETRIES` | `3` | Попыток при ошибке |
| `TEST_MODE_2_ONLY` | `False` | Скачать только 2 файла (отладка) |

### Использование

```bash
python main.py
# Enter the LANDR Pack URL: https://samples.landr.com/packs/ambient-drum-loops
```

Файлы сохраняются в `landr_samples/`. Рядом создаётся `_manifest.json` — удали его, чтобы форсировать повторное скачивание.

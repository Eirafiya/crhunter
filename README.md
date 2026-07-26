# CRHunter

Automated property alert monitor — tracks new listings and status changes across major Irish housing providers.

## Features

- Monitors 6 providers (central portal + 5 individual sites)
- Detects: new listings, status changes, deadline updates, bedroom updates
- Email alerts via [Resend](https://resend.com) (free tier)
- Static dashboard via GitHub Pages
- Runs every 3 hours on GitHub Actions — zero infrastructure cost

## Quick Start

### 1. Fork or use this repo

```bash
git clone https://github.com/Eirafiya/crhunter
cd crhunter
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config.example.yml config.yml
# Edit config.yml with your counties, bedrooms, keywords
```

### 3. Set GitHub Secrets

In your repo → Settings → Secrets → Actions:

| Secret | Description |
|---|---|
| `RESEND_API_KEY` | From [resend.com](https://resend.com) (free) |
| `EMAIL_SENDER` | From address (must be verified in Resend) |
| `EMAIL_RECIPIENT` | Your email address |

### 4. Run locally

```bash
python run_all.py --config config.yml
```

### 5. Enable GitHub Pages

Settings → Pages → Source: `GitHub Actions`

## Adding a New Provider

1. Create `scrapers/myprovider.py` extending `BaseProvider`
2. Implement `fetch() -> list[Listing]`
3. Add to `SCRAPERS` dict in `run_all.py`
4. Add to `config.example.yml`

## Running Tests

```bash
pytest tests/ -v
```

## License

AGPL-3.0 — free for personal use. Commercial use requires a licence.

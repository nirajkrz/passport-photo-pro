# 📷 Passport Photo Pro

Free, private, instant passport & visa photo converter with a polished UI and Buy Me a Coffee monetization.

## ✨ What's new in v2

| Feature | v1 | v2 |
|---|---|---|
| Multi-country presets | ✅ | ✅ |
| Print sheet generator | ✅ | ✅ |
| **Buy Me a Coffee button** | ❌ | ✅ Floating + inline banner |
| **Premium UI with Google Fonts** | ❌ | ✅ DM Sans + DM Serif Display |
| **Step-by-step workflow indicator** | ❌ | ✅ |
| **Photo quality score row** | ❌ | ✅ |
| **Privacy grid** | ❌ | ✅ |
| Google Sheets dependency | ❌ | ❌ (not needed) |

---

## ⚙️ Setup — edit these 4 lines in `app.py`

```python
BMC_USERNAME   = "yourname"         # buymeacoffee.com/<yourname>
KOFI_USERNAME  = "yourname"         # ko-fi.com/<yourname>  (optional)
CONTACT_EMAIL  = "you@example.com"
APP_TITLE      = "Passport Photo Pro"
```

---

## 💰 Revenue options

### 1. Buy Me a Coffee (easiest)
1. Sign up at [buymeacoffee.com](https://www.buymeacoffee.com)
2. Copy your username into `BMC_USERNAME`
3. The app shows a floating button (always visible) + an inline banner (shown before & after photo)

### 2. Ko-fi (alternative)
Replace the BMC link with `https://ko-fi.com/{KOFI_USERNAME}`

### 3. Google AdSense / sponsorship
Streamlit Cloud doesn't support JS ad injections, but you can:
- Add a sidebar sponsor section with a banner image
- Put a "Sponsored by X" text link in the footer

---

## 🚀 Deploy to Streamlit Cloud (free)

```bash
# 1. Push to GitHub
git init && git add . && git commit -m "init"
git remote add origin https://github.com/YOU/passport-photo-pro.git
git push -u origin main

# 2. Go to share.streamlit.io → New app → connect repo → deploy
# No secrets or environment variables needed.
```

### Local dev
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 📐 Supported specs

| Country | Size (px) | Max file |
|---|---|---|
| 🇮🇳 Indian Passport Seva | 630×810 | 250 KB |
| 🇺🇸 US Passport / Visa | 600×600 | 240 KB |
| 🇬🇧 UK Passport | 600×750 | 240 KB |
| 🇪🇺 EU / Schengen | 560×700 | 200 KB |
| 🇦🇺 Australian Passport | 472×590 | 200 KB |
| 🇨🇦 Canadian Passport | 600×750 | 240 KB |

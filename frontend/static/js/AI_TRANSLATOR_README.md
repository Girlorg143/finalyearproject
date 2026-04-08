# AI Recommendation Translation Service

## Overview

This module provides automatic translation for AI-generated recommendations using **LibreTranslate (Local)** as the primary option, with Azure Translator and Google Cloud Translation as fallbacks.

## 🚀 Quick Start (LibreTranslate - RECOMMENDED)

### Step 1: Start LibreTranslate with Docker

```bash
docker run -p 5000:5000 libretranslate/libretranslate
```

That's it! The translation service will automatically connect to `http://localhost:5000`.

### Step 2: Test Translation

1. Open your Farmer Dashboard
2. Select Telugu or Hindi from language dropdown
3. Click on a batch to see AI recommendations
4. The recommendations will automatically translate!

---

## Alternative Options

### Option 2: Microsoft Azure Translator

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a "Translator" resource
3. Get your API key and region
4. Set the key:

```javascript
localStorage.setItem('azure_translation_api_key', 'YOUR_API_KEY');
location.reload();
```

### Option 3: Google Cloud Translation

```javascript
localStorage.setItem('google_translation_api_key', 'YOUR_API_KEY');
location.reload();
```

---

## Features

### ✅ LibreTranslate Benefits
- **FREE** - No API costs
- **PRIVATE** - Data stays on your machine
- **NO INTERNET** - Works offline after Docker pull
- **FAST** - Local processing
- **PERFECT FOR VIVA** - Shows local AI/ML capability

### Caching Mechanism
- All translations cached in localStorage
- Cache persists across page reloads
- Reduces API calls and improves performance

### Fallback Handling
- If translation fails → returns original English
- UI continues working without breaking

---

## Supported Languages

| Language | Code | Status |
|----------|------|--------|
| English | en | Base (no translation) |
| Telugu | te | ✅ Supported |
| Hindi | hi | ✅ Supported |
| Tamil | ta | ✅ Supported |
| Kannada | kn | ✅ Supported |

---

## How It Works

```
1. AI generates recommendation (English)
2. System checks cache first
3. If not cached → calls LibreTranslate @ localhost:5000
4. Stores result in cache
5. Displays translated text
```

---

## Docker Commands

### Start LibreTranslate
```bash
docker run -p 5000:5000 libretranslate/libretranslate
```

### Start with specific languages only (faster)
```bash
docker run -p 5000:5000 libretranslate/libretranslate --load-only en,hi,te,ta,kn
```

### Run in background
```bash
docker run -d -p 5000:5000 libretranslate/libretranslate
```

### Stop LibreTranslate
```bash
docker stop $(docker ps -q --filter ancestor=libretranslate/libretranslate)
```

---

## API Methods

```javascript
// The translator is automatically available as 'aiTranslator'

// Check if LibreTranslate is working
await aiTranslator.translateText('Hello', 'te');

// View cache stats
aiTranslator.getCacheStats();

// Clear cache
aiTranslator.clearCache();

// Switch APIs manually
aiTranslator.useLibreTranslate = false;  // Use Azure
aiTranslator.useLibreTranslate = true;    // Use LibreTranslate (default)
```

---

## Troubleshooting

### "Translation API error" in console
- Check if Docker is running: `docker ps`
- Restart LibreTranslate: `docker run -p 5000:5000 libretranslate/libretranslate`
- Check if port 5000 is available

### First translation is slow
- Normal! LibreTranslate loads models on first use
- Subsequent translations are fast
- Cached translations are instant

### Want to use Azure instead?
- Set API key in localStorage (see Alternative Options)
- Or set `aiTranslator.useLibreTranslate = false`

---

## Integration Points

Modified files:
- `frontend/static/js/ai_recommendation_translator.js` - Translation service
- `frontend/static/js/farmer.js` - Integrated with AI recommendation display
- `frontend/templates/farmer.html` - Script reference added

---

## Viva Tips 💡

1. **Start Docker before demo**: `docker run -p 5000:5000 libretranslate/libretranslate`
2. **Show the caching**: Translate same text twice - second time is instant
3. **Show offline capability**: Works without internet after Docker pull
4. **Show privacy**: "No data leaves the machine - perfect for farmer data privacy"
5. **Show cost**: "Zero API costs - runs locally for free"

Good luck with your viva! 🎉

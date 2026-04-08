/**
 * AI Recommendation Translation Service
 * 
 * Provides automatic translation for AI-generated recommendations using MyMemory API (free).
 * Includes caching mechanism to reduce API calls.
 * 
 * Restrictions: Only modifies AI Recommendation Output Layer
 */

class AIRecommendationTranslator {
  constructor() {
    // LibreTranslate (Local) configuration - DISABLED by default due to Docker issues
    this.libreTranslateEndpoint = 'http://localhost:5000';
    this.useLibreTranslate = false; // Set to true ONLY if LibreTranslate is confirmed working
    
    // MyMemory API configuration (FREE - no API key needed!)
    this.myMemoryEndpoint = 'https://api.mymemory.translated.net/get';
    this.useMyMemory = true; // Use MyMemory as primary free translation service
    
    // Language mapping from UI codes to API codes
    this.langMap = {
      'en': 'en',
      'hi': 'hi',
      'te': 'te',
      'ta': 'ta',
      'kn': 'kn'
    };
    
    // In-memory cache for translations
    this.cache = new Map();
    
    // Load cache from localStorage if available
    this.loadCache();
  }
  
  /**
   * Call MyMemory API (FREE - no API key required!)
   * https://api.mymemory.translated.net/get?q=TEXT&langpair=en|te
   * @param {string} text - Text to translate
   * @param {string} targetLang - Target language code
   * @returns {Promise<string>} - Translated text
   */
  async callMyMemoryAPI(text, targetLang) {
    const langPair = `en|${targetLang}`;
    const encodedText = encodeURIComponent(text);
    const url = `${this.myMemoryEndpoint}?q=${encodedText}&langpair=${langPair}`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    try {
      const response = await fetch(url, {
        method: 'GET',
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`MyMemory API error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // MyMemory returns: { responseData: { translatedText: "...", match: 0.9 } }
      if (!data || !data.responseData || !data.responseData.translatedText) {
        throw new Error('Invalid MyMemory response format');
      }
      
      // Check if translation failed (returns "MYMEMORY WARNING" when quota exceeded)
      const translated = data.responseData.translatedText;
      if (translated.includes('MYMEMORY WARNING') || translated.includes('QUOTA EXCEEDED')) {
        throw new Error('MyMemory quota exceeded or API limit reached');
      }
      
      return translated;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('MyMemory translation timeout after 10 seconds');
      }
      throw error;
    }
  }
  
  /**
   * Load cache from localStorage
   */
  loadCache() {
    try {
      const saved = localStorage.getItem('ai_translation_cache');
      if (saved) {
        const parsed = JSON.parse(saved);
        this.cache = new Map(Object.entries(parsed));
      }
    } catch (e) {
      console.warn('Failed to load translation cache:', e);
    }
  }
  
  /**
   * Save cache to localStorage
   */
  saveCache() {
    try {
      const obj = Object.fromEntries(this.cache);
      localStorage.setItem('ai_translation_cache', JSON.stringify(obj));
    } catch (e) {
      console.warn('Failed to save translation cache:', e);
    }
  }
  
  /**
   * Generate cache key for text
   * @param {string} text - Original text
   * @returns {string} - Normalized key
   */
  getCacheKey(text) {
    return text.trim().toLowerCase().substring(0, 200);
  }
  
  /**
   * Check if translation exists in cache
   * @param {string} text - Original text
   * @param {string} targetLang - Target language code
   * @returns {string|null} - Cached translation or null
   */
  getCachedTranslation(text, targetLang) {
    const key = this.getCacheKey(text);
    const entry = this.cache.get(key);
    if (entry && entry[targetLang]) {
      return entry[targetLang];
    }
    return null;
  }
  
  /**
   * Store translation in cache
   * @param {string} text - Original text
   * @param {string} targetLang - Target language code
   * @param {string} translation - Translated text
   */
  setCachedTranslation(text, targetLang, translation) {
    const key = this.getCacheKey(text);
    const entry = this.cache.get(key) || {};
    entry[targetLang] = translation;
    this.cache.set(key, entry);
    this.saveCache();
  }
  
  /**
   * Main translation function
   * @param {string} text - English text to translate
   * @param {string} targetLang - Target language code (e.g., 'te', 'hi')
   * @returns {Promise<string>} - Translated text or original if fails
   */
  async translateText(text, targetLang) {
    // Validate inputs
    if (!text || typeof text !== 'string') {
      return text;
    }
    
    // Normalize target language
    const lang = this.langMap[targetLang] || targetLang;
    
    // Skip translation for English
    if (lang === 'en') {
      return text;
    }
    
    // Check cache first
    const cached = this.getCachedTranslation(text, lang);
    if (cached) {
      console.log('Translation cache hit:', text.substring(0, 30));
      return cached;
    }
    
    // Call API - Try LibreTranslate first (local, no API key needed)
    // Then fall back to MyMemory API (free, no API key needed)
    try {
      let translation;
      if (this.useLibreTranslate) {
        console.log('Using LibreTranslate (local) for translation...');
        translation = await this.callLibreTranslateAPI(text, lang);
      } else if (this.useMyMemory) {
        console.log('Using MyMemory API (free) for translation...');
        translation = await this.callMyMemoryAPI(text, lang);
      } else {
        throw new Error('No translation service configured');
      }
      
      // Store in cache
      this.setCachedTranslation(text, lang, translation);
      
      return translation;
    } catch (error) {
      console.error('Translation API error:', error);
      // Fallback: return original text
      return text;
    }
  }
  
  /**
   * Call LibreTranslate API (Local - No API Key Required!)
   * @param {string} text - Text to translate
   * @param {string} targetLang - Target language code
   * @returns {Promise<string>} - Translated text
   */
  async callLibreTranslateAPI(text, targetLang) {
    const url = `${this.libreTranslateEndpoint}/translate`;
    
    // Add timeout - use longer timeout for first request (model loading takes time)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout for model loading
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          q: text,
          source: 'en',
          target: targetLang,
          format: 'text'
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`LibreTranslate API error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (!data || !data.translatedText) {
        throw new Error('Invalid LibreTranslate response format');
      }
      
      return data.translatedText;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        console.warn('Translation timeout - LibreTranslate may still be loading models (first request can take 20-30 seconds)');
        throw new Error('Translation timeout after 30 seconds - models may still be loading');
      }
      throw error;
    }
  }

  /**
   * Clear translation cache
   */
  clearCache() {
    this.cache.clear();
    localStorage.removeItem('ai_translation_cache');
  }
  
  /**
   * Get cache statistics
   * @returns {Object} - Cache stats
   */
  getCacheStats() {
    return {
      size: this.cache.size,
      entries: Array.from(this.cache.keys())
    };
  }
}

// Create global instance
const aiTranslator = new AIRecommendationTranslator();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AIRecommendationTranslator, aiTranslator };
}

/**
 * Initialize API
 * Call this function on page load
 */
function initAITranslator() {
  // LibreTranslate is disabled by default due to Docker networking issues on Windows
  console.log('AI Translator: LibreTranslate disabled by default. Set useLibreTranslate=true if Docker is working.');
  
  // MyMemory API is used as default (FREE, no API key needed!)
  if (aiTranslator.useMyMemory) {
    console.log('AI Translator: Using MyMemory API (free) - https://mymemory.translated.net/');
    console.log('AI Translator: No API key required! 1000 words/day free limit.');
  }
}

// Initialize on script load
document.addEventListener('DOMContentLoaded', initAITranslator);

// Also expose globally
window.initAITranslator = initAITranslator;


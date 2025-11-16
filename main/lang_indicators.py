"""
Smart Language Detector - Hybrid approach
Uses langdetect for most languages, custom detection for Devanagari conflicts
"""

from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# For consistent results
DetectorFactory.seed = 0

class SmartLanguageDetector:
    def __init__(self):
        # Languages that langdetect handles well
        self.langdetect_langs = ['bn', 'ta', 'te', 'ml', 'kn', 'pa', 'or', 'as', 'ur', 'si', 'en']
        
        # Devanagari script languages that need custom detection
        self.devanagari_langs = ['hi', 'mr', 'gu', 'sa', 'ne']  # Hindi, Marathi, Gujarati, Sanskrit, Nepali
        
        # Custom indicators for Devanagari language distinction
        self.devanagari_indicators = {
            'hi': {  # Hindi
                'है': 3, 'हैं': 3, 'हो': 2, 'क्या': 2, 'यह': 2, 'वह': 2, 
                'मैं': 2, 'तुम': 2, 'को': 1, 'से': 1, 'ने': 1, 'पर': 1,
                'में': 1, 'का': 1, 'की': 1, 'के': 1,
            },
            'mr': {  # Marathi
                'आहे': 3, 'आहोत': 3, 'काय': 2, 'हा': 2, 'ती': 2, 'मी': 2, 
                'तू': 2, 'आम्ही': 2, 'तुम्ही': 2, 'ला': 1, 'ने': 1, 'च': 1,
                'पण': 1, 'आणि': 1,
            },
            'gu': {  # Gujarati
                'છે': 3, 'થાય': 3, 'શું': 2, 'આ': 2, 'તે': 2, 'હું': 2,
                'તમે': 2, 'ને': 1, 'થી': 1, 'અને': 1, 'પણ': 1,
            },
            'sa': {  # Sanskrit (less common)
                'अस्ति': 3, 'भवति': 3, 'किम्': 2, 'अहम्': 2, 'त्वम्': 2,
                'सः': 2, 'तत्': 2, 'च': 1, 'वा': 1,
            },
            'ne': {  # Nepali
                'छ': 3, 'हो': 2, 'के': 2, 'यो': 2, 'त्यो': 2, 'म': 2,
                'तिमी': 2, 'हामी': 2, 'लाई': 1, 'बाट': 1, 'र': 1,
            }
        }
        
        # Map to IndicTrans2 language codes
        self.lang_code_map = {
            'hi': 'hin_Deva', 'mr': 'mar_Deva', 'bn': 'ben_Beng', 'ta': 'tam_Taml',
            'te': 'tel_Telu', 'gu': 'guj_Gujr', 'kn': 'kan_Knda', 'ml': 'mal_Mlym',
            'pa': 'pan_Guru', 'or': 'ory_Orya', 'as': 'asm_Beng', 'ur': 'urd_Arab',
            'en': 'eng_Latn', 'ne': 'nep_Deva', 'si': 'sin_Sinh', 'sa': 'san_Deva',
        }

    def is_devanagari_script(self, text):
        """Check if text uses Devanagari script"""
        return any('\u0900' <= char <= '\u097F' for char in text)

    def detect_devanagari_language(self, text):
        """Custom detection for Devanagari script languages"""
        lang_scores = {}
        
        for lang, indicators in self.devanagari_indicators.items():
            score = 0
            for word, weight in indicators.items():
                if word in text:
                    score += weight
            if score > 0:
                lang_scores[lang] = score
        
        if lang_scores:
            # Return the language with highest score
            best_lang = max(lang_scores.items(), key=lambda x: x[1])[0]
            return best_lang, lang_scores[best_lang]
        
        # If no clear indicators, default to Hindi (most common)
        return 'hi', 0

    def detect_language(self, text):
        """Smart hybrid language detection"""
        if not text or len(text.strip()) < 2:
            return 'hin_Deva'

        # Step 1: Check if it's Devanagari script
        if self.is_devanagari_script(text):
            print("🔍 Detected Devanagari script - using custom detection")
            devanagari_lang, confidence = self.detect_devanagari_language(text)
            print(f"✅ Custom detection: {devanagari_lang} (confidence: {confidence})")
            return self.lang_code_map[devanagari_lang]
        
        # Step 2: For non-Devanagari scripts, use langdetect
        try:
            detected_lang = detect(text)
            print(f"🌐 Langdetect result: {detected_lang}")
            
            if detected_lang in self.lang_code_map:
                return self.lang_code_map[detected_lang]
            else:
                print(f"⚠️  Langdetect returned unsupported language: {detected_lang}")
                return 'hin_Deva'  # Fallback
                
        except LangDetectException:
            print("❌ Langdetect failed, using fallback")
            return 'hin_Deva'  # Fallback

    def get_detection_method(self, text):
        """Get information about detection method used"""
        if self.is_devanagari_script(text):
            lang, confidence = self.detect_devanagari_language(text)
            return {
                'method': 'custom_devanagari_detection',
                'detected_lang': lang,
                'confidence': confidence,
                'indicators_used': len([k for k, v in self.devanagari_indicators[lang].items() if k in text])
            }
        else:
            try:
                lang = detect(text)
                return {
                    'method': 'langdetect',
                    'detected_lang': lang,
                    'confidence': 'high'
                }
            except:
                return {
                    'method': 'fallback',
                    'detected_lang': 'hi',
                    'confidence': 'low'
                }
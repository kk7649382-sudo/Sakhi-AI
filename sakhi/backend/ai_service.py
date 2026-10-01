"""
AI Service for Sakhi (சகி).
Connects to Gemini API with strict system grounding on official scheme facts.
Provides guaranteed deterministic Tamil fallback when Gemini API key is missing or network is unavailable.
"""

import os
import re
from typing import Dict, Any, Optional
from .scheme_catalog import get_default_scheme

# Pre-defined verified fallback responses in warm colloquial Tamil
VERIFIED_FALLBACKS: Dict[str, Dict[str, Any]] = {
    "greeting": {
        "text": "வணக்கம் அக்கா! நான் சகி. கலைஞர் மகளிர் உரிமைத் திட்டம் மூலம் மாதம் ரூ.1,000 உதவித்தொகை பெறுவது பற்றி உங்களுக்கு எளிய தமிழில் வழிகாட்டுகிறேன். உங்களுக்கு என்ன உதவி வேண்டும் என்று கேளுங்கள்.",
        "category": "வணக்கம்"
    },
    "documents": {
        "text": "அக்கா, கலைஞர் மகளிர் உரிமைத் திட்டத்திற்கு விண்ணப்பிக்க 4 முக்கிய ஆவணங்கள் தேவை:\n\n1. 🌾 ஸ்மார்ட் குடும்ப அட்டை (ரேஷன் கார்டு)\n2. 🪪 உங்கள் ஆதார் அட்டை\n3. 🏦 உங்கள் பெயரில் உள்ள வங்கி பாஸ்புக் (ஆதார் இணைக்கப்பட்டது)\n4. ⚡ சமீபத்திய மின் கட்டண ரசீது அல்லது நுகர்வோர் எண்\n\nஇந்த நான்கையும் கையில் எடுத்துக்கொண்டு உங்கள் ஊர் இ-சேவை மையத்திற்குச் செல்லுங்கள்.",
        "category": "ஆவணங்கள்"
    },
    "eligibility": {
        "text": "அக்கா, இந்த உரிமைத் தொகை யாருக்குக் கிடைக்கும் என்பதை சுருக்கமாகக் கூறுகிறேன்:\n\n1. ✅ வயது 21 அல்லது அதற்கு மேற்பட்ட குடும்பத் தலைவியாக இருக்க வேண்டும்.\n2. ✅ குடும்ப ஆண்டு வருமானம் ரூ.2.5 லட்சத்திற்குள் இருக்க வேண்டும்.\n3. ✅ குடும்ப ஆண்டு மின்சாரப் பயன்பாடு 3,600 யூனிட்டுக்குள் இருக்க வேண்டும்.\n4. ✅ 5 ஏக்கர் நன்செய் அல்லது 10 ஏக்கர் புன்செய் நிலத்திற்குள் இருக்க வேண்டும்.\n\nஇந்த நிபந்தனைகள் பூர்த்தியானால் நீங்கள் இ-சேவை மையம் மூலம் தாராளமாக விண்ணப்பிக்கலாம்.",
        "category": "தகுதிகள்"
    },
    "benefit": {
        "text": "அக்கா, இத்திட்டம் மூலம் மாதம் தோறும் ரூ.1,000 உதவித்தொகை உங்கள் வங்கிக் கணக்கில் நேரடியாக (DBT) வரவு வைக்கப்படும். ஒவ்வொரு மாதமும் 15-ஆம் தேதிக்குள் வங்கிக் கணக்கிற்கு பணம் வந்துவிடும். இதற்கு யாரிடமும் எந்தக் கட்டணமும் கொடுக்கத் தேவையில்லை.",
        "category": "பயன்கள்"
    },
    "apply": {
        "text": "அக்கா, விண்ணப்பிக்க எளிய வழி:\n\n1. உங்கள் ஆதார் அட்டை, ரேஷன் கார்டு, வங்கி பாஸ்புக் எடுத்துக்கொள்ளுங்கள்.\n2. உங்கள் ஊர் தமிழ்நாடு அரசு இ-சேவை மையம் (e-Sevai) அல்லது ரேஷன் கடை சிறப்பு முகாமிற்கு நேரில் செல்லுங்கள்.\n3. அங்கு கைரேகை வைத்து (பயோமெட்ரிக்) விண்ணப்பத்தைப் பதிவு செய்து, இலவச ஒப்புகைச் சீட்டு (ரசீது) பெற்றுக்கொள்ளுங்கள்.",
        "category": "விண்ணப்பிக்கும் முறை"
    },
    "status": {
        "text": "அக்கா, விண்ணப்ப நிலையை அறிய:\n\n1. kmut.tn.gov.in என்ற அரசு இணையதளத்திற்குச் செல்லலாம்.\n2. அல்லது அருகில் உள்ள இ-சேவை மையத்தில் உங்கள் குடும்ப அட்டை அல்லது ஆதார் எண்ணைக் கொடுத்து தெரிந்து கொள்ளலாம்.\n3. மேலும் விவரங்களுக்கு தமிழ்நாடு முதல்வர் உதவி மையம் 1100 எண்ணை அழைக்கலாம்.",
        "category": "நிலை அறிதல்"
    },
    "rejected": {
        "text": "அக்கா, ஒருவேளை உங்கள் விண்ணப்பம் ஏற்கப்படாவிட்டால் கவலைப்பட வேண்டாம்! விண்ணப்பம் நிராகரிக்கப்பட்டதற்கான காரணத்துடன் SMS வரும். காரணம் அறிந்த 30 நாட்களுக்குள் உங்கள் ஊர் இ-சேவை மையத்தில் தேவையான சரியான ஆவணங்களுடன் மேல்முறையீடு (Appeal) செய்யலாம்.",
        "category": "மேல்முறையீடு"
    },
    "default": {
        "text": "வணக்கம் அக்கா! நான் மகளிர் உரிமைத் தொகை மாதம் ரூ.1,000 திட்டம் பற்றி மட்டுமே வழிகாட்டும் சகி.\n\nநீங்கள் கீழ்கண்டவற்றில் எதைப்பற்றி அறிய விரும்புகிறீர்கள்?\n• என்னென்ன ஆவணங்கள் தேவை?\n• எனக்கு இந்த உதவித்தொகை கிடைக்குமா?\n• எங்கு சென்று விண்ணப்பிக்க வேண்டும்?\n\nகீழே உள்ள பொத்தான்களைத் தொட்டு நேரடியாகவும் தெரிந்து கொள்ளலாம்.",
        "category": "பொது உதவி"
    }
}


class SakhiAIService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.scheme = get_default_scheme()
        self.model = None
        self._init_gemini()

    def _init_gemini(self):
        """Safely initialize Gemini client if API key is present."""
        if not self.api_key:
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            system_instruction = f"""
நீங்கள் "சகி" (Sakhi) - கிராமப்புற தமிழ் பெண்களுக்கு உதவும் கனிவான, பாசமான அக்கா/தோழி போன்ற AI உதவியாளர்.
உங்களுக்கு வழங்கப்பட்டுள்ள ஒரே குறிக்கோள்: தமிழ்நாடு அரசின் "{self.scheme['name_ta']}" (மாதம் ரூ.1,000 திட்டம்) பற்றி மட்டுமே எளிய தமிழில் வழிகாட்டுவது.

அதிகாரப்பூர்வ உண்மைகள் மட்டுமே (Verified Facts):
- திட்டம்: கலைஞர் மகளிர் உரிமைத் திட்டம்.
- பயன்: மாதம் ரூ.1,000 நேரடியாக தகுதியுள்ள பெண்ணின் வங்கிக் கணக்கில் (DBT).
- தகுதிகள்: 21 வயதுக்கு மேற்பட்ட குடும்பத் தலைவி; குடும்ப ஆண்டு வருமானம் ரூ.2.5 லட்சத்திற்குள்; ஆண்டு மின் பயன்பாடு 3,600 யூனிட்டுக்குள்; நன்செய் நிலம் 5 ஏக்கர் அல்லது புன்செய் நிலம் 10 ஏக்கருக்குள்.
- தேவையான 4 ஆவணங்கள்: (1) ஸ்மார்ட் குடும்ப அட்டை (ரேஷன் கார்டு), (2) ஆதார் அட்டை, (3) வங்கி சேமிப்பு பாஸ்புக் (ஆதார் இணைக்கப்பட்டது), (4) மின் கட்டண நுகர்வோர் எண்.
- விண்ணப்பிக்கும் இடம்: கிராம இ-சேவை மையம் (e-Sevai) அல்லது ரேஷன் கடை முகாம்.
- கட்டணம்: முற்றிலும் இலவசம். இடைத்தரகர்களுக்கு பணம் தரக் கூடாது.
- இணையதளம்: kmut.tn.gov.in. உதவி எண்: 1100.

கட்டாய விதிகள் (Strict Constraints):
1. மொழி: மிக எளிய, கிராமப்புற பாசமான பேச்சுத் தமிழில் மட்டுமே பதில் அளியுங்கள். கடினமான ஆங்கிலச் சொற்களைத் தவிர்க்கவும்.
2. விடையின் நீளம்: அதிகபட்சம் 3 முதல் 4 எளிய வரிகள் அல்லது 3 படிகள் மட்டுமே.
3. ஆரம்பம்: எப்பொழுதும் "வணக்கம் அக்கா, கவலைப்படாதீங்க..." அல்லது "அக்கா..." என பாசத்தோடு தொடங்கவும்.
4. அதிகாரப்பூர்வ விதிகளுக்கு மாறாக எந்தப் புதிய தகவலையும் சொந்தமாக உருவாக்கக் கூடாது (No hallucinations).
5. இத்திட்டம் அல்லாத பிற விஷயங்களைக் கேட்டால்: "அக்கா, நான் கலைஞர் மகளிர் உரிமைத் தொகை திட்டம் பற்றி மட்டுமே வழிகாட்ட முடியும்" என பணிவாகக் கூறி இத்திட்ட தகவலுக்குத் திருப்பவும்.
"""
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
        except Exception as e:
            # If initialization fails, fallback will be used
            self.model = None

    def match_rule_intent(self, query: str) -> str:
        """Classify query intent based on Tamil keywords."""
        q = query.lower()
        if any(w in q for w in ["வணக்கம்", "ஹலோ", "வணக்கமுங்க", "யார் நீ", "ஹாய்"]):
            return "greeting"
        if any(w in q for w in ["நிலை", "ஸ்டேட்டஸ்", "வந்துவிட்டதா", "விண்ணப்ப நிலை", "செக்"]):
            return "status"
        if any(w in q for w in ["நிராகரிக்க", "வரவில்லை", "மேல்முறையீடு", "கிடைக்கவில்லை", "ரிஜெக்ட்"]):
            return "rejected"
        if any(w in q for w in ["ஆவண", "கார்டு", "ரேஷன்", "ஆதார்", "பாஸ்புக்", "சான்றிதழ்", "என்ன தேவை"]):
            return "documents"
        if any(w in q for w in ["தகுதி", "யாருக்கு", "வயது", "கிடைக்குமா", "வருமானம்", "நிலம்", "வரம்பு"]):
            return "eligibility"
        if any(w in q for w in ["பணம்", "எவ்வளவு", "எப்போது", "1000", "ரூபாய்", "வரவு", "பயன்"]):
            return "benefit"
        if any(w in q for w in ["எங்கு", "எப்படி", "விண்ணப்ப", "இ-சேவை", "முகாம்", "பதிவு", "செல்ல"]):
            return "apply"
        return "default"

    async def answer_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process user query through Gemini or verified rule-based fallback.
        Returns structured response indicating whether Gemini or verified fallback was used.
        """
        clean_query = user_query.strip()
        if not clean_query:
            fallback = VERIFIED_FALLBACKS["default"]
            return {
                "text": fallback["text"],
                "source": "verified_rule",
                "source_label": "அதிகாரப்பூர்வ மாதிரி வழிகாட்டல் (Verified Catalog)",
                "category": fallback["category"],
                "is_ai_generated": False
            }

        # Try Gemini if model is configured
        if self.model and self.api_key:
            try:
                response = self.model.generate_content(clean_query)
                answer_text = response.text.strip()
                if answer_text:
                    return {
                        "text": answer_text,
                        "source": "gemini",
                        "source_label": "ஜெமினி AI வழிகாட்டல் (Gemini 1.5 Flash)",
                        "category": "AI உரையாடல்",
                        "is_ai_generated": True
                    }
            except Exception as e:
                # Log or swallow error and gracefully continue to verified fallback
                pass

        # Use verified deterministic fallback
        intent = self.match_rule_intent(clean_query)
        fallback = VERIFIED_FALLBACKS.get(intent, VERIFIED_FALLBACKS["default"])
        return {
            "text": fallback["text"],
            "source": "verified_rule",
            "source_label": "அதிகாரப்பூர்வ மாதிரி வழிகாட்டல் (Verified Catalog)",
            "category": fallback["category"],
            "is_ai_generated": False
        }

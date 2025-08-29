import re
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class Intent:
    name: Optional[str] = None
    arg: Optional[str] = None
    extra: Optional[str] = None

class IntentService:
    """Service for detecting user intents"""
    
    def __init__(self):
        self.weather_pattern = re.compile(r"\b(weather|temperature|forecast)\b.*\b(in|at)\b\s+(?P<city>[\w\s,.-]+)\??", re.I)
        self.news_pattern = re.compile(r"\b(news|headlines|latest)\b(\s+on\s+(?P<topic>[\w\s-]+))?", re.I)
        self.movie_pattern = re.compile(r"\b(movie|film|cinema)\b.*(?P<query>[\w\s-]+)", re.I)
        self.anime_pattern = re.compile(r"\banime\b.*(?P<query>[\w\s-]+)", re.I)
        self.quote_pattern = re.compile(r"\b(quote|inspire|motivate|wisdom)\b.*(?P<category>[\w\s-]+)?", re.I)
    
    def detect_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect user intent from text"""
        if not text or not text.strip():
            return None
        
        text_lower = text.lower().strip()
        
        # Weather patterns
        weather_patterns = [
            r"weather in ([\w\s]+)",
            r"temperature in (\w+)",
            r"how.*weather.*(\w+)",
            r"what.*weather.*like in (\w+)",
            r"weather.*(\w+)",
            r"temperature.*(\w+)"
        ]
        
        for pattern in weather_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return {"intent": "weather", "location": match.group(1).strip()}
        
        # Generic weather check
        if any(keyword in text_lower for keyword in ["weather", "temperature", "forecast", "climate"]):
            return {"intent": "weather", "location": "London"}  # Default location
        
        # News patterns
        if any(w in text_lower for w in ["news", "headlines", "happening", "current events"]):
            match = re.search(r"news.*?about\s+(\w+)|(\w+)\s+news", text_lower)
            topic = (match.group(1) or match.group(2)) if match else "general"
            return {"intent": "news", "topic": topic}
        
        # Movie patterns
        if any(w in text_lower for w in ["movie", "film", "cinema"]):
            match = re.search(r"movies?.*?about\s+([\w\s]+)|find.*?movie\s+([\w\s]+)|search.*?movie\s+([\w\s]+)", text_lower)
            query = match.group(1) or match.group(2) or match.group(3) if match else "popular"
            return {"intent": "movies", "query": query.strip()}
        
        # Anime patterns
        if "anime" in text_lower:
            match = re.search(r"anime.*?about\s+([\w\s]+)|search.*?anime\s+([\w\s]+)", text_lower)
            query = (match.group(1) or match.group(2)) if match else "naruto"
            return {"intent": "anime", "query": query.strip()}
        
        # Quote patterns
        if any(w in text_lower for w in ["quote", "inspire", "motivate", "wisdom"]):
            match = re.search(r"quote.*?about\s+([\w\s]+)", text_lower)
            category = match.group(1).strip() if match else "motivational"
            return {"intent": "quote", "category": category}
        
        return None

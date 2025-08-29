import asyncio  # Add this import at the top of skills_service.py
import os
import requests
import random
import time
import logging
from typing import Optional, Dict, Any, Union, List

log = logging.getLogger("lumeai.skills_service")

class SkillsService:
    """Service for handling external API integrations"""
    
    def __init__(self):
        self.weather_api_key = os.getenv("WEATHER_API_KEY", "")
        self.news_api_key = os.getenv("NEWS_API_KEY", "")
        self.tmdb_api_key = os.getenv("TMDB_API_KEY", "")
    
    async def execute_skill(self, intent_data: Dict[str, Any]) -> str:
        """Execute the appropriate skill based on intent"""
        try:
            intent = intent_data.get("intent")
            
            if intent == "weather":
                location = intent_data.get("location", "London")
                result = await self.get_weather(location)
                if isinstance(result, dict) and "error" in result:
                    return f"Sorry, I couldn't get weather for {location}. Please check the city name."
                if isinstance(result, dict):
                    temp = result.get('temperature_c', 'Unknown')
                    condition = result.get('condition', 'Unknown')
                    loc_name = result.get('location', location)
                    country = result.get('country', '')
                    return f"Weather in {loc_name}, {country}: {temp}°C, {condition}"
                return f"Weather info for {location} is not available right now."
            
            elif intent == "news":
                topic = intent_data.get("topic", "general")
                result = await self.get_news(topic)
                if isinstance(result, str):
                    return result
                elif isinstance(result, list) and result:
                    headlines = []
                    for item in result[:3]:
                        title = item.get("title", "No title")
                        source = item.get("source", "Unknown")
                        headlines.append(f"• {title} ({source})")
                    return f"Latest {topic} headlines:\n" + "\n".join(headlines)
                return "Couldn't fetch news right now. Please try again later."
            
            elif intent == "movies":
                query = intent_data.get("query", "popular")
                result = await self.search_movies(query)
                if isinstance(result, dict) and "error" in result:
                    return f"Sorry, couldn't find movies about '{query}'. Try a different search term."
                if isinstance(result, list) and result:
                    movies = result[:3]
                    movie_list = []
                    for movie in movies:
                        title = movie.get("title", "Unknown")
                        year = movie.get("release_date", "")[:4] if movie.get("release_date") else ""
                        rating = movie.get("rating", 0)
                        year_str = f" ({year})" if year else ""
                        rating_str = f" - {rating}/10" if rating else ""
                        movie_list.append(f"• {title}{year_str}{rating_str}")
                    return f"Movies about '{query}':\n" + "\n".join(movie_list)
                return f"No movies found for '{query}'. Try a different search term."
            
            elif intent == "anime":
                query = intent_data.get("query", "naruto")
                result = await self.search_anime(query)
                if isinstance(result, dict) and "error" in result:
                    return f"Sorry, {result['error']}"
                if isinstance(result, list) and result:
                    anime_list = []
                    for anime in result[:3]:
                        title = anime.get("title", "Unknown")
                        score = anime.get("score", 0)
                        episodes = anime.get("episodes", 0)
                        anime_list.append(f"• {title} - Score: {score}/10 ({episodes} eps)")
                    return f"Anime results for '{query}':\n" + "\n".join(anime_list)
                return f"No anime found for '{query}'. Try a different search term."
            
            elif intent == "quote":
                category = intent_data.get("category", "motivational")
                result = await self.get_quote(category)
                quote_text = result.get("quote", "")
                author = result.get("author", "Unknown")
                return f'"{quote_text}" - {author}'
                
        except Exception as e:
            log.exception(f"Skill execution error: {e}")
            return f"Sorry, there was an error processing your request: {str(e)}"
        
        return "I'm not sure how to help with that."
    
    async def get_weather(self, city: str) -> Union[Dict[str, Any], str]:
        """Get weather information using WeatherAPI"""
        if not city.strip() or not self.weather_api_key:
            return {"error": "Invalid city or API key not set"}
        
        try:
            url = f"http://api.weatherapi.com/v1/current.json"
            params = {
                "key": self.weather_api_key,
                "q": city.strip(),
                "aqi": "no"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return {"error": f"Failed to fetch weather for {city}"}
            
            data = response.json()
            return {
                "location": data.get("location", {}).get("name"),
                "country": data.get("location", {}).get("country"),
                "temperature_c": data.get("current", {}).get("temp_c"),
                "condition": data.get("current", {}).get("condition", {}).get("text"),
            }
        except Exception as e:
            log.exception(f"Weather API error: {e}")
            return {"error": f"Weather error: {str(e)}"}
    
    async def get_news(self, topic: str = "general", n: int = 5) -> Union[List[Dict], str]:
        """Get news using NewsAPI"""
        if not self.news_api_key:
            return f"Please set NEWS_API_KEY to get {topic} news."
        
        try:
            url = "https://newsapi.org/v2/top-headlines"
            valid_categories = ['business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology']
            
            if topic.lower() in valid_categories:
                params = {
                    "apiKey": self.news_api_key,
                    "category": topic.lower(),
                    "language": "en",
                    "pageSize": n,
                    "country": "us"
                }
            else:
                params = {
                    "apiKey": self.news_api_key,
                    "q": topic,
                    "language": "en",
                    "pageSize": n,
                    "sortBy": "publishedAt"
                }
            
            response = requests.get(url, params=params, timeout=12)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok":
                return f"News API error: {data.get('message', 'Unknown error')}"
                
            articles = data.get("articles", [])[:n]
            if not articles:
                return f"No {topic} news found. Try: general, business, technology, sports"
            
            return [
                {
                    "title": a.get('title', 'No title'),
                    "url": a.get('url', ''),
                    "snippet": a.get('description', ''),
                    "source": a.get('source', {}).get('name', 'Unknown')
                } for a in articles
            ]
            
        except Exception as e:
            log.exception(f"News API error: {e}")
            return f"News fetch error: {str(e)}"
    
    async def search_movies(self, query: str) -> Union[List[Dict], Dict[str, str]]:
        """Search movies using TMDB API"""
        if not query.strip() or not self.tmdb_api_key:
            return {"error": "Invalid query or TMDB_API_KEY not set"}
        
        try:
            url = "https://api.themoviedb.org/3/search/movie"
            params = {
                "api_key": self.tmdb_api_key,
                "query": query.strip(),
                "page": 1,
                "include_adult": False
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 401:
                return {"error": "Invalid TMDB API key"}
            elif response.status_code != 200:
                return {"error": f"TMDB API error: HTTP {response.status_code}"}
            
            data = response.json()
            movies = data.get("results", [])
            
            if not movies:
                return {"error": f"No movies found for '{query}'"}
            
            return [
                {
                    "title": m.get("title", "Unknown"),
                    "release_date": m.get("release_date", ""),
                    "overview": m.get("overview", "No description"),
                    "rating": m.get("vote_average", 0),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else "",
                    "id": m.get("id", 0),
                    "popularity": m.get("popularity", 0)
                } for m in movies[:10]
            ]
            
        except requests.RequestException as e:
            log.exception(f"Movie search network error: {e}")
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            log.exception(f"Movie search error: {e}")
            return {"error": f"Movie search error: {str(e)}"}
    
    async def search_anime(self, query: str = "naruto", retries: int = 3) -> Union[List[Dict], Dict[str, str]]:
        """Search anime using Jikan API"""
        try:
            # Add delay to avoid rate limiting
            await asyncio.sleep(random.uniform(1, 2))
            
            url = "https://api.jikan.moe/v4/anime"
            params = {
                "q": query.strip(),
                "limit": 5,
                "order_by": "score",
                "sort": "desc",
                "status": "complete"
            }
            
            for attempt in range(retries):
                try:
                    response = requests.get(url, params=params, timeout=15)
                    
                    if response.status_code == 429:
                        wait_time = int(response.headers.get('Retry-After', 60))
                        if attempt < retries - 1:
                            await asyncio.sleep(wait_time)
                            continue
                        return {"error": "API rate limited. Please try again later."}
                    
                    elif response.status_code != 200:
                        if attempt < retries - 1:
                            await asyncio.sleep(2)
                            continue
                        return {"error": f"Anime search failed: HTTP {response.status_code}"}
                    
                    data = response.json()
                    anime_list = data.get("data", [])
                    
                    if not anime_list:
                        return {"error": f"No anime found for '{query}'. Try a different search term."}
                    
                    results = []
                    for a in anime_list:
                        genres = []
                        if a.get("genres"):
                            genres = [g.get("name", "") for g in a.get("genres", [])[:3]]
                        
                        synopsis = a.get("synopsis", "No description")
                        if synopsis and len(synopsis) > 150:
                            synopsis = synopsis[:150] + "..."
                        
                        results.append({
                            "title": a.get("title", "Unknown"),
                            "title_english": a.get("title_english", ""),
                            "episodes": a.get("episodes", 0),
                            "score": round(a.get("score", 0.0), 1) if a.get("score") else 0.0,
                            "synopsis": synopsis,
                            "status": a.get("status", "Unknown"),
                            "year": a.get("year", None),
                            "genres": genres,
                            "image_url": a.get("images", {}).get("jpg", {}).get("image_url", ""),
                            "mal_id": a.get("mal_id", 0)
                        })
                    
                    return results
                    
                except requests.RequestException as e:
                    if attempt < retries - 1:
                        await asyncio.sleep(3)
                        continue
                    return {"error": f"Network error: {str(e)}"}
                
        except Exception as e:
            log.exception(f"Anime search error: {e}")
            return {"error": f"Anime search error: {str(e)}"}
    
    async def get_quote(self, category: str = "motivational") -> Dict[str, str]:
        """Get inspirational quotes"""
        try:
            if category.lower() in ["motivational", "inspirational", "success", "life"]:
                url = f"https://zenquotes.io/api/quotes/[{category}]"
            else:
                url = "https://zenquotes.io/api/random"
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                url = "https://zenquotes.io/api/random"
                response = requests.get(url, timeout=10)
            
            data = response.json()
            if data and isinstance(data, list):
                quote = data[0]
                return {
                    "quote": quote.get("q", ""),
                    "author": quote.get("a", "Unknown"),
                    "category": category
                }
            
            # Fallback quotes
            fallbacks = [
                {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
                {"quote": "Innovation distinguishes between a leader and a follower.", "author": "Steve Jobs"},
                {"quote": "Success is not final, failure is not fatal: courage to continue counts.", "author": "Churchill"}
            ]
            return random.choice(fallbacks)
            
        except Exception as e:
            log.exception(f"Quote API error: {e}")
            return {
                "quote": "Believe you can and you're halfway there.",
                "author": "Theodore Roosevelt",
                "source": "fallback"
            }
    
    def get_skill_status(self) -> Dict[str, Dict[str, bool]]:
        """Check which skills are available"""
        return {
            "weather": {"available": bool(self.weather_api_key)},
            "news": {"available": bool(self.news_api_key)},
            "movies": {"available": bool(self.tmdb_api_key)},
            "anime": {"available": True},
            "quotes": {"available": True}
        }
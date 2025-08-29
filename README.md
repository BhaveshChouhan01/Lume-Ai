<h1 align="center">🪞 LumeAI</h1>
<p align="center">
  <b>Shining a light on every word you say.</b>  
</p>

  <p align="center">
  <!-- Languages & Frameworks -->
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/Vanilla%20JS-ES6-yellow?logo=javascript" />
  <img src="https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=fff" />
  <img src="https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=fff" />

  <!-- AI & APIs -->
  <img src="https://img.shields.io/badge/AssemblyAI-STT-orange?logo=google-voice" />
  <img src="https://img.shields.io/badge/Google%20Gemini-LLM-blueviolet?logo=googlegemini" />
  <img src="https://img.shields.io/badge/Murf.ai-TTS-ff69b4?logo=google-translate" />

  <!-- Infra & Tools -->
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=fff" />
  <img src="https://img.shields.io/badge/WebSocket-Low%20Latency-008000?logo=websocket&logoColor=fff" />
  <img src="https://img.shields.io/badge/Deployment-Render%20" />

  <!-- Project Info -->
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" />
</p>

---

## ✨ Features

- 🎙 **Real-time Voice Conversations**: Streaming speech-to-text and text-to-speech  
- 🎭 **Multiple AI Personas**: Default assistant, Madara Uchiha, Pirate, Cowboy, Robot, Professor  
- 🧩 **Smart Skills Integration**: Weather, news, movies, and more  
- 🔑 **User-Provided API Keys**: No hosting costs - users bring their own keys  
- 🐳 **Docker Containerized**: Easy deployment across platforms  
- 🔗 **WebSocket Streaming**: Low-latency audio processing  
- 📱 **Responsive Web Interface**: Works on desktop and mobile  
- 🛡 **Production Ready**: Health checks, logging, error handling  

---

## 🛠 Tech Stack

### **Frontend**
- **HTML5**, **CSS3**, **JavaScript (Vanilla)**
- Web Speech API *(for fallback TTS)*
- MediaRecorder API *(for audio capture)*

### **Backend**
- **Python 3.10+**, **FastAPI**
- [Murf API](https://murf.ai) — Text-to-Speech  
- [AssemblyAI](https://www.assemblyai.com) — Speech-to-Text  
- [Google Gemini API](https://ai.google) — AI Responses

---
## 🔑 Required API Keys

Users need to obtain their own API keys (free tiers available):

| Service | Required | Purpose | Get Key |
|---------|----------|---------|---------|
| [AssemblyAI](https://www.assemblyai.com/) | ✅ Yes | Speech-to-text | Free tier: 5 hours/month |
| [Google Gemini](https://aistudio.google.com/app/apikey) | ✅ Yes | AI responses | Free tier: 60 requests/minute |
| [Murf.ai](https://murf.ai/) | ⚪ Optional | Text-to-speech | Trial available |
| [WeatherAPI](https://weatherapi.com/) | ⚪ Optional | Weather queries | Free tier: 1M calls/month |
| [NewsAPI](https://newsapi.org/) | ⚪ Optional | News queries | Free tier: 1000 requests/day |
| [TMDB](https://www.themoviedb.org/settings/api) | ⚪ Optional | Movie queries | Free |

## 🎭 Available Personas

- **Default**: Helpful and neutral AI assistant
- **Madara Uchiha**: Arrogant and dominant (Naruto character)
- **Pirate**: Witty seafarer with pirate speech
- **Cowboy**: Wild West character with southern drawl
- **Robot**: Logical, technical responses with beeps
- **Professor**: Scholarly, educational responses

## 🐳 Deployment Options

### Render.com (Free Tier)
1. Fork this repository
2. Connect to Render.com
3. Create new Web Service
4. Select "Docker" environment
5. Deploy automatically

### Docker Compose
```yaml
version: '3.8'
services:
  lumeai:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - AUTO_ASSISTANT_REPLY=true
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped
```

## 🏗️ Architecture

```
Frontend (JavaScript)
    ↓ WebSocket
Backend (FastAPI)
    ↓ HTTP APIs
External Services:
    - AssemblyAI (STT)
    - Google Gemini (LLM)
    - Murf.ai (TTS)
    - Weather/News/TMDB APIs
```

### Project Structure
```
lumeai/
├── app/
│   ├── main.py              # Main FastAPI application
│   ├── core/                # Configuration and constants
│   ├── services/            # External API integrations
│   ├── routes/              # API endpoints
│   └── schemas/             # Pydantic models
├── templates/
│   └── index.html           # Frontend interface
├── static/
│   ├── css/
│   └── js/
├── docker-compose.yml       # Docker configuration
├── requirements.txt         # Python dependencies
└── README.md
```

## 🔧 Configuration

Configure via the web interface or environment variables:

```env
# Optional fallback keys (users override via UI)
ASSEMBLYAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
MURF_API_KEY=your_key_here

# App settings
AUTO_ASSISTANT_REPLY=true
PORT=8000
```

## 🎯 Skills System

LumeAI includes smart skills that detect user intent and provide specialized responses:

- **Weather**: "What's the weather in London?"
- **News**: "Get me tech news" 
- **Movies**: "Find action movies"
- **General AI**: Fallback to Gemini for other queries

Add custom skills by extending `app/services/skills_service.py`.

## 🔒 Security Features

- **No API Key Storage**: Keys passed via WebSocket parameters
- **User Session Isolation**: Each user gets isolated session
- **Input Validation**: All inputs sanitized and validated
- **Container Security**: Non-root user, minimal attack surface
- **CORS Protection**: Configurable CORS policies
## 🛠️ Development

### Adding New Personas
```python
# In app/core/config.py
PERSONAS = {
    "your_persona": """You are a [character description].
    Speak with [specific traits and language patterns]."""
}
```

### Adding New Skills
```python
# In app/services/skills_service.py
async def your_skill(self, query: str):
    # Your skill logic here
    return "Skill response"
```

### Frontend Customization
- Modify `templates/index.html` for UI changes
- Update `static/js/script.js` for behavior changes
- Add CSS in `static/css/` for styling

## 📊 Monitoring

### Health Checks
```bash
curl http://localhost:8000/health
```

### Logs
```bash
# Docker
docker-compose logs -f lumeai

# Local
tail -f logs/lumeai.log
```

### Debug Endpoints
- `/debug/personas/{session_id}` - Check session state
- `/reset/{session_id}` - Reset session data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Code formatting
black app/
isort app/

# Type checking
mypy app/
```

## 🐛 Common Issues

### Audio Not Working
- Ensure HTTPS for microphone access in production
- Check browser permissions for microphone
- Verify Murf.ai API key if using TTS

### Connection Errors
- Verify all required API keys are provided
- Check server URL configuration
- Ensure WebSocket support on hosting platform

### Performance Issues
- Consider Redis for session storage in production
- Monitor API rate limits
- Check network latency to external services

## 🙏 Acknowledgments

- [AssemblyAI](https://www.assemblyai.com/) for speech-to-text
- [Google Gemini](https://ai.google.dev/) for AI responses  
- [Murf.ai](https://murf.ai/) for text-to-speech
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework

## 📞 Support

- Create an [Issue](https://github.com/yourusername/lumeai-voice-assistant/issues) for bug reports
- [Discussions](https://github.com/yourusername/lumeai-voice-assistant/discussions) for questions
- Check the [Wiki](https://github.com/yourusername/lumeai-voice-assistant/wiki) for detailed guides

---
## 🙌 Special Thanks

Huge thanks to **Murf AI** for organizing this amazing challenge and encouraging builders to explore the world of voice-first interfaces.
Your tools are enabling the next generation of interactive agents 💜

---
## 🔗 Follow My Progress

📍 Catch my updates on LinkedIn with: [#30DayVoiceAgent](https://www.linkedin.com/in/bhavesh-chouhan-n01/)
Let’s build cool voice stuff together!
---
**Made with ❤️ for the voice AI community**
```
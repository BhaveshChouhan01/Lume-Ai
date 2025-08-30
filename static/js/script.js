// static/js/script.js - Fixed version
console.log("✅ LumeAI streaming script loaded");

let captureCtx = null;
let processor = null;
let sourceNode = null;
let ws = null;
let isRecording = false;
let playbackCtx = null;
let playbackTime = 0;
let unlockedPlayback = false;

const sessionId = `user-${Date.now()}`;
const JITTER_SECS = 0.12;

// DOM elements
const recordBtn = document.getElementById("recordBtn");
const statusEl = document.getElementById("uploadStatus");
const chatHistoryEl = document.getElementById("chatHistory");
const connectionStatus = document.getElementById("connectionStatus");
const statusIndicator = document.getElementById("statusIndicator");
const personaSelect = document.getElementById("personaSelect");
const chatHeader = document.getElementById("chatHeader");

// API Configuration - removed serverUrl as it's not needed
let apiConfig = {
  murfKey: "",
  assemblyKey: "",
  geminiKey: "",
  weatherKey: "",
  newsKey: "",
  tmdbKey: ""
};

// Audio playback state
let audioChunks = [];
let currentAudioSession = null;

/* =============================================================================
   Configuration Management
============================================================================= */

function loadSettings() {
  try {
    const saved = localStorage.getItem('lumeai_config');
    if (saved) {
      const savedConfig = JSON.parse(saved);
      apiConfig = { ...apiConfig, ...savedConfig };
      
      // Populate form fields - removed serverUrl
      const fields = [
        'murfKey', 'assemblyKey', 'geminiKey', 
        'weatherKey', 'newsKey', 'tmdbKey'
      ];
      
      fields.forEach(field => {
        const element = document.getElementById(field);
        if (element) element.value = apiConfig[field] || '';
      });
    }
    
    updateConfigStatus();
  } catch (error) {
    console.error('Error loading settings:', error);
  }
}

function updateConfigStatus() {
  const hasRequiredKeys = apiConfig.assemblyKey && apiConfig.geminiKey;
  
  if (hasRequiredKeys) {
    updateConnectionStatus('status-ready', 'Configuration Ready');
    updateEmptyStateMessage('🎤 Configuration ready! Start recording to begin your conversation...');
  } else {
    updateConnectionStatus('status-disconnected', 'Missing Required API Keys');
    updateEmptyStateMessage('⚙️ Please configure your API keys in the setup menu above!');
  }
}

function updateEmptyStateMessage(message) {
  if (chatHistoryEl) {
    const emptyState = chatHistoryEl.querySelector('.empty-state');
    if (emptyState) {
      emptyState.innerHTML = `<p><em>${message}</em></p>`;
    }
  }
}

function saveSettings() {
  // Get form values - removed serverUrl
  const murfKey = document.getElementById('murfKey')?.value.trim() || '';
  const assemblyKey = document.getElementById('assemblyKey')?.value.trim() || '';
  const geminiKey = document.getElementById('geminiKey')?.value.trim() || '';
  const weatherKey = document.getElementById('weatherKey')?.value.trim() || '';
  const newsKey = document.getElementById('newsKey')?.value.trim() || '';
  const tmdbKey = document.getElementById('tmdbKey')?.value.trim() || '';

  // Basic validation - removed serverUrl validation
  if (!assemblyKey || !geminiKey) {
    alert('⚠️ Please provide at least AssemblyAI and Gemini API keys');
    return;
  }

  // Update configuration - removed serverUrl
  apiConfig = { murfKey, assemblyKey, geminiKey, weatherKey, newsKey, tmdbKey };

  // Save to localStorage
  try {
    localStorage.setItem('lumeai_config', JSON.stringify(apiConfig));
    closeSettings();
    
    updateConnectionStatus('status-ready', 'Configuration saved successfully!');
    updateConfigStatus();
    
    if (statusEl) statusEl.textContent = '✅ Configuration saved! Ready to record';
    
    console.log('📝 Settings saved successfully');
    
  } catch (error) {
    console.error('Error saving settings:', error);
    alert('❌ Error saving configuration. Please try again.');
  }
}

function openSettings() {
  loadSettings();
  document.getElementById('settingsModal')?.classList.add('show');
}

function closeSettings() {
  document.getElementById('settingsModal')?.classList.remove('show');
}

/* =============================================================================
   Connection Status Management
============================================================================= */

function updateConnectionStatus(status, message) {
  if (connectionStatus) connectionStatus.textContent = message;
  if (statusIndicator) statusIndicator.className = `status-indicator ${status}`;
}

/* =============================================================================
   WebSocket URL Helper
============================================================================= */

function getWebSocketUrl() {
  // Use current page's host for WebSocket connection
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}`;
}

/* =============================================================================
   Audio Management
============================================================================= */

async function ensurePlaybackCtx() {
  if (!playbackCtx) {
    playbackCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  
  if (playbackCtx.state === "suspended") {
    try { 
      await playbackCtx.resume(); 
    } catch (e) {
      console.warn('Could not resume audio context:', e);
    }
  }
  
  if (playbackTime === 0) {
    playbackTime = playbackCtx.currentTime + JITTER_SECS;
  }
}

async function playAudioChunk(base64Data) {
  try {
    await ensurePlaybackCtx();
    
    // Convert base64 to ArrayBuffer
    const audioData = Uint8Array.from(atob(base64Data), c => c.charCodeAt(0)).buffer;
    
    // Assume it's PCM16 data from Murf
    const pcm16 = new Int16Array(audioData);
    const float32 = new Float32Array(pcm16.length);
    
    // Convert to float32
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 0x8000;
    }
    
    // Create audio buffer
    const audioBuffer = playbackCtx.createBuffer(1, float32.length, 44100);
    audioBuffer.copyToChannel(float32, 0);
    
    // Play the buffer
    const source = playbackCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(playbackCtx.destination);
    
    const startAt = Math.max(playbackTime, playbackCtx.currentTime + 0.01);
    source.start(startAt);
    playbackTime = startAt + audioBuffer.duration;
    
    console.log(`▶️ Played audio chunk (${audioBuffer.duration.toFixed(2)}s)`);
    
  } catch (err) {
    console.error("❌ Error playing audio chunk:", err);
  }
}

function resetAudioChunks() {
  audioChunks = [];
  currentAudioSession = null;
  playbackTime = 0;
  console.log("🔄 Audio chunks reset");
}

/* =============================================================================
   Chat UI Management
============================================================================= */

function appendChatMessage(sender, text) {
  // Remove empty state on first message
  const emptyState = chatHistoryEl.querySelector('.empty-state');
  if (emptyState) {
    emptyState.remove();
  }
  
  const msgDiv = document.createElement("div");
  const className = sender.toLowerCase() === "you" ? "user" : "assistant";
  msgDiv.classList.add("chat-message", className);
  
  // Apply persona class to assistant messages
  if (className === "assistant" && personaSelect) {
    const currentPersona = personaSelect.value;
    if (currentPersona !== "default") {
      msgDiv.classList.add(currentPersona);
    }
  }
  
  msgDiv.textContent = text;
  chatHistoryEl.appendChild(msgDiv);
  chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
}

function updateStatus(message, isError = false) {
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.className = isError ? 'error' : '';
  }
}

/* =============================================================================
   Audio Processing Utilities
============================================================================= */

function downsampleBuffer(buffer, originalRate, targetRate) {
  if (originalRate === targetRate) return buffer;
  
  const ratio = originalRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  
  let offsetResult = 0;
  let offsetBuffer = 0;
  
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    
    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  
  return result;
}

function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  let offset = 0;
  
  for (let i = 0; i < float32Array.length; i++, offset += 2) {
    const sample = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
  }
  
  return new Int16Array(buffer);
}

/* =============================================================================
   Recording Functions
============================================================================= */

async function startRecording() {
  // Validate configuration
  if (!apiConfig.assemblyKey || !apiConfig.geminiKey) {
    alert('⚠️ Please configure your API keys in the setup menu first!');
    openSettings();
    return;
  }

  try {
    // Initialize playback context for iOS/Chrome
    if (!unlockedPlayback) {
      await ensurePlaybackCtx();
      unlockedPlayback = true;
    }

    // Get microphone access
    const stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        sampleRate: 48000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true
      }
    });

    captureCtx = new (window.AudioContext || window.webkitAudioContext)();
    const inputSampleRate = captureCtx.sampleRate || 48000;

    sourceNode = captureCtx.createMediaStreamSource(stream);
    processor = captureCtx.createScriptProcessor(4096, 1, 1);

    // Build WebSocket URL - use dynamic host instead of serverUrl
    const persona = personaSelect ? personaSelect.value : "default";
    const wsBaseUrl = getWebSocketUrl();
    
    const params = new URLSearchParams({
      session: sessionId,
      persona: persona,
      assembly_key: apiConfig.assemblyKey,
      gemini_key: apiConfig.geminiKey,
      murf_key: apiConfig.murfKey || '',
      weather_key: apiConfig.weatherKey || '',
      news_key: apiConfig.newsKey || '',
      tmdb_key: apiConfig.tmdbKey || ''
    });
    
    const wsUrl = `${wsBaseUrl}/ws/stream?${params}`;
    
    console.log(`Connecting with persona: ${persona}`);
    
    ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      console.log("WebSocket connected");
      updateStatus("Listening...");
      updateConnectionStatus('status-connected', 'Connected');
      
      // Start audio processing
      sourceNode.connect(processor);
      processor.connect(captureCtx.destination);
      
      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const downsampled = downsampleBuffer(inputData, inputSampleRate, 16000);
        const pcm16 = floatTo16BitPCM(downsampled);
        
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(pcm16.buffer);
        }
      };
      
      isRecording = true;
      recordBtn.classList.add("recording");
      recordBtn.textContent = "⏹";
    };

    ws.onmessage = handleWebSocketMessage;
    ws.onerror = handleWebSocketError;
    ws.onclose = handleWebSocketClose;

  } catch (err) {
    console.error("Error starting recording:", err);
    updateStatus("Microphone access denied or not available", true);
    updateConnectionStatus('status-error', 'Microphone Error');
  }
}

function stopRecording() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    console.log("Sending stop signal");
    try {
      ws.send("__stop");
      ws.close();
    } catch (e) {
      console.warn('Error sending stop signal:', e);
    }
  }
  
  // Clean up audio processing
  if (processor) {
    processor.disconnect();
    processor.onaudioprocess = null;
    processor = null;
  }
  
  if (sourceNode) {
    try { 
      sourceNode.disconnect(); 
      sourceNode.mediaStream?.getTracks().forEach(track => track.stop());
    } catch (e) {
      console.warn('Error disconnecting source node:', e);
    }
    sourceNode = null;
  }
  
  if (captureCtx) {
    try { 
      captureCtx.close(); 
    } catch (e) {
      console.warn('Error closing audio context:', e);
    }
    captureCtx = null;
  }
  
  isRecording = false;
  recordBtn.classList.remove("recording");
  recordBtn.textContent = "🎙️";
  updateStatus("Processing...");
}

/* =============================================================================
   WebSocket Message Handlers
============================================================================= */

function handleWebSocketMessage(event) {
  try {
    const data = JSON.parse(event.data);
    console.log("WebSocket message:", data.type);
    
    switch (data.type) {
      case "transcript":
        updateStatus(`${data.text}`);
        if (data.end_of_turn) {
          appendChatMessage("You", data.text);
        }
        break;
        
      case "llm_response":
        appendChatMessage("Assistant", data.text);
        break;
        
      case "llm_chunk":
        // Real-time streaming - could update a partial response area
        console.log("LLM chunk:", data.text);
        break;
        
      case "audio_start":
        console.log("Audio generation started");
        resetAudioChunks();
        currentAudioSession = data.context_id;
        updateStatus("Generating audio...");
        break;
        
      case "audio_chunk":
        console.log(`Audio chunk #${data.chunk_number}`);
        if (data.audio) {
          audioChunks.push({
            data: data.audio,
            chunkNumber: data.chunk_number,
            timestamp: Date.now()
          });
          playAudioChunk(data.audio);
        }
        break;
        
      case "audio_complete":
        console.log(`Audio complete - ${data.total_chunks} chunks`);
        updateStatus("Ready to record");
        break;
        
      case "audio_error":
        console.error("Audio error:", data.message);
        updateStatus(`Audio error: ${data.message}`, true);
        break;
        
      case "error":
        console.error("Server error:", data.message);
        updateStatus(`${data.message}`, true);
        if (data.message.includes('API key') || data.message.includes('Missing')) {
          alert('API Key Error: Please check your configuration.');
          openSettings();
        }
        break;
        
      case "info":
        updateStatus(`${data.message}`);
        break;
        
      default:
        console.log("Unknown message type:", data.type, data);
    }
    
  } catch (err) {
    console.warn("Could not parse WebSocket message:", event.data, err);
  }
}

function handleWebSocketError(error) {
  console.error("WebSocket error:", error);
  updateStatus("Connection error - Check your configuration", true);
  updateConnectionStatus('status-error', 'Connection Error');
}

function handleWebSocketClose() {
  console.log("WebSocket closed");
  updateStatus("Disconnected");
  updateConnectionStatus('status-disconnected', 'Disconnected');
  
  isRecording = false;
  recordBtn.classList.remove("recording");
  recordBtn.textContent = "🎙️";
}

/* =============================================================================
   Event Listeners
============================================================================= */

// Record button
if (recordBtn) {
  recordBtn.addEventListener("click", async () => {
    if (!isRecording) {
      await startRecording();
    } else {
      stopRecording();
    }
  });
}

// Persona selection
if (personaSelect && chatHeader) {
  personaSelect.addEventListener("change", () => {
    const personaLabel = personaSelect.options[personaSelect.selectedIndex].text;
    chatHeader.textContent = `Chat History (${personaLabel})`;
    
    // Apply body class for styling
    document.body.className = "";
    const persona = personaSelect.value;
    if (persona !== "default") {
      document.body.classList.add(persona);
    }
    
    if (isRecording) {
      updateStatus("Persona change will apply to next conversation");
    } else {
      updateStatus(`Switched to ${personaLabel}`);
    }
  });
  
  // Initialize header
  const initialPersonaLabel = personaSelect.options[personaSelect.selectedIndex].text;
  chatHeader.textContent = `Chat History (${initialPersonaLabel})`;
}

/* =============================================================================
   Page Initialization
============================================================================= */

document.addEventListener('DOMContentLoaded', function() {
  loadSettings();
  
  // Settings modal event listeners
  const settingsModal = document.getElementById('settingsModal');
  if (settingsModal) {
    settingsModal.addEventListener('click', function(e) {
      if (e.target === this) closeSettings();
    });
  }
  
  // Close modal on Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeSettings();
    }
  });
});

// Make functions globally available for HTML onclick handlers
window.openSettings = openSettings;
window.closeSettings = closeSettings;
window.saveSettings = saveSettings;
console.log("✅ script.js loaded");

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
const sessionId = Math.random().toString(36).substring(7);

const recordBtn = document.getElementById("recordBtn");
const statusEl = document.getElementById("uploadStatus");
const echoAudio = document.getElementById("echo-audio");

// Toggle record button click
recordBtn.addEventListener("click", () => {
  if (!isRecording) {
    startRecording();
  } else {
    stopRecording();
  }
});

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = processRecording;

    mediaRecorder.start();
    isRecording = true;
    recordBtn.innerHTML = "⏺"; // change to stop icon
    recordBtn.classList.add("recording");
    statusEl.textContent = "🎙️ Recording...";
  } catch (err) {
    alert("Microphone access denied.");
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    isRecording = false;
    recordBtn.innerHTML = "🎙️"; // change back to mic icon
    recordBtn.classList.remove("recording");
    statusEl.textContent = "⏳ Processing...";
  }
}

async function processRecording() {
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  const formData = new FormData();
  formData.append("file", audioBlob, "recording.webm");

  try {
    const res = await fetch(`/agent/chat/${sessionId}`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (res.ok) {
      updateChat(data.chat_history);

      if (data.fallback_text) {
        speakFallback(data.fallback_text);
      } else if (data.audioFile) {
        echoAudio.src = data.audioFile;
        echoAudio.hidden = true;
        echoAudio.play();
      }

      statusEl.textContent = "✅ Response ready!";
    } else {
      statusEl.textContent = "❌ " + (data.detail || "Unknown error");
    }
  } catch (err) {
    statusEl.textContent = "❌ Error: " + err.message;
  }
}

function updateChat(history) {
  const historyBox = document.getElementById("chatHistory");
  historyBox.innerHTML = "";
  history.forEach(msg => {
    const bubble = document.createElement("div");
    bubble.classList.add("chat-message", msg.role);
    const label = msg.role === "user" ? "You" : "AI🤖";
    bubble.innerHTML = `
      <div><strong>${label}:</strong> ${msg.content}</div>
      <div class="chat-timestamp">${new Date().toLocaleTimeString()}</div>
    `;
    historyBox.appendChild(bubble);
  });
  historyBox.scrollTop = historyBox.scrollHeight;
}

function speakFallback(text) {
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1;
  utter.pitch = 1;
  utter.lang = "en-US";
  speechSynthesis.speak(utter);
}

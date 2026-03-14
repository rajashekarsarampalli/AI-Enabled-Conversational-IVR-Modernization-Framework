const API_BASE = "http://127.0.0.1:8000/ivr";

// ──── STATE ────
let sessionId = null;
let ttsEnabled = true;
let isSpeaking = false;
let pendingTranscript = null;
let speechCooldownUntil = 0;

// ──── DOM ELEMENTS ────
const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const resetBtn = document.getElementById("resetBtn");
const muteBtn = document.getElementById("muteBtn");
const suggestionsDiv = document.getElementById("suggestions");
const debugToggle = document.getElementById("debugToggle");
const debugPanel = document.getElementById("debugPanel");

// Debug fields
const dbgState = document.getElementById("dbgState");
const dbgIntent = document.getElementById("dbgIntent");
const dbgPhone = document.getElementById("dbgPhone");
const dbgDept = document.getElementById("dbgDept");
const dbgSession = document.getElementById("dbgSession");
const dbgSource = document.getElementById("dbgSource");


// ──── INIT ────
window.addEventListener("DOMContentLoaded", () => {
    // Do not auto-start the AI conversation here.
    // The first greeting will be sent when the user enters Chat mode
    // or sends their first message.
});


// ──── SEND MESSAGE ────
async function sendMessage(text) {
    if (!text || !text.trim()) return;

    stopSpeaking();

    // Show user message (except initial "hi")
    if (text !== "hi") {
        addMessage(text, "user");
    }

    userInput.value = "";
    clearSuggestions();
    showTyping();

    try {
        const response = await fetch(`${API_BASE}/converse`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                text: text
            })
        });

        removeTyping();

        if (!response.ok) {
            addMessage("Something went wrong. Please try again.", "error");
            return;
        }

        const data = await response.json();

        // Store session ID
        sessionId = data.session_id;

        // Show system response
        addMessage(data.message, "system");

        // Show suggestions
        if (data.suggestions) {
            showSuggestions(data.suggestions);
        }

        // Update debug panel
        updateDebug(data);

        // Speak response if TTS enabled
        if (ttsEnabled) {
            speak(data.message);
        }

    } catch (err) {
        removeTyping();
        addMessage("Cannot connect to server. Make sure the backend is running on port 8000.", "error");
    }
}


// ──── CHAT UI ────
function addMessage(text, type) {
    const msg = document.createElement("div");
    msg.classList.add("message", type);
    msg.textContent = text;
    chatArea.appendChild(msg);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping() {
    const typing = document.createElement("div");
    typing.classList.add("typing");
    typing.id = "typingIndicator";
    typing.textContent = "Thinking";
    chatArea.appendChild(typing);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById("typingIndicator");
    if (typing) typing.remove();
}


// ──── SUGGESTIONS ────
function showSuggestions(suggestions) {
    clearSuggestions();
    suggestions.forEach(s => {
        const btn = document.createElement("button");
        btn.classList.add("suggestion-btn");
        btn.textContent = s;
        btn.addEventListener("click", () => sendMessage(s));
        suggestionsDiv.appendChild(btn);
    });
}

function clearSuggestions() {
    suggestionsDiv.innerHTML = "";
}


// ──── DEBUG PANEL ────
debugToggle.addEventListener("change", () => {
    debugPanel.classList.toggle("visible", debugToggle.checked);
});

function updateDebug(data) {
    dbgState.textContent = data.state || "—";
    dbgIntent.textContent = data.intent || "—";
    dbgSource.textContent = data.intent_source || "—";
    dbgPhone.textContent = data.entities?.phone || "—";
    dbgDept.textContent = data.entities?.department_id || "—";
    dbgSession.textContent = data.session_id || "—";
}


// ──── TEXT-TO-SPEECH (Browser Built-in) ────
let ttsReady = false;

// Browsers block TTS until user interacts with the page — unlock on first click
document.addEventListener("click", () => {
    if (!ttsReady) {
        ttsReady = true;
        // Warm up speechSynthesis with a silent utterance
        const warmup = new SpeechSynthesisUtterance("");
        warmup.volume = 0;
        window.speechSynthesis.speak(warmup);
    }
}, { once: false });

// ──── VOICE SELECTOR (Deepgram Aura) ────
const voiceSelect = document.getElementById("voiceSelect");
let selectedVoice = "asteria";
let currentAudio = null;

function setSpeaking(active) {
    isSpeaking = active;
    if (!active) {
        speechCooldownUntil = Date.now() + 500;
    }
}

function stopSpeaking() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    window.speechSynthesis.cancel();
    setSpeaking(false);
}

async function populateVoices() {
    try {
        const r = await fetch(`${API_BASE}/tts/voices`);
        const voices = await r.json();
        if (!voices || Object.keys(voices).length === 0) {
            populateBrowserVoices();
            return;
        }
        voiceSelect.innerHTML = "";

        for (const [key, label] of Object.entries(voices)) {
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = label;
            voiceSelect.appendChild(opt);
        }
        voiceSelect.value = "asteria";
        selectedVoice = "asteria";
    } catch (err) {
        // Deepgram unavailable — fall back to browser voices
        console.warn("Deepgram voices unavailable, using browser TTS");
        populateBrowserVoices();
    }
}

function populateBrowserVoices() {
    const voices = window.speechSynthesis.getVoices();
    voiceSelect.innerHTML = "";
    const englishVoices = voices.filter(v => v.lang.startsWith("en"));
    const list = englishVoices.length ? englishVoices : voices;
    list.forEach((v, i) => {
        const opt = document.createElement("option");
        opt.value = `browser_${i}`;
        opt.textContent = `${v.name} (${v.lang})`;
        voiceSelect.appendChild(opt);
    });
    if (list.length) {
        voiceSelect.value = voiceSelect.options[0]?.value;
        selectedVoice = voiceSelect.value;
    }
}

// Load voices after DOM ready
populateVoices();

voiceSelect.addEventListener("change", () => {
    selectedVoice = voiceSelect.value;
});

async function speak(text) {
    stopSpeaking();

    // Use Deepgram only for Chat mode; in Keypad mode use fast browser TTS
    const shouldUseDeepgram =
        currentMode === "chat" && !selectedVoice.startsWith("browser_");

    if (shouldUseDeepgram) {
        // Use Deepgram TTS
        try {
            const r = await fetch(`${API_BASE}/tts/speak`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, voice: selectedVoice })
            });
            if (!r.ok) throw new Error("TTS request failed");
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            currentAudio = new Audio(url);
            currentAudio.onplay = () => setSpeaking(true);
            currentAudio.onended = () => {
                URL.revokeObjectURL(url);
                currentAudio = null;
                setSpeaking(false);
            };
            currentAudio.onerror = () => {
                URL.revokeObjectURL(url);
                currentAudio = null;
                setSpeaking(false);
            };
            currentAudio.play();
            return;
        } catch (err) {
            console.warn("Deepgram TTS failed, falling back to browser:", err);
        }
    }

    // Browser fallback
    if (!("speechSynthesis" in window)) return;
    const cleanText = text
        .replace(/[•]/g, "")
        .replace(/\d+\./g, "")
        .replace(/[#*\-]+/g, "")
        .replace(/\n+/g, ". ")
        .replace(/\s+/g, " ")
        .trim();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = "en-IN";
    utterance.rate = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const englishVoices = voices.filter(v => v.lang.startsWith("en"));
    const list = englishVoices.length ? englishVoices : voices;
    const idx = parseInt((selectedVoice || "").replace("browser_", ""), 10);
    if (!isNaN(idx) && list[idx]) utterance.voice = list[idx];
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
}

muteBtn.addEventListener("click", () => {
    ttsEnabled = !ttsEnabled;
    muteBtn.textContent = ttsEnabled ? "🔊 TTS On" : "🔇 TTS Off";
    if (!ttsEnabled) {
        stopSpeaking();
    }
});


// ──── SPEECH-TO-TEXT (Browser Built-in Web Speech API) ────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 5;

    recognition.onresult = (event) => {
        const result = event.results[0];
        let best = result[0];
        for (let i = 1; i < result.length; i++) {
            if (result[i].confidence > best.confidence) {
                best = result[i];
            }
        }
        const transcript = best.transcript;
        pendingTranscript = transcript;
        userInput.value = transcript;
        recognition.stop();
    };

    recognition.onend = () => {
        isListening = false;
        micBtn.classList.remove("listening");
        micBtn.textContent = "🎤";
        // Leave the recognized text in the input so the user can review/edit
        // and press Send manually, instead of auto-sending potentially misheard text.
    };

    recognition.onerror = (event) => {
        isListening = false;
        pendingTranscript = null;
        micBtn.classList.remove("listening");
        micBtn.textContent = "🎤";
        if (event.error !== "no-speech") {
            addMessage("Speech recognition error: " + event.error, "error");
        }
    };
} else {
    micBtn.title = "Speech recognition not supported in this browser";
    micBtn.style.opacity = "0.4";
}

micBtn.addEventListener("click", () => {
    if (!recognition) {
        addMessage("Speech recognition is not supported in your browser. Use Chrome or Edge.", "error");
        return;
    }

    if (isListening) {
        recognition.stop();
    } else {
        if (isSpeaking) {
            stopSpeaking();
        }

        if (Date.now() < speechCooldownUntil) {
            setTimeout(() => {
                if (!isListening) {
                    micBtn.click();
                }
            }, speechCooldownUntil - Date.now());
            return;
        }

        isListening = true;
        micBtn.classList.add("listening");
        micBtn.textContent = "⏹️";
        recognition.start();
    }
});


// ──── INPUT HANDLERS ────
sendBtn.addEventListener("click", () => {
    sendMessage(userInput.value);
});

userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        sendMessage(userInput.value);
    }
});


// ──── RESET ────
resetBtn.addEventListener("click", async () => {
    chatArea.innerHTML = "";
    clearSuggestions();
    window.speechSynthesis.cancel();

    if (currentMode === "keypad") {
        // Reset only the DTMF flow, keep AI chat idle
        keypadInput.value = "";
        dtmfState = "main_menu";
        loadDTMFMenu("/start");
        sessionId = null;
    } else if (currentMode === "chat") {
        // Reset conversational AI session
        if (sessionId) {
            try {
                await fetch(`${API_BASE}/converse/reset`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ session_id: sessionId, text: "" })
                });
            } catch (_) {}
        }
        sessionId = null;
        sendMessage("hi");
    }
});


// ──── MODE SWITCHING ────
const chatModeBtn = document.getElementById("chatModeBtn");
const keypadModeBtn = document.getElementById("keypadModeBtn");
const chatInputArea = document.getElementById("chatInputArea");
const keypadContainer = document.getElementById("keypadContainer");
const keypadMenu = document.getElementById("keypadMenu");
const keypadInput = document.getElementById("keypadInput");
const keypadSendBtn = document.getElementById("keypadSendBtn");

let currentMode = "chat";

chatModeBtn.addEventListener("click", () => switchMode("chat"));
keypadModeBtn.addEventListener("click", () => switchMode("keypad"));

function switchMode(mode) {
    // Stop any ongoing TTS when switching modes to avoid overlap
    stopSpeaking();

    currentMode = mode;

    chatModeBtn.classList.toggle("active", mode === "chat");
    keypadModeBtn.classList.toggle("active", mode === "keypad");

    chatInputArea.style.display = mode === "chat" ? "flex" : "none";
    keypadContainer.style.display = mode === "keypad" ? "block" : "none";
    suggestionsDiv.style.display = mode === "chat" ? "flex" : "none";

    if (mode === "keypad") {
        dtmfState = "main_menu";
        keypadInput.value = "";
        loadDTMFMenu("/start");
    } else if (mode === "chat") {
        // Start conversational AI greeting on first entry to Chat mode
        if (!sessionId) {
            sendMessage("hi");
        }
    }
}


// ──── KEYPAD / DTMF MODE ────

let dtmfState = "main_menu";
let dtmfPhoneDigits = "";
let dtmfCollectingPhone = false;
let dtmfPhoneCallback = null;

// Route map for DTMF navigation
const DTMF_ROUTES = {
    "main_menu": {
        route: "/start",
        keys: {
            "1": { next: "appointments_menu", route: "/appointments" },
            "2": { next: "lab_menu", route: "/lab" },
            "3": { next: "billing_menu", route: "/billing" },
            "4": { next: "reception_menu", route: "/reception" },
            "5": { next: "emergency_menu", route: "/emergency" }
        }
    },
    "appointments_menu": {
        keys: {
            "1": { next: "departments", route: "/departments" },
            "2": { next: "main_menu", route: "/start" }
        }
    },
    "departments": {
        keys: {
            "1": { action: "book", dept: 1 },
            "2": { action: "book", dept: 2 },
            "3": { action: "book", dept: 3 },
            "4": { action: "book", dept: 4 },
            "5": { action: "book", dept: 5 },
            "6": { action: "book", dept: 6 },
            "0": { next: "appointments_menu", route: "/appointments" }
        }
    },
    "lab_menu": {
        keys: {
            "1": { action: "lab_check" },
            "2": { next: "main_menu", route: "/start" }
        }
    },
    "billing_menu": {
        keys: {
            "1": { action: "billing_check" },
            "2": { next: "main_menu", route: "/start" }
        }
    },
    "emergency_menu": {
        keys: {
            "1": { action: "emergency", type: "ambulance" },
            "2": { action: "emergency", type: "fire" },
            "3": { next: "main_menu", route: "/start" }
        }
    },
    "reception_menu": {
        keys: {
            "1": { action: "reception_inquiry" },
            "2": { action: "reception_connect" },
            "3": { next: "main_menu", route: "/start" }
        }
    }
};

async function loadDTMFMenu(route) {
    try {
        const r = await fetch(`${API_BASE}${route}`);
        const data = await r.json();

        addMessage(data.message, "system");
        if (ttsEnabled) speak(data.message);

        // Show menu options on the keypad
        keypadMenu.innerHTML = "";
        if (data.options) {
            for (const [key, label] of Object.entries(data.options)) {
                const opt = document.createElement("div");
                opt.classList.add("menu-option");
                opt.innerHTML = `<span class="menu-key">${key}</span><span class="menu-label">${label}</span>`;
                keypadMenu.appendChild(opt);
            }
        }
    } catch (err) {
        addMessage("Cannot connect to server.", "error");
    }
}

function startPhoneCollection(callback) {
    dtmfCollectingPhone = true;
    dtmfPhoneDigits = "";
    dtmfPhoneCallback = callback;
    keypadInput.value = "";
    addMessage("Please enter your 10-digit phone number, then press #.", "system");
    if (ttsEnabled) speak("Please enter your 10-digit phone number, then press pound.");
    keypadMenu.innerHTML = '<div class="menu-option"><span class="menu-label">Enter 10 digits, then press #</span></div>';
}

// Handle keypad button clicks
document.querySelectorAll(".key-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        const key = btn.dataset.key;

        // Collecting phone number
        if (dtmfCollectingPhone) {
            if (key === "#") {
                if (dtmfPhoneDigits.length === 10) {
                    dtmfCollectingPhone = false;
                    const phone = dtmfPhoneDigits;
                    dtmfPhoneDigits = "";
                    keypadInput.value = "";
                    if (dtmfPhoneCallback) dtmfPhoneCallback(phone);
                } else {
                    addMessage("Please enter exactly 10 digits.", "error");
                }
            } else if (key === "*") {
                dtmfPhoneDigits = dtmfPhoneDigits.slice(0, -1);
                keypadInput.value = dtmfPhoneDigits;
            } else {
                if (dtmfPhoneDigits.length < 10) {
                    dtmfPhoneDigits += key;
                    keypadInput.value = dtmfPhoneDigits;
                }
            }
            return;
        }

        // Normal menu navigation
        const stateConfig = DTMF_ROUTES[dtmfState];
        if (!stateConfig || !stateConfig.keys || !stateConfig.keys[key]) {
            addMessage(`Key ${key} is not valid here.`, "error");
            return;
        }

        const action = stateConfig.keys[key];
        addMessage(`Pressed: ${key}`, "user");

        if (action.route) {
            dtmfState = action.next;
            loadDTMFMenu(action.route);
        } else if (action.action === "book") {
            startPhoneCollection(async (phone) => {
                try {
                    const r = await fetch(`${API_BASE}/book`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ phone, department_id: action.dept })
                    });
                    const data = await r.json();
                    addMessage(data.message, "system");
                    if (ttsEnabled) speak(data.message);
                    dtmfState = "main_menu";
                    setTimeout(() => loadDTMFMenu("/start"), 3000);
                } catch (err) {
                    addMessage("Error booking appointment.", "error");
                }
            });
        } else if (action.action === "lab_check") {
            startPhoneCollection(async (phone) => {
                try {
                    const r = await fetch(`${API_BASE}/lab/check`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ phone })
                    });
                    const data = await r.json();
                    let msg = data.message;
                    if (data.reports) {
                        data.reports.forEach(rp => { msg += `\n  • ${rp.report_name} — ${rp.status} (${rp.date})`; });
                    }
                    addMessage(msg, "system");
                    if (ttsEnabled) speak(msg);
                    dtmfState = "main_menu";
                    setTimeout(() => loadDTMFMenu("/start"), 3000);
                } catch (err) {
                    addMessage("Error checking lab reports.", "error");
                }
            });
        } else if (action.action === "billing_check") {
            startPhoneCollection(async (phone) => {
                try {
                    const r = await fetch(`${API_BASE}/billing/check`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ phone })
                    });
                    const data = await r.json();
                    addMessage(data.message, "system");
                    if (ttsEnabled) speak(data.message);
                    dtmfState = "main_menu";
                    setTimeout(() => loadDTMFMenu("/start"), 3000);
                } catch (err) {
                    addMessage("Error checking billing.", "error");
                }
            });
        } else if (action.action === "emergency") {
            startPhoneCollection(async (phone) => {
                try {
                    const r = await fetch(`${API_BASE}/emergency/confirm`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ phone, type: action.type })
                    });
                    const data = await r.json();
                    addMessage(data.message, "system");
                    if (ttsEnabled) speak(data.message);
                    dtmfState = "main_menu";
                    setTimeout(() => loadDTMFMenu("/start"), 3000);
                } catch (err) {
                    addMessage("Error contacting emergency.", "error");
                }
            });
        } else if (action.action === "reception_inquiry") {
            startPhoneCollection(async (phone) => {
                try {
                    const r = await fetch(`${API_BASE}/reception/inquiry`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ phone })
                    });
                    const data = await r.json();
                    addMessage(data.message, "system");
                    if (ttsEnabled) speak(data.message);
                    dtmfState = "main_menu";
                    setTimeout(() => loadDTMFMenu("/start"), 3000);
                } catch (err) {
                    addMessage("Error connecting to reception.", "error");
                }
            });
        } else if (action.action === "reception_connect") {
            startPhoneCollection(async (phone) => {
                try {
                    const r = await fetch(`${API_BASE}/reception/connect`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ phone })
                    });
                    const data = await r.json();
                    addMessage(data.message, "system");
                    if (ttsEnabled) speak(data.message);
                    dtmfState = "main_menu";
                    setTimeout(() => loadDTMFMenu("/start"), 3000);
                } catch (err) {
                    addMessage("Error connecting to front desk.", "error");
                }
            });
        }
    });
});

keypadSendBtn.addEventListener("click", () => {
    if (dtmfCollectingPhone && dtmfPhoneDigits.length === 10) {
        dtmfCollectingPhone = false;
        const phone = dtmfPhoneDigits;
        dtmfPhoneDigits = "";
        keypadInput.value = "";
        if (dtmfPhoneCallback) dtmfPhoneCallback(phone);
    }
});

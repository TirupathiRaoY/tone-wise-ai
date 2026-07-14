/* ToneWise AI browser behaviour. The Python server provides the /api routes. */

const FALLBACK_OPTIONS = {
  tones: ["Formal", "Casual", "Very Simple (ELI5)", "Encouraging/Supportive"],
  languages: ["English", "Hindi", "Tamil", "Telugu", "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati", "Punjabi", "Urdu", "Spanish", "French", "German", "Portuguese", "Arabic", "Japanese", "Korean", "Chinese (Simplified)"],
  default_tone: "Casual",
  default_language: "English",
};

const sourceText = document.querySelector("#source-text");
const characterCount = document.querySelector("#character-count");
const fileInput = document.querySelector("#file-input");
const fileName = document.querySelector("#file-name");
const removeFileButton = document.querySelector("#remove-file");
const toneSelect = document.querySelector("#tone-select");
const languageSelect = document.querySelector("#language-select");
const simplifyButton = document.querySelector("#simplify-button");
const statusMessage = document.querySelector("#status-message");
const resultSection = document.querySelector("#result-section");
const simplifiedResult = document.querySelector("#simplified-result");
const providerLabel = document.querySelector("#provider-label");
const languageLabel = document.querySelector("#language-label");
const downloadBox = document.querySelector("#download-box");
const downloadTxt = document.querySelector("#download-txt");
const downloadDocx = document.querySelector("#download-docx");
const shareTeamBox = document.querySelector("#share-team-box");
const shareTeamSelect = document.querySelector("#share-team-select");
const shareTeamButton = document.querySelector("#share-team-button");
const shareTeamMessage = document.querySelector("#share-team-message");
const chatSection = document.querySelector("#chat-section");
const chatMessages = document.querySelector("#chat-messages");
const chatForm = document.querySelector("#chat-form");
const chatQuestion = document.querySelector("#chat-question");
const feedbackBox = document.querySelector("#feedback-box");
const feedbackButtons = document.querySelectorAll(".feedback-button");
const feedbackMessage = document.querySelector("#feedback-message");
const teamSection = document.querySelector("#team-section");
const shareButton = document.querySelector("#share-button");
const shareMessage = document.querySelector("#share-message");
const teamComments = document.querySelector("#team-comments");
const commentsEmpty = document.querySelector("#comments-empty");
const teamForm = document.querySelector("#team-form");
const teamName = document.querySelector("#team-name");
const teamNote = document.querySelector("#team-note");
const readAloudButton = document.querySelector("#read-aloud-button");
const sourceVoiceButton = document.querySelector("#source-voice-button");
const chatVoiceButton = document.querySelector("#chat-voice-button");
const voiceInputStatus = document.querySelector("#voice-input-status");
const voiceRepliesToggle = document.querySelector("#voice-replies-toggle");
const signinLink = document.querySelector("#signin-link");
const logoutButton = document.querySelector("#logout-button");

let conversationId = null;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const SPEECH_LOCALES = { Hindi: "hi-IN", Tamil: "ta-IN", Telugu: "te-IN", Malayalam: "ml-IN", Kannada: "kn-IN", Bengali: "bn-IN", Marathi: "mr-IN", Gujarati: "gu-IN", Punjabi: "pa-IN", Urdu: "ur-PK", Spanish: "es-ES", French: "fr-FR", German: "de-DE", Portuguese: "pt-BR", Arabic: "ar-SA", Japanese: "ja-JP", Korean: "ko-KR", "Chinese (Simplified)": "zh-CN" };

function speechLocale() { return SPEECH_LOCALES[languageSelect.value] || "en-US"; }

function speakText(text) {
  if (localStorage.getItem("tonewise_voice_muted") === "true" || !voiceRepliesToggle.checked || !("speechSynthesis" in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = speechLocale();
  window.speechSynthesis.speak(utterance);
}

function startVoiceInput(target, button, statusTarget) {
  if (!SpeechRecognition) {
    statusTarget.textContent = "Voice input is not supported by this browser. Try Chrome or Edge.";
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = speechLocale();
  recognition.interimResults = true;
  recognition.continuous = false;
  let finalText = "";
  button.disabled = true;
  button.classList.add("listening");
  statusTarget.textContent = "Listening...";
  recognition.onresult = (event) => {
    let interimText = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      if (event.results[index].isFinal) finalText += event.results[index][0].transcript;
      else interimText += event.results[index][0].transcript;
    }
    target.value = finalText || interimText;
    if (target === sourceText) updateCharacterCount();
  };
  recognition.onerror = (event) => { statusTarget.textContent = event.error === "not-allowed" ? "Microphone access was blocked. Allow it in your browser settings." : "I couldn't hear that. Please try again."; };
  recognition.onend = () => { button.disabled = false; button.classList.remove("listening"); if (finalText) statusTarget.textContent = "Voice input ready."; };
  try { recognition.start(); } catch { button.disabled = false; button.classList.remove("listening"); statusTarget.textContent = "Voice input is already active. Please try again in a moment."; }
}

function fillSelect(selectElement, choices, selectedChoice) {
  selectElement.innerHTML = "";
  choices.forEach((choice) => {
    const option = document.createElement("option");
    option.value = choice;
    option.textContent = choice;
    option.selected = choice === selectedChoice;
    selectElement.append(option);
  });
}

function setSelectorOptions(options) {
  fillSelect(toneSelect, options.tones, options.default_tone);
  fillSelect(languageSelect, options.languages, options.default_language);
}

async function loadSelectorOptions() {
  setSelectorOptions(FALLBACK_OPTIONS);
  try {
    const response = await fetch("/api/options");
    if (response.ok) setSelectorOptions(await response.json());
  } catch {
    // The page can still show its built-in choices while the server is offline.
  }
}

async function loadAccountPreferences() {
  try {
    const response = await fetch("/api/auth/me");
    const account = await response.json();
    if (!account.authenticated) return;
    signinLink.textContent = account.user.full_name.split(" ")[0];
    signinLink.href = "/dashboard";
    logoutButton.hidden = false;
    if (account.preferences) {
      if ([...toneSelect.options].some((option) => option.value === account.preferences.default_tone)) toneSelect.value = account.preferences.default_tone;
    }
  } catch { /* The existing app remains usable if auth is temporarily offline. */ }
}

logoutButton.addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.assign("/signin");
});

function updateCharacterCount() {
  characterCount.textContent = `${sourceText.value.length.toLocaleString()} / 12,000 characters`;
}

function setStatus(message = "", isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

function clearSelectedFile() {
  fileInput.value = "";
  fileName.textContent = "No file selected";
  removeFileButton.hidden = true;
}

function showMessage(text, type) {
  const message = document.createElement("div");
  message.className = `message ${type}`;
  message.textContent = text;
  chatMessages.append(message);
  message.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function displaySavedMessages(messages) {
  chatMessages.innerHTML = "";
  messages.forEach((message) => showMessage(message.content, message.sender_role));
}

function setDownloadLinks() {
  const safeId = encodeURIComponent(conversationId);
  downloadTxt.href = `/api/conversations/${safeId}/download?format=txt`;
  downloadDocx.href = `/api/conversations/${safeId}/download?format=docx`;
}

function displayConversation(data, shouldSpeak = false) {
  conversationId = data.session_id;
  simplifiedResult.textContent = data.response;
  readAloudButton.hidden = !("speechSynthesis" in window);
  resultSection.hidden = false;
  chatSection.hidden = false;
  feedbackBox.hidden = false;
  downloadBox.hidden = false;
  loadTeamsForSharing();
  teamSection.hidden = false;
  providerLabel.textContent = data.provider_used ? `Powered by ${data.provider_used}` : "";
  providerLabel.hidden = !data.provider_used;
  languageLabel.textContent = data.language ? data.language : "";
  languageLabel.hidden = !data.language;
  feedbackMessage.textContent = "";
  feedbackButtons.forEach((button) => { button.disabled = false; });
  setDownloadLinks();
  displaySavedMessages(data.messages || []);

  if (data.tone) toneSelect.value = data.tone;
  if (data.language) languageSelect.value = data.language;
  loadTeamComments();
  if (shouldSpeak) speakText(data.response);
}

async function loadTeamsForSharing() {
  try {
    const response = await fetch("/api/dashboard/teams");
    if (!response.ok) return;
    const data = await response.json();
    shareTeamBox.hidden = data.teams.length === 0;
    shareTeamSelect.innerHTML = data.teams.map((team) => `<option value="${team.id}">${team.name}</option>`).join("");
  } catch { shareTeamBox.hidden = true; }
}

shareTeamButton.addEventListener("click", async () => {
  if (!conversationId || !shareTeamSelect.value) return;
  shareTeamButton.disabled = true;
  try {
    const response = await fetch(`/api/dashboard/teams/${encodeURIComponent(shareTeamSelect.value)}/items/${encodeURIComponent(conversationId)}/share`, { method: "POST" });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.detail || "Could not share this item.");
    shareTeamMessage.textContent = "Shared with your team.";
  } catch (error) { shareTeamMessage.textContent = error.message || "Could not share this item."; }
  finally { shareTeamButton.disabled = false; }
});

readAloudButton.addEventListener("click", () => {
  if (!("speechSynthesis" in window)) return;
  const wasEnabled = voiceRepliesToggle.checked;
  voiceRepliesToggle.checked = true;
  speakText(simplifiedResult.textContent);
  voiceRepliesToggle.checked = wasEnabled;
});

sourceVoiceButton.addEventListener("click", () => startVoiceInput(sourceText, sourceVoiceButton, voiceInputStatus));
chatVoiceButton.addEventListener("click", () => startVoiceInput(chatQuestion, chatVoiceButton, voiceInputStatus));
voiceRepliesToggle.checked = localStorage.getItem("tonewise_voice_muted") !== "true";
voiceRepliesToggle.addEventListener("change", () => {
  localStorage.setItem("tonewise_voice_muted", String(!voiceRepliesToggle.checked));
  if (!voiceRepliesToggle.checked && "speechSynthesis" in window) window.speechSynthesis.cancel();
});

function renderTeamComment(comment) {
  const card = document.createElement("article");
  card.className = "team-comment";
  const header = document.createElement("div");
  header.className = "team-comment-header";
  const author = document.createElement("span");
  author.className = "team-comment-author";
  author.textContent = comment.author_name;
  const time = document.createElement("span");
  time.className = "team-comment-time";
  time.textContent = comment.created_at || "Just now";
  const content = document.createElement("p");
  content.className = "team-comment-content";
  content.textContent = comment.content;
  header.append(author, time);
  card.append(header, content);
  teamComments.append(card);
}

async function loadTeamComments() {
  if (!conversationId) return;
  teamComments.innerHTML = "";
  try {
    const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}/comments`);
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.detail || "Could not load team notes.");
    commentsEmpty.hidden = data.comments.length > 0;
    data.comments.forEach(renderTeamComment);
  } catch (error) {
    commentsEmpty.hidden = false;
    commentsEmpty.textContent = error.message || "Team notes could not be loaded.";
  }
}

sourceText.addEventListener("input", updateCharacterCount);
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  fileName.textContent = file.name;
  removeFileButton.hidden = false;
  setStatus("");
});
removeFileButton.addEventListener("click", clearSelectedFile);

simplifyButton.addEventListener("click", async () => {
  const text = sourceText.value.trim();
  const file = fileInput.files[0];
  if (!text && !file) {
    setStatus("Please paste some content or choose a TXT, PDF, or DOCX file first.", true);
    return;
  }

  simplifyButton.disabled = true;
  simplifyButton.textContent = "Simplifying...";
  setStatus("ToneWise AI is preparing your clear explanation...");
  const formData = new FormData();
  formData.append("text", text);
  formData.append("tone", toneSelect.value);
  formData.append("language", languageSelect.value);
  if (file) formData.append("file", file);

  try {
    const response = await fetch("/api/simplify", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.detail || data.errors?.[0] || "Unable to simplify this content.");
    history.replaceState({}, "", `?conversation=${encodeURIComponent(data.session_id)}`);
    displayConversation(data, true);
    setStatus("Your explanation is ready.");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setStatus(error.message || "The server is not ready yet.", true);
  } finally {
    simplifyButton.disabled = false;
    simplifyButton.textContent = "Simplify this content";
  }
});

feedbackButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    if (!conversationId) return;
    feedbackButtons.forEach((item) => { item.disabled = true; });
    feedbackMessage.textContent = "Saving your feedback...";
    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: conversationId, was_clear: button.dataset.clear === "true" }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.detail || "Could not save feedback.");
      feedbackMessage.textContent = "Thank you - your feedback was saved.";
    } catch (error) {
      feedbackMessage.textContent = error.message || "Feedback could not be saved. Please try again.";
      feedbackButtons.forEach((item) => { item.disabled = false; });
    }
  });
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = chatQuestion.value.trim();
  if (!question || !conversationId) return;
  showMessage(question, "user");
  chatQuestion.value = "";
  const submitButton = chatForm.querySelector("button");
  submitButton.disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: conversationId, question }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.detail || data.errors?.[0]);
    showMessage(data.response, "assistant");
    speakText(data.response);
  } catch (error) {
    showMessage(error.message || "I could not answer that question. Please try again.", "assistant");
  } finally {
    submitButton.disabled = false;
  }
});

shareButton.addEventListener("click", async () => {
  if (!conversationId) return;
  const link = new URL(window.location.href);
  link.searchParams.set("conversation", conversationId);
  try {
    await navigator.clipboard.writeText(link.toString());
    shareMessage.textContent = "Share link copied. Send it to your team.";
  } catch {
    window.prompt("Copy this share link:", link.toString());
  }
});

teamForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!conversationId) return;
  const authorName = teamName.value.trim();
  const content = teamNote.value.trim();
  if (!authorName || !content) {
    shareMessage.textContent = "Please enter both your name and a team note.";
    return;
  }
  const submitButton = teamForm.querySelector("button");
  submitButton.disabled = true;
  try {
    const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author_name: authorName, content }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.detail || "Could not save this team note.");
    commentsEmpty.hidden = true;
    renderTeamComment(data.comment);
    teamNote.value = "";
    shareMessage.textContent = "Team note added.";
  } catch (error) {
    shareMessage.textContent = error.message || "Team note could not be saved.";
  } finally {
    submitButton.disabled = false;
  }
});

async function loadSharedConversation() {
  const sharedId = new URLSearchParams(window.location.search).get("conversation");
  if (!sharedId) return;
  setStatus("Loading the shared explanation...");
  try {
    const response = await fetch(`/api/conversations/${encodeURIComponent(sharedId)}`);
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.detail || "This shared explanation could not be loaded.");
    displayConversation(data);
    setStatus("Shared explanation loaded.");
  } catch (error) {
    setStatus(error.message || "This shared explanation could not be loaded.", true);
  }
}

async function initializePage() {
  await loadSelectorOptions();
  await loadAccountPreferences();
  updateCharacterCount();
  await loadSharedConversation();
  const voiceText = new URLSearchParams(window.location.search).get("voiceText");
  if (voiceText) {
    sourceText.value = voiceText;
    updateCharacterCount();
    setStatus("Your spoken text is ready. Choose a style, then simplify it.");
  }
}

initializePage();

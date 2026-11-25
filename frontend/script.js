/* ToneWise AI browser behaviour. The Python server provides the /api routes. */

const FALLBACK_OPTIONS = {
  tones: ["Formal", "Casual", "Very Simple (ELI5)", "Encouraging/Supportive"],
  languages: ["English", "Hindi", "Tamil", "Telugu", "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati", "Punjabi", "Urdu", "Spanish", "French", "German", "Portuguese", "Arabic", "Japanese", "Korean", "Chinese (Simplified)"],
  default_tone: "Casual",
  default_language: "English",
};

const sourceText = document.querySelector("#source-text");
const sourceTextLabel = document.querySelector('label[for="source-text"]');
const questionModeHelp = document.querySelector("#question-mode-help");
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
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const MAX_FILE_SIZE_LABEL = "10 MB";
const selectedJobTool = new URLSearchParams(window.location.search).get("job_tool");

let conversationId = null;
let currentUserType = null;
const studentTools = document.querySelector("#student-tools");
const businessTools = document.querySelector("#business-tools");
const professionalTools = document.querySelector("#professional-tools");
const jobSeekerTools = document.querySelector("#job-seeker-tools");
const toneControl = document.querySelector("#tone-control");
let preselectedJobToolApplied = false;
const SPEECH_LOCALES = { Hindi: "hi-IN", Tamil: "ta-IN", Telugu: "te-IN", Malayalam: "ml-IN", Kannada: "kn-IN", Bengali: "bn-IN", Marathi: "mr-IN", Gujarati: "gu-IN", Punjabi: "pa-IN", Urdu: "ur-PK", Spanish: "es-ES", French: "fr-FR", German: "de-DE", Portuguese: "pt-BR", Arabic: "ar-SA", Japanese: "ja-JP", Korean: "ko-KR", "Chinese (Simplified)": "zh-CN" };

const roleInterfaces = {
  Student: {
    key: "student",
    mark: "ST",
    eyebrow: "YOUR PERSONAL STUDY SPACE",
    title: "Make learning click,<br><span>one concept at a time.</span>",
    description: "Turn class notes, textbooks, research, and technical topics into clear study material.",
    guideLabel: "STUDENT STUDY SPACE",
    guideTitle: "Learn it, see it, remember it.",
    guideDescription: "Upload study material and choose optional study tools to deepen your understanding.",
    tips: ["Simplify difficult concepts", "Add examples and a quiz", "Keep your explanation to review later"],
    placeholder: "Paste class notes, textbook excerpts, research, or a topic you want to understand…",
  },
  "Working Professional": {
    key: "professional",
    mark: "WP",
    eyebrow: "YOUR WORKDAY CLARITY SPACE",
    title: "Get to the point,<br><span>and move work forward.</span>",
    description: "Make reports, policies, meeting notes, and technical messages easier to understand and act on.",
    guideLabel: "WORKING PROFESSIONAL",
    guideTitle: "Turn dense work into clear next steps.",
    guideDescription: "Upload a work document, ask a question, and select optional tools to find key details.",
    tips: ["Get answers from reports and policies", "Find key points, deadlines, and responsibilities", "Share a clear version with your team"],
    placeholder: "Paste a report, policy, meeting note, or work message you want to make clearer…",
  },
  "Job Seeker": {
    key: "job-seeker",
    mark: "JS",
    eyebrow: "YOUR CAREER CLARITY SPACE",
    title: "Make your next move<br><span>with confidence.</span>",
    description: "Understand job descriptions, prepare for interviews, and make sense of career documents.",
    guideLabel: "JOB SEEKER",
    guideTitle: "Get ready for the opportunity ahead.",
    guideDescription: "Break down career information into clear language so you can focus on your next step.",
    tips: ["Decode job requirements", "Understand offer documents", "Prepare clear interview answers"],
    placeholder: "Paste a job description, interview prompt, resume feedback, or offer detail…",
    chatPlaceholder: "For example: Which qualifications are essential for this role?",
  },
  "Business Owner": {
    key: "business-owner",
    mark: "BO",
    eyebrow: "YOUR BUSINESS CLARITY SPACE",
    title: "Make complex business<br><span>decisions clearer.</span>",
    description: "Understand business documents and communicate your products, processes, and decisions clearly.",
    guideLabel: "BUSINESS OWNER",
    guideTitle: "Spend less time decoding paperwork.",
    guideDescription: "Simplify operational, customer, financial, or contract language while keeping important details intact.",
    tips: ["Clarify contracts and invoices", "Understand operational information", "Write clear customer messages"],
    placeholder: "Paste a contract excerpt, invoice detail, procedure, or customer message…",
  },
  Other: {
    key: "other",
    mark: "TW",
    eyebrow: "YOUR PERSONAL CLARITY SPACE",
    title: "Make the complicated<br><span>feel understandable.</span>",
    description: "Bring any document, unfamiliar topic, or long message and get a clear explanation.",
    guideLabel: "YOUR TONEWISE SPACE",
    guideTitle: "Clarity for whatever you’re working through.",
    guideDescription: "Simplify unfamiliar terms, long documents, and complicated ideas at your own pace.",
    tips: ["Understand complex documents", "Learn unfamiliar terminology", "Ask follow-up questions"],
    placeholder: "Paste a document, unfamiliar topic, or message you want explained…",
  },
};

function applyRoleInterface(userType) {
  const config = roleInterfaces[userType] || roleInterfaces.Other;
  document.body.dataset.role = config.key;
  document.querySelector("#workspace-eyebrow").textContent = config.eyebrow;
  document.querySelector("#workspace-title").innerHTML = config.title;
  document.querySelector("#workspace-description").textContent = config.description;
  document.querySelector("#role-guide-mark").textContent = config.mark;
  document.querySelector("#role-guide-label").textContent = config.guideLabel;
  document.querySelector("#role-guide-title").textContent = config.guideTitle;
  document.querySelector("#role-guide-description").textContent = config.guideDescription;
  const tips = document.querySelector("#role-guide-tips");
  tips.replaceChildren(...config.tips.map((tip) => {
    const item = document.createElement("li");
    item.textContent = tip;
    return item;
  }));
  document.querySelector("#role-guide").hidden = false;
  currentUserType = userType;
  updateSourceTextMode();
  toneControl.hidden = currentUserType === "Job Seeker";
  const isJobSeeker = currentUserType === "Job Seeker";
  document.querySelector(".settings-card .section-heading h2").textContent =
    isJobSeeker ? "Choose your explanation language" : "Choose your explanation style";
  document.querySelector("#chat-section .step-label").textContent =
    isJobSeeker ? "CAREER QUESTIONS" : "NEED MORE CLARITY?";
  document.querySelector("#chat-section .chat-heading > p").textContent = isJobSeeker
    ? "Ask about qualifications, transferable skills, interview rounds, or offer details."
    : "Ask about words, details, or what this means for you.";
  chatQuestion.placeholder = isJobSeeker
    ? roleInterfaces["Job Seeker"].chatPlaceholder
    : "For example: What does this mean for my team?";
  updateStudentTools();
  updateBusinessTools();
  updateProfessionalTools();
  updateJobSeekerTools();
  if (isJobSeeker) {
    const targetGroup = [...jobSeekerTools.querySelectorAll(".job-tool-group")]
      .find((group) => group.dataset.jobTool === selectedJobTool);
    if (targetGroup) targetGroup.open = true;
  }
}

function updateSourceTextMode() {
  const hasFile = fileInput.files.length > 0;
  const config = roleInterfaces[currentUserType] || roleInterfaces.Other;
  questionModeHelp.hidden = !hasFile;
  sourceTextLabel.textContent = hasFile
    ? "Question about the uploaded document"
    : "Technical content to simplify";
  sourceText.placeholder = hasFile
    ? "Ask a question about this document, or leave blank for a general explanation…"
    : config.placeholder;
}

function updateStudentTools() {
  if (!studentTools) return;
  studentTools.hidden = currentUserType !== "Student" || !fileInput.files.length;
  if (studentTools.hidden) {
    studentTools.querySelectorAll('input[name="student-feature"]').forEach((input) => { input.checked = false; });
  }
}

function updateBusinessTools() {
  if (!businessTools) return;
  businessTools.hidden = currentUserType !== "Business Owner" || !fileInput.files.length;
  if (businessTools.hidden) {
    businessTools.querySelectorAll('input[name="business-feature"]').forEach((input) => { input.checked = false; });
  }
}

function updateProfessionalTools() {
  if (!professionalTools) return;
  professionalTools.hidden = currentUserType !== "Working Professional" || !fileInput.files.length;
  if (professionalTools.hidden) {
    professionalTools.querySelectorAll('input[name="professional-feature"]').forEach((input) => { input.checked = false; });
  }
}

function updateJobSeekerTools() {
  if (!jobSeekerTools) return;
  jobSeekerTools.hidden = currentUserType !== "Job Seeker" || !fileInput.files.length;
  if (jobSeekerTools.hidden) {
    jobSeekerTools.querySelectorAll('input[name="job-seeker-feature"]').forEach((input) => { input.checked = false; });
    return;
  }
  if (selectedJobTool && !preselectedJobToolApplied) {
    const targetGroup = [...jobSeekerTools.querySelectorAll(".job-tool-group")]
      .find((group) => group.dataset.jobTool === selectedJobTool);
    if (targetGroup) {
      targetGroup.open = true;
      targetGroup.querySelectorAll('input[name="job-seeker-feature"]').forEach((input) => { input.checked = true; });
      preselectedJobToolApplied = true;
    }
  }
}

function speechLocale() { return SPEECH_LOCALES[languageSelect.value] || "en-US"; }

function speechRecognitionErrorMessage(error) {
  if (error === "not-allowed" || error === "permission-denied" || error === "service-not-allowed") {
    return "Microphone or speech access is blocked. Allow it in your browser's site settings, then try again.";
  }
  if (error === "audio-capture") {
    return "No microphone was found. Connect a microphone and check your Windows input settings.";
  }
  if (error === "network") {
    return "Could not reach the browser's speech service. Check your internet connection and try again.";
  }
  if (error === "no-speech") {
    return "No speech was detected. Check your microphone input and try speaking again.";
  }
  return `Voice error: ${error}. Please try again.`;
}

function speakText(text) {
  if (localStorage.getItem("tonewise_voice_muted") === "true" || !voiceRepliesToggle.checked || !("speechSynthesis" in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = speechLocale();
  window.speechSynthesis.speak(utterance);
}

// Tracks the active SpeechRecognition instance per button (keyed by button id)
const activeRecognitions = {};

function startVoiceInput(target, button, statusTarget) {
  if (!SpeechRecognition) {
    statusTarget.textContent = "⚠️ Voice input is not supported. Please use Google Chrome or Microsoft Edge.";
    statusTarget.style.color = "red";
    return;
  }

  // If already listening for this button, stop on second tap
  if (activeRecognitions[button.id]) {
    activeRecognitions[button.id].stop();
    return;
  }

  // NOTE: Do NOT call getUserMedia() before SpeechRecognition.
  // The Speech API manages microphone access on its own — calling getUserMedia
  // first causes a device-in-use conflict that prevents audio from reaching
  // the recognition engine (resulting in "no-speech" / "couldn't hear" errors).
  const recognition = new SpeechRecognition();
  recognition.lang = speechLocale();
  recognition.interimResults = true;
  recognition.continuous = true;
  recognition.maxAlternatives = 1;

  // Preserve any existing text — append instead of overwrite
  const existingText = target.value.trim();
  let finalText = existingText ? existingText + " " : "";
  let speechError = "";
  let receivedSpeech = false;
  activeRecognitions[button.id] = recognition;

  button.classList.add("listening");
  button.textContent = button.id === "source-voice-button" ? "⏹️ Tap to stop" : "⏹️";
  statusTarget.textContent = "🎤 Listening… speak now. Tap again to stop.";
  statusTarget.style.color = "";

  recognition.onresult = (event) => {
    let interimText = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      if (event.results[index].isFinal) {
        finalText += event.results[index][0].transcript + " ";
        receivedSpeech = true;
      } else {
        interimText += event.results[index][0].transcript;
      }
    }
    target.value = (finalText + interimText).trim();
    if (target === sourceText) updateCharacterCount();
  };

  recognition.onerror = (event) => {
    speechError = speechRecognitionErrorMessage(event.error);
    delete activeRecognitions[button.id];
    button.classList.remove("listening");
    button.textContent = button.id === "source-voice-button" ? "🎙️ Dictate content" : "🎙️";
    statusTarget.textContent = speechError;
    statusTarget.style.color = "red";
  };

  recognition.onend = () => {
    delete activeRecognitions[button.id];
    button.classList.remove("listening");
    button.textContent = button.id === "source-voice-button" ? "🎙️ Dictate content" : "🎙️";
    if (speechError) return;
    if (!receivedSpeech) {
      target.value = existingText;
      if (target === sourceText) updateCharacterCount();
      statusTarget.textContent = "No speech was detected. Check your microphone input and try again.";
      statusTarget.style.color = "red";
    } else {
      statusTarget.textContent = "✅ Voice input captured. You can speak again to add more.";
      statusTarget.style.color = "green";
    }
  };

  try {
    recognition.start();
  } catch (err) {
    delete activeRecognitions[button.id];
    button.classList.remove("listening");
    button.textContent = button.id === "source-voice-button" ? "🎙️ Dictate content" : "🎙️";
    statusTarget.textContent = `Could not start voice input: ${err.message || "please try again."}`;
    statusTarget.style.color = "red";
    console.error("SpeechRecognition start error:", err);
  }
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
      if (account.preferences.user_type) applyRoleInterface(account.preferences.user_type);
    }
  } catch { /* The existing app remains usable if auth is temporarily offline. */ }
}

async function loadAiProviderStatus() {
  const status = document.querySelector("#ai-provider-status");
  if (!status) return;
  status.textContent = "Checking local AI…";
  try {
    const response = await fetch("/api/ai/status");
    if (!response.ok) throw new Error("Could not check the local AI service.");
    const data = await response.json();
    const ollama = data.ollama;
    if (!ollama.available) {
      status.dataset.state = "ready";
      status.textContent = "Cloud AI providers are tried first; Ollama is unavailable as a local fallback.";
    } else if (!ollama.model_installed) {
      status.dataset.state = "warning";
      status.textContent = `Cloud AI providers are tried first. Ollama fallback model ${ollama.model} is not downloaded; run: ollama pull ${ollama.model}`;
    } else {
      status.dataset.state = "ready";
      status.textContent = `Cloud AI providers are tried first; Ollama ${ollama.model} is ready as a local fallback.`;
    }
  } catch {
    status.dataset.state = "warning";
    status.textContent = "Could not check Ollama status. Simplification will still try the configured providers.";
  }
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

function getApiError(data, fallback) {
  if (data.detail) return data.detail;
  if (Array.isArray(data.errors) && data.errors.length) return data.errors.join(" | ");
  return fallback;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function clearSelectedFile() {
  fileInput.value = "";
  fileName.textContent = "No file selected";
  removeFileButton.hidden = true;
  updateSourceTextMode();
  updateStudentTools();
  updateBusinessTools();
  updateProfessionalTools();
  updateJobSeekerTools();
}

function normalizeResponseText(text) {
  return String(text ?? "")
    .replace(/<br\s*\/?>/gi, "\n\n")
    .replace(/[\u2B50\u2605\u2606\u2726-\u2734\u2B51\u2B52\u{1F31F}\u{1F320}\u{1F7C4}]\uFE0F?/gu, "")
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanInlineFormatting(text) {
  return text
    .replace(/\*{1,3}([^\n*]+?)\*{1,3}/g, "$1")
    .replace(/`([^`\n]+)`/g, "$1")
    .trim();
}

function parseMarkdownTableRow(line) {
  const trimmed = line.trim();
  if (!trimmed.includes("|")) return null;
  return trimmed
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cleanInlineFormatting(cell.trim()));
}

function isMarkdownTableStart(lines, index) {
  const headers = parseMarkdownTableRow(lines[index]);
  const separators = lines[index + 1] ? parseMarkdownTableRow(lines[index + 1]) : null;
  return Boolean(
    headers?.length > 1
      && separators?.length === headers.length
      && separators.every((cell) => /^:?-{3,}:?$/.test(cell)),
  );
}

function isFormattedBlockStart(lines, index) {
  return /^#{1,6}\s+/.test(lines[index])
    || /^\s*(?:[-+*•]|\d+[.)])\s+\S/.test(lines[index])
    || /^\s*```(?:mermaid|flowchart)\s*$/i.test(lines[index])
    || isMarkdownTableStart(lines, index);
}

function appendMarkdownTable(container, lines, startIndex) {
  const headers = parseMarkdownTableRow(lines[startIndex]);
  const wrapper = document.createElement("div");
  wrapper.className = "response-table-wrap";
  const table = document.createElement("table");
  table.className = "response-table";
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headers.forEach((value) => {
    const cell = document.createElement("th");
    cell.textContent = value;
    headerRow.append(cell);
  });
  thead.append(headerRow);
  table.append(thead);

  const tbody = document.createElement("tbody");
  let index = startIndex + 2;
  while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
    const values = parseMarkdownTableRow(lines[index]);
    if (!values) break;
    const row = document.createElement("tr");
    headers.forEach((_, cellIndex) => {
      const cell = document.createElement("td");
      cell.textContent = values[cellIndex] || "";
      row.append(cell);
    });
    tbody.append(row);
    index += 1;
  }
  table.append(tbody);
  wrapper.append(table);
  container.append(wrapper);
  return index;
}

let flowchartSequence = 0;

function createSvgElement(name, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function wrapDiagramLabel(label, maxCharacters = 22) {
  const lines = [];
  let current = "";
  label.trim().split(/\s+/).forEach((word) => {
    if (current && `${current} ${word}`.length > maxCharacters) {
      lines.push(current);
      current = word;
    } else {
      current = current ? `${current} ${word}` : word;
    }
  });
  if (current) lines.push(current);
  if (lines.length > 3) {
    lines.length = 3;
    lines[2] = `${lines[2].slice(0, maxCharacters - 1)}…`;
  }
  return lines;
}

function appendFlowchartDiagram(container, source) {
  const lines = source.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const header = lines[0]?.match(/^flowchart\s+(TD|LR)$/i);
  if (!header) return false;

  const nodes = new Map();
  const edges = [];
  const edgePattern = /^([A-Za-z][\w-]*)\s*\[([^\]]{1,80})\]\s*-->\s*([A-Za-z][\w-]*)\s*\[([^\]]{1,80})\]$/;
  for (const line of lines.slice(1)) {
    const edge = line.match(edgePattern);
    if (!edge || edge[1] === edge[3]) return false;
    nodes.set(edge[1], edge[2].trim());
    nodes.set(edge[3], edge[4].trim());
    edges.push([edge[1], edge[3]]);
  }
  if (nodes.size < 2 || nodes.size > 10 || edges.length > 14) return false;

  const indegree = new Map([...nodes.keys()].map((id) => [id, 0]));
  const outgoing = new Map([...nodes.keys()].map((id) => [id, []]));
  edges.forEach(([from, to]) => {
    indegree.set(to, indegree.get(to) + 1);
    outgoing.get(from).push(to);
  });

  const rank = new Map([...nodes.keys()].map((id) => [id, 0]));
  const queue = [...nodes.keys()].filter((id) => indegree.get(id) === 0);
  let visited = 0;
  while (queue.length) {
    const from = queue.shift();
    visited += 1;
    outgoing.get(from).forEach((to) => {
      rank.set(to, Math.max(rank.get(to), rank.get(from) + 1));
      indegree.set(to, indegree.get(to) - 1);
      if (indegree.get(to) === 0) queue.push(to);
    });
  }
  if (visited !== nodes.size) return false;

  const direction = header[1].toUpperCase();
  const maxRank = Math.max(...rank.values());
  const layers = Array.from({ length: maxRank + 1 }, () => []);
  nodes.forEach((label, id) => layers[rank.get(id)].push(id));
  const boxWidth = 210;
  const boxHeight = 78;
  const gap = 58;
  const padding = 24;
  const largestLayer = Math.max(...layers.map((layer) => layer.length));
  const width = direction === "TD"
    ? Math.max(boxWidth + padding * 2, largestLayer * boxWidth + (largestLayer - 1) * gap + padding * 2)
    : (maxRank + 1) * boxWidth + maxRank * gap + padding * 2;
  const height = direction === "TD"
    ? (maxRank + 1) * boxHeight + maxRank * gap + padding * 2
    : largestLayer * boxHeight + (largestLayer - 1) * gap + padding * 2;
  const positions = new Map();

  layers.forEach((layer, layerIndex) => {
    layer.forEach((id, itemIndex) => {
      const layerSize = direction === "TD" ? layer.length : largestLayer;
      const span = layerSize * boxWidth + (layerSize - 1) * gap;
      const crossPosition = (direction === "TD" ? width : height) / 2
        - span / 2 + itemIndex * (boxWidth + gap);
      positions.set(id, direction === "TD"
        ? { x: crossPosition, y: padding + layerIndex * (boxHeight + gap) }
        : { x: padding + layerIndex * (boxWidth + gap), y: crossPosition });
    });
  });

  const figure = document.createElement("figure");
  figure.className = "diagram-wrap";
  const svg = createSvgElement("svg", {
    class: "flowchart-svg",
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": "Diagram explanation",
    preserveAspectRatio: "xMidYMin meet",
  });
  const markerId = `flowchart-arrow-${++flowchartSequence}`;
  const defs = createSvgElement("defs");
  const marker = createSvgElement("marker", {
    id: markerId,
    markerWidth: "8",
    markerHeight: "8",
    refX: "7",
    refY: "4",
    orient: "auto",
  });
  marker.append(createSvgElement("path", { d: "M0,0 L8,4 L0,8 Z", class: "flowchart-arrow" }));
  defs.append(marker);
  svg.append(defs);

  edges.forEach(([from, to]) => {
    const start = positions.get(from);
    const end = positions.get(to);
    const isTopDown = direction === "TD";
    svg.append(createSvgElement("line", {
      x1: start.x + (isTopDown ? boxWidth / 2 : boxWidth),
      y1: start.y + (isTopDown ? boxHeight : boxHeight / 2),
      x2: end.x + (isTopDown ? boxWidth / 2 : 0),
      y2: end.y + (isTopDown ? 0 : boxHeight / 2),
      class: "flowchart-edge",
      "marker-end": `url(#${markerId})`,
    }));
  });

  nodes.forEach((label, id) => {
    const position = positions.get(id);
    svg.append(createSvgElement("rect", {
      x: position.x,
      y: position.y,
      width: boxWidth,
      height: boxHeight,
      rx: "10",
      class: "flowchart-node",
    }));
    const text = createSvgElement("text", {
      x: position.x + boxWidth / 2,
      y: position.y + boxHeight / 2,
      "text-anchor": "middle",
      class: "flowchart-label",
    });
    const labelLines = wrapDiagramLabel(label);
    const lineHeight = 17;
    labelLines.forEach((labelLine, lineIndex) => {
      const tspan = createSvgElement("tspan", {
        x: position.x + boxWidth / 2,
        dy: lineIndex === 0
          ? `${-((labelLines.length - 1) * lineHeight) / 2}px`
          : `${lineHeight}px`,
      });
      tspan.textContent = labelLine;
      text.append(tspan);
    });
    svg.append(text);
  });

  const caption = document.createElement("figcaption");
  caption.textContent = "Concept map";
  figure.append(svg, caption);
  container.append(figure);
  return true;
}

function renderFormattedText(container, value) {
  const lines = normalizeResponseText(value).split("\n");
  container.replaceChildren();
  let currentList = null;
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      currentList = null;
      index += 1;
      continue;
    }

    if (/^\s*```(?:mermaid|flowchart)\s*$/i.test(line)) {
      currentList = null;
      let end = index + 1;
      while (end < lines.length && !/^\s*```\s*$/.test(lines[end])) end += 1;
      const source = lines.slice(index + 1, end).join("\n");
      if (!appendFlowchartDiagram(container, source)) {
        const code = document.createElement("pre");
        code.className = "diagram-source";
        code.textContent = source;
        container.append(code);
      }
      index = end < lines.length ? end + 1 : end;
      continue;
    }

    if (isMarkdownTableStart(lines, index)) {
      currentList = null;
      index = appendMarkdownTable(container, lines, index);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      currentList = null;
      const level = Math.min(heading[1].length + 1, 4);
      const element = document.createElement(`h${level}`);
      element.textContent = cleanInlineFormatting(heading[2]);
      container.append(element);
      index += 1;
      continue;
    }

    const listItem = line.match(/^\s*(?:([-+*•])|(\d+)[.)])\s+(.+)$/);
    if (listItem) {
      const listType = listItem[2] ? "ol" : "ul";
      if (!currentList || currentList.tagName.toLowerCase() !== listType) {
        currentList = document.createElement(listType);
        container.append(currentList);
      }
      const item = document.createElement("li");
      item.textContent = cleanInlineFormatting(listItem[3]);
      currentList.append(item);
      index += 1;
      continue;
    }

    currentList = null;
    const paragraphLines = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !isFormattedBlockStart(lines, index)) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    const paragraph = document.createElement("p");
    paragraph.textContent = cleanInlineFormatting(paragraphLines.join(" "));
    container.append(paragraph);
  }
}

function showMessage(text, type) {
  const message = document.createElement("div");
  message.className = `message ${type}`;
  if (type === "assistant") {
    renderFormattedText(message, text);
  } else {
    message.textContent = text;
  }
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
  renderFormattedText(simplifiedResult, data.response);
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

sourceVoiceButton.dataset.idleLabel = "🎙️ Dictate content";
sourceVoiceButton.dataset.idleAria = "Dictate content";
chatVoiceButton.dataset.idleLabel = "🎙️";
chatVoiceButton.dataset.idleAria = "Ask a question by voice";
window.setupVoiceInput({
  button: sourceVoiceButton,
  status: voiceInputStatus,
  language: () => languageSelect.value,
  onTranscription: (text) => {
    sourceText.value = `${sourceText.value.trim()} ${text}`.trim();
    sourceText.dispatchEvent(new Event("input", { bubbles: true }));
    voiceInputStatus.textContent = "Voice text added. Choose a style, then simplify it.";
  },
});
window.setupVoiceInput({
  button: chatVoiceButton,
  status: voiceInputStatus,
  language: () => languageSelect.value,
  onTranscription: (text) => {
    chatQuestion.value = `${chatQuestion.value.trim()} ${text}`.trim();
    chatQuestion.focus();
    voiceInputStatus.textContent = "Voice question added. Review it, then send.";
  },
});
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
  if (file.size > MAX_FILE_SIZE_BYTES) {
    clearSelectedFile();
    setStatus(`Please choose a file smaller than ${MAX_FILE_SIZE_LABEL}.`, true);
    return;
  }
  fileName.textContent = `${file.name} (${formatFileSize(file.size)})`;
  removeFileButton.hidden = false;
  updateSourceTextMode();
  updateStudentTools();
  updateBusinessTools();
  updateProfessionalTools();
  updateJobSeekerTools();
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
  simplifyButton.textContent = "Generating...";
  setStatus("ToneWise AI is preparing your clear explanation...");
  const formData = new FormData();
  formData.append("text", file ? "" : text);
  formData.append("question", file ? text : "");
  if (currentUserType !== "Job Seeker") formData.append("tone", toneSelect.value);
  formData.append("language", languageSelect.value);
  if (file) {
    formData.append("file", file);
    if (currentUserType === "Student") {
      document.querySelectorAll('input[name="student-feature"]:checked').forEach((input) => {
        formData.append("student_features", input.value);
      });
    }
    if (currentUserType === "Business Owner") {
      document.querySelectorAll('input[name="business-feature"]:checked').forEach((input) => {
        formData.append("business_features", input.value);
      });
    }
    if (currentUserType === "Working Professional") {
      document.querySelectorAll('input[name="professional-feature"]:checked').forEach((input) => {
        formData.append("professional_features", input.value);
      });
    }
    if (currentUserType === "Job Seeker") {
      document.querySelectorAll('input[name="job-seeker-feature"]:checked').forEach((input) => {
        formData.append("job_seeker_features", input.value);
      });
    }
  }

  try {
    const response = await fetch("/api/simplify", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(getApiError(data, "Unable to simplify this content."));
    history.replaceState({}, "", `?conversation=${encodeURIComponent(data.session_id)}`);
    displayConversation(data, true);
    setStatus("Your explanation is ready.");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setStatus(error.message || "The server is not ready yet.", true);
  } finally {
    simplifyButton.disabled = false;
    simplifyButton.textContent = "Generate Explanation";
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
  const submitButton = chatForm.querySelector(".send-button");
  submitButton.disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: conversationId, question }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(getApiError(data, "I could not answer that question. Please try again."));
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
  await Promise.all([loadAccountPreferences(), loadAiProviderStatus()]);
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

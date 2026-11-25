const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value || "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
let conversations = [];
let accountUser = null;
const DashboardSpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

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

async function api(url, options) {
  const response = await fetch(url, options);
  if (response.status === 401) return location.assign("/signin");
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Something went wrong.");
  return data;
}

function showHistory(items) {
  $("#history-list").innerHTML = items.length ? items.map((item) => `<a class="history-row" href="/workspace?conversation=${encodeURIComponent(item.session_id)}"><h3>${esc(item.original_text)}</h3><p>${new Date(item.created_at + "Z").toLocaleDateString()} &middot; ${esc(item.tone)}</p></a>`).join("") : '<p class="empty">No simplifications yet.</p>';
}

function showTeams(teams) {
  $("#teams-list").innerHTML = teams.length ? teams.map((team) => `<article class="team"><strong>${esc(team.name)}</strong><p class="members"><span class="role-badge">${esc(team.member_role)}</span> &middot; ${team.members.length} members</p><a class="button-link" href="/team-feed?team=${team.id}">Open workspace &rarr;</a></article>`).join("") : '<p class="empty">Create a team to begin collaborating.</p>';
  const switcher = $("#team-switcher");
  switcher.innerHTML = teams.length ? teams.map((team) => `<option value="${team.id}">${esc(team.name)}</option>`).join("") : '<option value="">No teams yet</option>';
  switcher.onchange = () => switcher.value && location.assign(`/team-feed?team=${switcher.value}`);
}

function setProfileUser(user) {
  accountUser = user;
  const initials = user.full_name.trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "U";
  $("#profile-button").textContent = initials;
  $("#profile-name").value = user.full_name;
  $("#profile-email").value = user.email;
}

async function load() {
  const data = await api("/api/dashboard/summary");
  conversations = data.conversations;
  setProfileUser(data.user);
  const isBusinessOwner = data.user.user_type === "Business Owner";
  const isJobSeeker = data.user.user_type === "Job Seeker";
  $("#email-assistant-nav").hidden = !isBusinessOwner;
  $("#email-assistant-link").hidden = !isBusinessOwner;
  $("#job-seeker-tools").hidden = !isJobSeeker;
  if (isJobSeeker) {
    $("#hero-title").innerHTML = "Make your next career move<br>with <span>confidence.</span>";
    document.querySelector(".hero-copy > p:not(.hero-kicker)").textContent =
      "Decode job descriptions, prepare for interviews, and understand every step of the hiring process.";
    const careerStartLink = document.querySelector(".hero-actions .start-button");
    careerStartLink.href = "/career-tools/job-description";
    careerStartLink.textContent = "Start career preparation →";
    document.querySelector(".hero-note").lastChild.textContent = " Your next opportunity starts with clarity";
  }
  $("#welcome").textContent = `Welcome back, ${data.user.full_name.split(" ")[0]}`;
  $("#stat-total").textContent = data.stats.total;
  $("#stat-tone").textContent = data.stats.tone;
  $("#stat-teams").textContent = data.teams.length;
  $("#stat-provider").textContent = data.stats.provider;
  showHistory(conversations);
  showTeams(data.teams);
}

$("#history-search").oninput = (event) => showHistory(conversations.filter((item) => `${item.original_text} ${item.tone}`.toLowerCase().includes(event.target.value.toLowerCase())));
$("#team-form").onsubmit = async (event) => {
  event.preventDefault();
  try {
    const data = await api("/api/dashboard/teams", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: event.target.name.value, description: "" }) });
    location.assign(`/team-settings?team=${data.team.id}`);
  } catch (error) { alert(error.message); }
};

$("#profile-button").onclick = () => { $("#profile-menu").hidden = !$("#profile-menu").hidden; $("#notification-menu").hidden = true; };
$("#open-profile").onclick = () => { $("#profile-menu").hidden = true; $("#profile-error").hidden = true; $("#profile-dialog").showModal(); };
$("#close-profile").onclick = () => $("#profile-dialog").close();
$("#profile-form").onsubmit = async (event) => {
  event.preventDefault();
  const error = $("#profile-error");
  error.hidden = true;
  try {
    const data = await api("/api/auth/profile", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: $("#profile-name").value }) });
    setProfileUser(data.user);
    $("#welcome").textContent = `Welcome back, ${data.user.full_name.split(" ")[0]}`;
    $("#profile-dialog").close();
  } catch (exception) { error.textContent = exception.message; error.hidden = false; }
};
$("#logout").onclick = async () => { await fetch("/api/auth/logout", { method: "POST" }); location.assign("/signin"); };

function setupVoiceAssistant() {
  const button = $("#voice-button"), status = $("#voice-status");
  const muteButton = document.createElement("button");
  muteButton.type = "button";
  muteButton.className = "voice-mute-button";
  button.insertAdjacentElement("afterend", muteButton);
  const updateMuteButton = () => {
    const muted = localStorage.getItem("tonewise_voice_muted") === "true";
    muteButton.textContent = muted ? "Unmute voice" : "Mute voice";
    muteButton.setAttribute("aria-pressed", String(muted));
  };
  muteButton.onclick = () => {
    const muted = localStorage.getItem("tonewise_voice_muted") === "true";
    localStorage.setItem("tonewise_voice_muted", String(!muted));
    if (!muted && "speechSynthesis" in window) window.speechSynthesis.cancel();
    updateMuteButton();
    status.textContent = muted ? "Voice replies are on." : "Voice replies are muted.";
  };
  updateMuteButton();

  window.setupVoiceInput({
    button,
    status,
    language: () => "English",
    onTranscription: (text) => {
      status.textContent = "✅ Got it! Opening workspace…";
      location.assign(`/workspace?voiceText=${encodeURIComponent(text)}`);
    },
  });
}

async function notifications() {
  const data = await api("/api/dashboard/notifications");
  const button = $("#notification-button"), menu = $("#notification-menu");
  const count = button.querySelector(".notification-count");
  count.textContent = data.unread || "";
  count.hidden = !data.unread;
  button.setAttribute("aria-label", data.unread ? `Notifications (${data.unread} unread)` : "Notifications");
  menu.innerHTML = data.notifications.length ? data.notifications.map((notice) => `<a class="history-row" href="${esc(notice.link || "/dashboard")}"><strong>${esc(notice.message)}</strong><p>${new Date(notice.created_at + "Z").toLocaleString()}</p></a>`).join("") : '<p class="empty">No notifications yet.</p>';
  button.onclick = async () => { menu.hidden = !menu.hidden; $("#profile-menu").hidden = true; if (!menu.hidden) await api("/api/dashboard/notifications/read", { method: "POST" }); };
}

document.addEventListener("click", (event) => {
  if (!event.target.closest(".profile-wrap")) { $("#profile-menu").hidden = true; $("#notification-menu").hidden = true; }
});

setupVoiceAssistant();
load().then(notifications).catch((error) => alert(error.message));

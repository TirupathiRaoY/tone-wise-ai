const params = new URLSearchParams(location.search);
let teamId = Number(params.get("team")) || null;
const $ = (selector) => document.querySelector(selector);
const esc = (value) =>
  String(value || "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);

async function api(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Something went wrong.");
  return data;
}

async function loadTeams() {
  const data = await api("/api/dashboard/teams");
  if (!teamId && data.teams[0]) teamId = data.teams[0].id;

  const switcher = $("#team-switcher");
  switcher.innerHTML = data.teams.length
    ? data.teams
        .map(
          (team) =>
            `<option value="${team.id}" ${
              team.id === teamId ? "selected" : ""
            }>${esc(team.name)}</option>`
        )
        .join("")
    : "<option>No teams yet</option>";
  switcher.onchange = () => location.assign(`/team-feed?team=${switcher.value}`);

  if (!teamId) {
    $("#feed").innerHTML =
      '<p class="empty">Create a team from the dashboard to begin collaborating.</p>';
    return false;
  }
  return true;
}

function card(item) {
  const messageLabel = `${item.message_count} ${
    item.message_count === 1 ? "message" : "messages"
  }`;
  return `<article class="feed-card">
    <header>
      <div>
        <h2>${esc(item.author_name)}</h2>
        <p class="meta">${new Date(item.created_at + "Z").toLocaleString()} · ${esc(item.language)}</p>
      </div>
      <div class="badges">
        <span class="badge">${esc(item.tone)}</span>
        <span class="badge">${esc(item.user_role)}</span>
      </div>
    </header>
    <p class="explanation">${esc(item.simplified_explanation).slice(0, 560)}${
      item.simplified_explanation.length > 560 ? "…" : ""
    }</p>
    <button class="button secondary" data-item="${esc(item.session_id)}">
      Continue shared chat · ${messageLabel} · ${item.comment_count} comments
    </button>
  </article>`;
}

async function loadFeed() {
  if (!(await loadTeams())) return;

  const teamData = await api(`/api/dashboard/teams/${teamId}`);
  $("#team-name").textContent = teamData.team.name;
  $("#team-description").textContent =
    teamData.team.description ||
    "A shared place for clear explanations and team discussion.";
  $("#settings-link").href = `/team-settings?team=${teamId}`;

  const feedData = await api(`/api/dashboard/teams/${teamId}/feed`);
  $("#feed").innerHTML = feedData.items.length
    ? feedData.items.map(card).join("")
    : '<p class="empty">No shared simplifications yet. Share one from the simplification workspace.</p>';

  document
    .querySelectorAll("[data-item]")
    .forEach((button) => (button.onclick = () => openItem(button.dataset.item)));

  const requestedItem = params.get("item");
  if (requestedItem) await openItem(requestedItem);
}

function message(item) {
  const sender = item.sender_role === "user" ? "Team member" : "ToneWise AI";
  return `<div class="message ${
    item.sender_role === "user" ? "user" : "assistant"
  }"><strong>${sender}</strong><br>${esc(item.content)}</div>`;
}

async function openItem(id) {
  const data = await api(`/api/dashboard/teams/${teamId}/items/${id}`);
  const item = data.item;
  $("#item-detail").innerHTML = `<header>
    <h2>${esc(item.author_name)}'s simplification</h2>
    <p class="meta">${new Date(item.created_at + "Z").toLocaleString()} · ${esc(item.tone)} · ${esc(item.user_role)}</p>
  </header>
  <p class="explanation">${esc(item.simplified_explanation)}</p>
  <h3>Continue this shared chat</h3>
  <p class="meta">Your follow-ups and AI replies are saved for everyone on this team.</p>
  <div id="thread" class="thread" aria-live="polite">${
    item.messages.map(message).join("") ||
    '<p class="empty">Ask the first follow-up question for your team.</p>'
  }</div>
  <p id="chat-status" class="notice chat-status" role="status"></p>
  <form id="chat-form" class="comment-form">
    <input id="question" required maxlength="4000" placeholder="Ask a follow-up for the team">
    <button class="button">Send to shared chat</button>
  </form>
  <h3>Comments</h3>
  <div id="comments" class="comments">${
    item.comments
      .map(
        (comment) =>
          `<article class="comment"><strong>${esc(comment.author_name)}</strong><span class="meta"> · ${new Date(comment.created_at + "Z").toLocaleString()}</span><p>${esc(comment.content)}</p></article>`
      )
      .join("") || '<p class="empty">No comments yet.</p>'
  }</div>
  <form id="comment-form" class="comment-form">
    <input id="comment-text" required maxlength="2000" placeholder="Add a comment for your team">
    <button class="button secondary">Comment</button>
  </form>`;

  $("#item-dialog").showModal();
  $("#chat-form").onsubmit = async (event) => {
    event.preventDefault();
    const questionInput = $("#question");
    const question = questionInput.value.trim();
    const button = $("#chat-form button");
    const status = $("#chat-status");
    if (!question || button.disabled) return;

    button.disabled = true;
    questionInput.disabled = true;
    status.classList.remove("error");
    status.textContent = "Waiting for the AI to reply…";
    try {
      const result = await api(
        `/api/dashboard/teams/${teamId}/items/${encodeURIComponent(id)}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        }
      );
      $("#thread").insertAdjacentHTML(
        "beforeend",
        message({ sender_role: "user", content: question }) +
          message({ sender_role: "assistant", content: result.response })
      );
      questionInput.value = "";
      status.textContent = "Reply saved to the shared chat.";
      $("#thread").scrollTop = $("#thread").scrollHeight;
    } catch (error) {
      status.classList.add("error");
      status.textContent = error.message || "The reply could not be added.";
    } finally {
      button.disabled = false;
      questionInput.disabled = false;
      questionInput.focus();
    }
  };

  $("#comment-form").onsubmit = async (event) => {
    event.preventDefault();
    const input = $("#comment-text");
    const content = input.value.trim();
    if (!content) return;

    try {
      const result = await api(
        `/api/dashboard/teams/${teamId}/items/${encodeURIComponent(id)}/comments`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
        }
      );
      $("#comments").insertAdjacentHTML(
        "beforeend",
        `<article class="comment"><strong>${esc(result.comment.author_name)}</strong><span class="meta"> · just now</span><p>${esc(result.comment.content)}</p></article>`
      );
      input.value = "";
    } catch (error) {
      $("#feed-message").textContent =
        error.message || "The comment could not be added.";
    }
  };
}

$("#close-item").onclick = () => $("#item-dialog").close();
loadFeed().catch((error) => {
  $("#feed-message").textContent = error.message;
});

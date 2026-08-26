// SMS Security Lab — frontend logic.
// Talks only to the local Flask API on the same origin. No external
// requests are ever made from this file.

const recipientInput = document.getElementById("recipient");
const messageInput = document.getElementById("message");
const charCount = document.getElementById("char-count");
const sendBtn = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");
const statusLine = document.getElementById("status-line");
const errorLine = document.getElementById("error-line");

const statAttempts = document.getElementById("stat-attempts");
const statDelivered = document.getElementById("stat-delivered");
const statFailed = document.getElementById("stat-failed");
const statMessages = document.getElementById("stat-messages");

const inboxList = document.getElementById("inbox-list");
const eventTbody = document.getElementById("event-tbody");

messageInput.addEventListener("input", () => {
  charCount.textContent = messageInput.value.length;
});

function setStatus(text, cls) {
  statusLine.textContent = text;
  statusLine.className = "status-line" + (cls ? " " + cls : "");
}

function setError(text) {
  errorLine.textContent = text || "";
}

function renderStats(stats) {
  statAttempts.textContent = stats.attempts;
  statDelivered.textContent = stats.delivered;
  statFailed.textContent = stats.failed;
  statMessages.textContent = stats.messages;
}

function renderInbox(inbox) {
  if (!inbox.length) {
    inboxList.innerHTML = '<p class="empty-state">No messages yet. Send a SMS to populate the inbox.</p>';
    return;
  }
  inboxList.innerHTML = inbox.map((item) => `
    <div class="inbox-item">
      <div class="inbox-item-top">
        <span>${item.sender}</span>
        <span>${item.timestamp}</span>
      </div>
      <div class="inbox-item-body">${escapeHtml(item.message)}</div>
      <div class="inbox-item-bottom">
        <span>To: ${item.recipient_masked}</span>
        <span class="status-pill ${item.status}">${item.status}</span>
        <span class="mock-label">${item.label}</span>
      </div>
    </div>
  `).join("");
}

function renderEvents(events) {
  if (!events.length) {
    eventTbody.innerHTML = '<tr><td colspan="6" class="empty-state">No events yet.</td></tr>';
    return;
  }
  eventTbody.innerHTML = events.map((ev) => `
    <tr>
      <td>${ev.timestamp}</td>
      <td>${ev.mode}</td>
      <td>${ev.recipient_masked}</td>
      <td>${ev.status}</td>
      <td>${ev.message_id}</td>
      <td>${ev.provider}</td>
    </tr>
  `).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function refreshState() {
  const res = await fetch("/api/state");
  const data = await res.json();
  renderStats(data.stats);
  renderInbox(data.inbox);
  renderEvents(data.events);
}

async function sendSms() {
  setError("");
  const number = recipientInput.value.trim();
  const message = messageInput.value;

  sendBtn.disabled = true;
  setStatus("Processing delivery...", "processing");

  try {
    const res = await fetch("/api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ number, message }),
    });
    const data = await res.json();

    if (!res.ok || !data.ok) {
      setStatus("", "");
      setError(data.error || "Something went wrong.");
      return;
    }

    renderStats(data.stats);
    renderInbox(data.inbox);
    await refreshState(); // also picks up the new event row

    if (data.event.status === "DELIVERED") {
      setStatus("SMS delivered to Inbox.", "success");
    } else {
      setStatus("Delivery failed.", "failure");
    }
  } catch (err) {
    setStatus("", "");
    setError("Could not reach the local server.");
  } finally {
    sendBtn.disabled = false;
  }
}

async function clearData() {
  if (!confirm("Clear all messages and event logs?")) return;
  await fetch("/api/clear", { method: "POST" });
  setStatus("", "");
  setError("");
  await refreshState();
}

sendBtn.addEventListener("click", sendSms);
clearBtn.addEventListener("click", clearData);

refreshState();

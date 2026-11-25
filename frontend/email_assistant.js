const form = document.querySelector("#email-form");
const generateButton = document.querySelector("#generate-letter");
const errorMessage = document.querySelector("#email-error");
const resultSection = document.querySelector("#letter-result");
const letterContent = document.querySelector("#letter-content");
const providerNote = document.querySelector("#letter-provider");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorMessage.hidden = true;
  generateButton.disabled = true;
  generateButton.textContent = "Creating your letter…";

  const payload = Object.fromEntries(new FormData(form));
  try {
    const response = await fetch("/api/business/email-assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (response.status === 401) {
      location.assign("/signin");
      return;
    }
    if (!response.ok || !data.success) {
      throw new Error(data.detail || data.errors?.join(" | ") || "Could not create the letter.");
    }
    letterContent.textContent = data.letter;
    providerNote.textContent = data.provider_used ? `Drafted with ${data.provider_used}.` : "";
    resultSection.hidden = false;
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    errorMessage.textContent = error.message || "Could not create the letter.";
    errorMessage.hidden = false;
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = "✦ Create formal letter";
  }
});

document.querySelector("#copy-letter").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText(letterContent.textContent);
    button.textContent = "Copied";
    setTimeout(() => { button.textContent = "Copy letter"; }, 1800);
  } catch {
    errorMessage.textContent = "Could not access the clipboard. Select and copy the letter text instead.";
    errorMessage.hidden = false;
  }
});

document.querySelector("#download-letter").addEventListener("click", () => {
  const blob = new Blob([letterContent.textContent], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "tonewise-business-letter.txt";
  link.click();
  URL.revokeObjectURL(url);
});

/* Records voice in the browser and transcribes it on the local ToneWise server. */

window.setupVoiceInput = function ({ button, status, language, onTranscription }) {
  let recorder = null;
  let stream = null;
  let chunks = [];
  let starting = false;

  function setIdle() {
    button.classList.remove("listening");
    button.textContent = button.dataset.idleLabel || "🎙️";
    button.setAttribute("aria-label", button.dataset.idleAria || "Start voice input");
  }

  async function transcribe(blob) {
    if (!blob.size) {
      status.textContent = "No audio was recorded. Check your microphone and try again.";
      return;
    }
    if (blob.size > 20 * 1024 * 1024) {
      status.textContent = "The recording is too large. Please record a shorter clip.";
      return;
    }

    status.textContent = "Transcribing on this computer…";
    button.disabled = true;
    const formData = new FormData();
    const mimeType = blob.type.toLowerCase();
    const extension = mimeType.includes("mp4") ? "mp4" : mimeType.includes("ogg") ? "ogg" : "webm";
    formData.append("audio", blob, `voice.${extension}`);
    formData.append("language", language());

    try {
      const response = await fetch("/api/transcribe", { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.detail || "Voice transcription failed.");
      }
      if (!data.text) {
        status.textContent = "No speech was detected. Try speaking closer to the microphone.";
        return;
      }
      onTranscription(data.text);
    } catch (error) {
      status.textContent = error.message || "Voice transcription failed. Please try again.";
    } finally {
      button.disabled = false;
    }
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      status.textContent = "Audio recording is not supported in this browser. Try a current version of Chrome or Edge.";
      return;
    }
    if (starting) return;

    starting = true;
    status.textContent = "Requesting microphone access…";
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
        .find((type) => MediaRecorder.isTypeSupported(type));
      recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunks = [];
      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size) chunks.push(event.data);
      });
      recorder.addEventListener("stop", () => {
        const recording = new Blob(chunks, { type: recorder.mimeType });
        stream.getTracks().forEach((track) => track.stop());
        recorder = null;
        stream = null;
        setIdle();
        void transcribe(recording);
      }, { once: true });
      recorder.addEventListener("error", (event) => {
        status.textContent = event.error?.message || "Could not record audio. Check your microphone and try again.";
        stream?.getTracks().forEach((track) => track.stop());
        stream = null;
        recorder = null;
        setIdle();
      }, { once: true });
      recorder.start();
      button.textContent = "⏹️ Tap to stop";
      button.setAttribute("aria-label", "Stop recording");
      button.classList.add("listening");
      status.textContent = "🎤 Listening… speak now, then tap to stop.";
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop());
      stream = null;
      recorder = null;
      setIdle();
      status.textContent = error.name === "NotAllowedError"
        ? "Microphone access is blocked. Allow it in your browser's site settings, then try again."
        : error.name === "NotFoundError"
          ? "No microphone was found. Connect a microphone and check your Windows input settings."
          : `Could not start recording: ${error.message || "check your microphone and try again."}`;
    } finally {
      starting = false;
    }
  }

  button.addEventListener("click", () => {
    if (recorder?.state === "recording") {
      status.textContent = "Finishing recording…";
      recorder.stop();
    } else {
      void startRecording();
    }
  });
};

const tools = {
  "job-description": {
    title: "Job Description Analyzer",
    description: "Upload or paste a role description to understand its responsibilities, requirements, skills, and important details.",
    result: "Job description analysis",
  },
  "interview-preparation": {
    title: "Interview Preparation",
    description: "Turn a skill you want to build into a focused lesson, practical examples, and interview practice tailored to your goal.",
    result: "Your interview lesson",
  },
  "aptitude-learning": {
    title: "Aptitude Learning",
    description: "Learn the reasoning behind an aptitude topic, see each step worked through, and build confidence with practice.",
    result: "Your aptitude lesson",
  },
  "recruitment-email": {
    title: "Recruitment Email Assistant",
    description: "Make recruiter and HR messages easier to act on. We’ll clarify the request, highlight stated dates, and organize your next steps.",
    result: "Recruitment message explained",
  },
};

const pathParts = location.pathname.split("/").filter(Boolean);
const tool = pathParts[pathParts.length - 1];
const workflow = tools[tool];
const statusMessage = document.querySelector("#tool-status");
const resultSection = document.querySelector("#tool-result");
const resultContent = document.querySelector("#result-content");
const submitButtons = [...document.querySelectorAll(".career-form button[type=submit]")];
const quizPanel = document.querySelector("#quiz-panel");
const quizQuestions = document.querySelector("#quiz-questions");
const quizProgress = document.querySelector("#quiz-progress");
const quizDifficultyBadge = document.querySelector("#quiz-difficulty-badge");
const quizScore = document.querySelector("#quiz-score");
const submitQuizButton = document.querySelector("#submit-quiz");
const retakeQuizButton = document.querySelector("#retake-quiz");
let activeQuiz = null;
let activeDifficulty = "";

if (workflow) {
  document.title = `${workflow.title} | ToneWise AI`;
  document.querySelector("#tool-title").textContent = workflow.title;
  document.querySelector("#tool-description").textContent = workflow.description;
  document.querySelector(`#workflow-${tool}`).hidden = false;
} else {
  location.replace("/dashboard");
}

function showStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

document.querySelectorAll('.career-form[data-tool="job-description"], .career-form[data-tool="recruitment-email"]').forEach((form) => {
  const text = form.elements.text;
  const file = form.elements.file;
  text.addEventListener("input", () => { if (text.value.trim()) file.value = ""; });
  file.addEventListener("change", () => { if (file.files.length) text.value = ""; });
});

document.querySelectorAll(".career-form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formTool = form.dataset.tool;
    const action = event.submitter?.dataset.action || "learn";
    const topic = form.elements.topic?.value.trim() || "";
    const text = form.elements.text?.value.trim() || "";
    const file = form.elements.file?.files[0] || null;

    if ((formTool === "job-description" || formTool === "recruitment-email") && Boolean(text) === Boolean(file)) {
      showStatus("Please provide pasted content or choose one file.", true);
      return;
    }
    if (file && file.size > 10 * 1024 * 1024) {
      showStatus("The file is larger than 10 MB. Choose a smaller file.", true);
      return;
    }
    if ((formTool === "interview-preparation" || formTool === "aptitude-learning") && !topic) {
      showStatus("Enter a skill or topic first so the lesson and practice are relevant to you.", true);
      return;
    }
    if (formTool === "recruitment-email" && !form.elements.email_type.value) {
      showStatus("Choose the type of recruitment message first.", true);
      return;
    }

    const payload = new FormData();
    payload.append("tool", formTool);
    payload.append("action", action);
    payload.append("topic", topic);
    payload.append("difficulty", form.elements.difficulty?.value || "Beginner");
    payload.append("email_type", form.elements.email_type?.value || "");
    payload.append("text", text);
    if (file) payload.append("file", file);

    submitButtons.forEach((button) => { button.disabled = true; });
    const clickedButton = event.submitter || form.querySelector(`[data-action="${action}"]`);
    const originalText = clickedButton.textContent;
    clickedButton.textContent = "Preparing your guide…";
    showStatus("ToneWise AI is working on your career guide…");
    resultSection.hidden = true;

    try {
      const response = await fetch("/api/job-seeker/tools", { method: "POST", body: payload });
      const data = await response.json();
      if (response.status === 401) {
        location.assign("/signin");
        return;
      }
      if (!response.ok || !data.success) {
        throw new Error(data.detail || data.errors?.join(" | ") || "Could not prepare this career guide.");
      }

      const isQuiz = action === "quiz";
      resultContent.hidden = isQuiz;
      quizPanel.hidden = !isQuiz;
      if (isQuiz) {
        activeQuiz = data.quiz;
        activeDifficulty = data.difficulty;
        renderQuiz();
      } else {
        resultContent.textContent = data.response;
        document.querySelector("#result-title").textContent = workflow.result;
      }
      document.querySelector("#provider-note").textContent =
        data.provider_used ? `Prepared with ${data.provider_used}.` : "";
      resultSection.hidden = false;
      showStatus("Your career guide is ready.");
      resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      showStatus(error.message || "Could not prepare this career guide.", true);
    } finally {
      submitButtons.forEach((button) => { button.disabled = false; });
      if (clickedButton) clickedButton.textContent = originalText;
    }
  });
});

function renderQuiz() {
  const questions = activeQuiz.questions;
  quizQuestions.replaceChildren();
  quizScore.textContent = "";
  submitQuizButton.hidden = false;
  submitQuizButton.disabled = false;
  retakeQuizButton.hidden = true;
  quizDifficultyBadge.textContent = `${activeDifficulty} level`;
  quizProgress.textContent = `${questions.length} questions · Choose one answer for each`;
  document.querySelector("#result-title").textContent = `${activeDifficulty} quiz`;

  questions.forEach((question, questionIndex) => {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "quiz-question";
    fieldset.dataset.questionIndex = String(questionIndex);

    const legend = document.createElement("legend");
    legend.textContent = `${questionIndex + 1}. ${question.question}`;
    fieldset.append(legend);

    const options = document.createElement("div");
    options.className = "quiz-options";
    question.options.forEach((option, optionIndex) => {
      const label = document.createElement("label");
      label.className = "quiz-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = `quiz-question-${questionIndex}`;
      input.value = String(optionIndex);
      input.setAttribute("aria-label", option);
      const marker = document.createElement("span");
      marker.className = "option-marker";
      marker.textContent = String.fromCharCode(65 + optionIndex);
      const text = document.createElement("span");
      text.className = "option-text";
      text.textContent = option;
      label.append(input, marker, text);
      options.append(label);
    });

    const explanation = document.createElement("p");
    explanation.className = "quiz-explanation";
    explanation.hidden = true;
    explanation.textContent = question.explanation;
    fieldset.append(options, explanation);
    quizQuestions.append(fieldset);
  });
  quizQuestions.addEventListener("change", updateQuizProgress);
}

function updateQuizProgress() {
  const total = quizQuestions.querySelectorAll(".quiz-question").length;
  const answered = quizQuestions.querySelectorAll(".quiz-question input:checked").length;
  quizProgress.textContent = `${answered} of ${total} answered`;
}

submitQuizButton.addEventListener("click", () => {
  const questionCards = [...quizQuestions.querySelectorAll(".quiz-question")];
  const answers = questionCards.map((card) =>
    card.querySelector("input[type=radio]:checked"),
  );
  const unansweredIndex = answers.findIndex((answer) => !answer);
  if (unansweredIndex !== -1) {
    quizProgress.textContent = `Answer question ${unansweredIndex + 1} before submitting.`;
    questionCards[unansweredIndex].scrollIntoView({ behavior: "smooth", block: "center" });
    questionCards[unansweredIndex].querySelector("input").focus();
    return;
  }

  let score = 0;
  questionCards.forEach((card, index) => {
    const selectedIndex = Number(answers[index].value);
    const question = activeQuiz.questions[index];
    const isCorrect = selectedIndex === question.correct_index;
    if (isCorrect) score += 1;
    card.querySelectorAll(".quiz-option").forEach((label, optionIndex) => {
      label.classList.toggle("is-correct", optionIndex === question.correct_index);
      label.classList.toggle("is-incorrect", optionIndex === selectedIndex && !isCorrect);
      label.querySelector("input").disabled = true;
    });
    const explanation = card.querySelector(".quiz-explanation");
    explanation.hidden = false;
    explanation.textContent = `${isCorrect ? "Correct. " : `Not quite. The correct answer is ${String.fromCharCode(65 + question.correct_index)}. `}${question.explanation}`;
  });

  quizProgress.textContent = "Quiz complete";
  const percentage = Math.round((score / questionCards.length) * 100);
  const encouragement = percentage === 100
    ? "Perfect score—excellent work!"
    : percentage >= 60
      ? "Good progress—review the explanations to strengthen your skills."
      : "Keep practicing—your explanations below show what to review.";
  quizScore.textContent = `You scored ${score} out of ${questionCards.length} (${percentage}%). ${encouragement}`;
  submitQuizButton.hidden = true;
  retakeQuizButton.hidden = false;
});

retakeQuizButton.addEventListener("click", () => {
  resultSection.hidden = true;
  quizPanel.hidden = true;
  const form = document.querySelector(`.career-form[data-tool="${tool}"]`);
  form.querySelector('[data-action="quiz"]').focus();
  form.scrollIntoView({ behavior: "smooth", block: "center" });
  showStatus("Choose a difficulty or topic and start another quiz.");
});

document.querySelector("#copy-result").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    const content = quizPanel.hidden
      ? resultContent.textContent
      : quizQuestions.innerText;
    await navigator.clipboard.writeText(content);
    button.textContent = "Copied";
    setTimeout(() => { button.textContent = "Copy"; }, 1600);
  } catch {
    showStatus("Could not access the clipboard. Select and copy the result text instead.", true);
  }
});

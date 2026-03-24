const boot = window.__STUDY_BOOTSTRAP__;

const state = {
  session: null,
  currentIndex: 0,
  trialStartedAt: null,
  aiRevealedAt: null,
  loading: false,
  error: '',
};

const app = document.getElementById('app');

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function conditionKey() {
  return boot.query.condition === 'ai' ? 'ai' : 'baseline';
}

function conditionMeta() {
  return boot.conditions[conditionKey()];
}

async function apiPost(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || 'Request failed.');
  }
  return data;
}

function renderShell(innerHtml) {
  app.innerHTML = `
    <main class="study-shell">
      <section class="study-card">
        ${innerHtml}
      </section>
    </main>
  `;
}

function introHtml() {
  const previewMode = boot.query.assignmentId === 'ASSIGNMENT_ID_NOT_AVAILABLE';
  const meta = conditionMeta();
  return `
    <div class="topline">
      <div>
        <p class="eyebrow">CSE 594 Human AI Interaction</p>
        <h1>${escapeHtml(boot.title)}</h1>
      </div>
      <span class="condition-pill ${conditionKey()}">${escapeHtml(meta.label)}</span>
    </div>

    <div class="intro-grid">
      <div class="panel soft-panel">
        <h2>Your task</h2>
        <p>You will read a short client statement and a candidate counselor response. Your job is to judge whether the counselor response is <strong>appropriate</strong> or <strong>problematic</strong>.</p>
        <ul class="clean-list">
          <li>Appropriate: empathetic, collaborative, ethically aligned, safety-aware</li>
          <li>Problematic: invalidating, coercive, boundary-violating, or unsafe</li>
          <li>You will complete ${boot.config.trialsPerParticipant} trials</li>
          <li>You will also rate your confidence on each trial</li>
        </ul>
      </div>

      <div class="panel accent-panel">
        <h2>Condition</h2>
        <p>${escapeHtml(meta.description)}</p>
        ${conditionKey() === 'ai' ? '<p class="small-note">In this version, AI help is optional. You can reveal it when you want it, and the system logs whether you used it.</p>' : '<p class="small-note">This version intentionally shows no AI assistance.</p>'}
        <div class="meta-block">
          <p><strong>Worker ID:</strong> ${escapeHtml(boot.query.workerId || '(not provided)')}</p>
          <p><strong>Assignment ID:</strong> ${escapeHtml(boot.query.assignmentId || '(local test)')}</p>
        </div>
      </div>
    </div>

    ${previewMode ? '<div class="notice error">MTurk preview mode detected. Accept the HIT first, then reopen the link to start.</div>' : ''}
    ${state.error ? `<div class="notice error">${escapeHtml(state.error)}</div>` : ''}

    <div class="button-row left">
      <button class="primary-button" id="start-study" ${previewMode ? 'disabled' : ''}>Start study</button>
    </div>
  `;
}

function renderIntro() {
  renderShell(introHtml());
  const startButton = document.getElementById('start-study');
  if (startButton) {
    startButton.addEventListener('click', startStudy);
  }
}

async function startStudy() {
  state.loading = true;
  state.error = '';
  renderIntro();
  try {
    const payload = await apiPost('/api/start', {
      condition: conditionKey(),
      worker_id: boot.query.workerId || '',
      assignment_id: boot.query.assignmentId || '',
      hit_id: boot.query.hitId || '',
      turk_submit_to: boot.query.turkSubmitTo || '',
      user_agent: navigator.userAgent,
    });
    state.session = payload;
    state.currentIndex = payload.responses.length;
    if (payload.participant.status === 'completed') {
      renderAlreadyCompleted();
      return;
    }
    renderCurrentStep();
  } catch (error) {
    state.error = error.message;
    renderIntro();
  } finally {
    state.loading = false;
  }
}

function currentTrial() {
  return state.session.trials[state.currentIndex];
}

function progressPercent() {
  if (!state.session) return 0;
  return Math.round((state.currentIndex / state.session.trials.length) * 100);
}

function renderCurrentStep() {
  if (!state.session) {
    renderIntro();
    return;
  }
  if (state.currentIndex >= state.session.trials.length) {
    renderPostSurvey();
    return;
  }
  renderTrial();
}

function renderTrial() {
  const trial = currentTrial();
  const meta = conditionMeta();
  state.trialStartedAt = Date.now();
  state.aiRevealedAt = null;

  renderShell(`
    <div class="progress-row">
      <div>
        <p class="eyebrow">${escapeHtml(meta.label)} condition</p>
        <h2>Trial ${state.currentIndex + 1} of ${state.session.trials.length}</h2>
      </div>
      <div class="progress-pill">${progressPercent()}% complete</div>
    </div>
    <div class="progress-bar"><span style="width:${progressPercent()}%"></span></div>

    <div class="trial-grid">
      <article class="panel statement-panel">
        <p class="panel-label">Client statement</p>
        <p class="trial-text">${escapeHtml(trial.input_client_statement)}</p>
      </article>
      <article class="panel response-panel">
        <p class="panel-label">Counselor response</p>
        <p class="trial-text">${escapeHtml(trial.input_counselor_response)}</p>
      </article>
    </div>

    ${conditionKey() === 'ai' ? renderAiPanel(trial) : ''}

    <form id="trial-form" class="panel answer-panel">
      <p class="panel-label">Your judgment</p>
      <div class="option-grid two-col">
        <label class="choice-card">
          <input type="radio" name="participant_label" value="appropriate">
          <span>Appropriate</span>
        </label>
        <label class="choice-card">
          <input type="radio" name="participant_label" value="problematic">
          <span>Problematic</span>
        </label>
      </div>

      <p class="panel-label tight-top">How confident are you in this judgment?</p>
      <div class="option-grid five-col">
        ${boot.config.confidenceOptions.map((value) => `
          <label class="choice-card small-card">
            <input type="radio" name="confidence" value="${value}">
            <span>${value}</span>
          </label>
        `).join('')}
      </div>

      <div id="trial-error" class="notice error hidden"></div>
      <div class="button-row left">
        <button type="submit" class="primary-button">Save and continue</button>
      </div>
    </form>
  `);

  const revealButton = document.getElementById('reveal-ai');
  if (revealButton) {
    revealButton.addEventListener('click', () => revealAi(trial));
  }

  document.getElementById('trial-form').addEventListener('submit', submitTrial);
}

function renderAiPanel(trial) {
  return `
    <section class="panel ai-panel ${conditionKey()}">
      <div class="ai-header">
        <div>
          <p class="panel-label">Optional AI assistance</p>
          <p class="small-note">Reveal the AI suggestion if you want decision support. Your choice to reveal it will be logged.</p>
        </div>
        <button type="button" id="reveal-ai" class="secondary-button">Reveal AI suggestion</button>
      </div>
      <div id="ai-content" class="ai-content hidden">
        <div class="ai-badge-row">
          <span class="condition-pill ai">AI says: ${escapeHtml(trial.model_output)}</span>
          <span class="progress-pill">P(appropriate): ${(Number(trial.model_probability) * 100).toFixed(1)}%</span>
        </div>
        <p class="trial-text">${escapeHtml(trial.ai_assistance)}</p>
      </div>
    </section>
  `;
}

function revealAi() {
  const panel = document.getElementById('ai-content');
  if (!panel) return;
  panel.classList.remove('hidden');
  state.aiRevealedAt = state.aiRevealedAt || Date.now();
  const button = document.getElementById('reveal-ai');
  if (button) {
    button.disabled = true;
    button.textContent = 'AI revealed';
  }
}

async function submitTrial(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const participantLabel = formData.get('participant_label');
  const confidence = formData.get('confidence');
  const errorBox = document.getElementById('trial-error');

  if (!participantLabel || !confidence) {
    errorBox.textContent = 'Please choose a label and a confidence rating before continuing.';
    errorBox.classList.remove('hidden');
    return;
  }

  errorBox.classList.add('hidden');
  const trial = currentTrial();
  const timeSpentMs = Date.now() - state.trialStartedAt;
  const aiRequested = Boolean(state.aiRevealedAt);
  const aiRequestElapsedMs = aiRequested ? state.aiRevealedAt - state.trialStartedAt : null;

  try {
    await apiPost('/api/submit-trial', {
      participant_id: state.session.participant.participant_id,
      trial_id: trial.trial_id,
      order_index: trial.order_index,
      participant_label: participantLabel,
      confidence: Number(confidence),
      time_spent_ms: timeSpentMs,
      ai_requested: aiRequested,
      ai_request_elapsed_ms: aiRequestElapsedMs,
    });

    state.session.responses.push({
      trial_id: trial.trial_id,
      order_index: trial.order_index,
      participant_label: participantLabel,
      confidence: Number(confidence),
      time_spent_ms: timeSpentMs,
      ai_requested: aiRequested ? 1 : 0,
    });
    state.currentIndex += 1;
    renderCurrentStep();
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove('hidden');
  }
}

function renderPostSurvey() {
  renderShell(`
    <div class="progress-row">
      <div>
        <p class="eyebrow">Final questionnaire</p>
        <h2>One more minute</h2>
      </div>
      <div class="progress-pill">Task complete</div>
    </div>

    <form id="post-form" class="panel answer-panel">
      <p class="panel-label">Overall, how confident were you in your answers?</p>
      <div class="option-grid five-col">
        ${boot.config.confidenceOptions.map((value) => `
          <label class="choice-card small-card">
            <input type="radio" name="overall_confidence" value="${value}">
            <span>${value}</span>
          </label>
        `).join('')}
      </div>

      <p class="panel-label tight-top">How mentally demanding did this task feel?</p>
      <div class="option-grid five-col">
        ${boot.config.workloadOptions.map((value) => `
          <label class="choice-card small-card">
            <input type="radio" name="workload" value="${value}">
            <span>${value}</span>
          </label>
        `).join('')}
      </div>

      ${conditionKey() === 'ai' ? `
        <p class="panel-label tight-top">How helpful was the AI assistance overall?</p>
        <div class="option-grid five-col">
          ${boot.config.workloadOptions.map((value) => `
            <label class="choice-card small-card">
              <input type="radio" name="ai_helpfulness" value="${value}">
              <span>${value}</span>
            </label>
          `).join('')}
        </div>
      ` : ''}

      <p class="panel-label tight-top">Comments (optional)</p>
      <textarea name="comments" rows="4" class="comment-box" placeholder="Anything that was confusing, helpful, or frustrating?"></textarea>

      <div id="post-error" class="notice error hidden"></div>
      <div class="button-row left">
        <button type="submit" class="primary-button">Finish study</button>
      </div>
    </form>
  `);

  document.getElementById('post-form').addEventListener('submit', submitPostSurvey);
}

async function submitPostSurvey(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const overallConfidence = formData.get('overall_confidence');
  const workload = formData.get('workload');
  const aiHelpfulness = formData.get('ai_helpfulness');
  const errorBox = document.getElementById('post-error');

  if (!overallConfidence || !workload || (conditionKey() === 'ai' && !aiHelpfulness)) {
    errorBox.textContent = 'Please answer the required questionnaire items before finishing.';
    errorBox.classList.remove('hidden');
    return;
  }

  try {
    const result = await apiPost('/api/complete', {
      participant_id: state.session.participant.participant_id,
      overall_confidence: Number(overallConfidence),
      workload: Number(workload),
      ai_helpfulness: aiHelpfulness ? Number(aiHelpfulness) : null,
      comments: formData.get('comments') || '',
    });
    renderCompletion(result);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove('hidden');
  }
}

function renderCompletion(result) {
  const submitForm = result.submit_url && result.assignment_id ? `
    <form class="mturk-submit-form" method="POST" action="${escapeHtml(result.submit_url)}">
      <input type="hidden" name="assignmentId" value="${escapeHtml(result.assignment_id)}">
      <input type="hidden" name="completionCode" value="${escapeHtml(result.completion_code)}">
      <button type="submit" class="secondary-button">Optional: auto-submit to MTurk</button>
    </form>
  ` : '';

  renderShell(`
    <div class="topline">
      <div>
        <p class="eyebrow">Study complete</p>
        <h1>Thank you</h1>
      </div>
      <span class="condition-pill ${conditionKey()}">${escapeHtml(conditionMeta().label)}</span>
    </div>

    <div class="panel soft-panel">
      <p><strong>Step 1:</strong> Copy this completion code.</p>
      <div class="completion-code">${escapeHtml(result.completion_code)}</div>
      <p><strong>Step 2:</strong> Return to the MTurk task page and paste the code into the survey code box there.</p>
      <p class="small-note">The survey code box is on the previous MTurk page, not on this study page. Do not leave this page until you have copied the code.</p>
      <div class="button-row left">
        <button type="button" class="primary-button" id="back-to-mturk">Back to MTurk page</button>
      </div>
      ${submitForm}
    </div>
  `);

  const backButton = document.getElementById('back-to-mturk');
  if (backButton) {
    backButton.addEventListener('click', () => {
      window.history.back();
    });
  }
}

function renderAlreadyCompleted() {
  renderShell(`
    <div class="topline">
      <div>
        <p class="eyebrow">Session found</p>
        <h1>This assignment was already completed</h1>
      </div>
      <span class="condition-pill ${conditionKey()}">${escapeHtml(conditionMeta().label)}</span>
    </div>
    <div class="panel soft-panel">
      <p>You already have a completion code stored for this assignment. If you need to recover it, check the study database or export file.</p>
    </div>
  `);
}

renderIntro();

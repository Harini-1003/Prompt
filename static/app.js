// State variables
let currentUser = null;
let currentSubjects = [];
let currentPaperData = null;
let currentRefineQIndex = null;
let selectedFile = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  checkAuth();
  setupDragAndDrop();
  loadSubjects();
});

// AUTHENTICATION LOGIC (Satisfies "whatever credentials we put it have to go")
function checkAuth() {
  const saved = localStorage.getItem("autoexam_user");
  if (saved) {
    currentUser = JSON.parse(saved);
    updateNavAuth(currentUser);
  } else {
    updateNavAuth(null);
  }
}

function updateNavAuth(user) {
  const badge = document.getElementById("userBadge");
  const navBtns = document.getElementById("authNavButtons");
  const navUsername = document.getElementById("navUsername");

  if (user) {
    badge.classList.remove("hidden");
    navBtns.classList.add("hidden");
    navUsername.textContent = user.username || "Faculty";
  } else {
    badge.classList.add("hidden");
    navBtns.classList.remove("hidden");
  }
}

function openAuthModal(tab = 'signin') {
  setAuthTab(tab);
  document.getElementById("authModal").classList.remove("hidden");
}

function closeAuthModal() {
  document.getElementById("authModal").classList.add("hidden");
}

function setAuthTab(tab) {
  const btnIn = document.getElementById("btnAuthTabSignIn");
  const btnUp = document.getElementById("btnAuthTabSignUp");
  const nameGrp = document.getElementById("authFullNameGroup");
  const submitBtn = document.getElementById("btnSubmitAuth");

  if (tab === 'signup') {
    btnUp.classList.add("active");
    btnIn.classList.remove("active");
    nameGrp.classList.remove("hidden");
    submitBtn.textContent = "Create Account & Sign In";
  } else {
    btnIn.classList.add("active");
    btnUp.classList.remove("active");
    nameGrp.classList.add("hidden");
    submitBtn.textContent = "Sign In";
  }
}

async function submitAuth() {
  const username = document.getElementById("authUsername").value.trim() || "faculty";
  const password = document.getElementById("authPassword").value.trim() || "password";
  const fullName = document.getElementById("authFullName").value.trim() || "Professor";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, full_name: fullName })
    });
    const data = await res.json();
    currentUser = data.user || { username, full_name: fullName };
    localStorage.setItem("autoexam_user", JSON.stringify(currentUser));
    updateNavAuth(currentUser);
    closeAuthModal();
    goToApp();
  } catch (e) {
    // Immediate fallback: allow any credentials unconditionally
    currentUser = { username, full_name: fullName };
    localStorage.setItem("autoexam_user", JSON.stringify(currentUser));
    updateNavAuth(currentUser);
    closeAuthModal();
    goToApp();
  }
}

function handleLogout() {
  localStorage.removeItem("autoexam_user");
  currentUser = null;
  updateNavAuth(null);
  switchView('landing');
}

// VIEW SWITCHING
function switchView(viewName) {
  document.getElementById("viewLanding").classList.remove("active");
  document.getElementById("viewDashboard").classList.remove("active");

  if (viewName === 'landing') {
    document.getElementById("viewLanding").classList.add("active");
  } else {
    document.getElementById("viewDashboard").classList.add("active");
  }
}

function goToApp() {
  switchView('dashboard');
  switchTab('subjects');
}

function switchTab(tabId) {
  // Update tab buttons
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));

  if (tabId === 'subjects') {
    document.querySelector("button[onclick=\"switchTab('subjects')\"]").classList.add("active");
    document.getElementById("tabSubjects").classList.add("active");
    loadSubjects();
  } else if (tabId === 'upload') {
    document.querySelector("button[onclick=\"switchTab('upload')\"]").classList.add("active");
    document.getElementById("tabUpload").classList.add("active");
    populateSubjectSelects();
  } else if (tabId === 'generate') {
    document.querySelector("button[onclick=\"switchTab('generate')\"]").classList.add("active");
    document.getElementById("tabGenerate").classList.add("active");
    populateSubjectSelects();
  } else if (tabId === 'blueprint') {
    document.querySelector("button[onclick=\"switchTab('blueprint')\"]").classList.add("active");
    document.getElementById("tabBlueprint").classList.add("active");
  } else if (tabId === 'history') {
    document.querySelector("button[onclick=\"switchTab('history')\"]").classList.add("active");
    document.getElementById("tabHistory").classList.add("active");
    loadHistory();
  }
}

// 1. SUBJECTS LOGIC
async function loadSubjects() {
  const container = document.getElementById("subjectsList");
  try {
    const res = await fetch("/api/subjects");
    const data = await res.json();
    currentSubjects = data.subjects || [];
    renderSubjectsGrid(currentSubjects);
    populateSubjectSelects();
  } catch (e) {
    container.innerHTML = `<p class="text-rose-400">Failed to load subjects: ${e.message}</p>`;
  }
}

function renderSubjectsGrid(subjects) {
  const container = document.getElementById("subjectsList");
  container.innerHTML = "";

  subjects.forEach(subj => {
    const isIndexed = subj.chunk_count > 0;
    const card = document.createElement("div");
    card.className = "subject-card";
    card.innerHTML = `
      <div class="subject-header">
        <span class="subject-title">${escapeHtml(subj.name)}</span>
        <span class="subject-code-badge">${escapeHtml(subj.code || 'SUBJ')}</span>
      </div>
      <div class="subject-status ${isIndexed ? 'indexed' : ''}">
        <i class="fa-solid ${isIndexed ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i>
        ${isIndexed ? `${subj.chunk_count} syllabus chunks indexed` : 'No syllabus uploaded yet'}
      </div>
      <div class="flex-between">
        <button onclick="selectSubjectForUpload(${subj.id})" class="btn-outline-sm">
          <i class="fa-solid fa-cloud-arrow-up"></i> Ingest Syllabus
        </button>
        <button onclick="selectSubjectForGen(${subj.id})" class="btn-primary-sm">
          <i class="fa-solid fa-file-circle-plus"></i> Generate Paper
        </button>
      </div>
    `;
    container.appendChild(card);
  });
}

function populateSubjectSelects() {
  const upSel = document.getElementById("uploadSubjectSelect");
  const genSel = document.getElementById("genSubjectSelect");
  if (!upSel || !genSel) return;

  upSel.innerHTML = "";
  genSel.innerHTML = "";

  currentSubjects.forEach(s => {
    const opt1 = new Option(s.name, s.id);
    const opt2 = new Option(s.name, s.id);
    upSel.add(opt1);
    genSel.add(opt2);
  });
}

function selectSubjectForUpload(id) {
  switchTab('upload');
  document.getElementById("uploadSubjectSelect").value = id;
}

function selectSubjectForGen(id) {
  switchTab('generate');
  document.getElementById("genSubjectSelect").value = id;
}

// 2. UPLOAD & INGESTION LOGIC
function setupDragAndDrop() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("syllabusFileInput");

  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });
}

function handleFileSelected(file) {
  selectedFile = file;
  document.getElementById("selectedFileName").textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  document.getElementById("selectedFileInfo").classList.remove("hidden");
}

function clearSelectedFile() {
  selectedFile = null;
  document.getElementById("syllabusFileInput").value = "";
  document.getElementById("selectedFileInfo").classList.add("hidden");
}

async function handleSyllabusUpload() {
  if (!selectedFile) {
    alert("Please select or drop a syllabus file first.");
    return;
  }

  const subjectId = document.getElementById("uploadSubjectSelect").value;
  const progressBox = document.getElementById("uploadProgress");
  const progressBar = document.getElementById("uploadProgressBar");
  const progressText = document.getElementById("uploadProgressText");
  const btn = document.getElementById("btnProcessSyllabus");

  progressBox.classList.remove("hidden");
  btn.disabled = true;
  progressBar.style.width = "25%";
  progressText.textContent = "Uploading & extracting syllabus text...";

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("subject_id", subjectId);

  try {
    progressBar.style.width = "50%";
    progressText.textContent = "Chunking and computing local vector embeddings...";

    const res = await fetch("/api/syllabus/upload", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }

    progressBar.style.width = "85%";
    progressText.textContent = "Extracting Course Outcomes & mapping units...";

    const data = await res.json();
    progressBar.style.width = "100%";
    progressText.textContent = `Completed! Indexed ${data.chunk_count} chunks.`;

    // Render Preview
    document.getElementById("syllabusPreviewBox").textContent = data.extracted_preview || "Syllabus processed.";
    renderCourseOutcomes(data.course_outcomes || []);

    loadSubjects();
    setTimeout(() => progressBox.classList.add("hidden"), 3000);
  } catch (err) {
    alert(`Error processing syllabus: ${err.message}`);
    progressBox.classList.add("hidden");
  } finally {
    btn.disabled = false;
  }
}

function renderCourseOutcomes(cos) {
  const container = document.getElementById("coListDisplay");
  container.innerHTML = "";
  if (!cos || cos.length === 0) {
    container.innerHTML = "<p class='text-slate-500 text-sm'>No COs extracted.</p>";
    return;
  }
  cos.forEach(c => {
    const div = document.createElement("div");
    div.className = "co-item";
    div.innerHTML = `<span class="co-tag">${escapeHtml(c.co_id)}</span> <span>${escapeHtml(c.description)}</span>`;
    container.appendChild(div);
  });
}

// 3. GENERATION LOGIC
async function handleGeneratePaper() {
  const subjectId = document.getElementById("genSubjectSelect").value;
  const collegeName = document.getElementById("genCollegeName").value;
  const examName = document.getElementById("genExamName").value;
  const subjectCode = document.getElementById("genSubjectCode").value;
  const duration = parseInt(document.getElementById("genDuration").value) || 180;

  // Selected Bloom's levels
  const bloomChecked = Array.from(document.querySelectorAll(".bloom-check:checked")).map(cb => cb.value);
  if (bloomChecked.length === 0) {
    alert("Please select at least one Bloom's Taxonomy level.");
    return;
  }

  const sections = [
    {
      name: "Part A",
      type: "Short Answer",
      marks_per_q: parseInt(document.getElementById("secAMarks").value) || 2,
      count: parseInt(document.getElementById("secACount").value) || 5
    },
    {
      name: "Part B",
      type: "Medium Analytical",
      marks_per_q: parseInt(document.getElementById("secBMarks").value) || 8,
      count: parseInt(document.getElementById("secBCount").value) || 5
    },
    {
      name: "Part C",
      type: "Comprehensive Application / Case Study",
      marks_per_q: parseInt(document.getElementById("secCMarks").value) || 10,
      count: parseInt(document.getElementById("secCCount").value) || 1
    }
  ];

  const payload = {
    subject_id: parseInt(subjectId),
    college_name: collegeName,
    exam_name: examName,
    subject_code: subjectCode,
    duration_minutes: duration,
    blooms_distribution: bloomChecked.join(", "),
    sections: sections
  };

  const progressBox = document.getElementById("genProgress");
  const progressBar = document.getElementById("genProgressBar");
  const progressText = document.getElementById("genProgressText");
  const btn = document.getElementById("btnGeneratePaper");

  progressBox.classList.remove("hidden");
  btn.disabled = true;
  progressBar.style.width = "30%";
  progressText.textContent = "Retrieving grounded syllabus chunks...";

  try {
    progressBar.style.width = "65%";
    progressText.textContent = "Prompting LLM with strict Bloom's taxonomy & anti-hallucination rules...";

    const res = await fetch("/api/paper/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Paper generation failed");
    }

    progressBar.style.width = "100%";
    progressText.textContent = "Validating blueprint coverage and formatting exam paper...";

    const paperResult = await res.json();
    currentPaperData = paperResult;

    // Switch to blueprint view
    renderPaperAndBlueprint(paperResult);
    switchTab('blueprint');
  } catch (err) {
    alert(`Generation error: ${err.message}`);
  } finally {
    btn.disabled = false;
    progressBox.classList.add("hidden");
  }
}

// 4. BLUEPRINT & PAPER RENDERING
function renderPaperAndBlueprint(paper) {
  document.getElementById("noPaperPlaceholder").classList.add("hidden");
  document.getElementById("paperContentWrapper").classList.remove("hidden");

  // Render Blueprint Matrix
  renderBlueprintTable(paper.blueprint);

  // Render Header Details
  document.getElementById("displayCollegeName").textContent = (paper.college_name || "Autonomous Institute").toUpperCase();
  document.getElementById("displayExamName").textContent = (paper.exam_name || "Degree Examination").toUpperCase();
  document.getElementById("displayMetaBar").innerHTML = `
    <span><b>Subject:</b> ${escapeHtml(paper.subject_name)} (${escapeHtml(paper.subject_code)})</span>
    <span><b>Time:</b> ${paper.duration_minutes} Mins</span>
    <span><b>Max Marks:</b> ${paper.total_marks}</span>
  `;

  // Render Questions per Section
  const secContainer = document.getElementById("renderedQuestionsList");
  secContainer.innerHTML = "";

  (paper.sections || []).forEach(sec => {
    const secBlock = document.createElement("div");
    secBlock.className = "rendered-section-block";
    secBlock.innerHTML = `
      <div class="section-heading-bar">${escapeHtml(sec.section_name)} (${escapeHtml(sec.section_type)}) - ${sec.marks_per_question} Marks Each</div>
    `;

    (sec.questions || []).forEach((q) => {
      const qRow = document.createElement("div");
      qRow.className = "question-row";
      qRow.innerHTML = `
        <div class="q-main">
          <div><b>${escapeHtml(q.question_number)}.</b> ${escapeHtml(q.question_text)}</div>
          <div class="q-meta-badges">
            <span class="badge-co">${escapeHtml(q.course_outcome || 'CO1')}</span>
            <span class="badge-bloom">${escapeHtml(q.bloom_level || 'Understand')}</span>
            <span class="badge-marks">${q.marks} Marks</span>
            <span class="badge-co">${escapeHtml(q.unit || 'Unit 1')}</span>
          </div>
        </div>
        <button onclick="openRefineModal('${escapeHtml(q.question_number)}')" class="btn-refine-trigger">
          <i class="fa-solid fa-pen-nib"></i> Refine
        </button>
      `;
      secBlock.appendChild(qRow);
    });

    secContainer.appendChild(secBlock);
  });

  // Render Answer Key
  const ansContainer = document.getElementById("renderedAnswerKey");
  ansContainer.innerHTML = "";
  (paper.all_questions || []).forEach(q => {
    const ansRow = document.createElement("div");
    ansRow.className = "question-row";
    ansRow.innerHTML = `
      <div class="q-main">
        <div><b>${escapeHtml(q.question_number)}:</b> <span class="text-slate-300">${escapeHtml(q.model_answer)}</span></div>
        <div class="text-xs text-amber-300 mt-1"><b>Marking Scheme:</b> ${escapeHtml(q.marking_scheme)} (${q.marks}M)</div>
      </div>
    `;
    ansContainer.appendChild(ansRow);
  });
}

function renderBlueprintTable(blueprint) {
  if (!blueprint) return;
  const table = document.getElementById("blueprintTable");
  const warningsBox = document.getElementById("blueprintWarnings");
  document.getElementById("blueprintTotalBadge").textContent = `Total Marks: ${blueprint.total_marks}`;

  warningsBox.innerHTML = "";
  (blueprint.warnings || []).forEach(w => {
    warningsBox.innerHTML += `<div><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(w)}</div>`;
  });

  const blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"];
  const cos = ["CO1", "CO2", "CO3", "CO4", "CO5"];

  let html = `<thead><tr><th>CO / Bloom's</th>`;
  blooms.forEach(b => html += `<th>${b}</th>`);
  html += `<th>Total Marks</th></tr></thead><tbody>`;

  cos.forEach(co => {
    html += `<tr><td><b>${co}</b></td>`;
    blooms.forEach(b => {
      const marks = (blueprint.matrix[co] && blueprint.matrix[co][b]) || 0;
      html += `<td>${marks > 0 ? `<b>${marks}M</b>` : '-'}</td>`;
    });
    html += `<td><b>${blueprint.co_totals[co] || 0}M</b></td></tr>`;
  });

  // Footer totals
  html += `<tr style="background:#0f172a"><td><b>Bloom Total</b></td>`;
  blooms.forEach(b => {
    html += `<td><b>${blueprint.bloom_totals[b] || 0}M</b></td>`;
  });
  html += `<td><b class="text-emerald-400">${blueprint.total_marks}M</b></td></tr></tbody>`;

  table.innerHTML = html;
}

// 5. REFINEMENT
function openRefineModal(qNum) {
  if (!currentPaperData) return;
  const allQ = currentPaperData.all_questions || [];
  const targetQ = allQ.find(q => q.question_number === qNum);
  if (!targetQ) return;

  currentRefineQIndex = targetQ.question_number;
  document.getElementById("refineQuestionNumberLabel").textContent = `Refining Question ${targetQ.question_number} (${targetQ.marks} Marks)`;
  document.getElementById("refineOriginalText").textContent = targetQ.question_text;
  document.getElementById("refineInstructionInput").value = "";
  document.getElementById("refineModal").classList.remove("hidden");
}

function closeRefineModal() {
  document.getElementById("refineModal").classList.add("hidden");
}

function setRefineText(text) {
  document.getElementById("refineInstructionInput").value = text;
}

async function submitQuestionRefinement() {
  const instruction = document.getElementById("refineInstructionInput").value.trim();
  if (!instruction) {
    alert("Please enter a refinement instruction.");
    return;
  }

  const allQ = currentPaperData.all_questions;
  const targetQ = allQ.find(q => q.question_number === currentRefineQIndex);
  if (!targetQ) return;

  const btn = document.getElementById("btnSubmitRefine");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Refining...`;

  try {
    const res = await fetch("/api/paper/refine-question", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject_id: currentPaperData.subject_id,
        question: targetQ,
        instruction: instruction
      })
    });

    if (!res.ok) throw new Error("Refinement request failed");
    const refinedQ = await res.json();

    // Drop-in replace only that question in memory
    Object.assign(targetQ, refinedQ);

    // Also update inside sections
    for (const sec of currentPaperData.sections) {
      for (let i = 0; i < sec.questions.length; i++) {
        if (sec.questions[i].question_number === targetQ.question_number) {
          sec.questions[i] = refinedQ;
        }
      }
    }

    // Recompute blueprint
    const bpRes = await fetch("/api/paper/recompute-blueprint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questions: currentPaperData.all_questions })
    });
    if (bpRes.ok) {
      currentPaperData.blueprint = await bpRes.json();
    }

    closeRefineModal();
    renderPaperAndBlueprint(currentPaperData);
  } catch (e) {
    alert(`Refinement failed: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-check"></i> Refine This Question`;
  }
}

function regenerateEntirePaper() {
  handleGeneratePaper();
}

// 6. EXPORT LOGIC
async function exportCurrentPaper(format = 'pdf') {
  if (!currentPaperData) {
    alert("No paper to export.");
    return;
  }

  try {
    const res = await fetch(`/api/paper/export?format=${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentPaperData)
    });

    if (!res.ok) throw new Error("Export generation failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Exam_Paper_${currentPaperData.subject_code || 'QuestionPaper'}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (e) {
    alert(`Failed to export ${format.toUpperCase()}: ${e.message}`);
  }
}

// 7. HISTORY LOGIC
async function loadHistory() {
  const container = document.getElementById("historyList");
  try {
    const res = await fetch("/api/papers/history");
    const data = await res.json();
    const papers = data.papers || [];

    if (papers.length === 0) {
      container.innerHTML = `<p class="text-slate-500">No generated papers stored yet.</p>`;
      return;
    }

    container.innerHTML = "";
    papers.forEach(p => {
      const item = document.createElement("div");
      item.className = "subject-card mb-3";
      item.innerHTML = `
        <div class="flex-between">
          <div>
            <h4>${escapeHtml(p.exam_name)} - ${escapeHtml(p.subject_name)} (${escapeHtml(p.subject_code)})</h4>
            <p class="text-xs text-slate-400">Created: ${p.created_at} | Total Marks: ${p.total_marks}</p>
          </div>
          <button onclick="loadPaperById(${p.id})" class="btn-primary-sm">
            <i class="fa-solid fa-folder-open"></i> Open Paper
          </button>
        </div>
      `;
      container.appendChild(item);
    });
  } catch (e) {
    container.innerHTML = `<p class="text-rose-400">Failed to load history: ${e.message}</p>`;
  }
}

async function loadPaperById(id) {
  try {
    const res = await fetch(`/api/papers/${id}`);
    const data = await res.json();
    currentPaperData = data;
    renderPaperAndBlueprint(data);
    switchTab('blueprint');
  } catch (e) {
    alert(`Failed to retrieve paper: ${e.message}`);
  }
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

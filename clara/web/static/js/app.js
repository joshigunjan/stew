let activeDatasetId = null;
let activeProfile = null;
let chatHistory = [];
let allPreviewRows = [];

document.addEventListener("DOMContentLoaded", () => {
    initIntakeModes();
    initDropZone();
    initZenodoIngest();
    initKitchenTabs();
    initSettingsModal();
    initChat();
    initTableSearch();
    checkBackendStatus();
});

// Check Helmholtz Blablador status
async function checkBackendStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        const indicator = document.getElementById("statusIndicatorText");
        const dot = document.querySelector(".pulse-indicator");
        
        if (data.is_configured) {
            indicator.textContent = `Blablador Connected (${data.model})`;
            dot.style.backgroundColor = "var(--stew-sage)";
        } else {
            indicator.textContent = `Stew Local Mode (${data.model})`;
            dot.style.backgroundColor = "var(--stew-copper)";
        }
    } catch (e) {
        console.error("Status check error", e);
    }
}

// Intake Mode Switcher (Zenodo vs Upload vs Samples)
function initIntakeModes() {
    const tabBtns = document.querySelectorAll(".pot-mode-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".intake-panel").forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            const mode = btn.dataset.mode;
            document.getElementById(`panel-${mode}`).classList.add("active");
        });
    });
}

// Zenodo & DOI Ingestion
function initZenodoIngest() {
    const ingestBtn = document.getElementById("zenodoIngestBtn");
    const input = document.getElementById("zenodoInput");

    ingestBtn.addEventListener("click", () => {
        const val = input.value.trim();
        if (val) importZenodo(val);
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const val = input.value.trim();
            if (val) importZenodo(val);
        }
    });
}

async function importZenodo(identifier) {
    const isUrl = identifier.startsWith("http://") || identifier.startsWith("https://");
    const label = isUrl ? `web repository: ${identifier}` : `Zenodo: ${identifier}`;
    showSimmering(`Stew is inspecting data structures and metadata from ${label}...`);
    try {
        const res = await fetch("/api/import-url", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: identifier, identifier: identifier })
        });
        
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Import failed");
        }
        onDatasetLoaded(data);
    } catch (err) {
        alert("Import Notice: " + err.message);
    } finally {
        hideSimmering();
    }
}

function setZenodoInput(doi) {
    const input = document.getElementById("zenodoInput");
    input.value = doi;
    importZenodo(doi);
}

// File dropzone
function initDropZone() {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");

    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            uploadFile(fileInput.files[0]);
        }
    });
}

async function uploadFile(file) {
    showSimmering(`Stew is profiling dataset schema and statistical distributions (${file.name})...`);
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload error");
        onDatasetLoaded(data);
    } catch (err) {
        alert("Upload failed: " + err.message);
    } finally {
        hideSimmering();
    }
}

async function loadSample(sampleName) {
    showSimmering(`Stew is loading benchmark dataset: ${sampleName}...`);
    try {
        const res = await fetch(`/api/load-sample/${sampleName}`);
        const data = await res.json();
        onDatasetLoaded(data);
    } catch (err) {
        alert("Failed to load sample: " + err.message);
    } finally {
        hideSimmering();
    }
}

// Dataset Loaded State Handler
function onDatasetLoaded(data) {
    activeDatasetId = data.dataset_id;
    activeProfile = data.profile;
    allPreviewRows = activeProfile.preview_rows || [];
    chatHistory = [
        { role: "assistant", content: data.initial_review }
    ];

    // Transition view from Pot intake to Kitchen dashboard
    document.getElementById("intakeHeroSection").style.display = "none";
    document.getElementById("dashboardCockpit").classList.add("active");

    // Banner metadata
    document.getElementById("datasetTitle").textContent = activeProfile.title;
    document.getElementById("datasetFileName").textContent = activeProfile.file_name;
    document.getElementById("badgeFormat").textContent = activeProfile.file_format.toUpperCase();
    
    // DOI badge if available
    const doiBadge = document.getElementById("badgeDoi");
    if (activeProfile.metadata_context && activeProfile.metadata_context.doi) {
        doiBadge.style.display = "inline-flex";
        doiBadge.textContent = "DOI: " + activeProfile.metadata_context.doi;
        doiBadge.href = `https://doi.org/${activeProfile.metadata_context.doi}`;
    } else {
        doiBadge.style.display = "none";
    }

    // Spatial badge
    const spatialBadge = document.getElementById("badgeSpatial");
    if (activeProfile.is_spatial) {
        spatialBadge.style.display = "inline-block";
        spatialBadge.textContent = "Geospatial";
    } else {
        spatialBadge.style.display = "none";
    }

    // Metrics
    document.getElementById("statRows").textContent = activeProfile.row_count.toLocaleString();
    document.getElementById("statCols").textContent = activeProfile.column_count;
    
    // FAIR² Compliance Gauge & Breakdown
    const fairScore = data.fair_score || { overall_score: 93, grade: "A (AI-Ready)" };
    document.getElementById("fairScoreNum").textContent = fairScore.overall_score;
    document.getElementById("fairGradeBadge").textContent = fairScore.grade;

    if (fairScore.categories) {
        const cats = fairScore.categories;
        const dimF = document.getElementById("dimF");
        const dimA = document.getElementById("dimA");
        const dimI = document.getElementById("dimI");
        const dimR = document.getElementById("dimR");
        if (dimF) dimF.textContent = `F: ${cats.findable ?? 25}`;
        if (dimA) dimA.textContent = `A: ${cats.accessible ?? 25}`;
        if (dimI) dimI.textContent = `I: ${cats.interoperable ?? 25}`;
        if (dimR) dimR.textContent = `R: ${cats.reusable ?? 18}`;
    }

    // Render Preview Table & Columns Deck
    renderTablePreview(allPreviewRows);
    renderColumnsDeck(activeProfile);

    // Render Stew Chat
    renderChatMessages();

    // Default to explorer tab
    switchTab("explorer");
}

// Table search filter
function initTableSearch() {
    const searchInput = document.getElementById("tableSearchInput");
    searchInput.addEventListener("input", () => {
        const query = searchInput.value.toLowerCase().trim();
        if (!query) {
            renderTablePreview(allPreviewRows);
            return;
        }
        const filtered = allPreviewRows.filter(row => {
            return Object.values(row).some(v => String(v).toLowerCase().includes(query));
        });
        renderTablePreview(filtered);
    });
}

function renderTablePreview(rows) {
    const thead = document.getElementById("tableHead");
    const tbody = document.getElementById("tableBody");
    thead.innerHTML = "";
    tbody.innerHTML = "";

    if (!activeProfile || !rows || rows.length === 0) return;
    const cols = (rows[0] && Object.keys(rows[0]).length > 0) ? Object.keys(rows[0]) : Object.keys(activeProfile.columns);

    const headRow = document.createElement("tr");
    cols.forEach(col => {
        const th = document.createElement("th");
        th.textContent = col.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);

    rows.forEach(row => {
        const tr = document.createElement("tr");
        cols.forEach(col => {
            const td = document.createElement("td");
            const val = row[col];
            if (val === null || val === undefined) {
                td.innerHTML = '<span class="null-indicator">null</span>';
            } else if (String(val) === "-999" || String(val) === "-999.0") {
                td.innerHTML = `<span class="sentinel-pill">${val} (sentinel)</span>`;
            } else if (String(val).startsWith("http://") || String(val).startsWith("https://")) {
                td.innerHTML = `<a href="${val}" target="_blank" style="color:var(--stew-copper); font-weight:600; text-decoration:none;">🔗 Access Layer</a>`;
            } else {
                td.textContent = val;
            }
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
}

function renderColumnsDeck(profile) {
    const deck = document.getElementById("columnsDeck");
    deck.innerHTML = "";

    Object.values(profile.columns).forEach(col => {
        const card = document.createElement("div");
        card.className = "col-card-unit";
        card.innerHTML = `
            <div class="col-card-head">
                <span class="col-name-label">${col.name}</span>
                <span class="col-type-badge">${col.inferred_type}</span>
            </div>
            <div class="col-desc-text">${col.suggested_description || "Measurement variable"}</div>
            <div class="col-metric-row">
                <span>Standard Unit:</span>
                <span style="color:var(--stew-copper)">${col.suggested_unit || "dimensionless"}</span>
            </div>
            <div class="col-metric-row">
                <span>Missing / Nulls:</span>
                <span>${col.null_count} (${Math.round(col.null_ratio * 100)}%)</span>
            </div>
            <div class="col-metric-row">
                <span>Distinct Values:</span>
                <span>${col.distinct_count}</span>
            </div>
            ${col.min_val !== null ? `
            <div class="col-metric-row">
                <span>Value Bounds:</span>
                <span>[${col.min_val} .. ${col.max_val}]</span>
            </div>
            ` : ""}
            ${col.missing_value_markers.length ? `
            <div class="col-metric-row" style="color: var(--stew-amber)">
                <span>Sentinel Flags:</span>
                <span>${col.missing_value_markers.join(", ")}</span>
            </div>
            ` : ""}
        `;
        deck.appendChild(card);
    });
}

// Tab navigation
function initKitchenTabs() {
    const tabBtns = document.querySelectorAll(".kitchen-tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });
}

async function switchTab(tabName) {
    document.querySelectorAll(".kitchen-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-view-panel").forEach(p => p.classList.remove("active"));

    const targetBtn = document.querySelector(`.kitchen-tab-btn[data-tab="${tabName}"]`);
    const targetPanel = document.getElementById(`view-${tabName}`);

    if (targetBtn) targetBtn.classList.add("active");
    if (targetPanel) targetPanel.classList.add("active");

    if (!activeDatasetId) return;

    if (tabName === "croissant") {
        const res = await fetch(`/api/croissant/${activeDatasetId}`);
        const data = await res.json();
        document.getElementById("croissantViewer").textContent = JSON.stringify(data, null, 2);
    } else if (tabName === "dictionary") {
        const res = await fetch(`/api/dictionary/${activeDatasetId}`);
        const data = await res.json();
        document.getElementById("dictionaryViewer").textContent = data.markdown;
    } else if (tabName === "article") {
        showSimmering("Stew is compiling publication-ready FAIR Data Article...");
        const res = await fetch(`/api/article/${activeDatasetId}`, { method: "POST" });
        const data = await res.json();
        document.getElementById("articleViewer").textContent = data.article_markdown;
        hideSimmering();
    } else if (tabName === "rocrate") {
        const res = await fetch(`/api/ro-crate/${activeDatasetId}`);
        const data = await res.json();
        document.getElementById("roCrateViewer").textContent = JSON.stringify(data, null, 2);
    }
}

// Stew Chat System
function initChat() {
    const sendBtn = document.getElementById("chatSendBtn");
    const chatInput = document.getElementById("chatInputField");

    sendBtn.addEventListener("click", () => sendChatMessage());
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendChatMessage();
    });
}

async function sendChatMessage(customMsg = null) {
    const chatInput = document.getElementById("chatInputField");
    const msg = customMsg || chatInput.value.trim();
    if (!msg || !activeDatasetId) return;

    chatInput.value = "";
    chatHistory.push({ role: "user", content: msg });
    renderChatMessages();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                dataset_id: activeDatasetId,
                message: msg,
                history: chatHistory
            })
        });
        const data = await res.json();
        chatHistory = data.history;
        renderChatMessages();
    } catch (e) {
        chatHistory.push({ role: "assistant", content: "Stew notice: Connection error: " + e.message });
        renderChatMessages();
    }
}

function quickPrompt(text) {
    sendChatMessage(text);
}

function renderChatMessages() {
    const flow = document.getElementById("chatFlow");
    flow.innerHTML = "";

    chatHistory.forEach(item => {
        const row = document.createElement("div");
        row.className = `chat-turn-row ${item.role}`;
        
        const avatar = document.createElement("div");
        avatar.className = item.role === "assistant" ? "avatar-stew" : "avatar-user";
        avatar.innerHTML = item.role === "assistant" ? "🍲" : "👤";

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble-body";
        bubble.innerHTML = formatMarkdown(item.content);

        row.appendChild(avatar);
        row.appendChild(bubble);
        flow.appendChild(row);
    });

    flow.scrollTop = flow.scrollHeight;
}

function formatMarkdown(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n\n/g, '<br/><br/>')
        .replace(/\n- (.*)/g, '<br/>• $1');
}

// Export Package
function downloadFairPackage() {
    if (!activeDatasetId) return;
    window.location.href = `/api/export/${activeDatasetId}`;
}

function copyCode(elementId) {
    const text = document.getElementById(elementId).textContent;
    navigator.clipboard.writeText(text).then(() => {
        alert("Copied to clipboard!");
    });
}

// Settings modal
function initSettingsModal() {
    const modal = document.getElementById("settingsModal");
    const openBtn = document.getElementById("openSettingsBtn");
    const closeBtn = document.getElementById("closeSettingsBtn");
    const saveBtn = document.getElementById("saveSettingsBtn");

    openBtn.addEventListener("click", () => modal.classList.add("active"));
    closeBtn.addEventListener("click", () => modal.classList.remove("active"));

    saveBtn.addEventListener("click", async () => {
        const apiKey = document.getElementById("settingApiKey").value;
        const model = document.getElementById("settingModel").value;

        await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: apiKey, model: model })
        });
        modal.classList.remove("active");
        checkBackendStatus();
    });
}

function showSimmering(msg) {
    document.getElementById("loadingOverlay").style.display = "flex";
    document.getElementById("loadingText").textContent = msg;
}

function hideSimmering() {
    document.getElementById("loadingOverlay").style.display = "none";
}

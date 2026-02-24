/**
 * The Last Shelter — Frontend Application
 */

let currentProject = null;
let selectedScriptFile = null;
let eventSource = null;
let isGenerating = false;

// =============================================================================
// PROJECT MANAGEMENT
// =============================================================================

function showCreateForm() {
    document.getElementById('createForm').style.display = 'block';
    document.getElementById('titleInput').focus();
    setupScriptUpload();
}

function hideCreateForm() {
    document.getElementById('createForm').style.display = 'none';
    clearScriptFile();
}

function setupScriptUpload() {
    const zone = document.getElementById('scriptUploadZone');
    const input = document.getElementById('scriptFileInput');
    if (!zone || !input) return;

    // Click to browse
    zone.onclick = (e) => {
        if (e.target.closest('.btn-icon')) return;
        input.click();
    };

    // File selected
    input.onchange = () => {
        if (input.files.length > 0) {
            setScriptFile(input.files[0]);
        }
    };

    // Drag and drop
    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add('drag-over'); };
    zone.ondragleave = () => zone.classList.remove('drag-over');
    zone.ondrop = (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            setScriptFile(e.dataTransfer.files[0]);
        }
    };
}

function setScriptFile(file) {
    selectedScriptFile = file;
    document.getElementById('scriptUploadPlaceholder').style.display = 'none';
    document.getElementById('scriptFileInfo').style.display = 'flex';
    document.getElementById('scriptFileName').textContent = file.name;

    // Auto-fill title from filename if empty
    const titleInput = document.getElementById('titleInput');
    if (!titleInput.value.trim()) {
        // Remove extension and clean up filename
        let name = file.name.replace(/\.md$/i, '').replace(/_/g, ' ');
        titleInput.value = name;
    }
}

function clearScriptFile() {
    selectedScriptFile = null;
    const placeholder = document.getElementById('scriptUploadPlaceholder');
    const info = document.getElementById('scriptFileInfo');
    const input = document.getElementById('scriptFileInput');
    if (placeholder) placeholder.style.display = 'flex';
    if (info) info.style.display = 'none';
    if (input) input.value = '';
}

async function createProject() {
    const title = document.getElementById('titleInput').value.trim();
    if (!title) return;

    // Disable button and show loading
    const btn = document.getElementById('btnCreateProject');
    const origText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Creating...';

    try {
        const formData = new FormData();
        formData.append('title', title);
        if (selectedScriptFile) {
            formData.append('script', selectedScriptFile);
        }

        const res = await fetch('/api/project/create', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.project_id) {
            // Add to sidebar
            const card = createProjectCard(data.project_id, title, data.metadata.status, data.metadata.duration || '');
            const list = document.getElementById('projectList');
            list.prepend(card);

            // Hide form, clear inputs
            hideCreateForm();
            document.getElementById('titleInput').value = '';
            clearScriptFile();

            // Load the new project
            await loadProject(data.project_id);
        }
    } catch (err) {
        console.error('Create project error:', err);
        alert('Error creating project: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = origText;
    }
}

function createProjectCard(id, title, status, duration) {
    const div = document.createElement('div');
    div.className = 'project-card';
    div.dataset.projectId = id;
    div.onclick = () => loadProject(id);
    div.innerHTML = `
        <div class="project-card-row">
            <div class="project-title">${escapeHtml(title)}</div>
            <button class="btn-delete-sidebar" onclick="event.stopPropagation(); deleteProject('${id}')" title="Delete">🗑️</button>
        </div>
    `;
    return div;
}

async function loadProject(projectId) {
    // Highlight in sidebar
    document.querySelectorAll('.project-card').forEach(c => c.classList.remove('active'));
    const card = document.querySelector(`[data-project-id="${projectId}"]`);
    if (card) card.classList.add('active');

    // Fetch project data
    const res = await fetch(`/api/project/${projectId}`);
    const data = await res.json();
    currentProject = data;

    // Show project view
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('projectView').style.display = 'block';

    // Populate header
    document.getElementById('projectTitle').textContent = data.metadata.title;
    const durationEl = document.getElementById('projectDuration');
    durationEl.textContent = data.metadata.duration || '';
    durationEl.className = 'badge';
    document.getElementById('projectStatus').textContent = data.metadata.status;
    document.getElementById('projectStatus').className = `badge badge-${data.metadata.status}`;

    // Update steps bar
    updateStepsBar(data.metadata.steps_completed || []);

    // Render Script section
    renderScript(data.script);

    // Render Breakdown if available
    renderBreakdown(data.story);

    // Populate existing sections (for backward compatibility)
    window._currentProject = data.metadata;
    window._currentProjectId = data.metadata.id;
    window._currentNarration = data.narration;
    window._currentElements = data.elements || [];
    renderStory(data.story, data.quality_report);
    renderNarration(data.narration);
    renderVoice(data.narration, data.audio_manifest);
    renderElements(data.elements, data.element_images);
    populateChapterSelect(data.narration);
    loadProductionState();

    // Show/hide sections based on completion
    const steps = data.metadata.steps_completed || [];

    // Script section always visible
    document.getElementById('scriptSection').style.display = 'block';

    // Show script actions if script is loaded
    if (data.script) {
        document.getElementById('btnReuploadScript').style.display = '';
        document.getElementById('btnCollapseScript').style.display = '';
    }

    // Other sections: show based on steps completed
    // Keep old sections visible for backward compatibility (old projects)
    const hasScript = steps.includes('script') || steps.includes('story');
    // Show breakdown section if script is loaded
    const breakdownSection = document.getElementById('breakdownSection');
    if (breakdownSection) breakdownSection.style.display = hasScript ? 'block' : 'none';

    // Other sections: show based on steps
    document.getElementById('voiceSection').style.display = steps.includes('breakdown') ? 'block' : 'none';
    document.getElementById('elementsSection').style.display = steps.includes('breakdown') ? 'block' : 'none';
    document.getElementById('scenePromptsSection').style.display = (steps.includes('elements') || steps.includes('scene_prompts')) ? 'block' : 'none';
    // Show Launch Storyboard button when production section is visible
    const launchBtn = document.getElementById('btnLaunchStoryboard');
    if (launchBtn) launchBtn.style.display = (steps.includes('elements') || steps.includes('scene_prompts')) ? 'inline-flex' : 'none';
    const generateSection = document.getElementById('generateSection');
    if (generateSection) generateSection.style.display = steps.includes('scene_prompts') ? 'block' : 'none';

    // Toggle buttons
    toggleStepButtons(steps);

    // Collapse ALL sections by default on load
    ['scriptContent', 'breakdownContent', 'voiceContent', 'elementsContent', 'narrationContent', 'scenePromptsContent'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    ['btnCollapseScript', 'btnCollapseBreakdown', 'btnCollapseVoice', 'btnCollapseElements', 'btnCollapseNarration', 'btnCollapseScenePrompts'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.textContent = '▼ Expand';
    });
}

function updateStepsBar(completed) {
    const allSteps = ['script', 'breakdown', 'voice', 'elements', 'production'];
    document.querySelectorAll('.step').forEach(el => {
        const step = el.dataset.step;
        el.classList.remove('completed', 'active');
        if (completed.includes(step)) {
            el.classList.add('completed');
        }
    });
    // Mark the next incomplete step as active
    for (const step of allSteps) {
        if (!completed.includes(step)) {
            const el = document.querySelector(`.step[data-step="${step}"]`);
            if (el) el.classList.add('active');
            break;
        }
    }
}

// Step indicator click → scroll to corresponding section
const STEP_TO_SECTION = {
    script: 'scriptSection',
    breakdown: 'breakdownSection',
    voice: 'voiceSection',
    elements: 'elementsSection',
    production: 'scenePromptsSection'
};
document.querySelectorAll('.step[data-step]').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
        const sectionId = STEP_TO_SECTION[el.dataset.step];
        const section = sectionId && document.getElementById(sectionId);
        if (section && section.offsetHeight > 0) {
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

function toggleStepButtons(completed) {
    // Script — handled via renderScript

    // Breakdown
    const btnGenBd = document.getElementById('btnGenerateBreakdown');
    const btnRegenBd = document.getElementById('btnRegenerateBreakdown');
    const btnColBd = document.getElementById('btnCollapseBreakdown');
    if (btnGenBd) btnGenBd.style.display = completed.includes('breakdown') ? 'none' : '';
    if (btnRegenBd) btnRegenBd.style.display = completed.includes('breakdown') ? '' : 'none';
    if (btnColBd) btnColBd.style.display = completed.includes('breakdown') ? '' : 'none';

    // Elements
    const btnGenElem = document.getElementById('btnGenerateElements');
    const btnRegenElem = document.getElementById('btnRegenerateElements');
    const btnColElem = document.getElementById('btnCollapseElements');
    if (btnGenElem) btnGenElem.style.display = completed.includes('elements') ? 'none' : '';
    if (btnRegenElem) btnRegenElem.style.display = completed.includes('elements') ? '' : 'none';
    if (btnColElem) btnColElem.style.display = completed.includes('elements') ? '' : 'none';

    // Chapter Production
    const btnColScene = document.getElementById('btnCollapseScenePrompts');
    if (btnColScene) btnColScene.style.display = completed.includes('scene_prompts') ? '' : 'none';
}

// =============================================================================
// SCRIPT VIEWER
// =============================================================================

function renderScript(scriptData) {
    const container = document.getElementById('scriptContent');
    if (!container) return;

    if (!scriptData || !scriptData.sections || scriptData.sections.length === 0) {
        container.innerHTML = '<p class="text-muted">Upload a script .md file when creating the episode.</p>';
        return;
    }

    let html = '';

    // Summary bar
    const phases = scriptData.sections.filter(s => s.type === 'phase').length;
    const breaks = scriptData.sections.filter(s => s.type === 'jack_break').length;
    const chars = (scriptData.characters || []).map(c => c.name).join(', ');
    const objs = (scriptData.objects || []).map(o => o.name).join(', ');

    html += `<div class="script-summary">`;
    html += `<div class="script-summary-item"><strong>Words:</strong> ${(scriptData.word_count || 0).toLocaleString()}</div>`;
    html += `<div class="script-summary-item"><strong>Duration:</strong> ${escapeHtml(scriptData.total_duration || 'N/A')}</div>`;
    html += `<div class="script-summary-item"><strong>Sections:</strong> ${scriptData.sections.length} (${phases} chapters, ${breaks} breaks)</div>`;
    if (chars) html += `<div class="script-summary-item"><strong>Characters:</strong> ${escapeHtml(chars)}</div>`;
    if (objs) html += `<div class="script-summary-item"><strong>Key Objects:</strong> ${escapeHtml(objs)}</div>`;
    html += `<div class="script-summary-actions"><button class="btn btn-ghost btn-sm" onclick="toggleAllScriptSections()">▼ Expand All</button></div>`;
    html += `</div>`;

    // Render each section
    for (const section of scriptData.sections) {
        const typeClass = `script-section-${section.type}`;
        const typeIcon = {
            'intro': '🎬',
            'phase': '📋',
            'jack_break': '🎙️',
            'outro': '🏁'
        }[section.type] || '📄';

        const numLabel = section.number ? ` ${section.number}` : '';
        const typeLabel = {
            'intro': 'INTRO',
            'phase': `CH${numLabel}`,
            'jack_break': `BREAK${numLabel}`,
            'outro': 'OUTRO'
        }[section.type] || section.type.toUpperCase();

        const tsLabel = section.timestamps
            ? `${section.timestamps.start} — ${section.timestamps.end}`
            : '';
        const durLabel = section.duration || '';

        html += `<div class="script-section ${typeClass} collapsed">`;
        html += `<div class="script-section-header" onclick="this.parentElement.classList.toggle('collapsed')">`;
        html += `<div class="script-section-title">`;
        html += `<span class="script-type-badge">${typeIcon} ${typeLabel}</span>`;
        html += `<span class="script-section-name">${escapeHtml(section.title)}</span>`;
        html += `</div>`;
        html += `<div class="script-section-meta">`;
        if (durLabel) html += `<span class="script-duration">${escapeHtml(durLabel)}</span>`;
        if (tsLabel) html += `<span class="script-timestamp">${escapeHtml(tsLabel)}</span>`;
        html += `<span class="script-chevron">▼</span>`;
        html += `</div>`;
        html += `</div>`;

        // Section body
        html += `<div class="script-section-body">`;

        // Day markers
        if (section.day_markers && section.day_markers.length > 0) {
            html += `<div class="script-day-markers">`;
            for (const dm of section.day_markers) {
                html += `<span class="script-day-badge">📅 ${escapeHtml(dm)}</span>`;
            }
            html += `</div>`;
        }

        // Clean text with speaker styling
        const cleanText = section.clean_text || '';
        const paragraphs = cleanText.split('\n\n').filter(p => p.trim());
        for (const para of paragraphs) {
            const speakerClass = section.speaker === 'jack' ? 'script-speaker-jack' : 'script-speaker-narrator';
            html += `<p class="${speakerClass}">${escapeHtml(para.trim())}</p>`;
        }

        html += `</div>`; // .script-section-body
        html += `</div>`; // .script-section
    }

    container.innerHTML = html;
}

function toggleAllScriptSections() {
    const sections = document.querySelectorAll('.script-section');
    const btn = document.querySelector('.script-summary-actions button');
    const allCollapsed = Array.from(sections).every(s => s.classList.contains('collapsed'));
    sections.forEach(s => {
        if (allCollapsed) {
            s.classList.remove('collapsed');
        } else {
            s.classList.add('collapsed');
        }
    });
    if (btn) btn.textContent = allCollapsed ? '▲ Collapse All' : '▼ Expand All';
}

// =============================================================================
// BREAKDOWN (Step 2) — AI metadata extraction
// =============================================================================

async function generateBreakdown() {
    const projectId = currentProject?.metadata?.id;
    if (!projectId) return;
    if (isGenerating) return;

    isGenerating = true;

    const btn = document.getElementById('btnGenerateBreakdown');
    const regenBtn = document.getElementById('btnRegenerateBreakdown');
    const activeBtn = [btn, regenBtn].find(b => b && b.style.display !== 'none');
    let origHtml = '';
    if (activeBtn) {
        origHtml = activeBtn.innerHTML;
        activeBtn.disabled = true;
        activeBtn.innerHTML = '<span class="spinner"></span> Analyzing...';
    }

    showConsole();
    clearConsole();
    logConsole('🧩 Starting script breakdown...', 'info');

    // Start SSE progress stream
    startProgressStream(projectId, () => {
        isGenerating = false;
        if (activeBtn) {
            activeBtn.disabled = false;
            activeBtn.innerHTML = origHtml;
        }
        // Reload project to refresh all data
        loadProject(projectId);
    });

    try {
        const res = await fetch(`/api/project/${projectId}/generate-breakdown`, { method: 'POST' });
        const data = await res.json();
        if (data.error) {
            logConsole(`❌ Error: ${data.error}`, 'error');
            isGenerating = false;
            if (activeBtn) {
                activeBtn.disabled = false;
                activeBtn.innerHTML = origHtml;
            }
        }
    } catch (err) {
        logConsole(`❌ Network error: ${err.message}`, 'error');
        isGenerating = false;
        if (activeBtn) {
            activeBtn.disabled = false;
            activeBtn.innerHTML = origHtml;
        }
    }
}

function renderBreakdown(storyData) {
    const container = document.getElementById('breakdownContent');
    if (!container) return;

    if (!storyData || !storyData.character) {
        container.innerHTML = '<p class="text-muted">Click "Analyze Script" to extract characters, location, conflicts, and narrative arcs from the script.</p>';
        return;
    }

    const char = storyData.character || {};
    const loc = storyData.location || {};
    const con = storyData.construction || {};
    const tl = storyData.timeline || {};
    const arcs = storyData.narrative_arcs || [];
    const conflicts = storyData.conflicts || [];
    const companion = char.companion || {};

    let html = '';

    // --- Compact summary bar (4 key items only) ---
    html += '<div class="bd-summary-bar">';
    html += `<div class="bd-summary-item"><span class="bd-sum-icon">👤</span><strong>${escapeHtml(char.name || '?')}</strong></div>`;
    html += `<div class="bd-summary-item"><span class="bd-sum-icon">📍</span>${escapeHtml(loc.name || '?')}</div>`;
    html += `<div class="bd-summary-item"><span class="bd-sum-icon">🏗️</span>${escapeHtml(con.type || '?')}</div>`;
    html += `<div class="bd-summary-item"><span class="bd-sum-icon">⏱️</span>${tl.total_days || '?'} days</div>`;
    html += '</div>';

    // --- Narrative Timeline ---
    if (arcs.length > 0) {
        const chapterColors = [
            '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
            '#8b5cf6', '#ec4899', '#14b8a6', '#6366f1', '#f43f5e',
            '#84cc16', '#0ea5e9'
        ];

        html += '<div class="bd-timeline-section">';
        html += '<div class="bd-timeline-header">📊 NARRATIVE TIMELINE</div>';
        html += '<div class="bd-timeline-wrapper"><canvas id="tensionCurveCanvas"></canvas><div id="bdTooltip" class="bd-tooltip"></div></div>';

        // Chapter blocks row
        html += '<div class="bd-chapters-row">';
        for (let i = 0; i < arcs.length; i++) {
            const arc = arcs[i];
            const color = chapterColors[i % chapterColors.length];
            const pct = arc.percentage || Math.round(100 / arcs.length);
            html += `<div class="bd-chapter-block" style="flex: ${Math.max(pct, 3)}; background: ${color};" title="${escapeHtml(arc.phase || '')}\nTension: ${arc.tension || 0}/100\n${escapeHtml(arc.description || '')}">
                <span class="bd-ch-num">${i + 1}</span>
                <span class="bd-ch-pct">${pct}%</span>
            </div>`;
        }
        html += '</div>';

        // Legend row under chapter blocks
        html += '<div class="bd-chapters-legend">';
        for (let i = 0; i < arcs.length; i++) {
            const arc = arcs[i];
            const color = chapterColors[i % chapterColors.length];
            html += `<div class="bd-legend-item"><span class="bd-legend-dot" style="background:${color}"></span><span class="bd-legend-label">${escapeHtml(arc.phase || '?')}</span></div>`;
        }
        html += '</div>';

        html += '</div>';
    }

    container.innerHTML = html;

    // --- Draw tension curve on canvas (handles hidden sections) ---
    if (arcs.length > 0) {
        const totalDays = parseInt(tl.total_days) || 90;
        const drawData = { arcs, conflicts, totalDays };
        const tryDraw = () => {
            const wrapper = document.querySelector('.bd-timeline-wrapper');
            if (wrapper && wrapper.clientWidth > 0) {
                drawTensionCurve(drawData);
            }
        };
        requestAnimationFrame(tryDraw);
        const wrapper = document.querySelector('.bd-timeline-wrapper');
        if (wrapper) {
            const ro = new ResizeObserver(() => {
                if (wrapper.clientWidth > 0) {
                    drawTensionCurve(drawData);
                    ro.disconnect();
                }
            });
            ro.observe(wrapper);
        }
    }
}

function drawTensionCurve({ arcs, conflicts, totalDays }) {
    const canvas = document.getElementById('tensionCurveCanvas');
    if (!canvas) return;

    const wrapper = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const W = wrapper.clientWidth;
    const H = 160;

    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const padL = 24, padR = 24, padT = 22, padB = 15;
    const gW = W - padL - padR;
    const gH = H - padT - padB;

    const chColors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#8b5cf6', '#ec4899', '#14b8a6', '#6366f1', '#f43f5e', '#84cc16', '#0ea5e9'];

    // Build points positioned by cumulative percentage
    const pts = [];
    let cumPct = 0, peakIdx = 0, peakVal = 0;

    for (let i = 0; i < arcs.length; i++) {
        const pct = arcs[i].percentage || Math.round(100 / arcs.length);
        const midPct = cumPct + pct / 2;
        const x = padL + (midPct / 100) * gW;
        const t = arcs[i].tension || 0;
        const y = padT + gH - (t / 100) * gH;
        pts.push({ x, y, t, name: arcs[i].phase || '', desc: arcs[i].description || '', dayRange: arcs[i].day_range || '' });
        if (t > peakVal) { peakVal = t; peakIdx = i; }
        cumPct += pct;
    }

    if (pts.length < 2) return;

    // Catmull-Rom to Bezier
    const segs = [];
    for (let i = 0; i < pts.length - 1; i++) {
        const p0 = pts[Math.max(i - 1, 0)];
        const p1 = pts[i];
        const p2 = pts[i + 1];
        const p3 = pts[Math.min(i + 2, pts.length - 1)];
        segs.push({
            cp1: { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 },
            cp2: { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 },
            end: { x: p2.x, y: p2.y }
        });
    }

    // -- Gradient fill under curve --
    ctx.beginPath();
    ctx.moveTo(pts[0].x, H - padB);
    ctx.lineTo(pts[0].x, pts[0].y);
    for (const s of segs) ctx.bezierCurveTo(s.cp1.x, s.cp1.y, s.cp2.x, s.cp2.y, s.end.x, s.end.y);
    ctx.lineTo(pts[pts.length - 1].x, H - padB);
    ctx.closePath();
    const gr = ctx.createLinearGradient(0, padT, 0, H - padB);
    gr.addColorStop(0, 'rgba(239,68,68,0.30)');
    gr.addColorStop(0.4, 'rgba(234,179,8,0.15)');
    gr.addColorStop(1, 'rgba(34,197,94,0.03)');
    ctx.fillStyle = gr;
    ctx.fill();

    // -- Curve line with glow --
    ctx.save();
    ctx.shadowColor = 'rgba(255,255,255,0.3)';
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (const s of segs) ctx.bezierCurveTo(s.cp1.x, s.cp1.y, s.cp2.x, s.cp2.y, s.end.x, s.end.y);
    ctx.strokeStyle = 'rgba(255,255,255,0.9)';
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.stroke();
    ctx.restore();

    // -- Conflict markers (⚡) — diamonds only, details via tooltip --
    if (conflicts && conflicts.length > 0) {
        for (const c of conflicts) {
            if (!c.day) continue;
            const dayPct = (c.day / totalDays) * 100;
            const cx = padL + (dayPct / 100) * gW;
            const cy = _getYOnCurve(cx, pts, segs);
            const sev = c.severity || 5;
            const markerColor = sev >= 7 ? '#ef4444' : sev >= 4 ? '#f59e0b' : '#22c55e';

            // Vertical dashed line from marker to baseline
            ctx.save();
            ctx.setLineDash([3, 3]);
            ctx.strokeStyle = markerColor + '44';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx, H - padB);
            ctx.stroke();
            ctx.restore();

            // Diamond marker
            const ds = 6;
            ctx.save();
            ctx.translate(cx, cy - ds - 3);
            ctx.rotate(Math.PI / 4);
            ctx.fillStyle = markerColor;
            ctx.shadowColor = markerColor;
            ctx.shadowBlur = 5;
            ctx.fillRect(-ds / 2, -ds / 2, ds, ds);
            ctx.restore();
        }
    }

    // -- Colored dots with glow --
    for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        const color = chColors[i % chColors.length];
        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.restore();
        ctx.beginPath();
        ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.5)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    // -- PEAK marker (small triangle, no text to avoid clipping) --
    const pk = pts[peakIdx];
    ctx.save();
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.moveTo(pk.x, pk.y - 14);
    ctx.lineTo(pk.x - 4, pk.y - 8);
    ctx.lineTo(pk.x + 4, pk.y - 8);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    // -- Interactive tooltip on hover --
    canvas.onmousemove = (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        const tooltip = document.getElementById('bdTooltip');
        if (!tooltip) return;

        let found = false;
        for (let i = 0; i < pts.length; i++) {
            const dx = mx - pts[i].x;
            const dy = my - pts[i].y;
            if (Math.sqrt(dx * dx + dy * dy) < 14) {
                const p = pts[i];
                tooltip.innerHTML = `<strong>${escapeHtml(p.name)}</strong><br>Tension: ${p.t}/100<br>${escapeHtml(p.dayRange)}`;
                tooltip.style.left = Math.min(p.x + 12, W - 180) + 'px';
                tooltip.style.top = (p.y - 10) + 'px';
                tooltip.classList.add('visible');
                canvas.style.cursor = 'pointer';
                found = true;
                break;
            }
        }
        if (!found && conflicts) {
            for (const c of conflicts) {
                if (!c.day) continue;
                const dayPct = (c.day / totalDays) * 100;
                const cfx = padL + (dayPct / 100) * gW;
                const cfy = _getYOnCurve(cfx, pts, segs);
                const dx = mx - cfx;
                const dy = my - (cfy - 11);
                if (Math.sqrt(dx * dx + dy * dy) < 16) {
                    tooltip.innerHTML = `<strong>⚡ ${escapeHtml(c.title || '?')}</strong><br>${escapeHtml(c.description || '')}<br>Day ${c.day} · Severity ${c.severity || '?'}/10`;
                    tooltip.style.left = Math.min(cfx + 12, W - 200) + 'px';
                    tooltip.style.top = (cfy - 30) + 'px';
                    tooltip.classList.add('visible');
                    canvas.style.cursor = 'pointer';
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            tooltip.classList.remove('visible');
            canvas.style.cursor = 'default';
        }
    };
    canvas.onmouseleave = () => {
        const tooltip = document.getElementById('bdTooltip');
        if (tooltip) tooltip.classList.remove('visible');
        canvas.style.cursor = 'default';
    };
}

// Helper: approximate Y on curve at a given X
function _getYOnCurve(targetX, pts, segs) {
    for (let i = 0; i < segs.length; i++) {
        const startX = pts[i].x;
        const endX = segs[i].end.x;
        if (targetX >= startX && targetX <= endX) {
            const t = (targetX - startX) / (endX - startX);
            const p0y = pts[i].y;
            const p1y = segs[i].cp1.y;
            const p2y = segs[i].cp2.y;
            const p3y = segs[i].end.y;
            const mt = 1 - t;
            return mt * mt * mt * p0y + 3 * mt * mt * t * p1y + 3 * mt * t * t * p2y + t * t * t * p3y;
        }
    }
    if (targetX <= pts[0].x) return pts[0].y;
    return pts[pts.length - 1].y;
}


async function reuploadScript(input) {
    if (!input.files.length) return;
    const file = input.files[0];
    const projectId = currentProject?.metadata?.id;
    if (!projectId) return;

    const formData = new FormData();
    formData.append('script', file);

    try {
        const res = await fetch(`/api/project/${projectId}/upload-script`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.status === 'ok') {
            // Reload project to refresh everything
            await loadProject(projectId);
        } else {
            alert('Error uploading script: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Reupload error:', err);
        alert('Error uploading script: ' + err.message);
    }
    input.value = '';
}

function deleteProject(projectId) {
    // Find the project title for the modal
    const card = document.querySelector(`[data-project-id="${projectId}"]`);
    const title = card ? card.querySelector('.project-title')?.textContent || 'this episode' : 'this episode';

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'delete-overlay';
    overlay.innerHTML = `
        <div class="delete-modal">
            <div class="delete-modal-icon">🗑️</div>
            <h3>Delete Episode?</h3>
            <p>"${escapeHtml(title)}" will be permanently deleted. This cannot be undone.</p>
            <div class="delete-modal-actions">
                <button class="btn btn-ghost" id="deleteCancelBtn">Cancel</button>
                <button class="btn btn-danger" id="deleteConfirmBtn">Delete</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // Close on cancel or overlay click
    overlay.querySelector('#deleteCancelBtn').onclick = () => overlay.remove();
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    // Confirm delete
    overlay.querySelector('#deleteConfirmBtn').onclick = async () => {
        overlay.querySelector('#deleteConfirmBtn').innerHTML = '<span class="spinner"></span> Deleting...';
        overlay.querySelector('#deleteConfirmBtn').disabled = true;

        await fetch(`/api/project/${projectId}`, { method: 'DELETE' });

        // Remove from sidebar
        if (card) card.remove();

        // Reset view if deleted project is current
        if (currentProject && currentProject.metadata.id === projectId) {
            currentProject = null;
            document.getElementById('projectView').style.display = 'none';
            document.getElementById('emptyState').style.display = '';
        }

        overlay.remove();
    };
}

// =============================================================================
// GENERATION STEPS
// =============================================================================

async function generateStep(step) {
    if (!currentProject) {
        console.error('generateStep called but currentProject is null');
        return;
    }
    if (isGenerating) {
        console.warn('Generation already in progress');
        return;
    }

    isGenerating = true;
    const id = currentProject.metadata.id;

    const endpoints = {
        'story': 'generate-story',
        'narration': 'generate-narration',
        'elements': 'generate-elements',
    };

    const btnMap = {
        'story': ['btnGenerateStory', 'btnRegenerateStory'],
        'narration': ['btnGenerateNarration', 'btnRegenerateNarration'],
        'elements': ['btnGenerateElements', 'btnRegenerateElements'],
    };

    const endpoint = endpoints[step];
    if (!endpoint) { isGenerating = false; return; }

    // Disable all step buttons and show loading on the active one
    const btns = btnMap[step] || [];
    const activeBtn = btns.map(id => document.getElementById(id)).find(b => b && b.style.display !== 'none');
    let origHtml = '';
    if (activeBtn) {
        origHtml = activeBtn.innerHTML;
        activeBtn.disabled = true;
        activeBtn.innerHTML = '<span class="spinner"></span> Generating...';
    }

    // Show console
    showConsole();
    clearConsole();
    logConsole(`🚀 Starting ${step} generation...`, 'info');

    // Start SSE listener
    startProgressStream(id, () => {
        // On complete/error callback — re-enable button
        isGenerating = false;
        if (activeBtn) {
            activeBtn.disabled = false;
            activeBtn.innerHTML = origHtml;
        }
    });

    // Trigger generation
    try {
        const res = await fetch(`/api/project/${id}/${endpoint}`, { method: 'POST' });
        const data = await res.json();
        if (data.error) {
            logConsole(`❌ Error: ${data.error}`, 'error');
            isGenerating = false;
            if (activeBtn) {
                activeBtn.disabled = false;
                activeBtn.innerHTML = origHtml;
            }
        }
    } catch (err) {
        logConsole(`❌ Network error: ${err.message}`, 'error');
        isGenerating = false;
        if (activeBtn) {
            activeBtn.disabled = false;
            activeBtn.innerHTML = origHtml;
        }
    }
}
function startProgressStream(projectId, onDone) {
    // Close existing stream
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(`/api/project/${projectId}/progress`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        logConsole(data.message, data.type);

        // On completion, refresh project data
        if (data.type === 'complete') {
            eventSource.close();
            eventSource = null;
            if (onDone) onDone();
            setTimeout(() => loadProject(projectId), 500);
        }

        if (data.type === 'error') {
            eventSource.close();
            eventSource = null;
            if (onDone) onDone();
        }
    };

    eventSource.onerror = () => {
        logConsole('⚠️ Connection lost. Check server.', 'error');
        eventSource.close();
        eventSource = null;
        if (onDone) onDone();
    };
}

// =============================================================================
// RENDER FUNCTIONS
// =============================================================================

const EPISODE_TYPE_LABELS = {
    'build': '🏗️ Build Before Deadline',
    'rescue': '🤝 Rescue & Rebuild',
    'restore': '🏚️ Restore the Forgotten',
    'survive': '❄️ Survive or Freeze',
    'full_build': '🪵 Start to Finish',
    'critical_system': '⚙️ Critical System',
    'underground': '🕳️ Underground Build',
    'cabin_life': '🏠 Cabin Life',
};

function renderStory(story, qualityReport) {
    const el = document.getElementById('storyContent');
    if (!el) return; // storyContent may not exist if replaced by breakdownContent
    if (!story) {
        el.innerHTML = '<p class="text-muted">Click "Generate" to create the story.</p>';
        return;
    }

    const char = story.character || {};
    const companion = char.companion || {};
    const loc = story.location || {};
    const construction = story.construction || {};
    const timeline = story.timeline || {};
    const conflicts = story.conflicts || [];
    const synopsis = story.synopsis || '';
    const episodeType = story.episode_type || '';

    // Quality gate score (real, programmatic)
    const qr = qualityReport || {};
    const qPassed = qr.passed_count || 0;
    const qTotal = qr.total_checks || 10;
    const qPercent = qTotal > 0 ? Math.round((qPassed / qTotal) * 100) : 0;
    let qColor = '#ea4a5a';
    if (qPercent >= 80) qColor = '#34d058';
    else if (qPercent >= 60) qColor = '#f5a623';

    // Arc colors — vivid
    const arcColors = ['#6366f1', '#f97316', '#eab308', '#ef4444', '#10b981', '#ec4899', '#3b82f6', '#8b5cf6', '#06b6d4'];

    // Build narrative timeline from narrative_arcs (array format)
    const arcs = story.narrative_arcs || [];
    const arcArray = Array.isArray(arcs) ? arcs : Object.entries(arcs).map(([k, v]) => ({
        phase: k,
        percentage: typeof v === 'object' ? (v.percentage || 0) : v,
        description: typeof v === 'object' ? (v.description || '') : ''
    }));

    // Helper: get display title for a phase
    // Uses the phase name directly (now scene-based: "Arrival and Setup", "Cabin Construction", etc.)
    function phaseTitle(arc) {
        return arc.phase || arc.description?.split(/[.,;:—]/)[0]?.trim() || '?';
    }

    // Timeline bar — thick segments with scene names inside
    let timelineHTML = '';
    let phaseCardsHTML = '';
    if (arcArray.length > 0) {
        const segments = arcArray.map((arc, i) => {
            const color = arcColors[i % arcColors.length];
            const pct = arc.percentage || 0;
            const title = phaseTitle(arc);
            const label = pct >= 8
                ? `<span class="tl-seg-name">${escapeHtml(title)}</span><span class="tl-seg-pct">${pct}%</span>`
                : `<span class="tl-seg-pct">${pct}%</span>`;
            return `<div class="tl-segment" style="width: ${pct}%; background: ${color};" title="${escapeHtml(title)}: ${pct}%">${label}</div>`;
        }).join('');

        // ─── Build SVG tension curve (paths only) + HTML overlay dots ───
        const svgW = 1000;
        const svgH = 100;
        const padTop = 6;
        const padBot = 5;
        const curveH = svgH - padTop - padBot;

        // Calculate position for each phase point
        let cumPct = 0;
        const points = arcArray.map((arc, i) => {
            const pct = arc.percentage || 0;
            const tension = arc.tension != null ? arc.tension : 50;
            const xPct = cumPct + pct / 2;       // horizontal center (% of width)
            const xSvg = (xPct / 100) * svgW;    // SVG coordinate
            cumPct += pct;
            const ySvg = svgH - padBot - (tension / 100) * curveH;
            const bottomPct = (tension / 100) * 100;  // CSS bottom %
            return { xPct, xSvg, ySvg, bottomPct, tension, pct, color: arcColors[i % arcColors.length], phase: phaseTitle(arc) };
        });

        const peakIdx = points.reduce((best, p, i) => p.tension > points[best].tension ? i : best, 0);

        // SVG: bezier curve anchored to baseline at edges
        const baseline = svgH - padBot;
        const allPts = [
            { xSvg: 0, ySvg: baseline },
            ...points,
            { xSvg: svgW, ySvg: baseline }
        ];

        let pathD = `M ${allPts[0].xSvg} ${allPts[0].ySvg}`;
        for (let i = 1; i < allPts.length; i++) {
            const prev = allPts[i - 1];
            const curr = allPts[i];
            const cpx = (prev.xSvg + curr.xSvg) / 2;
            pathD += ` C ${cpx} ${prev.ySvg}, ${cpx} ${curr.ySvg}, ${curr.xSvg} ${curr.ySvg}`;
        }
        const fillD = pathD + ` L ${svgW} ${baseline} L 0 ${baseline} Z`;

        const gradStops = points.map((p, i) => {
            let cumP = 0;
            for (let j = 0; j <= i; j++) cumP += (arcArray[j].percentage || 0);
            const offset = cumP - (arcArray[i].percentage || 0) / 2;
            return `<stop offset="${offset}%" stop-color="${p.color}" stop-opacity="0.4"/>`;
        }).join('');

        // SVG only draws paths (no text/circles — those distort with preserveAspectRatio=none)
        const tensionSVG = `
            <svg class="tension-curve-svg" viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="none">
                <defs>
                    <linearGradient id="tensionGrad" x1="0%" y1="0%" x2="100%" y2="0%">${gradStops}</linearGradient>
                </defs>
                <path d="${fillD}" fill="url(#tensionGrad)" />
                <path d="${pathD}" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;

        // HTML overlay dots — positioned with CSS percentages so they don't stretch
        const dotsOverlay = points.map((p, i) => {
            const isPeak = i === peakIdx;
            return `
                <div class="tc-dot${isPeak ? ' tc-dot--peak' : ''}" style="left: ${p.xPct}%; bottom: ${p.bottomPct}%;">
                    <span class="tc-dot-circle" style="background: ${p.color}; box-shadow: 0 0 8px ${p.color}80;"></span>
                    ${isPeak ? '<span class="tc-peak-label">▲ PEAK</span>' : ''}
                    <div class="tc-tooltip">
                        <div class="tc-tooltip-title" style="color: ${p.color};">${escapeHtml(p.phase)}</div>
                        <div class="tc-tooltip-row">Tension <strong>${p.tension}/100</strong></div>
                        <div class="tc-tooltip-row">Duration <strong>${p.pct}%</strong> of episode</div>
                    </div>
                </div>
            `;
        }).join('');

        timelineHTML = `
            <div class="story-panel">
                <div class="panel-label">📊 NARRATIVE TIMELINE</div>
                <div class="tension-curve-container">
                    ${tensionSVG}
                    <div class="tc-dots-overlay">${dotsOverlay}</div>
                </div>
                <div class="tl-bar">${segments}</div>
            </div>
        `;

        // Phase detail cards at bottom — scene-focused
        phaseCardsHTML = `
            <div class="phase-cards">
                ${arcArray.map((arc, i) => {
            const color = arcColors[i % arcColors.length];
            const title = phaseTitle(arc);
            return `
                    <div class="phase-card" style="border-left-color: ${color};">
                        <div class="phase-card-title" style="color: ${color};">${escapeHtml(title)}</div>
                        <div class="phase-card-desc">${escapeHtml(arc.description || '')}</div>
                    </div>`;
        }).join('')}
            </div>
        `;
    }

    // Duration card
    const totalDays = timeline.total_days || '?';
    const durationLabel = totalDays > 60 ? `${Math.round(totalDays / 30)} months` : `${totalDays} days`;

    // Challenges = conflicts as chips
    const challengeChips = conflicts.map(c => {
        return `<span class="challenge-chip">${escapeHtml(c.title || c.description || '')}</span>`;
    }).join('');

    // Episode type label
    const typeLabel = EPISODE_TYPE_LABELS[episodeType] || episodeType || '';

    el.innerHTML = `
        <div class="story-display-v2">

            <!-- Synopsis + Episode Type + Quality Score -->
            <div class="story-panel synopsis-panel">
                <div class="synopsis-header">
                    <div class="panel-label">📖 ABOUT THIS VIDEO</div>
                    <div style="display:flex; gap:0.5rem; align-items:center;">
                        ${qualityReport ? `
                        <span class="quality-gate-badge" style="--qg-color: ${qColor};">
                            <span class="quality-gate-bar"><span class="quality-gate-fill" style="width:${qPercent}%; background:${qColor};"></span></span>
                            ${qPassed}/${qTotal} checks
                        </span>` : ''}
                        ${typeLabel ? `<span class="episode-type-pill">${escapeHtml(typeLabel)}</span>` : ''}
                    </div>
                </div>
                <div class="synopsis-text">"${escapeHtml(synopsis || `${char.name || 'Someone'} faces the wilderness with nothing but determination and ${timeline.total_days || 'limited'} days to build shelter before the cold arrives.`)}"</div>
            </div>

            <!-- Narrative Timeline -->
            ${timelineHTML}

            <!-- Duration + Challenges + Protagonist + Outcome row -->
            <div class="info-row">
                <div class="story-panel info-card duration-card">
                    <div class="panel-label">⏱️ DURATION</div>
                    <div class="duration-big">${durationLabel}</div>
                    ${timeline.deadline_reason ? `<div class="duration-sub">${escapeHtml(timeline.deadline_reason)}</div>` : ''}
                </div>
                <div class="story-panel info-card challenges-card">
                    <div class="panel-label">⚔️ SURVIVAL CHALLENGES</div>
                    <div class="challenge-chips">${challengeChips || '<span class="text-muted">No challenges yet</span>'}</div>
                </div>
                <div class="story-panel info-card protagonist-card">
                    <div class="panel-label">👤 PROTAGONIST</div>
                    <div class="protagonist-name">${escapeHtml(char.name || 'Unknown')}</div>
                    <div class="protagonist-details">${char.age || '?'} · ${escapeHtml(char.profession || '')}</div>
                    <div class="protagonist-details">${escapeHtml(char.origin || '')}</div>
                    ${companion.name ? `<div class="protagonist-companion">🐕 ${escapeHtml(companion.name)} — ${escapeHtml(companion.breed || companion.type || '')}</div>` : ''}
                </div>
                ${(() => {
            const outcome = story.outcome || {};
            const oType = outcome.type || 'success';
            const oIcon = oType === 'success' ? '✅' : oType === 'partial' ? '⚠️' : '💀';
            const oLabel = oType === 'success' ? 'SUCCESS' : oType === 'partial' ? 'PARTIAL' : 'FAILURE';
            const oClass = 'outcome-' + oType;
            return `
                    <div class="story-panel info-card outcome-card ${oClass}">
                        <div class="panel-label">🎬 OUTCOME</div>
                        <div class="outcome-icon">${oIcon}</div>
                        <div class="outcome-label">${oLabel}</div>
                        ${outcome.visual ? `<div class="outcome-visual">${escapeHtml(outcome.visual)}</div>` : ''}
                        ${outcome.one_liner ? `<div class="outcome-oneliner">"${escapeHtml(outcome.one_liner)}"</div>` : ''}
                    </div>`;
        })()}
            </div>

            <!-- Phase Detail Cards -->
            ${phaseCardsHTML}
        </div>
    `;
}
function renderNarration(narration) {
    const el = document.getElementById('narrationContent');
    if (!el) return;
    if (!narration) {
        el.innerHTML = '<p class="text-muted">Presenter intro, phase narrations, and breaks will appear here.</p>';
        return;
    }

    const intro = narration.intro || {};
    const phases = narration.phases || [];
    const breaks = narration.breaks || [];
    const close = narration.close || {};
    const summary = narration.summary || {};

    // Phase colors for narration
    const phaseColors = ['#f97316', '#ef4444', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

    // Helper: format narration text with paragraph breaks
    function formatNarrationText(text) {
        if (!text) return '';
        return text.split(/\n\n+/).map(p => `<p>${escapeHtml(p.trim())}</p>`).join('');
    }

    // Helper: clean phase name by removing 'Phase X:' prefix
    function cleanPhaseName(name) {
        return (name || '').replace(/^Phase\s*\d+\s*[:.]\s*/i, '').trim() || name;
    }

    let breakNumber = 0;
    const chapterColorMap = {};  // maps base chapter name → color

    el.innerHTML = `
        <div class="narration-display">
            <!-- Summary stats -->
            <div class="narration-stats">
                <span class="narration-stat">${summary.total_words || 0} total words</span>
                <span class="narration-stat">📝 ${summary.voiceover_words || summary.total_words || 0} voiceover</span>
                <span class="narration-stat">📢 ${summary.breaks_words || 0} presenter</span>
                <span class="narration-stat">${summary.phases_count || 0} phases</span>
                <span class="narration-stat">${summary.breaks_count || 0} breaks</span>
            </div>

            <!-- Presenter Intro -->
            ${intro.text ? `
                <div class="narration-block narration-intro">
                    <div class="narration-block-header narration-collapsible" onclick="toggleNarrationBlock(this)">
                        <span class="narration-toggle">▼</span>
                        <span class="narration-block-icon">📢</span>
                        <span>Presenter Intro</span>
                        <span class="narration-wc">${intro.text.split(/\s+/).length} words</span>
                        <span class="narration-duration">${intro.duration_seconds || 0}s</span>
                    </div>
                    <div class="narration-block-body">
                        <div class="narration-block-text">${formatNarrationText(intro.text)}</div>
                    </div>
                </div>
            ` : ''}

            <!-- Phase Narrations -->
            ${phases.map((p, i) => {
        const breakAfter = breaks.find(b => b.after_phase_index === i);
        // Assign color based on base chapter name (strip Part N suffix) so same chapter = same color
        const baseName = cleanPhaseName(p.phase_name).replace(/\s*\(Part\s*\d+\)\s*$/i, '').trim();
        if (!chapterColorMap[baseName]) {
            chapterColorMap[baseName] = phaseColors[Object.keys(chapterColorMap).length % phaseColors.length];
        }
        const color = chapterColorMap[baseName];
        const isFailed = !p.narration || p.narration.includes('failed to generate');
        return `
                    <div class="narration-block narration-phase ${isFailed ? 'narration-failed' : ''}" style="border-left-color: ${color};">
                        <div class="narration-block-header narration-collapsible" onclick="toggleNarrationBlock(this)">
                            <span class="narration-toggle">▼</span>
                            <span class="narration-phase-dot" style="background: ${color};"></span>
                            <span>${escapeHtml(cleanPhaseName(p.phase_name) || `Phase ${i + 1}`)}</span>
                            <span class="narration-wc">${p.word_count || 0} words</span>
                            ${p.scene_range ? `<span class="narration-scenes">Scenes ${p.scene_range[0]}-${p.scene_range[1]}</span>` : ''}
                        </div>
                        <div class="narration-block-body">
                            ${isFailed
                ? `<div class="narration-block-text narration-failed-text">⚠️ This phase failed to generate after retries (Gemini returned truncated JSON). Click "Regenerate" to retry the full narration.</div>`
                : `<div class="narration-block-text">${formatNarrationText(p.narration)}</div>`
            }
                        </div>
                    </div>
                    ${breakAfter ? (() => {
                breakNumber++;
                return `
                        <div class="narration-block narration-break">
                            <div class="narration-block-header narration-collapsible" onclick="toggleNarrationBlock(this)">
                                <span class="narration-toggle">▼</span>
                                <span class="narration-block-icon">📢</span>
                                <span>Presenter Break #${breakNumber}</span>
                                ${breakAfter.after_chapter ? `<span class="narration-break-label">after ${escapeHtml(breakAfter.after_chapter)}</span>` : ''}
                                <span class="narration-duration">${breakAfter.duration_seconds || 0}s</span>
                            </div>
                            <div class="narration-block-body">
                                <div class="narration-block-text narration-break-text">"${escapeHtml(breakAfter.text || '')}"</div>
                            </div>
                        </div>
                    `})() : ''}
                `;
    }).join('')}

            <!-- Presenter Close -->
            ${close.text ? `
                <div class="narration-block narration-close">
                    <div class="narration-block-header narration-collapsible" onclick="toggleNarrationBlock(this)">
                        <span class="narration-toggle">▼</span>
                        <span class="narration-block-icon">📢</span>
                        <span>Presenter Outro</span>
                        <span class="narration-wc">${close.text.split(/\s+/).length} words</span>
                        <span class="narration-duration">${close.duration_seconds || 0}s</span>
                    </div>
                    <div class="narration-block-body">
                        <div class="narration-block-text">${formatNarrationText(close.text)}</div>
                        ${close.teaser ? `<div class="narration-teaser">${escapeHtml(close.teaser)}</div>` : ''}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// Toggle narration block collapse/expand
function toggleNarrationBlock(header) {
    const block = header.closest('.narration-block');
    const body = block.querySelector('.narration-block-body');
    const toggle = header.querySelector('.narration-toggle');
    if (block.classList.contains('collapsed')) {
        block.classList.remove('collapsed');
        body.style.maxHeight = body.scrollHeight + 'px';
        toggle.textContent = '▼';
        setTimeout(() => { body.style.maxHeight = 'none'; }, 300);
    } else {
        body.style.maxHeight = body.scrollHeight + 'px';
        requestAnimationFrame(() => {
            body.style.maxHeight = '0';
        });
        block.classList.add('collapsed');
        toggle.textContent = '▶';
    }
}

// Download narration as ordered TXT script
function downloadNarrationScript() {
    if (!window._currentProject) return;
    const projectId = window._currentProject.id;
    if (!projectId) return;
    const title = window._currentProject.title || 'narration-script';
    const slug = title.replace(/[^a-zA-Z0-9\s]/g, '').trim().replace(/\s+/g, '-').toLowerCase();
    // Fetch from server, use data URI for guaranteed filename support
    fetch(`/api/project/${encodeURIComponent(projectId)}/download-script`)
        .then(r => r.text())
        .then(text => {
            const dataUri = 'data:text/plain;charset=utf-8,' + encodeURIComponent(text);
            const a = document.createElement('a');
            a.href = dataUri;
            a.download = slug + '.txt';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => document.body.removeChild(a), 500);
        })
        .catch(err => console.error('Download failed:', err));
}

// =============================================================================
// RENDER — Voice (Per-chapter TTS)
// =============================================================================

function renderVoice(narration, audioManifest) {
    const container = document.getElementById('voiceChaptersContainer');
    if (!container) return;
    if (!narration) {
        container.innerHTML = '<p class="text-muted">Generate narration first to see audio chapters.</p>';
        return;
    }

    const intro = narration.intro || {};
    const phases = narration.phases || [];
    const breaks = narration.breaks || [];
    const close = narration.close || {};
    const manifest = audioManifest || {};

    // Build ordered audio segments: chapters + breaks only (intro/close handled by Kling scenes)
    const segments = [];

    // Phases only — no breaks (handled visually in script), no intro/close (Kling scenes)
    phases.forEach((phase, i) => {
        const phaseName = (phase.phase_name || '').replace(/^Phase\s*\d+\s*[:.]?\s*/i, '').trim() || `Chapter ${i + 1}`;
        const chNum = i + 1;
        const safeTitle = phaseName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
        segments.push({
            id: `chapter_${i}`,
            type: 'chapter',
            typeLabel: `CH ${chNum}`,
            typeClass: 'voice-type-chapter',
            title: phaseName,
            text: phase.narration || '',
            words: phase.word_count || (phase.narration || '').split(/\s+/).length,
            segmentType: 'narration',
            downloadName: `ch${String(chNum).padStart(2, '0')}_${safeTitle}.mp3`
        });
    });

    // Format text into paragraphs (reuse)
    function formatText(text) {
        if (!text) return '';
        return text.split(/\n\n+/).map(p => `<p>${escapeHtml(p.trim())}</p>`).join('');
    }

    // Check manifest for existing audio
    function getAudioInfo(segId) {
        return manifest[segId] || null;
    }

    container.innerHTML = segments.map((seg, idx) => {
        const audio = getAudioInfo(seg.id);
        const hasAudio = !!audio;
        const statusClass = hasAudio ? 'done' : 'pending';
        const statusIcon = hasAudio ? '✅' : '⏳';
        const statusText = hasAudio ? `${audio.duration_seconds || '?'}s` : 'Not generated';

        return `
            <div class="voice-chapter-card ${hasAudio ? 'has-audio' : ''}" id="voice-card-${seg.id}">
                <div class="voice-chapter-header" onclick="toggleVoiceChapter('${seg.id}')">
                    <span class="voice-chapter-toggle" id="voice-toggle-${seg.id}">▶</span>
                    <span class="voice-chapter-type ${seg.typeClass}">${seg.typeLabel}</span>
                    <span class="voice-chapter-title">${escapeHtml(seg.title)}</span>
                    <span class="voice-chapter-words">${seg.words}w</span>
                    <span class="voice-chapter-status ${statusClass}" id="voice-status-${seg.id}">${statusIcon} ${statusText}</span>
                    <button class="voice-chapter-btn" id="voice-btn-${seg.id}"
                        onclick="event.stopPropagation(); generateChapterAudio('${seg.id}', '${seg.segmentType}', ${idx})">${hasAudio ? '🔄 Regenerate' : '🎙️ Generate'}</button>
                    <a class="voice-download-btn" id="voice-dl-${seg.id}" style="display:${hasAudio ? 'inline-flex' : 'none'}" 
                        href="/api/project/${currentProject.metadata.id}/audio/${hasAudio ? audio.filename : ''}" download="${seg.downloadName || seg.id + '.mp3'}"
                        onclick="event.stopPropagation()">📥</a>
                </div>
                <div class="voice-chapter-body" id="voice-body-${seg.id}">
                    <div class="voice-chapter-text">${formatText(seg.text)}</div>
                    ${hasAudio ? `
                        <div class="voice-audio-row">
                            <audio controls src="/api/project/${currentProject.metadata.id}/audio/${audio.filename}"></audio>
                            <span class="voice-audio-duration">${audio.duration_seconds || '?'}s</span>
                        </div>
                    ` : ''}
                </div>
            </div>`;
    }).join('');

    // Store segments for later use
    window._voiceSegments = segments;

    // Show Download All button if any audio already exists
    const hasAnyAudio = segments.some(seg => !!(manifest[seg.id]));
    const dlAllBtn = document.getElementById('btnDownloadAllAudio');
    if (dlAllBtn && hasAnyAudio) dlAllBtn.style.display = '';

    // Update total duration label
    setTimeout(() => updateVoiceTotalDuration(), 100);
}

function toggleVoiceChapter(segId) {
    const body = document.getElementById(`voice-body-${segId}`);
    const toggle = document.getElementById(`voice-toggle-${segId}`);
    if (body.classList.contains('expanded')) {
        body.classList.remove('expanded');
        toggle.textContent = '▶';
    } else {
        body.classList.add('expanded');
        toggle.textContent = '▼';
    }
}

async function generateChapterAudio(segId, segmentType, segIdx) {
    if (!currentProject) return;
    const projectId = currentProject.metadata.id;

    // Get TTS settings from the Voice settings bar
    const voiceId = document.getElementById('voiceTtsVoiceId').value.trim();
    const model = document.getElementById('voiceTtsModel').value;
    const speed = parseFloat(document.getElementById('voiceTtsSpeed').value);
    const stability = parseFloat(document.getElementById('voiceTtsStability').value);

    if (!voiceId) {
        alert('Please enter an ElevenLabs Voice ID in the Voice settings.');
        return;
    }

    // Update button state
    const btn = document.getElementById(`voice-btn-${segId}`);
    const status = document.getElementById(`voice-status-${segId}`);
    btn.textContent = '⏳ Generating...';
    btn.classList.add('generating');
    status.textContent = '🔄 Generating...';
    status.className = 'voice-chapter-status generating';

    try {
        const res = await fetch(`/api/project/${projectId}/generate_audio_segment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                segment_id: segId,
                segment_type: segmentType,
                voice_id: voiceId,
                model: model,
                speed: speed,
                stability: stability
            })
        });

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        // Update card
        const card = document.getElementById(`voice-card-${segId}`);
        card.classList.add('has-audio');
        btn.textContent = '🔄 Regenerate';
        btn.classList.remove('generating');
        status.textContent = `✅ ${data.duration_seconds || '?'}s`;
        status.className = 'voice-chapter-status done';

        // Show download button
        const dlBtn = document.getElementById(`voice-dl-${segId}`);
        if (dlBtn) {
            dlBtn.href = `/api/project/${projectId}/audio/${data.filename}`;
            // Use segment's downloadName if available
            const seg = (window._voiceSegments || []).find(s => s.id === segId);
            dlBtn.download = (seg && seg.downloadName) ? seg.downloadName : `${segId}.mp3`;
            dlBtn.style.display = 'inline-flex';
        }

        // Add audio player if body is expanded
        const body = document.getElementById(`voice-body-${segId}`);
        let audioRow = body.querySelector('.voice-audio-row');
        if (!audioRow) {
            audioRow = document.createElement('div');
            audioRow.className = 'voice-audio-row';
            body.appendChild(audioRow);
        }
        audioRow.innerHTML = `
            <audio controls src="/api/project/${projectId}/audio/${data.filename}?t=${Date.now()}"></audio>
            <span class="voice-audio-duration">${data.duration_seconds || '?'}s</span>
        `;

        logConsole(`✅ Audio for "${segId}": ${data.duration_seconds}s`, 'success');
        updateVoiceTotalDuration();
    } catch (err) {
        btn.textContent = '🎙️ Retry';
        btn.classList.remove('generating');
        status.textContent = '❌ Error';
        status.className = 'voice-chapter-status pending';
        logConsole(`❌ Audio generation failed for ${segId}: ${err.message}`, 'error');
    }
}

async function generateAllVoice() {
    if (!window._voiceSegments || window._voiceSegments.length === 0) {
        alert('No audio segments to generate. Make sure narration exists.');
        return;
    }

    const segments = window._voiceSegments;
    logConsole(`🎙️ Starting generation of ${segments.length} audio segments...`, 'info');
    showConsole();

    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        logConsole(`⏳ [${i + 1}/${segments.length}] Generating: ${seg.title}...`, 'batch');
        await generateChapterAudio(seg.id, seg.segmentType, i);
        // Small delay between segments to avoid rate limiting
        await new Promise(r => setTimeout(r, 500));
    }

    logConsole(`✅ All ${segments.length} audio segments processed!`, 'success');

    // Show download all button + total duration
    const dlAllBtn = document.getElementById('btnDownloadAllAudio');
    if (dlAllBtn) dlAllBtn.style.display = '';
    updateVoiceTotalDuration();
}

function updateVoiceTotalDuration() {
    const statusEls = document.querySelectorAll('.voice-chapter-status.done');
    let totalSec = 0;
    statusEls.forEach(el => {
        const match = el.textContent.match(/(\d+\.?\d*)s/);
        if (match) totalSec += parseFloat(match[1]);
    });
    const label = document.getElementById('voiceTotalDuration');
    if (!label) return;
    if (totalSec > 0) {
        const mins = Math.floor(totalSec / 60);
        const secs = Math.round(totalSec % 60);
        label.textContent = `⏱️ ${mins}:${secs.toString().padStart(2, '0')}`;
        label.style.display = '';
    } else {
        label.style.display = 'none';
    }
}

async function downloadAllAudio() {
    if (!currentProject) return;
    const projectId = currentProject.metadata.id;
    logConsole('📦 Downloading all audio as ZIP...', 'info');

    try {
        const res = await fetch(`/api/project/${projectId}/audio_zip`);
        if (!res.ok) throw new Error('No audio files to download');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentProject.metadata.title || projectId}_audio.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        logConsole('✅ Audio ZIP downloaded!', 'success');
    } catch (err) {
        logConsole(`❌ Download failed: ${err.message}`, 'error');
    }
}

// =============================================================================
// RENDER — Elements
// =============================================================================

function renderElements(elements, elementImages) {
    const el = document.getElementById('elementsContent');
    if (!el) return;
    if (!elements || elements.length === 0) {
        el.innerHTML = '<p class="text-muted">Characters, objects, and environment reference images will appear here.</p>';
        return;
    }

    const categoryIcons = { character: '🧑', vehicle: '🚗', object: '🔧', environment: '🌲' };
    const categoryColors = { character: '#8b5cf6', vehicle: '#ef4444', object: '#f59e0b', environment: '#10b981' };

    const cards = elements.map((elem, i) => {
        const elemId = elem.element_id || elem.id || `element_${i + 1}`;
        const category = elem.category || 'unknown';
        const icon = categoryIcons[category] || '📦';
        const color = categoryColors[category] || 'var(--text-muted)';
        const imgFilename = elem.image_filename;
        const imgUrl = imgFilename
            ? `/api/project/${window._currentProjectId}/element/${imgFilename}?t=${Date.now()}`
            : null;

        const safeLabel = (elem.label || '').replace(/'/g, "\\'");
        const imageBlock = imgUrl
            ? `<div class="element-img-container">
                   <img src="${escapeHtml(imgUrl)}" alt="${escapeHtml(elem.label || '')}"
                        class="element-img" onclick="openLightbox('${escapeHtml(imgUrl)}', '${safeLabel}')" />
               </div>`
            : `<div class="element-img-container element-img-placeholder">
                   <span>No image</span>
               </div>`;

        return `
            <div class="element-card" id="element-card-${escapeHtml(elemId)}">
                <div class="element-badge" style="color: ${color}; background: ${color}1a; border-color: ${color}40;">
                    ${icon} ${escapeHtml(category.toUpperCase())}
                </div>
                ${imageBlock}
                <div class="element-info">
                    <div class="element-label">${escapeHtml(elem.label || `Element ${i + 1}`)}</div>
                    <div class="element-desc">${escapeHtml(elem.description || '')}</div>
                </div>
                <div class="element-actions">
                    <button class="btn btn-ghost btn-sm" onclick="regenerateElement('${escapeHtml(elemId)}')"
                            id="btnRegenElement-${escapeHtml(elemId)}">↻ Regenerate</button>
                    <button class="btn btn-ghost btn-sm" onclick="openElementEditModal('${escapeHtml(elemId)}', '${imgUrl ? escapeHtml(imgUrl) : ''}')"
                            id="btnEditElement-${escapeHtml(elemId)}">✏️ Edit</button>
                    <label class="btn btn-ghost btn-sm element-upload-btn">
                        📎 Upload
                        <input type="file" accept="image/*" style="display:none"
                               onchange="uploadElementImage('${escapeHtml(elemId)}', this)" />
                    </label>
                </div>
            </div>
        `;
    }).join('');

    el.innerHTML = `<div class="elements-grid">${cards}</div>`;
}


async function regenerateElement(elementId) {
    const projectId = window._currentProjectId;
    if (!projectId) return;

    const btn = document.getElementById(`btnRegenElement-${elementId}`);
    const card = document.getElementById(`element-card-${elementId}`);
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Generating...'; }

    try {
        const resp = await fetch(`/api/project/${projectId}/regenerate-element/${elementId}`, {
            method: 'POST'
        });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.error || 'Regeneration failed');

        // Reload the image in the card
        const img = card?.querySelector('.element-img');
        if (img && data.element?.image_filename) {
            const newUrl = `/api/project/${projectId}/element/${data.element.image_filename}?t=${Date.now()}`;
            img.src = newUrl;
            const safeLabel = (data.element.label || '').replace(/'/g, "\\'");
            img.setAttribute('onclick', `openLightbox('${newUrl}', '${safeLabel}')`);
        } else {
            // Reload full page data if no img element found
            loadProject(projectId);
        }
    } catch (err) {
        console.error('Regenerate element failed:', err);
        alert(`Error: ${err.message}`);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '↻ Regenerate'; }
    }
}


async function uploadElementImage(elementId, inputEl) {
    const projectId = window._currentProjectId;
    if (!projectId || !inputEl.files.length) return;

    const file = inputEl.files[0];
    const formData = new FormData();
    formData.append('file', file);

    const card = document.getElementById(`element-card-${elementId}`);

    try {
        const resp = await fetch(`/api/project/${projectId}/upload-element/${elementId}`, {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.error || 'Upload failed');

        // Update the image in the card
        const imgContainer = card?.querySelector('.element-img-container');
        if (imgContainer && data.filename) {
            const imgUrl = `/api/project/${projectId}/element/${data.filename}?t=${Date.now()}`;
            imgContainer.innerHTML = `<img src="${escapeHtml(imgUrl)}" alt="" class="element-img"
                onclick="openLightbox('${escapeHtml(imgUrl)}', '')" />`;
            imgContainer.classList.remove('element-img-placeholder');
        }
    } catch (err) {
        console.error('Upload element image failed:', err);
        alert(`Error: ${err.message}`);
    }

    // Reset file input
    inputEl.value = '';
}

function openElementEditModal(elementId, currentImgUrl) {
    document.getElementById('editElementId').value = elementId;
    const preview = document.getElementById('editElementPreview');
    if (currentImgUrl) {
        preview.src = currentImgUrl;
        preview.style.display = 'block';
    } else {
        preview.src = '';
        preview.style.display = 'none';
    }
    document.getElementById('editElementFeedback').value = '';
    document.getElementById('editElementOverlay').style.display = 'flex';
}

function closeEditElementModal() {
    document.getElementById('editElementOverlay').style.display = 'none';
    document.getElementById('editElementId').value = '';
    document.getElementById('editElementFeedback').value = '';
}

async function submitElementEdit() {
    const elementId = document.getElementById('editElementId').value;
    const feedback = document.getElementById('editElementFeedback').value.trim();
    const projectId = window._currentProjectId;

    if (!elementId || !projectId) return;
    if (!feedback) {
        alert("Please provide instructions for the AI.");
        return;
    }

    const btn = document.getElementById('btnSubmitElementEdit');
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳ Generating...';

    // Also update the button on the card
    const cardBtn = document.getElementById(`btnEditElement-${elementId}`);
    if (cardBtn) {
        cardBtn.disabled = true;
        cardBtn.textContent = '⏳...';
    }

    try {
        const resp = await fetch(`/api/project/${projectId}/regenerate-element/${elementId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback: feedback })
        });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.error || 'Edit failed');

        closeEditElementModal();

        // Reload the image in the card
        const card = document.getElementById(`element-card-${elementId}`);
        const img = card?.querySelector('.element-img');
        if (img && data.element?.image_filename) {
            const newUrl = `/api/project/${projectId}/element/${data.element.image_filename}?t=${Date.now()}`;
            img.src = newUrl;
            const safeLabel = (data.element.label || '').replace(/'/g, "\\'");
            img.setAttribute('onclick', `openLightbox('${newUrl}', '${safeLabel}')`);

            // Re-bind the edit button with the new image URL
            if (cardBtn) {
                cardBtn.setAttribute('onclick', `openElementEditModal('${elementId}', '${newUrl}')`);
            }
        } else {
            // Reload full page data
            loadProject(projectId);
        }
    } catch (err) {
        console.error('Edit element failed:', err);
        alert(`Error: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
        if (cardBtn) {
            cardBtn.disabled = false;
            cardBtn.textContent = '✏️ Edit';
        }
    }
}



// =============================================================================
// RENDER — Storyboard
// =============================================================================

function renderStoryboard(scenePromptsData, elements) {
    const el = document.getElementById('scenePromptsContent');
    if (!scenePromptsData || !scenePromptsData.scenes || scenePromptsData.scenes.length === 0) {
        el.innerHTML = '<p class="text-muted">Launch the storyboard to generate scene prompts and Frame A images.</p>';
        return;
    }

    const scenes = scenePromptsData.scenes;
    const totalScenes = scenes.length;
    const totalDuration = scenes.reduce((sum, s) => sum + (s.duration || 8), 0);
    const mins = Math.floor(totalDuration / 60);
    const secs = totalDuration % 60;
    const projectId = window._currentProjectId;
    const elemList = elements || window._currentElements || [];

    // Build element lookup by @Element reference
    const elemLookup = {};
    elemList.forEach((elem, i) => {
        const id = elem.element_id || elem.id || `element_${i + 1}`;
        elemLookup[`@Element${i + 1}`] = { ...elem, _idx: i, _id: id };
    });

    const sceneCards = scenes.map((scene, i) => {
        const num = scene.number || (i + 1);
        const typeIcon = scene.type === 'narrator_break' ? '🎙️' :
            scene.type === 'narrator_intro' ? '🎬' :
                scene.type === 'narrator_outro' ? '🏁' : '🎥';
        const typeLabel = scene.type || 'narration';
        const duration = scene.duration || 8;
        const phase = scene.phase || '';

        // Frame A image
        const frameFile = scene.frame_a_filename;
        const frameUrl = frameFile
            ? `/api/project/${projectId}/frame/${frameFile}?t=${Date.now()}`
            : null;

        const frameBlock = frameUrl
            ? `<div class="sb-frame-container">
                   <img src="${escapeHtml(frameUrl)}" alt="Scene ${num} Frame A"
                        class="sb-frame-img" id="sb-frame-img-${num}"
                        onclick="openLightbox('${escapeHtml(frameUrl)}', 'Scene ${num} — Frame A')" />
               </div>`
            : `<div class="sb-frame-container sb-frame-placeholder">
                   <span>⏳ No Frame A</span>
               </div>`;

        // Elements used in this scene
        const usedRefs = scene.elements_used || [];
        const elementBadges = usedRefs.map(ref => {
            const elem = elemLookup[ref];
            if (!elem) return '';
            const thumbFile = elem.image_filename;
            const thumbUrl = thumbFile
                ? `/api/project/${projectId}/element/${thumbFile}?t=1`
                : null;
            const thumb = thumbUrl
                ? `<img src="${escapeHtml(thumbUrl)}" class="sb-elem-thumb" />`
                : `<span class="sb-elem-thumb sb-elem-thumb-empty">?</span>`;
            return `<div class="sb-elem-badge" title="${escapeHtml(elem.label || ref)}">
                        ${thumb}
                        <span class="sb-elem-name">${escapeHtml(elem.label || ref)}</span>
                    </div>`;
        }).filter(Boolean).join('');

        // Narration text
        const narText = scene.narration_text || '';
        const narPreview = narText.length > 150
            ? narText.substring(0, 150) + '...'
            : narText;

        return `
            <div class="sb-card" id="sb-card-${num}">
                <div class="sb-card-left">
                    ${frameBlock}
                    <div class="sb-frame-actions">
                        <button class="btn btn-ghost btn-xs" onclick="regenerateFrameA(${num})"
                                id="sb-regen-btn-${num}">↻ Regenerate</button>
                        <label class="btn btn-ghost btn-xs sb-upload-btn">
                            📎 Upload
                            <input type="file" accept="image/*" style="display:none"
                                   onchange="uploadFrameA(${num}, this)" />
                        </label>
                    </div>
                </div>
                <div class="sb-card-right">
                    <div class="sb-card-header">
                        <span class="sb-scene-num">${typeIcon} Scene ${num}</span>
                        <span class="sb-scene-type">${escapeHtml(typeLabel)}</span>
                        <span class="sb-scene-duration">${duration}s</span>
                        ${phase ? `<span class="sb-scene-phase">${escapeHtml(phase)}</span>` : ''}
                    </div>
                    ${narPreview ? `<div class="sb-narration">"${escapeHtml(narPreview)}"</div>` : ''}
                    <div class="sb-prompt-section">
                        <div class="sb-prompt-label">🎥 Video Prompt</div>
                        <div class="sb-prompt-text">${escapeHtml(scene.video_prompt || '—')}</div>
                    </div>
                    ${elementBadges ? `
                        <div class="sb-elements-row">
                            <span class="sb-elements-label">Elements:</span>
                            ${elementBadges}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');

    el.innerHTML = `
        <div class="sb-summary">
            <span class="sb-summary-stat">📋 <strong>${totalScenes}</strong> scenes</span>
            <span class="sb-summary-stat">⏱️ <strong>${mins}m ${secs}s</strong> total</span>
        </div>
        <div class="sb-grid">
            ${sceneCards}
        </div>
    `;
}


async function regenerateFrameA(sceneNumber) {
    const projectId = window._currentProjectId;
    if (!projectId) return;

    const btn = document.getElementById(`sb-regen-btn-${sceneNumber}`);
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Generating...'; }

    try {
        const resp = await fetch(`/api/project/${projectId}/regenerate-frame/${sceneNumber}`, {
            method: 'POST'
        });
        const data = await resp.json();
        if (data.status === 'ok' && data.scene && data.scene.frame_a_filename) {
            const img = document.getElementById(`sb-frame-img-${sceneNumber}`);
            if (img) {
                img.src = `/api/project/${projectId}/frame/${data.scene.frame_a_filename}?t=${Date.now()}`;
            } else {
                loadProject(projectId);
            }
        } else {
            alert('Frame A regeneration failed: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Regenerate Frame A failed:', err);
        alert('Error regenerating Frame A');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '↻ Regenerate'; }
    }
}


async function uploadFrameA(sceneNumber, inputEl) {
    const file = inputEl.files[0];
    if (!file) return;

    const projectId = window._currentProjectId;
    if (!projectId) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch(`/api/project/${projectId}/upload-frame/${sceneNumber}`, {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (data.status === 'uploaded' && data.filename) {
            const img = document.getElementById(`sb-frame-img-${sceneNumber}`);
            if (img) {
                img.src = `/api/project/${projectId}/frame/${data.filename}?t=${Date.now()}`;
            } else {
                loadProject(projectId);
            }
        }
    } catch (err) {
        console.error('Upload Frame A failed:', err);
        alert('Error uploading Frame A image');
    }
    inputEl.value = '';
}

function showConsole() {
    document.getElementById('console').style.display = '';
}

function toggleConsole() {
    const console = document.getElementById('console');
    console.style.display = console.style.display === 'none' ? '' : 'none';
}

function clearConsole() {
    document.getElementById('consoleBody').innerHTML = '';
}
function toggleCollapse(contentId, btn) {
    const el = document.getElementById(contentId);
    if (!el) return;
    const isCollapsed = el.style.display === 'none';
    if (isCollapsed) {
        el.style.display = '';
        btn.textContent = '▲ Collapse';
    } else {
        el.style.display = 'none';
        btn.textContent = '▼ Expand';
    }
}

function logConsole(message, type = 'info') {
    const body = document.getElementById('consoleBody');
    const line = document.createElement('div');
    line.className = `console-line ${type}`;
    line.textContent = `${new Date().toLocaleTimeString()} │ ${message}`;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
}


// =============================================================================
// CHAPTER PRODUCTION
// =============================================================================

function populateChapterSelect(narration) {
    const sel = document.getElementById('chapterSelect');
    if (!sel) return;
    sel.innerHTML = '';

    if (!narration || !narration.phases) {
        sel.innerHTML = '<option value="0">No narration available</option>';
        return;
    }

    // Group phases by chapter
    const chapters = {};
    narration.phases.forEach(p => {
        const ch = p.chapter || p.phase_name || 'Unknown';
        if (!chapters[ch]) chapters[ch] = [];
        chapters[ch].push(p);
    });

    Object.keys(chapters).forEach((name, i) => {
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = `Chapter ${i + 1}: ${name}`;
        sel.appendChild(opt);
    });
}

async function loadProductionState() {
    const projectId = window._currentProjectId;
    if (!projectId) return;

    const chapterIdx = document.getElementById('chapterSelect')?.value || 0;

    try {
        const res = await fetch(`/api/project/${projectId}/storyboard/${chapterIdx}`);
        if (res.ok) {
            const data = await res.json();
            if (data.storyboard) {
                renderProductionStoryboard(data);
                document.getElementById('storyboardContainer').style.display = '';
                document.getElementById('btnGenerateProduction').style.display = '';
            }
            if (data.validation) {
                renderValidation(data.validation);
            }
        }
    } catch (e) { /* No storyboard yet — that's fine */ }

    // Check for production results
    try {
        const res = await fetch(`/api/project/${projectId}/production/${chapterIdx}/prompts.json`);
        if (res.ok) {
            const prompts = await res.json();
            renderProductionResults(prompts, parseInt(chapterIdx));
        }
    } catch (e) { /* No production yet */ }
}

async function analyzeChapter() {
    const projectId = window._currentProjectId;
    if (!projectId) return;

    const chapterIdx = parseInt(document.getElementById('chapterSelect').value);
    const btn = document.getElementById('btnAnalyzeChapter');
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';

    // Reset UI
    document.getElementById('storyboardContainer').style.display = 'none';
    document.getElementById('validationResults').style.display = 'none';
    document.getElementById('productionResults').style.display = 'none';
    document.getElementById('btnGenerateProduction').style.display = 'none';

    showConsole();
    clearConsole();
    logConsole(`🔍 Analyzing Chapter ${chapterIdx + 1}...`, 'info');

    // Start SSE
    startProgressStream(projectId, async () => {
        btn.disabled = false;
        btn.innerHTML = origHtml;

        // Load the generated storyboard
        try {
            const res = await fetch(`/api/project/${projectId}/storyboard/${chapterIdx}`);
            if (res.ok) {
                const data = await res.json();
                renderProductionStoryboard(data);
                document.getElementById('storyboardContainer').style.display = '';
                document.getElementById('btnGenerateProduction').style.display = '';

                if (data.validation) {
                    renderValidation(data.validation);
                }
            }
        } catch (e) {
            logConsole(`❌ Failed to load storyboard: ${e.message}`, 'error');
        }
    });

    // Trigger analysis
    try {
        const res = await fetch(`/api/project/${projectId}/analyze-chapter`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chapter_index: chapterIdx }),
        });
        const data = await res.json();
        if (data.error) {
            logConsole(`❌ ${data.error}`, 'error');
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    } catch (err) {
        logConsole(`❌ Network error: ${err.message}`, 'error');
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

function renderValidation(validation) {
    const el = document.getElementById('validationResults');
    if (!validation) { el.style.display = 'none'; return; }

    const scoreClass = validation.score >= 80 ? 'val-good' :
        validation.score >= 50 ? 'val-warn' : 'val-bad';

    const errorItems = (validation.errors || []).map(e => `
        <div class="val-item val-error">
            <span class="val-icon">❌</span>
            <div>
                <strong>${escapeHtml(e.message)}</strong>
                ${e.details ? `<div class="val-details">${Array.isArray(e.details) ? e.details.map(d => escapeHtml(d)).join('<br>') : escapeHtml(String(e.details))}</div>` : ''}
            </div>
        </div>
    `).join('');

    const warnItems = (validation.warnings || []).map(w => `
        <div class="val-item val-warning">
            <span class="val-icon">⚠️</span>
            <div>
                <strong>${escapeHtml(w.message)}</strong>
                ${w.details ? `<div class="val-details">${escapeHtml(String(w.details))}</div>` : ''}
            </div>
        </div>
    `).join('');

    el.innerHTML = `
        <div class="val-header ${scoreClass}">
            <span class="val-score">${validation.score}/100</span>
            <span class="val-summary">${escapeHtml(validation.summary)}</span>
        </div>
        ${errorItems}${warnItems}
    `;
    el.style.display = '';
}

function renderProductionStoryboard(data) {
    const container = document.getElementById('storyboardContainer');
    const storyboard = data.storyboard || [];

    // Store full data for editing
    window._currentStoryboard = JSON.parse(JSON.stringify(data));

    if (storyboard.length === 0) {
        container.innerHTML = '<p class="text-muted">No scenes in storyboard.</p>';
        return;
    }

    _renderStoryboardEditor(container, storyboard, data.validation);
}

function _renderStoryboardEditor(container, storyboard, validation) {
    // Index validation issues by scene_num for inline display
    const issuesByScene = {};
    if (validation) {
        const allIssues = [...(validation.errors || []), ...(validation.warnings || [])];
        for (const issue of allIssues) {
            // Extract scene number from message (e.g., "Scene 14: ...")
            const m = issue.message.match(/Scene (\d+)/);
            if (m) {
                const num = parseInt(m[1]);
                if (!issuesByScene[num]) issuesByScene[num] = [];
                issuesByScene[num].push(issue);
            }
        }
    }

    const narrated = storyboard.filter(s => s.type === 'narrated').length;
    const bridges = storyboard.filter(s => s.type === 'bridge').length;
    const ratio = storyboard.length > 0 ? Math.round((bridges / storyboard.length) * 100) : 0;
    const ratioClass = ratio >= 30 ? 'ratio-good' : 'ratio-low';

    // Build rows with add-bridge insertions
    let rowsHtml = '';
    storyboard.forEach((scene, i) => {
        const num = scene.scene_num || (i + 1);
        const type = scene.type || 'narrated';
        const typeClass = type === 'bridge' ? 'sb-type-bridge' :
            type === 'presenter' ? 'sb-type-presenter' :
                type === 'silent' ? 'sb-type-silent' : 'sb-type-narrated';
        const typeIcon = type === 'bridge' ? '🔗' :
            type === 'presenter' ? '🎙️' :
                type === 'silent' ? '🤫' : '🎥';

        const action = scene.action || '—';
        const narExcerpt = scene.narration_excerpt || '';
        const location = scene.location_id || '';
        const elements = (scene.elements || []).join(', ') || '—';
        const tools = (scene.tools || []).join(', ') || '—';
        const progress = scene.progress_delta || '';
        const time = scene.time_of_day || '';
        const bridgeReason = scene.bridge_reason || '';

        // Inline validation issues
        let issuesHtml = '';
        if (issuesByScene[num]) {
            issuesHtml = issuesByScene[num].map(iss => {
                const icon = iss.severity === 'error' ? '🔴' : '🟡';
                return `<div class="sb-inline-issue sb-issue-${iss.severity}">${icon} ${escapeHtml(iss.message)}</div>`;
            }).join('');
        }

        rowsHtml += `
            <tr class="${typeClass}" data-scene-index="${i}">
                <td class="sb-td-num">${num}</td>
                <td><span class="sb-type-badge ${typeClass}">${typeIcon} ${type}</span></td>
                <td class="sb-td-action-edit">
                    <textarea class="sb-action-input" data-index="${i}" rows="2">${escapeHtml(action)}</textarea>
                    ${bridgeReason ? `<div class="sb-bridge-reason">↳ ${escapeHtml(bridgeReason)}</div>` : ''}
                    ${issuesHtml}
                </td>
                <td class="sb-td-narr">${narExcerpt ? `"${escapeHtml(narExcerpt.substring(0, 60))}${narExcerpt.length > 60 ? '...' : ''}"` : '—'}</td>
                <td>${escapeHtml(location)}</td>
                <td class="sb-td-elements">${escapeHtml(elements)}</td>
                <td>${escapeHtml(tools)}</td>
                <td>${escapeHtml(time)}</td>
                <td>${escapeHtml(progress)}</td>
                <td class="sb-td-actions">
                    <button class="btn-icon sb-btn-delete" title="Delete scene" onclick="sbDeleteScene(${i})">🗑️</button>
                </td>
            </tr>
            <tr class="sb-add-row">
                <td colspan="10">
                    <button class="sb-btn-add-bridge" onclick="sbAddBridge(${i})">
                        ➕ Add bridge after scene ${num}
                    </button>
                </td>
            </tr>
        `;
    });

    container.innerHTML = `
        <div class="sb-editor-toolbar">
            <div class="sb-editor-stats">
                <span>📋 ${storyboard.length} scenes</span>
                <span>🎥 ${narrated} narrated</span>
                <span>🔗 ${bridges} bridges</span>
                <span class="sb-ratio ${ratioClass}">📊 ${ratio}% bridges ${ratio >= 30 ? '✅' : '⚠️ (< 30%)'}</span>
                <span>⏱️ ~${storyboard.length * 15}s total</span>
            </div>
            <div class="sb-editor-actions">
                <button class="btn btn-sm btn-warning" onclick="sbSaveChanges()">💾 Save Changes</button>
            </div>
        </div>
        <div class="sb-table-wrapper">
            <table class="sb-table sb-table-editable">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Type</th>
                        <th>Action</th>
                        <th>Narration</th>
                        <th>Location</th>
                        <th>Elements</th>
                        <th>Tools</th>
                        <th>Time</th>
                        <th>Progress</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        </div>
    `;
}

function sbDeleteScene(index) {
    const data = window._currentStoryboard;
    if (!data || !data.storyboard) return;

    const scene = data.storyboard[index];
    const desc = scene.action || `Scene ${index + 1}`;
    if (!confirm(`Delete scene ${index + 1}?\n\n"${desc.substring(0, 80)}"`)) return;

    data.storyboard.splice(index, 1);
    // Renumber
    data.storyboard.forEach((s, i) => { s.scene_num = i + 1; });
    // Update counts
    data.total_narrated = data.storyboard.filter(s => s.type === 'narrated').length;
    data.total_bridges = data.storyboard.filter(s => s.type === 'bridge').length;
    data.total_scenes = data.storyboard.length;
    // Re-render
    const container = document.getElementById('storyboardContainer');
    _renderStoryboardEditor(container, data.storyboard, data.validation);
    logConsole(`🗑️ Deleted scene. Now ${data.total_scenes} scenes.`, 'info');
}

function sbAddBridge(afterIndex) {
    const data = window._currentStoryboard;
    if (!data || !data.storyboard) return;

    const prevScene = data.storyboard[afterIndex];
    const newBridge = {
        scene_num: afterIndex + 2,
        type: 'bridge',
        narration_excerpt: null,
        action: '(describe the bridge action here)',
        location_id: prevScene.location_id || '',
        elements: prevScene.elements ? [...prevScene.elements] : [],
        time_of_day: prevScene.time_of_day || '',
        weather: prevScene.weather || '',
        tools: [],
        progress_delta: null,
        bridge_reason: '(why is this bridge needed?)',
        notes: null
    };

    data.storyboard.splice(afterIndex + 1, 0, newBridge);
    // Renumber
    data.storyboard.forEach((s, i) => { s.scene_num = i + 1; });
    data.total_narrated = data.storyboard.filter(s => s.type === 'narrated').length;
    data.total_bridges = data.storyboard.filter(s => s.type === 'bridge').length;
    data.total_scenes = data.storyboard.length;
    // Re-render
    const container = document.getElementById('storyboardContainer');
    _renderStoryboardEditor(container, data.storyboard, data.validation);
    logConsole(`➕ Added bridge after scene ${afterIndex + 1}. Now ${data.total_scenes} scenes.`, 'info');
}

async function sbSaveChanges() {
    const data = window._currentStoryboard;
    if (!data) return;
    const projectId = window._currentProjectId;
    if (!projectId) return;
    const chapterIdx = parseInt(document.getElementById('chapterSelect').value);

    // Sync edited action texts from textareas
    const textareas = document.querySelectorAll('.sb-action-input');
    textareas.forEach(ta => {
        const idx = parseInt(ta.dataset.index);
        if (data.storyboard[idx]) {
            data.storyboard[idx].action = ta.value;
        }
    });

    // Update counts
    data.total_narrated = data.storyboard.filter(s => s.type === 'narrated').length;
    data.total_bridges = data.storyboard.filter(s => s.type === 'bridge').length;
    data.total_scenes = data.storyboard.length;
    data.estimated_video_duration_seconds = data.storyboard.length * 15;

    try {
        const res = await fetch(`/api/project/${projectId}/storyboard/${chapterIdx}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            logConsole(`💾 Storyboard saved! ${data.total_scenes} scenes (${data.total_narrated} narrated + ${data.total_bridges} bridges)`, 'success');
            // Show generate button
            document.getElementById('btnGenerateProduction').style.display = '';
        } else {
            const err = await res.json();
            logConsole(`❌ Save failed: ${err.error || res.statusText}`, 'error');
        }
    } catch (e) {
        logConsole(`❌ Save failed: ${e.message}`, 'error');
    }
}

async function generateChapterProduction() {
    const projectId = window._currentProjectId;
    if (!projectId) return;

    const chapterIdx = parseInt(document.getElementById('chapterSelect').value);
    const btn = document.getElementById('btnGenerateProduction');
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';

    document.getElementById('productionResults').style.display = 'none';

    showConsole();
    clearConsole();
    logConsole(`🚀 Generating production for Chapter ${chapterIdx + 1}...`, 'info');

    startProgressStream(projectId, async () => {
        btn.disabled = false;
        btn.innerHTML = origHtml;

        // Load production results
        try {
            const res = await fetch(`/api/project/${projectId}/production/${chapterIdx}/prompts.json`);
            if (res.ok) {
                const prompts = await res.json();
                renderProductionResults(prompts, chapterIdx);
            }
        } catch (e) {
            logConsole(`❌ Failed to load results: ${e.message}`, 'error');
        }
    });

    try {
        const res = await fetch(`/api/project/${projectId}/generate-chapter-production`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chapter_index: chapterIdx }),
        });
        const data = await res.json();
        if (data.error) {
            logConsole(`❌ ${data.error}`, 'error');
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    } catch (err) {
        logConsole(`❌ Network error: ${err.message}`, 'error');
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

function renderProductionResults(prompts, chapterIdx) {
    const el = document.getElementById('productionResults');
    const projectId = window._currentProjectId;

    if (!prompts || !prompts.scenes || prompts.scenes.length === 0) {
        el.innerHTML = '<p class="text-muted">No production results available.</p>';
        el.style.display = '';
        return;
    }

    const scenes = prompts.scenes;
    const totalDuration = scenes.reduce((s, sc) => s + (sc.duration || 8), 0);
    const mins = Math.floor(totalDuration / 60);
    const secs = totalDuration % 60;

    const cards = scenes.map((scene, i) => {
        const num = scene.scene_num || scene.number || (i + 1);
        const type = scene.type || 'narrated';
        const typeIcon = type === 'presenter' ? '🎙️' :
            type === 'bridge' ? '🔗' :
                type === 'silent' ? '🤫' : '🎥';
        const typeClass = `sb-type-${type}`;

        // Location image
        const locImg = scene.location_image;
        const locUrl = locImg ? `/api/project/${projectId}/locations/${locImg}?t=${Date.now()}` : null;
        const imgBlock = locUrl
            ? `<div class="prod-img-wrap">
                   <img src="${escapeHtml(locUrl)}" class="prod-loc-img"
                        onclick="openLightbox('${escapeHtml(locUrl)}', 'Scene ${num} Location')" />
               </div>`
            : `<div class="prod-img-wrap prod-img-placeholder"><span>No image</span></div>`;

        const videoPrompt = scene.video_prompt || '—';
        const narration = scene.narration_excerpt || scene.narration_text || '';

        return `
        <div class="prod-card ${typeClass}">
            <div class="prod-card-left">
                ${imgBlock}
            </div>
            <div class="prod-card-right">
                <div class="prod-card-header">
                    <span class="sb-scene-num">${typeIcon} Scene ${num}</span>
                    <span class="sb-type-badge ${typeClass}">${type}</span>
                    <span class="sb-scene-duration">${scene.duration || 8}s</span>
                </div>
                ${narration ? `<div class="prod-narration">"${escapeHtml(narration.substring(0, 150))}"</div>` : ''}
                <div class="prod-prompt">
                    <div class="prod-prompt-label">🎥 Video Prompt</div>
                    <div class="prod-prompt-text">${escapeHtml(videoPrompt)}</div>
                </div>
            </div>
        </div>`;
    }).join('');

    el.innerHTML = `
        <div class="prod-summary">
            <span>✅ <strong>Production Complete</strong></span>
            <span>📋 ${scenes.length} scenes</span>
            <span>⏱️ ${mins}m ${secs}s</span>
        </div>
        <div class="prod-grid">${cards}</div>
    `;
    el.style.display = '';
}

// Listen for chapter selector change
document.addEventListener('DOMContentLoaded', () => {
    const sel = document.getElementById('chapterSelect');
    if (sel) {
        sel.addEventListener('change', () => {
            // Reset UI when switching chapters
            document.getElementById('storyboardContainer').style.display = 'none';
            document.getElementById('validationResults').style.display = 'none';
            document.getElementById('productionResults').style.display = 'none';
            document.getElementById('btnGenerateProduction').style.display = 'none';
            loadProductionState();
        });
    }
});

// =============================================================================
// UTILITIES
// =============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// IMAGE LIGHTBOX
// =============================================================================

function openLightbox(src, caption) {
    // Create overlay if it doesn't exist
    let overlay = document.getElementById('lightboxOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'lightboxOverlay';
        overlay.className = 'lightbox-overlay';
        overlay.innerHTML = `
            <div class="lightbox-content">
                <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
                <img id="lightboxImg" src="" alt="">
                <div class="lightbox-caption" id="lightboxCaption"></div>
            </div>
        `;
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeLightbox();
        });
        document.body.appendChild(overlay);
    }

    document.getElementById('lightboxImg').src = src;
    document.getElementById('lightboxCaption').textContent = caption || '';
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const overlay = document.getElementById('lightboxOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Close lightbox with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLightbox();
});

// =============================================================================
// STEP PILL NAVIGATION
// =============================================================================

const stepToSection = {
    'story': 'storySection',
    'narration': 'narrationSection',
    'voice': 'voiceSection',
    'elements': 'elementsSection',
    'scene_prompts': 'scenePromptsSection',
    'generate': 'generateSection',
};


function goToStep(stepName) {
    const sectionId = stepToSection[stepName];
    if (!sectionId) return;
    const section = document.getElementById(sectionId);
    if (section && section.style.display !== 'none') {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Handle Enter key on title input
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('titleInput');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') createProject();
        });
    }

    // Add click handlers to step pills
    document.querySelectorAll('.step').forEach(el => {
        el.style.cursor = 'pointer';
        el.addEventListener('click', () => {
            const stepName = el.dataset.step;
            if (stepName) goToStep(stepName);
        });
    });

    // Load first project if exists
    const firstCard = document.querySelector('.project-card');
    if (firstCard) {
        loadProject(firstCard.dataset.projectId);
    }

    // Initialize Show Settings upload zone
    initUploadZone();
});


// =============================================================================
// SHOW SETTINGS
// =============================================================================

function openShowSettings() {
    document.getElementById('showSettingsOverlay').style.display = 'flex';
    loadShowSettings();
}

function closeShowSettings() {
    document.getElementById('showSettingsOverlay').style.display = 'none';
}

async function loadShowSettings() {
    try {
        const res = await fetch('/api/show-settings');
        const data = await res.json();
        const p = data.presenter || {};
        document.getElementById('settingsPresenterName').value = p.name || '';
        document.getElementById('settingsVoiceId').value = p.elevenlabs_voice_id || '';
        document.getElementById('settingsVoiceModel').value = p.elevenlabs_model || 'eleven_v3';
        document.getElementById('settingsVoiceStability').value = String(p.elevenlabs_stability ?? 0.5);
        document.getElementById('settingsVoiceSpeed').value = p.elevenlabs_speed || 0.75;
        document.getElementById('speedValue').textContent = p.elevenlabs_speed || 0.75;
        // Show turnaround preview if exists
        if (p.turnaround_image) {
            const preview = document.getElementById('uploadPreview');
            preview.src = `/config/presenter/${p.turnaround_image}`;
            preview.style.display = 'block';
            document.getElementById('uploadPlaceholder').style.display = 'none';
        }
    } catch (err) {
        console.error('Failed to load show settings:', err);
    }
}

async function saveShowSettings() {
    const data = {
        name: document.getElementById('settingsPresenterName').value,
        elevenlabs_voice_id: document.getElementById('settingsVoiceId').value,
        elevenlabs_model: document.getElementById('settingsVoiceModel').value,
        elevenlabs_stability: parseFloat(document.getElementById('settingsVoiceStability').value),
        elevenlabs_speed: parseFloat(document.getElementById('settingsVoiceSpeed').value),
    };
    try {
        const res = await fetch('/api/show-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await res.json();
        if (result.status === 'saved') {
            closeShowSettings();
        }
    } catch (err) {
        console.error('Failed to save show settings:', err);
    }
}

function initUploadZone() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('uploadInput');
    if (!zone || !input) return;

    // Click to browse
    zone.addEventListener('click', () => input.click());

    // File selected
    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) uploadPresenterImage(e.target.files[0]);
    });

    // Drag & drop
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) uploadPresenterImage(e.dataTransfer.files[0]);
    });
}

async function uploadPresenterImage(file) {
    const formData = new FormData();
    formData.append('file', file);
    try {
        const res = await fetch('/api/show-settings/upload', {
            method: 'POST',
            body: formData,
        });
        const result = await res.json();
        if (result.status === 'uploaded') {
            // Show preview
            const preview = document.getElementById('uploadPreview');
            preview.src = `/config/presenter/${result.filename}`;
            preview.style.display = 'block';
            document.getElementById('uploadPlaceholder').style.display = 'none';
        }
    } catch (err) {
        console.error('Failed to upload image:', err);
    }
}

// ─── Storyboard Grid Launch ───
function launchStoryboard() {
    const projectId = window._currentProjectId;
    if (!projectId) { alert('No project selected'); return; }
    window.location.href = `/storyboard/${projectId}`;
}

// Close modals with Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeShowSettings();
    }
});

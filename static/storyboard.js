/**
 * Storyboard Grid — Frontend Logic
 * Loads project data and renders visual storyboard blocks
 */

// ─── State ───
let projectData = null;
let elementsData = [];
let presenterData = null;
let storyboardBlocks = [];

// ─── Init ───
document.addEventListener('DOMContentLoaded', async () => {
    await loadProjectData();
});

async function loadProjectData() {
    try {
        // Load project + show settings in parallel
        const [projectRes, settingsRes] = await Promise.all([
            fetch(`/api/project/${PROJECT_ID}`),
            fetch('/api/show-settings')
        ]);

        if (!projectRes.ok) throw new Error('Failed to load project');
        projectData = await projectRes.json();
        elementsData = projectData.elements || [];

        if (settingsRes.ok) {
            const settings = await settingsRes.json();
            presenterData = settings.presenter || null;
        }

        buildBlocks();
    } catch (err) {
        document.getElementById('sbLoading').innerHTML =
            `<p style="color:var(--danger)">Error: ${err.message}</p>`;
    }
}

function buildBlocks() {
    storyboardBlocks = [];
    const narration = projectData.narration || {};
    const phases = narration.phases || [];

    // Intro block
    storyboardBlocks.push({
        type: 'intro',
        name: 'INTRO',
        index: -1,
        chapterIndex: null,
        scenes: [],
        prompts: [],
        elements: getBlockElements('intro')
    });

    // Chapter blocks from narration phases
    phases.forEach((phase, i) => {
        const phaseName = phase.phase_name || `Chapter ${i + 1}`;
        storyboardBlocks.push({
            type: 'chapter',
            name: `Chapter ${i + 1}: ${phaseName}`,
            index: i,
            chapterIndex: i,
            scenes: [],
            prompts: [],
            elements: getBlockElements(phaseName)
        });

        // Break after each chapter (except last)
        if (i < phases.length - 1) {
            storyboardBlocks.push({
                type: 'break',
                name: `BREAK ${i + 1}`,
                index: i,
                chapterIndex: null,
                scenes: [],
                prompts: [],
                elements: getBlockElements('break')
            });
        }
    });

    // Close block
    storyboardBlocks.push({
        type: 'close',
        name: 'CLOSE',
        index: -1,
        chapterIndex: null,
        scenes: [],
        prompts: [],
        elements: getBlockElements('close')
    });

    loadExistingStoryboards();
}

function getBlockElements(blockName) {
    const blockLower = blockName.toLowerCase();
    const result = [];

    // Always add presenter (Jack) for intro, close, breaks
    if (presenterData && (blockLower === 'intro' || blockLower === 'close' || blockLower.startsWith('break'))) {
        result.push({
            element_id: 'presenter',
            label: presenterData.name || 'Presenter',
            category: 'presenter',
            image_url: `/config/presenter/${presenterData.turnaround_image || 'jack-harlan.png'}`
        });
    }

    // Match project elements
    elementsData.forEach(el => {
        const appearsIn = (el.appears_in || []).map(a => a.toLowerCase());
        if (blockLower === 'intro' || blockLower === 'close' || blockLower.startsWith('break')) {
            // Only show characters that actually appear in this block's scene elements
            if (el.category === 'character') {
                const block = storyboardBlocks.find(b =>
                    (b.type === 'intro' && blockLower === 'intro') ||
                    (b.type === 'close' && blockLower === 'close') ||
                    (b.type === 'break' && blockLower.includes(`break_${b.index + 1}`))
                );
                if (block && block.scenes) {
                    const usedElements = new Set();
                    for (const s of block.scenes) {
                        for (const e of (s.elements || [])) usedElements.add(e);
                        for (const e of (s.prompt?.elements || [])) usedElements.add(e);
                    }
                    if (usedElements.has(el.label) || usedElements.has(el.label.replace(/ \(.*\)/, ''))) {
                        result.push(el);
                    }
                }
            }
        } else {
            // Match by chapter name
            if (appearsIn.some(ch => ch.includes(blockLower) || blockLower.includes(ch))) {
                result.push(el);
            }
        }
    });

    return result;
}

async function loadExistingStoryboards() {
    for (const block of storyboardBlocks) {
        if (block.type === 'intro') {
            try {
                const res = await fetch(`/api/project/${PROJECT_ID}/storyboard/intro`);
                if (res.ok) {
                    const data = await res.json();
                    block.scenes = data.storyboard || [];
                }
            } catch (e) { /* No intro storyboard yet */ }
        } else if (block.chapterIndex !== null) {
            try {
                const res = await fetch(`/api/project/${PROJECT_ID}/storyboard/${block.chapterIndex}`);
                if (res.ok) {
                    const data = await res.json();
                    block.scenes = data.storyboard || [];
                }
            } catch (e) { /* No storyboard yet */ }
        }
    }
    // Re-compute elements now that scenes are loaded (initial call had empty scenes)
    for (const block of storyboardBlocks) {
        const blockName = block.type === 'intro' ? 'intro' :
            block.type === 'close' ? 'close' :
                block.type === 'break' ? `break_${block.index + 1}` :
                    block.name.replace(/^Chapter \d+:\s*/, '');  // extract phase name
        block.elements = getBlockElements(blockName);
    }
    renderAllBlocks();
}

// ─── Render ───
function renderAllBlocks() {
    const container = document.getElementById('sbContainer');
    container.innerHTML = '';

    let totalDuration = 0;

    storyboardBlocks.forEach((block, blockIdx) => {
        const blockEl = createBlockElement(block, blockIdx);
        container.appendChild(blockEl);

        if (block.scenes.length > 0) {
            block.scenes.forEach(s => {
                totalDuration += parseDuration(s.duration);
            });
        }
    });

    const mins = Math.floor(totalDuration / 60);
    const secs = Math.round(totalDuration % 60);
    document.getElementById('totalDuration').textContent =
        totalDuration > 0 ? `${mins}:${String(secs).padStart(2, '0')} total` : '—';
}

function createBlockElement(block, blockIdx) {
    const div = document.createElement('div');
    div.className = 'sb-block';
    div.id = `block-${blockIdx}`;
    div.setAttribute('data-block-type', block.type);

    // Header
    const header = document.createElement('div');
    header.className = 'sb-block-header';

    const info = document.createElement('div');
    info.className = 'sb-block-info';

    // Type badge
    const typeBadge = document.createElement('span');
    const isNarrator = ['break', 'intro', 'outro'].includes(block.type);
    typeBadge.className = `sb-type-badge ${isNarrator ? 'sb-type-narrator' : 'sb-type-chapter'}`;
    typeBadge.textContent = block.type.toUpperCase();
    info.appendChild(typeBadge);

    const name = document.createElement('span');
    name.className = 'sb-block-name';
    name.textContent = block.name;
    info.appendChild(name);

    // Scene count + duration
    if (block.scenes.length > 0) {
        const meta = document.createElement('span');
        meta.className = 'sb-block-meta';
        const dur = block.scenes.reduce((sum, s) => sum + parseDuration(s.duration), 0);
        const mins = Math.floor(dur / 60);
        const secs = Math.round(dur % 60);
        meta.textContent = `${block.scenes.length} scenes · ${mins}:${String(secs).padStart(2, '0')}`;
        info.appendChild(meta);
    }

    // Element thumbnails with names
    const elemBox = document.createElement('div');
    elemBox.className = 'sb-block-elements';
    (block.elements || []).forEach(el => {
        const elemWrap = document.createElement('div');
        elemWrap.className = 'sb-element-item';

        const imgSrc = el.image_url
            ? el.image_url
            : el.image_filename
                ? `/api/project/${PROJECT_ID}/element/${el.image_filename}`
                : null;

        if (imgSrc) {
            const img = document.createElement('img');
            img.className = 'sb-element-thumb';
            img.src = imgSrc;
            img.alt = el.label;
            img.title = el.label;
            img.onclick = (e) => { e.stopPropagation(); openLightbox(imgSrc); };
            elemWrap.appendChild(img);
        }

        const label = document.createElement('span');
        label.className = 'sb-element-label';
        label.textContent = el.label || el.element_id;
        elemWrap.appendChild(label);

        elemBox.appendChild(elemWrap);
    });
    info.appendChild(elemBox);

    header.appendChild(info);

    // Actions
    const actions = document.createElement('div');
    actions.className = 'sb-block-actions';

    // Generate Storyboard button — show for ALL block types when no scenes exist
    if (block.scenes.length === 0) {
        const genBtn = document.createElement('button');
        genBtn.className = 'btn btn-primary btn-sm';
        genBtn.textContent = '🔍 Generate Storyboard';
        genBtn.onclick = () => generateStoryboard(block, blockIdx);
        actions.appendChild(genBtn);
    }

    if (block.scenes.length > 0) {
        // Regenerate scenes button
        const regenBtn = document.createElement('button');
        regenBtn.className = 'btn btn-ghost btn-sm';
        regenBtn.textContent = '🔄 Regenerate Scenes';
        regenBtn.onclick = () => openRegenConfirmModal(block, blockIdx);
        actions.appendChild(regenBtn);

        // Generate/Regenerate prompts button
        const hasPrompts = block.scenes.some(s => s.prompt && s.prompt.prompt_text);
        const promptBtn = document.createElement('button');
        promptBtn.className = 'btn btn-ghost btn-sm';
        promptBtn.textContent = hasPrompts ? '🔄 Regenerate Prompts' : '📝 Generate Prompts';
        promptBtn.onclick = () => generatePrompts(block, blockIdx);
        actions.appendChild(promptBtn);
    }

    header.appendChild(actions);
    div.appendChild(header);

    // Scene cards row
    if (block.scenes.length > 0) {
        const row = createSceneRow(block, blockIdx);
        div.appendChild(row);
    } else {
        const empty = document.createElement('div');
        empty.className = 'sb-empty-block';
        const actionText = 'Click "Generate Storyboard" to analyze this block.';
        empty.innerHTML = `<p>No scenes yet. ${actionText}</p>`;
        div.appendChild(empty);
    }


    return div;
}

function createSceneRow(block, blockIdx) {
    const row = document.createElement('div');
    row.className = 'sb-scene-row';

    block.scenes.forEach((scene, sceneIdx) => {
        if (sceneIdx > 0) {
            const addBtn = document.createElement('button');
            addBtn.className = 'sb-add-btn';
            addBtn.textContent = '+';
            addBtn.title = 'Insert scene with AI';
            addBtn.onclick = () => openAddSceneModal(blockIdx, sceneIdx);
            row.appendChild(addBtn);
        }

        // Vertical column: scene card + connector + prompt card
        const column = document.createElement('div');
        column.className = 'sb-scene-column';

        const card = createSceneCard(scene, sceneIdx, blockIdx);
        column.appendChild(card);

        // Prompt card below (if prompt exists)
        if (scene.prompt && scene.prompt.prompt_text) {
            const connector = document.createElement('div');
            connector.className = 'sb-connector-line';
            column.appendChild(connector);

            const promptCard = createPromptCard(scene.prompt, sceneIdx, blockIdx);
            column.appendChild(promptCard);
        }

        row.appendChild(column);
    });

    const addBtn = document.createElement('button');
    addBtn.className = 'sb-add-btn';
    addBtn.textContent = '+';
    addBtn.title = 'Add scene at end';
    addBtn.onclick = () => openAddSceneModal(blockIdx, block.scenes.length);
    row.appendChild(addBtn);

    return row;
}

function createSceneCard(scene, sceneIdx, blockIdx) {
    const card = document.createElement('div');
    card.className = 'sb-card';

    const sceneType = (scene.type || 'bridge').toLowerCase();
    const sceneNum = scene.scene_number || sceneIdx + 1;

    // ─── Header: SCENE N — [TYPE] — 8s — ✏️ 🗑️ ───
    const header = document.createElement('div');
    header.className = 'sb-card-header';

    const title = document.createElement('span');
    title.className = 'sb-card-scene-title';
    title.textContent = `SCENE ${sceneNum}`;
    header.appendChild(title);

    const typeBadge = document.createElement('span');
    typeBadge.className = `sb-card-type sb-type-${sceneType}`;
    typeBadge.textContent = scene.type || 'Bridge';
    header.appendChild(typeBadge);

    const dur = document.createElement('span');
    dur.className = 'sb-card-duration';
    dur.textContent = scene.duration || '—';
    header.appendChild(dur);

    const spacer = document.createElement('span');
    spacer.className = 'sb-card-header-spacer';
    header.appendChild(spacer);

    const editBtn = document.createElement('button');
    editBtn.className = 'sb-card-icon-btn';
    editBtn.title = 'Edit';
    editBtn.textContent = '✏️';
    editBtn.onclick = (e) => { e.stopPropagation(); openAiEditModal(blockIdx, sceneIdx, 'scene'); };
    header.appendChild(editBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'sb-card-icon-btn';
    deleteBtn.title = 'Delete';
    deleteBtn.textContent = '🗑️';
    deleteBtn.onclick = (e) => { e.stopPropagation(); deleteScene(blockIdx, sceneIdx); };
    header.appendChild(deleteBtn);

    card.appendChild(header);

    // ─── Image 16:9 (clickable → lightbox) ───
    const visual = document.createElement('div');
    visual.className = 'sb-card-visual';

    const sceneImage = scene.scene_image;
    if (sceneImage) {
        const block = storyboardBlocks[blockIdx];
        const blockFolder = block.type === 'intro' ? 'intro' :
            block.type === 'chapter' ? `chapter_${block.index + 1}` :
                block.type === 'break' ? `break_${block.index + 1}` : 'close';
        const imgSrc = `/api/project/${PROJECT_ID}/scene-image/${blockFolder}/${sceneImage}?t=${Date.now()}`;
        const img = document.createElement('img');
        img.className = 'sb-card-img';
        img.src = imgSrc;
        img.alt = `Scene ${sceneNum}`;
        img.onerror = () => { img.replaceWith(createPlaceholder(scene.visual_description)); };
        img.onclick = () => openLightbox(imgSrc);
        visual.appendChild(img);
    } else {
        visual.appendChild(createPlaceholder(scene.visual_description));
    }

    card.appendChild(visual);

    // ─── Body: Plano + Narración ───
    const body = document.createElement('div');
    body.className = 'sb-card-body';

    if (scene.camera || scene.visual_description) {
        const plano = document.createElement('div');
        plano.className = 'sb-card-plano';
        plano.innerHTML = `<span class="plano-label">Descripción visual:</span> ${scene.visual_description || scene.camera || '—'}`;
        body.appendChild(plano);
    }

    if (scene.narration && scene.narration.trim()) {
        const narr = document.createElement('div');
        narr.className = 'sb-card-narration';
        narr.innerHTML = `<span class="narr-label">Narración:</span> <em>${scene.narration}</em>`;
        body.appendChild(narr);
    }

    if (scene.action && scene.action.trim()) {
        const act = document.createElement('div');
        act.className = 'sb-card-action';
        act.innerHTML = `<span class="action-label">Acción:</span> ${scene.action}`;
        body.appendChild(act);
    }

    // ─── Chapter metadata: tools, weather, time ───
    if (scene.tools?.length || scene.weather || scene.time_of_day) {
        const meta = document.createElement('div');
        meta.className = 'sb-card-meta';
        let metaHtml = '';
        if (scene.time_of_day) metaHtml += `<span class="meta-tag">🕐 ${scene.time_of_day}</span>`;
        if (scene.weather) metaHtml += `<span class="meta-tag">🌤️ ${scene.weather}</span>`;
        if (scene.tools?.length) metaHtml += `<span class="meta-tag">🔧 ${scene.tools.join(', ')}</span>`;
        if (scene.progress_delta) metaHtml += `<span class="meta-tag">📊 ${scene.progress_delta}</span>`;
        meta.innerHTML = metaHtml;
        body.appendChild(meta);
    }

    card.appendChild(body);
    return card;
}

function createPlaceholder(visualDesc) {
    const ph = document.createElement('div');
    ph.className = 'sb-card-img-placeholder';
    const text = document.createElement('span');
    text.className = 'ph-text';
    text.textContent = visualDesc || '🎬 Generating...';
    ph.appendChild(text);
    return ph;
}

// ─── Global character color palette (consistent across all cards) ───
const CHAR_COLORS = [
    { bg: 'rgba(167, 139, 250, 0.2)', fg: '#c4b5fd' },  // lavender
    { bg: 'rgba(244, 114, 182, 0.2)', fg: '#f9a8d4' },  // pink
    { bg: 'rgba(129, 140, 248, 0.2)', fg: '#a5b4fc' },  // indigo
    { bg: 'rgba(232, 121, 249, 0.2)', fg: '#e879f9' },  // fuchsia
    { bg: 'rgba(253, 164, 175, 0.2)', fg: '#fda4af' },  // rose
    { bg: 'rgba(196, 181, 253, 0.2)', fg: '#ddd6fe' },  // violet
];
const charColorMap = {};
let charColorIdx = 0;

function createPromptCard(prompt, sceneIdx, blockIdx) {
    const card = document.createElement('div');
    card.className = 'sb-prompt-card' + (prompt.done ? ' sb-prompt-done' : '');

    const block = storyboardBlocks[blockIdx];
    const blockFolder = block.type === 'intro' ? 'intro' :
        block.type === 'chapter' ? `chapter_${block.index + 1}` :
            block.type === 'break' ? `break_${block.index + 1}` : 'close';

    const sceneNum = block.scenes[sceneIdx]?.scene_number || (sceneIdx + 1);

    // ─── Header ───
    const header = document.createElement('div');
    header.className = 'sb-prompt-card-header';

    const title = document.createElement('span');
    title.className = 'sb-prompt-card-title';
    title.textContent = `📹 Video Prompt ${sceneNum}`;
    header.appendChild(title);

    // Action buttons in header
    const headerActions = document.createElement('div');
    headerActions.className = 'sb-prompt-header-actions';

    const editPromptBtn = document.createElement('button');
    editPromptBtn.className = 'sb-card-action-btn';
    editPromptBtn.textContent = '✏️';
    editPromptBtn.title = 'Edit Prompt';
    editPromptBtn.onclick = () => openEditPromptModal(blockIdx, sceneIdx);
    headerActions.appendChild(editPromptBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'sb-card-action-btn delete';
    deleteBtn.textContent = '🗑️';
    deleteBtn.title = 'Delete Prompt';
    deleteBtn.onclick = () => deletePrompt(blockIdx, sceneIdx);
    headerActions.appendChild(deleteBtn);

    header.appendChild(headerActions);
    card.appendChild(header);

    // ─── Character Avatars (from @mentions + narrator when narration present) ───
    const promptText = prompt.prompt_text || '';
    const mentionMatches = promptText.match(/@(\w+)/g) || [];
    const uniqueMentions = [...new Set(mentionMatches.map(m => m.slice(1)))].filter(n => !n.startsWith('Image'));

    // If there's narration in the scene, the presenter is always speaking
    const sceneData = storyboardBlocks[blockIdx]?.scenes?.[sceneIdx] || {};
    const hasNarration = sceneData.narration || promptText.includes('Voice-over narration:');

    const avatarStrip = document.createElement('div');
    avatarStrip.className = 'sb-prompt-avatars';
    const shown = new Set();

    // Helper to add a presenter avatar
    const addPresenter = () => {
        if (!presenterData || shown.has('presenter')) return;
        shown.add('presenter');
        const avatarItem = document.createElement('div');
        avatarItem.className = 'sb-prompt-avatar-item';
        const img = document.createElement('img');
        img.className = 'sb-prompt-avatar-img';
        img.src = `/config/presenter/${presenterData.turnaround_image || 'jack-harlan.png'}`;
        img.alt = presenterData.name;
        avatarItem.appendChild(img);
        const name = document.createElement('span');
        name.className = 'sb-prompt-avatar-name';
        name.textContent = presenterData.name;
        avatarItem.appendChild(name);
        avatarStrip.appendChild(avatarItem);
    };

    // Helper to add an element avatar
    const addElement = (elData) => {
        if (!elData || shown.has(elData.element_id)) return;
        shown.add(elData.element_id);
        const avatarItem = document.createElement('div');
        avatarItem.className = 'sb-prompt-avatar-item';
        if (elData.image_filename) {
            const img = document.createElement('img');
            img.className = 'sb-prompt-avatar-img';
            img.src = `/api/project/${PROJECT_ID}/element/${elData.image_filename}`;
            img.alt = elData.label;
            avatarItem.appendChild(img);
        }
        const name = document.createElement('span');
        name.className = 'sb-prompt-avatar-name';
        name.textContent = elData.label.replace(/ \(.*\)/, '');
        avatarItem.appendChild(name);
        avatarStrip.appendChild(avatarItem);
    };

    // Always show presenter if there's narration — but only for intro blocks
    // In chapters, Jack doesn't appear; only scene elements do
    const blockType = storyboardBlocks[blockIdx]?.type;
    if (hasNarration && blockType === 'intro') addPresenter();

    // Show characters from @mentions in prompt text
    for (const mention of uniqueMentions) {
        const isPresenter = presenterData &&
            (presenterData.name || '').split(' ')[0].toLowerCase() === mention.toLowerCase();
        if (isPresenter) { addPresenter(); continue; }

        const mentionLower = mention.toLowerCase();
        const elData = elementsData.find(e => {
            // Check explicit prompt name
            if (e.prompt_name && e.prompt_name.toLowerCase() === mentionLower) return true;
            const label = e.label || '';

            // Match exact PascalCase labels (e.g. "Erik's Tent" -> "erikstent" matching "@EriksTent")
            const safeLabel = label.replace(/'/g, '').replace(/\s+/g, '').replace(/\(/g, '').replace(/\)/g, '').toLowerCase();
            if (safeLabel === mentionLower) return true;

            // Handle possessives better: strip 's so "Erik's" becomes "Erik"
            const firstName = label.split(' ')[0].replace(/'s/ig, '').replace(/'/g, '').toLowerCase();
            if (firstName === mentionLower) return true;

            if (label.toLowerCase() === mentionLower) return true;
            return false;
        });
        if (elData) addElement(elData);
    }

    if (avatarStrip.children.length > 0) {
        card.appendChild(avatarStrip);
    }
    // ─── Normalize locations (backward compat) ───
    if (!prompt.locations && prompt.location_id) {
        prompt.locations = [{
            id: prompt.location_id,
            image: prompt.location_image,
            prompt: prompt.location_prompt || ''
        }];
    }
    const locations = prompt.locations || [];

    // ─── Location Images ───
    if (locations.length > 0) {
        locations.forEach((loc, locIdx) => {
            if (!loc.image) return;
            const imgLabel = locations.length === 1 ? '@Image' : `@Image${locIdx + 1}`;

            const imgWrapper = document.createElement('div');
            imgWrapper.className = 'sb-prompt-img-wrapper';

            const label = document.createElement('div');
            label.className = 'sb-prompt-img-label';
            label.textContent = `${imgLabel} — ${loc.id.replace(/_/g, ' ')}`;
            imgWrapper.appendChild(label);

            const img = document.createElement('img');
            img.className = 'sb-prompt-location-img';
            img.src = `/api/project/${PROJECT_ID}/scene-image/${blockFolder}/${loc.image}?t=${Date.now()}`;
            img.alt = loc.id || 'Location reference';
            img.onclick = () => openLightbox(img.src);
            imgWrapper.appendChild(img);

            // Image action bar
            const imgActions = document.createElement('div');
            imgActions.className = 'sb-prompt-img-actions';

            const editImgBtn = document.createElement('button');
            editImgBtn.className = 'sb-prompt-btn';
            editImgBtn.textContent = '✏️ Edit Image';
            editImgBtn.onclick = () => openEditLocImageModal(blockIdx, sceneIdx, locIdx);
            imgActions.appendChild(editImgBtn);

            const dlBtn = document.createElement('button');
            dlBtn.className = 'sb-prompt-btn';
            dlBtn.textContent = '📥 Download';
            dlBtn.onclick = () => {
                const a = document.createElement('a');
                a.href = img.src;
                a.download = loc.image;
                a.click();
            };
            imgActions.appendChild(dlBtn);

            imgWrapper.appendChild(imgActions);
            card.appendChild(imgWrapper);
        });
    }

    // ─── Body: Prompt Text ───
    const body = document.createElement('div');
    body.className = 'sb-prompt-card-body';

    // Combine prompt + SFX for display and copy
    const fullPromptText = prompt.sfx
        ? `${prompt.prompt_text || ''}\nSFX: ${prompt.sfx}`
        : (prompt.prompt_text || '');

    const text = document.createElement('div');
    text.className = 'sb-prompt-text';
    // Highlight @mentions and @Image references in prompt text
    const highlightedText = fullPromptText
        .replace(/@(Image\d+)/g, '<span class="sb-prompt-img-ref">@$1</span>')
        .replace(/@(\w+)/g, (match, name) => {
            if (name.startsWith('Image')) return match;
            if (!charColorMap[name]) {
                charColorMap[name] = CHAR_COLORS[charColorIdx % CHAR_COLORS.length];
                charColorIdx++;
            }
            const c = charColorMap[name];
            return `<span style="background:${c.bg};color:${c.fg};padding:1px 4px;border-radius:3px;font-weight:600">@${name}</span>`;
        });
    text.innerHTML = highlightedText;
    text.onclick = () => text.classList.toggle('expanded');
    body.appendChild(text);


    card.appendChild(body);

    // ─── Footer: Copy button ───
    const footer = document.createElement('div');
    footer.className = 'sb-prompt-card-footer';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'sb-prompt-btn';
    copyBtn.textContent = '📋 Copy Prompt';
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(fullPromptText);
        copyBtn.textContent = '✅ Copied';
        setTimeout(() => copyBtn.textContent = '📋 Copy Prompt', 1500);
    };
    footer.appendChild(copyBtn);

    const doneBtn = document.createElement('button');
    doneBtn.className = 'sb-prompt-btn' + (prompt.done ? ' sb-done-active' : '');
    doneBtn.textContent = prompt.done ? '✅ Done' : '☐ Done';
    doneBtn.onclick = async () => {
        prompt.done = !prompt.done;
        card.classList.toggle('sb-prompt-done', prompt.done);
        doneBtn.classList.toggle('sb-done-active', prompt.done);
        doneBtn.textContent = prompt.done ? '✅ Done' : '☐ Done';
        // Persist to storyboard.json
        const block = storyboardBlocks[blockIdx];
        const blockFolder = block.type === 'intro' ? 'intro' :
            block.type === 'chapter' ? `chapter_${block.index + 1}` :
                block.type === 'break' ? `break_${block.index + 1}` : 'close';
        try {
            await fetch(`/api/project/${PROJECT_ID}/storyboard/${blockFolder}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ storyboard: block.scenes })
            });
        } catch (e) { console.error('Failed to save done state', e); }
    };
    footer.appendChild(doneBtn);

    card.appendChild(footer);
    return card;
}

function deletePrompt(blockIdx, sceneIdx) {
    if (!confirm('¿Eliminar este prompt?')) return;
    const block = storyboardBlocks[blockIdx];
    const scene = block.scenes[sceneIdx];
    delete scene.prompt;
    // Save back to server
    const blockFolder = block.type === 'intro' ? 'intro' :
        block.type === 'chapter' ? `chapter_${block.index + 1}` :
            block.type === 'break' ? `break_${block.index + 1}` : 'close';
    fetch(`/api/project/${PROJECT_ID}/update-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            block_folder: blockFolder,
            scene_index: sceneIdx,
            scene_type: scene.type,
            action: scene.action || '',
            narration: scene.narration || '',
            duration: scene.duration || '8s',
            regenerate_image: false
        })
    }).then(() => renderAllBlocks());
}

// ─── Actions ───
function selectScene(blockIdx, sceneIdx) {
    document.querySelectorAll('.sb-card').forEach(c => c.classList.remove('active'));
    const cards = document.querySelectorAll(`#block-${blockIdx} .sb-card`);
    if (cards[sceneIdx]) cards[sceneIdx].classList.add('active');
}

async function generateStoryboard(block, blockIdx) {
    const btn = document.querySelector(`#block-${blockIdx} .btn-primary`);
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Analyzing...'; }

    // Show activity console
    showConsole();
    addConsoleLine('🚀 Starting storyboard generation...', 'info');

    try {
        // Choose endpoint based on block type
        let endpoint, pollEndpoint;
        if (block.type === 'intro') {
            endpoint = `/api/project/${PROJECT_ID}/analyze-intro`;
            pollEndpoint = `/api/project/${PROJECT_ID}/storyboard/intro`;
        } else {
            endpoint = `/api/project/${PROJECT_ID}/analyze-chapter`;
            pollEndpoint = `/api/project/${PROJECT_ID}/storyboard/${block.chapterIndex}`;
        }

        const body = block.type === 'intro'
            ? {}
            : { chapter_index: block.chapterIndex };

        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Analysis failed');
        }

        // Start SSE progress stream
        startProgressStream(blockIdx, pollEndpoint);

    } catch (err) {
        if (btn) { btn.disabled = false; btn.textContent = '🔍 Generate Storyboard'; }
        addConsoleLine(`❌ Error: ${err.message}`, 'error');
    }
}

function startProgressStream(blockIdx, pollEndpoint) {
    const evtSource = new EventSource(`/api/project/${PROJECT_ID}/progress`);
    let gotComplete = false;

    evtSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            addConsoleLine(data.message, data.type || 'info');

            if (data.type === 'complete' || data.type === 'error') {
                gotComplete = true;
                evtSource.close();
                // Reload the storyboard data
                loadCompleted(blockIdx, pollEndpoint);
            }
        } catch (e) {
            addConsoleLine(event.data, 'info');
        }
    };

    evtSource.onerror = () => {
        evtSource.close();
        if (!gotComplete) {
            // Reconnect after 3s — generation may still be running (images take time)
            addConsoleLine('Connection interrupted. Reconnecting...', 'info');
            setTimeout(() => startProgressStream(blockIdx, pollEndpoint), 3000);
        }
    };
}

async function loadCompleted(blockIdx, pollEndpoint) {
    try {
        const res = await fetch(pollEndpoint);
        if (res.ok) {
            const data = await res.json();
            const block = storyboardBlocks[blockIdx];
            block.scenes = data.storyboard || [];
            addConsoleLine(`✅ Loaded ${block.scenes.length} scenes!`, 'complete');
            // Re-compute elements for this block
            const blockName = block.type === 'intro' ? 'intro' :
                block.type === 'close' ? 'close' :
                    block.type === 'break' ? `break_${block.index + 1}` :
                        block.name.replace(/^Chapter \d+:\s*/, '');
            block.elements = getBlockElements(blockName);
            renderAllBlocks();
        } else {
            addConsoleLine('⚠️ Storyboard not ready yet. Will retry in 5s...', 'info');
            setTimeout(() => loadCompleted(blockIdx, pollEndpoint), 5000);
        }
    } catch (e) {
        addConsoleLine('Failed to load storyboard. Retrying in 5s...', 'error');
        setTimeout(() => loadCompleted(blockIdx, pollEndpoint), 5000);
    }
}

async function generatePrompts(block, blockIdx) {
    const blockFolder = block.type === 'intro' ? 'intro' :
        block.type === 'chapter' ? `chapter_${block.index + 1}` :
            block.type === 'break' ? `break_${block.index + 1}` : 'close';

    const pollEndpoint = block.type === 'intro'
        ? `/api/project/${PROJECT_ID}/storyboard/intro`
        : `/api/project/${PROJECT_ID}/storyboard/${block.chapterIndex}`;

    // Find the prompt button (the last ghost button in the block's actions)
    const actionBtns = document.querySelectorAll(`#block-${blockIdx} .sb-block-actions .btn-ghost`);
    const promptBtn = actionBtns.length > 0 ? actionBtns[actionBtns.length - 1] : null;
    const originalText = promptBtn ? promptBtn.textContent : '📝 Generate Prompts';

    if (promptBtn) {
        promptBtn.disabled = true;
        promptBtn.textContent = '⏳ Generating...';
    }

    showConsole();
    addConsoleLine(`📝 Generating Kling prompts for ${block.scenes.length} scenes...`, 'info');

    try {
        const resp = await fetch(`/api/project/${PROJECT_ID}/generate-prompts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ block_folder: blockFolder })
        });

        if (!resp.ok) {
            const err = await resp.json();
            addConsoleLine(`❌ ${err.error || 'Generation failed'}`, 'error');
            if (promptBtn) {
                promptBtn.disabled = false;
                promptBtn.textContent = originalText;
            }
            return;
        }

        startProgressStream(blockIdx, pollEndpoint);
    } catch (e) {
        addConsoleLine(`❌ Failed: ${e.message}`, 'error');
        if (promptBtn) {
            promptBtn.disabled = false;
            promptBtn.textContent = originalText;
        }
    }
}

let addSceneTarget = null;

function openAddSceneModal(blockIdx, insertIdx) {
    addSceneTarget = { blockIdx, insertIdx };
    document.getElementById('addSceneType').value = 'flashback';
    document.getElementById('addSceneAction').value = '';
    document.getElementById('addSceneNarration').value = '';
    document.getElementById('addSceneDuration').value = '8s';
    document.getElementById('addSceneModal').style.display = 'flex';
}

function closeAddModal() {
    document.getElementById('addSceneModal').style.display = 'none';
    addSceneTarget = null;
}

async function submitAddScene() {
    if (!addSceneTarget) return;

    const sceneType = document.getElementById('addSceneType').value;
    const action = document.getElementById('addSceneAction').value.trim();
    const narration = document.getElementById('addSceneNarration').value.trim();
    const duration = document.getElementById('addSceneDuration').value.trim() || '8s';

    if (!action) {
        alert('Describe qué pasa en la escena.');
        return;
    }

    const { blockIdx, insertIdx } = addSceneTarget;
    const btn = document.getElementById('addSceneSubmit');
    btn.disabled = true;
    btn.textContent = '⏳ Creating...';
    closeAddModal();

    const block = storyboardBlocks[blockIdx];
    const blockFolder = block.type === 'intro' ? 'intro' :
        block.type === 'chapter' ? `chapter_${block.index + 1}` :
            block.type === 'break' ? `break_${block.index + 1}` : 'close';

    const pollEndpoint = block.type === 'intro'
        ? `/api/project/${PROJECT_ID}/storyboard/intro`
        : `/api/project/${PROJECT_ID}/storyboard/${block.chapterIndex}`;

    showConsole();
    addConsoleLine(`➕ Adding ${sceneType.toUpperCase()} scene at position ${insertIdx + 1}...`, 'info');

    try {
        const resp = await fetch(`/api/project/${PROJECT_ID}/insert-scene`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                block_folder: blockFolder,
                insert_index: insertIdx,
                scene_type: sceneType,
                action: action,
                narration: narration,
                duration: duration
            })
        });

        if (!resp.ok) {
            const err = await resp.json();
            addConsoleLine(`❌ ${err.error || 'Insert failed'}`, 'error');
            btn.disabled = false;
            btn.textContent = 'Add Scene + Generate Image';
            return;
        }

        startProgressStream(blockIdx, pollEndpoint);
    } catch (e) {
        addConsoleLine(`❌ Insert failed: ${e.message}`, 'error');
    }

    btn.disabled = false;
    btn.textContent = 'Add Scene + Generate Image';
}

// ─── AI Edit Modal ───
// ─── Regenerate Confirmation Modal ───
function openRegenConfirmModal(block, blockIdx) {
    const overlay = document.createElement('div');
    overlay.className = 'sb-modal-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    overlay.innerHTML = `
        <div class="sb-modal" style="width:450px">
            <div class="sb-modal-header">
                <h3>⚠️ Regenerar Storyboard</h3>
                <button class="sb-modal-close" onclick="this.closest('.sb-modal-overlay').remove()">✕</button>
            </div>
            <div class="sb-modal-body">
                <p style="font-size:0.85rem; line-height:1.6; color:var(--text-secondary)">
                    Si regeneras se perderán <strong>todas las escenas</strong> y los <strong>prompts de video</strong> de este bloque. Esta acción no se puede deshacer.
                </p>
            </div>
            <div class="sb-modal-footer">
                <button class="btn btn-ghost btn-sm" onclick="this.closest('.sb-modal-overlay').remove()">Cancelar</button>
                <button class="btn btn-sm" id="regen-confirm-btn" style="background:rgba(239,68,68,0.2);color:#fca5a5;border:1px solid rgba(239,68,68,0.4)">Continuar</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    document.getElementById('regen-confirm-btn').onclick = () => {
        overlay.remove();
        block.scenes = [];
        renderAllBlocks();
        generateStoryboard(block, blockIdx);
    };
}

let currentEditTarget = null;

function openAiEditModal(blockIdx, itemIdx, type) {
    if (type !== 'scene') return;
    currentEditTarget = { blockIdx, itemIdx, type };
    const block = storyboardBlocks[blockIdx];
    const scene = block.scenes[itemIdx];

    document.getElementById('editSceneNum').textContent = scene.scene_number || (itemIdx + 1);
    document.getElementById('editSceneType').value = scene.type || 'bridge';
    document.getElementById('editSceneAction').value = scene.action || '';
    document.getElementById('editSceneNarration').value = scene.narration || '';
    document.getElementById('editSceneDuration').value = scene.duration || '8s';
    document.getElementById('editRegenImage').checked = true;
    document.getElementById('aiEditModal').style.display = 'flex';
}

function closeAiModal() {
    document.getElementById('aiEditModal').style.display = 'none';
    currentEditTarget = null;
}

async function submitAiEdit() {
    if (!currentEditTarget) return;
    const { blockIdx, itemIdx } = currentEditTarget;

    const sceneType = document.getElementById('editSceneType').value;
    const action = document.getElementById('editSceneAction').value.trim();
    const narration = document.getElementById('editSceneNarration').value.trim();
    const duration = document.getElementById('editSceneDuration').value;
    const regenImage = document.getElementById('editRegenImage').checked;

    if (!action) {
        alert('Describe qué pasa en la escena.');
        return;
    }

    const btn = document.getElementById('aiModalSubmit');
    btn.disabled = true;
    btn.textContent = '⏳ Saving...';
    closeAiModal();

    const block = storyboardBlocks[blockIdx];
    const blockFolder = block.type === 'intro' ? 'intro' :
        block.type === 'chapter' ? `chapter_${block.index + 1}` :
            block.type === 'break' ? `break_${block.index + 1}` : 'close';

    const pollEndpoint = block.type === 'intro'
        ? `/api/project/${PROJECT_ID}/storyboard/intro`
        : `/api/project/${PROJECT_ID}/storyboard/${block.chapterIndex}`;

    showConsole();
    addConsoleLine(`✏️ Updating Scene ${itemIdx + 1}...`, 'info');

    try {
        const resp = await fetch(`/api/project/${PROJECT_ID}/update-scene`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                block_folder: blockFolder,
                scene_index: itemIdx,
                scene_type: sceneType,
                action: action,
                narration: narration,
                duration: duration,
                regenerate_image: regenImage
            })
        });

        if (!resp.ok) {
            const err = await resp.json();
            addConsoleLine(`❌ ${err.error || 'Update failed'}`, 'error');
            btn.disabled = false;
            btn.textContent = 'Save + Regenerate';
            return;
        }

        startProgressStream(blockIdx, pollEndpoint);
    } catch (e) {
        addConsoleLine(`❌ Update failed: ${e.message}`, 'error');
    }

    btn.disabled = false;
    btn.textContent = 'Save + Regenerate';
}

// ─── Console ───
function showConsole() {
    document.getElementById('sbConsole').style.display = 'block';
    document.getElementById('sbConsoleBody').innerHTML = '';
}

function closeConsole() {
    document.getElementById('sbConsole').style.display = 'none';
}

function addConsoleLine(text, type = 'info') {
    const body = document.getElementById('sbConsoleBody');
    const line = document.createElement('div');
    line.className = `sb-console-line ${type}`;
    line.textContent = text;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
}

// ─── Lightbox ───
function openLightbox(src) {
    const lb = document.getElementById('sbLightbox');
    document.getElementById('sbLightboxImg').src = src;
    lb.style.display = 'flex';
}

function closeLightbox() {
    document.getElementById('sbLightbox').style.display = 'none';
}

// ─── Delete ───
function deleteScene(blockIdx, sceneIdx) {
    if (!confirm(`Delete scene ${sceneIdx + 1}?`)) return;
    storyboardBlocks[blockIdx].scenes.splice(sceneIdx, 1);
    renderAllBlocks();
}

// ─── Download ───
function downloadImage(filename, blockIdx) {
    const block = storyboardBlocks[blockIdx];
    const blockFolder = block.type === 'intro' ? 'intro' : `chapter_${block.index + 1}`;
    const url = `/api/project/${PROJECT_ID}/location/${blockFolder}/locations/${filename}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
}

// ─── Utils ───
function parseDuration(dur) {
    if (!dur) return 0;
    if (typeof dur === 'number') return dur;
    const str = String(dur);
    const match = str.match(/(\d+)/);
    return match ? parseInt(match[1]) : 0;
}

// ─── Keyboard ───
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAiModal();
        closeEditPromptModal();
        closeEditLocImageModal();
        closeLightbox();
    }
});

// ─── Edit Prompt Modal ───
let editPromptState = { blockIdx: -1, sceneIdx: -1 };

function openEditPromptModal(blockIdx, sceneIdx) {
    const block = storyboardBlocks[blockIdx];
    const scene = block.scenes[sceneIdx];
    const prompt = scene.prompt || {};
    const sceneNum = scene.scene_number || (sceneIdx + 1);

    editPromptState = { blockIdx, sceneIdx };

    document.getElementById('editPromptNum').textContent = sceneNum;

    // Show current prompt + SFX combined
    const fullText = prompt.sfx
        ? `${prompt.prompt_text || ''}\nSFX: ${prompt.sfx}`
        : (prompt.prompt_text || '');
    document.getElementById('editPromptCurrent').textContent = fullText;

    document.getElementById('editPromptFeedback').value = '';
    document.getElementById('editPromptSubmit').disabled = false;
    document.getElementById('editPromptSubmit').textContent = '🤖 Rewrite Prompt';

    document.getElementById('editPromptModal').style.display = 'flex';
    document.getElementById('editPromptFeedback').focus();
}

function closeEditPromptModal() {
    document.getElementById('editPromptModal').style.display = 'none';
}

async function submitEditPrompt() {
    const { blockIdx, sceneIdx } = editPromptState;
    const block = storyboardBlocks[blockIdx];
    const scene = block.scenes[sceneIdx];
    const prompt = scene.prompt || {};
    const feedback = document.getElementById('editPromptFeedback').value.trim();

    if (!feedback) return;

    const btn = document.getElementById('editPromptSubmit');
    btn.disabled = true;
    btn.textContent = '⏳ Rewriting...';

    const blockFolder =
        block.type === 'intro' ? 'intro' :
            block.type === 'close' ? 'close' :
                block.type === 'chapter' ? `chapter_${block.index + 1}` :
                    block.type === 'break' ? `break_${block.index + 1}` : 'intro';

    try {
        const resp = await fetch(`/api/project/${PROJECT_ID}/edit-prompt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                block_folder: blockFolder,
                scene_index: sceneIdx,
                current_prompt: prompt.prompt_text || '',
                current_sfx: prompt.sfx || '',
                feedback: feedback
            })
        });

        const result = await resp.json();

        if (result.status === 'ok') {
            // Update in-memory data
            scene.prompt.prompt_text = result.prompt_text;
            scene.prompt.sfx = result.sfx;

            // Save scroll position, close modal, re-render, restore scroll
            const container = document.querySelector('.sb-content');
            const scrollLeft = container ? container.scrollLeft : 0;
            const scrollTop = window.scrollY;

            closeEditPromptModal();
            renderAllBlocks();

            if (container) container.scrollLeft = scrollLeft;
            window.scrollTo(0, scrollTop);
        } else {
            btn.textContent = `❌ ${result.error || 'Failed'}`;
            btn.disabled = false;
        }
    } catch (e) {
        btn.textContent = `❌ ${e.message}`;
        btn.disabled = false;
    }
}

// ─── Edit Location Image Modal ───
let editLocImageState = { blockIdx: -1, sceneIdx: -1, locIdx: 0 };

function openEditLocImageModal(blockIdx, sceneIdx, locIdx = 0) {
    const block = storyboardBlocks[blockIdx];
    const scene = block.scenes[sceneIdx];
    const prompt = scene.prompt || {};

    // Normalize locations for backward compat
    if (!prompt.locations && prompt.location_id) {
        prompt.locations = [{
            id: prompt.location_id,
            image: prompt.location_image,
            prompt: prompt.location_prompt || ''
        }];
    }
    const locations = prompt.locations || [];
    const loc = locations[locIdx];
    if (!loc) return;

    editLocImageState = { blockIdx, sceneIdx, locIdx };

    const imgLabel = locations.length === 1 ? '@Image' : `@Image${locIdx + 1}`;
    document.getElementById('editLocImageName').textContent =
        `${imgLabel} — ${loc.id.replace(/_/g, ' ')}`;

    // Show current image
    const blockFolder =
        block.type === 'intro' ? 'intro' :
            block.type === 'close' ? 'close' :
                block.type === 'chapter' ? `chapter_${block.index + 1}` :
                    block.type === 'break' ? `break_${block.index + 1}` : 'intro';
    const imgUrl = `/api/project/${PROJECT_ID}/scene-image/${blockFolder}/${loc.image}?t=${Date.now()}`;
    document.getElementById('editLocImagePreview').src = imgUrl;

    // Show current generation prompt
    document.getElementById('editLocImageCurrentPrompt').textContent = loc.prompt || '(no prompt saved)';

    // Populate reference image dropdown with all location images
    const refSelect = document.getElementById('editLocImageRefSelect');
    refSelect.innerHTML = '<option value="">— Sin referencia (generar desde cero) —</option>';
    const seen = new Set();
    for (const s of (block.scenes || [])) {
        const locs = s.prompt?.locations || [];
        // Also handle old format
        if (locs.length === 0 && s.prompt?.location_id) {
            locs.push({ id: s.prompt.location_id, image: s.prompt.location_image, prompt: s.prompt.location_prompt });
        }
        for (const l of locs) {
            if (l.image && !seen.has(l.image) && l.image !== loc.image) {
                seen.add(l.image);
                const sceneNum = s.scene_number || '?';
                const opt = document.createElement('option');
                opt.value = l.image;
                opt.textContent = `Scene ${sceneNum}: ${l.id.replace(/_/g, ' ')}`;
                refSelect.appendChild(opt);
            }
        }
    }

    document.getElementById('editLocImageFeedback').value = '';
    document.getElementById('editLocImageSubmit').disabled = false;
    document.getElementById('editLocImageSubmit').textContent = '🖼️ Regenerate Image';

    document.getElementById('editLocImageModal').style.display = 'flex';
    document.getElementById('editLocImageFeedback').focus();
}

function closeEditLocImageModal() {
    document.getElementById('editLocImageModal').style.display = 'none';
}

async function submitEditLocImage() {
    const { blockIdx, sceneIdx, locIdx } = editLocImageState;
    const block = storyboardBlocks[blockIdx];
    const scene = block.scenes[sceneIdx];
    const prompt = scene.prompt || {};
    const locations = prompt.locations || [];
    const loc = locations[locIdx];
    if (!loc) return;

    const feedback = document.getElementById('editLocImageFeedback').value.trim();
    if (!feedback) return;

    const btn = document.getElementById('editLocImageSubmit');
    btn.disabled = true;
    btn.textContent = '⏳ Generating new image...';

    const blockFolder =
        block.type === 'intro' ? 'intro' :
            block.type === 'close' ? 'close' :
                block.type === 'chapter' ? `chapter_${block.index + 1}` :
                    block.type === 'break' ? `break_${block.index + 1}` : 'intro';

    try {
        const resp = await fetch(`/api/project/${PROJECT_ID}/edit-location-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                block_folder: blockFolder,
                location_id: loc.id,
                location_image: loc.image,
                current_prompt: loc.prompt || '',
                feedback: feedback,
                reference_image: document.getElementById('editLocImageRefSelect').value || ''
            })
        });

        const result = await resp.json();

        if (result.status === 'ok') {
            // Update location prompt in all in-memory scenes with same location_id
            for (const b of storyboardBlocks) {
                for (const s of (b.scenes || [])) {
                    const locs = s.prompt?.locations || [];
                    for (const l of locs) {
                        if (l.id === loc.id) {
                            l.prompt = result.new_prompt;
                        }
                    }
                    // Also handle old format
                    if (s.prompt && s.prompt.location_id === loc.id) {
                        s.prompt.location_prompt = result.new_prompt;
                    }
                }
            }

            // Save scroll position, close modal, re-render, restore scroll
            const container = document.querySelector('.sb-content');
            const scrollLeft = container ? container.scrollLeft : 0;
            const scrollTop = window.scrollY;

            closeEditLocImageModal();
            renderAllBlocks();

            if (container) container.scrollLeft = scrollLeft;
            window.scrollTo(0, scrollTop);
        } else {
            btn.textContent = `❌ ${result.error || 'Failed'}`;
            btn.disabled = false;
        }
    } catch (e) {
        btn.textContent = `❌ ${e.message}`;
        btn.disabled = false;
    }
}

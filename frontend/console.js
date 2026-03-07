const API = "http://localhost:8001";
let ws = null;
let currentProfile = null;
let versionsCache = {};
let lastLineCount = 0;
let userMessages = [];
let cmdMode = true;

async function loadProfiles() {
    const res = await fetch(`${API}/profiles`);
    const profiles = await res.json();
    
    const container = document.getElementById('profiles-list');
    container.innerHTML = profiles.map(p => `
        <div class="profile-card ${currentProfile === p.name ? 'active' : ''}" 
             onclick="selectProfile('${p.name}')">
            <h3>${p.name}</h3>
            <div class="software">${p.software || 'Not configured'} ${p.version || ''}</div>
        </div>
    `).join('');

    // Hide profile-detail until a profile is selected
    const detail = document.getElementById('profile-detail');
    if (detail && !currentProfile) detail.classList.add('hidden');
}

async function createProfile() {
    const nameInput = document.getElementById('new-profile-name');
    if (!nameInput) return;
    
    const name = nameInput.value.trim();
    if (!name) return;
    
    await fetch(`${API}/profile/${name}`, { method: 'POST' });
    document.getElementById('new-profile-name').value = '';
    closeModal();
    loadProfiles();
}

function showCreateModal() {
    document.getElementById('create-modal').classList.remove('hidden');
    document.getElementById('new-profile-name').focus();
}

function closeModal() {
    document.getElementById('create-modal').classList.add('hidden');
}

document.getElementById('new-profile-name').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') createProfile();
});

async function loadAIStatus() {
    try {
        const res = await fetch(`${API}/ai/status`);
        const data = await res.json();
        document.getElementById('ai-toggle').textContent = `AI: ${data.enabled ? 'ON' : 'OFF'}`;
        document.getElementById('ai-mode').value = data.mode;
    } catch (e) {}
}

async function toggleAI() {
    await fetch(`${API}/ai/toggle`, { method: 'POST' });
    loadAIStatus();
}

async function setAIMode() {
    const mode = document.getElementById('ai-mode').value;
    await fetch(`${API}/ai/mode/${mode}`, { method: 'POST' });
}

async function loadConfig() {
    try {
        const res = await fetch(`${API}/config`);
        const config = await res.json();
        
        if (config.ai) {
            const setValue = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val;
            };
            const setChecked = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.checked = val;
            };
            
            setValue('api-key-groq', config.ai.providers?.groq?.api_key || '');
            setValue('api-key-openai', config.ai.providers?.openai?.api_key || '');
            setValue('api-key-anthropic', config.ai.providers?.anthropic?.api_key || '');
            setValue('api-key-google', config.ai.providers?.google?.api_key || '');
            setValue('api-key-azure', config.ai.providers?.azure?.api_key || '');
            setValue('azure-endpoint', config.ai.providers?.azure?.endpoint || '');
            setValue('azure-deployment', config.ai.providers?.azure?.deployment || '');
            setValue('local-url', config.ai.providers?.local?.url || 'http://localhost:11434');
            setValue('ai-provider', config.ai.provider || 'groq');
            setValue('ai-model', config.ai.model || 'llama-3.1-8b-instant');
            setValue('ai-mode', config.ai.mode || 'auto-safe');
            setValue('ai-name', config.ai.ai_name || 'Ava');
            setValue('response-method', config.ai.response_method || 'msg');
            setValue('admin-players', (config.ai.roles?.admin || []).join(', '));
            setValue('ai-prompt', config.ai.system_prompt || '');
            setChecked('auto-execute', config.ai.auto_execute || false);
            setValue('vision-provider', config.ai.vision_provider || config.ai.provider || 'groq');
            setValue('vision-api-key', config.ai.vision_api_key || '');
            updateProviderModels();
            if (document.getElementById('vision-model')) {
                updateVisionProviderModels(true);
                const visionModel = config.ai.vision_model || '';
                const providerKey = config.ai.vision_provider || config.ai.provider || 'groq';
                if (visionModel && PROVIDER_MODELS[providerKey]?.includes(visionModel)) {
                    setValue('vision-model', visionModel);
                    setValue('vision-model-custom', '');
                } else {
                    setValue('vision-model-custom', visionModel);
                }
            }
        }
        if (config.server) {
            document.getElementById('ram-setting').value = config.server.default_ram || '1G';
        }
    } catch (e) {
        console.log('Config loading failed', e);
    }
}

    const PROVIDER_MODELS = {
        groq: ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama-3.2-90b-vision-preview", "meta-llama/llama-4-scout-17b-16e-instruct", "mixtral-8x7b-32768"],
        openai: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        anthropic: ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"],
        google: ["gemini-1.5-flash", "gemini-1.5-pro"],
        azure: ["gpt-4", "gpt-35-turbo"],
        local: ["llama3", "llama2", "mistral", "codellama", "phi3", "gemma"]
    };

function updateProviderModels() {
    const provider = document.getElementById('ai-provider').value;
    const modelSelect = document.getElementById('ai-model');
    modelSelect.innerHTML = '';
    
    const models = PROVIDER_MODELS[provider] || [];
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
    });
}

function updateVisionProviderModels(forceSelectFirst = false) {
    const providerEl = document.getElementById('vision-provider');
    const modelSelect = document.getElementById('vision-model');
    if (!providerEl || !modelSelect) return;
    const provider = providerEl.value;
    modelSelect.innerHTML = '';
    
    const models = PROVIDER_MODELS[provider] || [];
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
    });
    
    if (forceSelectFirst && models.length > 0) {
        modelSelect.value = models[0];
    }
}

async function saveConfig() {
    try {
        const res = await fetch(`${API}/config`);
        const config = await res.json();
        
        if (!config.ai) config.ai = {};
        if (!config.server) config.server = {};
        
        config.ai.provider = document.getElementById('ai-provider').value;
        config.ai.model = document.getElementById('ai-model').value;
        const visionProviderEl = document.getElementById('vision-provider');
        const visionModelEl = document.getElementById('vision-model');
        const visionApiKeyEl = document.getElementById('vision-api-key');
        if (visionProviderEl) config.ai.vision_provider = visionProviderEl.value;
        const visionCustomEl = document.getElementById('vision-model-custom');
        if (visionModelEl) config.ai.vision_model = visionModelEl.value;
        if (visionCustomEl && visionCustomEl.value.trim()) {
            config.ai.vision_model = visionCustomEl.value.trim();
        }
        if (visionApiKeyEl) config.ai.vision_api_key = visionApiKeyEl.value;
        
        if (!config.ai.providers) config.ai.providers = {};
        
        config.ai.providers.groq = { api_key: document.getElementById('api-key-groq').value };
        config.ai.providers.openai = { api_key: document.getElementById('api-key-openai').value };
        config.ai.providers.anthropic = { api_key: document.getElementById('api-key-anthropic').value };
        config.ai.providers.google = { api_key: document.getElementById('api-key-google').value };
        config.ai.providers.azure = { 
            api_key: document.getElementById('api-key-azure').value,
            endpoint: document.getElementById('azure-endpoint').value,
            deployment: document.getElementById('azure-deployment').value
        };
        
        config.ai.providers.local = {
            url: document.getElementById('local-url').value,
            model: document.getElementById('ai-model').value
        };
        
        config.ai.ai_name = document.getElementById('ai-name').value;
        config.ai.response_method = document.getElementById('response-method').value;
        
        const adminInput = document.getElementById('admin-players').value;
        if (!config.ai.roles) config.ai.roles = {};
        config.ai.roles.admin = adminInput.split(',').map(s => s.trim()).filter(s => s);
        
        config.ai.auto_execute = document.getElementById('auto-execute').checked;
        config.server.default_ram = document.getElementById('ram-setting').value;
        
        await fetch(`${API}/config`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        alert('Settings saved!');
    } catch (e) {
        console.log('Config saving failed', e);
        alert('Failed to save settings');
    }
}

async function reloadAI() {
    try {
        const res = await fetch(`${API}/ai/reload`, { method: 'POST' });
        const data = await res.json();
        alert(`AI Reloaded! Name: ${data.ai_name}, Model: ${data.model}`);
    } catch (e) {
        console.log('Failed to reload AI', e);
        alert('Failed to reload AI');
    }
}

function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabId).classList.remove('hidden');
    event.target.classList.add('active');
    if (tabId === 'server-settings') loadServerProps();
}

async function loadServerProps() {
    if (!currentProfile) {
        alert('Select a profile first');
        return;
    }
    try {
        const res = await fetch(`${API}/server/properties/${currentProfile}`);
        const props = await res.json();
        
        document.getElementById('prop-motd').value = props['motd'] || '';
        document.getElementById('prop-max-players').value = props['max-players'] || 20;
        document.getElementById('prop-view-distance').value = props['view-distance'] || 10;
        document.getElementById('prop-gamemode').value = props['gamemode'] || 'survival';
        document.getElementById('prop-pvp').value = props['pvp'] || 'true';
        document.getElementById('prop-difficulty').value = props['difficulty'] || 'easy';
        document.getElementById('prop-spawn-animals').value = props['spawn-animals'] || 'true';
        document.getElementById('prop-spawn-monsters').value = props['spawn-monsters'] || 'true';
    } catch (e) {
        console.log('Failed to load server properties', e);
    }
}

async function saveServerProp(key, value) {
    if (!currentProfile) return;
    try {
        const res = await fetch(`${API}/server/properties/${currentProfile}`);
        const props = await res.json();
        props[key] = value;
        await fetch(`${API}/server/properties/${currentProfile}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(props)
        });
    } catch (e) {
        console.log('Failed to save server property', e);
    }
}

async function selectProfile(name) {
    currentProfile = name;
    const res = await fetch(`${API}/profile/${name}`);
    const profile = await res.json();
    
    document.getElementById('selected-profile-name').textContent = name;
    // Reveal profile detail, settings and console when profile selected
    document.getElementById('profile-detail').classList.remove('hidden');
    document.querySelector('.settings-section').classList.remove('hidden');
    document.querySelector('.console-section').classList.remove('hidden');
    
    if (profile.software) {
        document.getElementById('software-select').value = profile.software;
    }
    
    const downloadSection = document.querySelector('.config-panel');
    if (profile.software && profile.version) {
        downloadSection.innerHTML = `
            <div class="server-info">
                <span class="info-badge">${profile.software}</span>
                <span class="info-badge">${profile.version}</span>
            </div>
            <p class="server-ready">✅ Server ready to start</p>
        `;
    } else {
        downloadSection.innerHTML = `
            <div class="form-group">
                <label>Software</label>
                <select id="software-select" onchange="loadVersions()">
                    <option value="vanilla">Vanilla</option>
                    <option value="paper">Paper</option>
                    <option value="fabric">Fabric</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Version</label>
                <select id="version-select" onchange="loadBuilds()"></select>
            </div>
            
            <div id="build-group" class="form-group hidden">
                <label>Build</label>
                <select id="build-select"></select>
            </div>
            
            <button onclick="downloadServer()" class="download-btn">⬇ Download</button>
        `;
        loadVersions();
    }
    
    loadProfiles();
    updateStatus();
}

async function loadVersions() {
    const software = document.getElementById('software-select').value;
    
    if (versionsCache[software]) {
        renderVersions(versionsCache[software]);
        return;
    }
    
    const res = await fetch(`${API}/versions/${software}`);
    const versions = await res.json();
    versionsCache[software] = versions;
    renderVersions(versions);
}

function renderVersions(versions) {
    const select = document.getElementById('version-select');
    if (Array.isArray(versions)) {
        select.innerHTML = versions.map(v => 
            `<option value="${v.version || v}">${v.version || v}</option>`
        ).join('');
    }
    loadBuilds();
}

async function loadBuilds() {
    const software = document.getElementById('software-select').value;
    const version = document.getElementById('version-select').value;
    const buildGroup = document.getElementById('build-group');
    
    if (software === 'paper') {
        const res = await fetch(`${API}/paper/${version}/builds`);
        const builds = await res.json();
        if (builds && builds.length > 0) {
            const latest = builds[builds.length - 1];
            buildGroup.classList.remove('hidden');
            document.getElementById('build-select').innerHTML = 
                `<option value="${latest}">${latest} (latest)</option>`;
        }
    } else {
        buildGroup.classList.add('hidden');
    }
}

async function downloadServer() {
    const software = document.getElementById('software-select').value;
    const version = document.getElementById('version-select').value;
    const build = document.getElementById('build-select')?.value;
    
    const res = await fetch(`${API}/profile/${currentProfile}/download?software=${software}&version=${version}${build ? `&build=${build}` : ''}`, 
        { method: 'POST' });
    const data = await res.json();
    
    alert(data.message);
    loadProfiles();
    selectProfile(currentProfile);
}

async function startServer() {
    const res = await fetch(`${API}/start/${currentProfile}`, { method: 'POST' });
    const data = await res.json();
    
    if (data.success) {
        document.getElementById('start-btn').classList.add('hidden');
        document.getElementById('stop-btn').classList.remove('hidden');
        connectConsole();
    }
    alert(data.message);
    updateStatus();
}

async function stopServer() {
    const res = await fetch(`${API}/stop`, { method: 'POST' });
    const data = await res.json();
    
    document.getElementById('start-btn').classList.remove('hidden');
    document.getElementById('stop-btn').classList.add('hidden');
    alert(data.message);
    updateStatus();
}

async function sendCommand() {
    const input = document.getElementById('cmd-input');
    const cmd = input.value.trim();
    if (!cmd) return;
    
    const consoleDiv = document.getElementById('console');
    
    if (cmdMode) {
        consoleDiv.innerHTML += `<div class="line default">> ${escapeHtml(cmd)}</div>`;
        await fetch(`${API}/command`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cmd: cmd})
        });
    } else {
        const playerName = prompt("Enter your Minecraft username:", "Sweete_Nightmare") || "Player";
        // Add player chat message with avatar
        consoleDiv.innerHTML += `
            <div class="chat-message player-chat">
                <img src="https://minotar.net/helm/${playerName}/32.png" alt="${playerName}" class="chat-avatar">
                <div class="chat-content">
                    <span class="chat-name" style="color: #22d3ee;">${playerName}</span>
                    <span class="chat-text">${escapeHtml(cmd)}</span>
                </div>
            </div>`;
        const res = await fetch(`${API}/ai/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: cmd, player: playerName})
        });
        const data = await res.json();

        // Add AI response with avatar
        consoleDiv.innerHTML += `
            <div class="chat-message ai-chat">
                <img src="https://minotar.net/helm/Ava/32.png" alt="Ava" class="chat-avatar" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22><rect fill=%22%23c084fc%22 width=%2232%22 height=%2232%22/><text x=%2216%22 y=%2220%22 text-anchor=%22middle%22 fill=%22white%22>🤖</text></svg>'">
                <div class="chat-content">
                    <span class="chat-name" style="color: #c084fc;">Ava</span>
                    <span class="chat-text">${escapeHtml(data.response || '...')}</span>
                </div>
            </div>`;
    }
    input.value = '';
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}

function toggleCmdMode() {
    cmdMode = !cmdMode;
    const btn = document.getElementById('cmd-mode-toggle');
    const label = document.getElementById('mode-label');
    const input = document.getElementById('cmd-input');
    
    if (cmdMode) {
        btn.classList.add('cmd-active');
        btn.classList.remove('chat-active');
        label.textContent = '📢 CMD';
        input.placeholder = 'Type command...';
    } else {
        btn.classList.remove('cmd-active');
        btn.classList.add('chat-active');
        label.textContent = '💬 CHAT';
        input.placeholder = 'Chat with AI...';
    }
}

function copyConsole() {
    const consoleDiv = document.getElementById('console');
    const text = consoleDiv.innerText;
    navigator.clipboard.writeText(text).then(() => {
        alert('Console copied to clipboard!');
    });
}

function clearConsole() {
    document.getElementById('console').innerHTML = '';
    lastLineCount = 0;
}

function updateStatus() {
    fetch(`${API}/status`).then(r => r.json()).then(s => {
        const el = document.getElementById('server-status');
        el.textContent = s.status;
        el.className = 'status ' + s.status;
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function stripColorCodes(text) {
    text = text.replace(/\[(\d+;)+\d+m/g, '');
    text = text.replace(/\[0m/g, '');
    text = text.replace(/\[3m/g, '');
    text = text.replace(/\[4m/g, '');
    text = text.replace(/\[1m/g, '');
    return text;
}

function getLineClass(line) {
    if (line.includes('For help, type') || line.includes('For help type') || line.includes('Unknown command'))
        return 'filtered';
    
    if (line.includes('ERROR') || line.includes('Exception') || line.includes('Failed') || line.includes('error'))
        return 'error';
    if (line.includes(' WARN') || line.includes('[WARN]'))
        return 'warn';
    if (line.includes(' INFO') || line.includes('[INFO]'))
        return 'info';
    if (line.includes('Done') || line.includes('Done loading') || line.includes('For help'))
        return 'success';
    if (line.match(/<[^>]+>/))
        return 'chat';
    if (line.includes('joined') || line.includes('left') || line.includes('logged in') || line.includes(' disconnected'))
        return 'player';
    if (line.includes('Tick') || line.includes('TPS'))
        return 'performance';
    return 'default';
}

function colorizeLine(line) {
    line = line.replace(/\[(\d{2}:\d{2}:\d{2})\]/g, '<span class="timestamp">[$1]</span>');
    line = line.replace(/(\d{4}-\d{2}-\d{2})/g, '<span class="date">$1</span>');
    line = line.replace(/(WARN)/g, '<span class="warn-text">$1</span>');
    line = line.replace(/(INFO)/g, '<span class="info-text">$1</span>');
    line = line.replace(/(ERROR)/g, '<span class="error-text">$1</span>');
    line = line.replace(/(&lt;)([^&]+)(&gt;)/g, '$1<span class="chat-player">$2</span>$3');
    return line;
}

function connectConsole() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    
    lastLineCount = 0;
    
    ws = new WebSocket('ws://localhost:8001/console/ws');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const lines = data.lines || [];
        const ai = data.ai;
        const chat = data.chat;
        
        const consoleDiv = document.getElementById('console');
        
        if (lines.length > 0) {
            if (lines.length < lastLineCount || lastLineCount === 0) {
                lastLineCount = 0;
            }
            
            if (lines.length > lastLineCount) {
                const newLines = lines.slice(lastLineCount);
                newLines.forEach(line => {
                    line = stripColorCodes(line);
                    
                    // Skip entity data messages and other noise
                    if (line.includes('has the following entity data') || 
                        line.includes('Found no elements') ||
                        line.includes('Ticking entity') ||
                        line.includes('ChunkTaskScheduler') ||
                        line.includes('Server thread')) {
                        return;
                    }
                    
                    // Check if it's a chat message (handles both <player> and [Not Secure] <player> formats)
                    const chatMatch = line.match(/(?:\[.*?\]\s*)?<([^>]+)>\s*(.+)/);
                    if (chatMatch) {
                        const playerName = chatMatch[1];
                        const message = chatMatch[2];
                        consoleDiv.innerHTML += `
                            <div class="chat-message player-chat">
                                <img src="https://minotar.net/helm/${playerName}/32.png" alt="${playerName}" class="chat-avatar">
                                <div class="chat-content">
                                    <span class="chat-name" style="color: #22d3ee;">${playerName}</span>
                                    <span class="chat-text">${escapeHtml(message)}</span>
                                </div>
                            </div>`;
                        return;
                    }
                    
                    const cls = getLineClass(line);
                    const escaped = escapeHtml(line);
                    const colored = colorizeLine(escaped);
                    consoleDiv.innerHTML += `<div class="line ${cls}">${colored}</div>`;
                });
                lastLineCount = lines.length;
            }
        }
        
        if (ai) {
            consoleDiv.innerHTML += `
                <div class="chat-message ai-chat">
                    <img src="https://minotar.net/helm/Ava/32.png" alt="Ava" class="chat-avatar" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22><rect fill=%22%23c084fc%22 width=%2232%22 height=%2232%22/><text x=%2216%22 y=%2220%22 text-anchor=%22middle%22 fill=%22white%22>🤖</text></svg>'">
                    <div class="chat-content">
                        <span class="chat-name" style="color: #c084fc;">Ava</span>
                        <span class="chat-text">${escapeHtml(ai.message)}</span>
                    </div>
                </div>`;
        }
        
        if (chat && chat.message) {
            const playerName = chat.player || "Player";
            consoleDiv.innerHTML += `
                <div class="chat-message player-chat">
                    <img src="https://minotar.net/helm/${playerName}/32.png" alt="${playerName}" class="chat-avatar">
                    <div class="chat-content">
                        <span class="chat-name" style="color: #22d3ee;">${playerName}</span>
                        <span class="chat-text">${escapeHtml(chat.message)}</span>
                    </div>
                </div>`;
        }
        
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
    };
    
    ws.onclose = () => {
        ws = null;
        setTimeout(connectConsole, 2000);
    };
    
    ws.onerror = () => {
        ws = null;
    };
}

setInterval(updateStatus, 5000);
loadProfiles();
loadAIStatus();

// Mod Manager Functions
async function searchModsBtn() {
    const query = document.getElementById('mod-search').value;
    if (!query) return;
    await searchMods({target: {value: query}});
}

async function searchMods(event) {
    const query = event.target.value;
    if (query.length < 2) return;
    
    try {
        const res = await fetch(`${API}/mods/search?query=${encodeURIComponent(query)}`);
        const mods = await res.json();
        
        const resultsDiv = document.getElementById('mod-search-results');
        resultsDiv.innerHTML = mods.map(mod => `
            <div class="mod-result-item" style="padding: 10px; border-bottom: 1px solid var(--border);">
                <strong>${mod.title}</strong>
                <p style="color: var(--text-muted); font-size: 12px;">${mod.description || ''}</p>
                <button class="btn btn-small" onclick="installMod('${mod.id}', '${mod.title.replace(/'/g, "\\'")}')">Install</button>
            </div>
        `).join('');
    } catch (e) {
        console.log('Failed to search mods', e);
    }
}

async function installMod(projectId, modTitle) {
    if (!currentProfile) {
        alert('Select a profile first');
        return;
    }
    
    try {
        const versionsRes = await fetch(`${API}/mods/${projectId}/versions`);
        const versions = await versionsRes.json();
        
        if (versions.length > 0 && versions[0].files && versions[0].files.length > 0) {
            const file = versions[0].files[0];
            const installRes = await fetch(`${API}/mods/${currentProfile}/install`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url: file.url,
                    name: modTitle || projectId,
                    software: currentSoftware
                })
            });
            const result = await installRes.json();
            
            if (result.success) {
                alert(`Successfully installed: ${modTitle || projectId}`);
                loadInstalledMods();
            } else {
                alert('Failed to install: ' + result.error);
            }
        } else {
            alert('No files available for this mod');
        }
    } catch (e) {
        console.log('Failed to install mod', e);
        alert('Failed to install mod');
    }
}

async function loadInstalledMods() {
    if (!currentProfile) return;
    try {
        const url = currentSoftware ? `${API}/mods/${currentProfile}?software=${encodeURIComponent(currentSoftware)}` : `${API}/mods/${currentProfile}`;
        const res = await fetch(url);
        const mods = await res.json();
        
        const list = document.getElementById('installed-mods-list');
        if (mods.length === 0) {
            list.innerHTML = '<p style="color: var(--text-muted);">No mods installed</p>';
        } else {
            list.innerHTML = mods.map(mod => `
                <div style="padding: 10px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <span>${mod.name}</span>
                    <button class="btn btn-small btn-danger" onclick="removeMod('${mod.name}')">Remove</button>
                </div>
            `).join('');
        }
    } catch (e) {
        console.log('Failed to load mods', e);
    }
}

async function removeMod(modName) {
    if (!currentProfile) return;
    try {
        const url = currentSoftware ? `${API}/mods/${currentProfile}/${modName}?software=${encodeURIComponent(currentSoftware)}` : `${API}/mods/${currentProfile}/${modName}`;
        await fetch(url, {method: 'DELETE'});
        loadInstalledMods();
    } catch (e) {
        alert('Failed to remove mod');
    }
}

// Backup Functions
async function createBackup() {
    if (!currentProfile) {
        alert('Select a profile first');
        return;
    }
    try {
        const res = await fetch(`${API}/backup/${currentProfile}`);
        const result = await res.json();
        if (result.success) {
            alert('Backup created successfully!');
            loadBackupHistory();
        } else {
            alert('Backup failed: ' + result.error);
        }
    } catch (e) {
        alert('Failed to create backup');
    }
}

async function loadBackupHistory() {
    try {
        const res = await fetch(`${API}/backup/list`);
        const backups = await res.json();
        
        const list = document.getElementById('backup-history-list');
        if (backups.length === 0) {
            list.innerHTML = '<p style="color: var(--text-muted);">No backups yet</p>';
        } else {
            list.innerHTML = backups.map(b => `
                <div style="padding: 10px; border-bottom: 1px solid var(--border);">
                    <strong>${b.name}</strong>
                    <p style="color: var(--text-muted); font-size: 12px;">${b.timestamp}</p>
                </div>
            `).join('');
        }
    } catch (e) {
        console.log('Failed to load backup history', e);
    }
}

// Grief Protection Functions
async function toggleGriefProtection() {
    const enabled = document.getElementById('grief-enabled').checked;
    try {
        const endpoint = enabled ? '/grief/enable' : '/grief/disable';
        await fetch(`${API}${endpoint}`, {method: 'POST'});
    } catch (e) {
        console.log('Failed to toggle grief protection', e);
    }
}

async function loadGriefStatus() {
    try {
        const res = await fetch(`${API}/grief/status`);
        const status = await res.json();
        
        document.getElementById('grief-enabled').checked = status.enabled;
    } catch (e) {
        console.log('Failed to load grief status', e);
    }
}

// Web Hosting Functions
async function startHosting() {
    const port = document.getElementById('host-port').value;
    try {
        const res = await fetch(`${API}/host/start`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({port: parseInt(port)})
        });
        const result = await res.json();
        
        if (result.success) {
            document.getElementById('host-start-btn').classList.add('hidden');
            document.getElementById('host-stop-btn').classList.remove('hidden');
            document.getElementById('host-status-text').textContent = 'Running';
            document.getElementById('host-status-text').classList.remove('stopped');
            document.getElementById('host-status-text').classList.add('running');
            document.getElementById('host-local-url').textContent = result.local_url || `http://localhost:${port}`;
            document.getElementById('host-network-url').textContent = result.network_url || '';
        } else {
            alert('Failed to start hosting: ' + result.error);
        }
    } catch (e) {
        alert('Failed to start hosting');
    }
}

async function stopHosting() {
    try {
        const res = await fetch(`${API}/host/stop`, {method: 'POST'});
        const result = await res.json();
        
        if (result.success) {
            document.getElementById('host-start-btn').classList.remove('hidden');
            document.getElementById('host-stop-btn').classList.add('hidden');
            document.getElementById('host-status-text').textContent = 'Stopped';
            document.getElementById('host-status-text').classList.remove('running');
            document.getElementById('host-status-text').classList.add('stopped');
        }
    } catch (e) {
        alert('Failed to stop hosting');
    }
}

async function loadHostingStatus() {
    try {
        const res = await fetch(`${API}/host/status`);
        const status = await res.json();
        
        if (status.running) {
            document.getElementById('host-start-btn').classList.add('hidden');
            document.getElementById('host-stop-btn').classList.remove('hidden');
            document.getElementById('host-status-text').textContent = 'Running';
            document.getElementById('host-status-text').classList.remove('stopped');
            document.getElementById('host-status-text').classList.add('running');
            document.getElementById('host-local-url').textContent = status.local_url || '-';
            document.getElementById('host-network-url').textContent = status.network_url || '-';
        }
    } catch (e) {
        console.log('Failed to load hosting status', e);
    }
}
loadConfig();

// app.js - Multi-User Benchmark Arena

// State
let sessionToken = localStorage.getItem('benchmark_token');
let currentTurn = -1;
let myVote = null;
let lastStatus = null;

// DOM
const screens = {
    login: document.getElementById('login-screen'),
    lobby: document.getElementById('lobby-screen'),
    arena: document.getElementById('arena-screen'),
    results: document.getElementById('results-screen')
};

// --- Init ---
if (sessionToken) {
    pollState();
} else {
    showScreen('login');
}

// --- Login ---
document.getElementById('join-btn').addEventListener('click', async () => {
    const apiKey = document.getElementById('api-key').value.trim();
    const nickname = document.getElementById('nickname').value.trim();
    const playerCount = parseInt(document.getElementById('player-count').value) || 1;

    if (!apiKey || !nickname) return alert("Please enter API Key and Nickname");

    try {
        const res = await fetch('api/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey, nickname, expected_players: playerCount })
        });

        if (!res.ok) throw new Error("Invalid API Key");

        const data = await res.json();
        sessionToken = data.token;
        localStorage.setItem('benchmark_token', sessionToken);

        pollState(); // Start polling

    } catch (e) {
        alert(e.message);
    }
});

// --- Polling Loop ---
async function pollState() {
    try {
        const res = await fetch('api/poll', {
            headers: { 'token': sessionToken }
        });

        if (res.status === 401) {
            localStorage.removeItem('benchmark_token');
            sessionToken = null;
            showScreen('login');
            return;
        }

        const state = await res.json();
        renderState(state);

        // Loop
        setTimeout(pollState, 1000);

    } catch (e) {
        console.error("Poll error", e);
        setTimeout(pollState, 2000);
    }
}

// --- Render ---
function renderState(state) {
    // Status Badge
    const badge = document.getElementById('status-badge');
    if (badge) badge.textContent = state.status.toUpperCase();

    // Voters List
    const votersList = document.getElementById('voters-list');
    if (votersList) votersList.innerHTML = state.voters_names.map(n => `<li>${n}</li>`).join('');

    // Metrics
    const voterCount = document.getElementById('voter-count');
    if (voterCount) voterCount.textContent = `${state.voters_count} Voters`;

    const turnNum = document.getElementById('turn-num');
    if (turnNum) turnNum.textContent = state.turn + 1;

    // Session ID
    const sidLobby = document.getElementById('lobby-session-id');
    const sidArena = document.getElementById('arena-session-id');
    if (sidLobby) sidLobby.textContent = (state.session_id || '').substring(0, 8);
    if (sidArena) sidArena.textContent = (state.session_id || '').substring(0, 8);

    // Screen Logic
    if (state.status === 'waiting') {
        showScreen('lobby');
        const lobbyTitle = document.querySelector('#lobby-screen h2');
        if (lobbyTitle) {
            const remaining = (state.expected_players || 1) - (state.voters_count || 0);
            if (remaining > 0) {
                lobbyTitle.textContent = `Waiting for ${remaining} more player${remaining > 1 ? 's' : ''}...`;
            } else {
                lobbyTitle.textContent = `Lobby (Ready!)`;
            }
        }
    } else if (state.status === 'input' || state.status === 'thinking' || state.status === 'voting') {
        showScreen('arena');
        renderArena(state);
    } else if (state.status === 'results') {
        showScreen('results');
        renderResults(state);
    }
}

function renderArena(state) {
    const grid = document.getElementById('responses-grid');
    const inputSec = document.getElementById('input-section');
    const votingSec = document.getElementById('voting-section');

    if (state.status === 'thinking') {
        inputSec.style.opacity = '0.5';
        grid.innerHTML = '<div class="spinner"></div><p style="text-align:center">Models are generating...</p>';
        votingSec.style.display = 'none';
    } else {
        inputSec.style.opacity = '1';

        if (state.responses && state.responses.length > 0) {
            grid.innerHTML = state.responses.map(r => `
                <div class="response-card">
                    <h3>${r.alias}</h3>
                    <p>${escapeHtml(r.reply)}</p>
                </div>
            `).join('');

            votingSec.style.display = 'block';
            renderVoteButtons(state.responses);
        } else {
            // First turn, waiting for message
            grid.innerHTML = '<p style="text-align:center; color: var(--text-secondary)">Type a message above start the round.</p>';
            votingSec.style.display = 'none';
        }
    }
}

function renderVoteButtons(responses) {
    const container = document.getElementById('vote-options');
    container.innerHTML = responses.map(r => `
        <button class="vote-btn" onclick="castVote('${r.alias}')">${r.alias}</button>
    `).join('');
}

async function castVote(alias) {
    await fetch('api/vote/human', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voter_token: sessionToken, agent_alias: alias })
    });
    // Visual feedback
    document.querySelectorAll('.vote-btn').forEach(b => {
        if (b.textContent === alias) b.classList.add('selected');
        b.disabled = true;
    });
}

function renderResults(state) {
    const container = document.getElementById('results-content');

    // Tally Human Votes
    const humanTally = {};
    Object.values(state.human_votes || {}).forEach(alias => {
        humanTally[alias] = (humanTally[alias] || 0) + 1;
    });

    // Tally LLM Votes
    const llmTally = {};
    Object.values(state.llm_votes || {}).forEach(alias => {
        llmTally[alias] = (llmTally[alias] || 0) + 1;
    });

    // Map aliases to real names and times
    // In 'results' state, server sends 'model_name' in responses
    const map = {};
    if (state.responses) {
        state.responses.forEach(r => {
            map[r.alias] = {
                name: r.model_name,
                avg_time: state.avg_timings[r.model_name] || '?'
            };
        });
    }

    const html = `
        <div class="result-column">
            <h3>👥 Human Votes</h3>
            ${renderTallyList(humanTally, map)}
        </div>
        <div class="result-column">
            <h3>🤖 LLM Votes</h3>
            ${renderTallyList(llmTally, map)}
        </div>
    `;

    container.innerHTML = html;
}

function renderTallyList(tally, map) {
    const sorted = Object.entries(tally).sort((a, b) => b[1] - a[1]);

    if (sorted.length === 0) return '<p style="text-align:center; opacity:0.5">No votes cast</p>';

    return sorted.map(([alias, count], i) => {
        const info = map[alias] || { name: 'Unknown', avg_time: '?' };
        return `
        <div class="result-row ${i === 0 ? 'winner' : ''}">
            <div>
                <strong>${alias}</strong> <span style="color:var(--text-secondary)">(${info.name})</span>
                <br>
                <span class="latency-badge">Avg: ${info.avg_time}ms</span>
            </div>
            <div class="result-votes">${count} votes</div>
        </div>
        `;
    }).join('');
}

// --- Buttons ---
document.getElementById('send-btn').addEventListener('click', async () => {
    const msg = document.getElementById('message-input').value;
    if (!msg) return;

    await fetch('api/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'token': sessionToken },
        body: JSON.stringify({ message: msg })
    });
    document.getElementById('message-input').value = '';
});

document.getElementById('reveal-btn').addEventListener('click', async () => {
    await fetch('api/reveal', { headers: { 'token': sessionToken }, method: 'POST' });
});

document.getElementById('next-turn-btn').addEventListener('click', () => {
    // Switch view back to arena to type next message
    // Server status stays 'results' until we send a message?
    // No, server logic needs to handle transition. 
    // But since "Anyone can send next message", we can just show the Arena screen 
    // even if status is results, but purely client side? No.
    // We should probably tell server "we are done viewing results".
    // But simpliest is: User toggles UI to Arena, types message, clicks send.
    // Send -> triggers 'thinking' -> updates everyone.

    // I will manually force show Arena on client side, but really we need a "Reset Status" API?
    // Not strictly needed if /api/send works from any state.
    // But to show the Input box, we must be in Arena screen.
    showScreen('arena');
    // Clear previous responses visually until new state arrives
    document.getElementById('responses-grid').innerHTML = '<p style="text-align:center">Ready for next turn...</p>';
    document.getElementById('voting-section').style.display = 'none';
});

// Utils
function showScreen(id) {
    Object.values(screens).forEach(s => s.classList.remove('active'));
    screens[id].classList.add('active');
}
function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

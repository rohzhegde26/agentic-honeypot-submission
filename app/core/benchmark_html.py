"""
Benchmark Arena HTML Content
"""

BENCHMARK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Benchmark Arena (Fireworks)</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Space+Grotesk:wght@300;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #13131f;
            --accent-primary: #6366f1;
            --accent-secondary: #8b5cf6;
            --text-primary: #ffffff;
            --text-secondary: #a1a1aa;
            --success: #10b981;
            --error: #ef4444;
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow-x: hidden;
        }

        .background-effects {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none;
        }
        .glow-orb { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.15; }
        .orb-1 { top: -10%; left: -10%; width: 50vw; height: 50vw; background: var(--accent-primary); }
        .orb-2 { bottom: -10%; right: -10%; width: 60vw; height: 60vw; background: var(--accent-secondary); }

        .container { width: 90%; max-width: 1200px; margin: 2rem auto; }
        .screen { display: none; animation: fadeIn 0.5s ease; }
        .screen.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

        .glass-panel {
            background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border);
            border-radius: 16px; padding: 2rem; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        #login-screen { text-align: center; max-width: 500px; margin: 0 auto; }
        .setup-form { display: flex; flex-direction: column; gap: 1rem; margin-top: 2rem; }
        input {
            background: rgba(0, 0, 0, 0.3); border: 1px solid var(--glass-border); border-radius: 8px;
            padding: 1rem; color: white; font-family: inherit; font-size: 1rem;
        }

        .btn {
            padding: 0.8rem 1.5rem; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; transition: all 0.2s;
        }
        .btn-primary { background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }
        .btn-secondary { background: rgba(255,255,255,0.1); color: white; }

        .arena-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        .badge { background: rgba(255,255,255,0.1); padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 500; }
        
        .input-section { display: flex; gap: 1rem; margin-bottom: 2rem; }
        #message-input { flex: 1; }

        .responses-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .response-card {
            background: rgba(255,255,255,0.03); border: 1px solid var(--glass-border); border-radius: 12px;
            padding: 1.5rem; transition: transform 0.2s;
        }
        .response-card:hover { transform: translateY(-4px); background: rgba(255,255,255,0.05); }
        .response-card h3 { margin-top: 0; color: var(--accent-primary); font-size: 1.1rem; display: flex; justify-content: space-between; }
        .latency-badge { font-size: 0.75rem; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; color: var(--text-secondary); }

        .voting-section { text-align: center; padding: 2rem; background: var(--glass-bg); border-radius: 16px; margin-top: 2rem; }
        .vote-options { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; margin-top: 1rem; }
        .vote-btn { background: rgba(255,255,255,0.1); border: 1px solid var(--glass-border); color: white; padding: 0.8rem 2rem; border-radius: 8px; cursor: pointer; }
        .vote-btn:hover { background: var(--accent-primary); }
        .vote-btn.selected { background: var(--success); border-color: var(--success); }

        #voters-list li { padding: 0.5rem; background: rgba(255,255,255,0.05); margin-bottom: 0.5rem; border-radius: 4px; list-style: none; }
        
        .results-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
        .result-column h3 { text-align: center; color: var(--accent-secondary); border-bottom: 1px solid var(--glass-border); padding-bottom: 1rem; }
        .result-row { display: flex; justify-content: space-between; padding: 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .result-row.winner { background: rgba(16, 185, 129, 0.1); border-left: 3px solid var(--success); }
        
        .spinner { width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.1); border-top-color: white; border-radius: 50%; animation: spin 1s linear infinite; margin: 1rem auto; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="background-effects">
        <div class="glow-orb orb-1"></div>
        <div class="glow-orb orb-2"></div>
    </div>

    <main class="container">
        <!-- Login Screen -->
        <section id="login-screen" class="screen active">
            <h1>Benchmark <span class="accent">Arena</span></h1>
            <p class="subtitle">Multi-User Blind Voting</p>
            <div class="glass-panel setup-form">
                <input type="password" id="api-key" placeholder="Enter Admin API Key (same as .env)">
                <input type="text" id="nickname" placeholder="Your Nickname">
                <div style="display:flex; gap:10px; align-items:center; color:var(--text-secondary)">
                    <label>Players:</label>
                    <select id="expected-voters" style="background:rgba(0,0,0,0.3); color:white; border:1px solid var(--glass-border); padding:5px; border-radius:4px;">
                        <option value="1">1 (Solo / Auto-Start)</option>
                        <option value="2">2</option>
                        <option value="3">3</option>
                        <option value="4">4</option>
                        <option value="5">5</option>
                    </select>
                </div>
                <button id="join-btn" class="btn btn-primary">Join Session</button>
            </div>
        </section>

        <!-- Lobby Screen -->
        <section id="lobby-screen" class="screen">
            <h2>Waiting Room</h2>
            <div class="glass-panel">
                <p>Connected Voters:</p>
                <ul id="voters-list"></ul>
                <p style="font-size:0.8rem; color:var(--text-secondary); margin-top:10px;">
                    Game will start automatically when <span id="expected-count-display">1</span> players join.
                </p>
                <div class="spinner"></div>
            </div>
        </section>

        <!-- Arena Screen -->
        <section id="arena-screen" class="screen">
            <header class="arena-header">
                <div class="turn-info">
                    <h2>Turn <span id="turn-num">1</span></h2>
                    <span id="status-badge" class="badge">Waiting...</span>
                </div>
                <div class="metrics">
                    <span id="voter-count">0 Voters</span>
                </div>
            </header>

            <!-- Chat Input -->
            <div class="glass-panel input-section" id="input-section">
                <input type="text" id="message-input" placeholder="Type message for all models...">
                <button id="send-btn" class="btn btn-primary">Send to All</button>
            </div>

            <!-- Responses Grid -->
            <div id="responses-grid" class="responses-grid"></div>

            <!-- Voting Section -->
            <div class="voting-section" id="voting-section" style="display:none">
                <h3>Cast Your Vote</h3>
                <div class="vote-options" id="vote-options"></div>
            </div>

            <div class="controls">
                <button id="reveal-btn" class="btn btn-secondary">Reveal Results</button>
            </div>
        </section>

        <!-- Results Screen -->
        <section id="results-screen" class="screen">
            <h1>Turn Results</h1>
            <div id="results-content" class="glass-panel results-grid"></div>
            <button id="next-turn-btn" class="btn btn-primary" style="margin-top:20px; width:100%">Next Turn</button>
        </section>
    </main>

    <script>
        // State
        let sessionToken = localStorage.getItem('benchmark_token');
        let currentTurn = -1;

        // DOM
        const screens = {
            login: document.getElementById('login-screen'),
            lobby: document.getElementById('lobby-screen'),
            arena: document.getElementById('arena-screen'),
            results: document.getElementById('results-screen')
        };

        // Init
        if (sessionToken) { pollState(); } else { 
            showScreen('login');
            const autofillKey = localStorage.getItem('benchmark_api_key_autofill');
            if(autofillKey) document.getElementById('api-key').value = autofillKey;
        }

        // Login
        document.getElementById('join-btn').addEventListener('click', async () => {
            const apiKey = document.getElementById('api-key').value.trim();
            const nickname = document.getElementById('nickname').value.trim();
            const expectedVoters = parseInt(document.getElementById('expected-voters').value);
            
            if (!apiKey || !nickname) return alert("Please enter API Key and Nickname");
            
            try {
                const res = await fetch('/api/benchmark/join', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ api_key: apiKey, nickname, expected_voters: expectedVoters })
                });
                if (!res.ok) throw new Error("Invalid API Key");
                const data = await res.json();
                sessionToken = data.token;
                localStorage.setItem('benchmark_token', sessionToken);
                pollState();
            } catch(e) { alert(e.message); }
        });

        // Polling
        async function pollState() {
            try {
                const res = await fetch('/api/benchmark/poll', { headers: { 'token': sessionToken } });
                if (res.status === 401) {
                    localStorage.removeItem('benchmark_token');
                    sessionToken = null;
                    showScreen('login');
                    return;
                }
                const state = await res.json();
                renderState(state);
                setTimeout(pollState, 1000);
            } catch(e) { console.error(e); setTimeout(pollState, 2000); }
        }

        // Render
        function renderState(state) {
            document.getElementById('status-badge').textContent = state.status.toUpperCase();
            document.getElementById('voters-list').innerHTML = state.voters_names.map(n => `<li>${n}</li>`).join('');
            document.getElementById('voter-count').textContent = `${state.voters_count} Voters`;
            document.getElementById('turn-num').textContent = state.turn + 1;
            document.getElementById('expected-count-display').textContent = state.expected_voters || 1;
            
            if (state.status === 'input') {
                showScreen('arena');
                renderArena(state); // Will clear grid
            }
            else if (state.status === 'waiting') { showScreen('lobby'); }
            else if (state.status === 'thinking' || state.status === 'voting') {
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
            
            if (state.status === 'input') {
                inputSec.style.opacity = '1';
                grid.innerHTML = '<p style="text-align:center; color: var(--text-secondary)">Type a message above to start the round.</p>';
                votingSec.style.display = 'none';
            }
            else if (state.status === 'thinking') {
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
                    grid.innerHTML = '<p style="text-align:center; color: var(--text-secondary)">Waiting for results...</p>';
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
            await fetch('/api/benchmark/vote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'token': sessionToken },
                body: JSON.stringify({ agent_alias: alias })
            });
            document.querySelectorAll('.vote-btn').forEach(b => {
                if(b.textContent === alias) b.classList.add('selected');
                b.disabled = true;
            });
        }

        function renderResults(state) {
            const container = document.getElementById('results-content');
            
            const humanTally = {};
            Object.values(state.human_votes || {}).forEach(alias => humanTally[alias] = (humanTally[alias] || 0) + 1);
            
            const llmTally = {};
            Object.values(state.llm_votes || {}).forEach(alias => llmTally[alias] = (llmTally[alias] || 0) + 1);
            
            const map = {};
            if(state.responses) {
                state.responses.forEach(r => {
                    map[r.alias] = { name: r.model_name, avg_time: state.avg_timings[r.model_name] || '?' };
                });
            }
            
            container.innerHTML = `
                <div class="result-column"><h3>👥 Human Votes</h3>${renderTallyList(humanTally, map)}</div>
                <div class="result-column"><h3>🤖 LLM Votes</h3>${renderTallyList(llmTally, map)}</div>
            `;
        }

        function renderTallyList(tally, map) {
            const sorted = Object.entries(tally).sort((a,b) => b[1] - a[1]);
            if (sorted.length === 0) return '<p style="text-align:center; opacity:0.5">No votes cast</p>';
            return sorted.map(([alias, count], i) => {
                const info = map[alias] || {name: 'Unknown', avg_time: '?'};
                return `<div class="result-row ${i===0?'winner':''}">
                    <div><strong>${alias}</strong> <span style="color:var(--text-secondary)">(${info.name})</span><br>
                    <span class="latency-badge">Avg: ${info.avg_time}ms</span></div>
                    <div class="result-votes">${count} votes</div></div>`;
            }).join('');
        }

        // Actions
        document.getElementById('send-btn').addEventListener('click', async () => {
            const msg = document.getElementById('message-input').value;
            if(!msg) return;
            await fetch('/api/benchmark/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'token': sessionToken },
                body: JSON.stringify({ message: msg })
            });
            document.getElementById('message-input').value = '';
        });

        document.getElementById('reveal-btn').addEventListener('click', async () => {
             await fetch('/api/benchmark/reveal', { headers: { 'token': sessionToken }, method: 'POST' });
        });

        document.getElementById('next-turn-btn').addEventListener('click', async () => {
             await fetch('/api/benchmark/next', { headers: { 'token': sessionToken }, method: 'POST' });
        });

        function showScreen(id) { Object.values(screens).forEach(s => s.classList.remove('active')); screens[id].classList.add('active'); }
        function escapeHtml(text) { if (!text) return ''; return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
    </script>
</body>
</html>
"""

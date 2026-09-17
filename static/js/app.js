/* Stepping Stones — dashboard logic. Charts are inline SVG, no libraries. */

const state = { days: '', status: '', category: '', search: '' };
let searchTimer = null;

const CAT_ICON = {
    flow: 'fa-water',
    discourse: 'fa-comment-dots',
    accuracy: 'fa-circle-check',
    nuance: 'fa-feather',
    habit: 'fa-repeat',
};

const STATUS_LABEL = { todo: 'To do', working: 'Working on it', done: 'Done' };
const NEXT_STATUS = { todo: 'working', working: 'done', done: 'todo' };

document.addEventListener('DOMContentLoaded', () => {
    bindChips('.range .chip', btn => { state.days = btn.dataset.days; loadOverview(); });
    bindChips('#status-tabs .chip', btn => { state.status = btn.dataset.status; loadStudy(); });
    bindChips('#cat-tabs .chip', btn => { state.category = btn.dataset.category; loadStudy(); });

    document.getElementById('search').addEventListener('input', e => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => { state.search = e.target.value.trim(); loadStudy(); }, 300);
    });

    loadOverview();
    loadStudy();
});

function bindChips(selector, handler) {
    const group = document.querySelectorAll(selector);
    group.forEach(btn => btn.addEventListener('click', () => {
        group.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        handler(btn);
    }));
}

/* ------------------------------------------------------------- overview */

async function loadOverview() {
    const qs = state.days ? `?days=${state.days}` : '';
    try {
        const res = await fetch(`/api/overview${qs}`);
        if (!res.ok) throw new Error('overview failed');
        const d = await res.json();

        document.getElementById('source-note').textContent =
            d.total_sessions_all
                ? `Your data covers ${d.data_from} to ${d.data_to} — ${d.total_sessions_all} sessions in total. Showing ${d.sessions} of them.`
                : 'No data loaded yet.';

        setText('hero-pebbles', d.pebbles);
        setText('hero-sessions', d.sessions);
        setText('hero-words', d.words.toLocaleString());
        setText('hero-study', d.study_total);
        setText('hero-done', d.study_done);

        renderTower(d.pebbles);
        renderCategories(d.categories);
        renderPhraseChart('chart-filler', d.fillers, 1);
        renderPhraseChart('chart-hedge', d.hedges, 2);
        renderRecent(d.recent);
    } catch (err) {
        console.error(err);
        toast('Could not load your dashboard.', 'bad');
    }
}

function setText(id, v) { document.getElementById(id).textContent = v; }

// 돌탑: 세션 수를 눈에 보이는 더미로. 최대 24개까지 그리고 나머지는 숫자로 둔다.
function renderTower(n) {
    const tower = document.getElementById('tower');
    const shown = Math.min(n, 24);
    tower.innerHTML = Array.from({ length: shown }, (_, i) => {
        const w = 26 + ((i * 7) % 22);
        return `<span class="stone" style="width:${w}px;animation-delay:${i * 22}ms"></span>`;
    }).join('');
}

/* ------------------------------------------------- five category modules */

function renderCategories(cats) {
    const grid = document.getElementById('cat-grid');
    grid.innerHTML = '';

    cats.forEach(c => {
        const card = document.createElement('article');
        card.className = `card cat cat-${c.key}${c.measured ? '' : ' not-measured'}`;

        let body;
        if (!c.measured) {
            body = `<p class="cat-empty">
                        <i class="fa-regular fa-circle-question"></i>
                        We cannot measure this from your text yet.
                    </p>`;
        } else {
            body = `
                <div class="cat-value">
                    <span class="num">${c.value}</span>
                    <span class="unit">${escapeHtml(c.unit)}</span>
                    ${changeBadge(c)}
                </div>
                ${sparkline(c)}`;
        }

        card.innerHTML = `
            <div class="cat-head">
                <span class="cat-rank">${c.rank}</span>
                <i class="fa-solid ${CAT_ICON[c.key] || 'fa-circle'}" aria-hidden="true"></i>
                <div>
                    <h3>${escapeHtml(c.name)}</h3>
                    <p>${escapeHtml(c.blurb)}</p>
                </div>
            </div>
            ${body}`;
        grid.appendChild(card);
    });
}

function changeBadge(c) {
    if (c.change === null || c.change === 0) return '<span class="badge flat">no change</span>';
    const up = c.change > 0;
    // direction: 'up' = 높을수록 좋음, 'down' = 낮을수록 좋음, 'range' = 판단하지 않음
    let cls = 'flat';
    if (c.direction === 'up') cls = up ? 'good' : 'watch';
    if (c.direction === 'down') cls = up ? 'watch' : 'good';
    const arrow = up ? '▲' : '▼';
    return `<span class="badge ${cls}">${arrow} ${Math.abs(c.change)} vs earlier</span>`;
}

// 스파크라인: 계열이 하나뿐이라 범례 없이 끝점만 직접 라벨한다.
function sparkline(c) {
    const pts = c.trend || [];
    if (pts.length < 2) return '<p class="cat-empty">Not enough sessions yet.</p>';

    const w = 300, h = 74, pad = 10;
    const vals = pts.map(p => p.value);
    const min = Math.min(...vals), max = Math.max(...vals);
    const span = (max - min) || 1;
    const x = i => pad + (i * (w - pad * 2)) / (pts.length - 1);
    const y = v => pad + (h - pad * 2) * (1 - (v - min) / span);

    const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(' ');
    const area = `${line} L${x(pts.length - 1).toFixed(1)},${h - pad} L${x(0).toFixed(1)},${h - pad} Z`;
    const last = pts[pts.length - 1];

    return `
        <svg class="spark" viewBox="0 0 ${w} ${h}" role="img"
             aria-label="${pts.map(p => `${p.label}: ${p.value}`).join(', ')}">
            <path class="spark-area" d="${area}"></path>
            <path class="spark-line" d="${line}"></path>
            ${pts.map((p, i) => `<circle class="spark-dot" cx="${x(i).toFixed(1)}" cy="${y(p.value).toFixed(1)}" r="3"><title>${p.label}: ${p.value}</title></circle>`).join('')}
        </svg>
        <div class="spark-foot"><span>${escapeHtml(pts[0].label)}</span><span>${escapeHtml(last.label)} · ${last.value}</span></div>`;
}

/* ------------------------------------------------------------- 빈도 차트 */

function renderPhraseChart(elId, rows, slot) {
    const el = document.getElementById(elId);
    if (!rows || !rows.length) {
        el.innerHTML = '<p class="cat-empty">Nothing found in this range.</p>';
        return;
    }
    const max = Math.max(...rows.map(r => r.total));
    el.innerHTML = `
        <ul class="bars">
            ${rows.map(r => `
                <li>
                    <span class="bar-label">${escapeHtml(r.phrase)}</span>
                    <span class="bar-track">
                        <span class="bar-fill s${slot}" style="width:${(r.total / max) * 100}%"></span>
                    </span>
                    <span class="bar-num">${r.total}</span>
                </li>`).join('')}
        </ul>`;
}

function renderRecent(rows) {
    document.getElementById('recent-body').innerHTML = (rows || []).map(r => `
        <tr>
            <td class="mono">${escapeHtml(r.date)}</td>
            <td>${escapeHtml(r.title)}</td>
            <td><span class="tag">${escapeHtml((r.tag || '').replace('keep_', ''))}</span></td>
            <td class="num">${r.words}</td>
        </tr>`).join('');
}

/* ----------------------------------------------------------- study list */

async function loadStudy() {
    const p = new URLSearchParams();
    if (state.status) p.append('status', state.status);
    if (state.category) p.append('category', state.category);
    if (state.search) p.append('search', state.search);

    try {
        const res = await fetch(`/api/study?${p}`);
        if (!res.ok) throw new Error('study failed');
        renderStudy(await res.json());
    } catch (err) {
        console.error(err);
        toast('Could not load your study list.', 'bad');
    }
}

function renderStudy(items) {
    const list = document.getElementById('study-list');
    const empty = document.getElementById('study-empty');
    list.innerHTML = '';

    if (!items.length) { empty.hidden = false; return; }
    empty.hidden = true;

    items.forEach(it => {
        const row = document.createElement('article');
        row.className = `card study st-${it.status}`;
        row.innerHTML = `
            <button class="mark-btn ${it.status}" data-id="${it.id}" data-next="${NEXT_STATUS[it.status]}"
                    title="Click to change: To do → Working on it → Done">
                ${it.status === 'done' ? '<i class="fa-solid fa-check"></i>'
                  : it.status === 'working' ? '<i class="fa-solid fa-spinner"></i>'
                  : '<i class="fa-regular fa-circle"></i>'}
            </button>
            <div class="study-body">
                <div class="study-head">
                    <h4>${escapeHtml(it.title)}</h4>
                    <span class="pill cat-${it.category}">${escapeHtml(it.category)}</span>
                    <span class="pill status ${it.status}">${STATUS_LABEL[it.status]}</span>
                </div>
                <p class="study-detail">${escapeHtml(it.detail)}</p>
                <p class="study-evidence">
                    <i class="fa-solid fa-chart-simple"></i> ${escapeHtml(it.evidence)}
                    ${it.source_title ? ` · from “${escapeHtml(it.source_title)}”` : ''}
                </p>
            </div>`;
        list.appendChild(row);
    });

    list.querySelectorAll('.mark-btn').forEach(btn => {
        btn.addEventListener('click', () => setStatus(btn.dataset.id, btn.dataset.next));
    });
}

async function setStatus(id, next) {
    try {
        const res = await fetch(`/api/study/${id}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: next }),
        });
        if (!res.ok) throw new Error('status failed');
        await Promise.all([loadStudy(), loadOverview()]);
        toast(`Moved to “${STATUS_LABEL[next]}”.`, 'good');
    } catch (err) {
        console.error(err);
        toast('Could not save that change.', 'bad');
    }
}

/* ------------------------------------------------------------------ util */

function toast(msg, kind = 'info') {
    const box = document.getElementById('toasts');
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 2600);
}

function escapeHtml(t) {
    if (t === null || t === undefined) return '';
    return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

/* ==========================================================================
   Stepping Stones - English Coaching Dashboard
   ========================================================================== */

const state = {
    days: 30,
    status: '',
    type: '',
    coach: '',
    search: '',
};

let searchTimer = null;

const TYPE_LABEL = {
    vocab: '단어 · 구동사',
    expression: '표현',
    grammar: '문법',
    pronunciation: '발음',
};

const STATUS_LABEL = { new: '새 항목', learning: '학습 중', mastered: '마스터' };
const STATUS_ORDER = ['new', 'learning', 'mastered'];
const NEXT_STATUS = { new: 'learning', learning: 'mastered', mastered: 'new' };

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('f-date').value = new Date().toISOString().split('T')[0];

    document.querySelectorAll('.range-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.range-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.days = Number(btn.dataset.days);
            refreshAll();
        });
    });

    document.querySelectorAll('#status-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#status-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.status = btn.dataset.status;
            loadItems();
        });
    });

    document.getElementById('type-filter').addEventListener('change', e => {
        state.type = e.target.value;
        loadItems();
    });
    document.getElementById('coach-filter').addEventListener('change', e => {
        state.coach = e.target.value;
        loadItems();
    });

    const searchInput = document.getElementById('search-input');
    const clearBtn = document.getElementById('clear-search-btn');
    searchInput.addEventListener('input', () => {
        clearBtn.hidden = !searchInput.value;
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            state.search = searchInput.value.trim();
            loadItems();
        }, 300);
    });
    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.hidden = true;
        state.search = '';
        loadItems();
    });

    document.getElementById('add-btn').addEventListener('click', openModal);
    document.getElementById('close-modal').addEventListener('click', closeModal);
    document.getElementById('cancel-modal').addEventListener('click', closeModal);
    document.getElementById('item-form').addEventListener('submit', submitItem);

    refreshAll();
});

function refreshAll() {
    loadAnalytics();
    loadItems();
}

/* ---------------------------------------------------------------- 데이터 */

async function loadAnalytics() {
    try {
        const res = await fetch(`/api/analytics?days=${state.days}`);
        if (!res.ok) throw new Error('analytics failed');
        const a = await res.json();

        document.getElementById('sample-banner').hidden = !a.is_sample_only;

        document.getElementById('stat-items').textContent = a.total_items;
        document.getElementById('stat-sessions').textContent = a.total_sessions;
        document.getElementById('stat-minutes').textContent = formatMinutes(a.study_minutes);
        document.getElementById('stat-rate').textContent = `${a.mastery_rate}%`;

        renderStones(a);
        renderWeekly(a.weekly);
        renderTypes(a.by_type);
        renderStatus(a.by_status, a.total_items);
        renderCoachSplit(a.by_coach);
    } catch (err) {
        console.error(err);
        showToast('분석 데이터를 불러오지 못했습니다.', 'danger');
    }
}

async function loadItems() {
    const params = new URLSearchParams({ days: state.days });
    if (state.search) params.append('search', state.search);
    if (state.status) params.append('status', state.status);
    if (state.type) params.append('type', state.type);
    if (state.coach) params.append('coach', state.coach);

    try {
        const res = await fetch(`/api/items?${params}`);
        if (!res.ok) throw new Error('items failed');
        renderItems(await res.json());
    } catch (err) {
        console.error(err);
        showToast('학습 목록을 불러오지 못했습니다.', 'danger');
    }
}

/* ------------------------------------------------------- Stepping Stones */

function renderStones(a) {
    const cur = a.current_stone || {};
    const next = a.next_stone;

    document.getElementById('stone-mastered').textContent = a.mastered_total;
    document.getElementById('stone-name').textContent =
        cur.reached ? `${cur.no}. ${cur.name}` : '시작 전';
    document.getElementById('stone-caption').textContent = next
        ? `${next.name}(${next.label})까지 ${next.remaining}개 남았습니다.`
        : '마지막 단계에 도달했습니다.';

    const track = document.getElementById('stone-track');
    track.innerHTML = '';

    a.stones.forEach(s => {
        const done = a.mastered_total >= s.target;
        const active = !done && (!next || next.no === s.no);
        const li = document.createElement('li');
        li.className = `stone ${done ? 'done' : ''} ${active ? 'active' : ''}`;
        li.innerHTML = `
            <span class="stone-dot">${done ? '<i class="fa-solid fa-check"></i>' : s.no}</span>
            <span class="stone-name">${escapeHtml(s.name)}</span>
            <span class="stone-target">${s.target}개</span>
        `;
        track.appendChild(li);
    });

    // 현재 구간 진행률
    const pct = cur.percent || 0;
    track.style.setProperty('--stone-progress', `${pct}%`);
}

/* ------------------------------------------------------------------ 차트 */

// 주차별 학습 항목 — 단일 계열이므로 범례 없이 직접 라벨만 단다.
function renderWeekly(weekly) {
    const w = 520, h = 210, pad = { t: 24, r: 12, b: 34, l: 12 };
    const max = Math.max(1, ...weekly.map(d => d.items));
    const plotH = h - pad.t - pad.b;
    const bw = (w - pad.l - pad.r) / weekly.length;
    const barW = Math.min(64, bw - 18);

    const bars = weekly.map((d, i) => {
        const bh = Math.max(d.items > 0 ? 4 : 0, (d.items / max) * plotH);
        const x = pad.l + i * bw + (bw - barW) / 2;
        const y = pad.t + plotH - bh;
        return `
            <g class="bar-group" tabindex="0" role="listitem"
               aria-label="${d.label} 주 ${d.items}개, 세션 ${d.sessions}회">
                <rect class="bar-hit" x="${pad.l + i * bw}" y="${pad.t}" width="${bw}" height="${plotH}"></rect>
                <rect class="bar" x="${x}" y="${y}" width="${barW}" height="${bh}" rx="4"></rect>
                <text class="bar-value" x="${x + barW / 2}" y="${y - 8}">${d.items}</text>
                <text class="axis-label" x="${x + barW / 2}" y="${h - 12}">${d.label}</text>
                <title>${d.label} 주 · 항목 ${d.items}개 · 세션 ${d.sessions}회</title>
            </g>`;
    }).join('');

    document.getElementById('chart-weekly').innerHTML = `
        <svg viewBox="0 0 ${w} ${h}" class="chart chart-weekly" role="list"
             aria-label="주차별 학습 항목 수">
            <line class="axis-line" x1="${pad.l}" y1="${pad.t + plotH}" x2="${w - pad.r}" y2="${pad.t + plotH}"></line>
            ${bars}
        </svg>`;
}

// 유형별 분포 — 가로 막대에 값 직접 표기.
function renderTypes(byType) {
    const entries = Object.entries(byType);
    const max = Math.max(1, ...entries.map(([, v]) => v));

    document.getElementById('chart-type').innerHTML = `
        <ul class="hbar-list">
            ${entries.map(([k, v], i) => `
                <li class="hbar-row">
                    <span class="hbar-label">
                        <span class="swatch swatch-${i + 1}" aria-hidden="true"></span>
                        ${escapeHtml(TYPE_LABEL[k] || k)}
                    </span>
                    <span class="hbar-track">
                        <span class="hbar-fill fill-${i + 1}" style="width:${(v / max) * 100}%"></span>
                    </span>
                    <span class="hbar-value">${v}</span>
                </li>`).join('')}
        </ul>`;
}

// 숙련도 구성 — 상태 색은 예약 팔레트를 쓰고 라벨을 항상 붙인다.
function renderStatus(byStatus, total) {
    const segs = STATUS_ORDER.map(k => ({ key: k, value: byStatus[k] || 0 }));
    const sum = total || segs.reduce((a, s) => a + s.value, 0) || 1;

    document.getElementById('chart-status').innerHTML = `
        <div class="stack-bar" role="img"
             aria-label="${segs.map(s => `${STATUS_LABEL[s.key]} ${s.value}개`).join(', ')}">
            ${segs.filter(s => s.value > 0).map(s => `
                <span class="stack-seg seg-${s.key}" style="flex:${s.value}">
                    <span class="seg-num">${s.value}</span>
                </span>`).join('')}
        </div>
        <ul class="legend">
            ${segs.map(s => `
                <li><span class="swatch seg-${s.key}" aria-hidden="true"></span>
                    ${STATUS_LABEL[s.key]} <b>${s.value}</b>
                    <span class="muted">${Math.round(s.value / sum * 100)}%</span></li>`).join('')}
        </ul>`;
}

function renderCoachSplit(byCoach) {
    const entries = Object.entries(byCoach);
    document.getElementById('coach-split').innerHTML = entries.map(([name, v], i) => `
        <div class="coach-chip">
            <span class="swatch swatch-${i + 1}" aria-hidden="true"></span>
            <span class="coach-name">${escapeHtml(name)}</span>
            <b>${v}</b><span class="muted">개</span>
        </div>`).join('');
}

/* ------------------------------------------------------------ 학습 리스트 */

function renderItems(items) {
    const list = document.getElementById('item-list');
    const empty = document.getElementById('empty-state');
    list.innerHTML = '';

    if (!items.length) {
        empty.hidden = false;
        return;
    }
    empty.hidden = true;

    items.forEach(it => {
        const card = document.createElement('article');
        card.className = `item-card status-${it.status}`;
        card.innerHTML = `
            <button class="status-toggle seg-${it.status}"
                    title="클릭하면 다음 단계로 (새 항목 → 학습 중 → 마스터)"
                    data-id="${it.id}" data-next="${NEXT_STATUS[it.status]}">
                ${it.status === 'mastered' ? '<i class="fa-solid fa-check"></i>'
                  : it.status === 'learning' ? '<i class="fa-solid fa-rotate"></i>'
                  : '<i class="fa-regular fa-circle"></i>'}
            </button>
            <div class="item-body">
                <div class="item-head">
                    <h4>${escapeHtml(it.term)}</h4>
                    <span class="badge badge-type">${escapeHtml(TYPE_LABEL[it.item_type] || it.item_type)}</span>
                    ${it.coach ? `<span class="badge badge-coach">${escapeHtml(it.coach)}</span>` : ''}
                    <span class="badge seg-${it.status}">${STATUS_LABEL[it.status]}</span>
                </div>
                ${it.meaning ? `<p class="item-meaning">${escapeHtml(it.meaning)}</p>` : ''}
                ${it.example ? `<p class="item-example">“${escapeHtml(it.example)}”</p>` : ''}
                <div class="item-foot">
                    ${it.source_date ? `<span><i class="fa-regular fa-calendar"></i> ${escapeHtml(it.source_date)}</span>` : ''}
                    ${it.tags ? escapeHtml(it.tags).split(',').map(t =>
                        `<span class="tag">#${t.trim()}</span>`).join('') : ''}
                </div>
            </div>
            <button class="icon-btn btn-delete" data-del="${it.id}" title="삭제">
                <i class="fa-solid fa-trash-can"></i>
            </button>`;
        list.appendChild(card);
    });

    list.querySelectorAll('.status-toggle').forEach(btn => {
        btn.addEventListener('click', () => cycleStatus(btn.dataset.id, btn.dataset.next));
    });
    list.querySelectorAll('[data-del]').forEach(btn => {
        btn.addEventListener('click', () => deleteItem(btn.dataset.del));
    });
}

async function cycleStatus(id, next) {
    try {
        const res = await fetch(`/api/items/${id}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: next }),
        });
        if (!res.ok) throw new Error('status failed');
        await refreshAll();
        showToast(`${STATUS_LABEL[next]}(으)로 변경했습니다.`, 'success');
    } catch (err) {
        console.error(err);
        showToast('상태 변경에 실패했습니다.', 'danger');
    }
}

async function deleteItem(id) {
    if (!confirm('이 학습 항목을 삭제할까요?')) return;
    try {
        const res = await fetch(`/api/items/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('delete failed');
        await refreshAll();
        showToast('삭제했습니다.', 'info');
    } catch (err) {
        console.error(err);
        showToast('삭제에 실패했습니다.', 'danger');
    }
}

/* ------------------------------------------------------------------ 모달 */

function openModal() {
    document.getElementById('item-form').reset();
    document.getElementById('f-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('item-modal').classList.add('active');
}

function closeModal() {
    document.getElementById('item-modal').classList.remove('active');
}

async function submitItem(e) {
    e.preventDefault();
    const payload = {
        term: document.getElementById('f-term').value.trim(),
        meaning: document.getElementById('f-meaning').value.trim(),
        example: document.getElementById('f-example').value.trim(),
        item_type: document.getElementById('f-type').value,
        coach: document.getElementById('f-coach').value,
        tags: document.getElementById('f-tags').value.trim(),
        source_date: document.getElementById('f-date').value,
    };
    if (!payload.term) return;

    try {
        const res = await fetch('/api/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('create failed');
        closeModal();
        await refreshAll();
        showToast('학습 항목을 추가했습니다.', 'success');
    } catch (err) {
        console.error(err);
        showToast('저장 중 오류가 발생했습니다.', 'danger');
    }
}

/* ------------------------------------------------------------------ 유틸 */

function formatMinutes(m) {
    if (!m) return '0분';
    const h = Math.floor(m / 60);
    return h ? `${h}시간 ${m % 60}분` : `${m}분`;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? 'fa-circle-check'
        : type === 'danger' ? 'fa-circle-exclamation' : 'fa-circle-info';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 2800);
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

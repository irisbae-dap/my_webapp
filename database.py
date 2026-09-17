"""Stepping Stones dashboard - data layer.

DATABASE_URL(Supabase Postgres)이 있으면 Postgres를, 없으면 로컬 SQLite를 쓴다.

데이터 원본: Google Drive `7_english_corpus.md`
(Iris의 실제 영어 작성 + 코치 피드백 93개 대화, 2023-03 ~ 2026-02).
지표는 모두 Iris 본인 발화에서만 계산한다. 코치 답변 텍스트는 제외한다.
"""

import os
import sqlite3
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
elif os.environ.get('VERCEL'):
    SQLITE_FILE = os.path.join('/tmp', 'steppingstones.db')
else:
    SQLITE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'steppingstones.db')


# Stepping Stones 5-category 분석 모델 (05-project-stepping-stones.md, v2 기준).
# measured=False 인 카테고리는 원문만으로 계산할 수 없어 값을 지어내지 않는다.
CATEGORIES = [
    {
        'key': 'flow', 'rank': 1,
        'name': 'Flow & Thought Process',
        'blurb': 'How long and how varied your sentences are.',
        'metric': 'avg_sentence_len', 'unit': 'words / sentence',
        'direction': 'range', 'measured': True,
    },
    {
        'key': 'discourse', 'rank': 2,
        'name': 'Discourse & Voice',
        'blurb': 'How often you soften what you say (hedging).',
        'metric': 'hedge_per100', 'unit': 'per 100 words',
        'direction': 'down', 'measured': True,
    },
    {
        'key': 'accuracy', 'rank': 3,
        'name': 'Accuracy',
        'blurb': 'Grammar and word errors. Not measured yet.',
        'metric': None, 'unit': '',
        'direction': 'down', 'measured': False,
    },
    {
        'key': 'nuance', 'rank': 4,
        'name': 'Nuance & Lexical',
        'blurb': 'How many different words you use.',
        'metric': 'lexical_diversity', 'unit': '% unique words',
        'direction': 'up', 'measured': True,
    },
    {
        'key': 'habit', 'rank': 5,
        'name': 'Habit Analysis',
        'blurb': 'Filler words you repeat.',
        'metric': 'filler_per100', 'unit': 'per 100 words',
        'direction': 'down', 'measured': True,
    },
]

STATUSES = ('todo', 'working', 'done')


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _q(sql):
    return sql.replace('?', '%s') if USE_POSTGRES else sql


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


def _one(cur):
    row = cur.fetchone()
    return dict(row) if row else None


# --------------------------------------------------------------------------
# 스키마
# --------------------------------------------------------------------------

def init_db():
    serial = 'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'
    real = 'DOUBLE PRECISION' if USE_POSTGRES else 'REAL'

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS sessions (
                id {serial},
                sid TEXT UNIQUE,
                session_date TEXT NOT NULL,
                title TEXT DEFAULT '',
                tag TEXT DEFAULT '',
                word_count INTEGER DEFAULT 0,
                turn_count INTEGER DEFAULT 0,
                sentence_count INTEGER DEFAULT 0,
                unique_words INTEGER DEFAULT 0,
                avg_sentence_len {real} DEFAULT 0,
                sentence_len_sd {real} DEFAULT 0,
                lexical_diversity {real} DEFAULT 0,
                long_word_ratio {real} DEFAULT 0,
                filler_count INTEGER DEFAULT 0,
                filler_per100 {real} DEFAULT 0,
                hedge_count INTEGER DEFAULT 0,
                hedge_per100 {real} DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS patterns (
                id {serial},
                sid TEXT,
                session_date TEXT,
                kind TEXT NOT NULL,
                phrase TEXT NOT NULL,
                count INTEGER DEFAULT 0
            )
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS study_items (
                id {serial},
                kind TEXT NOT NULL DEFAULT 'habit',
                category TEXT NOT NULL DEFAULT 'habit',
                title TEXT NOT NULL,
                detail TEXT DEFAULT '',
                evidence TEXT DEFAULT '',
                source_date TEXT DEFAULT '',
                source_title TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'todo',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        conn.commit()
    finally:
        conn.close()


def wipe_all():
    conn = get_db()
    try:
        cur = conn.cursor()
        for t in ('patterns', 'study_items', 'sessions'):
            cur.execute(f'DELETE FROM {t}')
        conn.commit()
    finally:
        conn.close()


def session_count():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) AS n FROM sessions')
        return _one(cur)['n']
    finally:
        conn.close()


# --------------------------------------------------------------------------
# 적재
# --------------------------------------------------------------------------

SESSION_COLS = ('sid', 'session_date', 'title', 'tag', 'word_count', 'turn_count',
                'sentence_count', 'unique_words', 'avg_sentence_len', 'sentence_len_sd',
                'lexical_diversity', 'long_word_ratio', 'filler_count', 'filler_per100',
                'hedge_count', 'hedge_per100')


def load_dataset(payload, replace=True):
    """추출기가 만든 JSON을 통째로 적재한다."""
    if replace:
        wipe_all()

    now = datetime.now().isoformat()
    conn = get_db()
    try:
        cur = conn.cursor()

        cols = ', '.join(SESSION_COLS) + ', created_at'
        marks = ', '.join(['?'] * (len(SESSION_COLS) + 1))
        for s in payload.get('sessions', []):
            cur.execute(_q(f'INSERT INTO sessions ({cols}) VALUES ({marks})'),
                        tuple(s.get(c, 0 if c not in ('sid', 'session_date', 'title', 'tag')
                                    else '') for c in SESSION_COLS) + (now,))

        for p in payload.get('patterns', []):
            cur.execute(_q('INSERT INTO patterns (sid, session_date, kind, phrase, count)'
                           ' VALUES (?, ?, ?, ?, ?)'),
                        (p['sid'], p['session_date'], p['kind'], p['phrase'], p['count']))

        for it in payload.get('study_items', []):
            cur.execute(_q('INSERT INTO study_items (kind, category, title, detail, evidence,'
                           ' source_date, source_title, status, created_at, updated_at)'
                           ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'),
                        (it.get('kind', 'habit'), it.get('category', 'habit'), it['title'],
                         it.get('detail', ''), it.get('evidence', ''),
                         it.get('source_date', ''), it.get('source_title', ''),
                         it.get('status', 'todo'), now, now))
        conn.commit()
    finally:
        conn.close()

    return {'sessions': len(payload.get('sessions', [])),
            'patterns': len(payload.get('patterns', [])),
            'study_items': len(payload.get('study_items', []))}


# --------------------------------------------------------------------------
# 조회
# --------------------------------------------------------------------------

def data_range():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('SELECT MIN(session_date) AS a, MAX(session_date) AS b,'
                    ' COUNT(*) AS n FROM sessions')
        return _one(cur) or {'a': None, 'b': None, 'n': 0}
    finally:
        conn.close()


def _window(days):
    """데이터의 마지막 날짜를 기준으로 창을 잡는다.

    오늘 기준으로 자르면 코퍼스가 2026-02에서 끝나 화면이 비어버린다.
    """
    r = data_range()
    if not r['b']:
        return '0000-00-00', '9999-99-99'
    end = datetime.strptime(r['b'], '%Y-%m-%d').date()
    if not days:
        return '0000-00-00', r['b']
    start = end - timedelta(days=int(days) - 1)
    return start.strftime('%Y-%m-%d'), r['b']


def fetch_sessions(days=None):
    lo, hi = _window(days)
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('SELECT * FROM sessions WHERE session_date >= ? AND session_date <= ?'
                       ' ORDER BY session_date ASC, id ASC'), (lo, hi))
        return _rows(cur)
    finally:
        conn.close()


def fetch_patterns(kind, days=None, limit=8):
    lo, hi = _window(days)
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('SELECT phrase, SUM(count) AS total FROM patterns'
                       ' WHERE kind = ? AND session_date >= ? AND session_date <= ?'
                       ' GROUP BY phrase ORDER BY total DESC'), (kind, lo, hi))
        rows = _rows(cur)
        return [{'phrase': r['phrase'], 'total': int(r['total'])} for r in rows[:limit]]
    finally:
        conn.close()


def fetch_study_items(status='', category='', search=''):
    query = 'SELECT * FROM study_items WHERE 1=1'
    params = []
    if status:
        query += ' AND status = ?'
        params.append(status)
    if category:
        query += ' AND category = ?'
        params.append(category)
    if search:
        query += ' AND (title LIKE ? OR detail LIKE ? OR evidence LIKE ?)'
        params.extend([f'%{search}%'] * 3)
    query += (" ORDER BY CASE status WHEN 'todo' THEN 1 WHEN 'working' THEN 2 ELSE 3 END,"
              " id ASC")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q(query), params)
        return _rows(cur)
    finally:
        conn.close()


def get_study_item(item_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('SELECT * FROM study_items WHERE id = ?'), (item_id,))
        return _one(cur)
    finally:
        conn.close()


def set_study_status(item_id, status):
    if status not in STATUSES:
        return False
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('UPDATE study_items SET status = ?, updated_at = ? WHERE id = ?'),
                    (status, datetime.now().isoformat(), item_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# --------------------------------------------------------------------------
# 분석
# --------------------------------------------------------------------------

def _avg(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _trend(sessions, metric, buckets=6):
    """세션을 시간순 n구간으로 나눠 구간 평균을 낸다 (성장 추이용)."""
    if not sessions:
        return []
    size = max(1, -(-len(sessions) // buckets))
    out = []
    for i in range(0, len(sessions), size):
        grp = sessions[i:i + size]
        out.append({
            'label': grp[0]['session_date'][2:7].replace('-', '/'),
            'value': _avg([g.get(metric) for g in grp]),
            'sessions': len(grp),
        })
    return out[-buckets:]


def get_overview(days=None):
    sessions = fetch_sessions(days)
    rng = data_range()

    cats = []
    for c in CATEGORIES:
        entry = {k: c[k] for k in ('key', 'rank', 'name', 'blurb', 'unit',
                                   'direction', 'measured')}
        if c['measured'] and sessions:
            metric = c['metric']
            entry['value'] = _avg([s.get(metric) for s in sessions])
            entry['trend'] = _trend(sessions, metric)
            first_half = sessions[:max(1, len(sessions) // 2)]
            second_half = sessions[max(1, len(sessions) // 2):] or first_half
            a, b = _avg([s.get(metric) for s in first_half]), _avg([s.get(metric) for s in second_half])
            entry['change'] = round(b - a, 2)
        else:
            entry['value'] = None
            entry['trend'] = []
            entry['change'] = None
        cats.append(entry)

    items = fetch_study_items()
    done = sum(1 for i in items if i['status'] == 'done')

    return {
        'window_days': days,
        'data_from': rng['a'],
        'data_to': rng['b'],
        'total_sessions_all': rng['n'],
        'sessions': len(sessions),
        'words': sum(int(s['word_count'] or 0) for s in sessions),
        'pebbles': len(sessions),
        'study_total': len(items),
        'study_done': done,
        'categories': cats,
        'fillers': fetch_patterns('filler', days),
        'hedges': fetch_patterns('hedge', days),
        'volume_trend': _trend(sessions, 'word_count'),
        'recent': [
            {'date': s['session_date'], 'title': s['title'], 'tag': s['tag'],
             'words': s['word_count']}
            for s in list(reversed(sessions))[:8]
        ],
    }

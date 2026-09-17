"""Stepping Stones 학습 대시보드의 데이터 계층.

DATABASE_URL(Supabase Postgres)이 있으면 Postgres를, 없으면 로컬 SQLite를 쓴다.
덕분에 배포 환경은 데이터가 영구 보존되고, 로컬 개발은 설정 없이 그대로 돌아간다.
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
    # 서버리스는 프로젝트 디렉터리가 읽기 전용이라 /tmp 를 쓴다.
    SQLITE_FILE = os.path.join('/tmp', 'steppingstones.db')
else:
    SQLITE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'steppingstones.db')

COACHES = ('Molly', 'Bill')
ITEM_TYPES = ('vocab', 'expression', 'grammar', 'pronunciation')
STATUSES = ('new', 'learning', 'mastered')

# Stepping Stones 단계 정의. 누적 mastered 항목 수를 기준으로 삼는다.
# 실제 Stepping Stones 기준이 확정되면 이 표만 고치면 전체 대시보드에 반영된다.
STONES = [
    {'no': 1, 'name': 'Foundation', 'label': '기초 다지기', 'target': 20},
    {'no': 2, 'name': 'Momentum', 'label': '흐름 만들기', 'target': 50},
    {'no': 3, 'name': 'Fluency', 'label': '유창성 구간', 'target': 100},
    {'no': 4, 'name': 'Nuance', 'label': '뉘앙스 감각', 'target': 180},
    {'no': 5, 'name': 'Mastery', 'label': '자유로운 표현', 'target': 300},
]


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _q(sql):
    """플레이스홀더를 드라이버에 맞게 변환한다 (sqlite '?' -> psycopg2 '%s')."""
    return sql.replace('?', '%s') if USE_POSTGRES else sql


def _rows(cursor):
    return [dict(r) for r in cursor.fetchall()]


def _one(cursor):
    row = cursor.fetchone()
    return dict(row) if row else None


# --------------------------------------------------------------------------
# 스키마
# --------------------------------------------------------------------------

def init_db():
    serial = 'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS sessions (
                id {serial},
                session_date TEXT NOT NULL,
                coach TEXT NOT NULL,
                topic TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                duration_min INTEGER DEFAULT 0,
                is_sample INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS items (
                id {serial},
                session_id INTEGER,
                item_type TEXT NOT NULL DEFAULT 'vocab',
                term TEXT NOT NULL,
                meaning TEXT DEFAULT '',
                example TEXT DEFAULT '',
                coach TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'new',
                tags TEXT DEFAULT '',
                source_date TEXT DEFAULT '',
                is_sample INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        conn.commit()
    finally:
        conn.close()


def has_any_data():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) AS n FROM items')
        return _one(cur)['n'] > 0
    finally:
        conn.close()


def is_sample_only():
    """현재 데이터가 전부 샘플인지. 대시보드 상단 배너 표시에 쓴다."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) AS n FROM items WHERE is_sample = 0')
        real = _one(cur)['n']
        cur.execute('SELECT COUNT(*) AS n FROM items')
        total = _one(cur)['n']
        return total > 0 and real == 0
    finally:
        conn.close()


# --------------------------------------------------------------------------
# 조회
# --------------------------------------------------------------------------

def fetch_items(search='', item_type='', status='', coach='', days=30):
    query = 'SELECT * FROM items WHERE 1=1'
    params = []

    if days:
        cutoff = (datetime.now() - timedelta(days=int(days))).strftime('%Y-%m-%d')
        query += ' AND source_date >= ?'
        params.append(cutoff)
    if search:
        query += ' AND (term LIKE ? OR meaning LIKE ? OR example LIKE ? OR tags LIKE ?)'
        params.extend([f'%{search}%'] * 4)
    if item_type:
        query += ' AND item_type = ?'
        params.append(item_type)
    if status:
        query += ' AND status = ?'
        params.append(status)
    if coach:
        query += ' AND coach = ?'
        params.append(coach)

    query += (" ORDER BY CASE status WHEN 'new' THEN 1 WHEN 'learning' THEN 2 ELSE 3 END,"
              " source_date DESC, id DESC")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q(query), params)
        return _rows(cur)
    finally:
        conn.close()


def get_item(item_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('SELECT * FROM items WHERE id = ?'), (item_id,))
        return _one(cur)
    finally:
        conn.close()


def fetch_sessions(days=30):
    cutoff = (datetime.now() - timedelta(days=int(days))).strftime('%Y-%m-%d')
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('SELECT * FROM sessions WHERE session_date >= ?'
                       ' ORDER BY session_date DESC, id DESC'), (cutoff,))
        return _rows(cur)
    finally:
        conn.close()


# --------------------------------------------------------------------------
# 변경
# --------------------------------------------------------------------------

def set_status(item_id, status):
    if status not in STATUSES:
        return None
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('UPDATE items SET status = ?, updated_at = ? WHERE id = ?'),
                    (status, now, item_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def add_item(term, meaning='', example='', item_type='vocab', coach='',
             status='new', tags='', source_date='', session_id=None, is_sample=0):
    now = datetime.now().isoformat()
    source_date = source_date or datetime.now().strftime('%Y-%m-%d')
    sql = ('INSERT INTO items (session_id, item_type, term, meaning, example, coach,'
           ' status, tags, source_date, is_sample, created_at, updated_at)'
           ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    params = (session_id, item_type, term, meaning, example, coach,
              status, tags, source_date, is_sample, now, now)

    conn = get_db()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(_q(sql + ' RETURNING id'), params)
            new_id = _one(cur)['id']
        else:
            cur.execute(sql, params)
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def add_session(session_date, coach, topic='', summary='', duration_min=0, is_sample=0):
    now = datetime.now().isoformat()
    sql = ('INSERT INTO sessions (session_date, coach, topic, summary, duration_min,'
           ' is_sample, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)')
    params = (session_date, coach, topic, summary, duration_min, is_sample, now)

    conn = get_db()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(_q(sql + ' RETURNING id'), params)
            new_id = _one(cur)['id']
        else:
            cur.execute(sql, params)
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def delete_item(item_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(_q('DELETE FROM items WHERE id = ?'), (item_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def clear_sample_data():
    """실제 데이터를 넣을 때 샘플만 걷어낸다."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM items WHERE is_sample = 1')
        removed = cur.rowcount
        cur.execute('DELETE FROM sessions WHERE is_sample = 1')
        conn.commit()
        return removed
    finally:
        conn.close()


def import_payload(payload):
    """대화 기록에서 뽑은 학습 자료를 한 번에 밀어 넣는다.

    payload = {"sessions": [...], "items": [...], "replace_sample": true}
    """
    if payload.get('replace_sample', True):
        clear_sample_data()

    session_map = {}
    for s in payload.get('sessions', []):
        sid = add_session(
            session_date=s.get('session_date', datetime.now().strftime('%Y-%m-%d')),
            coach=s.get('coach', ''),
            topic=s.get('topic', ''),
            summary=s.get('summary', ''),
            duration_min=int(s.get('duration_min', 0) or 0),
        )
        if s.get('key'):
            session_map[s['key']] = sid

    count = 0
    for it in payload.get('items', []):
        if not it.get('term'):
            continue
        add_item(
            term=it['term'],
            meaning=it.get('meaning', ''),
            example=it.get('example', ''),
            item_type=it.get('item_type', 'vocab'),
            coach=it.get('coach', ''),
            status=it.get('status', 'new'),
            tags=it.get('tags', ''),
            source_date=it.get('source_date', ''),
            session_id=session_map.get(it.get('session_key')),
        )
        count += 1
    return count


# --------------------------------------------------------------------------
# 분석
# --------------------------------------------------------------------------

def get_analytics(days=30):
    items = fetch_items(days=days)
    sessions = fetch_sessions(days=days)

    by_status = {s: 0 for s in STATUSES}
    by_type = {t: 0 for t in ITEM_TYPES}
    by_coach = {c: 0 for c in COACHES}
    for it in items:
        by_status[it['status']] = by_status.get(it['status'], 0) + 1
        by_type[it['item_type']] = by_type.get(it['item_type'], 0) + 1
        if it.get('coach'):
            by_coach[it['coach']] = by_coach.get(it['coach'], 0) + 1

    # 주간 추이 (최근 4주, 오래된 주 -> 최근 주)
    today = datetime.now().date()
    weekly = []
    for w in range(3, -1, -1):
        end = today - timedelta(days=7 * w)
        start = end - timedelta(days=6)
        s, e = start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
        weekly.append({
            'label': start.strftime('%m/%d'),
            'items': sum(1 for it in items if s <= (it.get('source_date') or '') <= e),
            'sessions': sum(1 for x in sessions if s <= (x.get('session_date') or '') <= e),
        })

    mastered_total = _count_mastered_all_time()
    current, nxt = _stone_progress(mastered_total)

    total = len(items)
    return {
        'window_days': int(days),
        'total_items': total,
        'total_sessions': len(sessions),
        'study_minutes': sum(int(x.get('duration_min') or 0) for x in sessions),
        'mastered_total': mastered_total,
        'mastery_rate': round(by_status['mastered'] / total * 100) if total else 0,
        'by_status': by_status,
        'by_type': by_type,
        'by_coach': by_coach,
        'weekly': weekly,
        'stones': STONES,
        'current_stone': current,
        'next_stone': nxt,
        'is_sample_only': is_sample_only(),
    }


def _count_mastered_all_time():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM items WHERE status = 'mastered'")
        return _one(cur)['n']
    finally:
        conn.close()


def _stone_progress(mastered):
    current = STONES[0]
    for s in STONES:
        if mastered >= s['target']:
            current = s
    nxt = next((s for s in STONES if s['target'] > mastered), None)

    if nxt is None:
        return {**current, 'reached': True, 'percent': 100}, None

    prev_target = 0
    for s in STONES:
        if s['target'] <= mastered:
            prev_target = s['target']
    span = nxt['target'] - prev_target
    done = mastered - prev_target
    percent = round(done / span * 100) if span else 0

    reached = mastered >= STONES[0]['target']
    return ({**current, 'reached': reached, 'percent': percent},
            {**nxt, 'remaining': nxt['target'] - mastered})


# --------------------------------------------------------------------------
# 샘플 데이터 (실제 코칭 기록이 아님 - is_sample=1 로 명확히 표시)
# --------------------------------------------------------------------------

def seed_sample_data():
    """대시보드 동작 확인용 표본. 실제 몰리/빌 코칭 기록이 아니다.

    실제 자료를 넣으면 clear_sample_data()로 전부 사라진다.
    """
    if has_any_data():
        return 0

    today = datetime.now().date()

    def d(offset):
        return (today - timedelta(days=offset)).strftime('%Y-%m-%d')

    sessions = [
        (d(2), 'Molly', 'Small talk 확장', '날씨/주말 주제에서 후속 질문 연결 연습', 40),
        (d(5), 'Bill', 'Business email tone', '완곡 표현과 직설 표현의 경계 정리', 45),
        (d(9), 'Molly', 'Phrasal verbs', 'get/take 계열 구동사 집중', 40),
        (d(13), 'Bill', 'Presentation opening', '도입부 3문장 구조 훈련', 50),
        (d(18), 'Molly', 'Listening shadowing', '뉴스 클립 섀도잉', 35),
        (d(24), 'Bill', 'Negotiation phrases', '조건 제시 표현', 45),
    ]
    for sd, coach, topic, summary, dur in sessions:
        add_session(sd, coach, topic, summary, dur, is_sample=1)

    items = [
        ('touch base', '간단히 연락하다', "Let's touch base next week.", 'expression', 'Bill', 'mastered', 'business', 5),
        ('circle back', '다시 논의하다', 'I will circle back on this tomorrow.', 'expression', 'Bill', 'mastered', 'business', 5),
        ('get around to', '~할 시간을 내다', 'I finally got around to it.', 'vocab', 'Molly', 'learning', 'phrasal', 9),
        ('take up on', '제안을 받아들이다', "I'll take you up on that offer.", 'vocab', 'Molly', 'new', 'phrasal', 9),
        ('would you mind ~ing', '~해 주시겠어요 (공손)', 'Would you mind sending the file?', 'grammar', 'Bill', 'mastered', 'politeness', 5),
        ('I was wondering if', '~인지 궁금했어요 (완곡)', 'I was wondering if you had time.', 'grammar', 'Bill', 'learning', 'politeness', 5),
        ('schedule', '미국식 발음 주의 (스케줄)', 'The schedule is tight.', 'pronunciation', 'Molly', 'learning', 'sound', 18),
        ('comfortable', '3음절로 축약해 발음', 'Make yourself comfortable.', 'pronunciation', 'Molly', 'mastered', 'sound', 18),
        ('to be honest', '솔직히 말하면', 'To be honest, I disagree.', 'expression', 'Molly', 'mastered', 'smalltalk', 2),
        ('speaking of which', '말이 나온 김에', 'Speaking of which, did you finish?', 'expression', 'Molly', 'learning', 'smalltalk', 2),
        ('follow up on', '후속 조치하다', 'Let me follow up on that.', 'vocab', 'Bill', 'mastered', 'business', 24),
        ('in terms of', '~의 측면에서', 'In terms of cost, it works.', 'expression', 'Bill', 'mastered', 'presentation', 13),
        ('walk you through', '차근차근 설명하다', "I'll walk you through the data.", 'expression', 'Bill', 'learning', 'presentation', 13),
        ('narrow down', '범위를 좁히다', 'We narrowed down the options.', 'vocab', 'Bill', 'new', 'negotiation', 24),
        ('meet halfway', '절충하다', 'Can we meet halfway on price?', 'expression', 'Bill', 'new', 'negotiation', 24),
        ('run by', '의견을 구하다', 'Can I run this by you?', 'vocab', 'Molly', 'learning', 'business', 9),
        ('used to vs be used to', '과거 습관 / 익숙함', 'I used to live there. I am used to it.', 'grammar', 'Molly', 'learning', 'confusing', 9),
        ('rather than', '~보다는', 'Rather than wait, I called.', 'grammar', 'Bill', 'mastered', 'writing', 5),
        ('pick up on', '알아채다', 'She picked up on my hesitation.', 'vocab', 'Molly', 'new', 'phrasal', 2),
        ('bring up', '화제를 꺼내다', 'He brought up a good point.', 'vocab', 'Molly', 'mastered', 'phrasal', 18),
    ]
    for term, meaning, example, itype, coach, status, tags, ago in items:
        add_item(term, meaning, example, itype, coach, status, tags, d(ago), is_sample=1)

    return len(items)

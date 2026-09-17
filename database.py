import os
import sqlite3
from datetime import datetime

# DATABASE_URL(Supabase Postgres)이 있으면 Postgres를, 없으면 로컬 SQLite를 쓴다.
# 덕분에 배포 환경은 데이터가 영구 보존되고, 로컬 개발은 설정 없이 그대로 돌아간다.
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    SQLITE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'todo.db')


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
    return [dict(row) for row in cursor.fetchall()]


def init_db():
    if USE_POSTGRES:
        create_sql = '''
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'Work',
                priority TEXT DEFAULT 'Medium',
                due_date TEXT DEFAULT '',
                is_completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        '''
    else:
        create_sql = '''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'Work',
                priority TEXT DEFAULT 'Medium',
                due_date TEXT DEFAULT '',
                is_completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        '''

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(create_sql)
        conn.commit()

        # Seed initial data if empty
        cursor.execute('SELECT COUNT(*) AS count FROM todos')
        if dict(cursor.fetchone())['count'] == 0:
            now = datetime.now().isoformat()
            today = datetime.now().strftime('%Y-%m-%d')
            sample_todos = [
                ('플라스크 웹앱 구조 설계하기', 'Flask 백엔드 API와 SQLite DB 연동 작업', 'Work', 'High', today, 1, now, now),
                ('글래스모피즘 UI 스타일링', 'Inter 폰트와 다크 모드 네온 스타일 CSS 작성', 'Work', 'High', today, 1, now, now),
                ('장보기 목록 작성', '우유, 계란, 파스타 면, 토마토 소스 구매', 'Shopping', 'Medium', '', 0, now, now),
                ('매일 30분 운동하기', '가벼운 러닝 및 스트레칭', 'Health', 'Low', '', 0, now, now),
            ]
            cursor.executemany(_q('''
                INSERT INTO todos (title, description, category, priority, due_date, is_completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''), sample_todos)
            conn.commit()
    finally:
        conn.close()


def fetch_all_todos(search='', category='', priority='', status=''):
    query = 'SELECT * FROM todos WHERE 1=1'
    params = []

    if search:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    if category and category != 'All':
        query += ' AND category = ?'
        params.append(category)
    if priority and priority != 'All':
        query += ' AND priority = ?'
        params.append(priority)
    if status == 'active':
        query += ' AND is_completed = 0'
    elif status == 'completed':
        query += ' AND is_completed = 1'

    # 문자열 리터럴은 작은따옴표로 쓴다. Postgres에서 큰따옴표는 식별자를 뜻한다.
    query += (" ORDER BY is_completed ASC,"
              " CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END,"
              " id DESC")

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(_q(query), params)
        return _rows(cursor)
    finally:
        conn.close()


def get_todo_by_id(todo_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(_q('SELECT * FROM todos WHERE id = ?'), (todo_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_todo(title, description='', category='Work', priority='Medium', due_date=''):
    now = datetime.now().isoformat()
    insert_sql = '''
        INSERT INTO todos (title, description, category, priority, due_date, is_completed, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?)
    '''
    params = (title, description, category, priority, due_date, now, now)

    conn = get_db()
    try:
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute(_q(insert_sql + ' RETURNING id'), params)
            new_id = dict(cursor.fetchone())['id']
        else:
            cursor.execute(insert_sql, params)
            new_id = cursor.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def update_todo(todo_id, title, description='', category='Work', priority='Medium', due_date=''):
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(_q('''
            UPDATE todos
            SET title = ?, description = ?, category = ?, priority = ?, due_date = ?, updated_at = ?
            WHERE id = ?
        '''), (title, description, category, priority, due_date, now, todo_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def toggle_todo(todo_id):
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(_q('SELECT is_completed FROM todos WHERE id = ?'), (todo_id,))
        row = cursor.fetchone()
        if not row:
            return None
        new_status = 0 if dict(row)['is_completed'] else 1
        cursor.execute(_q('UPDATE todos SET is_completed = ?, updated_at = ? WHERE id = ?'),
                       (new_status, now, todo_id))
        conn.commit()
        return new_status
    finally:
        conn.close()


def delete_todo(todo_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(_q('DELETE FROM todos WHERE id = ?'), (todo_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_completed_todos():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM todos WHERE is_completed = 1')
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_stats():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) AS total FROM todos')
        total = dict(cursor.fetchone())['total']

        cursor.execute('SELECT COUNT(*) AS completed FROM todos WHERE is_completed = 1')
        completed = dict(cursor.fetchone())['completed']

        cursor.execute('SELECT COUNT(*) AS active FROM todos WHERE is_completed = 0')
        active = dict(cursor.fetchone())['active']

        cursor.execute("SELECT COUNT(*) AS high_priority FROM todos"
                       " WHERE priority = 'High' AND is_completed = 0")
        high_priority = dict(cursor.fetchone())['high_priority']

        completion_rate = round((completed / total * 100)) if total > 0 else 0

        return {
            'total': total,
            'completed': completed,
            'active': active,
            'high_priority': high_priority,
            'completion_rate': completion_rate,
        }
    finally:
        conn.close()

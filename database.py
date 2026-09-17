import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'todo.db')

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
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
        ''')
        conn.commit()
        
        # Seed initial data if empty
        cursor.execute('SELECT COUNT(*) as count FROM todos')
        if cursor.fetchone()['count'] == 0:
            now = datetime.now().isoformat()
            sample_todos = [
                ('플라스크 웹앱 구조 설계하기', 'Flask 백엔드 API와 SQLite DB 연동 작업', 'Work', 'High', datetime.now().strftime('%Y-%m-%d'), 1, now, now),
                ('글래스모피즘 UI 스타일링', 'Inter 폰트와 다크 모드 네온 스타일 CSS 작성', 'Work', 'High', datetime.now().strftime('%Y-%m-%d'), 1, now, now),
                ('장보기 목록 작성', '우유, 계란, 파스타 면, 토마토 소스 구매', 'Shopping', 'Medium', '', 0, now, now),
                ('매일 30분 운동하기', '가벼운 러닝 및 스트레칭', 'Health', 'Low', '', 0, now, now)
            ]
            cursor.executemany('''
                INSERT INTO todos (title, description, category, priority, due_date, is_completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_todos)
            conn.commit()

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

    query += ' ORDER BY is_completed ASC, CASE priority WHEN "High" THEN 1 WHEN "Medium" THEN 2 WHEN "Low" THEN 3 ELSE 4 END, id DESC'

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_todo_by_id(todo_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_todo(title, description='', category='Work', priority='Medium', due_date=''):
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO todos (title, description, category, priority, due_date, is_completed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        ''', (title, description, category, priority, due_date, now, now))
        conn.commit()
        return cursor.lastrowid

def update_todo(todo_id, title, description='', category='Work', priority='Medium', due_date=''):
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE todos 
            SET title = ?, description = ?, category = ?, priority = ?, due_date = ?, updated_at = ?
            WHERE id = ?
        ''', (title, description, category, priority, due_date, now, todo_id))
        conn.commit()
        return cursor.rowcount > 0

def toggle_todo(todo_id):
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_completed FROM todos WHERE id = ?', (todo_id,))
        row = cursor.fetchone()
        if not row:
            return None
        new_status = 0 if row['is_completed'] else 1
        cursor.execute('UPDATE todos SET is_completed = ?, updated_at = ? WHERE id = ?', (new_status, now, todo_id))
        conn.commit()
        return new_status

def delete_todo(todo_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()
        return cursor.rowcount > 0

def delete_completed_todos():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM todos WHERE is_completed = 1')
        conn.commit()
        return cursor.rowcount

def get_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as total FROM todos')
        total = cursor.fetchone()['total']

        cursor.execute('SELECT COUNT(*) as completed FROM todos WHERE is_completed = 1')
        completed = cursor.fetchone()['completed']

        cursor.execute('SELECT COUNT(*) as active FROM todos WHERE is_completed = 0')
        active = cursor.fetchone()['active']

        cursor.execute('SELECT COUNT(*) as high_priority FROM todos WHERE priority = "High" AND is_completed = 0')
        high_priority = cursor.fetchone()['high_priority']

        completion_rate = round((completed / total * 100)) if total > 0 else 0

        return {
            'total': total,
            'completed': completed,
            'active': active,
            'high_priority': high_priority,
            'completion_rate': completion_rate
        }

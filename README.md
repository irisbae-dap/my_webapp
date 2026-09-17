# TaskFlow

Flask + SQLite 기반의 할일 관리 웹앱. 다크 글래스모피즘 UI와 REST API를 제공합니다.

## 기능

- 할일 CRUD (제목, 상세 설명, 카테고리, 우선순위, 마감 기한)
- 완료 토글 / 완료 항목 일괄 삭제
- 검색(디바운스) + 카테고리 · 우선순위 · 진행 상태 필터
- 통계 대시보드 (전체 / 완료 / 긴급 / 달성률)
- 마감 임박·초과 항목 강조 표시

## 실행

```bash
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

http://127.0.0.1:5000 에서 접속합니다. 최초 실행 시 `todo.db`가 생성되고 샘플 데이터가 시딩됩니다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/todos` | 목록 조회 (`search`, `category`, `priority`, `status` 쿼리 지원) |
| POST | `/api/todos` | 생성 (`title` 필수) |
| GET | `/api/todos/<id>` | 단건 조회 |
| PUT | `/api/todos/<id>` | 수정 |
| DELETE | `/api/todos/<id>` | 삭제 |
| PATCH | `/api/todos/<id>/toggle` | 완료 상태 토글 |
| DELETE | `/api/todos/completed` | 완료 항목 일괄 삭제 |
| GET | `/api/stats` | 통계 조회 |

## 구조

```
app.py                 # Flask 라우트 / REST API
database.py            # SQLite 데이터 접근 계층
templates/index.html   # 단일 페이지 UI
static/css/style.css   # 스타일
static/js/app.js       # 프론트엔드 로직
```

## 참고

`app.py`는 개발 편의를 위해 `debug=True`로 실행됩니다. 배포 시에는 끄고 WSGI 서버(gunicorn 등)를 사용하세요.

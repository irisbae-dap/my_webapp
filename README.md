# Stepping Stones

몰리 · 빌과의 English coaching 기록을 모아 보는 학습 분석 대시보드.
Flask + Supabase Postgres, Vercel 배포.

## 기능

- **Stepping Stones 진행도** — 누적 마스터 항목 수로 5단계 사다리를 오른다
- **핵심 지표** — 기간 내 학습 항목 / 코칭 세션 / 학습 시간 / 마스터율
- **차트** — 주차별 학습량, 유형별 분포, 숙련도 구성, 코치별 비중
- **학습 리스트** — 검색 · 유형 · 코치 · 상태 필터, 클릭 한 번으로 상태 전환
  (새 항목 → 학습 중 → 마스터)
- **기간 전환** — 7일 / 30일 / 90일

## 실행

```bash
pip install -r requirements.txt
python app.py
```

http://127.0.0.1:5000 에서 접속합니다. `PORT` 환경변수로 포트를 바꿀 수 있습니다.

## 데이터베이스

`DATABASE_URL` 유무로 저장소가 결정됩니다.

| 환경변수 | 사용 DB | 용도 |
|---|---|---|
| 없음 | 로컬 SQLite (`steppingstones.db`) | 로컬 개발 |
| 설정됨 | Supabase Postgres | 배포 (데이터 영구 보존) |

Supabase 연결 문자열은 **Project Settings → Database → Connection string**의
Transaction pooler(포트 `6543`) 값을 씁니다. 서버리스는 요청마다 커넥션이 생기므로
풀러를 쓰지 않으면 연결 수 제한에 걸립니다. 형식은 `.env.example` 참고.

### 테이블

| 테이블 | 내용 |
|---|---|
| `sessions` | 코칭 세션 (날짜, 코치, 주제, 요약, 시간) |
| `items` | 학습 항목 (표현, 뜻, 예문, 유형, 코치, 상태, 태그, 학습일) |

`is_sample = 1`인 행은 대시보드 동작 확인용 표본입니다. 실제 자료를 적재하면
자동으로 제거되고, 화면 상단의 예시 데이터 경고 배너도 사라집니다.

## 실제 학습 자료 적재

`POST /api/import`에 아래 형태로 보내면 표본을 걷어내고 실제 자료로 교체합니다.

```json
{
  "replace_sample": true,
  "sessions": [
    { "key": "s1", "session_date": "2026-09-12", "coach": "Bill",
      "topic": "Business email tone", "summary": "...", "duration_min": 45 }
  ],
  "items": [
    { "term": "circle back", "meaning": "다시 논의하다",
      "example": "I will circle back on this tomorrow.",
      "item_type": "expression", "coach": "Bill", "status": "learning",
      "tags": "business", "source_date": "2026-09-12", "session_key": "s1" }
  ]
}
```

`item_type`은 `vocab` / `expression` / `grammar` / `pronunciation`,
`status`는 `new` / `learning` / `mastered` 중 하나입니다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/analytics?days=30` | 지표 · 차트 · 단계 진행도 |
| GET | `/api/items` | 목록 (`search`, `type`, `status`, `coach`, `days`) |
| POST | `/api/items` | 항목 추가 (`term` 필수) |
| PATCH | `/api/items/<id>/status` | 상태 변경 |
| DELETE | `/api/items/<id>` | 항목 삭제 |
| GET | `/api/sessions?days=30` | 세션 목록 |
| POST | `/api/import` | 실제 자료 일괄 적재 |
| DELETE | `/api/sample` | 표본 데이터만 제거 |

## 단계 기준 바꾸기

`database.py`의 `STONES` 목록이 단일 기준점입니다. 이름과 `target`(누적 마스터 수)을
고치면 대시보드 전체에 반영됩니다.

```python
STONES = [
    {'no': 1, 'name': 'Foundation', 'label': '기초 다지기', 'target': 20},
    ...
]
```

## 구조

```
app.py                 # Flask 라우트 / REST API
database.py            # 데이터 계층 (SQLite ↔ Postgres 이중 지원) + 단계 정의
templates/index.html   # 단일 페이지 대시보드
static/css/style.css   # 다크 글래스모피즘 스타일
static/js/app.js       # 대시보드 로직 + 인라인 SVG 차트
```

차트 색은 색각 이상 대비를 검증한 다크 모드 카테고리 팔레트를 쓰고, 상태색
(새 항목 / 학습 중 / 마스터)은 계열색과 섞이지 않도록 따로 예약했습니다.

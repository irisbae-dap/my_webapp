# Stepping Stones — English Dashboard

내 영어 코칭 기록을 한곳에서 보는 학습 분석 대시보드.
Flask + Supabase Postgres, Vercel 배포.

**Live:** https://260917v-azure.vercel.app

## 무엇을 보여주나

프로젝트 스펙(`05-project-stepping-stones.md`, `ss_engine_dashboard.md`)의
**5-category 분석 모델**을 그대로 화면 모듈로 옮겼습니다.

| # | 카테고리 | 이 대시보드가 재는 것 | 상태 |
|---|---|---|---|
| 1 | Flow & Thought Process | 문장 평균 길이와 변동성 | 측정됨 |
| 2 | Discourse & Voice | hedging 빈도 (100단어당) | 측정됨 |
| 3 | Accuracy | 문법·어휘 오류 | **미측정** |
| 4 | Nuance & Lexical | 어휘 다양성 (고유어 비율) | 측정됨 |
| 5 | Habit Analysis | 필러 단어 빈도 | 측정됨 |

Accuracy는 원문 텍스트만으로 계산할 수 없어 **값을 비워두고 화면에 그 사실을 밝힙니다.**
추정치를 채워 넣지 않았습니다.

이 외에 페블 타워(세션 1건 = 돌 1개), 필러·헤지 빈도 차트, 학습 리스트,
최근 세션 표가 있습니다.

## 데이터 출처

Google Drive `7_english_corpus.md` — 본인의 영어 작성 + 코치 피드백 대화 93건
(2023-03-05 ~ 2026-02-24). 이 중 영어 발화가 20단어 이상인 **87건**을 세션으로 적재했습니다.

**모든 지표는 본인 발화에서만 계산합니다.** 코치 답변 텍스트는 제외합니다.
학습 리스트도 빈도 근거가 있는 항목만 만듭니다 — 지어낸 항목은 없습니다.

| 학습 항목 종류 | 근거 |
|---|---|
| Habit | 실제 필러 사용 횟수 (예: "like" 85회 / 33개 세션) |
| Voice | 실제 hedging 사용 횟수 |
| Accuracy | 코치 피드백에 명시적으로 나온 교정 쌍 |
| Nuance | 코치가 알려준 어휘 |

### 기간 필터 주의

코퍼스는 2026-02-24에서 끝납니다. 오늘 날짜를 기준으로 자르면 화면이 비므로,
기간 필터는 **데이터의 마지막 날짜를 기준**으로 계산합니다
(`Last 30 days` = 2026-01-26 ~ 2026-02-24).

## 실행

```bash
pip install -r requirements.txt
python app.py
```

`.env`에 `DATABASE_URL`을 두면 Supabase를, 없으면 로컬 SQLite를 씁니다.
`PORT`로 포트를 바꿀 수 있습니다.

| 환경변수 | 사용 DB |
|---|---|
| 없음 | 로컬 SQLite (`steppingstones.db`) |
| `DATABASE_URL` | Supabase Postgres |

Supabase 연결 문자열은 **Settings → Database → Connection string**의
Transaction pooler(포트 `6543`)를 씁니다. 서버리스는 요청마다 커넥션이 생겨
풀러 없이는 연결 수 제한에 걸립니다.

## 데이터 다시 만들기

```bash
python tools_extract_corpus.py     # 코퍼스 -> extracted.json (지표 계산)
python tools_build_dataset.py      # extracted.json -> dataset.json (적재용)
curl -X POST http://127.0.0.1:5000/api/load \
     -H "Content-Type: application/json" --data-binary @dataset.json
```

두 스크립트 상단의 경로 상수를 실제 코퍼스 위치로 맞춘 뒤 실행하세요.
`/api/load`는 기본적으로 기존 데이터를 비우고 새로 적재합니다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/overview?days=` | 5개 카테고리, 빈도 차트, 요약 수치 |
| GET | `/api/sessions?days=` | 세션 원자료 |
| GET | `/api/study` | 학습 리스트 (`status`, `category`, `search`) |
| PATCH | `/api/study/<id>/status` | To do → Working on it → Done |
| POST | `/api/load` | 데이터셋 일괄 적재 |

## 테이블

| 테이블 | 내용 |
|---|---|
| `sessions` | 세션별 지표 (단어 수, 문장 길이, 어휘 다양성, 필러·헤지 빈도) |
| `patterns` | 세션별 필러/헤지 표현과 횟수 |
| `study_items` | 학습 항목과 진행 상태 |

## 기준 바꾸기

`database.py`의 `CATEGORIES`가 단일 기준점입니다. 어떤 지표를 어느 카테고리에
붙일지, 높은 값이 좋은지(`direction`), 측정 가능한지(`measured`)를 여기서 정합니다.

## 디자인

스펙의 **soft grey + warm undertone**, 페블/돌탑 모티프를 따랐습니다.
차트 색은 색각 이상 대비 검증을 통과한 팔레트를 쓰고, 대비가 낮은 색은
막대마다 숫자를 직접 붙여 보완했습니다. UI 문구는 쉬운 영어로 씁니다.

## 구조

```
app.py                    # Flask 라우트 / REST API
database.py               # 데이터 계층 (SQLite ↔ Postgres) + 5-category 정의
templates/index.html      # 단일 페이지 대시보드
static/css/style.css      # 웜그레이 페블 테마
static/js/app.js          # 대시보드 로직 + 인라인 SVG 차트
tools_extract_corpus.py   # 코퍼스 -> 지표 추출
tools_build_dataset.py    # 지표 -> 적재용 데이터셋
```

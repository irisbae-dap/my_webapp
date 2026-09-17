"""English corpus -> Stepping Stones 대시보드 데이터 추출기.

원문에서 '계산 가능한 것만' 뽑는다. 추정하거나 지어내지 않는다.
- sessions: 대화 1건 = 세션 1건 (날짜, 제목, 태그, Iris 발화량)
- metrics: Iris 본인 영어에서만 계산 (Feedback 텍스트는 제외)
- items: 코치 피드백에서 명시적으로 제시된 표현/어휘만 추출
"""

import json
import re
import statistics
import sys
from collections import Counter

SRC = (r"C:/Users/user/AppData/Local/Temp/claude/"
       r"C--Users-user-Desktop-AI-agent-260917-my-webapp/"
       r"51fe4624-73ec-4ec3-b6ca-0c38b875732a/scratchpad/ss/english_corpus.md")

# Habit Analysis (spec: 유일하게 순수 빈도 기반 카테고리)
FILLERS = ['like', 'just', 'really', 'very', 'actually', 'basically',
           'literally', 'so', 'well', 'anyway', 'stuff', 'things']
# Discourse & Voice: hedging (spec 5절 'Hedging reduction')
HEDGES = ['i think', 'i guess', 'maybe', 'kind of', 'kinda', 'sort of',
          'probably', 'i feel like', 'i believe', 'perhaps', 'somewhat',
          'a bit', 'a little', 'tbh', 'i mean', 'not sure', 'might be']


def split_conversations(text):
    chunks = re.split(r'(?m)^## \[', text)[1:]
    out = []
    for ch in chunks:
        m = re.match(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\]\s*(.*?)\s*`(keep_[a-z_]+)`', ch)
        if not m:
            continue
        date, time, title, tag = m.groups()
        out.append({'date': date, 'time': time, 'title': title.strip(),
                    'tag': tag, 'body': ch})
    return out


def iris_turns(body):
    """Iris 발화만 추출 (Feedback 블록 제외)."""
    turns = []
    for m in re.finditer(r'\*\*Iris:\*\*(.*?)(?=\*\*Feedback:\*\*|\*\*Iris:\*\*|\Z)',
                         body, re.S):
        turns.append(m.group(1).strip())
    return turns


def feedback_turns(body):
    return [m.group(1).strip() for m in
            re.finditer(r'\*\*Feedback:\*\*(.*?)(?=\*\*Iris:\*\*|\Z)', body, re.S)]


def english_words(text):
    return re.findall(r"[A-Za-z][A-Za-z'’]*", text)


def count_phrases(low, phrases):
    c = Counter()
    for p in phrases:
        n = len(re.findall(r'(?<![a-z])' + re.escape(p) + r'(?![a-z])', low))
        if n:
            c[p] = n
    return c


def sentence_lengths(text):
    sents = [s for s in re.split(r'[.!?]+\s+', text) if len(english_words(s)) >= 3]
    return [len(english_words(s)) for s in sents]


def analyse(conv):
    turns = iris_turns(conv['body'])
    raw = '\n'.join(turns)
    words = english_words(raw)
    n = len(words)
    low = raw.lower()

    fillers = count_phrases(low, FILLERS)
    hedges = count_phrases(low, HEDGES)
    lens = sentence_lengths(raw)
    uniq = len({w.lower() for w in words})

    per100 = (lambda x: round(x / n * 100, 2)) if n else (lambda x: 0.0)

    return {
        'word_count': n,
        'turn_count': len(turns),
        'unique_words': uniq,
        # Nuache & Lexical: type-token ratio (어휘 다양성)
        'lexical_diversity': round(uniq / n * 100, 1) if n else 0.0,
        'long_word_ratio': round(sum(1 for w in words if len(w) >= 8) / n * 100, 1) if n else 0.0,
        # Flow: 문장 길이와 변동성
        'avg_sentence_len': round(statistics.mean(lens), 1) if lens else 0.0,
        'sentence_len_sd': round(statistics.pstdev(lens), 1) if len(lens) > 1 else 0.0,
        'sentence_count': len(lens),
        # Habit
        'filler_count': sum(fillers.values()),
        'filler_per100': per100(sum(fillers.values())),
        'filler_top': fillers.most_common(6),
        # Discourse
        'hedge_count': sum(hedges.values()),
        'hedge_per100': per100(sum(hedges.values())),
        'hedge_top': hedges.most_common(6),
    }


# --- 학습 항목 추출 -------------------------------------------------------
# 코치가 명시적으로 제시한 것만. 추측 금지.

# "❌ X → ✅ Y", "X → Y", 'Instead of "X", say "Y"'
RE_ARROW = re.compile(r'[“"]([^”"\n]{3,90})[”"]\s*(?:→|->|=>)\s*[“"]([^”"\n]{3,90})[”"]')
RE_INSTEAD = re.compile(r'[Ii]nstead of\s+[“"]?([^”"\n,]{3,70})[”"]?[,:]?\s*(?:say|use|try)\s+[“"]([^”"\n]{3,90})[”"]')
RE_BULLET_ARROW = re.compile(r'(?m)^\s*[-*]\s+(.{3,80}?)\s*(?:→|->|=>)\s*(.{3,90})$')


def _clean(s):
    s = re.sub(r'[*_`]', '', s).strip(' .,:;"“”')
    return s.strip()


def _is_plain_english(s):
    if re.search(r'[가-힣]', s):        # 한글 포함 제외
        return False
    letters = re.findall(r'[A-Za-z]', s)
    return len(letters) >= 3 and len(letters) / max(len(s), 1) > 0.5


def extract_items(conv):
    found = []
    for fb in feedback_turns(conv['body']):
        for rx in (RE_ARROW, RE_INSTEAD, RE_BULLET_ARROW):
            for m in rx.finditer(fb):
                before, after = _clean(m.group(1)), _clean(m.group(2))
                if not (_is_plain_english(before) and _is_plain_english(after)):
                    continue
                if before.lower() == after.lower():
                    continue
                if len(before) > 70 or len(after) > 80:
                    continue
                found.append({'before': before, 'after': after, 'kind': 'rewrite'})

    # keep_vocab 대화: 코치가 따옴표로 제시한 영어 표현
    if conv['tag'] == 'keep_vocab':
        for fb in feedback_turns(conv['body']):
            for m in re.finditer(r"['‘]([A-Za-z][A-Za-z \-]{2,40})['’]", fb):
                term = _clean(m.group(1))
                if _is_plain_english(term) and len(term.split()) <= 4:
                    found.append({'before': '', 'after': term, 'kind': 'vocab'})

    seen, uniq = set(), []
    for f in found:
        k = (f['kind'], f['before'].lower(), f['after'].lower())
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    return uniq


def main():
    text = open(SRC, encoding='utf-8').read()
    convs = split_conversations(text)

    sessions, items = [], []
    for c in convs:
        m = analyse(c)
        if m['word_count'] < 20:      # Iris 영어가 사실상 없는 대화는 제외
            continue
        sid = f"{c['date']}-{len(sessions)+1}"
        sessions.append({**c, **m, 'sid': sid, 'body': None})
        for it in extract_items(c):
            items.append({**it, 'sid': sid, 'date': c['date'], 'title': c['title']})

    out = {'sessions': sessions, 'items': items}
    dest = SRC.replace('english_corpus.md', 'extracted.json')
    json.dump(out, open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('conversations parsed :', len(convs))
    print('sessions kept        :', len(sessions))
    print('date range           :', sessions[0]['date'], '->', sessions[-1]['date'])
    print('rewrite items        :', len(items))
    tot = sum(s['word_count'] for s in sessions)
    print('total Iris words     :', tot)
    print('avg hedge /100w      :', round(statistics.mean([s['hedge_per100'] for s in sessions]), 2))
    print('avg filler /100w     :', round(statistics.mean([s['filler_per100'] for s in sessions]), 2))
    print('avg lexical div      :', round(statistics.mean([s['lexical_diversity'] for s in sessions]), 1))
    print('\nsample items:')
    for it in items[:8]:
        print('  -', it['before'][:50], '=>', it['after'][:50])


if __name__ == '__main__':
    sys.exit(main())

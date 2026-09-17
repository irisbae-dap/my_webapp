"""extracted.json -> 대시보드 적재용 dataset.json.

study_items 는 '계산된 근거가 있는 것'만 만든다.
- habit  : 실제로 많이 쓴 필러 단어 (빈도 근거 포함)
- voice  : 실제로 많이 쓴 hedging 표현 (빈도 근거 포함)
- rewrite: 코치 피드백에 명시적으로 나온 교정 쌍
지어낸 항목은 없다.
"""

import collections
import json

SS = (r"C:/Users/user/AppData/Local/Temp/claude/"
      r"C--Users-user-Desktop-AI-agent-260917-my-webapp/"
      r"51fe4624-73ec-4ec3-b6ca-0c38b875732a/scratchpad/ss")

src = json.load(open(SS + '/extracted.json', encoding='utf-8'))

sessions, patterns = [], []
for s in src['sessions']:
    sessions.append({
        'sid': s['sid'],
        'session_date': s['date'],
        'title': s['title'],
        'tag': s['tag'],
        'word_count': s['word_count'],
        'turn_count': s['turn_count'],
        'sentence_count': s['sentence_count'],
        'unique_words': s['unique_words'],
        'avg_sentence_len': s['avg_sentence_len'],
        'sentence_len_sd': s['sentence_len_sd'],
        'lexical_diversity': s['lexical_diversity'],
        'long_word_ratio': s['long_word_ratio'],
        'filler_count': s['filler_count'],
        'filler_per100': s['filler_per100'],
        'hedge_count': s['hedge_count'],
        'hedge_per100': s['hedge_per100'],
    })
    for phrase, n in s['filler_top']:
        patterns.append({'sid': s['sid'], 'session_date': s['date'],
                         'kind': 'filler', 'phrase': phrase, 'count': n})
    for phrase, n in s['hedge_top']:
        patterns.append({'sid': s['sid'], 'session_date': s['date'],
                         'kind': 'hedge', 'phrase': phrase, 'count': n})

# --- study items ----------------------------------------------------------
filler_tot, hedge_tot = collections.Counter(), collections.Counter()
filler_sess, hedge_sess = collections.Counter(), collections.Counter()
for p in patterns:
    if p['kind'] == 'filler':
        filler_tot[p['phrase']] += p['count']
        filler_sess[p['phrase']] += 1
    else:
        hedge_tot[p['phrase']] += p['count']
        hedge_sess[p['phrase']] += 1

last_date = max(s['session_date'] for s in sessions)
items = []

for phrase, n in filler_tot.most_common(6):
    items.append({
        'kind': 'habit', 'category': 'habit',
        'title': f'Use "{phrase}" less',
        'detail': 'A filler word. Try to pause instead, or cut it.',
        'evidence': f'{n} times across {filler_sess[phrase]} sessions',
        'source_date': last_date, 'source_title': 'Habit Analysis',
    })

for phrase, n in hedge_tot.most_common(5):
    items.append({
        'kind': 'voice', 'category': 'discourse',
        'title': f'Say "{phrase}" with more confidence',
        'detail': 'Hedging softens your point. State it directly when you are sure.',
        'evidence': f'{n} times across {hedge_sess[phrase]} sessions',
        'source_date': last_date, 'source_title': 'Discourse & Voice',
    })

for it in src['items']:
    if it['kind'] == 'rewrite' and it['before'] and it['after']:
        items.append({
            'kind': 'rewrite', 'category': 'accuracy',
            'title': f'{it["before"]} → {it["after"]}',
            'detail': 'Your coach suggested this change.',
            'evidence': 'From your own feedback history',
            'source_date': it['date'], 'source_title': it['title'],
        })
    elif it['kind'] == 'vocab':
        items.append({
            'kind': 'vocab', 'category': 'nuance',
            'title': it['after'],
            'detail': 'A word your coach gave you.',
            'evidence': 'From your own feedback history',
            'source_date': it['date'], 'source_title': it['title'],
        })

out = {'sessions': sessions, 'patterns': patterns, 'study_items': items, 'replace': True}
json.dump(out, open(SS + '/dataset.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('sessions   :', len(sessions))
print('patterns   :', len(patterns))
print('study items:', len(items), collections.Counter(i['kind'] for i in items))
print('date range :', min(s['session_date'] for s in sessions), '->', last_date)

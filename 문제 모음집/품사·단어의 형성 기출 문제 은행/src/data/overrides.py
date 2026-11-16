"""변환으로 바로잡기 어려운 문항을 손으로 고친다(문항 번호 → 함수)."""
def _q193(q):
    rows = [('①', '묻었다', '이르러', '일러, 우러러', '파래'), ('②', '일러', '이르러, 파래', '묻었다', '우러러'),
            ('③', '이르러', '묻었다, 우러러', '파래', '일러'), ('④', '묻었다, 우러러', '일러', '이르러', '파래'),
            ('⑤', '일러, 우러러', '묻었다', '파래', '이르러')]
    head = '<tr><td></td>' + ''.join(f'<td style="text-align:center"><u>{k}</u></td>' for k in '㉠㉡㉢㉣') + '</tr>'
    body = ''.join('<tr>' + ''.join(f'<td style="text-align:center">{c}</td>' for c in r) + '</tr>' for r in rows)
    q['ctab'] = f'<table class="ht plain">{head}{body}</table>'
    q['choices'] = []
    q['blocks'] = [b for b in q['blocks'] if b['type'] != 'tabrows']
FIX = {193: _q193}

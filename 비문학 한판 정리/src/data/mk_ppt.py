"""PPT 변환본(A.dsl/B.dsl) → 배부용 데이터. 손본 곳은 모두 여기 적어 둔다."""
import sys, re
def sub(t, a, b, n=1):
    assert t.count(a) == n, (a, t.count(a)); return t.replace(a, b)
def clean(t):
    t = re.sub(r'^# --- slide \d+\n', '', t, flags=re.M)
    t = t.replace('imgw/', 'img/')
    return re.sub(r'\n{3,}', '\n\n', t)
src, which, out = sys.argv[1:4]
t = open(src, encoding='utf8').read()
if which == 'A':
    head = ('@meta school 부산외고 2학년\n@meta title 2025학년도 6월·9월·수능 비문학 한판 정리\n'
            '@meta exam 2026년 2학기 기말고사 대비\n@meta cover 2025학년도 6월·9월·수능|비문학 한판 정리\n'
            '@meta file 부산외고2_2025_6월9월수능_비문학_한판정리\n\n')
    t = sub(t, '@slide 보완책 ②와 함정', '@slide 보완책 ②')          # 함정 포인트 삭제 후 제목에 남은 말
    t = sub(t, '@slide 결정 영역과 함정', '@slide 결정 영역')
    t = sub(t, '@slide 판례와 함정', '@slide 판례')
    t = sub(t, '@slide 중국: 보충과 (가)·(나) 연결', '@slide 중국: 보충')  # 연결 상자 삭제됨
    t = sub(t, '# --- slide 12\n@slide 폴리에틸렌 중합 과정\n', '')        # 그림 슬라이드 → 앞 슬라이드에 붙임
    t = sub(t, '@slide 에이어의 논증\n@h 1. 에이어의 논증', '@slide 에이어의 논증\n@h (가) 에이어\n@h 1. 에이어의 논증')
    t = sub(t, '@h 3. 사람들이 오해하는 이유', '@h 2. 사람들이 오해하는 이유')  # 1 다음 번호
    t = sub(t, '@slide 전건 긍정식과 문제 제기 (1)', '@slide 전건 긍정식과 문제 제기')
    t = sub(t, '@slide 전건 긍정식과 문제 제기 (2)\n', '')
    t = sub(t, '@slide 재판매 가격 유지 행위 (1)', '@slide 재판매 가격 유지 행위')
    t = sub(t, '@slide 재판매 가격 유지 행위 (2)\n@h 1. 재판매 가격 유지 행위 (공정거래법, 원칙적 금지)\n', '')
    t = sub(t, '# --- slide 27\n@h 2. 새 블록이 연결되는 과정\n@img imgw/s27_그림30.png\n@img imgw/s27_그림28.png\n@img imgw/s27_그림26.png\n@img imgw/s27_그림32.png',
            '@imgs imgw/s27_그림26.png imgw/s27_그림28.png imgw/s27_그림30.png imgw/s27_그림32.png')
    t = sub(t, '@slide 정신분석학: 카메라 시점 동일시\n@h 2. 동일시의 종류\n', '@slide 정신분석학: 카메라 시점 동일시\n')
    t = sub(t, '@slide 가상 공간과 인터넷 ID\n@h 1. 자기표현과 가상 공간\n', '@slide 가상 공간과 인터넷 ID\n')
    t = sub(t, '제3자의 인식 여부는 책임의 . 근거가', '제3자의 인식 여부는 책임의 근거가')
    t = sub(t, '@img imgw/s10_그림8.png', '@img imgw/s10_그림8.png 50')
else:
    head = ('@meta school 부산국제고 1학년\n@meta title 김T 통합 교재 비문학 한판 정리\n'
            '@meta exam 2026년 2학기 기말고사 대비\n@meta cover 김T 통합 교재|비문학 한판 정리\n'
            '@meta file 부산국제고1_김T통합_비문학_한판정리\n\n')
    # 발달 과정 (1)(2): 한 표로
    m = re.search(r'@slide 발달 과정 \(1\)\n@h 2\. 발달 과정\n(.*?)\n\n# --- slide 5\n@slide 발달 과정 \(2\)\n@h 2\. 발달 과정\n\| \*\*단계\*\* \| \*\*특징\*\* \| \*\*의의 또는 한계\*\* \|\n', t, re.S)
    assert m
    t = t[:m.start()] + '@slide 발달 과정\n@h 2. 발달 과정\n' + m.group(1) + '\n' + t[m.end():]
    t = sub(t, '@slide 원인과 피해 확대\n@h 2. 문단별 내용\n', '@slide 원인과 피해 확대\n')
    t = sub(t, '@slide 본론 ①', '@slide 본론과 결론')     # 이 슬라이드에 본론 ②·결론도 있음
    t = sub(t, '  - **갑작스러운 지출을 감당할 수 있다:** 16.8%p 높음 - **소득이 없을 때 대응할 수 있다:** 12.6%p 높음',
            '  - **갑작스러운 지출을 감당할 수 있다:** 16.8%p 높음\n  - **소득이 없을 때 대응할 수 있다:** 12.6%p 높음')
    t = sub(t, '  - **구매를 신중하게 하는가:** 35점 높음 - **카드 대금을 납부일 안에 내는가:** 27.1점 높음',
            '  - **구매를 신중하게 하는가:** 35점 높음\n  - **카드 대금을 납부일 안에 내는가:** 27.1점 높음')
    t = sub(t, '**원인 :**', '**원인:**')
    t = sub(t, '**★ (가)의 관점으로 (나)·(다) 읽기**\n', '@box ★ (가)의 관점으로 (나)·(다) 읽기\n')
    t = sub(t, '- (다) "유대인을 죽여라"라는 군중: 부추김에 사람 사냥에 나서는 대중\n',
            '- **(다) "유대인을 죽여라"라는 군중:** 부추김에 사람 사냥에 나서는 대중\n@endbox\n')
    t = sub(t, '- **뉴욕타임스 논설위원 오크스의 편지**\n매카시즘은 모두의 말과 글과 사고에 영향을 미쳤다. 공격 대상이 될까 봐 더 조심하게 되었다.\n매카시가 사라져도',
            '- **뉴욕타임스 논설위원 오크스의 편지** // 매카시즘은 모두의 말과 글과 사고에 영향을 미쳤다. 공격 대상이 될까 봐 더 조심하게 되었다. 매카시가 사라져도')
    t = sub(t, '- **더 두드러지는 상황** 불확실할 때', '- **더 두드러지는 상황** // 불확실할 때')
    t = t[:t.index('# --- slide 38\n')]   # 마지막 '05·06·07 묶어 보기'는 빼기로 함(사용자 요청)
open(out, 'w', encoding='utf8').write(head + clean(t).strip() + '\n')

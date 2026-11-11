"""손으로 정한 배치. 문항 번호 앞에서 단/쪽을 나눈다. 열쇠는 (작품, 번호)."""
CH = '춘향전'
Q_BREAK = {(CH, 7): 'col', (CH, 9): 'col', ('춘향전 추가', 6): 'col'}
SET_BREAK = {}
CLOSE = set()
ANSWER_LINES = 8
SPLIT_CH = set()
KEEP_Q = set()

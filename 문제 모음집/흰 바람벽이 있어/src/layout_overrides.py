"""손으로 정한 배치. 문항 번호 앞에서 단/쪽을 나눈다. 열쇠는 (묶음, 번호)."""
# 'col' = 다음 단에서 시작, 'page' = 다음 쪽에서 시작, 'here' = 앞 문항 바로 아래에서 시작
Q_BREAK = {}
SET_BREAK = {}
CLOSE = set()
ANSWER_LINES = 8

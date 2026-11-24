"""손으로 정한 배치. 열쇠는 ('모의', 문항 번호 또는 '서답형 n')."""
Q_BREAK = {}
SET_BREAK = {}
CLOSE = set()
ANSWER_LINES = 7
SPLIT_CH = {('모의', '28')}   # 28번: 선지 ①을 <보기> 아래 혼자 두지 않고 ②~⑤와 함께 다음 단으로
KEEP_Q = set()

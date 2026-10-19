#!/bin/sh
# 사용: sh make.sh [데이터폴더]   (기본: src/data — {sw1,sw2,hg1,hg2}/out.json, 원본 PDF에서 옮긴 그대로)
# PDF판을 먼저 만들고, 그 배치(decisions.json)와 쪽수로 한글 파일을 만든다.
set -e
H=$(cd "$(dirname "$0")" && pwd); W=$(cd "${1:-$H/data}" && pwd); OUT="$H/.."
NAME="국제고 1학년 선운사에서·한 그리움이 다른 그리움에게 교재"
export NODE_PATH=${NODE_PATH:-$(npm root -g)}
python3 -I "$H/pdf/render.py" "$W" "$H/pdf/out.html"
node "$H/pdf/print.js" "$H/pdf/out.html" "$OUT/$NAME.pdf"
node "$H/pdf/decide.js" "$H/pdf/out.html" "$H/pdf/decisions.json"
P=$(pdfinfo "$OUT/$NAME.pdf" | awk '/^Pages/{print $2}')
TOTAL_PAGES=$((P - 1)) python3 -I "$H/build.py" "$W" "$OUT/$NAME.hwp"
rm -f "$H/pdf/out.html"

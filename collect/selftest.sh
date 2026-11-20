#!/bin/zsh
# selftest.html をヘッドレスChromeで走らせ、FAIL 0件なら exit 0
cd "$(dirname $0)/.." || exit 1
PORT=8765
/usr/bin/python3 -m http.server $PORT --bind 127.0.0.1 >/dev/null 2>&1 & SRV=$!
sleep 1
OUT=$("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-first-run --user-data-dir=$(mktemp -d /tmp/tadayomi-chrome.XXXX) --virtual-time-budget=60000 --dump-dom "http://127.0.0.1:$PORT/selftest.html" 2>/dev/null)
kill $SRV 2>/dev/null
RES=$(print -r -- "$OUT" | /usr/bin/python3 -c 'import sys,re,html;m=re.search(r"<pre id=\"out\">(.*?)</pre>",sys.stdin.read(),re.S);print(html.unescape(m.group(1)) if m else "NO OUTPUT")')
print -r -- "$RES" > collect/logs/selftest-last.txt
print -r -- "$RES" | grep -c '^PASS' | xargs echo PASS:
if print -r -- "$RES" | grep -q '^FAIL' || ! print -r -- "$RES" | grep -q '^PASS'; then print -r -- "$RES" | grep -v '^PASS'; exit 1; fi

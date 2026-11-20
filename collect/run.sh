#!/bin/zsh
# 毎朝: 収集 → build → selftest → commit & push。launchd com.yuki.tadayomi-collect から 07:00 と 12:00（回収用）に起動
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin
cd /Users/yuki/tadayomi || exit 1
LOG=collect/logs; mkdir -p $LOG
TODAY=$(TZ=Asia/Tokyo date +%F)
[[ "$(cat $LOG/.last-success 2>/dev/null)" == "$TODAY" && "$1" != "--force" ]] && { echo "$TODAY 済み"; exit 0; }
mkdir /tmp/tadayomi-collect.lock 2>/dev/null || { echo "多重起動のため終了"; exit 0; }
trap 'rmdir /tmp/tadayomi-collect.lock' EXIT
( sleep 900; kill -9 $$ ) 2>/dev/null & WD=$!
fail(){ echo "NG: $1"; git checkout -- . 2>/dev/null; osascript -e "display notification \"$1\" with title \"タダヨミ収集\"" 2>/dev/null; kill $WD; exit 1; }
echo "=== $(date '+%F %T') start"
git pull -q --rebase origin main || fail "git pull 失敗"
/usr/bin/python3 collect/collect.py --test || fail "X告知パーサの自己テストNG"
/usr/bin/python3 collect/collect.py > $LOG/collect-last.json || fail "収集NG（data.json は前回のまま）"
/usr/bin/python3 build.py || fail "build 失敗"
zsh collect/selftest.sh || fail "selftest FAIL（変更は破棄・公開は前回のまま）"
git add -A data.json collect *.html app.js common.css
git diff --cached --quiet || git commit -qm "タダヨミ 自動収集 $TODAY（$(/usr/bin/python3 -c 'import json;d=json.load(open("data.json"));print(len(d["items"]),"件")')）" 
git push -q origin HEAD:main || fail "git push 失敗"
echo $TODAY > $LOG/.last-success
echo "=== $(date '+%F %T') ok"
kill $WD

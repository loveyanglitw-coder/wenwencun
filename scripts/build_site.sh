#!/usr/bin/env bash
# 組出要發布的網站：公開版在根目錄、個人版在 /me/，兩邊用同一份 index.html，所以每次更新會同步
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _site && mkdir -p _site/me/icons _site/icons
for d in _site _site/me; do
  cp index.html sw.js firebase-config.js "$d/"
  cp -r data "$d/"
done
cp icons/icon-*.png _site/icons/
for s in 180 192 512; do cp "icons/personal-$s.png" "_site/me/icons/icon-$s.png"; done
cp editions/public.js _site/edition.js;   cp editions/manifest-public.json _site/manifest.json
cp editions/personal.js _site/me/edition.js; cp editions/manifest-personal.json _site/me/manifest.json
touch _site/.nojekyll
echo "公開版 → /    個人版 → /me/"

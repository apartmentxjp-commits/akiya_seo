#!/bin/bash
# deploy.sh — Hugo ビルド → Git push を一括実行
# 使い方: bash scripts/deploy.sh
# または: bash scripts/deploy.sh "コミットメッセージ"

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "📥 Step 0: リモートの最新を取得..."
git pull --rebase origin main 2>/dev/null || true

echo "🔨 Step 1: Hugo ビルド..."
cd site && hugo --minify --destination ../docs
cd "$ROOT"

echo "📦 Step 2: Git コミット & プッシュ..."
MSG="${1:-Auto-publish: $(date '+%Y-%m-%d %H:%M')}"

git add docs/ site/content/ site/static/ site/layouts/ scripts/ akiya_gen.py 2>/dev/null || git add docs/ site/content/
git commit -m "$MSG" || echo "Nothing to commit."
git push origin main || (git pull origin main -X ours --no-rebase && git push origin main)

echo "✅ デプロイ完了！ → https://akiya.tacky-consulting.com"

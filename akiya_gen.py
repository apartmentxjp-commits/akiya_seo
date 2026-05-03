#!/usr/bin/env python3
"""
akiya_gen.py — 空き家バンク・古民家情報センター 記事自動生成
API フォールバック: OpenRouter → Gemini → Groq
"""

import os, json, re, time, random, datetime, urllib.request, urllib.error, hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── API 設定 ──────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODELS  = [
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-4-scout:free",
    "mistralai/mistral-7b-instruct:free",
]

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS   = ["gemma-3-27b-it", "gemini-2.0-flash-lite", "gemma-4-26b-a4b-it"]

GROQ_KEYS   = [k for k in [os.getenv("GROQ_API_KEY",""), os.getenv("GROQ_API_KEY_2","")] if k]
GROQ_MODELS = ["llama-3.1-8b-instant","llama-3.3-70b-versatile","gemma2-9b-it","mixtral-8x7b-32768"]

CONTENT_DIR = Path(__file__).parent / "site" / "content" / "post"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

# ── 都道府県マスタ ─────────────────────────────────────────
PREFECTURES = [
    ("北海道","hokkaido"),("青森県","aomori"),("岩手県","iwate"),("宮城県","miyagi"),
    ("秋田県","akita"),("山形県","yamagata"),("福島県","fukushima"),("茨城県","ibaraki"),
    ("栃木県","tochigi"),("群馬県","gunma"),("埼玉県","saitama"),("千葉県","chiba"),
    ("東京都","tokyo"),("神奈川県","kanagawa"),("新潟県","niigata"),("富山県","toyama"),
    ("石川県","ishikawa"),("福井県","fukui"),("山梨県","yamanashi"),("長野県","nagano"),
    ("岐阜県","gifu"),("静岡県","shizuoka"),("愛知県","aichi"),("三重県","mie"),
    ("滋賀県","shiga"),("京都府","kyoto"),("大阪府","osaka"),("兵庫県","hyogo"),
    ("奈良県","nara"),("和歌山県","wakayama"),("鳥取県","tottori"),("島根県","shimane"),
    ("岡山県","okayama"),("広島県","hiroshima"),("山口県","yamaguchi"),("徳島県","tokushima"),
    ("香川県","kagawa"),("愛媛県","ehime"),("高知県","kochi"),("福岡県","fukuoka"),
    ("佐賀県","saga"),("長崎県","nagasaki"),("熊本県","kumamoto"),("大分県","oita"),
    ("宮崎県","miyazaki"),("鹿児島県","kagoshima"),("沖縄県","okinawa"),
]

# ── 記事タイプ定義 ────────────────────────────────────────
ARTICLE_TYPES = [
    {
        "type": "akiya_bank",
        "label": "空き家バンク",
        "title_template": "{pref}の空き家バンク完全ガイド【{year}年版】物件探しから購入まで",
        "prompt_template": (
            "あなたは日本の空き家・空き家バンク専門ライターです。\n"
            "{pref}の空き家バンク制度について詳しく解説する記事を日本語で書いてください。\n\n"
            "必須セクション:\n"
            "## {pref}の空き家バンクとは\n"
            "## 登録物件の特徴と相場（{pref}の傾向）\n"
            "## 空き家バンクの利用手順（ステップ別）\n"
            "## {pref}ならではの魅力・移住メリット\n"
            "## よくある質問\n\n"
            "条件: 800〜1200文字、マークダウン形式、具体的な数字や地名を含む、"
            "SEOキーワード「{pref} 空き家バンク 購入」を自然に含める"
        ),
    },
    {
        "type": "renovation",
        "label": "古民家リノベーション",
        "title_template": "{pref}の古民家リノベーション費用・事例まとめ【{year}年最新】",
        "prompt_template": (
            "あなたは日本の古民家リノベーション専門ライターです。\n"
            "{pref}の古民家リノベーションについて詳しく解説する記事を日本語で書いてください。\n\n"
            "必須セクション:\n"
            "## {pref}の古民家リノベーションの特徴\n"
            "## 費用の目安と内訳（{pref}の相場）\n"
            "## 古民家購入からリノベーションまでの流れ\n"
            "## 補助金・支援制度（{pref}で使えるもの）\n"
            "## 失敗しないための注意点\n\n"
            "条件: 800〜1200文字、マークダウン形式、具体的な費用感を含む、"
            "SEOキーワード「{pref} 古民家 リノベーション 費用」を自然に含める"
        ),
    },
    {
        "type": "migration",
        "label": "地方移住",
        "title_template": "{pref}への移住支援制度まとめ【{year}年】補助金・サポート情報",
        "prompt_template": (
            "あなたは地方移住・田舎暮らし専門ライターです。\n"
            "{pref}への移住支援について詳しく解説する記事を日本語で書いてください。\n\n"
            "必須セクション:\n"
            "## {pref}の移住支援制度一覧\n"
            "## 移住支援金・補助金の詳細（金額・条件）\n"
            "## {pref}で暮らす魅力・生活コスト\n"
            "## 移住者の声・体験談（例として）\n"
            "## 移住相談窓口・問い合わせ先\n\n"
            "条件: 800〜1200文字、マークダウン形式、具体的な支援金額を含む（例：最大100万円）、"
            "SEOキーワード「{pref} 移住 支援 補助金」を自然に含める"
        ),
    },
    {
        "type": "subsidy",
        "label": "補助金・支援制度",
        "title_template": "{pref}の空き家活用補助金ガイド【{year}年】申請方法と注意点",
        "prompt_template": (
            "あなたは不動産補助金・行政支援制度の専門ライターです。\n"
            "{pref}の空き家活用に使える補助金・支援制度について詳しく解説する記事を日本語で書いてください。\n\n"
            "必須セクション:\n"
            "## {pref}で使える空き家補助金の種類\n"
            "## 国の空き家補助金制度（全国共通）\n"
            "## {pref}独自の補助金・支援制度\n"
            "## 補助金の申請手順と注意点\n"
            "## よくある質問・Q&A\n\n"
            "条件: 800〜1200文字、マークダウン形式、金額・条件を具体的に記述、"
            "SEOキーワード「{pref} 空き家 補助金 申請」を自然に含める"
        ),
    },
]

# ── API 呼び出し関数 ─────────────────────────────────────

def _post_json(url: str, payload: dict, headers: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call_openrouter(prompt: str, model_idx: int = 0) -> str:
    if not OPENROUTER_API_KEY:
        return call_gemini(prompt)
    model = OPENROUTER_MODELS[model_idx % len(OPENROUTER_MODELS)]
    try:
        res = _post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {"model": model, "messages": [{"role":"user","content": prompt}], "max_tokens": 2000},
            {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        )
        return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [OpenRouter {model}] failed: {e}")
        if model_idx + 1 < len(OPENROUTER_MODELS):
            return call_openrouter(prompt, model_idx + 1)
        return call_gemini(prompt)


def call_gemini(prompt: str, model_idx: int = 0) -> str:
    if not GEMINI_API_KEY:
        return call_groq(prompt)
    model = GEMINI_MODELS[model_idx % len(GEMINI_MODELS)]
    url   = f"{GEMINI_BASE_URL}/{model}:generateContent?key={GEMINI_API_KEY}"
    try:
        res = _post_json(
            url,
            {"contents":[{"parts":[{"text": prompt}]}], "generationConfig":{"maxOutputTokens":2000}},
            {"Content-Type": "application/json"},
        )
        return res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"  [Gemini {model}] failed: {e}")
        if model_idx + 1 < len(GEMINI_MODELS):
            return call_gemini(prompt, model_idx + 1)
        return call_groq(prompt)


def call_groq(prompt: str, key_idx: int = 0, model_idx: int = 0) -> str:
    if not GROQ_KEYS:
        raise RuntimeError("No API keys available")
    key   = GROQ_KEYS[key_idx % len(GROQ_KEYS)]
    model = GROQ_MODELS[model_idx % len(GROQ_MODELS)]
    try:
        res = _post_json(
            "https://api.groq.com/openai/v1/chat/completions",
            {"model": model, "messages": [{"role":"user","content": prompt}], "max_tokens": 2000},
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [Groq {model}] failed: {e}")
        if model_idx + 1 < len(GROQ_MODELS):
            return call_groq(prompt, key_idx, model_idx + 1)
        if key_idx + 1 < len(GROQ_KEYS):
            return call_groq(prompt, key_idx + 1, 0)
        raise RuntimeError(f"All APIs failed: {e}")

# ── フロントマター生成 ─────────────────────────────────────

def generate_frontmatter(title: str, description: str, pref_name: str, pref_slug: str, atype: str) -> str:
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    keywords_map = {
        "akiya_bank":   [f"{pref_name} 空き家バンク", "空き家 購入", "空き家バンク 物件", f"{pref_name} 空き家"],
        "renovation":   [f"{pref_name} 古民家", "古民家 リノベーション 費用", f"{pref_name} 古民家 購入", "古民家 補助金"],
        "migration":    [f"{pref_name} 移住", "地方移住 支援", f"{pref_name} 田舎暮らし", "移住 補助金"],
        "subsidy":      [f"{pref_name} 空き家 補助金", "空き家活用 補助金", f"{pref_name} 補助金 申請", "空き家 支援制度"],
    }
    kws = keywords_map.get(atype, [])
    kw_yaml = "\n".join(f'  - "{k}"' for k in kws)
    return f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%dT%H:%M:%S+09:00")}
description: "{description}"
prefecture: "{pref_name}"
prefecture_slug: "{pref_slug}"
article_type: "{atype}"
keywords:
{kw_yaml}
---
"""

# ── スラッグ生成 ──────────────────────────────────────────

def make_slug(pref_slug: str, atype: str) -> str:
    ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y%m%d%H%M")
    return f"{pref_slug}-{atype}-{ts}"

# ── 記事生成メイン ────────────────────────────────────────

def generate_article(pref_name: str, pref_slug: str, article_type: dict) -> bool:
    year  = datetime.datetime.now().year
    title = article_type["title_template"].format(pref=pref_name, year=year)
    prompt = article_type["prompt_template"].format(pref=pref_name, year=year)

    print(f"  生成中: {title}")
    try:
        body = call_openrouter(prompt)
    except Exception as e:
        print(f"  ❌ 全API失敗: {e}")
        return False

    # 説明文（本文の最初の段落）
    lines = [l.strip() for l in body.split("\n") if l.strip() and not l.startswith("#")]
    description = lines[0][:120] if lines else title

    slug = make_slug(pref_slug, article_type["type"])
    fm   = generate_frontmatter(title, description, pref_name, pref_slug, article_type["type"])
    content = fm + "\n" + body

    out = CONTENT_DIR / f"{slug}.md"
    out.write_text(content, encoding="utf-8")
    print(f"  ✅ 保存: {out.name}")
    return True

# ── 生成済みチェック ──────────────────────────────────────

def already_generated(pref_slug: str, atype: str) -> bool:
    return any(f.stem.startswith(f"{pref_slug}-{atype}-") for f in CONTENT_DIR.glob("*.md"))

# ── エントリポイント ──────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Akiya SEO 記事生成")
    parser.add_argument("--count", type=int, default=10, help="生成記事数（デフォルト:10）")
    parser.add_argument("--pref",  type=str, default=None, help="特定の都道府県スラッグのみ生成")
    parser.add_argument("--type",  type=str, default=None, help="記事タイプ（akiya_bank/renovation/migration/subsidy）")
    parser.add_argument("--all",   action="store_true", help="全都道府県×全タイプを生成（188記事）")
    args = parser.parse_args()

    # 対象フィルタリング
    prefectures = PREFECTURES
    if args.pref:
        prefectures = [(n,s) for n,s in PREFECTURES if s == args.pref]

    atypes = ARTICLE_TYPES
    if args.type:
        atypes = [a for a in ARTICLE_TYPES if a["type"] == args.type]

    # 生成タスクキューを作成（未生成のもの優先）
    tasks = []
    for pref_name, pref_slug in prefectures:
        for atype in atypes:
            if not already_generated(pref_slug, atype["type"]):
                tasks.append((pref_name, pref_slug, atype))

    random.shuffle(tasks)

    if not args.all:
        tasks = tasks[:args.count]

    print(f"🏠 Akiya SEO ジェネレーター起動")
    print(f"📋 生成予定: {len(tasks)} 記事")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    success = 0
    for i, (pref_name, pref_slug, atype) in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {pref_name} / {atype['label']}")
        if generate_article(pref_name, pref_slug, atype):
            success += 1
        if i < len(tasks):
            time.sleep(2)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 完了: {success}/{len(tasks)} 記事生成")

if __name__ == "__main__":
    main()

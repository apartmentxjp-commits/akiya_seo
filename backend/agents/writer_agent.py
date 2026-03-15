"""
Writer Agent - Groq (Llama 3.3 70b) による空き家・古民家記事自動執筆エージェント
役割: SEO最適化された空き家バンク・地方移住・古民家リノベ記事を自動生成
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Optional
from groq import Groq
from slugify import slugify

MODEL = "llama-3.3-70b-versatile"

ARTICLE_SYSTEM_PROMPT = """
あなたは空き家・古民家・地方移住の専門ライターです。
SEO・AIO（AI Overview）対策に優れた、日本の空き家・古民家情報記事を執筆します。

執筆ルール:
1. 見出し構造 (H2, H3) を明確に使用する
2. 具体的な数値・データを含める（物件価格、面積、築年数など）
3. 読者の疑問に直接答えるQ&A形式を含める
4. 地域の特性・生活環境・移住支援情報も記述する
5. 必ず「まとめ」セクションを末尾に入れる
6. 文体: 丁寧語、専門的かつ読みやすく
7. 文字数: 1500〜2500文字
8. Markdown形式で出力

AIO対策:
- 冒頭の100文字以内に記事の核心情報を入れる
- 箇条書きで要点をまとめるセクションを含める
- FAQセクションを含める (3〜5問)

重点テーマ:
- 空き家バンク活用方法
- 古民家リノベーション費用・事例
- 地方移住補助金・支援制度
- 田舎暮らし・スローライフ
- DIYリフォーム情報
"""

SEO_SYSTEM_PROMPT = """
あなたはSEO専門家です。
与えられた記事からSEOメタデータを生成します。
必ずJSON形式のみで回答してください。前置きや説明は不要です。

出力形式:
{
  "meta_title": "60文字以内のタイトル",
  "meta_description": "120〜160文字の説明文",
  "keywords": ["キーワード1", "キーワード2", ...],
  "og_title": "OGPタイトル",
  "structured_data": {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "記事タイトル",
    "description": "説明",
    "keywords": "キーワード"
  }
}
"""


class WriterAgent:
    """Groq (Llama 3.3 70b) 空き家記事執筆エージェント"""

    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

    async def generate_article(
        self,
        area: str,
        prefecture: str,
        property_type: str,
        price_avg: Optional[int] = None,
        unit_price: Optional[int] = None,
        extra_context: str = "",
    ) -> dict:
        """指定エリア・物件種別の空き家・古民家記事を生成"""

        price_info = ""
        if price_avg:
            price_info = f"平均価格: 約{price_avg:,}万円"
        if unit_price:
            price_info += f"、坪単価: 約{unit_price}万円/㎡"

        prompt = f"""
以下の条件で空き家・古民家・地方移住に関する情報記事を執筆してください。

対象エリア: {prefecture} {area}
物件種別: {property_type}
価格情報: {price_info or '空き家バンク相場を参考に'}
追加情報: {extra_context}

記事タイトルも含めて、Markdown形式で出力してください。
地元の空き家バンク情報、移住支援制度、リノベーション事例なども積極的に盛り込んでください。
"""

        start = time.time()
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=MODEL,
                messages=[
                    {"role": "system", "content": ARTICLE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
            )
            content = response.choices[0].message.content
            duration_ms = int((time.time() - start) * 1000)

            # タイトル抽出 (最初の # 行)
            title = area + " " + property_type + "の空き家情報"
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break

            # スラッグ生成
            slug = slugify(f"{prefecture}-{area}-{property_type}-{datetime.now().strftime('%Y%m%d%H%M')}", allow_unicode=False)
            slug = slug.replace("--", "-")

            # SEOメタデータ生成
            seo_data = await self._generate_seo(title, content, area, property_type)

            return {
                "slug": slug,
                "title": title,
                "content": content,
                "excerpt": self._extract_excerpt(content),
                "area": area,
                "prefecture": prefecture,
                "property_type": property_type,
                "status": "published",
                "generated_by": "groq",
                "generation_prompt": prompt,
                "duration_ms": duration_ms,
                **seo_data,
            }

        except Exception as e:
            raise RuntimeError(f"記事生成エラー: {e}")

    async def _generate_seo(self, title: str, content: str, area: str, property_type: str) -> dict:
        """SEOメタデータをGroqで生成"""
        prompt = f"""
記事タイトル: {title}
対象: {area}の{property_type}情報

記事の最初の500文字:
{content[:500]}

上記のSEOメタデータをJSON形式で生成してください。
"""
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=MODEL,
                messages=[
                    {"role": "system", "content": SEO_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )
            text = response.choices[0].message.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            seo = json.loads(text.strip())
            return {
                "meta_title": seo.get("meta_title", title[:60]),
                "meta_description": seo.get("meta_description", ""),
                "keywords": seo.get("keywords", [area, property_type, "空き家", "古民家"]),
                "structured_data": seo.get("structured_data", {}),
            }
        except Exception:
            return {
                "meta_title": title[:60],
                "meta_description": f"{area}の{property_type}情報。空き家バンク・移住支援・リノベーション事例をご紹介します。",
                "keywords": [area, property_type, "空き家", "古民家", "地方移住", "リノベーション"],
                "structured_data": {},
            }

    def _extract_excerpt(self, content: str, max_len: int = 200) -> str:
        """記事から抜粋を抽出"""
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        text = " ".join(lines[:3])
        return text[:max_len] + "..." if len(text) > max_len else text


# ── バッチ記事生成 ────────────────────────────────────
# 50トピック × 30分間隔 = 25時間で一巡（1日48記事）
ARTICLE_TOPICS = [
    # 北海道
    {"area": "札幌市", "prefecture": "北海道", "property_type": "空き家"},
    {"area": "函館市", "prefecture": "北海道", "property_type": "古民家"},
    {"area": "富良野市", "prefecture": "北海道", "property_type": "古民家"},
    {"area": "ニセコ町", "prefecture": "北海道", "property_type": "空き家"},
    # 東北
    {"area": "弘前市", "prefecture": "青森県", "property_type": "古民家"},
    {"area": "角館", "prefecture": "秋田県", "property_type": "古民家"},
    {"area": "会津若松市", "prefecture": "福島県", "property_type": "古民家"},
    {"area": "仙台市", "prefecture": "宮城県", "property_type": "空き家"},
    # 関東
    {"area": "秩父市", "prefecture": "埼玉県", "property_type": "古民家"},
    {"area": "房総半島", "prefecture": "千葉県", "property_type": "古民家"},
    {"area": "南房総市", "prefecture": "千葉県", "property_type": "空き家"},
    {"area": "奥多摩町", "prefecture": "東京都", "property_type": "古民家"},
    {"area": "小田原市", "prefecture": "神奈川県", "property_type": "古民家"},
    # 北陸・甲信越
    {"area": "金沢市", "prefecture": "石川県", "property_type": "古民家"},
    {"area": "白川郷", "prefecture": "岐阜県", "property_type": "合掌造り"},
    {"area": "飛騨高山", "prefecture": "岐阜県", "property_type": "古民家"},
    {"area": "松本市", "prefecture": "長野県", "property_type": "古民家"},
    {"area": "佐久市", "prefecture": "長野県", "property_type": "空き家"},
    {"area": "富士河口湖町", "prefecture": "山梨県", "property_type": "古民家"},
    # 東海
    {"area": "伊豆半島", "prefecture": "静岡県", "property_type": "空き家"},
    {"area": "浜松市", "prefecture": "静岡県", "property_type": "古民家"},
    {"area": "伊賀市", "prefecture": "三重県", "property_type": "古民家"},
    # 関西
    {"area": "京都市", "prefecture": "京都府", "property_type": "京町家"},
    {"area": "亀岡市", "prefecture": "京都府", "property_type": "古民家"},
    {"area": "奈良市", "prefecture": "奈良県", "property_type": "古民家"},
    {"area": "吉野町", "prefecture": "奈良県", "property_type": "古民家"},
    {"area": "和歌山市", "prefecture": "和歌山県", "property_type": "空き家"},
    {"area": "熊野", "prefecture": "和歌山県", "property_type": "古民家"},
    {"area": "篠山市", "prefecture": "兵庫県", "property_type": "古民家"},
    {"area": "淡路島", "prefecture": "兵庫県", "property_type": "空き家"},
    # 中国・四国
    {"area": "津山市", "prefecture": "岡山県", "property_type": "古民家"},
    {"area": "尾道市", "prefecture": "広島県", "property_type": "古民家"},
    {"area": "江津市", "prefecture": "島根県", "property_type": "空き家"},
    {"area": "大山町", "prefecture": "鳥取県", "property_type": "古民家"},
    {"area": "徳島県", "prefecture": "徳島県", "property_type": "空き家"},
    {"area": "小豆島", "prefecture": "香川県", "property_type": "古民家"},
    {"area": "四万十市", "prefecture": "高知県", "property_type": "古民家"},
    # 九州・沖縄
    {"area": "唐津市", "prefecture": "佐賀県", "property_type": "古民家"},
    {"area": "長崎市", "prefecture": "長崎県", "property_type": "古民家"},
    {"area": "阿蘇市", "prefecture": "熊本県", "property_type": "古民家"},
    {"area": "日田市", "prefecture": "大分県", "property_type": "古民家"},
    {"area": "宮崎市", "prefecture": "宮崎県", "property_type": "空き家"},
    {"area": "鹿児島市", "prefecture": "鹿児島県", "property_type": "空き家"},
    {"area": "屋久島", "prefecture": "鹿児島県", "property_type": "古民家"},
    {"area": "那覇市", "prefecture": "沖縄県", "property_type": "古民家"},
    {"area": "石垣島", "prefecture": "沖縄県", "property_type": "空き家"},
    # テーマ別
    {"area": "移住支援が手厚い地域", "prefecture": "全国", "property_type": "古民家"},
    {"area": "100万円以下", "prefecture": "全国", "property_type": "空き家"},
    {"area": "海が見える", "prefecture": "全国", "property_type": "古民家"},
    {"area": "古民家カフェ開業", "prefecture": "全国", "property_type": "古民家リノベ"},
]

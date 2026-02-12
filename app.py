from __future__ import annotations

import datetime
import html
import json
import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib import error, request as urlrequest

from flask import Flask, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "blogger.db"

app = Flask(__name__)


@dataclass
class BlogPost:
    id: int
    title: str
    keywords: str
    content: str
    banner: str
    status: str
    created_at: str
    updated_at: str
    approved_by: str | None
    social_posted: int
    social_platform: str | None
    social_post_url: str | None
    social_caption: str | None


@dataclass
class SocialConfig:
    id: int
    platform: str
    org_name: str
    author_urn: str
    access_token: str
    is_active: int
    created_at: str
    updated_at: str


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                keywords TEXT NOT NULL,
                content TEXT NOT NULL,
                banner TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                approved_by TEXT,
                social_posted INTEGER NOT NULL DEFAULT 0,
                social_platform TEXT,
                social_post_url TEXT,
                social_caption TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS social_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                org_name TEXT NOT NULL,
                author_urn TEXT NOT NULL,
                access_token TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()
        }
        for col_name, col_type in [
            ("social_platform", "TEXT"),
            ("social_post_url", "TEXT"),
            ("social_caption", "TEXT"),
        ]:
            if col_name not in existing_columns:
                conn.execute(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}")

        conn.commit()


def fetch_posts(status: str | None = None) -> list[BlogPost]:
    query = "SELECT * FROM posts"
    params: Iterable[str] = []
    if status:
        query += " WHERE status = ?"
        params = [status]
    query += " ORDER BY created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [BlogPost(**row) for row in rows]


def fetch_post(post_id: int) -> BlogPost | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    return BlogPost(**row) if row else None


def fetch_active_social_config(platform: str = "linkedin") -> SocialConfig | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM social_configs
            WHERE platform = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (platform,),
        ).fetchone()
    return SocialConfig(**row) if row else None


def fetch_social_configs() -> list[SocialConfig]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM social_configs ORDER BY updated_at DESC"
        ).fetchall()
    return [SocialConfig(**row) for row in rows]


def build_trending_angles(topic: str, keywords: str) -> list[str]:
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] or ["industry trends"]
    seed = f"{topic.lower()}|{keywords.lower()}"
    rng = random.Random(seed)
    trend_pool = [
        "AI copilots entering daily workflows",
        "first-party data strategies replacing third-party tracking",
        "short-form video + newsletter hybrid distribution",
        "community-led demand generation",
        "compliance-first automation",
        "human-in-the-loop editorial QA",
        "creator partnerships and expert-led narratives",
        "search + social convergence through answer engines",
    ]
    selected = rng.sample(trend_pool, k=min(4, len(trend_pool)))
    selected.extend([f"{kw} adoption curve" for kw in keyword_list[:2]])
    return selected


def generate_professional_blog(topic: str, keywords: str) -> tuple[str, str, str]:
    title = f"{topic.title()}: Strategic Guide to {keywords.title()} in 2026"
    banner = f"{topic.title()} Growth Playbook"
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] or ["strategy", "execution"]
    trends = build_trending_angles(topic, keywords)
    today = datetime.date.today().strftime("%B %d, %Y")

    human_voice_intro = (
        "<p>Most teams are publishing more but connecting less. The gap is rarely effort—it is structure, "
        "timing, and audience empathy. This guide is designed to read like a human strategist wrote it: "
        "specific, practical, and directly tied to business outcomes.</p>"
    )

    sections = [
        f"<h1>{html.escape(title)}</h1>",
        f"<p><strong>Published:</strong> {today}</p>",
        human_voice_intro,
        "<h2>What Is Trending Right Now</h2>",
        "<ul>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in trends)
        + "</ul>",
        "<h2>Audience-First Content Architecture</h2>",
        "<p>Before writing, map the reader journey: awareness, evaluation, and decision. "
        "Every section should reduce uncertainty and increase confidence.</p>",
        "<h3>High-Engagement Structure</h3>",
        "<ol>"
        "<li><strong>Hook:</strong> Open with a relevant pain point in plain language.</li>"
        "<li><strong>Context:</strong> Explain why the topic matters now.</li>"
        "<li><strong>Framework:</strong> Provide a repeatable model readers can apply.</li>"
        "<li><strong>Proof:</strong> Include examples, mini case points, and realistic numbers.</li>"
        "<li><strong>Action:</strong> End with concrete next steps and metrics.</li>"
        "</ol>",
        f"<h2>Keyword Strategy for {html.escape(topic.title())}</h2>",
        "<p>Blend primary and secondary keywords naturally to keep the article discoverable yet readable. "
        "Avoid robotic repetition; optimize for clarity first.</p>",
        "<h3>Suggested Keyword Variations</h3>",
        "<ul>"
        + "".join(
            f"<li>{html.escape(k)}: use in headings, FAQ-style subpoints, and example snippets.</li>"
            for k in keyword_list
        )
        + "</ul>",
        "<h2>90-Day Execution Plan</h2>",
        "<h3>Phase 1: Foundation (Weeks 1-3)</h3>"
        "<p>Audit existing content, define positioning, and create a pillar article brief.</p>",
        "<h3>Phase 2: Production (Weeks 4-8)</h3>"
        "<p>Publish long-form content plus repurposed micro-content for social channels.</p>",
        "<h3>Phase 3: Amplification (Weeks 9-12)</h3>"
        "<p>Distribute through newsletter, social posting, creator partnerships, and remarketing.</p>",
        "<h2>Editorial Quality Checklist</h2>",
        "<ul>"
        "<li>Clear H1/H2/H3 hierarchy and scannable paragraphs.</li>"
        "<li>Balanced storytelling + actionable recommendations.</li>"
        "<li>Human tone (confident, concise, practical).</li>"
        "<li>Proof points, objections handled, and specific CTAs.</li>"
        "</ul>",
        "<h2>Final Takeaway</h2>",
        "<p>Winning content is not about sounding perfect. It is about being useful, specific, and trustworthy. "
        "Use this as your repeatable blueprint and iterate based on reader behavior.</p>",
    ]

    content = "\n".join(sections)
    return title, banner, content


def create_post(title: str, keywords: str, content: str, banner: str) -> None:
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO posts (title, keywords, content, banner, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, keywords, content, banner, "pending", now, now),
        )
        conn.commit()


def update_post(post_id: int, content: str, banner: str, status: str, approved_by: str | None) -> None:
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE posts
            SET content = ?, banner = ?, status = ?, approved_by = ?, updated_at = ?
            WHERE id = ?
            """,
            (content, banner, status, approved_by, now, post_id),
        )
        conn.commit()


def upsert_social_config(platform: str, org_name: str, author_urn: str, access_token: str) -> None:
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute("UPDATE social_configs SET is_active = 0 WHERE platform = ?", (platform,))
        conn.execute(
            """
            INSERT INTO social_configs (platform, org_name, author_urn, access_token, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (platform, org_name, author_urn, access_token, now, now),
        )
        conn.commit()


def build_social_caption(post: BlogPost) -> str:
    keyword_text = ", ".join(k.strip() for k in post.keywords.split(",") if k.strip())
    hashtags = " ".join(f"#{k.strip().replace(' ', '')}" for k in post.keywords.split(",") if k.strip())
    return (
        f"{post.title}\n\n"
        f"A practical guide on {keyword_text}.\n"
        "Read key trends, frameworks, and a 90-day execution plan.\n"
        f"{hashtags}".strip()
    )


def publish_to_linkedin(post: BlogPost, cfg: SocialConfig) -> tuple[bool, str]:
    caption = build_social_caption(post)
    payload = {
        "author": cfg.author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    req = urlrequest.Request(
        "https://api.linkedin.com/v2/ugcPosts",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            post_url = f"https://www.linkedin.com/feed/update/{response_body[:80]}"
            return True, post_url
    except error.HTTPError as exc:
        return False, f"LinkedIn API HTTP {exc.code}: {exc.reason}"
    except Exception as exc:  # broad error to capture local env/network issues
        return False, f"LinkedIn API error: {exc}"


def mark_social_posted(post_id: int, platform: str, caption: str, social_post_url: str) -> None:
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE posts
            SET social_posted = 1,
                social_platform = ?,
                social_caption = ?,
                social_post_url = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (platform, caption, social_post_url, now, post_id),
        )
        conn.commit()


@app.route("/")
def index() -> str:
    posts = fetch_posts()
    return render_template("index.html", posts=posts)


@app.route("/create")
def create() -> str:
    trending_samples = [
        "AI workflow automation",
        "B2B content personalization",
        "Zero-click search strategy",
        "Thought leadership with expert interviews",
    ]
    return render_template("create.html", trending_samples=trending_samples)


@app.route("/generate", methods=["POST"])
def generate() -> str:
    heading = request.form.get("heading", "").strip()
    keywords = request.form.get("keywords", "").strip()
    manual_content = request.form.get("manual_content", "").strip()

    if manual_content:
        title = heading or "Manual Draft"
        banner = request.form.get("banner", "").strip() or title
        content = manual_content
    else:
        title, banner, content = generate_professional_blog(
            heading or "High-Impact Content Strategy",
            keywords or "content marketing, engagement",
        )

    create_post(title, keywords or "manual", content, banner)
    return redirect(url_for("index"))


@app.route("/admin")
def admin() -> str:
    posts = fetch_posts(status="pending")
    return render_template("admin.html", posts=posts)


@app.route("/admin/post/<int:post_id>")
def admin_post(post_id: int) -> str:
    post = fetch_post(post_id)
    if not post:
        return redirect(url_for("admin"))
    return render_template("admin_post.html", post=post)


@app.route("/admin/post/<int:post_id>/approve", methods=["POST"])
def approve_post(post_id: int) -> str:
    content = request.form.get("content", "")
    banner = request.form.get("banner", "")
    approved_by = request.form.get("approved_by", "Admin")
    update_post(post_id, content, banner, "approved", approved_by)
    return redirect(url_for("view_post", post_id=post_id))


@app.route("/admin/post/<int:post_id>/needs-edit", methods=["POST"])
def needs_edit(post_id: int) -> str:
    content = request.form.get("content", "")
    banner = request.form.get("banner", "")
    update_post(post_id, content, banner, "needs_edit", None)
    return redirect(url_for("admin"))


@app.route("/settings/social")
def social_settings() -> str:
    configs = fetch_social_configs()
    return render_template("social_settings.html", configs=configs)


@app.route("/settings/social/save", methods=["POST"])
def social_settings_save() -> str:
    platform = request.form.get("platform", "linkedin").strip().lower()
    org_name = request.form.get("org_name", "").strip()
    author_urn = request.form.get("author_urn", "").strip()
    access_token = request.form.get("access_token", "").strip()

    if org_name and author_urn and access_token:
        upsert_social_config(platform, org_name, author_urn, access_token)
    return redirect(url_for("social_settings"))


@app.route("/post/<int:post_id>")
def view_post(post_id: int) -> str:
    post = fetch_post(post_id)
    social_cfg = fetch_active_social_config("linkedin")
    if not post:
        return redirect(url_for("index"))
    return render_template("post.html", post=post, social_cfg=social_cfg)


@app.route("/social/post/<int:post_id>", methods=["POST"])
def social_post(post_id: int) -> str:
    post = fetch_post(post_id)
    if not post or post.status != "approved":
        return redirect(url_for("view_post", post_id=post_id))

    cfg = fetch_active_social_config("linkedin")
    if not cfg:
        return redirect(url_for("social_settings"))

    ok, message = publish_to_linkedin(post, cfg)
    caption = build_social_caption(post)
    if ok:
        mark_social_posted(post.id, "linkedin", caption, message)
    else:
        mark_social_posted(post.id, "linkedin", caption, f"Failed: {message}")
    return redirect(url_for("view_post", post_id=post_id))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)

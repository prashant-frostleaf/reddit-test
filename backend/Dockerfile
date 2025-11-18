# Dockerfile (save in /backend)

FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .
# ===================final==================
# ==========================
# main.py
# ==========================================
# from fastapi import FastAPI, Query, Body
# from fastapi.middleware.cors import CORSMiddleware
# from config import db
# from datetime import datetime, timedelta
# from bson import ObjectId
# from collections import Counter, defaultdict
# from openai import OpenAI
# import os
# import re
# import json


from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()     # <--- THIS loads .env into environment variables
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from backend.config import db
from datetime import datetime, timedelta
from bson import ObjectId
from collections import Counter, defaultdict
import re
import os
from fastapi import FastAPI
import json


app = FastAPI(title="Reddit Data API", version="3.1")

# ---------- OpenAI Client (uses OPENAI_API_KEY env var) ----------
client = OpenAI()  # make sure OPENAI_API_KEY is set in your environment

# ---------- CORS for Streamlit ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helpers ----------
def serialize_post(post):
    post["_id"] = str(post["_id"])
    return post

def _to_date(obj_id):
    """Extract a UTC datetime from ObjectId (Mongo insert time)."""
    if isinstance(obj_id, ObjectId):
        return obj_id.generation_time  # aware datetime (UTC)
    return None

def _week_bucket(dt):
    """Return ISO week label like '2025-W07'."""
    iso = dt.isocalendar()
    return f"{dt.year}-W{iso[1]:02d}"

STOPWORDS = set("""
a an and the is are be to of in on for with at by from this that it as or if about
you your we our they their i me my he she his her them us was were been being do did does
""".split())

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-']+")

def tokenize(text: str):
    for w in WORD_RE.findall((text or "").lower()):
        if w not in STOPWORDS and 2 < len(w) < 30:
            yield w

# ---------- BASIC ROUTES ----------
@app.get("/")
def home():
    return {"message": "✅ Reddit Data API is running successfully!"}

@app.get("/posts")
def get_posts(limit: int = Query(10)):
    posts = list(db.posts.find().limit(limit))
    return [serialize_post(p) for p in posts]

@app.get("/posts/topic/{topic_name}")
def get_posts_by_topic(topic_name: str):
    posts = list(
        db.posts.find(
            {"metadata.topic": {"$regex": f"^{re.escape(topic_name)}$", "$options": "i"}}
        )
    )
    return [serialize_post(p) for p in posts]

@app.get("/posts/subreddit/{subreddit_name}")
def get_posts_by_subreddit(subreddit_name: str):
    posts = list(
        db.posts.find(
            {"subreddit": {"$regex": f"^{re.escape(subreddit_name)}$", "$options": "i"}}
        )
    )
    return [serialize_post(p) for p in posts]

# ---------- UPSERT (duplicate-proof) ----------
@app.post("/posts/upsert")
def upsert_post(post: dict = Body(...)):
    """
    Insert or update a Reddit post by metadata.document_id (avoids duplicates).
    Assumes your n8n pipeline sends a full post with metadata.document_id.
    """
    try:
        doc_id = (post.get("metadata") or {}).get("document_id")
        if not doc_id:
            return {"error": "metadata.document_id is required"}
        result = db.posts.update_one(
            {"metadata.document_id": doc_id},
            {"$set": post},
            upsert=True,
        )
        return {
            "status": "updated" if result.matched_count else "inserted",
            "document_id": doc_id,
        }
    except Exception as e:
        return {"error": str(e)}

# ======================================================
# 📊 ANALYTICS ROUTES – MARKETING VIEW
# ======================================================

# 1) Brand Awareness & Share of Voice (by topic/firm)
@app.get("/analytics/share_of_voice")
def share_of_voice():
    pipeline = [
        {"$group": {"_id": {"$toLower": "$metadata.topic"}, "count": {"$sum": 1}}},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"count": -1}},
    ]
    rows = list(db.posts.aggregate(pipeline))
    total = sum(r["count"] for r in rows) or 1
    out = []
    for r in rows:
        out.append(
            {
                "topic": r["_id"],
                "count": r["count"],
                "percent": round(100.0 * r["count"] / total, 2),
            }
        )
    return {"total": total, "items": out}

# 2) Sentiment Perception & Brand Health (per-topic)
@app.get("/analytics/sentiment_summary")
def sentiment_summary():
    """
    Requires enriched fields:
      - sentiment: 'positive' | 'negative' | 'neutral'
      - sentiment_score: float
    """
    pipeline = [
        {
            "$group": {
                "_id": {
                    "topic": {"$toLower": "$metadata.topic"},
                    "sent": {"$toLower": "$sentiment"},
                },
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$sentiment_score"},
            }
        },
        {"$match": {"_id.topic": {"$ne": None}}},
    ]
    rows = list(db.posts.aggregate(pipeline))

    topics = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "avg_score": None, "total": 0})
    for r in rows:
        t = r["_id"]["topic"]
        s = (r["_id"]["sent"] or "neutral")
        if s not in ("positive", "negative", "neutral"):
            s = "neutral"
        topics[t][s] += r["count"]
        topics[t]["total"] += r["count"]

        if r.get("avg_score") is not None:
            if topics[t]["avg_score"] is None:
                topics[t]["avg_score"] = r["avg_score"]
            else:
                prev_total = topics[t]["total"] - r["count"]
                topics[t]["avg_score"] = (
                    (topics[t]["avg_score"] * prev_total)
                    + (r["avg_score"] * r["count"])
                ) / max(prev_total + r["count"], 1)

    result = []
    for t, v in topics.items():
        pos = v["positive"]
        neg = v["negative"]
        neu = v["neutral"]
        tot = max(v["total"], 1)
        brand_health = round((pos - neg) / tot, 3)  # -1..+1
        result.append(
            {
                "topic": t,
                "positive": pos,
                "negative": neg,
                "neutral": neu,
                "total": tot,
                "avg_sentiment_score": None
                if v["avg_score"] is None
                else round(v["avg_score"], 3),
                "brand_health_index": brand_health,
            }
        )
    result.sort(key=lambda x: x["brand_health_index"], reverse=True)
    return result

# 3) Persona View (Beginner / Part-time / Professional / Failed)
@app.get("/analytics/persona_overview")
def persona_overview():
    """
    Uses:
      persona: 'beginner' | 'part_time' | 'professional' | 'failed'
    """

    # Global distribution
    pipeline_global = [
        {"$match": {"persona": {"$exists": True}}},
        {"$group": {"_id": {"$toLower": "$persona"}, "count": {"$sum": 1}}},
    ]
    rows_global = list(db.posts.aggregate(pipeline_global))
    total_global = sum(r["count"] for r in rows_global) or 1

    global_dist = []
    for r in rows_global:
        p = r["_id"]
        c = r["count"]
        global_dist.append(
            {
                "persona": p,
                "count": c,
                "percent": round(100.0 * c / total_global, 2),
            }
        )

    # By topic
    pipeline_topic = [
        {"$match": {"persona": {"$exists": True}}},
        {
            "$group": {
                "_id": {
                    "topic": {"$toLower": "$metadata.topic"},
                    "persona": {"$toLower": "$persona"},
                },
                "count": {"$sum": 1},
            }
        },
        {"$match": {"_id.topic": {"$ne": None}}},
    ]
    rows_topic = list(db.posts.aggregate(pipeline_topic))
    tmp = defaultdict(lambda: defaultdict(int))
    totals = defaultdict(int)
    for r in rows_topic:
        t = r["_id"]["topic"]
        p = r["_id"]["persona"]
        tmp[t][p] += r["count"]
        totals[t] += r["count"]

    by_topic = []
    for t, per in tmp.items():
        row = {
            "topic": t,
            "beginner": per.get("beginner", 0),
            "part_time": per.get("part_time", 0),
            "professional": per.get("professional", 0),
            "failed": per.get("failed", 0),
            "total": totals[t],
        }
        by_topic.append(row)

    by_topic.sort(key=lambda x: x["total"], reverse=True)

    return {"global": global_dist, "by_topic": by_topic}

# 4) Sub-Topic Drivers (keyword clusters, marketing lens)
KEYWORD_BUCKETS = {
    "payouts": [r"payout", r"withdraw(al)?", r"profit split", r"payment", r"cashout"],
    "launch_updates": [r"launch", r"beta", r"update", r"new (plan|program|rule|feature)"],
    "positives": [r"\bgood\b", r"great", r"amazing", r"helpful", r"love", r"\bfast\b", r"transparent"],
    "negatives": [r"\bbad\b", r"issue", r"problem", r"delay", r"\bscam\b", r"refus(ed)?", r"reject(ed)?"],
    "risk_rules": [r"daily loss", r"max(imum)? drawdown", r"equity( |-)?based", r"balance( |-)?based", r"news (rule|filter)"],
    "fees_resets": [r"fee", r"reset(s)?", r"refund", r"chargeback", r"commission", r"spread"],
    "promotion_offers": [r"discount", r"coupon", r"promo", r"promotion", r"sale", r"offer", r"bonus"],
}

@app.get("/analytics/subtopic_drivers/{topic_name}")
def subtopic_drivers(topic_name: str):
    posts = list(
        db.posts.find(
            {"metadata.topic": {"$regex": f"^{re.escape(topic_name)}$", "$options": "i"}}
        )
    )
    if not posts:
        return {"topic": topic_name, "buckets": {}, "total": 0}

    counts = {k: 0 for k in KEYWORD_BUCKETS}
    for p in posts:
        txt = (p.get("text") or "") + " " + (p.get("title") or "")
        low = txt.lower()
        for bucket, patterns in KEYWORD_BUCKETS.items():
            for pat in patterns:
                if re.search(pat, low):
                    counts[bucket] += 1
                    break  # avoid double counting per post per bucket

    return {"topic": topic_name, "buckets": counts, "total": len(posts)}

# 5) Marketing Opportunities (week-over-week risers + question share)
@app.get("/analytics/opportunities")
def marketing_opportunities(weeks: int = 8, top: int = 10):
    """
    Detect week-over-week risers and 'new' topics; also compute question-share
    (proxy for informational intent / unmet need).
    """
    # guard rails
    try:
        weeks = max(1, min(int(weeks), 52))
    except Exception:
        weeks = 8
    try:
        top = max(1, min(int(top), 25))
    except Exception:
        top = 10

    week_topic = defaultdict(lambda: defaultdict(int))  # topic -> week -> count
    question_topic = defaultdict(int)
    total_topic = defaultdict(int)

    cutoff = datetime.utcnow() - timedelta(days=7 * weeks + 1)

    cursor = db.posts.find(
        {}, {"metadata.topic": 1, "_id": 1, "text": 1, "title": 1}
    ).batch_size(1000)

    for p in cursor:
        try:
            dt = _to_date(p.get("_id"))
            if not dt or dt < cutoff:
                continue
            wk = _week_bucket(dt)
            topic = ((p.get("metadata") or {}).get("topic") or "").strip().lower()
            if not topic:
                continue

            week_topic[topic][wk] += 1
            txt = " ".join(
                [str(p.get("text") or ""), str(p.get("title") or "")]
            ).lower()
            if "?" in txt or re.search(
                r"\b(any help|anyone know|how do i|how to|recommend|advice)\b", txt
            ):
                question_topic[topic] += 1
            total_topic[topic] += 1
        except Exception:
            continue

    if not week_topic:
        return {
            "weeks_analyzed": weeks,
            "last_week": None,
            "previous_week": None,
            "top_risers": [],
            "new_topics": [],
        }

    all_weeks = sorted({w for counts in week_topic.values() for w in counts.keys()})
    last_week = all_weeks[-1]
    prev_week = all_weeks[-2] if len(all_weeks) > 1 else None

    rows = []
    for topic, counts in week_topic.items():
        last_cnt = counts.get(last_week, 0)
        prev_cnt = counts.get(prev_week, 0) if prev_week else 0
        wow_change = last_cnt - prev_cnt
        if prev_cnt:
            wow_pct = ((last_cnt - prev_cnt) / prev_cnt) * 100.0
        else:
            wow_pct = 100.0 if last_cnt > 0 else 0.0
        q_share = (
            question_topic.get(topic, 0) / max(1, total_topic.get(topic, 0))
        ) * 100.0

        rows.append(
            {
                "topic": topic,
                "week": last_week,
                "last_week": last_cnt,
                "previous_week": prev_cnt,
                "wow_change": wow_change,
                "wow_pct": round(wow_pct, 1),
                "question_share_pct": round(q_share, 1),
            }
        )

    top_risers = sorted(
        rows, key=lambda r: (r["wow_change"], r["last_week"]), reverse=True
    )[:top]

    new_topics = [
        r for r in rows if r["previous_week"] == 0 and r["last_week"] > 0
    ]
    new_topics = sorted(new_topics, key=lambda r: r["last_week"], reverse=True)[:top]

    return {
        "weeks_analyzed": weeks,
        "last_week": last_week,
        "previous_week": prev_week,
        "top_risers": top_risers,
        "new_topics": new_topics,
    }

# 6) Timeline & Campaign Impact (topic over time)
@app.get("/analytics/timeline/{topic_name}")
def timeline(topic_name: str, granularity: str = "week"):
    match = {
        "metadata.topic": {
            "$regex": f"^{re.escape(topic_name)}$",
            "$options": "i",
        }
    }
    cursor = db.posts.find(match, {"_id": 1, "sentiment": 1})
    buckets = defaultdict(lambda: {"count": 0, "pos": 0, "neg": 0, "neu": 0})

    for p in cursor:
        dt = _to_date(p["_id"])
        if not dt:
            continue
        label = _week_bucket(dt) if granularity == "week" else dt.strftime("%Y-%m-%d")
        buckets[label]["count"] += 1
        s = (p.get("sentiment") or "neutral").lower()
        if s.startswith("pos"):
            buckets[label]["pos"] += 1
        elif s.startswith("neg"):
            buckets[label]["neg"] += 1
        else:
            buckets[label]["neu"] += 1

    out = []
    for k in sorted(buckets.keys()):
        v = buckets[k]
        out.append({"bucket": k, **v})
    return out

# 7) Community Behavior Segmentation (intent buckets)
INTENT_RULES = {
    "question": [r"\?", r"\banyone know\b", r"\bhow do i\b", r"\bcan (someone|anyone)\b"],
    "review": [r"\breview\b", r"\bmy experience\b", r"\bhere's my take\b", r"\bpros? and cons?\b"],
    "complaint": [r"\b(issue|problem|delay|scam|refus(ed|al)|reject(ed)?)\b"],
    "success": [r"\bpassed\b", r"\bpayout(ed)?\b", r"\bfunded\b", r"\bhit target\b"],
    "education": [r"\bguide\b", r"\btips\b", r"\blesson\b", r"\bhow to\b"],
}

@app.get("/analytics/segments/{topic_name}")
def segments(topic_name: str):
    posts = list(
        db.posts.find(
            {"metadata.topic": {"$regex": f"^{re.escape(topic_name)}$", "$options": "i"}}
        )
    )
    counts = Counter()
    examples = defaultdict(list)

    for p in posts:
        txt = (
            (p.get("title") or "") + " " + (p.get("text") or "")
        ).lower().strip()
        label = "other"
        for intent, rules in INTENT_RULES.items():
            if any(re.search(r, txt) for r in rules):
                label = intent
                break
        counts[label] += 1
        if len(examples[label]) < 3:
            examples[label].append((p.get("title") or "")[:120])

    total = max(len(posts), 1)
    return {
        "topic": topic_name,
        "distribution": {k: int(v) for k, v in counts.items()},
        "share_pct": {k: round(100.0 * v / total, 2) for k, v in counts.items()},
        "examples": examples,
    }

# 8) Competitive Positioning / Gap Analysis between two topics/firms
@app.get("/analytics/compare")
def compare_topics(topic_a: str, topic_b: str, top_n: int = 20):
    def collect(topic):
        posts = list(
            db.posts.find(
                {"metadata.topic": {"$regex": f"^{re.escape(topic)}$", "$options": "i"}}
            )
        )
        words = Counter()
        sent = Counter()
        for p in posts:
            body = (p.get("title") or "") + " " + (p.get("text") or "")
            for w in tokenize(body):
                words[w] += 1
            s = (p.get("sentiment") or "neutral").lower()
            sent[s] += 1
        return {"words": words, "sent": sent, "n": len(posts)}

    A = collect(topic_a)
    B = collect(topic_b)

    def top_unique(a_words, b_words, n):
        diffs = []
        for w, c in a_words.items():
            score = c - b_words.get(w, 0)
            if score > 0:
                diffs.append((w, score))
        diffs.sort(key=lambda x: x[1], reverse=True)
        return [{"term": w, "score": int(s)} for w, s in diffs[:n]]

    result = {
        "topic_a": topic_a.lower(),
        "topic_b": topic_b.lower(),
        "top_unique_a": top_unique(A["words"], B["words"], top_n),
        "top_unique_b": top_unique(B["words"], A["words"], top_n),
        "sentiment_a": {k: int(v) for k, v in A["sent"].items()},
        "sentiment_b": {k: int(v) for k, v in B["sent"].items()},
        "count_a": A["n"],
        "count_b": B["n"],
    }
    return result

# 9) AI-style Narrative Summary (templated, no external LLM call here)
@app.get("/analytics/summary/{topic_name}")
def ai_like_summary(topic_name: str):
    sov = share_of_voice()["items"]
    sov_map = {i["topic"]: i for i in sov}
    tkey = topic_name.lower()
    sov_item = sov_map.get(tkey, {"count": 0, "percent": 0})

    sent = sentiment_summary()
    sent_map = {r["topic"]: r for r in sent}
    srow = sent_map.get(
        tkey,
        {"positive": 0, "negative": 0, "neutral": 0, "brand_health_index": 0},
    )

    opp = marketing_opportunities(weeks=8)["top_risers"]
    riser = next((o for o in opp if o["topic"] == tkey), None)

    drivers = subtopic_drivers(topic_name)
    top_driver = None
    if drivers.get("buckets"):
        non_zero = [(k, v) for k, v in drivers["buckets"].items() if v > 0]
        if non_zero:
            top_driver = max(non_zero, key=lambda x: x[1])[0]

    lines = []
    lines.append(
        f"{topic_name}: {sov_item.get('percent',0)}% share of voice ({sov_item.get('count',0)} mentions)."
    )
    lines.append(
        f"Brand health index: {srow.get('brand_health_index',0)} with P/N/N: {srow.get('positive',0)}/{srow.get('negative',0)}/{srow.get('neutral',0)}."
    )
    if top_driver:
        lines.append(
            f"Top discussion driver: **{top_driver.replace('_',' ')}**."
        )
    if riser:
        lines.append(
            f"Week-over-week: {riser['wow_change']} change ({riser['wow_pct']}%) in latest week; question share {riser['question_share_pct']}%."
        )
    else:
        lines.append("No major week-over-week spike detected in the last 4 weeks.")
    return {"topic": topic_name, "summary": " ".join(lines)}

# 10) Forecast (simple exponential smoothing on weekly counts)
@app.get("/analytics/forecast/{topic_name}")
def forecast(topic_name: str, alpha: float = 0.5, horizon: int = 4):
    series = timeline(topic_name, granularity="week")
    if not series:
        return {"topic": topic_name, "forecast": []}

    def week_key(label: str):
        y, w = label.split("-W")
        return (int(y), int(w))

    series_sorted = sorted(series, key=lambda r: week_key(r["bucket"]))
    counts = [r["count"] for r in series_sorted]
    if not counts:
        return {"topic": topic_name, "forecast": []}

    s = counts[0]
    for x in counts[1:]:
        s = alpha * x + (1 - alpha) * s

    last_y, last_w = week_key(series_sorted[-1]["bucket"])
    out = []
    y, w = last_y, last_w
    for _ in range(horizon):
        w += 1
        if w > 52:
            y += 1
            w = 1
        out.append({"bucket": f"{y}-W{w:02d}", "forecast_count": int(round(s))})

    return {
        "topic": topic_name,
        "last_observed": series_sorted[-1]["bucket"],
        "forecast": out,
    }

# ======================================================
# 11) 🚀 AI MARKETING REPORT (GPT + CACHED IN MONGO)
# ======================================================

@app.get("/analytics/ai_report/{topic_name}")
def ai_marketing_report(topic_name: str):
    """
    Hybrid marketing report for one firm/topic.

    - Checks Mongo cache (ai_reports collection)
    - If exists → returns cached report (no new OpenAI cost)
    - If not → builds metrics + calls GPT-4.1-mini, saves & returns
    """
    topic_key = topic_name.strip().lower()
    if not topic_key:
        return {"error": "topic_name is required"}

    # ---------- 1) Check cache ----------
    existing = db.ai_reports.find_one(
        {"topic": topic_key, "report_type": "marketing_v1"}
    )
    if existing:
        existing["_id"] = str(existing["_id"])
        existing["cached"] = True
        return existing

    # ---------- 2) Build metrics snapshot from existing endpoints ----------
    # Share of voice
    sov_all = share_of_voice()
    sov_map = {i["topic"]: i for i in sov_all.get("items", [])}
    sov_item = sov_map.get(topic_key, {"count": 0, "percent": 0})

    # Sentiment / brand health
    sent_all = sentiment_summary()
    sent_map = {r["topic"]: r for r in sent_all}
    sent_item = sent_map.get(
        topic_key,
        {"positive": 0, "negative": 0, "neutral": 0, "brand_health_index": 0},
    )

    # Personas by topic
    persona_all = persona_overview()
    persona_by_topic = {}
    for row in persona_all.get("by_topic", []):
        persona_by_topic[row["topic"]] = {
            "beginner": row.get("beginner", 0),
            "part_time": row.get("part_time", 0),
            "professional": row.get("professional", 0),
            "failed": row.get("failed", 0),
            "total": row.get("total", 0),
        }
    persona_item = persona_by_topic.get(
        topic_key,
        {"beginner": 0, "part_time": 0, "professional": 0, "failed": 0, "total": 0},
    )

    # Sub-topic drivers
    drivers = subtopic_drivers(topic_name)

    # Intent segments
    segs = segments(topic_name)

    # Opportunities (check if this topic is a riser)
    opp_all = marketing_opportunities(weeks=8, top=50)
    riser_row = None
    for row in opp_all.get("top_risers", []):
        if row["topic"] == topic_key:
            riser_row = row
            break

    # Timeline (last N buckets)
    tl = timeline(topic_name)
    tl_last = tl[-8:] if len(tl) > 8 else tl

    metrics = {
        "topic": topic_key,
        "share_of_voice": sov_item,
        "sentiment": sent_item,
        "personas": persona_item,
        "subtopics": drivers,
        "segments": segs,
        "opportunity": riser_row,
        "timeline": tl_last,
    }

    # ---------- 3) Call OpenAI for marketing narrative ----------
    prompt = f"""
You are a senior marketing strategist for a prop firm.

You are given structured analytics for one prop firm/topic from Reddit discussions.
Data is JSON below. Analyze it and write a detailed, marketing-focused report for the brand team.

JSON DATA:
{json.dumps(metrics, indent=2)}

Requirements for the output:
- Talk directly to the brand team of this prop firm (e.g. "For your brand, ...").
- Cover these sections clearly with headings:

1) Persona Insights
- Who is talking about the firm (beginner / part_time / professional / failed)?
- What does this tell us about funnel stage (awareness / consideration / post-failure / retention)?
- Concrete suggestions: what content or offers to build for these personas?

2) Brand Awareness & Share of Voice
- How strong is share of voice vs what we’d expect for a mid-size prop firm?
- Is this firm under-discussed or over-discussed compared to sentiment?
- How should the marketing team react: increase awareness, or focus on fixing perception?

3) Sentiment & Brand Health
- Interpret positive / negative / neutral counts and brand_health_index.
- Is this more like “fans with some complaints” or “heavy frustration”?
- What 2–3 key actions are needed (e.g. payouts comms, rule clarity, support improvements)?

4) Sub-Topic Drivers
- Which buckets dominate (payouts, risk_rules, fees_resets, promotion_offers, etc.)?
- Translate this into business language: “Traders are mainly stuck on X and obsessing about Y.”
- Suggest 2–3 campaign angles or landing pages that directly address these themes.

5) Community Behavior & Intent
- Use segments (question, complaint, success, review, education) to explain trader mindset.
- Are people in “research mode”, “panic mode”, “flex mode”, or “learning mode”?
- Suggest what kind of responses, guides, or ambassador programs would help here.

6) Opportunity & Playbook (Most important)
- Use opportunity + timeline data (trend and whether it’s a riser) to say:
  - Is this a good time to launch a promo, education series, or trust-building campaign?
  - What should be the 30-day and 90-day marketing focus?
- End with a short bullet list titled: "Execution Playbook" with 5–8 concrete actions.

Tone:
- Strategic but simple, like a consultant who understands both trading and marketing.
- Do NOT restate the raw numbers; interpret them.
- Assume the reader is the marketing lead at this prop firm.
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an expert in prop firm marketing and trader psychology."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
            temperature=0.3,
        )
        narrative = completion.choices[0].message.content
    except Exception as e:
        narrative = f"AI generation failed: {e}"

    # ---------- 4) Cache in Mongo ----------
    now = datetime.utcnow()
    report_doc = {
        "topic": topic_key,
        "report_type": "marketing_v1",
        "created_at": now,
        "updated_at": now,
        "metrics": metrics,
        "narrative": narrative,
    }
    db.ai_reports.update_one(
        {"topic": topic_key, "report_type": "marketing_v1"},
        {"$set": report_doc},
        upsert=True,
    )

    report_doc["created_at"] = report_doc["created_at"].isoformat() + "Z"
    report_doc["updated_at"] = report_doc["updated_at"].isoformat() + "Z"
    report_doc["cached"] = False
    return report_doc


# Expose port that FastAPI will run on
EXPOSE 8000

# Start FastAPI using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

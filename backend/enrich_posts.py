# # enrich_posts.py
# import os
# from time import sleep
# from pymongo import MongoClient
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()

# # ------------------------
# # CONFIG
# # ------------------------
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# if not OPENAI_API_KEY:
#     raise Exception("❌ Missing OPENAI_API_KEY in .env")

# client = OpenAI(api_key=OPENAI_API_KEY)

# MONGO_URI = "mongodb://127.0.0.1:27017"
# DB_NAME = "reddit_data"
# COLLECTION = "posts"

# mongo = MongoClient(MONGO_URI)
# db = mongo[DB_NAME]
# posts = db[COLLECTION]

# MODEL = "gpt-4.1-mini"   # Cheap + very accurate


# # ------------------------
# # OpenAI Classifier
# # ------------------------
# def classify_text(text: str):
#     """
#     Returns:
#     {
#         "sentiment": "positive|neutral|negative",
#         "sentiment_score": float,
#         "persona": "beginner|part_time|professional|failed"
#     }
#     """
#     prompt = f"""
#     Analyze the following Reddit text and return a JSON with:
#     - sentiment: positive, negative or neutral
#     - sentiment_score: float from -1 (very negative) to +1 (very positive)
#     - persona: classify user persona into one of:
#         ["beginner", "part_time", "professional", "failed"]

#     TEXT:
#     {text[:4000]}
#     """

#     try:
#         response = client.chat.completions.create(
#             model=MODEL,
#             messages=[{"role": "user", "content": prompt}],
#             response_format={"type": "json_object"}
#         )
#         data = response.choices[0].message.content
#         return eval(data)

#     except Exception as e:
#         print("OpenAI Error:", e)
#         return {
#             "sentiment": "neutral",
#             "sentiment_score": 0.0,
#             "persona": "beginner"
#         }


# # ------------------------
# # Batch Processor
# # ------------------------
# def get_unprocessed_posts(batch_size=25):
#     """Fetch posts missing AI fields."""
#     return list(
#         posts.find(
#             {"$or": [
#                 {"sentiment": {"$exists": False}},
#                 {"persona": {"$exists": False}}
#             ]}
#         ).limit(batch_size)
#     )


# def enrich_batch(docs):
#     """Runs OpenAI classification on batch of posts."""
#     for doc in docs:
#         text = (doc.get("text") or "") + " " + (doc.get("title") or "")

#         result = classify_text(text)

#         # update MongoDB
#         posts.update_one(
#             {"_id": doc["_id"]},
#             {"$set": {
#                 "sentiment": result.get("sentiment"),
#                 "sentiment_score": float(result.get("sentiment_score", 0)),
#                 "persona": result.get("persona")
#             }}
#         )

#         print(f"Updated → {doc['_id']}: {result}")


# # ------------------------
# # Driver
# # ------------------------
# if __name__ == "__main__":
#     print("🚀 Starting OpenAI enrichment...")

#     while True:
#         batch = get_unprocessed_posts()

#         if not batch:
#             print("🎉 All posts enriched!")
#             break

#         print(f"Processing {len(batch)} posts...")
#         enrich_batch(batch)

#         sleep(1)


# enrich_posts.py
import os
from time import sleep
from pymongo import MongoClient
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

# ------------------------
# CONFIG
# ------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("❌ Missing OPENAI_API_KEY in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🔥 Use MongoDB Atlas (NOT localhost)
MONGO_URI = "mongodb+srv://reddituser:23172410@cluster0.drr2ppd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "reddit_data"
COLLECTION = "posts"

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
posts = db[COLLECTION]

MODEL = "gpt-4.1-mini"   # Cheap + accurate


# ------------------------
# OpenAI Classifier
# ------------------------
def classify_text(text: str):
    """
    Returns a classified JSON:
    {
        "sentiment": "positive|neutral|negative",
        "sentiment_score": float,
        "persona": "beginner|part_time|professional|failed"
    }
    """

    prompt = f"""
    Analyze the following Reddit text and return ONLY a JSON object with:
    - sentiment: positive, negative, neutral
    - sentiment_score: float between -1 and +1
    - persona: one of ["beginner", "part_time", "professional", "failed"]

    TEXT:
    {text[:4000]}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}  # Guarantees real JSON
        )

        data = response.choices[0].message.content
        return json.loads(data)   # safer than eval()

    except Exception as e:
        print("OpenAI Error:", e)
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "persona": "beginner"
        }


# ------------------------
# Batch Processor
# ------------------------
def get_unprocessed_posts(batch_size=25):
    """Fetch posts missing LLM enrichment."""
    return list(
        posts.find(
            {"$or": [
                {"sentiment": {"$exists": False}},
                {"persona": {"$exists": False}}
            ]}
        ).limit(batch_size)
    )


def enrich_batch(docs):
    """Run OpenAI on each post in the batch."""
    for doc in docs:
        text = (doc.get("text") or "") + " " + (doc.get("title") or "")

        result = classify_text(text)

        # save back to MongoDB Atlas
        posts.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "sentiment": result.get("sentiment"),
                "sentiment_score": float(result.get("sentiment_score", 0)),
                "persona": result.get("persona")
            }}
        )

        print(f"✅ Updated → {doc['_id']} → {result}")


# ------------------------
# Driver
# ------------------------
if __name__ == "__main__":
    print("🚀 Starting OpenAI enrichment...\n")

    while True:
        batch = get_unprocessed_posts()

        if not batch:
            print("🎉 All posts enriched! No remaining documents.")
            break

        print(f"Processing {len(batch)} posts...")
        enrich_batch(batch)

        sleep(1)

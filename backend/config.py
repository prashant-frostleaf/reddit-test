# config.py
from pymongo import MongoClient
import os

# Use your Atlas URI
MONGO_URI = "mongodb+srv://reddituser:23172410@cluster0.drr2ppd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Name of your database
DB_NAME = "reddit_data"

# Create client
client = MongoClient(MONGO_URI)

# Connect to database
db = client[DB_NAME]

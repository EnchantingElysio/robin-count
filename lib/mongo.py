import logging
import os
from datetime import datetime

from pymongo import MongoClient

connection_string = (
    f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:"
    f"{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}@"
    f"{os.getenv('MONGO_INITDB_ROOT_HOST')}:"
    f"{os.getenv('MONGO_INITDB_ROOT_PORT')}/"
)
m = MongoClient(connection_string)
db = m.robin_count
c = db.robin_logs


def log_robins(user_id: str, count: int, dt: datetime):
    log = {"user_id": user_id, "count": count, "logged": dt}
    c.insert_one(log)
    logging.debug(f"Inserted log: {log}")


def get_robins(
    user_id: str = None, start_date: datetime = None, end_date: datetime = None
):
    # Build the filter query based on provided arguments
    query = {}
    if user_id:
        query["user_id"] = user_id

    if start_date or end_date:
        query["logged"] = {}
        if start_date:
            query["logged"]["$gte"] = start_date
        if end_date:
            query["logged"]["$lte"] = end_date

    # Create an aggregation pipeline to match and sum the counts
    pipeline = [
        {"$match": query},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]

    # Execute the aggregation query
    result = list(c.aggregate(pipeline))
    return result[0]["total"] if result else 0


def get_leaderboard(
    limit: int = 10, start_date: datetime = None, end_date: datetime = None
):
    query = {}
    if start_date or end_date:
        query["logged"] = {}
        if start_date:
            query["logged"]["$gte"] = start_date
        if end_date:
            query["logged"]["$lte"] = end_date
    pipeline = []
    if query:
        pipeline.append({"$match": query})

    pipeline.extend(
        [
            {"$group": {
                "user_id": {"$sum" : "$user_id"}, 
                "total": {"$sum": "$count"},
                "_id" : "$_id",
                }},
            {"$sort": {"total": -1}},
            {"$limit": limit},
        ]
    )
    results = list(c.aggregate(pipeline))
    return results

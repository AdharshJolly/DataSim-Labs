from collections.abc import Generator

import certifi
from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings


client = MongoClient(settings.mongodb_uri, tlsCAFile=certifi.where())
database = client[settings.mongodb_database]


def get_db() -> Generator[Database, None, None]:
    yield database

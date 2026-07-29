"""pytest 夹具：每个用例注入一个全新的 mongomock 库，无需真实 MongoDB。"""
import mongomock
import pytest

from research_agent.storage import db


@pytest.fixture(autouse=True)
def _mongo():
    client = mongomock.MongoClient()
    db.set_db(client["test_research_agent"])
    yield
    client.close()

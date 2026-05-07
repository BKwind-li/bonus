"""Broker registry — shared singleton instances.

Both routers and background services (scanner, scheduler) should import the
adapter from here so there is exactly one PaperBrokerAdapter instance in the
process.  Tests override the adapter via FastAPI's dependency_overrides on
``routers.portfolio.get_adapter`` — this module is not affected by that
override, but test isolation still holds because all adapter state lives in
SQLite (which is wiped by the clean_db fixture before each test).
"""

from brokers.paper import PaperBrokerAdapter

paper_adapter: PaperBrokerAdapter = PaperBrokerAdapter()

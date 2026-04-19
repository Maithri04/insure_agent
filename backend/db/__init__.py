# db/__init__.py
# InsureMind AI — Database Module Exports

from db.mongo import (
    get_mongo_db,
    create_mongo_indexes,
    check_mongo_health,
    close_mongo_connection,
)

from db.postgres import (
    get_postgres_pool,
    validate_schema,
    ensure_payer_rules_table,
    check_postgres_health,
    close_postgres_pool,
)

__all__ = [
    # MongoDB
    "get_mongo_db",
    "create_mongo_indexes",
    "check_mongo_health",
    "close_mongo_connection",
    # PostgreSQL
    "get_postgres_pool",
    "validate_schema",
    "ensure_payer_rules_table",
    "check_postgres_health",
    "close_postgres_pool",
]
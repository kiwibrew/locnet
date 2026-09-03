"""Run sqlite-web with LOCNET's database access restrictions.

The SQLite authorizer is enforced by SQLite itself for every statement issued
by sqlite-web.  This is deliberately independent of sqlite-web's HTML so a
crafted request cannot disclose authentication data or change the schema.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ALLOWED_TABLES = frozenset(
    {
        "backhaul",
        "countries",
        "country_bounds",
        "damodaran_risk",
        "defaults",
        "imf_inf_2024",
        "iso_639_3",
        "midhaul",
        "power",
        "solar_cache",
        "solarstats",
        "technology",
        "terrain",
        "text",
        "tower",
        "un_hh_size",
        "undesa_labour_share_gdp",
        "unpop_2024",
        "vegetation",
        "wb_gdp_cap",
        "wb_pop_growth",
        "wb_power_install",
        "wb_power_price",
    }
)
SQLITE_MASTER_TABLES = {"sqlite_master", "sqlite_temp_master"}
READ_ONLY_PRAGMAS = {
    "collation_list",
    "foreign_key_list",
    "index_info",
    "index_list",
    "table_info",
    "table_xinfo",
}
BLOCKED_ACTIONS = {
    sqlite3.SQLITE_ALTER_TABLE,
    sqlite3.SQLITE_ANALYZE,
    sqlite3.SQLITE_ATTACH,
    sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_INDEX,
    sqlite3.SQLITE_CREATE_TEMP_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
    sqlite3.SQLITE_CREATE_TEMP_VIEW,
    sqlite3.SQLITE_CREATE_TRIGGER,
    sqlite3.SQLITE_CREATE_VIEW,
    sqlite3.SQLITE_CREATE_VTABLE,
    sqlite3.SQLITE_DETACH,
    sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_DROP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_INDEX,
    sqlite3.SQLITE_DROP_TEMP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_TRIGGER,
    sqlite3.SQLITE_DROP_TEMP_VIEW,
    sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VIEW,
    sqlite3.SQLITE_DROP_VTABLE,
    sqlite3.SQLITE_REINDEX,
}
ORIGINAL_CONNECT = sqlite3.connect


def _table_is_allowed(table: str | None) -> bool:
    return table is not None and table.casefold() in ALLOWED_TABLES


def _authorize(action: int, arg1: str | None, arg2: str | None, *_: object) -> int:
    if action in BLOCKED_ACTIONS:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA:
        # sqlite-web needs these read-only PRAGMAs while it builds table
        # metadata. All other PRAGMAs can change connection/database state.
        return (
            sqlite3.SQLITE_OK
            if arg1 is not None and arg1.casefold() in READ_ONLY_PRAGMAS
            else sqlite3.SQLITE_DENY
        )
    if action in {
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
    }:
        if arg1 is not None and arg1.casefold() in SQLITE_MASTER_TABLES:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_OK if _table_is_allowed(arg1) else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _restricted_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
    connection = ORIGINAL_CONNECT(*args, **kwargs)
    connection.set_authorizer(_authorize)
    return connection


def main() -> None:
    sqlite3.connect = _restricted_connect  # type: ignore[assignment]
    from flask import abort, request
    from sqlite_web import sqlite_web

    sqlite_web.sqlite3.connect = _restricted_connect

    @sqlite_web.app.context_processor
    def allowlisted_template_context() -> dict[str, list[str]]:
        return {
            "allowed_tables": sorted(
                table for table in sqlite_web.dataset.tables if _table_is_allowed(table)
            )
        }

    @sqlite_web.app.before_request
    def enforce_route_allowlist() -> None:
        table = request.view_args.get("table") if request.view_args else None
        if table is not None and not _table_is_allowed(table):
            abort(404)
        # sqlite-web 0.6.4 has no configuration flag to disable arbitrary SQL
        # or migration pages.  Deny their routes before their handlers run.
        if request.endpoint in {
            "generic_query",
            "table_query",
            "table_create",
            "add_column",
            "drop_column",
            "rename_column",
            "add_index",
            "drop_index",
            "drop_trigger",
            "drop_table",
        }:
            abort(404)

    sqlite_web.app.jinja_loader.searchpath.insert(0, str(Path("/opt/locnet/templates")))
    sys.argv = [
        "sqlite_web",
        "/app/runtime/app.db",
        "--host=0.0.0.0",
        "--port=8080",
        "--no-browser",
        "--url-prefix=/admin/database/",
    ]
    sqlite_web.main()


if __name__ == "__main__":
    main()

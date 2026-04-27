"""Schema introspection for database verification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class DBType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"
    MONGODB = "mongodb"


@dataclass
class ColumnInfo:
    """Column metadata."""
    name: str
    data_type: str
    nullable: bool = True
    default: Any = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_ref: tuple[str, str] | None = None  # (table, column)


@dataclass
class TableInfo:
    """Table metadata."""
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    indexes: list[dict] = field(default_factory=list)


@dataclass
class SchemaInfo:
    """Complete database schema."""
    db_type: DBType
    tables: list[TableInfo] = field(default_factory=list)
    version: str | None = None


class SchemaIntrospector:
    """Introspects database schema for verification."""

    def __init__(self, connection: Any):
        """Initialize with database connection.

        Args:
            connection: Database connection (psycopg2 connection, sqlite connection, etc.)
        """
        self.connection = connection
        self._schema_cache: SchemaInfo | None = None

    def introspect(self) -> SchemaInfo:
        """Introspect database schema.

        Returns:
            SchemaInfo with tables, columns, and constraints
        """
        if self._schema_cache is not None:
            return self._schema_cache

        # Detect database type
        db_type = self._detect_db_type()

        if db_type == DBType.POSTGRESQL:
            self._schema_cache = self._introspect_postgresql()
        elif db_type == DBType.SQLITE:
            self._schema_cache = self._introspect_sqlite()
        elif db_type == DBType.MYSQL:
            self._schema_cache = self._introspect_mysql()
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

        return self._schema_cache

    def _detect_db_type(self) -> DBType:
        """Detect database type from connection."""
        module_name = type(self.connection).__module__.lower()

        if "psycopg2" in module_name or "psycopg" in module_name:
            return DBType.POSTGRESQL
        elif "sqlite3" in module_name:
            return DBType.SQLITE
        elif "pymysql" in module_name or "mysql" in module_name:
            return DBType.MYSQL
        elif "pymongo" in module_name or "mongo" in module_name:
            return DBType.MONGODB
        else:
            return DBType.SQLITE  # Default assumption

    def _introspect_postgresql(self) -> SchemaInfo:
        """Introspect PostgreSQL schema."""
        cursor = self.connection.cursor()

        # Get tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        table_infos = []
        for table_name in tables:
            table_info = self._get_postgres_table_info(cursor, table_name)
            table_infos.append(table_info)

        cursor.close()

        return SchemaInfo(db_type=DBType.POSTGRESQL, tables=table_infos)

    def _get_postgres_table_info(self, cursor, table_name: str) -> TableInfo:
        """Get detailed table info for PostgreSQL."""
        # Get columns
        cursor.execute("""
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length
            FROM information_schema.columns c
            WHERE c.table_name = %s AND c.table_schema = 'public'
        """, (table_name,))

        columns = []
        for row in cursor.fetchall():
            columns.append(ColumnInfo(
                name=row[0],
                data_type=row[1],
                nullable=(row[2] == "YES"),
                default=row[3],
            ))

        # Get primary key
        cursor.execute("""
            SELECT kcu.column_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = %s 
                AND tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = 'public'
        """, (table_name,))
        pk_columns = [row[0] for row in cursor.fetchall()]

        for col in columns:
            col.is_primary_key = col.name in pk_columns

        return TableInfo(name=table_name, columns=columns, primary_key=pk_columns)

    def _introspect_sqlite(self) -> SchemaInfo:
        """Introspect SQLite schema."""
        cursor = self.connection.cursor()

        # Get tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        table_infos = []
        for table_name in tables:
            table_info = self._get_sqlite_table_info(cursor, table_name)
            table_infos.append(table_info)

        cursor.close()

        return SchemaInfo(db_type=DBType.SQLITE, tables=table_infos)

    def _get_sqlite_table_info(self, cursor, table_name: str) -> TableInfo:
        """Get detailed table info for SQLite."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        rows = cursor.fetchall()

        columns = []
        pk_columns = []

        for row in rows:
            col = ColumnInfo(
                name=row[1],
                data_type=row[2] or "BLOB",
                nullable=(row[3] == 0),  # notnull
                default=row[4],
            )
            columns.append(col)
            if row[5] == 1:  # pk
                pk_columns.append(col.name)
                col.is_primary_key = True

        return TableInfo(name=table_name, columns=columns, primary_key=pk_columns)

    def _introspect_mysql(self) -> SchemaInfo:
        """Introspect MySQL schema."""
        cursor = self.connection.cursor()

        # Get tables
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        table_infos = []
        for table_name in tables:
            table_info = self._get_mysql_table_info(cursor, table_name)
            table_infos.append(table_info)

        cursor.close()

        return SchemaInfo(db_type=DBType.MYSQL, tables=table_infos)

    def _get_mysql_table_info(self, cursor, table_name: str) -> TableInfo:
        """Get detailed table info for MySQL."""
        cursor.execute(f"DESCRIBE `{table_name}`")
        rows = cursor.fetchall()

        columns = []
        pk_columns = []

        for row in rows:
            col = ColumnInfo(
                name=row[0],
                data_type=row[1],
                nullable=(row[2] == "YES"),
                default=row[4],
            )
            columns.append(col)
            if row[3] == "PRI":
                pk_columns.append(col.name)
                col.is_primary_key = True

        return TableInfo(name=table_name, columns=columns, primary_key=pk_columns)


__all__ = ["SchemaIntrospector", "TableInfo", "ColumnInfo", "DBType", "SchemaInfo"]
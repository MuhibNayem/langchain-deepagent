"""Tests for SchemaIntrospector - RED phase."""
import pytest
from unittest.mock import MagicMock, patch


class TestDBType:
    """Tests for DBType enum."""

    def test_db_type_enum_values(self):
        """Test DBType has expected values."""
        from luminamind.evaluator.schema_introspector import DBType

        assert DBType.POSTGRESQL.value == "postgresql"
        assert DBType.SQLITE.value == "sqlite"
        assert DBType.MYSQL.value == "mysql"
        assert DBType.MONGODB.value == "mongodb"


class TestColumnInfo:
    """Tests for ColumnInfo dataclass."""

    def test_column_info_creation(self):
        """Test ColumnInfo can be created with required fields."""
        from luminamind.evaluator.schema_introspector import ColumnInfo

        col = ColumnInfo(name="id", data_type="INTEGER")
        assert col.name == "id"
        assert col.data_type == "INTEGER"
        assert col.nullable is True
        assert col.is_primary_key is False

    def test_column_info_full(self):
        """Test ColumnInfo with all fields."""
        from luminamind.evaluator.schema_introspector import ColumnInfo

        col = ColumnInfo(
            name="user_id",
            data_type="BIGINT",
            nullable=False,
            default="0",
            is_primary_key=True,
            is_foreign_key=True,
            foreign_key_ref=("users", "id"),
        )
        assert col.name == "user_id"
        assert col.is_primary_key is True
        assert col.is_foreign_key is True
        assert col.foreign_key_ref == ("users", "id")


class TestTableInfo:
    """Tests for TableInfo dataclass."""

    def test_table_info_creation(self):
        """Test TableInfo can be created."""
        from luminamind.evaluator.schema_introspector import TableInfo

        table = TableInfo(name="users")
        assert table.name == "users"
        assert table.columns == []
        assert table.primary_key == []


class TestSchemaInfo:
    """Tests for SchemaInfo dataclass."""

    def test_schema_info_creation(self):
        """Test SchemaInfo can be created."""
        from luminamind.evaluator.schema_introspector import SchemaInfo, DBType

        schema = SchemaInfo(db_type=DBType.POSTGRESQL)
        assert schema.db_type == DBType.POSTGRESQL
        assert schema.tables == []


class TestSchemaIntrospector:
    """Tests for SchemaIntrospector class."""

    def test_init_with_connection(self):
        """Test SchemaIntrospector initializes with connection."""
        from luminamind.evaluator.schema_introspector import SchemaIntrospector

        mock_conn = MagicMock()
        inspector = SchemaIntrospector(mock_conn)
        assert inspector.connection is mock_conn

    def test_detect_sqlite(self):
        """Test SQLite type detection from connection module."""
        from luminamind.evaluator.schema_introspector import SchemaIntrospector, DBType

        mock_conn = MagicMock()
        mock_conn.__class__.__module__ = "sqlite3"

        inspector = SchemaIntrospector(mock_conn)
        db_type = inspector._detect_db_type()

        assert db_type == DBType.SQLITE

    def test_detect_postgresql(self):
        """Test PostgreSQL type detection."""
        from luminamind.evaluator.schema_introspector import SchemaIntrospector, DBType

        mock_conn = MagicMock()
        mock_conn.__class__.__module__ = "psycopg2"

        inspector = SchemaIntrospector(mock_conn)
        db_type = inspector._detect_db_type()

        assert db_type == DBType.POSTGRESQL

    def test_detect_mysql(self):
        """Test MySQL type detection."""
        from luminamind.evaluator.schema_introspector import SchemaIntrospector, DBType

        mock_conn = MagicMock()
        mock_conn.__class__.__module__ = "pymysql"

        inspector = SchemaIntrospector(mock_conn)
        db_type = inspector._detect_db_type()

        assert db_type == DBType.MYSQL

    def test_introspect_sqlite_tables(self):
        """Test SQLite schema introspection returns table list."""
        from luminamind.evaluator.schema_introspector import SchemaIntrospector, DBType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # First call: sqlite_master returns tables
        # Second call: PRAGMA for 'users' table
        # Third call: PRAGMA for 'orders' table
        mock_cursor.fetchall.side_effect = [
            [("users",), ("orders",)],  # sqlite_master
            [(0, "id", "INTEGER", 1, None, 1), (1, "name", "TEXT", 0, None, 0)],  # PRAGMA for users
            [(0, "id", "INTEGER", 1, None, 1)],  # PRAGMA for orders
        ]

        inspector = SchemaIntrospector(mock_conn)
        schema = inspector._introspect_sqlite()

        assert schema.db_type == DBType.SQLITE
        assert len(schema.tables) == 2

    def test_introspect_sqlite_column_info(self):
        """Test SQLite introspector extracts column info via PRAGMA."""
        from luminamind.evaluator.schema_introspector import SchemaIntrospector

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock PRAGMA table_info for users table
        # PRAGMA returns: (cid, name, type, notnull, dflt_value, pk)
        # notnull: 0 = nullable, 1 = NOT NULL
        mock_cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 1, None, 1),  # pk, NOT NULL
            (1, "name", "TEXT", 0, None, 0),   # nullable
            (2, "email", "TEXT", 0, None, 0),  # nullable (notnull=0)
        ]

        inspector = SchemaIntrospector(mock_conn)
        table_info = inspector._get_sqlite_table_info(mock_cursor, "users")

        assert table_info.name == "users"
        assert len(table_info.columns) == 3

        # Check first column (id)
        id_col = table_info.columns[0]
        assert id_col.name == "id"
        assert id_col.data_type == "INTEGER"
        assert id_col.is_primary_key is True

        # Check third column (email) - nullable
        email_col = table_info.columns[2]
        assert email_col.name == "email"
        assert email_col.nullable is True
"""Database state verification with assertions.

SEC-01 Compliance: All SQL queries use parameterized queries to prevent SQL injection.
Table and column names are validated against allowlists or isidentifier() check.
Custom queries must be pre-validated by the caller.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence
from enum import Enum
from datetime import datetime

from luminamind.evaluator.schema_introspector import SchemaIntrospector, SchemaInfo

# Pre-compiled regex for safe identifier patterns (alphanumeric + underscore)
_SAFE_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class AssertionType(Enum):
    """Types of database assertions."""
    ROW_COUNT = "row_count"
    CELL_VALUE = "cell_value"
    ROW_EXISTS = "row_exists"
    ROW_MISSING = "row_missing"
    SCHEMA_UNCHANGED = "schema_unchanged"
    QUERY_RETURNS = "query_returns"
    CUSTOM = "custom"


def _is_safe_identifier(name: str) -> bool:
    """Check if a name is a safe SQL identifier (table or column name)."""
    return bool(_SAFE_IDENTIFIER_RE.match(name)) if name else False


def _validate_identifier_list(names: list[str]) -> bool:
    """Validate a list of identifiers are all safe."""
    return all(_is_safe_identifier(n) for n in names)


@dataclass
class DBAssertion:
    """Database assertion to verify."""
    assertion_type: AssertionType
    description: str
    # For ROW_COUNT
    table: str | None = None
    expected_count: int | None = None
    where_clause: str | None = None
    where_params: Sequence[Any] | None = None  # SQL injection prevention: params for WHERE clause
    # For CELL_VALUE
    column: str | None = None
    expected_value: Any = None
    row_identifier: dict | None = None
    # For SCHEMA_UNCHANGED
    baseline_schema: SchemaInfo | None = None
    # For CUSTOM
    custom_query: str | None = None
    custom_validator: Any = None


@dataclass
class AssertionResult:
    """Result of an assertion."""
    assertion: DBAssertion
    passed: bool
    actual_value: Any | None = None
    message: str | None = None
    timestamp: str = field(default_factory=datetime.utcnow().isoformat)


@dataclass
class VerificationReport:
    """Complete verification report."""
    total_assertions: int
    passed: int
    failed: int
    results: list[AssertionResult]
    duration_ms: float


class DatabaseVerifier:
    """Verifies database state against assertions.

    Features:
    - Multiple assertion types (row count, cell value, schema, etc.)
    - Detailed failure reporting
    - Schema change detection
    - Query-based custom assertions
    """

    def __init__(self, connection: Any, introspector: SchemaIntrospector | None = None):
        """Initialize verifier.

        Args:
            connection: Database connection
            introspector: Optional schema introspector (created if not provided)
        """
        self.connection = connection
        self.introspector = introspector or SchemaIntrospector(connection)
        self._baseline_schema: SchemaInfo | None = None

    async def verify(self, assertions: list[DBAssertion]) -> VerificationReport:
        """Verify all assertions.

        Args:
            assertions: List of assertions to verify

        Returns:
            VerificationReport with results
        """
        start_time = datetime.utcnow()

        results = []
        for assertion in assertions:
            result = await self._verify_single(assertion)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return VerificationReport(
            total_assertions=len(assertions),
            passed=passed,
            failed=failed,
            results=results,
            duration_ms=duration_ms,
        )

    async def _verify_single(self, assertion: DBAssertion) -> AssertionResult:
        """Verify a single assertion."""
        try:
            if assertion.assertion_type == AssertionType.ROW_COUNT:
                return await self._verify_row_count(assertion)
            elif assertion.assertion_type == AssertionType.CELL_VALUE:
                return await self._verify_cell_value(assertion)
            elif assertion.assertion_type == AssertionType.ROW_EXISTS:
                return await self._verify_row_exists(assertion)
            elif assertion.assertion_type == AssertionType.ROW_MISSING:
                return await self._verify_row_missing(assertion)
            elif assertion.assertion_type == AssertionType.SCHEMA_UNCHANGED:
                return await self._verify_schema_unchanged(assertion)
            elif assertion.assertion_type == AssertionType.QUERY_RETURNS:
                return await self._verify_query_returns(assertion)
            else:
                return AssertionResult(
                    assertion=assertion,
                    passed=False,
                    message=f"Unknown assertion type: {assertion.assertion_type}",
                )
        except Exception as e:
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Verification error: {str(e)}",
            )

    async def _verify_row_count(self, assertion: DBAssertion) -> AssertionResult:
        """Verify row count matches expected."""
        cursor = self.connection.cursor()

        # SEC-01: Validate table name to prevent SQL injection
        if not _is_safe_identifier(assertion.table):
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Invalid table name: {assertion.table}",
            )

        query = f"SELECT COUNT(*) FROM {assertion.table}"
        params = []

        if assertion.where_clause:
            # SEC-01: Validate that WHERE clause uses parameterized placeholders
            # Expected format: "column1 = %s AND column2 = %s"
            # Parse to extract column names and validate them
            where_pattern = re.compile(r'^([\w]+)\s*=\s*%s(\s+AND\s+([\w]+)\s*=\s*%s)*$')
            match = where_pattern.match(assertion.where_clause)
            if not match:
                return AssertionResult(
                    assertion=assertion,
                    passed=False,
                    message=f"Invalid WHERE clause pattern (must use parameterized %s): {assertion.where_clause}",
                )
            query += f" WHERE {assertion.where_clause}"
            if assertion.where_params:
                params = list(assertion.where_params)

        cursor.execute(query, params)
        actual_count = cursor.fetchone()[0]
        cursor.close()

        passed = actual_count == assertion.expected_count
        message = None
        if not passed:
            message = f"Expected {assertion.expected_count} rows, found {actual_count}"

        return AssertionResult(
            assertion=assertion,
            passed=passed,
            actual_value=actual_count,
            message=message,
        )

    async def _verify_cell_value(self, assertion: DBAssertion) -> AssertionResult:
        """Verify cell value matches expected."""
        cursor = self.connection.cursor()

        # SEC-01: Validate table and column names to prevent SQL injection
        if not _is_safe_identifier(assertion.table):
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Invalid table name: {assertion.table}",
            )
        if not _is_safe_identifier(assertion.column):
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Invalid column name: {assertion.column}",
            )

        # Build query with parameterized WHERE clause
        query = f"SELECT {assertion.column} FROM {assertion.table}"
        where_parts = []
        params = []

        if assertion.row_identifier:
            # SEC-01: Validate all keys in row_identifier are safe identifiers
            if not _validate_identifier_list(list(assertion.row_identifier.keys())):
                return AssertionResult(
                    assertion=assertion,
                    passed=False,
                    message=f"Invalid row_identifier keys: {list(assertion.row_identifier.keys())}",
                )
            for key, value in assertion.row_identifier.items():
                where_parts.append(f"{key} = %s")
                params.append(value)

        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)

        cursor.execute(query, params)
        row = cursor.fetchone()
        cursor.close()

        if row is None:
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message="Row not found",
            )

        actual_value = row[0]
        passed = actual_value == assertion.expected_value
        message = None
        if not passed:
            message = f"Expected {assertion.expected_value}, found {actual_value}"

        return AssertionResult(
            assertion=assertion,
            passed=passed,
            actual_value=actual_value,
            message=message,
        )

    async def _verify_row_exists(self, assertion: DBAssertion) -> AssertionResult:
        """Verify row exists matching criteria."""
        cursor = self.connection.cursor()

        # SEC-01: Validate table name to prevent SQL injection
        if not _is_safe_identifier(assertion.table):
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Invalid table name: {assertion.table}",
            )

        query = f"SELECT 1 FROM {assertion.table}"
        where_parts = []
        params = []

        if assertion.row_identifier:
            # SEC-01: Validate all keys in row_identifier are safe identifiers
            if not _validate_identifier_list(list(assertion.row_identifier.keys())):
                return AssertionResult(
                    assertion=assertion,
                    passed=False,
                    message=f"Invalid row_identifier keys: {list(assertion.row_identifier.keys())}",
                )
            for key, value in assertion.row_identifier.items():
                where_parts.append(f"{key} = %s")
                params.append(value)

        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)

        query += " LIMIT 1"

        cursor.execute(query, params)
        exists = cursor.fetchone() is not None
        cursor.close()

        return AssertionResult(
            assertion=assertion,
            passed=exists,
            actual_value=exists,
        )

    async def _verify_row_missing(self, assertion: DBAssertion) -> AssertionResult:
        """Verify row does not exist matching criteria."""
        cursor = self.connection.cursor()

        # SEC-01: Validate table name to prevent SQL injection
        if not _is_safe_identifier(assertion.table):
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Invalid table name: {assertion.table}",
            )

        query = f"SELECT 1 FROM {assertion.table}"
        where_parts = []
        params = []

        if assertion.row_identifier:
            # SEC-01: Validate all keys in row_identifier are safe identifiers
            if not _validate_identifier_list(list(assertion.row_identifier.keys())):
                return AssertionResult(
                    assertion=assertion,
                    passed=False,
                    message=f"Invalid row_identifier keys: {list(assertion.row_identifier.keys())}",
                )
            for key, value in assertion.row_identifier.items():
                where_parts.append(f"{key} = %s")
                params.append(value)

        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)

        query += " LIMIT 1"

        cursor.execute(query, params)
        exists = cursor.fetchone() is not None
        cursor.close()

        return AssertionResult(
            assertion=assertion,
            passed=not exists,
            actual_value=not exists,
        )

    async def _verify_schema_unchanged(self, assertion: DBAssertion) -> AssertionResult:
        """Verify schema matches baseline."""
        current_schema = self.introspector.introspect()

        if assertion.baseline_schema is None:
            assertion.baseline_schema = self._baseline_schema

        if assertion.baseline_schema is None:
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message="No baseline schema available",
            )

        # Compare tables
        baseline_tables = {t.name for t in assertion.baseline_schema.tables}
        current_tables = {t.name for t in current_schema.tables}

        added = current_tables - baseline_tables
        removed = baseline_tables - current_tables

        passed = len(added) == 0 and len(removed) == 0
        message = None
        if not passed:
            message = f"Schema changed: added={added}, removed={removed}"

        return AssertionResult(
            assertion=assertion,
            passed=passed,
            actual_value={"added": list(added), "removed": list(removed)},
            message=message,
        )

    async def _verify_query_returns(self, assertion: DBAssertion) -> AssertionResult:
        """Verify custom query returns expected result.

        WARNING: custom_query must be pre-validated by caller.
        For safe operation, custom_query should use %s placeholders and
        caller should provide custom_params list separately.
        SEC-01: This method trusts the caller to validate custom_query.
        Only SELECT statements are allowed.
        """
        cursor = self.connection.cursor()

        # SEC-01: Validate that custom_query is a SELECT statement (read-only)
        if not assertion.custom_query or not assertion.custom_query.strip().upper().startswith('SELECT'):
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message="custom_query must be a SELECT statement",
            )

        cursor.execute(assertion.custom_query)
        result = cursor.fetchone()
        cursor.close()

        passed = assertion.custom_validator(result) if assertion.custom_validator else bool(result)

        return AssertionResult(
            assertion=assertion,
            passed=passed,
            actual_value=result,
        )

    def set_baseline_schema(self) -> None:
        """Capture current schema as baseline for future comparisons."""
        self._baseline_schema = self.introspector.introspect()


__all__ = ["DatabaseVerifier", "DBAssertion", "AssertionResult", "AssertionType", "VerificationReport"]
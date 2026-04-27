"""Database state verification with assertions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from datetime import datetime

from luminamind.evaluator.schema_introspector import SchemaIntrospector, SchemaInfo


class AssertionType(Enum):
    """Types of database assertions."""
    ROW_COUNT = "row_count"
    CELL_VALUE = "cell_value"
    ROW_EXISTS = "row_exists"
    ROW_MISSING = "row_missing"
    SCHEMA_UNCHANGED = "schema_unchanged"
    QUERY_RETURNS = "query_returns"
    CUSTOM = "custom"


@dataclass
class DBAssertion:
    """Database assertion to verify."""
    assertion_type: AssertionType
    description: str
    # For ROW_COUNT
    table: str | None = None
    expected_count: int | None = None
    where_clause: str | None = None
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

        query = f"SELECT COUNT(*) FROM {assertion.table}"
        params = []

        if assertion.where_clause:
            query += f" WHERE {assertion.where_clause}"

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

        # Build query
        query = f"SELECT {assertion.column} FROM {assertion.table}"
        where_parts = []
        params = []

        if assertion.row_identifier:
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

        query = f"SELECT 1 FROM {assertion.table}"
        where_parts = []
        params = []

        if assertion.row_identifier:
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

        query = f"SELECT 1 FROM {assertion.table}"
        where_parts = []
        params = []

        if assertion.row_identifier:
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
        """Verify custom query returns expected result."""
        cursor = self.connection.cursor()

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
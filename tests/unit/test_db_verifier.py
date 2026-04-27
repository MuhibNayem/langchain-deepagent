"""Tests for DatabaseVerifier - RED phase."""
import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio


class TestAssertionType:
    """Tests for AssertionType enum."""

    def test_all_assertion_types_defined(self):
        """Test all assertion types are defined."""
        from luminamind.evaluator.db_verifier import AssertionType

        expected = [
            "ROW_COUNT", "CELL_VALUE", "ROW_EXISTS", "ROW_MISSING",
            "SCHEMA_UNCHANGED", "QUERY_RETURNS", "CUSTOM"
        ]
        for t in expected:
            assert hasattr(AssertionType, t)


class TestDBAssertion:
    """Tests for DBAssertion dataclass."""

    def test_row_count_assertion(self):
        """Test creating row count assertion."""
        from luminamind.evaluator.db_verifier import DBAssertion, AssertionType

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_COUNT,
            description="Should have 5 users",
            table="users",
            expected_count=5,
        )
        assert assertion.assertion_type == AssertionType.ROW_COUNT
        assert assertion.table == "users"
        assert assertion.expected_count == 5

    def test_cell_value_assertion(self):
        """Test creating cell value assertion."""
        from luminamind.evaluator.db_verifier import DBAssertion, AssertionType

        assertion = DBAssertion(
            assertion_type=AssertionType.CELL_VALUE,
            description="User email should be test@example.com",
            table="users",
            column="email",
            expected_value="test@example.com",
            row_identifier={"id": 1},
        )
        assert assertion.column == "email"
        assert assertion.expected_value == "test@example.com"
        assert assertion.row_identifier == {"id": 1}

    def test_row_exists_assertion(self):
        """Test creating row exists assertion."""
        from luminamind.evaluator.db_verifier import DBAssertion, AssertionType

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_EXISTS,
            description="Admin user exists",
            table="users",
            row_identifier={"role": "admin"},
        )
        assert assertion.assertion_type == AssertionType.ROW_EXISTS


class TestAssertionResult:
    """Tests for AssertionResult dataclass."""

    def test_assertion_result_pass(self):
        """Test assertion result for passed assertion."""
        from luminamind.evaluator.db_verifier import AssertionResult, DBAssertion, AssertionType

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_COUNT,
            description="Test",
            table="users",
            expected_count=5,
        )
        result = AssertionResult(
            assertion=assertion,
            passed=True,
            actual_value=5,
        )
        assert result.passed is True
        assert result.actual_value == 5

    def test_assertion_result_fail(self):
        """Test assertion result for failed assertion."""
        from luminamind.evaluator.db_verifier import AssertionResult, DBAssertion, AssertionType

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_COUNT,
            description="Test",
            table="users",
            expected_count=5,
        )
        result = AssertionResult(
            assertion=assertion,
            passed=False,
            actual_value=3,
            message="Expected 5 rows, found 3",
        )
        assert result.passed is False
        assert result.actual_value == 3
        assert "Expected 5" in result.message


class TestVerificationReport:
    """Tests for VerificationReport dataclass."""

    def test_verification_report_creation(self):
        """Test creating verification report."""
        from luminamind.evaluator.db_verifier import VerificationReport, AssertionResult

        results = [
            AssertionResult(
                assertion=MagicMock(),
                passed=True,
            ),
            AssertionResult(
                assertion=MagicMock(),
                passed=False,
            ),
        ]
        report = VerificationReport(
            total_assertions=2,
            passed=1,
            failed=1,
            results=results,
            duration_ms=100.5,
        )
        assert report.total_assertions == 2
        assert report.passed == 1
        assert report.failed == 1


class TestDatabaseVerifier:
    """Tests for DatabaseVerifier class."""

    def test_init_with_connection(self):
        """Test DatabaseVerifier initializes with connection."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier

        mock_conn = MagicMock()
        verifier = DatabaseVerifier(mock_conn)
        assert verifier.connection is mock_conn

    def test_init_with_introspector(self):
        """Test DatabaseVerifier accepts custom introspector."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier

        mock_conn = MagicMock()
        mock_introspector = MagicMock()
        verifier = DatabaseVerifier(mock_conn, mock_introspector)
        assert verifier.introspector is mock_introspector

    @pytest.mark.asyncio
    async def test_verify_row_count_pass(self):
        """Test row count assertion passes when count matches."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (5,)

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_COUNT,
            description="Should have 5 users",
            table="users",
            expected_count=5,
        )

        result = await verifier._verify_row_count(assertion)

        assert result.passed is True
        assert result.actual_value == 5

    @pytest.mark.asyncio
    async def test_verify_row_count_fail(self):
        """Test row count assertion fails when count differs."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (3,)

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_COUNT,
            description="Should have 5 users",
            table="users",
            expected_count=5,
        )

        result = await verifier._verify_row_count(assertion)

        assert result.passed is False
        assert result.actual_value == 3
        assert "Expected 5" in result.message

    @pytest.mark.asyncio
    async def test_verify_cell_value(self):
        """Test cell value assertion validates column values."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("test@example.com",)

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.CELL_VALUE,
            description="User email should be test@example.com",
            table="users",
            column="email",
            expected_value="test@example.com",
            row_identifier={"id": 1},
        )

        result = await verifier._verify_cell_value(assertion)

        assert result.passed is True
        assert result.actual_value == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_cell_value_mismatch(self):
        """Test cell value assertion fails on mismatch."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("other@example.com",)

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.CELL_VALUE,
            description="User email should be test@example.com",
            table="users",
            column="email",
            expected_value="test@example.com",
            row_identifier={"id": 1},
        )

        result = await verifier._verify_cell_value(assertion)

        assert result.passed is False
        assert "Expected test@example.com" in result.message

    @pytest.mark.asyncio
    async def test_verify_row_exists(self):
        """Test row exists assertion passes when row found."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_EXISTS,
            description="Admin user exists",
            table="users",
            row_identifier={"role": "admin"},
        )

        result = await verifier._verify_row_exists(assertion)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_verify_row_not_exists(self):
        """Test row exists assertion fails when row not found."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_EXISTS,
            description="Admin user exists",
            table="users",
            row_identifier={"role": "admin"},
        )

        result = await verifier._verify_row_exists(assertion)

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_verify_row_missing(self):
        """Test row missing assertion passes when row not found."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_MISSING,
            description="Deleted user should not exist",
            table="users",
            row_identifier={"id": 999},
        )

        result = await verifier._verify_row_missing(assertion)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_verify_row_missing_found(self):
        """Test row missing assertion fails when row exists."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)

        verifier = DatabaseVerifier(mock_conn)

        assertion = DBAssertion(
            assertion_type=AssertionType.ROW_MISSING,
            description="Deleted user should not exist",
            table="users",
            row_identifier={"id": 1},
        )

        result = await verifier._verify_row_missing(assertion)

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_verify_multiple_assertions(self):
        """Test verify() method processes multiple assertions."""
        from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (5,)

        verifier = DatabaseVerifier(mock_conn)

        assertions = [
            DBAssertion(
                assertion_type=AssertionType.ROW_COUNT,
                description="Has 5 users",
                table="users",
                expected_count=5,
            ),
            DBAssertion(
                assertion_type=AssertionType.ROW_COUNT,
                description="Has 10 orders",
                table="orders",
                expected_count=10,  # Will fail
            ),
        ]

        report = await verifier.verify(assertions)

        assert report.total_assertions == 2
        assert report.passed == 1
        assert report.failed == 1
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

from dv_entity_linking.performance_mock import (
    AhoCorasickSnapshot,
    DATA_PRESETS,
    DVAIAgentServiceMock,
    EntityBatch,
    MockDataStats,
    MockMySqlConfig,
    MockRequestError,
    MySqlEntityDataMockSource,
    WordMatchBatch,
    create_mock_app,
)
from dv_entity_linking.performance_mock.seeder import DataPreset, _entity_rows, _word, _word_rows
from dv_entity_linking.infrastructure.entity_data_rest import RestEntityDataClient


ROOT = Path(__file__).resolve().parents[1]


class _StubSource:
    data_version = "mock-large-1000000-test"

    def health(self) -> str:
        return self.data_version

    def match_words(self, normalized_query, *, entity_types=()):
        matches = ()
        if "cpuusage000001001" in normalized_query and (
            not entity_types or "metric" in entity_types
        ):
            matches = (
                {
                    "entity_word_id": "1001",
                    "entity_id": "DV-MOCK-000000334",
                    "entity_type": "metric",
                    "entity_word": "CPU Usage 000001001",
                    "normalized_key": "cpuusage000001001",
                    "source": "alias",
                    "match_mode": "EXACT_WORD",
                    "min_context_required": False,
                    "context_keywords": [],
                    "priority": 99,
                },
            )
        return WordMatchBatch(matches, self.data_version)

    def batch_get(self, entity_ids):
        entities = {
            "DV-MOCK-000000334": {
                "entity_id": "DV-MOCK-000000334",
                "entity_type": "metric",
                "entity_name": "CPU Usage 000001000",
                "alias": ["CPU Usage 000001001"],
                "desc": "Synthetic load-test entity 334",
                "attributes": {"synthetic": True},
                "relationships": [],
            }
        }
        return EntityBatch(
            tuple(entities[value] for value in entity_ids if value in entities),
            tuple(value for value in entity_ids if value not in entities),
            self.data_version,
        )

    def stats(self):
        return MockDataStats(333_334, 1_000_000, self.data_version)


def test_remote_mock_exposes_contract_compatible_read_operations() -> None:
    service = DVAIAgentServiceMock(_StubSource())

    health = service.execute(
        {"contract_version": "v1", "operation": "HEALTH", "payload": {}}
    )
    match = service.execute(
        {
            "contract_version": "v1",
            "operation": "MATCH_WORDS",
            "payload": {
                "normalized_query": "checkcpuusage000001001now",
                "entity_types": [],
            },
        }
    )
    batch = service.execute(
        {
            "contract_version": "v1",
            "operation": "BATCH_GET_ENTITIES",
            "payload": {
                "entity_ids": ["DV-MOCK-000000334", "DV-MISSING"],
                "expected_data_version": _StubSource.data_version,
            },
        }
    )

    assert health["data"] == {
        "status": "healthy",
        "contract_version": "v4.entity-data.1",
    }
    assert match["operation"] == "MATCH_WORDS"
    assert match["status"] == "success"
    assert match["data"]["matches"][0]["entity_id"] == "DV-MOCK-000000334"
    assert batch["data"]["entities"][0]["entity_id"] == "DV-MOCK-000000334"
    assert batch["data"]["missing_ids"] == ["DV-MISSING"]


def test_remote_mock_rejects_cross_snapshot_batch_get() -> None:
    service = DVAIAgentServiceMock(_StubSource())

    with pytest.raises(MockRequestError, match="data_version_mismatch"):
        service.execute(
            {
                "contract_version": "v1",
                "operation": "BATCH_GET_ENTITIES",
                "payload": {
                    "entity_ids": ["DV-MOCK-000000334"],
                    "expected_data_version": "old-data",
                },
            }
        )


def test_flask_adapter_uses_the_same_execute_envelope() -> None:
    client = create_mock_app(_StubSource()).test_client()

    response = client.post(
        "/v1/entity-data:execute",
        json={
            "contract_version": "v1",
            "operation": "MATCH_WORDS",
            "payload": {
                "normalized_query": "checkcpuusage000001001now",
                "entity_types": [],
            },
        },
    )
    health = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json()["data"]["matches"][0]["normalized_key"] == "cpuusage000001001"
    assert health.status_code == 200
    assert health.get_json()["entity_word_count"] == 1_000_000


class _UrlResponse:
    status = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_existing_rest_client_calls_mock_without_contract_adapter() -> None:
    flask_client = create_mock_app(_StubSource()).test_client()

    def opener(request, timeout):
        response = flask_client.post(
            urlparse(request.full_url).path,
            data=request.data,
            content_type="application/json",
        )
        return _UrlResponse(response.get_json())

    client = RestEntityDataClient("http://mock", opener=opener)

    health = client.health()
    matches = client.match_words("checkcpuusage000001001now")
    entities = client.batch_get(
        ("DV-MOCK-000000334",),
        expected_data_version=matches.data_version,
    )

    assert health.status == "healthy"
    assert matches.matches[0].entity_id == "DV-MOCK-000000334"
    assert entities.entities[0].entity_name == "CPU Usage 000001000"


class _FakeCursor:
    def __init__(self) -> None:
        self.statements: list[tuple[str, Any]] = []
        self._last_statement = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, statement, params=None):
        self._last_statement = " ".join(statement.split())
        self.statements.append((self._last_statement, params))

    def fetchone(self):
        if "mock_metadata" in self._last_statement:
            return ("mock-data-test",)
        return (1,)

    def fetchall(self):
        if "FROM el_entity_word" in self._last_statement:
            return (
                (
                    52,
                    "DV-MOCK-000000018",
                    "device",
                    "KPI000000052",
                    "kpi000000052",
                    "entity_name",
                    "EXACT_WORD",
                    0,
                    "[]",
                    48,
                ),
            )
        return ()


class _FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = _FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def ping(self, reconnect=False):
        return None

    def close(self):
        self.closed = True


class _TestAutomaton:
    def __init__(self) -> None:
        self.patterns: dict[str, int] = {}

    def add_word(self, pattern: str, value: int) -> None:
        self.patterns[pattern] = value

    def make_automaton(self) -> None:
        return None

    def get_stats(self) -> dict[str, int]:
        return {"total_size": 128}

    def iter(self, query: str):
        for pattern, value in self.patterns.items():
            start = query.find(pattern)
            while start >= 0:
                yield start + len(pattern) - 1, value
                start = query.find(pattern, start + 1)


def test_ac_snapshot_finds_overlaps_and_deduplicates_repeated_hits() -> None:
    snapshot = AhoCorasickSnapshot.build(
        "mock-data-ac",
        ((1, "cpu"), (2, "cpuusage"), (3, "usage")),
        automaton_factory=_TestAutomaton,
    )

    assert snapshot.match_ids("cpuusageandcpu") == (1, 2, 3)
    assert snapshot.stats.pattern_count == 3
    assert snapshot.stats.size_bytes == 128


def test_real_pyahocorasick_snapshot_matches_instr_semantics() -> None:
    pytest.importorskip("ahocorasick")
    patterns = ((1, "cpu"), (2, "cpuusage"), (3, "usage"), (4, "alarm"))
    snapshot = AhoCorasickSnapshot.build("mock-data-real-ac", patterns)
    query = "checkcpuusageandcpu"

    expected = tuple(
        entity_word_id
        for entity_word_id, normalized_key in patterns
        if normalized_key in query
    )
    assert snapshot.match_ids(query) == expected
    assert snapshot.stats.size_bytes is not None


class _AcFakeCursor(_FakeCursor):
    def __init__(self) -> None:
        super().__init__()
        self._patterns_delivered = False

    def execute(self, statement, params=None):
        super().execute(statement, params)
        if "SELECT entity_word_id, normalized_key" in self._last_statement:
            self._patterns_delivered = False

    def fetchmany(self, size):
        if "SELECT entity_word_id, normalized_key" not in self._last_statement:
            return ()
        if self._patterns_delivered:
            return ()
        self._patterns_delivered = True
        return ((52, "kpi000000052"), (53, "pi000000052"))

    def fetchall(self):
        if "entity_word_id IN" in self._last_statement:
            return (
                (
                    52,
                    "DV-MOCK-000000018",
                    "device",
                    "KPI000000052",
                    "kpi000000052",
                    "entity_name",
                    "EXACT_WORD",
                    0,
                    "[]",
                    48,
                ),
            )
        return ()


class _AcFakeConnection(_FakeConnection):
    def __init__(self) -> None:
        self.cursor_instance = _AcFakeCursor()
        self.closed = False


def test_mysql_mock_source_owns_instr_sql_and_type_filter() -> None:
    connection = _FakeConnection()
    source = MySqlEntityDataMockSource(
        MockMySqlConfig(pool_size=1), connector=lambda **_: connection
    )

    result = source.match_words("checkkpi000000052", entity_types=("device",))
    source.close()

    query, params = next(
        item
        for item in connection.cursor_instance.statements
        if "FROM el_entity_word" in item[0]
    )
    assert "INSTR(%s, normalized_key) > 0" in query
    assert "status" not in query.casefold()
    assert "entity_type IN (%s)" in query
    assert params == ("checkkpi000000052", "device")
    assert result.matches[0]["entity_id"] == "DV-MOCK-000000018"
    assert connection.closed is True


def test_mysql_mock_source_ac_strategy_builds_then_fetches_hit_metadata(
    monkeypatch,
) -> None:
    import dv_entity_linking.performance_mock.ac_matcher as ac_matcher

    monkeypatch.setattr(ac_matcher, "_default_automaton_factory", _TestAutomaton)
    connection = _AcFakeConnection()
    source = MySqlEntityDataMockSource(
        MockMySqlConfig(pool_size=1),
        connector=lambda **_: connection,
        match_strategy="ac",
    )

    result = source.match_words("checkkpi000000052", entity_types=("device",))
    stats = source.stats()
    source.close()

    statements = connection.cursor_instance.statements
    assert any("SELECT entity_word_id, normalized_key" in sql for sql, _ in statements)
    detail_query, params = next(
        item for item in statements if "entity_word_id IN" in item[0]
    )
    assert "INSTR" not in detail_query
    assert "entity_type IN (%s)" in detail_query
    assert params == (52, 53, "device")
    assert result.matches[0]["entity_id"] == "DV-MOCK-000000018"
    assert stats.match_strategy == "ac"
    assert stats.matcher_pattern_count == 2
    assert stats.matcher_size_bytes == 128


def test_mock_database_name_is_isolated() -> None:
    with pytest.raises(ValueError, match="must start with dv_entity_data_mock"):
        MockMySqlConfig(database="production")


def test_large_data_presets_and_seed_rows_are_deterministic() -> None:
    assert {
        name: preset.entity_word_count for name, preset in DATA_PRESETS.items()
    } == {
        "small": 100_000,
        "medium": 500_000,
        "large": 1_000_000,
        "xlarge": 5_000_000,
    }
    assert _word(1001) == ("CPU Usage 000001001", "cpuusage000001001")
    tiny = DataPreset("test", 6, words_per_entity=3)
    entities = list(_entity_rows(tiny))
    words = list(_word_rows(tiny))
    assert len(entities) == 2
    assert len(words) == 6
    assert len(entities[0]) == 7
    assert len(words[0]) == 10
    assert entities[0][0] == "DV-MOCK-000000001"
    assert json_aliases(entities[0][3]) == [
        "ALM-51020-NODE-000000002",
        "Distributed Service Metric 000000003",
    ]
    assert [row[1] for row in words[:3]] == ["DV-MOCK-000000001"] * 3
    assert [row[0] for row in _entity_rows(tiny, start_index=2)] == [
        "DV-MOCK-000000002"
    ]
    assert [row[0] for row in _word_rows(tiny, start_index=5)] == [5, 6]


def test_new_mock_tables_do_not_define_soft_delete_status_columns() -> None:
    connection = _FakeConnection()

    from dv_entity_linking.performance_mock import MySqlMockDataSeeder

    MySqlMockDataSeeder._create_tables(connection)

    table_statements = [
        statement
        for statement, _ in connection.cursor_instance.statements
        if "CREATE TABLE" in statement
    ]
    assert len(table_statements) == 3
    assert all(" status " not in f" {statement.casefold()} " for statement in table_statements)
    assert any("idx_entity_type" in statement for statement in table_statements)
    assert any("idx_entity_word_type" in statement for statement in table_statements)


def test_legacy_status_migration_drops_columns_without_deleting_rows() -> None:
    connection = _FakeConnection()

    from dv_entity_linking.performance_mock import MySqlMockDataSeeder

    migrated = MySqlMockDataSeeder._remove_legacy_status_columns(connection)

    statements = [item[0] for item in connection.cursor_instance.statements]
    alters = [statement for statement in statements if statement.startswith("ALTER TABLE")]
    assert migrated is True
    assert len(alters) == 2
    assert all("DROP COLUMN `status`" in statement for statement in alters)
    assert not any("DELETE" in statement or "TRUNCATE" in statement for statement in statements)


def test_ready_to_run_query_sample_matches_mock_contract() -> None:
    payload = json.loads(
        (ROOT / "samples/mock/v5_entity_data_performance_queries.json").read_text(
            encoding="utf-8"
        )
    )
    service = DVAIAgentServiceMock(_StubSource())

    results = {
        item["name"]: service.execute(item["request"])
        for item in payload["queries"]
    }

    assert payload["endpoint"] == "/v1/entity-data:execute"
    assert results["no_match"]["data"]["matches"] == []
    assert results["single_hit"]["data"]["matches"][0]["entity_id"] == "DV-MOCK-000000334"
    assert results["batch_get_after_match"]["data"]["entities"][0]["entity_id"] == "DV-MOCK-000000334"


def json_aliases(value: str) -> list[str]:
    import json

    return json.loads(value)

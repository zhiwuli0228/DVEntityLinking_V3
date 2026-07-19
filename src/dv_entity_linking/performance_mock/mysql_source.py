"""Independent pooled MySQL data source used only by the performance mock."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from queue import Empty, LifoQueue
import re
import time
from threading import Lock
from typing import Any, Callable, Iterator, Sequence

from .ac_matcher import AhoCorasickSnapshot, AhoCorasickStats


SAFE_DATABASE = re.compile(r"^dv_entity_data_mock(?:_[a-z0-9_]+)?$")
SAFE_ENTITY_TYPE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class SourceUnavailable(RuntimeError):
    """Safe database-source failure without connection or credential details."""


@dataclass(frozen=True)
class MockMySqlConfig:
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "dv_entity_data_mock"
    pool_size: int = 32
    pool_wait_seconds: float = 5.0
    connect_timeout_seconds: int = 5
    read_timeout_seconds: int = 30
    write_timeout_seconds: int = 30

    def __post_init__(self) -> None:
        if not self.host.strip() or not self.user.strip():
            raise ValueError("MySQL host and user must not be empty")
        if not 1 <= self.port <= 65535:
            raise ValueError("MySQL port must be between 1 and 65535")
        if not SAFE_DATABASE.fullmatch(self.database):
            raise ValueError("mock database must start with dv_entity_data_mock")
        if self.pool_size <= 0 or self.pool_wait_seconds <= 0:
            raise ValueError("pool size and wait time must be positive")
        if min(
            self.connect_timeout_seconds,
            self.read_timeout_seconds,
            self.write_timeout_seconds,
        ) <= 0:
            raise ValueError("MySQL timeouts must be positive")


@dataclass(frozen=True)
class WordMatchBatch:
    matches: tuple[dict[str, Any], ...]
    data_version: str


@dataclass(frozen=True)
class EntityBatch:
    entities: tuple[dict[str, Any], ...]
    missing_ids: tuple[str, ...]
    data_version: str


@dataclass(frozen=True)
class MockDataStats:
    entity_count: int
    entity_word_count: int
    data_version: str
    match_strategy: str = "instr"
    matcher_data_version: str | None = None
    matcher_pattern_count: int = 0
    matcher_build_seconds: float | None = None
    matcher_size_bytes: int | None = None


Connector = Callable[..., Any]


def _default_connector(**kwargs: Any) -> Any:
    try:
        import pymysql
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            "PyMySQL is required; install dv-entity-linking[performance-mock]"
        ) from exc
    return pymysql.connect(**kwargs)


def _decode_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return fallback


class MySqlEntityDataMockSource:
    """The only performance-mock class allowed to query MySQL.

    Connections are created lazily up to ``pool_size`` and reused across HTTP
    requests. The class has no dependency on Flask or the production recall
    module, so it can be tested and moved independently.
    """

    def __init__(
        self,
        config: MockMySqlConfig,
        *,
        connector: Connector | None = None,
        match_strategy: str = "instr",
    ) -> None:
        if match_strategy not in {"instr", "ac"}:
            raise ValueError("match_strategy must be instr or ac")
        self.config = config
        self.match_strategy = match_strategy
        self._connector = connector or _default_connector
        self._pool: LifoQueue[Any] = LifoQueue(maxsize=config.pool_size)
        self._created = 0
        self._lock = Lock()
        self._closed = False
        self._matcher_lock = Lock()
        self._ac_snapshot: AhoCorasickSnapshot | None = None
        self._timings: list[dict[str, float]] = []
        self._timings_lock = Lock()

    def _new_connection(self) -> Any:
        return self._connector(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=self.config.connect_timeout_seconds,
            read_timeout=self.config.read_timeout_seconds,
            write_timeout=self.config.write_timeout_seconds,
        )

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        if self._closed:
            raise SourceUnavailable("mock_data_source_closed")
        connection = None
        reserved_new = False
        try:
            try:
                connection = self._pool.get_nowait()
            except Empty:
                with self._lock:
                    if self._created < self.config.pool_size:
                        self._created += 1
                        reserved_new = True
                if reserved_new:
                    try:
                        connection = self._new_connection()
                    except Exception as exc:
                        with self._lock:
                            self._created -= 1
                        raise SourceUnavailable("mock_database_connect_failed") from exc
                else:
                    try:
                        connection = self._pool.get(
                            timeout=self.config.pool_wait_seconds
                        )
                    except Empty as exc:
                        raise SourceUnavailable("mock_database_pool_exhausted") from exc
            try:
                connection.ping(reconnect=True)
            except Exception as exc:
                self._discard(connection)
                connection = None
                raise SourceUnavailable("mock_database_connect_failed") from exc
            yield connection
        finally:
            if connection is not None:
                try:
                    connection.ping(reconnect=False)
                except Exception:
                    self._discard(connection)
                else:
                    if self._closed:
                        self._discard(connection)
                    else:
                        self._pool.put(connection)

    def _discard(self, connection: Any) -> None:
        try:
            connection.close()
        except Exception:
            pass
        with self._lock:
            self._created = max(0, self._created - 1)

    @staticmethod
    def _data_version(cursor: Any) -> str:
        cursor.execute(
            "SELECT data_version FROM mock_metadata WHERE singleton_id = 1"
        )
        row = cursor.fetchone()
        if not row or not isinstance(row[0], str):
            raise SourceUnavailable("mock_data_not_prepared")
        return row[0]

    def health(self) -> str:
        try:
            with self._connection() as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return self._data_version(cursor)
        except SourceUnavailable:
            raise
        except Exception as exc:
            raise SourceUnavailable("mock_database_query_failed") from exc

    def match_words(
        self,
        normalized_query: str,
        *,
        entity_types: Sequence[str] = (),
    ) -> WordMatchBatch:
        if not isinstance(normalized_query, str) or not normalized_query:
            raise ValueError("normalized_query must not be empty")
        if len(normalized_query) > 16_384:
            raise ValueError("normalized_query is too long")
        normalized_types = tuple(dict.fromkeys(str(value) for value in entity_types))
        if len(normalized_types) > 64 or any(
            not SAFE_ENTITY_TYPE.fullmatch(value) for value in normalized_types
        ):
            raise ValueError("invalid entity_types")
        if self.match_strategy == "ac":
            return self._match_words_ac(normalized_query, normalized_types)
        return self._match_words_instr(normalized_query, normalized_types)

    def _match_words_instr(
        self,
        normalized_query: str,
        normalized_types: tuple[str, ...],
    ) -> WordMatchBatch:
        statement = """
            SELECT entity_word_id, entity_id, entity_type, entity_word,
                   normalized_key, source, match_mode, min_context_required,
                   context_keywords_json, priority
            FROM el_entity_word
            WHERE INSTR(%s, normalized_key) > 0
        """
        params: list[Any] = [normalized_query]
        if normalized_types:
            placeholders = ", ".join(["%s"] * len(normalized_types))
            statement += f" AND entity_type IN ({placeholders})"
            params.extend(normalized_types)
        statement += " ORDER BY priority DESC, entity_word_id ASC"
        try:
            with self._connection() as connection, connection.cursor() as cursor:
                data_version = self._data_version(cursor)
                cursor.execute(statement, tuple(params))
                rows = cursor.fetchall()
        except SourceUnavailable:
            raise
        except Exception as exc:
            raise SourceUnavailable("mock_database_query_failed") from exc
        return WordMatchBatch(self._map_word_rows(rows), data_version)

    @staticmethod
    def _map_word_rows(rows: Sequence[Sequence[Any]]) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "entity_word_id": str(row[0]),
                "entity_id": str(row[1]),
                "entity_type": str(row[2]),
                "entity_word": str(row[3]),
                "normalized_key": str(row[4]),
                "source": str(row[5]),
                "match_mode": str(row[6]),
                "min_context_required": bool(row[7]),
                "context_keywords": tuple(
                    str(value) for value in _decode_json(row[8], [])
                ),
                "priority": int(row[9]),
            }
            for row in rows
        )

    @staticmethod
    def _matcher_patterns(cursor: Any, *, batch_size: int = 10_000):
        cursor.execute(
            "SELECT entity_word_id, normalized_key "
            "FROM el_entity_word WHERE normalized_key <> '' "
            "ORDER BY entity_word_id ASC"
        )
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                return
            for entity_word_id, normalized_key in rows:
                yield int(entity_word_id), str(normalized_key)

    def _build_ac_snapshot(self) -> AhoCorasickSnapshot:
        try:
            with self._connection() as connection, connection.cursor() as cursor:
                data_version = self._data_version(cursor)
                snapshot = AhoCorasickSnapshot.build(
                    data_version,
                    self._matcher_patterns(cursor),
                )
                if self._data_version(cursor) != data_version:
                    raise SourceUnavailable("mock_data_changed_during_matcher_build")
                return snapshot
        except SourceUnavailable:
            raise
        except RuntimeError:
            raise
        except Exception as exc:
            raise SourceUnavailable("mock_matcher_build_failed") from exc

    def prepare_matcher(self, *, force: bool = False) -> AhoCorasickStats | None:
        if self.match_strategy != "ac":
            return None
        snapshot = self._ac_snapshot
        if not force and snapshot is not None:
            try:
                with self._connection() as connection, connection.cursor() as cursor:
                    current_version = self._data_version(cursor)
            except SourceUnavailable:
                raise
            except Exception as exc:
                raise SourceUnavailable("mock_database_query_failed") from exc
            if snapshot.stats.data_version == current_version:
                return snapshot.stats
        with self._matcher_lock:
            snapshot = self._ac_snapshot
            if not force and snapshot is not None:
                try:
                    with self._connection() as connection, connection.cursor() as cursor:
                        current_version = self._data_version(cursor)
                except SourceUnavailable:
                    raise
                except Exception as exc:
                    raise SourceUnavailable("mock_database_query_failed") from exc
                if snapshot.stats.data_version == current_version:
                    return snapshot.stats
            snapshot = self._build_ac_snapshot()
            self._ac_snapshot = snapshot
            return snapshot.stats

    @staticmethod
    def _timings_enabled() -> bool:
        return os.environ.get("DV_MOCK_TIMING") == "1"

    def _record_timing(self, ac_ms: float, dv_ms: float, fetch_ms: float) -> None:
        with self._timings_lock:
            self._timings.append(
                {
                    "ac_match_ms": round(ac_ms, 3),
                    "data_version_ms": round(dv_ms, 3),
                    "fetch_ms": round(fetch_ms, 3),
                }
            )

    def drain_timings(self) -> list[dict[str, float]]:
        with self._timings_lock:
            captured, self._timings = self._timings, []
        return captured

    def _match_words_ac(
        self,
        normalized_query: str,
        normalized_types: tuple[str, ...],
    ) -> WordMatchBatch:
        timing_on = self._timings_enabled()
        for attempt in range(2):
            self.prepare_matcher(force=attempt > 0)
            snapshot = self._ac_snapshot
            if snapshot is None:  # pragma: no cover - defensive invariant
                raise SourceUnavailable("mock_matcher_not_ready")
            if timing_on:
                _t0 = time.perf_counter()
                matched_ids = snapshot.match_ids(normalized_query)
                ac_ms = (time.perf_counter() - _t0) * 1000
            else:
                matched_ids = snapshot.match_ids(normalized_query)
                ac_ms = 0.0
            if not matched_ids:
                if timing_on:
                    self._record_timing(ac_ms, 0.0, 0.0)
                return WordMatchBatch((), snapshot.stats.data_version)

            rows: list[Sequence[Any]] = []
            version_changed = False
            dv_ms = 0.0
            fetch_ms = 0.0
            try:
                with self._connection() as connection, connection.cursor() as cursor:
                    if timing_on:
                        _t1 = time.perf_counter()
                        version_changed = (
                            self._data_version(cursor) != snapshot.stats.data_version
                        )
                        dv_ms = (time.perf_counter() - _t1) * 1000
                    else:
                        version_changed = (
                            self._data_version(cursor) != snapshot.stats.data_version
                        )
                    if not version_changed:
                        if timing_on:
                            _t2 = time.perf_counter()
                        for offset in range(0, len(matched_ids), 500):
                            batch = matched_ids[offset : offset + 500]
                            placeholders = ", ".join(["%s"] * len(batch))
                            statement = f"""
                                SELECT entity_word_id, entity_id, entity_type,
                                       entity_word, normalized_key, source,
                                       match_mode, min_context_required,
                                       context_keywords_json, priority
                                FROM el_entity_word
                                WHERE entity_word_id IN ({placeholders})
                            """
                            params: list[Any] = list(batch)
                            if normalized_types:
                                type_placeholders = ", ".join(
                                    ["%s"] * len(normalized_types)
                                )
                                statement += (
                                    f" AND entity_type IN ({type_placeholders})"
                                )
                                params.extend(normalized_types)
                            cursor.execute(statement, tuple(params))
                            rows.extend(cursor.fetchall())
                        if timing_on:
                            fetch_ms = (time.perf_counter() - _t2) * 1000
            except SourceUnavailable:
                raise
            except Exception as exc:
                raise SourceUnavailable("mock_database_query_failed") from exc
            if version_changed:
                continue
            rows.sort(key=lambda row: (-int(row[9]), int(row[0])))
            if timing_on:
                self._record_timing(ac_ms, dv_ms, fetch_ms)
            return WordMatchBatch(
                self._map_word_rows(rows),
                snapshot.stats.data_version,
            )
        raise SourceUnavailable("mock_data_version_unstable")

    def batch_get(self, entity_ids: Sequence[str]) -> EntityBatch:
        requested_ids = tuple(dict.fromkeys(str(value) for value in entity_ids))
        if len(requested_ids) > 1_000 or any(
            not value or len(value) > 128 for value in requested_ids
        ):
            raise ValueError("invalid entity_ids")
        try:
            with self._connection() as connection, connection.cursor() as cursor:
                data_version = self._data_version(cursor)
                if not requested_ids:
                    return EntityBatch((), (), data_version)
                placeholders = ", ".join(["%s"] * len(requested_ids))
                cursor.execute(
                    f"""
                    SELECT entity_id, entity_type, entity_name, alias_json,
                           description, attributes_json, relationships_json
                    FROM el_entity
                    WHERE entity_id IN ({placeholders})
                    """,
                    requested_ids,
                )
                rows = cursor.fetchall()
        except SourceUnavailable:
            raise
        except Exception as exc:
            raise SourceUnavailable("mock_database_query_failed") from exc
        mapped = {
            str(row[0]): {
                "entity_id": str(row[0]),
                "entity_type": str(row[1]),
                "entity_name": str(row[2]),
                "alias": tuple(str(value) for value in _decode_json(row[3], [])),
                "desc": str(row[4]),
                "attributes": dict(_decode_json(row[5], {})),
                "relationships": tuple(
                    dict(value)
                    for value in _decode_json(row[6], [])
                    if isinstance(value, dict)
                ),
            }
            for row in rows
        }
        return EntityBatch(
            tuple(mapped[value] for value in requested_ids if value in mapped),
            tuple(value for value in requested_ids if value not in mapped),
            data_version,
        )

    def stats(self) -> MockDataStats:
        try:
            with self._connection() as connection, connection.cursor() as cursor:
                data_version = self._data_version(cursor)
                cursor.execute("SELECT COUNT(*) FROM el_entity")
                entity_count = int(cursor.fetchone()[0])
                cursor.execute("SELECT COUNT(*) FROM el_entity_word")
                word_count = int(cursor.fetchone()[0])
        except SourceUnavailable:
            raise
        except Exception as exc:
            raise SourceUnavailable("mock_database_query_failed") from exc
        matcher = self._ac_snapshot.stats if self._ac_snapshot is not None else None
        return MockDataStats(
            entity_count,
            word_count,
            data_version,
            match_strategy=self.match_strategy,
            matcher_data_version=matcher.data_version if matcher else None,
            matcher_pattern_count=matcher.pattern_count if matcher else 0,
            matcher_build_seconds=matcher.build_seconds if matcher else None,
            matcher_size_bytes=matcher.size_bytes if matcher else None,
        )

    def close(self) -> None:
        self._closed = True
        while True:
            try:
                connection = self._pool.get_nowait()
            except Empty:
                break
            self._discard(connection)

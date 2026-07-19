"""Deterministic large-data provisioning for the MySQL performance mock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from typing import Any, Iterable

from .mysql_source import Connector, MockMySqlConfig, _default_connector


@dataclass(frozen=True)
class DataPreset:
    name: str
    entity_word_count: int
    words_per_entity: int = 3

    @property
    def entity_count(self) -> int:
        return math.ceil(self.entity_word_count / self.words_per_entity)


DATA_PRESETS: dict[str, DataPreset] = {
    "small": DataPreset("small", 100_000),
    "medium": DataPreset("medium", 500_000),
    "large": DataPreset("large", 1_000_000),
    "xlarge": DataPreset("xlarge", 5_000_000),
}


@dataclass(frozen=True)
class SeedReport:
    preset: str
    entity_count: int
    entity_word_count: int
    data_version: str
    reused_existing_data: bool


def _entity_type(entity_index: int) -> str:
    bucket = entity_index % 20
    if bucket < 16:
        return "metric"
    return ("alarm", "application", "device", "service")[bucket - 16]


def _word(index: int) -> tuple[str, str]:
    variant = index % 4
    if variant == 0:
        value = f"KPI{index:09d}"
    elif variant == 1:
        value = f"CPU Usage {index:09d}"
    elif variant == 2:
        value = f"ALM-51020-NODE-{index:09d}"
    else:
        value = f"Distributed Service Metric {index:09d}"
    return value, value.casefold().replace(" ", "")


def _entity_rows(
    preset: DataPreset,
    *,
    start_index: int = 1,
) -> Iterable[tuple[Any, ...]]:
    for entity_index in range(start_index, preset.entity_count + 1):
        first_word_index = (entity_index - 1) * preset.words_per_entity + 1
        last_word_index = min(
            first_word_index + preset.words_per_entity - 1,
            preset.entity_word_count,
        )
        name, _ = _word(first_word_index)
        aliases = [_word(index)[0] for index in range(first_word_index + 1, last_word_index + 1)]
        yield (
            f"DV-MOCK-{entity_index:09d}",
            _entity_type(entity_index),
            name,
            json.dumps(aliases, ensure_ascii=False),
            f"Synthetic load-test entity {entity_index}",
            json.dumps({"synthetic": True, "ordinal": entity_index}),
            "[]",
        )


def _word_rows(
    preset: DataPreset,
    *,
    start_index: int = 1,
) -> Iterable[tuple[Any, ...]]:
    for index in range(start_index, preset.entity_word_count + 1):
        entity_index = (index - 1) // preset.words_per_entity + 1
        entity_word, normalized_key = _word(index)
        entity_type = _entity_type(entity_index)
        yield (
            index,
            f"DV-MOCK-{entity_index:09d}",
            entity_type,
            entity_word,
            normalized_key,
            "entity_name" if (index - 1) % preset.words_per_entity == 0 else "alias",
            "STRUCTURED_TOKEN" if entity_type == "alarm" else "EXACT_WORD",
            1 if index % 5 == 0 else 0,
            '["system", "node"]' if index % 5 == 0 else "[]",
            100 - (index % 100),
        )


class MySqlMockDataSeeder:
    """Creates only the dedicated mock schema and its deterministic tables."""

    def __init__(
        self,
        config: MockMySqlConfig,
        *,
        connector: Connector | None = None,
    ) -> None:
        self.config = config
        self._connector = connector or _default_connector

    def _connect(self, *, database: str | None, autocommit: bool) -> Any:
        kwargs: dict[str, Any] = {
            "host": self.config.host,
            "port": self.config.port,
            "user": self.config.user,
            "password": self.config.password,
            "charset": "utf8mb4",
            "autocommit": autocommit,
            "connect_timeout": self.config.connect_timeout_seconds,
            "read_timeout": self.config.read_timeout_seconds,
            "write_timeout": self.config.write_timeout_seconds,
        }
        if database is not None:
            kwargs["database"] = database
        return self._connector(**kwargs)

    def _ensure_schema(self) -> None:
        connection = self._connect(database=None, autocommit=True)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.config.database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                )
        finally:
            connection.close()

    @staticmethod
    def _create_tables(connection: Any) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS el_entity (
                    entity_id VARCHAR(64) NOT NULL,
                    entity_type VARCHAR(64) NOT NULL,
                    entity_name VARCHAR(255) NOT NULL,
                    alias_json JSON NOT NULL,
                    description VARCHAR(512) NOT NULL,
                    attributes_json JSON NOT NULL,
                    relationships_json JSON NOT NULL,
                    PRIMARY KEY (entity_id),
                    KEY idx_entity_type (entity_type)
                ) ENGINE=InnoDB
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS el_entity_word (
                    entity_word_id BIGINT NOT NULL,
                    entity_id VARCHAR(64) NOT NULL,
                    entity_type VARCHAR(64) NOT NULL,
                    entity_word VARCHAR(255) NOT NULL,
                    normalized_key VARCHAR(255) NOT NULL,
                    source VARCHAR(32) NOT NULL,
                    match_mode VARCHAR(32) NOT NULL,
                    min_context_required TINYINT NOT NULL,
                    context_keywords_json JSON NOT NULL,
                    priority INT NOT NULL,
                    PRIMARY KEY (entity_word_id),
                    UNIQUE KEY uk_normalized_key (normalized_key),
                    KEY idx_entity_word_type (entity_type),
                    KEY idx_entity_id (entity_id)
                ) ENGINE=InnoDB
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mock_metadata (
                    singleton_id TINYINT NOT NULL,
                    preset_name VARCHAR(32) NOT NULL,
                    data_version VARCHAR(128) NOT NULL,
                    entity_count BIGINT NOT NULL,
                    entity_word_count BIGINT NOT NULL,
                    generated_at_utc VARCHAR(64) NOT NULL,
                    PRIMARY KEY (singleton_id)
                ) ENGINE=InnoDB
                """
            )

    @staticmethod
    def _remove_legacy_status_columns(connection: Any) -> bool:
        """Upgrade the old mock schema without deleting any entity data rows."""
        migrated = False
        migrations = (
            (
                "el_entity",
                "idx_entity_status_type",
                "idx_entity_type",
                "entity_type",
            ),
            (
                "el_entity_word",
                "idx_status_entity_type",
                "idx_entity_word_type",
                "entity_type",
            ),
        )
        with connection.cursor() as cursor:
            for table, old_index, new_index, indexed_column in migrations:
                cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE 'status'")
                if cursor.fetchone() is None:
                    continue
                cursor.execute(
                    f"ALTER TABLE `{table}` "
                    f"DROP INDEX `{old_index}`, "
                    "DROP COLUMN `status`, "
                    f"ADD INDEX `{new_index}` (`{indexed_column}`)"
                )
                migrated = True
        return migrated

    @staticmethod
    def _progress(connection: Any) -> tuple[int, int, int, int, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*),
                       COALESCE(MAX(CAST(SUBSTRING(entity_id, 9) AS UNSIGNED)), 0)
                FROM el_entity
                """
            )
            entity_count, max_entity_ordinal = (int(value) for value in cursor.fetchone())
            cursor.execute(
                "SELECT COUNT(*), COALESCE(MAX(entity_word_id), 0) FROM el_entity_word"
            )
            word_count, max_word_id = (int(value) for value in cursor.fetchone())
            cursor.execute("SELECT COUNT(*) FROM mock_metadata")
            metadata_count = int(cursor.fetchone()[0])
        return (
            entity_count,
            max_entity_ordinal,
            word_count,
            max_word_id,
            metadata_count,
        )

    @staticmethod
    def _insert_batches(
        connection: Any,
        statement: str,
        rows: Iterable[tuple[Any, ...]],
        batch_size: int,
    ) -> None:
        pending: list[tuple[Any, ...]] = []
        with connection.cursor() as cursor:
            for row in rows:
                pending.append(row)
                if len(pending) == batch_size:
                    cursor.executemany(statement, pending)
                    connection.commit()
                    pending.clear()
            if pending:
                cursor.executemany(statement, pending)
                connection.commit()

    def prepare(
        self,
        preset_name: str = "large",
        *,
        batch_size: int = 5_000,
    ) -> SeedReport:
        if preset_name not in DATA_PRESETS:
            raise ValueError(f"unknown data preset: {preset_name}")
        if batch_size <= 0 or batch_size > 20_000:
            raise ValueError("batch_size must be between 1 and 20000")
        preset = DATA_PRESETS[preset_name]
        self._ensure_schema()
        connection = self._connect(database=self.config.database, autocommit=False)
        try:
            self._create_tables(connection)
            schema_migrated = self._remove_legacy_status_columns(connection)
            connection.commit()
            (
                entity_count,
                max_entity_ordinal,
                word_count,
                max_word_id,
                metadata_count,
            ) = self._progress(connection)
            if entity_count > preset.entity_count or word_count > preset.entity_word_count:
                raise RuntimeError("existing mock data exceeds the selected preset")
            if max_entity_ordinal != entity_count or max_word_id != word_count:
                raise RuntimeError("existing mock data is not a contiguous seed prefix")
            if word_count and entity_count != preset.entity_count:
                raise RuntimeError("entity words exist before the entity seed is complete")
            if metadata_count and (
                entity_count != preset.entity_count
                or word_count != preset.entity_word_count
            ):
                raise RuntimeError("ready metadata conflicts with partial mock data")
            if (
                not schema_migrated
                and entity_count == preset.entity_count
                and word_count == preset.entity_word_count
            ):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT data_version FROM mock_metadata WHERE singleton_id = 1"
                    )
                    row = cursor.fetchone()
                if row and isinstance(row[0], str):
                    return SeedReport(
                        preset.name,
                        entity_count,
                        word_count,
                        row[0],
                        True,
                    )
            if entity_count < preset.entity_count:
                self._insert_batches(
                    connection,
                    """
                    INSERT INTO el_entity (
                        entity_id, entity_type, entity_name, alias_json, description,
                        attributes_json, relationships_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    _entity_rows(preset, start_index=entity_count + 1),
                    batch_size,
                )
            if word_count < preset.entity_word_count:
                self._insert_batches(
                    connection,
                    """
                    INSERT INTO el_entity_word (
                        entity_word_id, entity_id, entity_type, entity_word,
                        normalized_key, source, match_mode, min_context_required,
                        context_keywords_json, priority
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    _word_rows(preset, start_index=word_count + 1),
                    batch_size,
                )
            data_version = (
                f"mock-{preset.name}-{preset.entity_word_count}-"
                + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO mock_metadata (
                        singleton_id, preset_name, data_version, entity_count,
                        entity_word_count, generated_at_utc
                    ) VALUES (1, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        preset_name = VALUES(preset_name),
                        data_version = VALUES(data_version),
                        entity_count = VALUES(entity_count),
                        entity_word_count = VALUES(entity_word_count),
                        generated_at_utc = VALUES(generated_at_utc)
                    """,
                    (
                        preset.name,
                        data_version,
                        preset.entity_count,
                        preset.entity_word_count,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                cursor.execute("ANALYZE TABLE el_entity")
                cursor.fetchall()
                cursor.execute("ANALYZE TABLE el_entity_word")
                cursor.fetchall()
            connection.commit()
            return SeedReport(
                preset.name,
                preset.entity_count,
                preset.entity_word_count,
                data_version,
                False,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

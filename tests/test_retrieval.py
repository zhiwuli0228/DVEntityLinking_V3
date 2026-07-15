from __future__ import annotations

import json
from pathlib import Path

from dv_entity_linking.legacy.models import Status


def test_top_k_retrieval_returns_required_item_fields(service):
    result = service.retriever.similar_entities("NE-DV-RAN-001", k=5)

    assert result.status == Status.LINKED
    assert result.k == 5
    assert result.items
    first = result.items[0]
    assert first.entity_id
    assert first.entity_name
    assert first.entity_type
    assert 0.0 <= first.score <= 1.0
    assert first.similarity_reason
    assert first.source
    assert first.data_layer


def test_top_k_caps_at_twenty(service):
    result = service.retriever.similar_entities("NE-DV-RAN-001", k=100)

    assert result.k == 20
    assert len(result.items) <= 20


def test_top_k_sorting_is_stable(service):
    result = service.retriever.similar_entities("NE-DV-RAN-001", k=20)

    ordered = [(item.score, item.entity_id) for item in result.items]
    assert ordered == sorted(ordered, key=lambda item: (-item[0], item[1]))


def test_retrieval_samples_cover_expected_reasons(service):
    samples = json.loads(Path("samples/mock/query_samples.json").read_text(encoding="utf-8"))

    for sample in samples["retrieval_samples"]:
        result = service.retriever.similar_entities(sample["entity_id"], sample["k"])
        reasons = " | ".join(item.similarity_reason for item in result.items)

        assert sample["expected_reason"] in reasons, sample["id"]

from __future__ import annotations

import json

from dv_entity_linking.application.dto import CandidateResponseV1, LinkResponseV1
from dv_entity_linking.query_recall import QueryRecallFacade, RecallConfigProvider


class _Linker:
    def __init__(self) -> None:
        self.requests = []

    def link(self, request):
        self.requests.append(request)
        candidates = tuple(
            CandidateResponseV1(f"E-{index}", f"Entity {index}", "alarm", 1.0 / index, index)
            for index in range(1, 5)
        )
        return LinkResponseV1("v4.link-response.1", request.query, "linked", candidates=candidates)


def _write(path, *, use_llm=False, top_k=2):
    path.write_text(json.dumps({"recall": {"use_llm": use_llm, "top_k": top_k}}), encoding="utf-8")


def test_query_recall_uses_config_and_versionless_result(tmp_path) -> None:
    path = tmp_path / "recall.json"
    _write(path, use_llm=True, top_k=2)
    linker = _Linker()
    result = QueryRecallFacade(linker, RecallConfigProvider(path)).recall("check alarm")

    assert result.status == "linked"
    assert len(result.candidates) == 2
    assert linker.requests[0].extraction_mode == "llm"
    assert type(result).__name__ == "QueryRecallResult"


def test_query_recall_override_and_invalid_reload_keeps_last_policy(tmp_path) -> None:
    path = tmp_path / "recall.json"
    _write(path, use_llm=False, top_k=3)
    linker = _Linker()
    provider = RecallConfigProvider(path)
    facade = QueryRecallFacade(linker, provider)

    assert len(facade.recall("check", use_llm=True, top_k=1).candidates) == 1
    assert linker.requests[-1].extraction_mode == "llm"
    path.write_text("not-json", encoding="utf-8")
    assert len(facade.recall("check").candidates) == 3
    assert provider.last_error == "recall_config_reload_failed"

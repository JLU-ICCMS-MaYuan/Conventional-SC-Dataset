import anyio

from backend.rag import knowledge_graph


class _AsyncSession:
    def __init__(self, results):
        self.results = list(results)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _stmt):
        return self.results.pop(0)


class _Row:
    chemical_formula = "LaH10"

    def __getitem__(self, index):
        return {
            1: 250.0,
            2: 42,
            3: "High-pressure hydride",
        }[index]


class _RowsResult:
    def all(self):
        return [_Row()]


class _ScalarValueResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class _ScalarsResult:
    def __init__(self, record):
        self.record = record

    def scalars(self):
        return self

    def first(self):
        return self.record


def _session_factory(*results):
    return lambda: _AsyncSession(results)


def test_query_returns_empty_for_unknown_predicate():
    async def run():
        assert await knowledge_graph.query("未知属性", ">", "1") == []

    anyio.run(run)


def test_query_maps_approved_structured_records(monkeypatch):
    monkeypatch.setattr(knowledge_graph, "async_session_factory", _session_factory(_RowsResult()))

    async def run():
        result = await knowledge_graph.query("超导温度(AD)", ">", "200")

        assert result == [
            {
                "subject": "LaH10",
                "predicate": "超导温度(AD)",
                "object": "250.0",
                "paper_id": 42,
                "paper_title": "High-pressure hydride",
            }
        ]

    anyio.run(run)


def test_query_rejects_invalid_numeric_filter():
    async def run():
        assert await knowledge_graph.query("压力", ">", "not-a-number") == []

    anyio.run(run)


def test_get_all_properties_filters_empty_values(monkeypatch):
    record = type(
        "Record",
        (),
        {
            "allen_dynes_tc": 250.0,
            "experimental_tc": None,
            "pressure_gpa": 200.0,
            "lambda_value": 2.1,
            "omega_log": None,
            "space_group_symbol": "Fm-3m",
        },
    )()
    monkeypatch.setattr(knowledge_graph, "async_session_factory", _session_factory(_ScalarsResult(record)))

    async def run():
        result = await knowledge_graph.get_all_properties("LaH10")

        assert result == [
            {"predicate": "超导温度(AD)", "object": "250.0"},
            {"predicate": "压力", "object": "200.0"},
            {"predicate": "电声耦合lambda", "object": "2.1"},
            {"predicate": "空间群", "object": "Fm-3m"},
        ]

    anyio.run(run)


def test_stats_counts_approved_subjects_and_triples(monkeypatch):
    monkeypatch.setattr(
        knowledge_graph,
        "async_session_factory",
        _session_factory(_ScalarValueResult(3), _ScalarValueResult(12)),
    )

    async def run():
        assert await knowledge_graph.stats() == {"subjects": 3, "triples": 12}

    anyio.run(run)

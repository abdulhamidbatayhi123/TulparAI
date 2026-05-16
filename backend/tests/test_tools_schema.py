"""Sanity tests for the tool schema + dispatch table."""
from backend.tools.schema import TOOL_SCHEMAS, DISPATCH, schema_dispatch_consistent


def test_schema_dispatch_names_match():
    assert schema_dispatch_consistent(), (
        f"schemas={sorted({t['function']['name'] for t in TOOL_SCHEMAS})} "
        f"dispatch={sorted(DISPATCH.keys())}"
    )


def test_every_schema_has_required_fields():
    for t in TOOL_SCHEMAS:
        assert t["type"] == "function"
        fn = t["function"]
        assert "name" in fn and isinstance(fn["name"], str)
        assert "description" in fn and len(fn["description"]) > 20
        assert "parameters" in fn and "properties" in fn["parameters"]


def test_six_tools_exposed():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert names == {
        "search_sport_kb",
        "get_food_macros",
        "calc_macros",
        "get_weather",
        "log_session",
        "web_search_trusted",
    }


def test_search_sport_kb_constrains_sport_enum():
    s = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == "search_sport_kb")
    enum = s["function"]["parameters"]["properties"]["sport"]["enum"]
    assert set(enum) == {"football", "wrestling", "weightlifting", "volleyball"}

from letai_factbase.schemas import AgentContextPack


def test_agent_context_pack_has_usage_rules() -> None:
    pack = AgentContextPack(query="工银亚洲抵押事实")
    assert pack.usage_rules
    assert "Only confirmed facts" in pack.usage_rules[0]

from safeloop_visual.prompts import visual_loop_prompt


def test_prompt_separates_visual_from_gameplay_qa():
    prompt = visual_loop_prompt("Make it pretty")
    assert "VISUAL" in prompt
    assert "gameplay/physics QA" in prompt
    assert "actual render" in prompt

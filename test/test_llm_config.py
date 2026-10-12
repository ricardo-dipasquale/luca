from tools.llm_config import chat_completion_params, create_openai_llm, temperature_for


def test_fixed_temperature_models_omit_it():
    assert temperature_for("gpt-6-luna", 0.1) is None
    assert temperature_for("o3-mini", 0.1) is None
    assert temperature_for("gpt-4o-mini", 0.1) == 0.1


def test_raw_params_use_max_completion_tokens():
    assert chat_completion_params("gpt-6-luna", 0.1, 200) == {"model": "gpt-6-luna", "max_completion_tokens": 200}
    assert chat_completion_params("gpt-4o-mini", 0.1, 200) == {
        "model": "gpt-4o-mini", "max_completion_tokens": 200, "temperature": 0.1,
    }


def test_chat_llm_does_not_send_temperature_for_luna(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DEFAULT_LLM_TEMPERATURE", "0.1")
    assert "temperature" not in create_openai_llm(model="gpt-6-luna")._default_params
    assert create_openai_llm(model="gpt-4o-mini")._default_params["temperature"] == 0.1

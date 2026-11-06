"""Offline tests for the Claude Messages API adapter."""
from finnorte import llm
from finnorte.config import Config


def test_anthropic_uses_messages_api_and_accounts_json_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "4096")
    calls = []

    class HttpResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "model": "claude-sonnet-5-5",
                "content": [{"type": "text", "text": '{"ok": true}'}],
                "usage": {"input_tokens": 100, "output_tokens": 5},
                "stop_reason": "max_tokens",
            }

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return HttpResponse()

    monkeypatch.setattr(llm, "config", lambda: Config(
        llm_proveedor="anthropic",
        llm_modelo="claude-sonnet-5-5",
        anthropic_key="fake-test-key",
    ))
    monkeypatch.setattr(llm.requests, "post", post)
    eventos = []
    monkeypatch.setattr(llm.trazas, "registrar", lambda tipo, **kw: eventos.append((tipo, kw)))

    result = llm.generar(
        "Return an object with ok=true.",
        sistema="You are an assistant.",
        json=True,
        historial=[{"rol": "user", "texto": "Say hello."}, {"rol": "model", "texto": "Hello."}],
        registrar=True,
    )

    url, request = calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert request["headers"]["anthropic-version"] == "2023-06-01"
    assert request["headers"]["x-api-key"] == "fake-test-key"
    body = request["json"]
    assert body["model"] == "claude-sonnet-5-5"
    assert body["max_tokens"] == 4096
    assert "temperature" not in body
    assert body["messages"] == [
        {"role": "user", "content": "Say hello."},
        {"role": "assistant", "content": "Hello."},
        {"role": "user", "content": "Return an object with ok=true."},
    ]
    assert "valid JSON" in body["system"]
    assert result.proveedor == "anthropic"
    assert result.modelo == "claude-sonnet-5-5"
    assert result.datos == {"ok": True}
    assert (result.tokens_entrada, result.tokens_salida) == (100, 5)
    assert result.costo_usd == 0.00025
    assert result.extra == {
        "stop_reason": "max_tokens",
        "max_tokens": 4096,
        "limite_tokens_alcanzado": True,
    }
    assert eventos[0][1]["stop_reason"] == "max_tokens"
    assert eventos[0][1]["max_tokens"] == 4096
    assert eventos[0][1]["limite_tokens_alcanzado"] is True


def test_anthropic_without_key_fails_without_request(monkeypatch):
    monkeypatch.setattr(llm, "config", lambda: Config(
        llm_proveedor="anthropic",
        llm_modelo="claude-sonnet-5-5",
        anthropic_key="",
    ))
    monkeypatch.setattr(
        llm.requests, "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not call network")),
    )

    try:
        llm.generar("test", registrar=False)
    except llm.LLMError as exc:
        assert "ANTHROPIC_API_KEY" in str(exc)
    else:
        raise AssertionError("expected LLMError for missing key")



def test_precios_anthropic_seleccionados_por_modelo_y_umbral_haiku():
    sonnet = llm.Respuesta(
        texto="", proveedor="anthropic", modelo="claude-sonnet-5-5",
        tokens_entrada=100, tokens_salida=5,
    )
    haiku = llm.Respuesta(
        texto="", proveedor="anthropic", modelo="claude-haiku-5-5",
        tokens_entrada=100, tokens_salida=5,
    )
    haiku_large_prompt = llm.Respuesta(
        texto="", proveedor="anthropic", modelo="claude-haiku-5-5",
        tokens_entrada=100_001, tokens_salida=5,
    )

    assert sonnet.costo_usd == 0.00025
    assert haiku.costo_usd == 0.0000125
    assert haiku_large_prompt.costo_usd == 0.050013


def test_anthropic_sin_precio_para_modelo_desconocido_falla_explicitamente():
    respuesta = llm.Respuesta(
        texto="", proveedor="anthropic", modelo="claude-no-catalogado",
        tokens_entrada=1, tokens_salida=1,
    )
    try:
        respuesta.costo_usd
    except llm.LLMError as exc:
        assert "No hay precio configurado" in str(exc)
    else:
        raise AssertionError("no debe asignar costo cero a un modelo sin precio")

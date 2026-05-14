"""Integration tests for the inference layer.

These tests require llama-swap and at least one model to be running.
Skip with: pytest -m "not integration"
"""

import os
import pytest
import httpx

LLAMA_SWAP_URL = os.environ.get("OSA_LLAMA_SWAP_URL", "http://127.0.0.1:8080")

pytestmark = pytest.mark.skipif(
    not os.environ.get("OSA_INTEGRATION_TESTS"),
    reason="Set OSA_INTEGRATION_TESTS=1 to run integration tests",
)


class TestInference:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = httpx.Client(base_url=LLAMA_SWAP_URL, timeout=60.0)
        yield
        self.client.close()

    def test_health_check(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200

    def test_llama3_completion(self):
        resp = self.client.post("/v1/chat/completions", json={
            "model": "llama3-8b",
            "messages": [
                {"role": "system", "content": "Reply in one word."},
                {"role": "user", "content": "What color is the sky?"},
            ],
            "max_tokens": 10,
            "temperature": 0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        content = data["choices"][0]["message"]["content"].lower()
        assert "blue" in content

    def test_model_switching(self):
        """Test that llama-swap can switch between models."""
        # First request to llama3
        resp1 = self.client.post("/v1/chat/completions", json={
            "model": "llama3-8b",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 5,
        })
        assert resp1.status_code == 200

        # Second request to qwen (triggers model swap on 16GB systems)
        resp2 = self.client.post("/v1/chat/completions", json={
            "model": "qwen-coder",
            "messages": [{"role": "user", "content": "print('hello')"}],
            "max_tokens": 5,
        })
        assert resp2.status_code == 200

    def test_streaming(self):
        with self.client.stream("POST", "/v1/chat/completions", json={
            "model": "llama3-8b",
            "messages": [{"role": "user", "content": "Count to 3"}],
            "max_tokens": 20,
            "stream": True,
        }) as resp:
            assert resp.status_code == 200
            chunks = list(resp.iter_lines())
            assert len(chunks) > 1

"""Tests for the IPC protocol encoding/decoding."""

from osa_core.common.ipc import Request, Response, encode_message, decode_message


class TestIPC:
    def test_request_encode_decode(self):
        req = Request(text="hello world", model_hint="code", stream=True)
        encoded = encode_message(req)
        decoded = decode_message(encoded, Request)
        assert decoded.text == "hello world"
        assert decoded.model_hint == "code"
        assert decoded.stream is True

    def test_response_encode_decode(self):
        resp = Response(request_id="abc-123", text="result", model="llama3", done=True)
        encoded = encode_message(resp)
        decoded = decode_message(encoded, Response)
        assert decoded.request_id == "abc-123"
        assert decoded.text == "result"
        assert decoded.model == "llama3"
        assert decoded.done is True

    def test_request_has_uuid(self):
        req = Request(text="test")
        assert req.request_id
        assert len(req.request_id) > 10

    def test_error_response(self):
        resp = Response(request_id="x", text="", error="connection failed", done=True)
        encoded = encode_message(resp)
        decoded = decode_message(encoded, Response)
        assert decoded.error == "connection failed"

    def test_newline_terminated(self):
        req = Request(text="test")
        encoded = encode_message(req)
        assert encoded.endswith(b"\n")

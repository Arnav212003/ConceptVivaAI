"""HMAC signing for worker -> sandbox requests. Dependency-free so the sandbox
container never needs the API's configuration or secrets."""
import hashlib
import hmac


def sign_sandbox_request(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()

"""
Feature 1: Hello AI — starter

Your job: implement the /api/chat endpoint so it calls the LLM and returns
a reply. Everything else (app setup, health check, UI serving) is already done
for you — the server will boot and /docs will work before you write a single line.

Run this with:
    uvicorn main:app --reload --port 8000

Steps:
  1. Look for the TODO comments below — there are two.
  2. Fill in the ChatRequest model (Step 1).
  3. Implement the chat() function body (Step 2).
  4. Test your changes at http://localhost:8000/docs.
"""
import base64
import json
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from data.CustomerContext import CustomerContext
from data.AuthContext import AuthContext
from tools.customer.customer_client import fetch_customer_profile
from shared.llm_client import call_llm
from shared.provider_check import check_provider_config
from shared.session_store import create_session, get_session, list_sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks before the server begins accepting requests."""
    await check_provider_config()
    yield


app = FastAPI(
    title="Personal Finance Coach",
    description="Domain-Specific AI Assistant — AI Engineering Bootcamp, BlockseBlock",
    version="1.0.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    """The body expected by POST /api/chat."""

    # TODO (Feature 1, Step 1): Add a field called `message` of type str.
    # This is what the user sends to the assistant.
    # Hint: the syntax is:  field_name: field_type
    message: str


class ChatResponse(BaseModel):
    """The body returned by POST /api/chat."""

    response: str


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode and validate the payload section of a JWT.

    This is a lightweight validation step for Keycloak access tokens without
    requiring a separate JWT library. It checks the token structure, expiry,
    and the most important claim fields used by the auth context.
    """
    if not token or not token.strip():
        raise ValueError("Missing bearer token")

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWT")

    payload_segment = parts[1]
    padded = payload_segment + "=" * (-len(payload_segment) % 4)

    try:
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
        raise ValueError("JWT payload is not valid UTF-8 JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("JWT payload must be an object")

    now = int(time.time())
    exp = payload.get("exp")
    if exp is not None and now >= int(exp):
        raise ValueError("JWT has expired")

    nbf = payload.get("nbf")
    if nbf is not None and now < int(nbf):
        raise ValueError("JWT is not valid yet")

    if not payload.get("sub"):
        raise ValueError("JWT is missing subject claim")

    aud = payload.get("aud")
    aud_values = aud if isinstance(aud, list) else [aud] if aud else []
    if aud_values and "fintech-ai-assistant" not in aud_values:
        raise ValueError("JWT audience does not match this client")

    return payload


def validate_access_token(token: str) -> dict[str, Any]:
    """Return the decoded JWT claims or raise a 401-style error."""
    try:
        return _decode_jwt_payload(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def build_customer_context_from_token(token: str, claims: dict[str, Any] | None = None) -> CustomerContext:
    """Construct the CustomerContext used by the app from the JWT claims."""
    jwt_claims = claims or validate_access_token(token)

    customer_id = jwt_claims.get("sub")
    if not customer_id:
        raise ValueError("JWT is missing sub claim")

    realm_roles = jwt_claims.get("realm_access", {}).get("roles", []) if isinstance(jwt_claims.get("realm_access"), dict) else []
    resource_access = jwt_claims.get("resource_access", {})
    resource_roles: list[str] = []
    if isinstance(resource_access, dict):
        for client_roles in resource_access.values():
            if isinstance(client_roles, dict):
                resource_roles.extend(client_roles.get("roles", []))

    roles = [str(role) for role in list(realm_roles) + list(resource_roles)]

    permissions = jwt_claims.get("permissions")
    if isinstance(permissions, str):
        permissions = permissions.split()
    elif permissions is None:
        permissions = []
    permissions = [str(permission) for permission in permissions]

    session_id = jwt_claims.get("session_state") or jwt_claims.get("sid") or "unknown-session"

    return CustomerContext(
        customer_id=str(customer_id),
        roles=roles,
        permissions=permissions,
        session_id=str(session_id),
        access_token=token,
        default_account_id=jwt_claims.get("default_account_id"),
    )


@app.post("/api/customer/session")
async def create_customer_session(payload: dict) -> dict:
    """Accept the token object from the client, validate it and return an AuthContext.

    Expected payload is the token JSON returned by Keycloak (contains at least
    `access_token` and optionally `refresh_token` and `refresh_expires_in`).
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid token payload")

    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access_token in payload")

    claims = validate_access_token(access_token)

    customer_id = claims.get("sub")
    realm_roles = claims.get("realm_access", {}).get("roles", []) if isinstance(claims.get("realm_access"), dict) else []
    resource_access = claims.get("resource_access", {})
    resource_roles: list[str] = []
    if isinstance(resource_access, dict):
        for client_roles in resource_access.values():
            if isinstance(client_roles, dict):
                resource_roles.extend(client_roles.get("roles", []))

    roles = [str(role) for role in list(realm_roles) + list(resource_roles)]

    permissions = claims.get("permissions")
    if isinstance(permissions, str):
        permissions = permissions.split()
    elif permissions is None:
        permissions = []
    permissions = [str(p) for p in permissions]

    session_id = claims.get("session_state") or claims.get("sid") or "unknown-session"

    # Compute refresh token expiry ms if provided by the client
    refresh_expires_in = 0
    if payload.get("refresh_expires_in"):
        try:
            refresh_expires_in = int(payload.get("refresh_expires_in")) * 1000
        except Exception:
            refresh_expires_in = 0

    import time
    refresh_token_expiry = int(time.time() * 1000) + (refresh_expires_in or 0)

    auth_ctx = AuthContext(
        customer_id=str(customer_id or ""),
        roles=roles,
        permissions=permissions,
        session_id=str(session_id),
        access_token=access_token,
        refresh_token=str(payload.get("refresh_token") or ""),
        refresh_token_expiry=refresh_token_expiry,
    )

    # Return a JSON representation the client can store locally.
    resp = {
        "customer_id": auth_ctx.customer_id,
        "roles": auth_ctx.roles,
        "permissions": auth_ctx.permissions,
        "session_id": auth_ctx.session_id,
        "access_token": auth_ctx.access_token,
        "refresh_token": auth_ctx.refresh_token,
        "refresh_token_expiry": auth_ctx.refresh_token_expiry,
    }

    # Try to fetch the richer customer profile from the Java backend so the
    # client can store CustomerContext in sessionStorage. Fail silently
    # (returning auth only) if the backend call fails.
    try:
        profile = await fetch_customer_profile(auth_ctx.customer_id, auth_ctx.access_token)
        # Map profile dataclass to JSON-serializable dict
        accounts = []
        for a in profile.AccountSummary or []:
            accounts.append({
                "account_id": a.account_id,
                "account_type": a.account_type,
                "is_default": a.is_default,
            })

        beneficiaries = []
        for b in profile.BeneficiaryResponse or []:
            beneficiaries.append({
                "beneficiary_id": b.beneficiary_id,
                "name": b.name,
                "account_id": b.account_id,
            })

        customer_ctx = {
            "customer_id": profile.customer_id,
            "customer_name": profile.customer_name,
            "default_account_id": profile.default_account_id,
            "accounts": accounts,
            "beneficiaries": beneficiaries,
        }
        resp["customer_context"] = customer_ctx
    except Exception:
        # Ignore errors here; the client will still have AuthContext and can
        # fetch profile later if needed.
        pass

    return resp


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """Send a message to the AI assistant and get a reply."""
    # The frontend should send the session id from the AuthContext instead
    # of an access token. If it's missing, return 401 to force login.
    session_id = request.headers.get("x-session-id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing session id. Please login.")
    request.state.session_id = session_id

    messages = [
        {
            "role": "system",
            "content": (
                "You are a personal banking assistant. "
                "You help the authenticated customer understand their own financial information. "
                f"session_id={request.state.session_id}. "
                "Use that context to personalize responses but never invent data. "
                "If the customer asks for data they do not have access to, say so clearly. "
                "Only use tools when needed and prefer factual responses based on the provided customer context."
            )
        },
        {"role": "user", "content": payload.message},
    ]

    result = await call_llm(messages)
    return ChatResponse(response=result.content or "")


@app.get("/api/health")
async def health():
    """Quick liveness check — returns 200 OK if the server is running."""
    return {"status": "ok"}


@app.get("/api/provider-info")
async def provider_info():
    """Return which LLM and voice provider are currently active (no API keys)."""
    from shared.config import settings

    voice_name = settings.effective_voice_provider().lower().strip()
    llm_name = settings.llm_provider.lower().strip()

    model_map = {
        "openai": settings.openai_model,
        "anthropic": settings.anthropic_model,
        "cohere": settings.cohere_model,
        "ollama": settings.ollama_model,
        "groq": settings.groq_model,
        "custom": settings.custom_model,
    }

    return {
        "llm_provider": llm_name,
        "llm_model": model_map.get(llm_name, "unknown"),
        "voice_provider": voice_name if voice_name != llm_name else None,
        "voice_model": model_map.get(voice_name) if voice_name != llm_name else None,
    }

@app.post("/auth/keycloak/callback")
async def keycloak_callback(request: Request):
    payload = await request.json()
    code = payload.get("code")
    code_verifier = payload.get("code_verifier")
    redirect_uri = payload.get("redirect_uri")

    print("DEBUG KEYCLOAK CALLBACK PAYLOAD:", payload)

    if not code or not code_verifier or not redirect_uri:
        raise HTTPException(
            status_code=400,
            detail="Missing required Keycloak callback fields: code, code_verifier, redirect_uri",
        )

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "http://localhost:9090/realms/fintech-realm/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "fintech-ai-assistant",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            timeout=20,
        )

    print("DEBUG KEYCLOAK TOKEN STATUS:", token_resp.status_code)
    print("DEBUG KEYCLOAK TOKEN BODY:", token_resp.text)

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Keycloak token exchange failed",
                "status": token_resp.status_code,
                "response": token_resp.text,
            },
        )

    token_data = token_resp.json()
    print("DEBUG KEYCLOAK TOKEN JSON:", token_data)
    print("DEBUG KEYCLOAK TOKEN KEYS:", list(token_data.keys()) if isinstance(token_data, dict) else type(token_data).__name__)
    return JSONResponse({"ok": True, "token": token_data})

@app.post("/api/sessions", tags=["F3 · AI Memory"])
async def new_session(tenant_id: str = Depends(get_tenant_id)) -> dict:
    return {"session_id": create_session(tenant_id=tenant_id)}


@app.get("/api/sessions", response_model=list[SessionSummary], tags=["F3 · AI Memory"])
async def sessions_list() -> list[SessionSummary]:
    summaries = []
    for s in list_sessions():
        first_user_msg = next((m.content for m in s.messages if m.role == "user"), "")
        title = (first_user_msg[:60] + "…") if len(first_user_msg) > 60 else (first_user_msg or "New conversation")
        summaries.append(SessionSummary(id=s.id, created_at=s.created_at.isoformat(), message_count=len(s.messages), title=title))
    return summaries

@app.post("/api/sessions/{session_id}/chat", response_model=StructuredResponse, tags=["F3 · AI Memory"])
async def session_chat(session_id: str, request: ChatRequest, tenant_id: str = Depends(get_tenant_id)) -> StructuredResponse:
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    messages: list[dict] = [{"role": "system", "content": _STRUCTURED_SYSTEM_PROMPT}]
    for msg in session.messages[-CONTEXT_WINDOW_SIZE:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})
    add_message(session_id, "user", request.message)
    result = await call_llm(messages, temperature=0.3, response_format={"type": "json_object"})
    structured = _parse_structured(result.content or "")
    add_message(session_id, "assistant", structured.answer)
    return structured


@app.get("/api/sessions/{session_id}/history", response_model=list[Message], tags=["F3 · AI Memory"])
async def session_history(session_id: str, tenant_id: str = Depends(get_tenant_id)) -> list[Message]:
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session.messages

_ui_path = Path(__file__).resolve().parents[0] / "ui"
print(f"UI path: {_ui_path}")
if _ui_path.exists():
    app.mount("/", StaticFiles(directory=str(_ui_path), html=True), name="ui")
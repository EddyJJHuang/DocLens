from fastapi.testclient import TestClient

from app.api.schemas import DocumentResponse
from app.main import app
from app.session_store import session_store


SESSION_A = {"X-DocLens-Session": "test-session-alpha"}
SESSION_B = {"X-DocLens-Session": "test-session-bravo"}


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_upload_rejects_unsupported_file_type() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            headers=SESSION_A,
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_documents_are_session_scoped() -> None:
    with TestClient(app) as client:
        session = session_store.get_or_create("test-session-alpha")
        session.documents.append(DocumentResponse(id="doc-1", filename="alpha.md", status="completed"))

        alpha_docs = client.get("/api/documents", headers=SESSION_A)
        bravo_docs = client.get("/api/documents", headers=SESSION_B)

    assert alpha_docs.status_code == 200
    assert bravo_docs.status_code == 200
    assert alpha_docs.json() == [{"id": "doc-1", "filename": "alpha.md", "status": "completed"}]
    assert bravo_docs.json() == []


def test_session_end_deletes_runtime_state() -> None:
    with TestClient(app) as client:
        session = session_store.get_or_create("test-session-alpha")
        session.documents.append(DocumentResponse(id="doc-1", filename="alpha.md", status="completed"))

        end_response = client.post("/api/session/end", headers=SESSION_A)
        docs_after = client.get("/api/documents", headers=SESSION_A)

    assert end_response.status_code == 200
    assert end_response.json() == {"status": "deleted"}
    assert docs_after.status_code == 200
    assert docs_after.json() == []

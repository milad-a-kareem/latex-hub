"""Test fixtures.

The Firebase Admin SDK is mocked at the ``firebase_admin`` package boundary
so importing the FastAPI app under test never reaches network or filesystem
credentials. Each test that touches Firestore patches ``app.firebase.db``
to return a small in-memory fake.
"""

from __future__ import annotations

import os
import sys
import types
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_STORAGE_BUCKET", "test-bucket")


# Stub firebase_admin before any application import so initialize_app does not
# attempt to load real credentials. We replace the whole package surface that
# app.firebase relies on.
def _install_fake_firebase_admin() -> None:
    if "firebase_admin" in sys.modules and not isinstance(
        sys.modules["firebase_admin"], types.ModuleType
    ):
        return
    fake = types.ModuleType("firebase_admin")
    fake.initialize_app = MagicMock(return_value=MagicMock(name="FirebaseApp"))  # type: ignore[attr-defined]
    fake.App = MagicMock  # type: ignore[attr-defined]

    fake_creds = types.ModuleType("firebase_admin.credentials")
    fake_creds.Certificate = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
    fake_creds.ApplicationDefault = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]

    fake_auth = types.ModuleType("firebase_admin.auth")
    fake_auth.verify_id_token = MagicMock(return_value={"uid": "test-uid"})  # type: ignore[attr-defined]

    fake_firestore = types.ModuleType("firebase_admin.firestore")
    fake_firestore.client = MagicMock(return_value=MagicMock(name="FirestoreClient"))  # type: ignore[attr-defined]

    fake_storage = types.ModuleType("firebase_admin.storage")
    fake_storage.bucket = MagicMock(return_value=MagicMock(name="Bucket"))  # type: ignore[attr-defined]

    sys.modules["firebase_admin"] = fake
    sys.modules["firebase_admin.credentials"] = fake_creds
    sys.modules["firebase_admin.auth"] = fake_auth
    sys.modules["firebase_admin.firestore"] = fake_firestore
    sys.modules["firebase_admin.storage"] = fake_storage


_install_fake_firebase_admin()

# Imported after the stub install because google.cloud.firestore lazily
# touches firebase_admin via the same site-packages tree.
from google.cloud.firestore import DELETE_FIELD, SERVER_TIMESTAMP  # noqa: E402


class FakeDocRef:
    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str) -> None:
        self._store = store
        self._id = doc_id

    @property
    def id(self) -> str:
        return self._id

    def get(self) -> FakeSnap:
        return FakeSnap(self._id, self._store.get(self._id))

    def set(self, data: dict[str, Any]) -> None:
        self._store[self._id] = _resolve(data)

    def update(self, data: dict[str, Any]) -> None:
        current = self._store.setdefault(self._id, {})
        for key, value in _resolve(data).items():
            if "." in key:
                top, sub = key.split(".", 1)
                nested = current.setdefault(top, {})
                if value is DELETE_FIELD:
                    nested.pop(sub, None)
                else:
                    nested[sub] = value
            elif value is DELETE_FIELD:
                current.pop(key, None)
            else:
                current[key] = value

    def delete(self) -> None:
        self._store.pop(self._id, None)


class FakeSnap:
    def __init__(self, doc_id: str, data: dict[str, Any] | None) -> None:
        self._id = doc_id
        self._data = data

    @property
    def id(self) -> str:
        return self._id

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return None if self._data is None else dict(self._data)


class FakeQuery:
    def __init__(self, docs: list[FakeSnap]) -> None:
        self._docs = docs

    def where(self, *args: Any, **kwargs: Any) -> FakeQuery:
        field = args[0] if args else kwargs.get("field_path")
        value = args[2] if len(args) >= 3 else kwargs.get("value")
        filtered = [d for d in self._docs if (d.to_dict() or {}).get(field) == value]
        return FakeQuery(filtered)

    def order_by(self, *args: Any, **kwargs: Any) -> FakeQuery:
        return self

    def stream(self) -> list[FakeSnap]:
        return list(self._docs)


class FakeCollection:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store
        self._counter = 0

    def document(self, doc_id: str | None = None) -> FakeDocRef:
        if doc_id is None:
            self._counter += 1
            doc_id = f"doc-{self._counter}"
        return FakeDocRef(self._store, doc_id)

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        docs = [FakeSnap(k, v) for k, v in self._store.items()]
        return FakeQuery(docs).where(field, op, value)


class FakeFirestore:
    def __init__(self) -> None:
        self._stores: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._stores.setdefault(name, {}))

    def get_store(self, name: str) -> dict[str, dict[str, Any]]:
        return self._stores.setdefault(name, {})


def _resolve(payload: dict[str, Any]) -> dict[str, Any]:
    """Replace Firestore sentinels with concrete values so the fake behaves
    deterministically."""
    out: dict[str, Any] = {}
    now = datetime.now(UTC)
    for key, value in payload.items():
        if value is SERVER_TIMESTAMP:
            out[key] = now
        else:
            out[key] = value
    return out


from app import auth as _auth_mod  # noqa: E402
from app import firebase as _firebase_mod  # noqa: E402
from app.main import app as _app  # noqa: E402
from app.routers import compile as _compile_router  # noqa: E402
from app.services import projects as _projects_svc  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeFirestore]:
    fake = FakeFirestore()
    monkeypatch.setattr(_firebase_mod, "db", lambda: fake)
    monkeypatch.setattr(_projects_svc, "db", lambda: fake)
    monkeypatch.setattr(_compile_router, "db", lambda: fake)
    yield fake


@pytest.fixture
def client(fake_db: FakeFirestore) -> Iterator[Any]:
    _app.dependency_overrides[_auth_mod.get_current_user] = lambda: _auth_mod.CurrentUser(
        uid="test-uid", email="t@example.com"
    )
    try:
        with TestClient(_app) as c:
            yield c
    finally:
        _app.dependency_overrides.pop(_auth_mod.get_current_user, None)

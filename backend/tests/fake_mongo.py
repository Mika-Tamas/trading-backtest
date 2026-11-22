"""Thread-safe in-memory PyMongo double for offline unit testing."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import threading
from typing import Any

from pymongo import DESCENDING, ReturnDocument, UpdateOne
from pymongo.errors import DuplicateKeyError, OperationFailure


def _normalize_comparable(value: Any) -> Any:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _matches_filter(doc: dict[str, Any], flt: dict[str, Any]) -> bool:
    for key, condition in flt.items():
        if isinstance(condition, dict):
            has_key = key in doc
            val = doc.get(key)
            for op, target in condition.items():
                if op == "$gte":
                    if not has_key or val is None or _normalize_comparable(val) < _normalize_comparable(target):
                        return False
                elif op == "$lte":
                    if not has_key or val is None or _normalize_comparable(val) > _normalize_comparable(target):
                        return False
                elif op == "$gt":
                    if not has_key or val is None or _normalize_comparable(val) <= _normalize_comparable(target):
                        return False
                elif op == "$lt":
                    if not has_key or val is None or _normalize_comparable(val) >= _normalize_comparable(target):
                        return False
                elif op == "$in":
                    if not has_key or val not in target:
                        return False
                elif op == "$exists":
                    if has_key != bool(target):
                        return False
                else:
                    raise NotImplementedError(f"Unsupported filter operator: {op}")
        else:
            if key not in doc or _normalize_comparable(doc[key]) != _normalize_comparable(condition):
                return False
    return True


def _apply_projection(doc: dict[str, Any], projection: dict[str, int] | None) -> dict[str, Any]:
    copied = copy.deepcopy(doc)
    if not projection:
        return copied

    include_fields = {k for k, v in projection.items() if v and k != "_id"}
    exclude_fields = {k for k, v in projection.items() if not v}

    if include_fields:
        result = {k: copied[k] for k in include_fields if k in copied}
        if projection.get("_id", 1) and "_id" in copied:
            result["_id"] = copied["_id"]
        return result

    for k in exclude_fields:
        copied.pop(k, None)
    return copied


def _apply_update(doc: dict[str, Any], update: dict[str, Any]) -> None:
    if "$set" in update:
        for k, v in update["$set"].items():
            doc[k] = copy.deepcopy(v)
    if "$min" in update:
        for k, v in update["$min"].items():
            if k not in doc or doc[k] is None or _normalize_comparable(v) < _normalize_comparable(doc[k]):
                doc[k] = copy.deepcopy(v)
    if "$max" in update:
        for k, v in update["$max"].items():
            if k not in doc or doc[k] is None or _normalize_comparable(v) > _normalize_comparable(doc[k]):
                doc[k] = copy.deepcopy(v)


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]):
        self._docs = docs

    def sort(self, key_or_list: str | list[tuple[str, int]], direction: int | None = None) -> "FakeCursor":
        if isinstance(key_or_list, str):
            specs = [(key_or_list, direction if direction is not None else 1)]
        else:
            specs = list(key_or_list)

        result = list(self._docs)
        for field, order in reversed(specs):
            reverse = order == DESCENDING
            result.sort(
                key=lambda d: (
                    d.get(field) is None,
                    _normalize_comparable(d.get(field)) if d.get(field) is not None else "",
                ),
                reverse=reverse,
            )
        return FakeCursor(result)

    def limit(self, count: int) -> "FakeCursor":
        if count <= 0:
            return FakeCursor(list(self._docs))
        return FakeCursor(self._docs[:count])

    def __iter__(self):
        return iter(self._docs)


class FakeCollection:
    def __init__(self, name: str):
        self.name = name
        self._lock = threading.RLock()
        self._docs: list[dict[str, Any]] = []
        self._next_id = 1
        self._indexes: dict[str, dict[str, Any]] = {
            "_id_": {"key": [("_id", 1)], "unique": True}
        }
        self.update_many_calls = 0

    def create_index(
        self,
        keys: list[tuple[str, int]],
        unique: bool = False,
        expireAfterSeconds: int | None = None,
        name: str | None = None,
    ) -> str:
        with self._lock:
            index_name = name or "_".join(f"{k}_{d}" for k, d in keys)
            spec: dict[str, Any] = {"key": list(keys)}
            if unique:
                spec["unique"] = True
            if expireAfterSeconds is not None:
                spec["expireAfterSeconds"] = expireAfterSeconds

            if index_name in self._indexes:
                if self._indexes[index_name] != spec:
                    raise OperationFailure(
                        f"Index already exists with different options: {index_name}",
                        code=85,
                    )
                return index_name

            self._indexes[index_name] = spec
            return index_name

    def index_information(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._indexes)

    def _check_unique_constraints(self, candidate: dict[str, Any], exclude_idx: int | None = None) -> None:
        for idx_spec in self._indexes.values():
            if not idx_spec.get("unique"):
                continue
            key_fields = [k for k, _ in idx_spec["key"]]
            cand_tuple = tuple(candidate.get(k) for k in key_fields)
            for i, existing in enumerate(self._docs):
                if i == exclude_idx:
                    continue
                if tuple(existing.get(k) for k in key_fields) == cand_tuple:
                    raise DuplicateKeyError(f"Duplicate key on {key_fields}: {cand_tuple}")

    def insert_one(self, document: dict[str, Any]) -> None:
        with self._lock:
            doc = copy.deepcopy(document)
            if "_id" not in doc:
                doc["_id"] = self._next_id
                self._next_id += 1
            self._check_unique_constraints(doc)
            self._docs.append(doc)

    def find_one(
        self,
        flt: dict[str, Any] | None = None,
        projection: dict[str, int] | None = None,
    ) -> dict[str, Any] | None:
        flt = flt or {}
        with self._lock:
            for doc in self._docs:
                if _matches_filter(doc, flt):
                    return _apply_projection(doc, projection)
            return None

    def find(
        self,
        flt: dict[str, Any] | None = None,
        projection: dict[str, int] | None = None,
    ) -> FakeCursor:
        flt = flt or {}
        with self._lock:
            matched = [
                _apply_projection(doc, projection)
                for doc in self._docs
                if _matches_filter(doc, flt)
            ]
            return FakeCursor(matched)

    def _upsert_or_update_one_locked(
        self,
        flt: dict[str, Any],
        update: dict[str, Any],
        upsert: bool,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        for idx, doc in enumerate(self._docs):
            if _matches_filter(doc, flt):
                before = copy.deepcopy(doc)
                candidate = copy.deepcopy(doc)
                _apply_update(candidate, update)
                self._check_unique_constraints(candidate, exclude_idx=idx)
                self._docs[idx] = candidate
                return before, copy.deepcopy(candidate)

        if not upsert:
            return None, None

        new_doc: dict[str, Any] = {}
        for k, v in flt.items():
            if not isinstance(v, dict):
                new_doc[k] = copy.deepcopy(v)
        _apply_update(new_doc, update)
        if "_id" not in new_doc:
            new_doc["_id"] = self._next_id
            self._next_id += 1
        self._check_unique_constraints(new_doc)
        self._docs.append(new_doc)
        return None, copy.deepcopy(new_doc)

    def update_one(
        self,
        flt: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> None:
        with self._lock:
            self._upsert_or_update_one_locked(flt, update, upsert=upsert)

    def find_one_and_update(
        self,
        flt: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
        return_document: bool = ReturnDocument.BEFORE,
    ) -> dict[str, Any] | None:
        with self._lock:
            before, after = self._upsert_or_update_one_locked(flt, update, upsert=upsert)
            return after if return_document == ReturnDocument.AFTER else before

    def update_many(self, flt: dict[str, Any], update: dict[str, Any]) -> int:
        with self._lock:
            self.update_many_calls += 1
            modified = 0
            for idx, doc in enumerate(self._docs):
                if _matches_filter(doc, flt):
                    candidate = copy.deepcopy(doc)
                    _apply_update(candidate, update)
                    self._check_unique_constraints(candidate, exclude_idx=idx)
                    self._docs[idx] = candidate
                    modified += 1
            return modified

    def bulk_write(self, requests: list[Any], ordered: bool = True) -> None:
        if not requests:
            raise ValueError("bulk_write requests must not be empty")
        with self._lock:
            for req in requests:
                if isinstance(req, UpdateOne):
                    self._upsert_or_update_one_locked(
                        req._filter,
                        req._doc,
                        upsert=bool(req._upsert),
                    )
                else:
                    raise NotImplementedError(f"Unsupported bulk_write op: {type(req)}")

    def delete_one(self, flt: dict[str, Any]) -> int:
        with self._lock:
            for idx, doc in enumerate(self._docs):
                if _matches_filter(doc, flt):
                    self._docs.pop(idx)
                    return 1
            return 0

    def delete_many(self, flt: dict[str, Any]) -> int:
        with self._lock:
            before = len(self._docs)
            self._docs = [doc for doc in self._docs if not _matches_filter(doc, flt)]
            return before - len(self._docs)

    def count_documents(self, flt: dict[str, Any] | None = None) -> int:
        flt = flt or {}
        with self._lock:
            return sum(1 for doc in self._docs if _matches_filter(doc, flt))


class FakeDatabase:
    def __init__(self, name: str = "test_trading_backtest"):
        self.name = name
        self._lock = threading.RLock()
        self._collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        with self._lock:
            if name not in self._collections:
                self._collections[name] = FakeCollection(name)
            return self._collections[name]

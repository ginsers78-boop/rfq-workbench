import json
import re
import sqlite3
import uuid

from pydantic import BaseModel, ConfigDict, Field

from .extraction import ExtractionError


class SupplierInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str | None = None
    revision: int = Field(default=0, ge=0)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=254)
    categories: list[str] = Field(min_length=1, max_length=100)
    active: bool = True


def list_suppliers(store):
    with store.connect() as connection:
        return [json.loads(row[0]) for row in connection.execute("SELECT payload FROM suppliers ORDER BY lower(email)").fetchall()]


def save_supplier(store, payload):
    try:
        supplier = SupplierInput.model_validate(payload)
    except ValueError:
        raise ExtractionError("Supplier data is invalid. Enter a name, email and at least one category.") from None
    supplier.name = supplier.name.strip()
    supplier.email = supplier.email.strip()
    if not supplier.name or any(ord(char) < 32 for char in supplier.name):
        raise ExtractionError("Enter a valid supplier name without control characters.")
    # A single ASCII business mailbox, never a display-name list or header content.
    if not re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", supplier.email):
        raise ExtractionError("Enter one ASCII business email address, without names, commas or line breaks.")
    if len(set(supplier.categories)) != len(supplier.categories) or any(category not in store.categories or category == "Unclassified" for category in supplier.categories):
        raise ExtractionError("Choose distinct configured supplier categories; Unclassified cannot receive RFQs.")
    identifier = supplier.id or str(uuid.uuid4())
    record = supplier.model_dump() | {"id": identifier, "revision": supplier.revision + 1}
    try:
        with store.connect() as connection:
            if supplier.id:
                changed = connection.execute("UPDATE suppliers SET revision = ?, payload = ?, email = ? WHERE id = ? AND revision = ?", (record["revision"], json.dumps(record), supplier.email, identifier, supplier.revision)).rowcount
                if changed != 1:
                    raise ExtractionError("The supplier changed or was not found. Refresh the supplier list before saving.")
            else:
                if supplier.revision != 0:
                    raise ExtractionError("New suppliers must start at revision zero.")
                connection.execute("INSERT INTO suppliers VALUES (?, ?, ?, ?)", (identifier, 1, json.dumps(record), supplier.email))
    except sqlite3.IntegrityError:
        raise ExtractionError("That supplier email already exists. Edit its existing permanent record instead.") from None
    return record

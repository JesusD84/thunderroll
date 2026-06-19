"""Seed the real client model-equivalence table (manufacturer -> internal).

This is the authoritative mapping the client provided (separate from the demo
placeholders in ``seed.py``). It is idempotent — it upserts by manufacturer
model — so it is safe to run repeatedly and against an already-populated
production database:

    python -m app.database.seed_equivalences

Notes on the source data:
- ``AK-160`` is stored without the stray space the client wrote ("AK- 160") so
  it matches the real supplier label.
- The keys for ``xiaodou`` and ``diaoyu`` use the spelling the suppliers actually
  ship in the sample files (the client wrote them "XIADOU"/"DIAOYOU"); we trust
  the samples since that is the data received directly from the supplier.
- Still pending client confirmation (left out until answered):
  - ``TY-530`` (mapping) vs ``TY-D530`` (sample): are they the same product?
  - ``TY-TJ571`` and ``ZHAIBANG`` (seen in samples): do they have an internal
    name, or are they used as-is?
  - ``MC-316`` / ``MC-118`` / ``Q-02`` (in the mapping but not yet seen in any
    sample): waiting for a supplier sample to test against.
"""

from app.database.database import SessionLocal
from app.services.model_equivalence_service import upsert_equivalence

# Manufacturer model (as the supplier labels it in the sample files) -> client's
# internal model. Keys follow the supplier's real spelling so imports auto-resolve.
CLIENT_MODEL_EQUIVALENCES: dict[str, str] = {
    "xiaodou": "TR 571 PLUS",
    "X3": "571",
    "diaoyu": "TR 571 PRO",
    "AK-160": "TR-TON",
}


def seed_client_model_equivalences(db=None) -> int:
    """Upsert the client mapping. Returns the number of equivalences processed."""
    own_session = db is None
    db = db or SessionLocal()
    try:
        for manufacturer_model, internal_model in CLIENT_MODEL_EQUIVALENCES.items():
            upsert_equivalence(db, manufacturer_model, internal_model)
        return len(CLIENT_MODEL_EQUIVALENCES)
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    count = seed_client_model_equivalences()
    print(f"✓ Seeded {count} client model equivalences")

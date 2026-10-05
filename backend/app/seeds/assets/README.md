# Demo Cephalogram — Licensed Sample Image

The Ceph demo seeder (`app/seeds/demo_ceph.py`) uses a real lateral cephalogram for the demo if one
is present here; otherwise it falls back to a clearly-labeled synthetic placeholder.

## To use a licensed/sample ceph image
1. Place the image at one of:
   - `sample_ceph.png`  (preferred)
   - `sample_ceph.jpg` / `sample_ceph.jpeg`
2. Record its license + attribution in `SAMPLE_CEPH_LICENSE.txt` in this folder.
3. Re-run the demo seed (startup/reseed, or
   `docker exec orthoflow-backend-1 python -c "import asyncio; from app.seeds.demo_ceph import seed_ceph_demo; asyncio.run(seed_ceph_demo())"`).
   Note: the seeder is idempotent — if a demo ceph is already seeded it skips. To re-seed with the new
   image, remove the existing demo ceph image/tracings for Priscilla first (or bump the marker).

## Approved sources (must confirm license allows commercial demo use + attribution)
- **Aariz dataset** (github.com/manwaarkhd/aariz-cephalometric-dataset) — 1,000 LCRs, published in
  Nature Scientific Data 2025, open-access (CC-BY). Requires attribution; access may require the
  dataset's request step.
- **AAOF Legacy Collection** (aaoflegacycollection.org) — large ceph archive with its own usage terms.
- Any lateral cephalogram the practice/company owns the rights to use in marketing/demos.

Do NOT drop in an image without confirmed rights — these are clinical radiographs with licensing and
(for real patients) privacy obligations. Use de-identified, properly-licensed images only.

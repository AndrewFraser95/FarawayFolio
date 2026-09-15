# Where the money actually comes from

## Status as of 2026-09-15 (morning after overnight run)
**Three packs are live and selling on Gumroad**, all linked from the site's shop cards:
- Volume One: Quiet Luxury (6 images, £8) — https://farawayfolio.gumroad.com/l/volume-1, custom landing page
- Volume Two: Coastal Village (13 images, £10) — https://farawayfolio.gumroad.com/l/haoif
- Volume Three: Alpine Retreat (13 images, £10) — https://farawayfolio.gumroad.com/l/ysgrf

**Volumes Four (Desert Kasbah) and Five (Quiet Garden) are incomplete** — the overnight batch run (`run_all_volumes.sh` via a one-shot launchd job) crashed on both: Volume Four got 1/13 images (`riad-courtyard`) before a ComfyUI network timeout killed the process on `desert-dunes`; Volume Five got 0/13 (crashed on the first image, `zen-garden`). Root cause: the Windows ComfyUI machine went unreachable (likely went to sleep) partway through the run, and `generate_product_pack.py` doesn't catch the resulting `RuntimeError`, so the whole process died instead of skipping ahead. The pipeline is resumable (skips finished images, reuses orphaned raw PNGs) — resuming just needs ComfyUI reachable again, then re-running `generate_product_pack.py --volume content-pipeline/products/volume-{4,5}.json` and publishing via `publish_volume_to_gumroad.py`.

A duplicate, broken "Volume Two" listing (created by a pre-fix Gumroad publish attempt that failed on a non-square-thumbnail error but still partially created the product) was found and deleted this morning — only the correct Volume Two listing above remains.

**Upscale technique evaluated and rejected**: tested a hires-fix second pass (`LatentUpscaleBy` + low-denoise second `KSampler`) against the single-pass HQ workflow already in use. Improvement was marginal (slightly more fine texture) for a large time cost (~20-30 min/image vs ~5-8 min). Kept the single-pass HQ workflow as the standard.

- Site's shop cards now link to the three real live packs (previously fictional placeholder products with `#` hrefs) — done 2026-09-15.
- No affiliate program applied to yet.

## The plan, in priority order

### 1. Printable wall-art / wallpaper packs — LIVE, 3 of 5 volumes published
Fastest realistic path: sell the aesthetic itself, not a physical product. No approval process, no waiting on affiliate networks, sells directly to whatever audience the IG/Facebook posts bring in.

- **Products**: Volumes One–Three live now (see above). Four and Five pending completion (blocked on ComfyUI availability).
- **Platform**: Gumroad.
- **Price**: £8 (Volume One, smaller pack) / £10 (Volumes Two+, 13-image packs).
- **Path to £2k**: at ~£9 net/sale average after Gumroad's fee, that's ~220 sales across all volumes. Realistic only with actual traffic — these products' job is to convert whatever audience the content builds, not to be the sole growth engine.
- **Next**: finish Volumes Four/Five once ComfyUI is reachable; consider adding them to the site once there's room (currently 3 cards, matching 3 live volumes).

### 2. Amazon Associates
Apply once the site has some real traffic (a few weeks of consistent posting). Needs 3 qualifying sales within 180 days to stay approved, so this only starts paying once there's an actual audience clicking through — not a week-one lever.

### 3. LTK / ShopMy
Usually gate on engagement/follower thresholds for brand-new accounts. Apply once IG has a consistent posting history to point to.

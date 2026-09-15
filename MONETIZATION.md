# Where the money actually comes from

## Status as of 2026-09-15 (all 5 volumes live)
**All five packs are live and selling on Gumroad.** Volumes One-Three are linked from the site's shop cards; Four and Five are live on the Gumroad storefront but not yet added to the homepage (only 3 card slots exist there currently):
- Volume One: Quiet Luxury (6 images, £8) — https://farawayfolio.gumroad.com/l/volume-1, custom landing page
- Volume Two: Coastal Village (13 images, £10) — https://farawayfolio.gumroad.com/l/haoif
- Volume Three: Alpine Retreat (13 images, £10) — https://farawayfolio.gumroad.com/l/ysgrf
- Volume Four: Desert Kasbah (13 images, £10) — https://farawayfolio.gumroad.com/l/hqylp
- Volume Five: Quiet Garden (13 images, £10) — https://farawayfolio.gumroad.com/l/lcfand

**Resolved this morning**: the overnight batch run crashed twice on ComfyUI network timeouts (Windows machine went unreachable), leaving Four at 1/13 and Five at 0/13. Root cause: `generate_product_pack.py` didn't catch the resulting `RuntimeError`, so one failed image killed the whole run instead of skipping ahead — fixed (now logs and continues). Once ComfyUI came back online, resumed and completed both volumes; `desert-dunes` (Volume Four) failed once more on the resumed run and was cleanly skipped-then-retried thanks to the fix, rather than crashing again.

A duplicate, broken "Volume Two" listing (created by a pre-fix Gumroad publish attempt that failed on a non-square-thumbnail error but still partially created the product) was found and deleted this morning — only the correct Volume Two listing above remains.

**Upscale technique evaluated and rejected**: tested a hires-fix second pass (`LatentUpscaleBy` + low-denoise second `KSampler`) against the single-pass HQ workflow already in use. Improvement was marginal (slightly more fine texture) for a large time cost (~20-30 min/image vs ~5-8 min). Kept the single-pass HQ workflow as the standard.

- Site's shop cards now link to the three real live packs (previously fictional placeholder products with `#` hrefs) — done 2026-09-15.
- No affiliate program applied to yet.

## The plan, in priority order

### 1. Printable wall-art / wallpaper packs — LIVE, all 5 volumes published
Fastest realistic path: sell the aesthetic itself, not a physical product. No approval process, no waiting on affiliate networks, sells directly to whatever audience the IG/Facebook posts bring in.

- **Products**: Volumes One–Five, all live (see above).
- **Platform**: Gumroad.
- **Price**: £8 (Volume One, smaller pack) / £10 (Volumes Two-Five, 13-image packs).
- **Path to £2k**: at ~£9 net/sale average after Gumroad's fee, that's ~220 sales across all volumes. Realistic only with actual traffic — these products' job is to convert whatever audience the content builds, not to be the sole growth engine.
- **Next**: add Volumes Four/Five to the homepage shop cards (currently only 3 slots, showing One-Three); apply to an affiliate program once there's posting history.

### 2. Amazon Associates
Apply once the site has some real traffic (a few weeks of consistent posting). Needs 3 qualifying sales within 180 days to stay approved, so this only starts paying once there's an actual audience clicking through — not a week-one lever.

### 3. LTK / ShopMy
Usually gate on engagement/follower thresholds for brand-new accounts. Apply once IG has a consistent posting history to point to.

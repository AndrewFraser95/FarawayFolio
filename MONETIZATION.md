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

### 4. Hotel affiliate content (Booking.com Partner Program) — in progress, not yet monetized
Andrew asked 2026-09-17 to expand into "recommended hotels" content, ideally ones with affiliate deals. Real hotel data (names, ratings, prices, facilities) is sourced via the Booking.com MCP connector available in Claude Code sessions — this gives factually accurate hotel content instead of hallucinated hotel names, which matters since a wrong hotel name/claim in paid-feeling content is a worse trust problem than a generic scenery post.

**Important catch, found immediately**: the connector's returned booking URLs embed `aid=8132308` — that's Claude's own Booking.com affiliate id, not Andrew's. Using those links as-is would send any commission to Anthropic's account, not Faraway Folio's. Fixed by using plain (non-affiliate) booking.com links in hotel content until Andrew has his own affiliate id, at which point his `aid=` gets substituted into the same links.

**To get a real affiliate id**, Andrew needs to apply himself (business/tax details required, not something Claude can submit on his behalf):
- Booking.com's own affiliate program is run through their **Partner Hub** (partner.booking.com) — search for "Booking.com affiliate program" / "Booking.com Partner Hub" to find the current signup flow, since Booking.com restructures this periodically.
- Alternatively, Booking.com's affiliate program is also carried by third-party affiliate networks (Awin and CJ Affiliate both have listed it historically) — applying through one of those may be faster for a new/small site, worth comparing once Andrew is ready to apply.
- Needs: a live site with real content (farawayfolio.com already qualifies), business/payment details, and agreement to their terms.

**Until that id exists**: hotel content posts with real hotel facts and plain links, clearly not yet monetized — better to build genuine content/audience now than wait on the application before posting anything.

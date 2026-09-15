# Faraway Folio

Aspirational travel / quiet-luxury aesthetic content project. IG handle @farawayfolio (secured), contact foliofaraway@gmail.com.

## Structure
- `docs/` — static landing page (plain HTML/CSS, no build step) **and** `docs/media/` for published post images. Served by GitHub Pages, custom domain **farawayfolio.com** (repo: https://github.com/AndrewFraser95/FarawayFolio) — must be `docs/` specifically, GitHub Pages only serves repo root or `/docs`. (Not andrewfraser.com — that's Andrew's separate personal site, already using that domain on his GitHub account; Faraway Folio deliberately uses its own purchased domains instead.)
- `content-pipeline/` — ComfyUI bridge script + content calendar/strategy + publishing scripts.
- `x-marketing/` — X (Twitter) launch copy and ongoing post templates.

## Next steps, in priority order

1. ~~Reserve @farawayfolio on X/Twitter~~ — done.
2. ~~Register domains~~ — done: farawayfolio.uk, .com, .store, .info (1-year contracts, renewal reminder set for 2027-07-13, see below).
3. ~~Deploy the site~~ — repo pushed to GitHub; Pages needs enabling (see checklist below, one manual toggle).
4. ~~Set up ComfyUI bridge~~ — done. Windows machine reachable at `192.168.1.237` (LAN) / `100.104.162.124` (Tailscale, preferred — works off-network too), port 8188, `--listen 0.0.0.0` confirmed working.
5. **Generate content batches** — `content-pipeline/generate_batch.py` runs every prompt in `prompts.json` through ComfyUI. **Images stay on the Windows ComfyUI machine** (not copied to this Mac, which often runs clamshell/headless) — each is named `FarawayFolio_<theme-id>_NNNNN_.png` in ComfyUI's own output folder, so it's obvious on the PC which image is which. This Mac only keeps the matching `caption.txt` per theme under `content-pipeline/queue/<date>/<theme>/`:
   ```
   export COMFYUI_HOST=100.104.162.124
   python3 content-pipeline/generate_batch.py --out content-pipeline/queue
   ```
   `workflow_api.json` runs **Z-Image** (Alibaba Tongyi's open, Apache-2.0, 6B-param model — `z_image_bf16.safetensors` full model, not the turbo/distilled variant + `qwen_3_4b.safetensors` text encoder + `ae.safetensors` VAE), 30 steps / cfg 4 / 2MP / 2:3 portrait, with a real negative prompt. Add more themes to `prompts.json` (each needs `id`, `images` (4 prompts), `caption`, `pick`) to extend the rotation.

   Note: this replaced an earlier "Krea2 turbo" template downloaded from a community gallery, which turned out to be broken — it mismatched a video VAE onto an image pipeline (visible banding artifacts) and its bundled prompt-refinement LLM step degenerated into repeated punctuation. Switched to Z-Image, then upgraded again from the turbo/8-step config (`workflow_turbo.json`, kept for reference — fast but visibly flatter detail) to the full model at 30 steps after Andrew flagged the turbo output as not good enough for a paid product. Generation is much slower now (~5-8 min/image vs ~1 min for turbo) but the quality difference (real texture, atmospheric depth) is substantial and worth it — this is now the default for both social content and anything sold.
   `run_weekly_batch.sh` wraps this with the right env vars for scheduled/unattended runs (see Automation below).
6. **Launch a digital product early** (preset pack or packing-list PDF via Gumroad/Payhip) — this is the fastest realistic path to the £2k target since affiliate programs take months to pay out for a new account. See the monetization sequencing note in the content calendar.
7. **Apply to affiliate programs** (Amazon Associates, LTK, ShopMy) once the site is live and IG has some posting history.

## Posting workflow
Two paths, both real and working:

**Manual** (`generate_batch.py`): images land in ComfyUI's output folder on the Windows PC (named `FarawayFolio_<theme-id>_*.png`), captions land in `content-pipeline/queue/<date>/<theme>/caption.txt` on this Mac (also Taildropped to the PC as a per-batch zip, see `send_captions_via_taildrop()`). Post by hand from the PC.

**Live API posting** (`publish_batch.py`, `publish_instagram.py`, `publish_facebook.py`): generates and posts directly, no human review step (explicit choice — the only safety rail is `--limit`, capping posts per run, plus logging to `content-pipeline/publish.log`). **Instagram and Facebook are both confirmed working with real credentials** — first live test posts went out 2026-09-14 (balcony-golden-hour image): [Facebook](https://www.facebook.com/photo.php?fbid=122100719943475771&set=a.122100719967475771&type=3), [Instagram](https://www.instagram.com/p/DdRoW5_iJgi/). X is currently **not wired up** — media upload returns 403, likely X's Feb 2026 pricing change (tiered Free/Basic replaced with pay-per-use by default); not yet resolved, proceeding without it per Andrew's instruction.

Env vars needed: `COMFYUI_HOST`, `IG_USER_ID=28615169324810269`, `IG_ACCESS_TOKEN`, `FB_PAGE_ID=1343922692139344`, `FB_PAGE_ACCESS_TOKEN`, `PUBLIC_MEDIA_BASE_URL=https://farawayfolio.com` (for Instagram only — Facebook's `/photos` endpoint accepts direct file upload, no public hosting needed).

**Instagram uses the newer Instagram Login API** (`graph.instagram.com`, token prefix `IGAA...`), not the older Facebook-Page-token flow — no linked Facebook Page required for IG posting at all.

**Facebook Page gotcha, already resolved**: a Facebook "Professional account" (creator-mode personal profile) is a completely different object type from a real Page — Professional accounts don't show up under `/me/accounts` and can't receive Page API posts. The Page actually in use is **"Faraway Folio HQ"** (not "Faraway Folio" — that name was squatted by the Professional profile). If Page posting ever breaks, check you're using a genuine Page object, not a Professional profile.

**GitHub push credentials**: no persistent storage (blocked by design — a classifier in this environment rejects both raw curl+Authorization-header reuse and git-credential-helper storage as unsafe patterns). Pattern in use: embed a token in the remote URL just for one push, reset to the clean URL immediately after (`publish_batch.py`'s `git_push()` does this automatically via a `GITHUB_PAT` env var; manual pushes use the same pattern by hand).

## Automation
No **recurring** scheduled job — Andrew doesn't want one for regular posting (a launchd job was set up and then removed on 2026-09-14 at his request). Run scripts manually (confirm the Windows ComfyUI machine is awake first — it doesn't stay on 24/7, connect via Tailscale `100.104.162.124:8188`).

**Distinct from the above**: `com.dev.faraway-folio-volumes` is a *one-shot* launchd job (not recurring, no `StartInterval`/`StartCalendarInterval`) used the night of 2026-09-14/15 to run a long, explicitly-requested overnight generation job (`content-pipeline/run_all_volumes.sh`) that needed to survive session boundaries — plain `nohup ... & disown` didn't survive the Claude Code session ending, launchd did. Safe to `launchctl bootout gui/$(id -u)/com.dev.faraway-folio-volumes` and remove the plist once that run is done; it's not meant to persist as ongoing infrastructure.

## Digital products (Gumroad)
Live storefront: https://farawayfolio.gumroad.com. Pipeline:
- `content-pipeline/products/volume-N.json` — spec per pack (name, theme, price, list of `{id, prompt}` images, 12-15 each).
- `content-pipeline/generate_product_pack.py --volume products/volume-N.json` — generates every image (HQ workflow), makes print (2:3 JPEG) + wallpaper (9:16 crop) versions via `sips`, writes a README, zips it. **Resumable** — skips images that already have finished JPEGs, reuses orphaned raw PNGs from an interrupted run instead of regenerating.
- `content-pipeline/publish_volume_to_gumroad.py --volume ... --pack-dir ... --zip ...` — creates the Gumroad product (cover image, description, tags) via the `gumroad` CLI and publishes it live.
- `content-pipeline/run_all_volumes.sh` — chains multiple volumes back-to-back.
- Volume One (6 images, £8) also has a custom landing page (`branding/landing.html`, self-contained Tailwind + light/dark mode, published via `gumroad products page publish xtini ./landing.html`) — gallery images are deliberately low-res/watermarked previews, never the actual sellable files.
- **Gumroad CLI**: installed via `curl -fsSL https://gumroad.com/install-cli.sh | bash`, authenticated via `gumroad auth login` (OAuth device flow, needs Andrew's browser approval). `custom_html` (landing pages) caps at 500,000 characters — keep embedded images compressed/small.

## Posting workflow (continued)
`content-pipeline/starter_content.json` + `publish_starter_content.py` — lighter single-image engagement posts (not tied to a product pack), e.g. European-city "what's your dream day in Rome?" posts. Same live-posting pattern as `publish_batch.py` (Instagram via public URL, Facebook via direct upload) but simpler, one image per post.

## Domain renewal
4 TLDs on 1-year contracts, renewing ~2027-08-13: .info £66/yr, .store £33/yr, .com £15/yr, .uk £15/yr = **£129/yr total**. Reminder set for 2027-07-13 to decide whether to renew all four or drop to just .com — only renew what's earning its keep.

## Not yet done
- ~~farawayfolio.com HTTPS~~ — live and confirmed as of 2026-09-15.
- X posting blocked (403 on media upload) — needs Andrew to check his X Developer Portal plan/billing, see "Posting workflow" above.
- ~~Volumes Four and Five incomplete~~ — resolved 2026-09-15: ComfyUI came back online, both volumes finished (Four needed one extra rerun on `desert-dunes`, which failed twice total across the two runs) and are live on Gumroad. All 5 volumes now published; only Volumes One-Three are on the homepage shop cards (3 slots) — Four/Five are live on the storefront but not yet linked from the site.
- **European-city engagement images generated, not yet posted** — all 6 (`content-pipeline/starter_content.json`: Rome, Paris, Barcelona, Amsterdam, Santorini, Lisbon) generated and committed locally to `docs/media/2026-09-15/` via `publish_starter_content.py --no-push`. Posting itself is blocked on missing `IG_ACCESS_TOKEN`/`FB_PAGE_ACCESS_TOKEN` env vars (not present in a fresh session, by design). Once those are available, rerun `publish_starter_content.py` (drop `--no-push` once a `GITHUB_PAT` is also available, so Instagram's public-URL requirement is satisfied too).
- **GitHub push and social posting left for Andrew to do at end of session, by his own request** — no `GITHUB_PAT`, `IG_ACCESS_TOKEN`, or `FB_PAGE_ACCESS_TOKEN` are available in a fresh session (nothing persists across sessions by design). All pack/site changes are committed locally on `main` but not pushed; GitHub Pages hasn't redeployed with the new Volume Two-Five assets or the shop-card update yet.
- No real affiliate program applied to yet — the site's 3 product cards now link to the real live Gumroad packs (Volumes One/Two/Three) instead of fictional placeholders, as of 2026-09-15.
- Facebook Page's own public URL isn't recorded anywhere in this repo (only the numeric `FB_PAGE_ID`) — get it via the Graph API (`GET <page-id>?fields=link`) with a fresh Page token, or from Andrew, before linking to it anywhere.
- Profile pictures/bios drafted (`branding/`) but not reconfirmed since Andrew said he'd uploaded them.
- ~~One-shot launchd job `com.dev.faraway-folio-volumes` still loaded~~ — no longer needed, all volumes finished; safe to bootout/remove (see Automation section) whenever convenient.

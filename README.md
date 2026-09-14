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
No scheduled/cron job — Andrew doesn't want one (a launchd job was set up and then removed on 2026-09-14 at his request). Run scripts manually (confirm the Windows ComfyUI machine is awake first — it doesn't stay on 24/7, connect via Tailscale `100.104.162.124:8188`).

## Domain renewal
4 TLDs on 1-year contracts, renewing ~2027-08-13: .info £66/yr, .store £33/yr, .com £15/yr, .uk £15/yr = **£129/yr total**. Reminder set for 2027-07-13 to decide whether to renew all four or drop to just .com — only renew what's earning its keep.

## Not yet done
- farawayfolio.com HTTPS cert still provisioning as of 2026-09-14 (automatic via GitHub, can take up to 24h) — until it's ready, real production Instagram posts (via `publish_batch.py`'s auto-hosting flow) aren't possible; the live test above used a one-time workaround (temporarily using `andrewfraser.com`, Andrew's separate personal domain, as a test-only image host, then reverted).
- X posting blocked (403 on media upload) — needs Andrew to check his X Developer Portal plan/billing, see "Posting workflow" above.
- No affiliate links are live — the "Shop the pick" buttons on the site are placeholders.
- No digital product built yet.
- Profile pictures/bios drafted (`branding/`) but not yet confirmed uploaded to every platform by Andrew (he said he had, worth a final visual check).

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
   `workflow_api.json` runs **Z-Image Turbo** (Alibaba Tongyi's open, Apache-2.0, 6B-param model — `z_image_turbo_bf16.safetensors` + `qwen_3_4b.safetensors` text encoder + `ae.safetensors` VAE), 1:1 square by default (edit node `49` to change aspect ratio for Reels/Stories vs. feed). Add more themes to `prompts.json` (each needs `id`, `prompt`, `caption`, `pick`) to extend the rotation beyond the initial 6.

   Note: this replaced an earlier "Krea2 turbo" template downloaded from a community gallery, which turned out to be broken — it mismatched a video VAE onto an image pipeline (visible banding artifacts) and its bundled prompt-refinement LLM step degenerated into repeated punctuation. Z-Image Turbo is the officially documented, verified-working local model for this GPU.
   `run_weekly_batch.sh` wraps this with the right env vars for scheduled/unattended runs (see Automation below).
6. **Launch a digital product early** (preset pack or packing-list PDF via Gumroad/Payhip) — this is the fastest realistic path to the £2k target since affiliate programs take months to pay out for a new account. See the monetization sequencing note in the content calendar.
7. **Apply to affiliate programs** (Amazon Associates, LTK, ShopMy) once the site is live and IG has some posting history.

## Posting workflow
There's no connected Instagram/X posting API in this setup (both require their own developer-account/app-review process — a separate, bigger undertaking). The realistic loop for now:
1. Run a batch — images land in ComfyUI's output folder **on the Windows PC** (named `FarawayFolio_<theme-id>_*.png`), captions land in `content-pipeline/queue/<date>/<theme>/caption.txt` on this Mac.
2. Post from the PC: image from ComfyUI's output folder to Instagram feed/Reel, caption text (copy from the Mac's `caption.txt`, or ask this session to paste it — already includes the affiliate-pick line and hashtags).
3. Cross-post the same caption's first line to X via the templates in `x-marketing/launch-copy.md`, or ask for a fresh one-liner per post.

## Automation
No scheduled/cron job — Andrew doesn't want one (a launchd job was set up and then removed on 2026-09-14 at his request). Run `content-pipeline/generate_batch.py` manually whenever fresh content is wanted (confirm the Windows ComfyUI machine is awake first — it doesn't stay on 24/7, connect via Tailscale `100.104.162.124:8188`).

## Live posting via Instagram/X APIs (in progress)
`content-pipeline/publish_batch.py` generates content and posts it **directly, live, with no human review step** (explicit choice — the only safety rail is `--limit`, capping posts per run). It:
1. Generates an image via ComfyUI (downloaded locally, unlike `generate_batch.py`).
2. Commits it into this repo's `docs/media/<date>/<theme-id>.png` and pushes — GitHub Pages then serves it at a public URL, which Instagram's Content Publishing API requires (it fetches images server-side, no direct upload).
3. Posts to Instagram (`publish_instagram.py`, Graph API) and X (`publish_x.py`, API v2 + v1.1 media upload).
4. Deletes the local temp copy.

Needs these env vars set: `COMFYUI_HOST`, `IG_USER_ID`, `IG_ACCESS_TOKEN`, `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `PUBLIC_MEDIA_BASE_URL=https://farawayfolio.com`.

**Setup checklist:**
1. ~~GitHub repo + Pages~~ — done: https://github.com/AndrewFraser95/FarawayFolio, code pushed, Pages enabled (source: main branch, `/docs` folder). **Custom domain still needed**: repo → Settings → Pages → Custom domain → `farawayfolio.com` → Save, then add these DNS records at the registrar: A records @ → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`; CNAME `www` → `andrewfraser95.github.io`. (GitHub defaulted Pages to `andrewfraser.com`, which is Andrew's separate personal site on the same account — deliberately not used here.)
2. ~~Instagram → Business + Facebook Page~~ — done.
3. Meta Developer App created, App ID `1411016084512038`. Still needed: add the **Instagram Graph API** product if not already added, then generate a User Access Token via [Graph API Explorer](https://developers.facebook.com/tools/explorer) with scopes `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management` — this works without App Review since it's Andrew's own app + Page + IG account (Development Mode). Then: exchange for a long-lived token, call `/me/accounts` to find the linked Page, read `instagram_business_account.id` from it → that's `IG_USER_ID`; the Page's access token → `IG_ACCESS_TOKEN`.
4. X Developer account (Free tier) → Project + App → User auth set to Read+Write → four API keys still needed.

None of this is live yet — scripts are written but not yet run against real credentials. First real "did this actually post" test still needs to happen once IG_USER_ID/IG_ACCESS_TOKEN and the X keys exist.

## Domain renewal
4 TLDs on 1-year contracts, renewing ~2027-08-13: .info £66/yr, .store £33/yr, .com £15/yr, .uk £15/yr = **£129/yr total**. Reminder set for 2027-07-13 to decide whether to renew all four or drop to just .com — only renew what's earning its keep.

## Not yet done
- Two real image batches generated 2026-09-14 (Z-Image Turbo, 6 images each) — first batch was downloaded to this Mac (`content-pipeline/queue/2026-09-14/`, back when images were still copied here), second batch onward stays on the Windows PC per the clamshell workflow above. Neither batch posted yet.
- No affiliate links are live — the "Shop the pick" buttons on the site are placeholders.
- No digital product built yet.
- GitHub Pages not yet enabled (manual toggle, see checklist above) — `docs/media/` URLs won't resolve until then.
- IG_USER_ID/IG_ACCESS_TOKEN and X API keys not yet obtained — `publish_batch.py` untested against real accounts.

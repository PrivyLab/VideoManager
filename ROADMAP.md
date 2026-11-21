# VideoManager Roadmap

The beta should preserve the current user-visible operations while redesigning them for browser-local media work: download supported single videos, batches, and playlists; inspect supported pages for video links; organize and play a local library, including QR-based playback on a local network; trim, extract audio, compress, create GIFs, and stitch clips; and show download/processing progress. Editing, processing, and export of user-selected media stay in the browser. New visitors may use browser-local editing as guests for one successful export per rolling 24-hour period. After an export, prompt them to create an account or sign in; they may use the guest allowance again when the next 24-hour window begins. The premium URL downloader is a separate exception: it is available only to authenticated premium users, never to guests. It handles only supported sources, uses an authenticated backend streaming endpoint and isolated configured Tor/VPN egress, and does not store downloaded media in VideoManager. All other third-party API integrations (such as billing, email, or any later approved external service) must also be called by the backend through approved provider-specific integrations; the browser calls only VideoManager APIs. Persist an audit event linking each external API action to the initiating user or system actor. The backend also handles accounts, authentication, plans, feature configuration, and administration. Never upload user-selected source files or projects for editing. Accounts have normal and premium plans; administrators manage users, entitlements, and feature availability.

This roadmap is directional: phases describe dependencies and intended outcomes, not release dates. Priorities favor a useful, reliable local editor before optional AI or collaboration features.

## Current capabilities

- Download single videos, batches, and playlists; inspect pages for video links.
- Organize and play the local video library, including QR-based playback on a local network.
- Trim a clip, extract audio, compress video, create a GIF, and stitch clips.
- Track downloads and processing through the existing dashboard and background progress updates.

The current stitcher offers Smart Auto, Fast Stream Copy, and Safe Re-encode modes. Its output-quality choices are Match source (the default), 1080p, 720p, and 480p. Explicit resolution presets re-encode the clips, use the first clip's orientation, and do not upscale that clip; Fast Stream Copy preserves source quality and ignores the resolution choice.

The current product's downloader, library, and media tools use the backend. The beta should preserve their user-facing capabilities, not their server-side media implementation: move editing, processing, export, and the media library to the user's device; keep supported remote URL acquisition behind the authenticated premium downloader; and preserve page-link inspection, batches/playlists, local playback, QR playback, and progress feedback subject to security and compatibility validation. There is not yet a browser-local editing workflow, a secured premium downloader flow with controlled egress, persistent local project format, multi-clip timeline, or export queue.

The current-capabilities list describes existing code, not the target architecture. Preserve the supported user workflows but redesign their implementation: do not retain server-hosted user media or backend editing/export; keep the library device-local; and redesign QR playback as an explicitly user-initiated, access-controlled local-network feature that does not upload media to VideoManager. Page inspection, batch/playlist downloads, and URL sources must be constrained to sources that can be handled safely. Publish a tested browser/device/codec/source compatibility matrix and give actionable fallback errors; do not promise universal compatibility.

## Roadmap at a glance

| Phase | Focus | Outcome |
|---|---|---|
| 0A | Local prototype for user testing | Build and test the browser-first product locally with Docker PostgreSQL and LocalStack; no production AWS resources |
| 0B | Post-test beta readiness and deployment | After the user tests and approves the prototype, resolve launch policies, harden the product, and deploy the beta to AWS Mumbai |
| 1 | Browser timeline editor MVP | Assemble, trim, preview, and export videos entirely on the user's device |
| 2 | Browser transforms and conversion | Common formats, framing, speed, and audio controls processed client-side |
| 3 | Titles, subtitles, and effects | Add presentational polish without leaving the editor |
| 4 | Pro workflow | Reusable presets, batch jobs, project portability, and advanced controls |
| Future | Organization SaaS / Enterprise | Shared workspaces, organization administration, identity integrations, and governance |
| Later | Optional smart features | Opt-in transcription, assisted edits, and collaboration after core editing is stable |

## Phase 0A — Local prototype for user testing

**Goal:** build a local, end-to-end prototype for the user to test before committing to production policies or deploying to AWS. This phase is not a public beta and must not use production accounts, credentials, or data.

### Local development environment

- [ ] Run the React frontend, FastAPI API/downloader, and PostgreSQL locally. Use Docker for PostgreSQL and the LocalStack image the user has already pulled; do not pull or provision a real AWS resource for this phase.
- [ ] Port the prototype's application metadata/data-access path to local PostgreSQL using versioned migrations, so the prototype exercises its intended relational data model rather than leaving PostgreSQL idle.
- [ ] Use LocalStack only for the AWS APIs the prototype actually exercises, initially S3 integration tests for the audit archive if needed. Direct-stream downloader media must not go into S3 or SQS.
- [ ] Keep local configuration and test credentials separate from any future AWS account. LocalStack is an API emulator, not a production-equivalence test for RDS, ECS/Fargate, CloudFront, IAM operations, networking, or AWS availability.
- [ ] Add a reproducible local startup/test/cleanup workflow and synthetic fixtures. Document any Docker services and LocalStack services required; use the already-pulled image rather than downloading another copy.

### User-testable prototype scope

- [ ] Implement the selected browser media stack in a worker and port the current trim, audio extraction, compression, GIF, and stitch workflows for local-device processing. Compare outputs with the current Python/FFmpeg implementation as a temporary reference.
- [ ] Provide local file import, browser-local library/workspace, playback, export, progress, cancellation where supported, and actionable error behavior. Do not upload user-selected files, frames, projects, or exports.
- [ ] Exercise the direct-stream downloader locally with supported test sources, the 100 MB per-video default, and bounded-memory transfer. A local proxy may be used for functional tests, but production Tor/VPN routing, source-visible IP, and fail-closed guarantees remain Phase 0B launch validation.
- [ ] Use clearly marked development-only seeded identities/test accounts if account switching is needed to test UI flows. Do not treat this as the production authentication implementation. The guest one-successful-export-per-rolling-24-hour experience may be exercised locally with test data, without committing to guest-ID retention.
- [ ] Do not implement account recovery/session-expiry policy, production guest or downloader metadata retention, downloader limit overrides beyond the fixed prototype default, real billing/email integrations, production monitoring/alerts, AWS budgets, backup/restore operations, or legal approval in this phase.
- [ ] Test the prototype on the supported desktop browsers and representative files; record defects and user feedback. Use the already-selected media libraries rather than reopening the library-selection research.

### Prototype acceptance gate

The user can run the prototype locally, exercise its agreed core workflows, inspect failures/progress, and provide feedback. Stop at this gate for user testing and changes. Do not deploy the prototype publicly or begin production rollout until the user accepts it and the Phase 0B launch decisions are addressed.

## Phase 0B — Post-test beta readiness and deployment

**Goal:** after the user tests and approves the local prototype, finalize deferred policies, harden the product, complete production-readiness validation, and deploy the beta. Phase 0A can begin without these decisions; they are gates for production-grade implementation and beta launch.

### Decisions and controls required after prototype testing, before beta

- [ ] Finalize production authentication behavior: session expiry/revocation, account recovery, email verification, and the MFA deferral safeguards.
- [ ] Set and disclose finite retention/deletion rules for guest identifiers and minimal downloader request metadata; never retain source URLs or downloaded media.
- [ ] Benchmark browser and downloader limits, then set the maximum audited per-user downloader override above the 100 MB default. Do not select an untested override ceiling.
- [ ] Before launch, configure basic monitoring, spend alerts, database backups, restore verification, and deployment rollback. Detailed low/expected/high cost analysis and formal validation of the provisional availability/RTO/RPO targets remain deferred until after live usage, as previously decided.
- [ ] Obtain privacy/legal approval for the selected 30-day audit-event retention and deletion policy before beta. The local prototype can test audit-event flow, but this approval is not implied by LocalStack testing.

### Complete and harden the locally validated product

- [ ] Harden the PostgreSQL data model for accounts, ownership, entitlements, and audit records. Before production cutover, plan and test migration of any SQLite metadata that must be retained; back up data, validate records and relationships, and document recovery.
- [ ] Keep the implementation and integrations running locally until the prototype is accepted. Use LocalStack for the AWS APIs exercised by local integration tests; do not add an SQS queue or downloader media-storage integration for the direct-stream flow.
- [ ] Complete cross-browser/device performance and compatibility validation of the selected media stack below. Compare prototype outputs with current Python/FFmpeg reference outputs, memory/CPU use, responsiveness, bundle and worker costs, and failure behavior across representative files. Test supported desktop Chrome, Edge, Firefox, and Safari, then assess mainstream mobile browsers; document exact supported versions and codec/container combinations based on results. Verify the selected FFmpeg.wasm core build's enabled codecs/filters and license obligations before distribution. Treat 100 MB as an initial candidate limit until these tests establish the supported editing limit; this validates limits and implementation, not a search for replacement libraries.
- [ ] Harden the prototype's TypeScript media-engine interface and dedicated Web Worker contract. Keep React responsible for UI and job orchestration, not decoding/encoding. Use streaming inputs/outputs and OPFS or other browser-managed storage where supported; avoid loading whole source and result files into duplicate in-memory buffers. Verify progress, cancellation, output validation, and actionable errors.
- [ ] Complete browser-operation parity tests against the existing Python/FFmpeg implementation as a temporary correctness oracle. Do not remove Python media endpoints until every retained operation passes output and browser-compatibility gates. Remove backend media processing after parity is verified; retain backend account/admin services and the authenticated premium URL downloader.

#### Selected browser media stack and migration map

These are the selected implementation tools for the browser beta, not an open-ended shortlist:

| Tool | Decision and responsibility |
|---|---|
| [`mediabunny`](https://mediabunny.dev/) | Primary media library for metadata/probing, container demux/mux, compatible packet-copy, browser-side conversion, thumbnail extraction, and media sample handling. Use its conversion and output-source APIs for transforms and clip assembly. |
| Browser [**WebCodecs API**](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API) (`VideoDecoder`, `VideoEncoder`, `AudioDecoder`, `AudioEncoder`) | Codec engine used through Mediabunny for supported hardware/native decode and encode. Check actual codec configuration support at runtime before processing; a browser brand or file extension is not a capability check. WebCodecs alone does not read/mux media containers. |
| Browser [**Dedicated Web Workers**](https://developer.mozilla.org/en-US/docs/Web/API/Worker) and **OffscreenCanvas** | Run the media pipeline away from the React/UI thread; use worker messages for job lifecycle, progress, cancellation, and errors. Use OffscreenCanvas for worker-side frame processing where supported. |
| [`@ffmpeg/ffmpeg`](https://ffmpegwasm.netlify.app/) with [`@ffmpeg/core`](https://www.npmjs.com/package/@ffmpeg/core) | Compatibility fallback only, initially single-threaded, for the existing palette/dither GIF pipeline, MP3 extraction when browser encoders cannot provide it, and specific tested formats/filters missing from the primary path. Do not route ordinary compatible conversion through it. The project documents slower performance than native FFmpeg, a 2 GB WebAssembly input limit, and higher memory/CPU use for its multithreaded build; its progress reporting is experimental. Keep fallback operations bounded and report stages rather than claiming precise progress when the core cannot provide it. |
| Browser [**File System API**](https://developer.mozilla.org/en-US/docs/Web/API/File_System_API) including **OPFS** (`navigator.storage.getDirectory()`), **IndexedDB**, and **File System Access API** (`showSaveFilePicker`) | Store app-managed local media/work files in OPFS where available and project/library metadata in IndexedDB. Stream exports to a user-selected file when supported; provide a normal download fallback. Handle unsupported APIs, quota, eviction, and user cancellation explicitly. |

This selection intentionally does **not** use [`gifenc`](https://github.com/mattdesl/gifenc): its own documentation describes no dithering support and cautions that it is better suited to flat graphics than photographic/video frames. The existing video-to-GIF workflow uses palette generation and dithering, so the selected FFmpeg.wasm GIF path better preserves the current result. The FFmpeg.wasm fallback is not a promise that every current Python/FFmpeg codec/filter is included; supported capabilities are restricted to the core build we verify and ship.

Mediabunny's documentation covers browser parsing/writing, on-demand reads, streaming targets/backpressure, conversion, trimming, resizing, audio resampling, progress, and cancellation. Its documented codec availability depends on the browser. Its conversion API currently forces transcoding when a non-default trim start is used, so retain fast trim separately through encoded-packet copying only when keyframe boundaries and stream compatibility permit; use decode/encode for frame-accurate cuts. Review Mediabunny's MPL-2.0 license and the chosen FFmpeg core's FFmpeg/external-library licenses during dependency approval.

| Existing Python operation | Selected browser implementation | Important behavior to preserve or validate |
|---|---|---|
| `probe_file` / `VideoStitcher.probe_video` | Mediabunny `Input` and track metadata; Mediabunny/WebCodecs decode capability checks | Duration, dimensions/orientation, tracks, codecs, and clear unsupported/corrupt-input errors |
| `VideoStitcher.stitch` | Mediabunny `Input`, encoded packet sinks/sources, and `Output` for stream-copy when all stream configurations match; Mediabunny `VideoSampleSink`/`AudioSampleSink` with `VideoSampleSource`/`AudioSampleSource` and WebCodecs for normalized re-encode | Preserve ordering, mixed dimensions/orientation, missing audio behavior, selected output quality, browser-playable MP4, timestamps/audio sync, and full output validation |
| `trim_video` | Mediabunny encoded-packet demux/mux for keyframe-safe stream-copy; Mediabunny conversion/WebCodecs for frame-accurate cuts | Test actual cut-boundary accuracy and timestamp/audio sync; never label a keyframe-limited cut frame-accurate |
| `extract_audio` and trim-audio path | Mediabunny track extraction/conversion and WebCodecs audio encoding where supported; `@ffmpeg/ffmpeg` fallback for MP3 when browser encoding is unavailable | Preserve supported MP3/M4A/AAC/WAV choices and bitrates; handle absent audio and unavailable encoders explicitly |
| `compress_video` | Mediabunny Conversion API with WebCodecs, quality/resolution controls, and audio conversion | Preserve named presets, aspect ratio, audio settings, and output-size estimates; do not promise exact size from a quality preset |
| `create_gif` | `@ffmpeg/ffmpeg` + verified `@ffmpeg/core` GIF palette/dithering filters, executed in a worker | Preserve start time, 1–30 second duration, FPS/width bounds, palette quality, animation playback, and output-size limits; do not promise frame-level progress unless measured |
| `generate_thumbnail` / preview | Mediabunny `CanvasSink`/`VideoSampleSink`; HTML video/Canvas only for simple supported cases | Orientation, seek accuracy, decoder capability checks, cleanup of frames/bitmaps, and no server upload |

Use the existing Python/FFmpeg implementation only as a temporary reference for test fixtures and expected behavior. Porting is complete per operation only when representative input/output tests pass and the browser/device matrix, resource bounds, cancellation, and failure behavior are documented. The same source can require different encoders on different browsers; check actual codec configuration before starting. Unsupported operations must fail before expensive processing with an explanation, rather than silently uploading media or falling back to backend editing.

**Architecture decision:** TypeScript orchestration in the frontend; a dedicated worker-based media engine; Mediabunny + WebCodecs for the normal processing path; `@ffmpeg/ffmpeg` + the verified single-thread `@ffmpeg/core` only for the named compatibility operations above; OPFS/IndexedDB for local storage; and File System Access API with a download fallback for exports. Keep account, entitlement, audit, and premium URL download flows in the backend. Editing source files and exports must never be sent to it.

#### Automatic GPU & Hardware Acceleration Policy

Use hardware acceleration where the browser and device support it, while preserving usable fallbacks or clear compatibility errors on other devices:

1. **Client-Side Live Web Application (Browser Execution via WebCodecs)**:
   - This policy is planned for the browser media-engine implementation and is not active until the worker and capability-gated encoding path are added.
   - At runtime, query `VideoEncoder.isConfigSupported()` for the exact codec, dimensions, frame rate, bitrate mode, and each candidate before expensive work begins. Browser support for this API and codec acceleration varies, so do not infer support from the browser name or file extension.
   - Probe hardware and software configurations explicitly, for example `hardwareAcceleration: 'prefer-hardware'` and `'prefer-software'`, in a supported worker context. If the preferred hardware configuration is accepted, use it; if it is unsupported or initialization later fails, retry a software/`no-preference` configuration and surface a clear compatibility error only if neither configuration works.
   - Hardware acceleration applies to browser codec encode/decode operations, not to unrelated JavaScript or canvas work. Actual hardware routing is controlled by the browser and may be unavailable in restricted, virtualized, or power-saving contexts.
   - Never claim that hardware acceleration guarantees a resolution, frame rate, quality target, exact file size, or output-byte parity. Validate the produced MP4 and decodability through the browser/device golden test matrix.

2. **Backend Services & Desktop Engine (Python / FFmpeg)**:
   - The backend includes a dynamic hardware encoder detection probe (`detect_hardware_encoder()`).
   - Its current implementation prioritizes a 64x64 one-frame FFmpeg encode probe in this order:
     * **macOS / Apple Silicon**: `h264_videotoolbox` (Apple hardware GPU/media engine)
     * **NVIDIA (Linux/Windows)**: `h264_nvenc`
     * **Intel (Linux/Windows)**: `h264_qsv`
     * **Linux VA-API**: `h264_vaapi` is currently detected but not mapped to encode arguments
     * **Universal fallback**: `libx264` (CPU software encoding)
   - The probe runs at server startup; subsequent calls reuse the process-cached result until the process restarts. A probe exception or failed candidate falls through to the next candidate or `libx264`.
   - A successful one-frame probe verifies encoder initialization, but it is not a benchmark or an end-to-end output-quality gate. A real encode can still fail due to resolution, color format, driver, container, or runtime restrictions.
   - Hardware encoding is an optimization: use the correct encoder arguments for each supported backend, validate the final media for decodability and stream integrity, and compare output behavior rather than assuming byte-for-byte parity with CPU encoding.

- [ ] Complete backend hardware-acceleration implementation by adding a real encode-argument branch for `h264_vaapi`, or remove it from detection if VA-API is not a supported target. Also validate the existing `h264_videotoolbox`, `h264_nvenc`, and `h264_qsv` argument mappings on supported representative hosts.
- [ ] Add focused hardware tests with mocked FFmpeg candidates: candidate priority, a failed probe continuing to the next candidate, probe exceptions/timeouts, CPU fallback, cache behavior, and exact output arguments for each mapped encoder. Preserve the existing public smoke test, but do not treat it as proof that hardware encoding works.
- [ ] Add browser capability tests for supported, unsupported, hardware, software, and failed-initialization configurations in dedicated worker jobs. Establish a compatibility matrix for supported desktop/mobile browsers, codecs, resolutions, and devices before promising browser hardware acceleration.
- [ ] Build golden test fixtures for every current media operation, including mixed portrait/landscape stitching, variable frame rates, missing audio, non-keyframe trim boundaries, and unsupported codecs. Compare browser outputs with defined behavior and decodability checks, not byte-for-byte equality with FFmpeg outputs.
- [ ] Set per-operation browser/device input limits only after measuring peak memory, processing time, output correctness, tab stability, and thermal/resource behavior on representative desktop and mobile devices. Establish smaller supported limits or disable specific operations on devices that cannot meet the gate; do not assume the downloader's server limit is automatically a safe browser-editing limit.
- [ ] Build a backend URL-downloader proof of concept for representative supported sources, preserving supported single-video, batch, playlist, and page-link inspection workflows. Test source compatibility, redirects, playlists/manifests, authenticated streaming requests, large files, chunked transfer, slow-client backpressure, cancellation, and client disconnects. For batches and playlists, define browser delivery, partial-failure reporting, and retry behavior without creating server-side archives. Apply SSRF protections and selected egress to page inspection as well as media fetches. Set the initial server-enforced maximum to 100 MB per video; allow admins to set an audited per-user size limit, bounded by a platform hard ceiling established by benchmarks. Also enforce duration, concurrency, and usage limits. Ensure the platform ceiling is within tested browser editing capability unless a separate download-only mode is explicitly designed. On disconnect, abort the upstream fetch and explain that retry may restart from the beginning unless source range support is verified. Do not persist downloaded media or source URLs, and do not let the browser contact the media source directly.
- [ ] Offer an explicit downloader egress choice (backend direct egress, Tor, or a managed VPN). Route all source-fetch traffic, including DNS, through the selected path; if Tor/VPN is selected, fail closed when it is unavailable and never retry directly. Verify the source sees only the backend or selected egress address, not the user's address.
- [ ] Do not promise arbitrary-site downloading or browser-cookie extraction. Do not forward user IP headers or browser credentials to source sites. Explain that the backend still sees the user's connection IP and that Tor/VPN egress does not guarantee anonymity or source availability.
- [ ] Define supported browser/device/codec/container/source and egress matrices. Unsupported codecs or sources, blocked Tor/VPN traffic, or tunnel failures must produce clear errors and safe fallbacks where available; never silently switch to browser-direct fetching or editing on the backend.
- [ ] Secure downloader URL fetching against SSRF: allow only supported protocols, block loopback/private/link-local/metadata destinations, revalidate redirects and resolved addresses, isolate workers, and restrict worker network egress to the configured path.
- [ ] Use Web Workers and streaming/chunked file handling where supported so media work does not freeze the UI or unnecessarily duplicate large buffers. Detect unsupported formats/capabilities before work starts and provide actionable errors.
- [ ] Let users choose a local video file in the browser and process it there, producing a separate export without modifying the original. Offer an explicit opt-in to keep a copy in the app-managed browser workspace for project reopening. Never upload user video bytes for editing. Support relinking/reselecting a source if the browser cannot retain it or its permission expires.
- [ ] Preserve the local video library and playback workflows using browser-managed media and metadata only. Redesign QR playback as an explicit, time-limited pairing flow for a device on the local network; define and test authentication, access expiry, network exposure, and browser/platform limitations before implementation. Never route the media through VideoManager's cloud storage.
- [ ] Preserve progress feedback for downloads and local media operations with clear status, cancellation where supported, and actionable failure states. Keep local editing-task history on-device and avoid exposing source URLs in progress UI or logs.
- [ ] Keep local editing projects and any retained source/preview data in browser-managed storage such as OPFS or IndexedDB where supported; handle browser quota limits, eviction, private-browsing restrictions, and storage permission failures gracefully. Provide a portable project/export download.
- [ ] Set the initial maximum user-selected local video size to 100 MB per file and one import at a time per browser by default for beta, subject to the media-processing benchmark. These limits are client-enforced and device-local. Separately, set the server-enforced downloader default to 100 MB per video and allow an audited per-user admin override up to the benchmarked platform ceiling; enforce duration, concurrency, and usage limits too. Keep the platform ceiling within tested browser editing capability so a successful download can be edited.
- [ ] Build authentication, sign-in/sign-out, account recovery, email verification, and session review/revocation. Defer MFA to future scope; until it is implemented, restrict administrator access to named accounts, require re-authentication for sensitive administrative actions, and log and alert on privileged sign-ins and changes. Record the increased account-takeover risk for this period.
- [ ] Allow a guest one successful browser-local export per rolling 24-hour period. The guest may import and edit locally to prepare that export; count it only after a validated export is generated, not for failed or cancelled attempts. Afterward, keep the completed result available for download, prompt for account creation/sign-in, and block new imports, edits, and exports until the next 24-hour window begins or the visitor authenticates.
- [ ] Issue a random, opaque, server-backed guest ID and use server timestamps to enforce one successful export per rolling 24-hour period. Keep this record minimal; do not send media, filenames, or project data to the server, and do not use IP addresses or browser fingerprinting as the guest identity. Define and disclose guest-ID retention before launch, rate-limit ID issuance, and let account creation claim the current guest session without deleting browser-local work. This is a product gate, not high-assurance identity: users can still reset or tamper with browser state.
- [ ] Keep the URL downloader unavailable to guests: it always requires an authenticated account and premium entitlement, in addition to the server-enforced quotas.
- [ ] For beta, grant premium downloader access manually through an administrator-controlled, time-limited entitlement; audit every grant, extension, revocation, and expiry. Do not collect subscription payments or imply that a manual grant is a paid subscription.
- [ ] Implement server-side authorization for accounts, plans, feature configuration, administrative actions, and the premium downloader endpoint. Do not create backend editing, transcoding, or export APIs.
- [ ] Route all third-party API calls through the backend; prohibit direct browser-to-provider API calls and never put provider secrets in frontend code. Use allowlisted, provider-specific integrations rather than a generic open proxy. Record durable audit events for user-initiated external calls and privileged management actions.
- [ ] Define audit-event fields before beta and retain application audit events for one month (30 days) in PostgreSQL and the S3 archive. At minimum record actor/account, action, provider (and only a normalized host when useful), timestamp, outcome, and a correlation/request ID. Redact credentials, tokens, full URLs and sensitive parameters, request/response bodies, and media contents; restrict audit-log access. Record system-initiated calls with a service actor. Set a separate retention policy for CloudTrail/provider-managed security logs.
- [ ] Store searchable application audit events in an append-only PostgreSQL table and transactionally couple management changes with their audit records. For external calls, durably record the attempt before dispatch and append the outcome; do not dispatch if the attempt cannot be recorded. Export events through a transactional outbox to a versioned S3 archive in a separate AWS account. Use unique object keys and least-privilege create-only access; keep delete controls outside the application account. Expire database records and all current/noncurrent S3 object versions after 30 days; test deletion and alert on export failures or backlog. Use CloudTrail to record archive configuration and scoped object access. Versioning and CloudTrail improve recovery and detection but are not immutable storage; do not claim tamper-proof audit retention until Object Lock is configured and verified. The separate archive account is not another hosted application environment.
- [ ] Implement guest, normal, and premium access: guests get one successful browser-local export per rolling 24-hour period; normal users can continue editing locally; premium users can additionally submit URLs to the authenticated server-side downloader. Enforce downloader entitlement and quotas on the server. Keep admin role distinct from plan; browser-only editing feature gates remain best-effort.
- [ ] Keep the data model ready for future organization workspaces for backend-managed account and entitlement records. Do not persist browser-local projects or media assets in the backend database in beta. Users still get personal accounts and management workspaces.
- [ ] Build the protected admin panel for account management, time-limited premium entitlement grants/revocations, feature flags, session revocation, per-user browser-local limits, and per-user server-enforced downloader size limits and quotas. Audit privileged changes, including downloader-limit changes. Clearly label browser-only limits as best-effort/device-local and downloader limits as server-enforced.
- [ ] Test manual premium grants, extensions, expiry, and revocation; confirm every change is audited, expired/revoked accounts cannot start new downloader requests, and define whether revocation terminates an already-active stream.
- [ ] Enforce authentication and admin permissions on management APIs and server-side authorization on every downloader request. Do not treat client-side plan checks or feature flags as a security boundary. Do not expose backend editing, transcoding, or export endpoints.
- [ ] Port existing trim, audio extraction, compression, GIF, and stitch workflows to browser processing. Show progress/cancel/error status locally; do not queue these client-side edits as backend jobs.
- [ ] Keep media inspection and editing in the browser where supported. Preserve supported page-link inspection and route actual URL downloads through the authenticated downloader only; do not add backend media editing, transcoding, or export processing.
- [ ] Prefer stream-copy/remux for compatible operations; benchmark re-encoding, compression, resizing, GIF, and frame-accurate trimming on representative devices and files to set reliable client-side limits and fallbacks.
- [ ] Apply the seven-day beta expiry to app-managed browser workspace data and project metadata, not to the user's original files or exports saved outside VideoManager. Explain that browser storage may be cleared or evicted sooner and that downloaded files cannot be deleted by the app.
- [ ] Add a **My Account** section showing the current browser's managed videos/projects, each app-managed item's time remaining, and the count expiring within the next seven days. State that the local list and its quota usage are device-specific; do not send expiry-warning emails in beta.
- [ ] Add account data export/deletion, user feedback and actionable failures, and privacy-conscious management/security metrics. Keep browser media-task history local. Explain that account deletion cannot remotely erase browser-local files on devices that are not currently available.
- [ ] Verify feature parity for every retained operation across the documented browser/device/codec matrix: single, batch, and playlist downloads; supported page-link inspection; local library/playback and paired QR playback; trim, audio extraction, compression, GIF creation, stitch, and progress/error feedback.
- [ ] Verify browser media processing with frontend tests and representative browser/device tests, including memory pressure, interrupted work, local storage eviction, source relinking, expiry cleanup, and output validation. Test that the official app allows one successful guest export in a rolling 24-hour window, blocks additional imports/edits/exports until the server-calculated window expires, failed/cancelled exports do not consume the allowance, and sign-up restores full account access. Confirm the result remains downloadable and guests cannot invoke the downloader. Also test downloader authorization, the 100 MB default and audited per-user size overrides (including rejection above the platform ceiling), source and response limits, bounded-memory streaming, slow-client backpressure, cancellation, disconnect handling, retry behavior, response integrity, that downloads at the configured size limit can be imported for editing, SSRF defenses, quotas, Tor/VPN fail-closed behavior, and confirm source requests cannot fall back to direct egress.
- [ ] Document local PostgreSQL startup, service initialization, test fixtures, and cleanup so developers can reproduce the local environment.

### Phase 0B beta scope

The beta begins only after Phase 0A prototype acceptance, Phase 0B decisions and launch gates are complete, and production deployment is verified. Guests may complete one validated browser-local export per rolling 24-hour period; after each export, prompt for account creation/sign-in and block further imports, edits, and exports until the next window begins or the visitor authenticates. The completed result remains available for download. A minimal server-backed anonymous ID and server timestamps track the guest allowance without uploading media or project data. The URL downloader always requires an authenticated premium account. During beta, admins manually grant time-limited premium access; payments and self-service subscriptions are deferred. Preserve the current supported workflows: single, batch, and playlist downloads; supported page-link inspection; local library/playback and QR-based local-network playback; trim, audio extraction, compression, GIF creation, stitch, and progress feedback. Edit, process, and export user-selected media entirely in the browser. Premium users submit supported remote URLs to the authenticated backend; an isolated downloader fetches through configured Tor/VPN egress and streams directly to the user without storing media. Set the downloader's server-enforced default to 100 MB per video, with audited per-user admin overrides up to the tested platform ceiling. Other third-party API integrations are called from the backend and recorded in the audit log. No editing, transcoding, or export jobs run on the backend. Admins manage accounts, entitlements, flags, audit records, best-effort local editing limits, and server-enforced downloader limits. The multi-clip timeline editor remains Phase 1. Expiry is shown in the current browser's My Account section; automated warning emails are deferred.

### Final Phase 0B step — Deploy the tested product

- [ ] **Deployment target:** AWS Mumbai (`ap-south-1`) using pay-as-you-go for beta; confirm service availability and applicable data-protection obligations. Avoid long-term commitments until usage is measured.
- [ ] Before inviting beta users, set a conservative initial monthly spend limit and configure AWS Budgets/billing alerts. Defer detailed low/expected/high usage projections and capacity optimization until live usage data is available; do not make long-term commitments meanwhile.
- [ ] Deploy the frontend as a static site on S3 behind CloudFront, retain the separate versioned S3 audit archive, and run the management API on ECS/Fargate with managed PostgreSQL on RDS. Deploy an isolated downloader service that streams remote media through the authenticated backend response using bounded-memory chunks and backpressure; do not provision an SQS queue or S3 bucket for downloader media. Abort upstream work when the client disconnects and enforce tested request, size, duration, and concurrency limits. Do not provision editing, transcoding, or export workers.
- [ ] Enforce seven-day expiry in browser-managed workspace data and local project metadata, running cleanup when the app is opened and while it remains active. Browser-only cleanup cannot run reliably while the app is closed, and browser storage may be cleared or evicted sooner; do not imply that the app can delete source/export files saved elsewhere on the device.
- [ ] Keep account, entitlement, feature-flag, quota configuration, and audit events in the cloud database. Pass source URLs only to the isolated downloader in memory; redact them from access, application, and error logs. Do not persist downloaded media. Since no completed artifact is stored, the earlier one-hour artifact-access window does not apply; choose and document finite retention for minimal downloader request metadata before beta. Do not store user-selected source files, project timelines, thumbnails, per-video local workspace lists, or editing-task history in the backend.
- [ ] Configure TLS, secrets, least-privilege IAM/database credentials, connection pooling, health checks, logs, metrics, and alerts. Store provider credentials only in the backend secret manager.
- [ ] Establish PostgreSQL backups and retention, and successfully test a restore plus SQLite-to-PostgreSQL migration/rollback before cutover. Formal measurement of the provisional RTO/RPO targets and Multi-AZ failover performance is deferred until after launch.
- [ ] Maintain one hosted production environment only; do not provision staging. Use local PostgreSQL and test fixtures for pre-release verification, and synthetic test records for brief production smoke tests. Keep production credentials and data out of local development.
- [ ] Set up GitHub Actions for builds, tests, security checks, and container publishing. Initially deploy each approved release directly to all production traffic in one stage, without canary or blue/green rollout. Require all checks and explicit approval; verify deployment health and run smoke tests, with documented rollback/recovery and backward-compatible migrations. Record the increased release risk until staged rollout is added.
- [ ] After launch, measure real API usage, active-stream concurrency, downloaded bytes, and Tor/VPN/network costs; then tune pay-as-you-go capacity and build a low/expected/high cost model.
- [ ] Validate production accounts/admin controls, manual premium grant/expiry/revocation and audit behavior, browser-local editing, premium downloader authorization and quotas, source-visible egress IP for each egress mode, fail-closed Tor/VPN behavior, bounded-memory stream integrity, slow-client backpressure, cancellation and disconnect behavior, retry limits, that downloads at the configured cap remain editable in the browser, server-mediated third-party calls and corresponding audit events, redaction/access controls for audit logs, the tested local import limit, seven-day local expiry UI, monitoring, billing alerts, backup restore, and rollback before opening beta registration.

**Done when:** Phase 0A has been tested and accepted by the user; Phase 0B decisions are resolved, and the beta preserves the supported current user-facing operations—downloads, page-link inspection, local library/playback including paired QR playback, editing tools, and progress feedback—alongside accounts, entitlements, and admin controls. Editing files, projects, and exports remain in the browser; only explicitly submitted URLs and streamed download responses pass through the backend. Supported browser/device/codec combinations and source limitations are documented and tested. The timeline editor is explicitly Phase 1. Phase 0B is complete only after local/CI verification and production smoke tests confirm server-side management/downloader access controls, browser-local import guidance, enforced downloader quotas, correct egress for each mode with no direct fallback from Tor/VPN, bounded-memory streaming and disconnect behavior, seven-day local expiry visibility, budget alerts, and verified backup/restore and rollback procedures.

### Initial access matrix

| Account access | Browser-local editing | Server-side URL downloader | Admin panel |
|---|---:|---:|---:|
| Guest with allowance available | Yes, for one successful export per rolling 24 hours | No | No |
| Normal user | Yes | No | No |
| Premium user | Yes | Yes | No |
| Administrator | According to their assigned plan | According to their assigned plan | Yes |

Feature flags can configure client-side capabilities, but browser code and local processing can be modified by users; client-side feature gates are not tamper-proof access control. The anonymous guest ID discourages casual repeat use but cannot guarantee one export per person per day or prevent a visitor from altering the browser app. Do not use this gate as a security, billing, or identity boundary. Admin privileges are separate from premium access. Premium access can initially be assigned by an administrator; subscription and payment integration can be planned separately.

### Browser-local import limits

Per-account import settings in the admin panel remain a permanent product control, but for local browser editing they are client-side policy/UX settings, not hard security or storage quotas. Signed-in users receive their account settings; guests receive the global defaults. These settings apply in the current browser and do not represent authoritative usage across devices. The anonymous guest-export record is separate from the local import limits. Global defaults and platform-wide guidance may change as device compatibility is measured.

| Limit | Public beta default | Admin control and limitation |
|---|---|---|
| Maximum size per imported video | **100 MB per file** | Configure a per-account client-side limit; browser/device capability may impose a lower practical limit |
| Simultaneous imports | One at a time per browser | Configure a per-account client-side allowance; it is not coordinated across devices |
| Videos in app-managed browser workspace | Configurable default maximum | Configure a per-account client-side maximum; only the current browser can report its local count |

The browser's 100 MB limit is per locally imported file, not a total account-storage allowance. It is a client-side setting and may be changed per account as best-effort guidance; check it before processing and handle browser/device storage limits even if the configured limit is higher. Separately, the downloader starts with a 100 MB per-video server-enforced limit; an administrator may set an audited per-user override up to the benchmarked platform ceiling. Downloader duration, concurrency, and usage limits are also server-enforced. In **My Account**, show the configured browser-local settings and clearly label local video count/expiry as applying to this browser only. Never claim browser-local limits are centrally enforced. Keep seven-day app-managed browser-data expiry separate from import settings.

## Deployment decisions recorded

These are the current planning assumptions from the deployment discussion, not a final bill or a claim that the infrastructure has already been provisioned.

| Area | Starting decision |
|---|---|
| Cloud and region | AWS, Mumbai (`ap-south-1`), selected for beta; sovereignty is not a selection requirement. Serve the site globally and confirm service availability and applicable data-protection obligations before launch |
| Availability and recovery | Provisional, unvalidated targets: 99.9% monthly availability, 4-hour RTO, and 15-minute RPO for backend services and data. Design for Multi-AZ availability in Mumbai; measure these targets after launch and do not claim them as an SLA before validation. Regional failover is deferred; a region-wide outage may exceed the availability target until a disaster-recovery strategy is selected |
| Pricing approach | Pay-as-you-go during beta; avoid long-term compute commitments until real usage and cost are measured |
| Frontend | Static React build on S3, delivered through CloudFront |
| API | Containerized FastAPI management service on Amazon ECS with AWS Fargate; authenticated URL-download endpoint only for remote media acquisition |
| Other external API integrations | Backend-only, provider-specific allowlisted calls linked to an actor and a protected audit event; no direct browser-to-provider API calls |
| Editing, processing, and export | Run in the user's browser/device; do not provision editing/transcoding/export workers |
| URL downloader | Authenticated API validates and authorizes supported single, batch, playlist, and page-inspection requests; an isolated downloader fetches via configured Tor/VPN egress and streams media through the backend to the user with no persistent media copy |
| Local library and QR playback | Keep library media and metadata on-device; QR playback is an explicit, access-controlled local-network pairing flow and never uploads media to VideoManager |
| Database | Managed PostgreSQL on Amazon RDS |
| Media data | User-selected files, projects, and exports remain in the browser. Source URLs are passed only to the downloader in memory and redacted from logs; downloaded media is streamed to the user and not persisted by VideoManager |
| Delivery | Deliver the application globally through CloudFront; keep the API and downloader in the initial region and do not use a CDN to distribute user editing media in beta |
| Environments | One hosted production environment only; no staging environment. Local development and tests use synthetic data and separate credentials |
| Local development | Phase 0A uses Docker PostgreSQL and the already-pulled LocalStack image for AWS API integration tests as needed; run frontend/API/downloader locally and keep editing media on the test device. LocalStack does not replace managed RDS/ECS/CloudFront validation in Phase 0B |
| CI/CD | GitHub Actions for builds, tests, security checks, and container publishing; require passing checks and approval before deploying directly to the single production environment |

### Lean beta deployment recommendation

Keep AWS as the planned launch platform. Choose enough initial downloader capacity to accept and sustain tested long-lived streams; defer cost-driven scale-to-zero tuning until after live behavior is measured.

- Use Multi-AZ RDS and deploy the API across availability zones. Test backup restoration before beta; measure failover and the provisional RTO/RPO targets after launch.
- Regional disaster recovery is deferred. Document the regional-outage risk and do not claim the 99.9% target is protected against a Mumbai-wide outage until a cross-region recovery strategy is selected and tested.
- Keep S3 for static website assets (delivered through CloudFront) and the separate versioned audit archive. Do not provision SQS or temporary S3 storage for downloader media; direct streaming has no completed artifact to retrieve or expire.
- Provision no staging resources. Run pre-deployment checks locally/in CI and limit production smoke tests to synthetic records and non-destructive checks.
- Start with one application region and use the CDN for global delivery of static assets. Measure API and download latency from target regions; add regions only if usage justifies the cost and operational complexity.
- Do not weaken the downloader's no-IP-leak protections to reduce cost: selected Tor/VPN egress must continue to fail closed, with no direct-egress fallback.

### Cloud provider comparison (reviewed 17 November 2026)

The product must be accessible worldwide, but sovereign-cloud hosting is not a requirement. AWS Mumbai is selected for beta; this provider comparison is background reference, and detailed cost comparisons are deferred until after launch. Start with one application region and global static-asset delivery. The workload is an always-available, low-volume management API and PostgreSQL database plus potentially long-lived direct-streaming URL downloads. Editing and exports stay in the browser. The downloader's controlled egress, streaming reliability, and delivery of downloaded media matter more than video-processing compute. Prices below are historical public USD list-price anchors, before tax, VPN/Tor provider charges, and any unpriced networking or logging; they are not a current budget or equivalent full-stack quotes.

| Provider | Relevant regional capabilities | Published price anchors and trade-offs |
|---|---|---|
| AWS | Mumbai (`ap-south-1`); ECS/Fargate, RDS PostgreSQL, S3, CloudFront, IAM, Secrets Manager, and CloudTrail fit the planned architecture. Validate long-lived streaming, connection timeouts, and downloader scaling in the proof of concept. | The earlier **$180–$250/month** estimate included production and modest staging and does not apply to the single-environment plan. The **$12** Lightsail compute, **$30** managed database, and roughly **$54** subtotal including a second instance are historical anchors only; they omit static delivery, snapshots, logs, VPN/Tor, and overage. Defer a current all-in estimate until post-launch usage is measured; retain the pre-beta spend limit and billing alerts. |
| Google Cloud | Mumbai (`asia-south1`); Cloud Run services and Jobs, Cloud SQL for PostgreSQL, Cloud Storage, IAM, Secret Manager, and Cloud Audit Logs. Cloud Run Jobs can run for up to seven days; services and jobs can scale to zero. Direct VPC egress avoids the extra VM charge of a Serverless VPC Access connector. | Cloud Run has a monthly free usage grant for small workloads. Cloud SQL remains an always-on cost: its published compute rates include **$0.0413/vCPU-hour** and **$0.007/GiB-hour** in the displayed pricing table; a 1-vCPU/3.75-GiB example is about **$49/month for compute** before storage, backups, networking, and Mumbai-specific price verification. A VPN/Tor egress gateway and data transfer still need costing. This is the strongest scale-to-zero alternative to benchmark, not a confirmed lower all-in quote. |
| Microsoft Azure | India Central and other India regions; Container Apps can scale to zero and run jobs, while Azure Database for PostgreSQL Flexible Server provides managed PostgreSQL, backups, and stop/start for non-production cost control. Azure also provides managed identity, Key Vault, and activity/audit logs. | Container Apps has monthly free grants and no replica usage charge at zero. PostgreSQL Flexible Server has a Burstable 1-vCore/2-GiB option, but the public pricing page requires calculator inputs for a dependable regional price. Database storage/backups and the controlled egress path remain billable. Strong capability fit, but no evidence yet that it beats AWS or Google on total beta cost. |
| DigitalOcean | Bangalore (`blr1`) supports Droplets and Managed PostgreSQL. App Platform supports static sites, container services, and scheduled/deployment jobs; Droplets allow a custom Linux VPN/Tor gateway and firewall rules. | A 2-vCPU/4-GiB Droplet is **$24/month** with 4,000 GiB listed transfer. A 2-GiB Managed PostgreSQL node is **$30.45/month**, with storage billed separately (the displayed minimum is 30 GiB at $0.215/GiB-month). That is about **$61/month** for one app Droplet plus the minimum database storage; a separate 1-vCPU/2-GiB worker Droplet adds **$12/month**. Static App Platform sites are free, but its documented jobs are deployment-time or scheduled rather than a native on-demand job runner. Lower and more predictable VM pricing, but more networking/host operations and fewer enterprise control-plane capabilities than the hyperscalers. |
| Oracle Cloud Infrastructure (OCI) | Mumbai (`ap-mumbai-1`); Compute, private-network-only OCI Database with PostgreSQL, automated backups (up to 35 days), IAM policies, logging, and metrics are available. | OCI has a capable managed PostgreSQL offering, but the public price-list content did not yield a verifiable Mumbai small-beta total in this review. Treat OCI as a pricing-calculator candidate, not a proven cheapest option. It adds a distinct operational ecosystem and should pass the same egress and recovery tests before selection. |

**Recommendation:** AWS remains selected for beta. Keep the pre-launch proof of concept focused on isolated worker networking, DNS/tunnel fail-closed behavior, private database access, slow-client backpressure, and disconnect/retry behavior. Revisit provider and price comparisons only after live usage provides evidence that cost, latency, or capability justifies a change.

**Pricing sources:** [AWS Fargate](https://aws.amazon.com/fargate/pricing/), [Amazon RDS for PostgreSQL](https://aws.amazon.com/rds/postgresql/pricing/), [Amazon Lightsail](https://aws.amazon.com/lightsail/pricing/); [Cloud Run](https://cloud.google.com/run/pricing), [Cloud Run Jobs](https://cloud.google.com/run/docs/execute/jobs), [Cloud Run VPC egress](https://cloud.google.com/run/docs/configuring/connecting-vpc), [Cloud SQL](https://cloud.google.com/sql/pricing); [Azure Container Apps](https://azure.microsoft.com/en-us/pricing/details/container-apps/), [Azure Database for PostgreSQL](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/); [DigitalOcean Droplets](https://www.digitalocean.com/pricing/droplets), [Managed Databases](https://www.digitalocean.com/pricing/managed-databases), [regional availability](https://docs.digitalocean.com/platform/regional-availability/), [App Platform jobs](https://docs.digitalocean.com/products/app-platform/how-to/manage-jobs/); [OCI Database with PostgreSQL](https://docs.oracle.com/en-us/iaas/Content/postgresql/overview.htm), [OCI regions](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm), [OCI price list](https://www.oracle.com/cloud/price-list/).

### Post-launch reliability and cost review (deferred)

- The earlier **USD $150–$350/month** estimate assumed server-side media storage and processing; it is obsolete and must not be used as a current estimate.
- After launch, compare the provisional 99.9% availability, 4-hour RTO, and 15-minute RPO targets against measured API/download availability, restore results, and Multi-AZ failover behavior. Decide whether to retain or revise the targets; regional failover remains a separate decision.
- Measure actual downloader volume, stream duration/concurrency, network and video egress, Tor/VPN charges, and idle service/database costs. Recalculate AWS Mumbai costs for the API/database, downloader, audit archive, S3/CloudFront website delivery, logs, backups, and networking; tune capacity based on observed demand.
- Use live operational and cost data to set beta exit criteria and decide whether to scale, limit, or change the service. Until this review, keep a conservative initial spend limit and AWS billing alerts in place. Browser limits are device-local and best-effort; do not treat them as authoritative account-wide usage controls.

## Later — Billing and service operations

These features can follow the core account, editing, and access-control workflows.

- [ ] Replace one-stage production releases with canary or blue/green rollout and health-based automatic rollback when operational maturity and budget allow.
- [ ] If a future, explicitly approved cloud-media/sync mode is added, offer optional expiry reminder emails for server-tracked assets. Browser-local beta files cannot be reliably monitored or emailed about from the server.
- [ ] Integrate subscriptions and payments for premium plans, including plan changes, renewals, cancellations, payment failures, and billing history. Clearly distinguish server-enforced downloader entitlement from best-effort premium feature gates for browser-only functionality.
- [ ] Define how premium entitlements change when a subscription expires or is cancelled, without deleting a user's projects or source media unexpectedly.
- [ ] Back up organization/cloud project data and configuration, document recovery procedures, and offer users a portable way to export projects and their media. Browser-local beta projects are not server-backed up; users keep their own copies.
- [ ] Define retention, restore, and deletion policies for backups and user media; test recovery rather than relying on backups alone.
- [ ] Obtain privacy/legal approval for the one-month audit-event retention and deletion policy before beta. Object Lock remains deferred; if adopted later, select its mode/retention with privacy/legal approval, test privileged-bypass and recovery behavior, and only then describe the archive as immutable or tamper-evident.

## Phase 1 — Timeline editor MVP

**Goal:** let users make a complete short edit from files they select locally, entirely in their browser/device.

- [ ] Provide a direct "Open video" or "Import video" action using the browser's local file picker; do not upload file contents to the backend.
- [ ] Create, rename, save, duplicate, and reopen browser-local editing projects. Keep project manifests and optional source copies on-device; support relinking when browser permissions or retained files are unavailable.
- [ ] Add a multi-clip timeline with reorder, trim handles, split-at-playhead, delete, and ripple delete.
- [ ] Provide a preview player with frame/time seeking, fit-to-view, and keyboard shortcuts for play, pause, split, and undo/redo.
- [ ] Support a primary video track and an independent audio track; start with clip-level mute and volume.
- [ ] Add non-destructive undo/redo and autosave.
- [ ] Export a timeline to a browser-supported format with progress, cancellation, and a user-selected download destination; report codec support before export.

**Success measure:** a user can open local videos, assemble and export a multi-clip edit without uploading user-selected source files to the backend, then reopen the project in the same browser/device if its local project data and source access remain available. Remote URL downloads use the separate authenticated downloader exception.

## Phase 2 — Transform and convert

**Goal:** cover common format and framing needs in the same browser-local project/export flow.

- [ ] Add explicit output container and codec choices based on actual browser/WebCodecs/FFmpeg.wasm capability detection; offer a compatible fallback or explain unsupported combinations.
- [ ] Offer export presets for resolution, frame rate, quality/bitrate, and audio codec/bitrate, with an estimated output size where feasible.
- [ ] Add crop, resize, rotate/flip, aspect-ratio presets, and letterbox/fill behavior.
- [ ] Add clip speed changes and audio gain, mute, and simple fade-in/fade-out.
- [ ] Preserve source audio/video streams when browser-side remux/stream-copy is safe; explain when re-encoding is required and its device resource cost.

**Success measure:** users can convert a file or export an edited timeline with predictable, validated format settings.

## Phase 3 — Titles, subtitles, and effects

**Goal:** support the most common finishing touches with clear previews.

- [ ] Add text/title overlays with position, font, color, size, and timing controls.
- [ ] Import and style SRT subtitles; support subtitle burn-in and selectable subtitle tracks when the target format allows it.
- [ ] Add basic transitions (cut, crossfade, fade to/from black) and per-clip opacity.
- [ ] Add a small set of understandable color controls (exposure, contrast, saturation, temperature) with reset and before/after preview.
- [ ] Make effect rendering consistent between editor preview and final export.

**Success measure:** titles, subtitles, transitions, and basic corrections render in the expected position and time range in the exported file.

## Phase 4 — Pro workflow

**Goal:** make editing repeatable and efficient for frequent users.

- [ ] Add reusable export presets and batch conversion/export from the library.
- [ ] Optimize the browser media pipeline using WebCodecs where supported and FFmpeg.wasm where needed; maintain capability detection, memory limits, cancellation, and clear fallback behavior.
- [ ] Add project asset relinking, missing-file warnings, and a portable project package option.
- [ ] Add proxy/low-resolution preview media for smooth editing on large source files.
- [ ] Add timeline zoom, snapping, markers, clip grouping, and multi-track audio/video.
- [ ] Add searchable project/library tags and keyboard-shortcut customization.
- [ ] Add local history and cleanup controls for browser editing tasks. Keep only minimal downloader request status and quota data on the backend; redact source URLs from logs, define finite request-metadata retention before beta, and clean up records accordingly. Do not retain downloaded media.

**Success measure:** users can work on larger projects without excessive preview lag and can export a portable project package with its media for transfer to another device.

## Future scope — Organization SaaS / Enterprise

The long-term product direction includes SaaS workspaces for organizations, not only individual user accounts. Build management capabilities after the individual editing product is proven; the early ownership model should make this expansion possible without weakening tenant isolation. Browser-local projects cannot be shared with a team by themselves. Shared media or centralized processing would require an explicit future change to the media-local policy and a separately designed, opt-in cloud-media mode.

### Organizations and collaboration

- [ ] Let customers create organizations and shared workspaces, invite members, and manage membership lifecycle.
- [ ] Support personal and organization-owned projects and media, with explicit ownership and sharing rules. Do not allow cross-organization access.
- [ ] Add organization roles such as owner, administrator, editor, and viewer, with least-privilege permissions for projects, assets, exports, billing, and settings.
- [ ] Add shared project workflows such as comments, review links, approval states, and version history before considering real-time co-editing.
- [ ] Provide organization-level administration, member offboarding, ownership transfer, and recovery when the only organization owner leaves.

### Identity, plans, and administration

- [ ] Add organization-level plans and billing, including seat counts, usage allowances, invoices, renewals, and cancellation behavior.
- [ ] Support business identity integrations such as SAML/OIDC single sign-on, domain verification, and optional enforced SSO.
- [ ] Add SCIM or equivalent automated user provisioning/deprovisioning for customers who need centralized identity lifecycle management.
- [ ] Add MFA, mandatory for platform and organization administrators and available to users, with tested enrollment, recovery, factor reset, and step-up authentication for sensitive actions.
- [ ] Allow organization admins to configure allowed features and management policies within platform-wide limits. Any shared-media, download, upload/export, or centralized-retention controls require a separately approved cloud-media architecture.
- [ ] Keep platform administrators separate from customer organization administrators; audit privileged actions and make logs available to the appropriate customer admins.

### Security, governance, and service commitments

- [ ] Define tenant-isolation controls for database records, object-storage paths and permissions, processing jobs, logs, and support tooling; test attempts to cross tenant boundaries.
- [ ] Offer organization-configurable retention and deletion policies, exportable audit logs, data export, and documented offboarding/deletion behavior.
- [ ] Evaluate customer requirements for data residency, encryption/key management, security questionnaires, penetration testing, incident response, and compliance certifications. Make no compliance or SLA claims until independently verified and operationally supported.
- [ ] Define service availability goals, support response expectations, incident communication, backup/recovery objectives, and an operational status page before offering enterprise contracts.
- [ ] Add organization-level usage, storage, processing, and cost reports so customers can understand and administer their consumption.

**Enterprise readiness gate:** organization membership and authorization must be enforced server-side across management APIs and any explicitly approved future cloud-media services; tenant isolation, offboarding, auditability, support operations, and any published service/security commitments must be tested and documented before selling organization plans. Shared media or centralized processing would require an explicit change to the browser-local-only media policy.

## Later — Optional smart features

These should follow a solid manual editing experience and be opt-in, especially where media leaves the local machine.

- [ ] On-device speech-to-text for subtitle drafts, with editable text and timing. Remote transcription is outside this architecture unless separately approved.
- [ ] Scene/quiet-section detection and suggested cut points that users review and apply themselves.
- [ ] Optional background removal, denoise, stabilization, and smart reframing, subject to hardware and model availability.
- [ ] Keep smart-media features local to the browser/device. Any proposal for remote processing must first change the media-local-only policy and clearly disclose the transfer.

## Product and reliability guardrails

- Keep editing non-destructive: source files are inputs, and exports are separate outputs.
- The backend is for management, the explicitly requested URL-download operation, and approved third-party API integrations. Never upload user-selected source files, decoded frames, project timelines, thumbnails, or browser-generated exports. Pass remote source URLs only in memory to the authenticated downloader; redact them from logs and do not persist them. The downloader backend necessarily sees the user's incoming connection IP; configured egress hides that IP from the media source, not from VideoManager or its hosting/network providers. Do not promise anonymity. Any third-party integration that processes media, or any other cloud media storage, sync, collaboration, or remote processing, requires explicit approval and user disclosure.
- Keep account/plan and admin configuration separate from browser-local media metadata. Avoid collecting filenames, local paths, or detailed editing activity.
- Enforce authentication, authorization, account ownership, and plan entitlements on the server; hiding a UI control is never an access-control boundary.
- Gate the official guest experience to one successful local export per rolling 24-hour period using a minimal server-backed anonymous ID and server timestamps. After each export, prompt for account creation/sign-in and block further editing until the next window begins or the visitor authenticates. The browser remains modifiable, so this is not a hard anti-abuse or security boundary. Do not upload local media or use IP addresses or browser fingerprinting as guest identity; keep the downloader account- and premium-only.
- Treat feature flags as global capability controls, not a replacement for authentication or per-user authorization; protect administrative settings and sensitive APIs independently.
- Send all provider API requests through authenticated, allowlisted backend integrations and record actor-linked audit events. Do not embed third-party credentials in the browser or expose a generic outbound proxy.
- Keep editing, processing, and export in the browser. The sole remote-media exception is a user-initiated supported URL download through the authenticated downloader with controlled Tor/VPN egress; never silently switch between direct and proxied fetches. Keep QR playback local, explicitly paired, and access-controlled.
- Validate media and export settings before starting long jobs; never report success until the output is verified.
- Keep the UI usable while jobs run, and expose progress, cancellation, and actionable failures.
- Test generated media with FFprobe and representative playback checks; include odd aspect ratios, variable frame rates, missing audio, and long files.
- Document supported codecs and URL-import sources based on runtime browser capability, CORS behavior, and the bundled FFmpeg.wasm build.

## Not in the initial scope

- Replacing a full professional nonlinear editor with advanced compositing or a plugin marketplace.
- Cloud upload/storage as a prerequisite for editing; the initial upload and editing workflow should work locally.
- Automatic or AI-generated edits that alter a project without user review.

Real-time multi-user collaboration is deferred; organization workspaces, sharing, review, and approval workflows are future scope described above.

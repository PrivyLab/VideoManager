# VideoManager Roadmap

VideoManager should let people upload videos they own and then edit them in the same place. Uploading a file—not finding or downloading a video online—is the primary entry point for the editing experience. Keep the existing download and library features, but make major capabilities independently configurable so an administrator can enable or disable them without removing code. Accounts have normal and premium plans; administrators manage users and feature availability.

This roadmap is directional: phases describe dependencies and intended outcomes, not release dates. Priorities favor a useful, reliable local editor before optional AI or collaboration features.

## Current capabilities

- Download single videos, batches, and playlists; inspect pages for video links.
- Organize and play the local video library, including QR-based playback on a local network.
- Trim a clip, extract audio, compress video, create a GIF, and stitch clips.
- Track downloads and processing through the existing dashboard and background progress updates.

The current product does not yet provide a video upload workflow. Its media tools operate on videos already in the library and create one output at a time. There is not yet a persistent editing project, multi-clip timeline, general-purpose format-conversion workflow, or export queue.

## Roadmap at a glance

| Phase | Focus | Outcome |
|---|---|---|
| 0 | Local product foundation, then deployment | Build and test PostgreSQL-backed accounts, uploads, existing editing tools, and admin locally; deploy the beta to AWS Mumbai as the final step |
| 1 | Timeline editor MVP | Open uploaded videos, assemble, trim, preview, and export edits |
| 2 | Transform and convert | Common formats, framing, speed, and audio controls |
| 3 | Titles, subtitles, and effects | Add presentational polish without leaving the editor |
| 4 | Pro workflow | Reusable presets, batch jobs, project portability, and advanced controls |
| Future | Organization SaaS / Enterprise | Shared workspaces, organization administration, identity integrations, and governance |
| Later | Optional smart features | Opt-in transcription, assisted edits, and collaboration after core editing is stable |

## Phase 0 — Local foundation, then production deployment

**Goal:** build and test the multi-user editing product locally first. Treat deployment as the final part of Phase 0, after the local product and its behavior are verified.

### Build and test locally

- [ ] Run PostgreSQL locally for development and tests; replace SQLite in the application data layer before adding accounts, ownership, projects, or other multi-user features.
- [ ] Introduce versioned schema migrations and a PostgreSQL-compatible data-access layer. Plan and test migration of existing SQLite metadata; back up data, validate records and relationships, and document recovery before cutover.
- [ ] Use LocalStack for local AWS-service development, initially emulating S3 for uploaded media and generated files and SQS for processing jobs. Keep LocalStack state local and disposable; never use production credentials or data locally.
- [ ] Configure the application to switch between LocalStack endpoints and real AWS through environment-based configuration while keeping the same S3/SQS integration paths. Keep video blobs out of PostgreSQL.
- [ ] Implement and test browser uploads locally against LocalStack S3, including large-file/multipart behavior, file/type validation, metadata probing, quota checks, and interrupted uploads.
- [ ] Enforce configurable maximum file size, one simultaneous upload per user by default for beta, and per-user video-count limits. Test that backend checks prevent bypassing browser controls.
- [ ] Build authentication, sign-in/sign-out, account recovery, email verification, optional MFA, and session review/revocation.
- [ ] Implement server-side authorization and ownership checks for media, projects, exports, and jobs. Add tests that prove users cannot access one another's resources.
- [ ] Implement normal and premium entitlements: normal users can upload/edit; premium users can additionally use the downloader. Keep admin role distinct from plan.
- [ ] Keep the data model ready for future organization workspaces: represent ownership and access through a clear personal-workspace/organization boundary, and avoid assuming every asset or project is owned directly by a single user. Users still get personal accounts and workspaces in beta.
- [ ] Build the protected admin panel for account management, plan assignments, feature flags, session revocation, and permanent per-user upload quotas. Record audited changes; lowering quotas must not delete existing assets.
- [ ] Enforce feature flags, entitlements, upload limits, rate limits, and processing limits on backend/API/job paths, not only in the UI.
- [ ] Implement local queued FFmpeg workers with progress, cancellation, retries, safe temporary storage, per-user/global concurrency limits, backpressure, and cleanup. Start with one active processing job per user and a conservative global cap.
- [ ] Prefer stream-copy/remux for compatible operations; benchmark re-encoding, compression, resizing, GIF, and frame-accurate trimming on representative media to tune size/duration and resource limits.
- [ ] Implement the seven-day beta expiry policy locally: display expiry, support explicit export download and deletion, and clean expired records/files idempotently without interrupting active jobs.
- [ ] Add a **My Account** section to the website. In that section, list the user's uploaded videos and show the exact time remaining until each video is deleted, plus a count of videos expiring within the next seven days. Do not send expiry-warning emails in beta.
- [ ] Add account data export/deletion, user feedback and actionable failures, and privacy-conscious admin usage/job metrics.
- [ ] Verify all behavior with backend/frontend tests, including PostgreSQL migrations, concurrent requests, media ownership, quota enforcement, expiration cleanup, and FFmpeg output validation.
- [ ] Document LocalStack startup, service initialization, test fixtures, and cleanup so developers can reproduce the local environment.

### Phase 0 beta scope

The beta begins when Phase 0 is complete and deployed. It makes the existing library and media-processing tools available under the configured feature flags and account entitlements: normal users can upload and use editing tools; premium users can also use the existing downloader; admins manage access and quotas. The new multi-clip timeline editor remains Phase 1 and is not a prerequisite for the Phase 0 beta. Expiry is communicated in the product UI only; automated warning emails are deferred.

### Final Phase 0 step — Deploy the tested product

- [ ] **Deployment target:** AWS Mumbai (`ap-south-1`) using pay-as-you-go for beta; confirm service availability and data-residency requirements. Avoid long-term commitments until usage is measured.
- [ ] Document and cost the AWS architecture before provisioning. Estimate small-beta, expected-growth, and high-usage scenarios in the AWS Pricing Calculator, including taxes and contingency.
- [ ] Deploy the frontend as a static site through S3/CloudFront; run the containerized FastAPI service on ECS/Fargate; use managed PostgreSQL on RDS; store media in private S3; and use a durable queue such as SQS for isolated FFmpeg worker tasks. Lambda is for short event-driven tasks, not full exports.
- [ ] Use short-lived scoped authorization for browser-to-S3 multipart uploads. Verify completed uploads in the API and enforce quotas both before upload authorization and at completion.
- [ ] Configure seven-day expiry for uploads, projects, exports, and previews. Run monitored cleanup for objects and database records; use S3 lifecycle expiration as a backstop and clean abandoned multipart uploads.
- [ ] Decide and secure worker access to S3 and temporary storage. Enforce resource/disk limits and ensure active jobs finish or cancel safely before expiry cleanup removes their inputs.
- [ ] Configure TLS, secrets, least-privilege IAM/database credentials, connection pooling, health checks, logs, metrics, and alerts. Set AWS Budgets and billing alerts before inviting beta users.
- [ ] Establish PostgreSQL backups, retention, restore drills, and recovery objectives. Validate SQLite-to-PostgreSQL migration and rollback against a backup before cutover.
- [ ] Create isolated staging and production environments, credentials, databases, and storage. Use test media only in staging.
- [ ] Validate LocalStack-dependent behavior against real AWS services in staging, especially signed upload URLs, multipart upload completion/abort, S3 lifecycle cleanup, SQS delivery/retries, IAM permissions, and object access policies; emulation is not a substitute for this integration test.
- [ ] Set up GitHub Actions for builds, tests, security checks, and container publishing; deploy to staging first and require approval for production. Use repeatable infrastructure configuration, backward-compatible migrations, and documented rollback/recovery.
- [ ] Tune pay-as-you-go and scale-to-zero processing capacity so workers do not idle unnecessarily. Include always-on database/API, networking, logs, backups, and video egress in the cost model; low traffic does not mean zero baseline cost.
- [ ] Validate production upload, processing, authorization, the 100 MB per-video default, user-specific quota overrides, seven-day cleanup and expiry UI, monitoring, billing alerts, backup restore, and rollback before opening beta registration.

**Done when:** the Phase 0 beta—accounts, uploads, existing editing tools, entitlements, and admin controls—is implemented and tested end-to-end locally before any public deployment work begins. The timeline editor is explicitly Phase 1. Phase 0 is complete only after the beta is deployed to AWS Mumbai through staging, with access controls, the 100 MB per-video default and admin overrides, seven-day cleanup with in-product expiry visibility, budget alerts, and tested backup/restore and rollback.

### Initial access matrix

| Account access | Video upload and editing | Video downloader | Admin panel |
|---|---:|---:|---:|
| Normal user | Yes | No | No |
| Premium user | Yes | Yes | No |
| Administrator | According to their assigned plan | According to their assigned plan | Yes |

Feature flags can disable a capability for everyone regardless of plan. Admin privileges are separate from premium access and do not implicitly grant downloader access. Premium access can initially be assigned by an administrator; subscription and payment integration can be planned separately.

### Upload quota policy

Per-user quota management is a permanent admin capability for both beta and main release. Beta defaults are initial operating limits, not temporary admin functionality; administrators retain user-specific controls after launch. Global defaults and platform-wide hard ceilings may change as capacity, plans, and costs are understood.

| Limit | Public beta default | Admin control |
|---|---|---|
| Maximum size per video | **100 MB per user** initially | Set a per-user override up to a platform-wide hard ceiling |
| Simultaneous uploads | One upload in progress per user | Increase a specific user's allowance if operationally safe |
| Videos per user | Configurable default maximum | Set a per-user maximum; increasing it does not change other users' quotas |

The 100 MB limit is the maximum size of each video upload, not a total account-storage allowance. Enforce it server-side before issuing upload authorization and again when finalizing an upload. In **My Account**, report the user's configured upload limit and current video count alongside the uploaded-video list and expiry times. Keep the seven-day beta retention policy separate from upload quotas: expiry removes eligible media, while quotas control upload size, simultaneous uploads, and video count. Set and document main-release defaults before general availability without removing admin override controls.

## Deployment decisions recorded

These are the current planning assumptions from the deployment discussion, not a final bill or a claim that the infrastructure has already been provisioned.

| Area | Starting decision |
|---|---|
| Cloud and region | AWS, Mumbai (`ap-south-1`), selected for beta; confirm service availability and data-residency requirements before launch |
| Pricing approach | Pay-as-you-go during beta; avoid long-term compute commitments until real usage and cost are measured |
| Frontend | Static React build on S3, delivered through CloudFront |
| API | Containerized FastAPI service on Amazon ECS with AWS Fargate |
| Video processing | Separate, isolated ECS/Fargate worker tasks consuming jobs from a durable queue such as SQS; use Lambda only for short event-driven tasks, not full FFmpeg exports |
| Beta media engine | FFmpeg in isolated workers, with queued jobs, conservative concurrency, and size/duration limits; benchmark before scaling |
| Database | Managed PostgreSQL on Amazon RDS |
| Media files | Private S3 buckets for originals, exports, and derived previews; public beta retains media and associated project data for 7 days from upload/creation, then deletes automatically |
| Large uploads | Browser-to-S3 multipart upload using short-lived, scoped authorization; API verifies completion and records ownership/metadata |
| Delivery | Authorized media access, with CDN delivery considered only after private-access controls, transfer costs, and caching behavior are validated |
| Environments | Separate development, staging, and production accounts/resources or equivalent isolation; staging must not use production media |
| Local development | Local PostgreSQL plus LocalStack S3/SQS emulation; validate AWS-specific behavior in isolated staging |
| CI/CD | GitHub Actions for builds, tests, security checks, and container publishing; deploy to staging first and require an approval gate for production |

### Cost assumptions to validate

- A preliminary small-beta planning range discussed was **about USD $150–$350 per month**, before taxes. This is a rough, unverified estimate—not an AWS quote or calculator result.
- Pay-as-you-go can reduce variable compute costs during low-usage periods, especially when workers scale down, but this rough range assumes baseline API/database resources and limited private media storage with 7-day beta retention. It does not promise high availability or include a workload-specific data-transfer estimate.
- Video delivery/egress, repeated exports, retained copies, worker runtime, database availability configuration, NAT/networking, logs, backups, and support can materially increase the bill. Video traffic and processing volume are major unknowns.
- Before launch, calculate Mumbai-region costs using expected monthly upload GB, retained GB, playback/download GB, average source and output sizes, processing minutes by worker size, API uptime, database sizing, backup retention, and environment count. Compare the estimate with actual beta usage.
- Configure budget alerts and per-user storage, upload, export, and concurrent-job limits before opening public registration; validate that the 7-day retention and cleanup policy is working.

## Later — Billing and service operations

These features can follow the core account, editing, and access-control workflows.

- [ ] Add optional expiry reminder emails before media is deleted; keep in-product expiry status available regardless of email preferences.
- [ ] Integrate subscriptions and payments for premium plans, including plan changes, renewals, cancellations, payment failures, and billing history.
- [ ] Define how premium entitlements change when a subscription expires or is cancelled, without deleting a user's projects or source media unexpectedly.
- [ ] Back up project data and configuration, document recovery procedures, and offer users a portable way to export projects and their media.
- [ ] Define retention, restore, and deletion policies for backups and user media; test recovery rather than relying on backups alone.

## Phase 1 — Timeline editor MVP

**Goal:** let users make a complete short edit starting with a video they uploaded.

- [ ] Provide a direct path from a successful upload to "Edit video"; also allow editing any supported video already in the library.
- [ ] Create, rename, save, duplicate, and reopen editing projects.
- [ ] Add a multi-clip timeline with reorder, trim handles, split-at-playhead, delete, and ripple delete.
- [ ] Provide a preview player with frame/time seeking, fit-to-view, and keyboard shortcuts for play, pause, split, and undo/redo.
- [ ] Support a primary video track and an independent audio track; start with clip-level mute and volume.
- [ ] Add non-destructive undo/redo and autosave.
- [ ] Export a timeline to MP4 (H.264/AAC) with progress, cancellation, and a clear destination.

**Success measure:** a user can upload one or more videos, assemble and export a multi-clip edit, and return to the project later without modifying source files or losing project state after a reload.

## Phase 2 — Transform and convert

**Goal:** cover common format and framing needs in the same project/export flow.

- [ ] Add explicit output container and codec choices, initially MP4, WebM, and MKV where the installed FFmpeg build supports them.
- [ ] Offer export presets for resolution, frame rate, quality/bitrate, and audio codec/bitrate, with an estimated output size where feasible.
- [ ] Add crop, resize, rotate/flip, aspect-ratio presets, and letterbox/fill behavior.
- [ ] Add clip speed changes and audio gain, mute, and simple fade-in/fade-out.
- [ ] Preserve source audio/video streams when a lossless remux or stream-copy export is safe; explain when re-encoding is required.

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
- [ ] Evaluate browser-side WebCodecs or FFmpeg.wasm for selected operations only if measured server compute savings outweigh client performance, compatibility, and support costs.
- [ ] Add project asset relinking, missing-file warnings, and a portable project package option.
- [ ] Add proxy/low-resolution preview media for smooth editing on large source files.
- [ ] Add timeline zoom, snapping, markers, clip grouping, and multi-track audio/video.
- [ ] Add searchable project/library tags and keyboard-shortcut customization.
- [ ] Add job history with retry and cleanup controls for generated previews and exports.

**Success measure:** users can work on larger projects without excessive preview lag and can move a project to another machine with its media.

## Future scope — Organization SaaS / Enterprise

The long-term product direction includes SaaS workspaces for organizations, not only individual user accounts. Build these capabilities after the individual editing product is proven; the early ownership model should make this expansion possible without weakening tenant isolation.

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
- [ ] Allow organization admins to configure allowed features, downloader availability, upload/export quotas, retention policies, and sharing controls within platform-wide limits.
- [ ] Keep platform administrators separate from customer organization administrators; audit privileged actions and make logs available to the appropriate customer admins.

### Security, governance, and service commitments

- [ ] Define tenant-isolation controls for database records, object-storage paths and permissions, processing jobs, logs, and support tooling; test attempts to cross tenant boundaries.
- [ ] Offer organization-configurable retention and deletion policies, exportable audit logs, data export, and documented offboarding/deletion behavior.
- [ ] Evaluate customer requirements for data residency, encryption/key management, security questionnaires, penetration testing, incident response, and compliance certifications. Make no compliance or SLA claims until independently verified and operationally supported.
- [ ] Define service availability goals, support response expectations, incident communication, backup/recovery objectives, and an operational status page before offering enterprise contracts.
- [ ] Add organization-level usage, storage, processing, and cost reports so customers can understand and administer their consumption.

**Enterprise readiness gate:** organization membership and authorization must be enforced server-side across API, storage, worker jobs, and exports; tenant isolation, offboarding, auditability, support operations, and any published service/security commitments must be tested and documented before selling organization plans.

## Later — Optional smart features

These should follow a solid manual editing experience and be opt-in, especially where media leaves the local machine.

- [ ] Local or explicitly configured speech-to-text for subtitle drafts, with editable text and timing.
- [ ] Scene/quiet-section detection and suggested cut points that users review and apply themselves.
- [ ] Optional background removal, denoise, stabilization, and smart reframing, subject to hardware and model availability.
- [ ] Optional remote access only after authentication, permissions, and media-transfer boundaries are designed.

## Product and reliability guardrails

- Keep editing non-destructive: source files are inputs, and exports are separate outputs.
- Enforce authentication, authorization, account ownership, and plan entitlements on the server; hiding a UI control is never an access-control boundary.
- Treat feature flags as global capability controls, not a replacement for authentication or per-user authorization; protect administrative settings and sensitive APIs independently.
- Prefer local processing by default; clearly disclose any feature that sends media to an external service.
- Validate media and export settings before starting long jobs; never report success until the output is verified.
- Keep the UI usable while jobs run, and expose progress, cancellation, and actionable failures.
- Test generated media with FFprobe and representative playback checks; include odd aspect ratios, variable frame rates, missing audio, and long files.
- Document supported codecs based on the actual FFmpeg build rather than promising formats that may not be installed.

## Not in the initial scope

- Replacing a full professional nonlinear editor with advanced compositing or a plugin marketplace.
- Cloud upload/storage as a prerequisite for editing; the initial upload and editing workflow should work locally.
- Automatic or AI-generated edits that alter a project without user review.

Real-time multi-user collaboration is deferred; organization workspaces, sharing, review, and approval workflows are future scope described above.

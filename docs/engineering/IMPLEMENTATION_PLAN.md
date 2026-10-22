# Implementation plan

## P0

1. Replace browser-shipped edit authorization with server-side authenticated
   sessions, or disable the shared editing feature until that is available.
2. Regenerate the manifest/published asset and enforce byte/hash integrity in
   the publication pipeline.

## P1

1. Preserve existing per-record edit fields on subsequent edits and refuse
   writes after an uncertain store read.
2. Make static-catalog fallback fetch all pages or fail clearly.
3. Add CI jobs for `app`, `api`, and publish-integrity checks.

## P2

1. Consolidate legacy frontends into one explicitly supported application.
2. Add API/UI regression coverage and bounded link validation.
3. Update product/security documentation from executable behavior.


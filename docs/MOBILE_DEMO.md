# Pharma Path Android

The final release is **1.4.1 / version code 8**, Android ARM64, React Native / Expo SDK 58. Native iOS delivery remains excluded. Download the APK, checksum, certificate and device recording from the [immutable release](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/tag/nesfic-i09-final-v1.4.1).

The app connects to **https://pharma-path.onrender.com**. Its More screen identifies the compiled source commit. Public synthetic credentials are intentionally pre-filled; they are not private company credentials. A default independent rehearsal lasts two hours. Use the website's generated rehearsal email and the public evaluation password to share the same inventory on both clients.

Existing installations retain the selected server and pending commands. Resolve those commands before changing accounts or origins. The Free API can need about a minute to wake. The final native package disables cleartext traffic and retains the existing evaluation signing certificate for upgrades. This is evaluation signing, not managed production/store signing.

## Included workflows

- Five tabs: Today, Network, Actions, Stock, More. Sage/ivory/forest visual language and bundled Manrope / DM Sans fonts match the website.
- Offline bundled regional vector map, fit/zoom controls, medicine selection, live backend stock/risk markers, approximate sites and illustrative permitted route links. The accessible location list opens the same site details as a map marker. No map-provider key or phone GPS permission is needed.
- Stock-risk explanations and eligible/blocked source comparison, with shelf-life, donor protection, transport assumptions and an explicit warning when an eligible transfer arrives after the projected shortage/due date.
- Requests, proposed plans, versioned approval/reservation, partial dispatch, per-batch partial receipt, accepted versus damage/quarantine quantities and cancellation of unshipped stock. Roles and site scopes gate controls; server checks remain authoritative.
- Batch lookup and native camera QR scanner with manual entry fallback. `GRD:BATCH:<internal-id>` and `GRD:SHIPMENT:<internal-id>` labels are accepted; a product barcode is never treated as batch/expiry evidence. Images stay on device; identifiers go to the configured backend for verification.
- Physical counts create review cases. Mobile counts retain the original batch timestamp and are rejected for recount if the backend stock changed before upload. The phone never silently adjusts or resolves a case.
- Evaluated forecast jobs, forecast intervals, held-out baseline metrics, policy-simulation results, declared data provenance, reconciliation, scoped activity and grounded read-only assistant. The new phone Operations desk includes return transitions/disposition, supplier receipts, assigned count rounds and alerts. Demand imports remain on the website.

## Reproduce the hosted build

Use Node 24, the locked mobile dependencies and Android SDK/JDK. From `mobile`:

```sh
npm ci
EXPO_PUBLIC_GRD_API_URL=https://pharma-path.onrender.com GRD_ALLOW_LOCAL_HTTP=0 npx expo prebuild --platform android --no-install
cd android
EXPO_PUBLIC_GRD_API_URL=https://pharma-path.onrender.com ./gradlew app:assembleRelease -PreactNativeArchitectures=arm64-v8a --max-workers 2
```

The Expo configuration derives version/code/source from the canonical release metadata and checked-out commit. Generated native folders are ignored and must not be hand-edited. Cloud EAS builds or paid hosting are not required. For local development, use the documented private/local server override deliberately; never replay an existing hosted outbox into a local organisation.

## Outbox and offline boundary

Native tokens, cached authorised records and pending commands are kept in Expo SecureStore (OS keychain/keystore), with iOS this-device-only/unlocked access. Passwords are not stored. An outbox belongs to a hash of server origin, organisation and user. At most 100 commands, each up to 25,000 UTF-8 bytes, are accepted. Larger values and the index are split into encrypted SecureStore items; the manifest commits last so failed writes retain the previous complete value. Persistence succeeds before transmission; retries always use the saved body and original idempotency key.

The narrow offline workflows are a receipt or count entered from already-fetched records. Unconfirmed actions do **not** increase confirmed stock. They appear in More with their original quantities, date and reference. Retry is deliberate, not automatic. A 409 or other non-retryable input/access conflict stops replay and requires refresh/reconciliation. Removing a local entry does not undo a server movement. A count whose snapshot changed requires reopening the batch and physically recounting.

Approval, proposal and dispatch also retain an unconfirmed command after a lost response, so the user can safely confirm the result using the same key; they should be initiated online. Stale planning is always checked by the backend. A session expiry requires reauthentication as the same account to access its retained actions. Sign-out requires resolving/removing pending entries and revokes the user's existing sessions, including the website.

Authorised network/stock/worklist snapshots are encrypted in SecureStore chunks. A native cold start can restore the most recent account-bound records while the server-issued session is still valid. Cached records are marked provisional/stale and mutations still require server acceptance; first login and expired sessions need connectivity. Browser preview storage is session memory only, explicitly labelled in More. Native persistence, camera optics, permissions and device-specific behaviour require native/device QA.

## Verification

The final release verification JSON records CI and physical checks against the exact packaged build. It distinguishes camera/online receipt, denied permission and offline persistence if exercised. A passed logic test or emulator screenshot alone does not prove native offline operation. Push delivery, automatic background sync, GPS vehicle tracking, supplier/courier integrations and app-store publication remain outside the demonstrated scope.

The Expo starter licence remains in `mobile/EXPO_TEMPLATE_LICENSE`. Public benchmark data carries CC BY-NC 4.0 restrictions; it is research evidence, not licensed commercial company training data.

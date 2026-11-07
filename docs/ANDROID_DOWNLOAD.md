# Current Android download — Pharma Path 1.4.2

[Download Pharma Path Android 1.4.2 APK](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/download/nesfic-i09-final-v1.4.2/Pharma_Path_Android_1.4.2.apk)

The current installation package is **1.4.2 / Android version code 9**, ARM64,
package `in.grdsupply.demo`. Install it over the existing app. Keep app data when
pending actions exist; the application ID and evaluation signing certificate are
unchanged. First sign-in and confirmed stock changes require connectivity.

| Identity | Value |
|---|---|
| Immutable release | [nesfic-i09-final-v1.4.2](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/tag/nesfic-i09-final-v1.4.2) |
| APK source | [`32809d1a200e8a977e7c0db902b55c5dfcffe20b`](https://github.com/Pulkit-10-0/pharma-path-nesfic/tree/32809d1a200e8a977e7c0db902b55c5dfcffe20b) |
| APK file | `Pharma_Path_Android_1.4.2.apk` — 41,096,209 bytes |
| APK SHA-256 | `97a682bc7f04e55ec68b3561191b24d671ff39e2f65d6634670f13e50ae62cf8` |
| Certificate SHA-256 | `fac61745dc0903786fb9ede62a962b399f7348f0bb6f899b8332667591033b9c` |

Release files: [SHA256SUMS.txt](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/download/nesfic-i09-final-v1.4.2/SHA256SUMS.txt),
[connection verification JSON](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/download/nesfic-i09-final-v1.4.2/connection-release-verification.json),
[connection fix and recovery guidance](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/download/nesfic-i09-final-v1.4.2/CONNECTION_FIX.md).

This patch uses the direct HTTPS API first and an eligible alternate-host retry
to handle Android DNS/network failures. Both public addresses reach the same
stock ledger. It preserves account/cache/outbox identities and does not forward
custom-server credentials to public hosts. See [the connection patch](ANDROID_CONNECTION_FIX.md).

Verification includes 22 mobile logic tests and live sign-in, stock reads and
ledger reconciliation on the direct API and an alternate host after an injected
DNS failure. The affected friend's phone/Wi-Fi has not been retested; no native
physical-device or offline acceptance is established by these checks.

The [1.4.1 submission PDFs, PPTX and evidence](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/tag/nesfic-i09-final-v1.4.1)
remain the immutable product-evidence snapshot. Keep their recorded source,
checksums and captured build labels; use **1.4.2** for a new Android installation.
Website, API and APK remain frozen at source `32809d1`; later repository
documentation commits do not change that package or hosting deployment.

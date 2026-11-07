# Final release of record

The canonical release is **Pharma Path 1.4.2**, tag
[`nesfic-i09-final-v1.4.2`](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/tag/nesfic-i09-final-v1.4.2).
The [Android APK](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/download/nesfic-i09-final-v1.4.2/Pharma_Path_Android_1.4.2.apk),
`SHA256SUMS.txt` and `connection-release-verification.json` are published with
that tag after CI, deployment and package checks. They identify frozen source
`32809d1a200e8a977e7c0db902b55c5dfcffe20b`, CI, APK certificate/checksum and the
physical-test boundary. See [download and verification details](ANDROID_DOWNLOAD.md).

## Android connection patch

Version 1.4.2 fixes Android DNS/network error handling. Public mobile requests use
the direct API hostname first and can fall back to the branded HTTPS hostname.
Both addresses use the same backend and stock ledger. Cache and outbox identities
remain stable; custom organisation servers never fall back to public hosts.

The [1.4.1 product evidence deck and supporting proposal](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/tag/nesfic-i09-final-v1.4.1)
remain an immutable evidence snapshot. Their original asset manifest and release
verification JSON continue to describe that snapshot. No presentation,
architecture, product workflow, dataset or forecasting method is changed by
this connection patch. See
[ANDROID_CONNECTION_FIX](ANDROID_CONNECTION_FIX.md) for scope and recovery.

## How to verify the same source

- Website: `/release.json`, and Help → release identity.
- Backend: public `/health/release` returns the source commit, version and tag.
- Android: More → Connected account shows its compiled version and source commit.
- PDFs: the unchanged 1.4.1 snapshot identifies its original source
  `ecb9897df2a61c8f7cfe24463685c05b5ba28af0` and CI; its captured Android QR/online
  receipt is app 1.3.2. It is not physical acceptance evidence for APK 1.4.2.
- Source: the immutable canonical tag. The existing deployment repository mirrors
  the same commit so the configured Free services can build it without migration.

The website, API and APK remain frozen at `32809d1`; later documentation-only
commits on `main` do not replace that release or deploy a new service build.
The 1.4.2 checks do not claim a retest on the affected friend's phone or Wi-Fi.

Never use a moving `main` link as the only release identifier. Earlier `review-2`
assets, version 1.3.2 recordings and dated audit guides are historical evidence,
not the final build's identity. No current result is inferred from an old tag.

## Access and repeatability

The public synthetic evaluation account remains pre-filled. A default independent
rehearsal copies the versioned dynamic demand into a separate organisation and
uses its frozen opening batches. It has a two-hour lifetime, a maximum of three
concurrent sessions and a Free database size guard. No shared/company stock is
reset. Cleanup removes only expired organisations explicitly marked disposable;
active calculation work is protected. Unchecking the isolation option uses the
existing shared synthetic account if capacity is reached.

The workspace email can be entered on Android or the website with the public
evaluation password to share one rehearsal. Expired rehearsals are rejected;
new sessions start from the same generated stock. The rehearsal explicitly
assumes a two-day central-to-Dibrugarh express lane; it is not a measured route.

## Evidence boundaries

The forecast predictors/selection remain `weekly-rolling-v2`. The fixed protocol
and additional reproduction script are in `docs/evaluation/FINAL_PROTOCOL.md`
and `scripts/evaluate_final_evidence.py`. Raw dated prediction paths, paired
bootstrap summaries and 200-seed inventory frontiers are packaged in `grd/assets`.

The 17.0% observed benchmark improvement is against repeating last week, below
the 20% challenge target; improvement versus the four-week mean is 7.7%. Selected
mean bias is -4.26%. ML everywhere scored lower test WAPE and more negative bias;
selection has not been retuned on that known test. Interval coverage is uneven
and intervals are not used for a stochastic shortage probability.

The inventory replay uses chronological observed sales as a demand proxy with
invented bounded supply and shelf lives. Buffers are selected on calibration;
test fill targets can fail. It is not actual distributor stock history or savings.

Power BI remains in the MAIN submission, alongside website and Android. Its
analytics module identifies the dataset, model and supply assumptions behind each metric.
The final source does not claim measured GRD outcomes, weather/outbreak awareness,
native iOS acceptance or production readiness.

## Free hosting and video

The static site and API remain on Free Render plans with persistent Neon Free
PostgreSQL. The static `/review/index.html` page provides the release link and
data limits even if the API is cold. Submission recordings are supplied
separately. The scheduled readiness check
is best-effort; it is not an availability guarantee. No paid service is required.

Grant category remains unconfirmed. The ₹18 lakh development budget is an
indicative estimate, conditional on the eventual selected tier and owner approval.

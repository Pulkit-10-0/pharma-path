# Android connection patch - 1.4.2

## Report and diagnosis

An Android phone reported `java.net.UnknownHostException` while resolving
`pharma-path.onrender.com`. The same app works on the applicant's phone; the
affected friend is believed to use Wi-Fi. Both public HTTPS hostnames resolve
and return the existing API release from the development machine. This points
to a device/network DNS or filtering issue; the affected Wi-Fi is not available
for direct testing. Server cold starts and DNS lookup failures are different.

## Fix

- Native requests for either public Pharma Path hostname use
  `https://grd-supply-demo.onrender.com` first, avoiding the static website proxy.
- If the connection fails, eligible requests can use
  `https://pharma-path.onrender.com`. Both names reach the same API/SQL ledger.
  The reachable name is reused for that client.
- Automatic retry is limited to reads, commands with their original persisted
  idempotency key, and confirmed DNS failures. A write with an ambiguous lost
  reply and no idempotency key is not automatically repeated. Login does not
  silently create another workspace after an ambiguous failed response.
- Android Java DNS/network errors are converted to a clear message suggesting
  mobile data or another Wi-Fi network. Unconfirmed commands stay in the outbox.
- Saved server/account/cache identities stay unchanged. This avoids losing access
  to existing cached stock or pending commands after upgrading.
- Custom organisation servers have no public-host fallback. Authentication and
  stock-conflict responses are not retried against a different host.
- HTTPS and certificate checks remain enabled. No fixed IP address, public DNS
  resolver, security exception or new device permission is introduced.

## Recovery on a phone

Install the new APK over the existing app; do not uninstall or clear its data if
pending actions exist. Use the existing login/workspace. If Wi-Fi blocks both
Render addresses, try mobile data or another Wi-Fi network and retry. The APK
cannot provide connectivity when the network blocks both endpoints or is offline.
First login and server-confirmed stock actions still require a connection.

The 1.4.1 APK also has a temporary workaround: on Sign in, open **Server
connection**, set **Backend server origin** to
`https://grd-supply-demo.onrender.com`, and sign in. Existing unsynced actions
remain bound to their original server/account, so upgrade and reuse the existing
setting when pending actions exist.

## Verification and scope

Nine additional connection tests cover the reported Java error, direct API
routing, alternate-host login and sticky routing, exact command key/body replay,
no replay for ambiguous writes, no credential forwarding from custom servers,
HTTP conflicts, session changes and timeouts. Existing queue/cache tests remain.
The Android release keeps the installed evaluation signing certificate and uses
version code 9. See the release assets for build/checksum evidence and CI results.

No website/app workflow redesign, dataset/model change, Power BI change, video
edit or Canva edit is included. The product evidence deck remains the frozen
1.4.1 snapshot. Neither a physical test on the affected phone nor a fix to its
Wi-Fi DNS configuration is claimed without that test.

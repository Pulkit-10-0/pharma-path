import { useEffect, useState } from "react";
import type { ReleaseInfo } from "../../shared/evidence";
declare const __PHARMA_RELEASE__: ReleaseInfo;
export function ReleaseIdentity() {
  const build = __PHARMA_RELEASE__;
  const [server, setServer] = useState<ReleaseInfo | null>(null);
  useEffect(() => {
    let current = true;
    void fetch((import.meta.env.VITE_API_BASE_URL || "") + "/health/release")
      .then((r) => (r.ok ? r.json() : null))
      .then((r) => {
        if (current) setServer(r);
      })
      .catch(() => {});
    return () => {
      current = false;
    };
  }, []);
  return (
    <div className="release-identity">
      <strong>Pharma Path {build.version}</strong>
      <p>
        Website source: {build.commit.slice(0, 8)} · Backend source:{" "}
        {server?.commit.slice(0, 8) || "checking"}
      </p>
      {server && server.commit !== build.commit && (
        <p className="text-coral">
          Website and backend are running different source revisions.
        </p>
      )}
      <a href={build.release_url} target="_blank" rel="noreferrer">
        Release files and verification
      </a>
    </div>
  );
}

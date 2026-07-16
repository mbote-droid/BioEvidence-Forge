# Security posture

BioEvidence Forge is designed to minimize local exposure. It does not claim compliance
with any healthcare or privacy regulation.

- The default HTTP listener is bound to `127.0.0.1`; do not expose it publicly without
  authenticated reverse-proxy controls.
- Store only publicly available research material unless approved governance, consent,
  privacy controls, and access restrictions are in place.
- Keep `.env` private. It may contain a contact email but must never hold passwords or
  long-lived access tokens.
- The container runs as an unprivileged user with all Linux capabilities removed.
- Review source terms, rate limits, and licensing before enabling additional connectors.
- Report security concerns privately to the repository owner; do not include sensitive
  details in a public issue.


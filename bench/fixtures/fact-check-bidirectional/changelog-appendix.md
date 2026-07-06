# Security & Compliance Notes — Appendix to v4.2 Changelog

This appendix covers security-relevant changes for v4.2 that are tracked
separately from the main changelog for our compliance review process.

## Encryption

End-to-end encryption for shared folders is now available as an opt-in
beta feature in v4.2. Once enabled on a shared folder, only members with
the folder's key can decrypt file contents — NimbusSync's own servers
store only ciphertext for folders with this enabled. Opt-in only for this
release; we're evaluating making it the default in a future release once
we've validated performance with beta users.

## Access logging

Shared-folder access logs now retain 90 days of history (up from 30),
matching our updated compliance requirements.

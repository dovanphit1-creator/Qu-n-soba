# Quán Mì của tôi — 1.0.0

## Ready
- Standalone Windows x64 executable, fixed title and noodle-bowl icon.
- Fresh first-run state and welcome screen; separate per-user local saves.
- CI exercises first launch, independent users, resume, and full service on the actual EXE.
- Test profiles are temporary and never touch production saves or enter the release archive.
- Release archive contains only executable, instructions, release status and SHA-256 checksum.

## Publication blocker
The current executable is unsigned. This build is not Microsoft Store approved and must not be described as guaranteed to bypass Windows warnings.

For Store MSIX publication, the owner must supply their registered Partner Center application identity and complete account verification/submission. Do not invent a publisher identity or purchase credentials on their behalf. Microsoft signs accepted Store MSIX packages.

For direct EXE distribution, a trusted code-signing certificate/service with the owner's verified identity is required. Signing alone does not guarantee SmartScreen reputation. Never upload private signing keys into this repository or ask for them in chat.

Official references:
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options

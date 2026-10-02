# Permanent game identity

The owner explicitly requires the official name **Quán Mì Của Tôi** and a noodle-bowl application icon to remain unchanged in all future updates.

- Use soba_manual/brand.py as the canonical title and Windows application identity.
- Preserve the noodle-bowl artwork in soba_manual/build_brand_assets.py; rebuilding identical assets is allowed. Do not redesign it unless the owner explicitly asks.
- Keep the Windows executable name Quán Mì Của Tôi.exe, window title, product metadata and in-game headings consistent.
- Keep the existing QuanSobaManual/save-vnd.json save location for compatibility. It is an internal historical path, not the public product name.
- Gameplay updates must preserve saved progress and this identity.

# Release order

Follow the order explicitly listed by the owner for each update. The old always-web-first rule is replaced. The current audio update is web-only; do not distribute other platforms until requested. Preserve disposable browser sessions. Do not claim a web update is live until deployment succeeds. Choose the next version for new features as authorized by the owner. Preserve the existing 40% service timing reduction.

# Required update notifications

The owner requires every new game build on every platform to check for newer compatible releases and show an in-game notification with a download/update action, like the Windows edition. Preserve offline play and saved progress. This is a release requirement, not an optional feature. Android APK releases must retain the application ID and the owner-held stable signing key. Never publish CI debug-signed APKs as updates. Verify newer/equal/older versions, platform filtering, offline failure and the visible notification before release.

# Shared loading screen

The owner requires the same restaurant painting and branded loading layout on every edition. Canonical artwork: soba_manual/loading-art/restaurant.jpg. Keep title, icon and publisher unchanged. Show it during actual startup work; hide only after the first game frame. Do not add artificial loading delays or fabricated percentage progress. Preserve native APK signing and update notifications.

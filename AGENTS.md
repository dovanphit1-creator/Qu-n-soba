# Permanent game identity

The owner explicitly requires the official name **Quán Mì Của Tôi** and a noodle-bowl application icon to remain unchanged in all future updates.

- Use soba_manual/brand.py as the canonical title and Windows application identity.
- Preserve the noodle-bowl artwork in soba_manual/build_brand_assets.py; rebuilding identical assets is allowed. Do not redesign it unless the owner explicitly asks.
- Keep the Windows executable name Quán Mì Của Tôi.exe, window title, product metadata and in-game headings consistent.
- Keep the existing QuanSobaManual/save-vnd.json save location for compatibility. It is an internal historical path, not the public product name.
- Gameplay updates must preserve saved progress and this identity.

# Release order

The owner requires every gameplay update to be published and verified on the existing web game first, before building or distributing the Windows edition. Preserve disposable browser sessions. Do not claim a web update is live until deployment succeeds. Keep GAME_VERSION at 1.1.0 for the current 40% timing reduction.

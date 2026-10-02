# Web 2.1.2

- Correct pointer mapping after small-screen and desktop resizing; touch laptops no longer automatically request mobile orientation.
- Keep the selected furniture position stable while moving the mouse to confirmation. Dragging furniture does not move the owner.
- Return from recruitment, text editing and other phone dialogs to the original app. Preserve names up to 48 characters in the menu editor.
- Fit button labels, explain unavailable furniture purchases, and display input errors above dialogs.
- Match catalog, placement and installed furniture proportions with nearest-pixel scaling. Align cooking hit points with the displayed stove.
- Use one continuous wooden floor throughout the room.
- Sort furniture, people, carried objects and tabletop items by depth. Walking cycles follow distance travelled; stationary employees use work poses instead of walking in place.
- Desktop click-to-walk, keyboard controls and existing touch steering are supported. Carried noodle bowls retain their toppings.

Validation: actual pointer interaction at 1600×1000, 1280×720, 844×390 and 768×1024; all nine phone apps; CV/back navigation; long menu names; placement confirmation; walking/stopping; delivery, cooking, serving and hold-to-clean regressions; packaged boot; audio and fullscreen fallback checks.

This release improves the existing artwork and animation system; it does not replace every character action with newly drawn directional animation frames. Browser QA on physical devices remains useful.

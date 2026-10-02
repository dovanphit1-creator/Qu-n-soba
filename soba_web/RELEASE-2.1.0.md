# Quán Mì Của Tôi — Web 2.1.0

Web only. Windows/Android and their save formats are unchanged.

## Art
Five bundled raster atlases (80 cells): furniture, environment, owner walking in four directions, visitors/delivery worker, idle/carry/work/wash actions. Art is sampled onto a shared two-world-pixel grid and rendered nearest-neighbor; no runtime asset download or smoothing. Warm wood dining floor and sage kitchen tiles, directional furniture details, translucent pixel shadows, steam and breathing/walk cycles. Permanent game icon and loading illustration are preserved.

## Repairs
- Delivery cartons occupy distinct positions; overflow waits for a later truck.
- Floor navigation chooses an unoccupied arrival point and no longer resets to a hard-coded blocked position.
- A sealed carton can be opened and stored in one explicit cabinet action.
- Stale serve/storage/customer dialogs no longer assume objects still exist.
- Bowls put on the floor are excluded from automatic staff serving/preparation.
- Focus loss clears held cleaning, pointer and button state.
- Escorted groups no longer get pulled back to the ticket machine.
- Guests and staff route around player furniture. Staff cannot finish a job while still walking toward it.

## Verification
Headless Python regression tests cover physical economy/service, native finger events, all phone apps and archived receipts, plus the repairs above and all sprite cells. Browser boot/package/audio/presentation checks run separately. No physical iPhone or Android device was available for this release.

## Remaining art constraints
Guest walk sheets currently face forward; the owner has four walking directions. Furniture has a single illustrated viewing direction, scaled to rotated footprints. Further directional furniture/guest art is needed for fully bespoke rotation animation. Pixel detail is generated raster artwork, not a claim of hand-drawn assets.

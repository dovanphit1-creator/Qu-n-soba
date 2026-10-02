# Web 2.1 art direction and generation record

Created using the built-in image_gen tool, not CLI. These are original generated raster atlases. Keep the permanent application icon and loading painting separate.

Common prompt: production game sprite atlas for a cozy Vietnamese soba restaurant; true crisp pixel art, warm modern indie style; consistent slightly angled top-down orthographic view (not isometric); upper-left light; honey oak, cream, sage, teal and terracotta; transparent background; 4 by 4 equally spaced cells, isolated subjects, generous gutters, no text/grid; detailed silhouettes, materials and highlights; no vector, 3D, smooth painting or blurry edges.

- furniture.png: row 1 round table with 1/2/3 chairs and square table with 4; row 2 meal-ticket machine, attendance clock, calendar, empty chalkboard; row 3 double sink, bowl cabinet, glass drinks fridge, six-pot stove (3 by 2); row 4 rice cooker on stand, serving pass, refrigerated preparation counter, spice cabinet.
- owner.png: same dark-haired adult male, green shirt, cream apron, brown trousers/shoes. Four sequential walking frames per row. Rows face down, left, right, up. Same feet baseline; visible arm/leg motion; conceptually 32 by 48 pixel character.
- environment.png: row 1 wood floor, sage ceramic tile, sidewalk, asphalt; row 2 wood/plaster wall, lit window, entrance door, noren noodle curtain; row 3 potted plant, paper lantern, noodle bowl, dirty dishes; row 4 sealed carton, open carton, cream/sage truck, decorative shelf.
- guests.png: four down-facing walk frames per row. Rows: woman with dark bob and terracotta cardigan; man with glasses and navy shirt; elderly woman with grey bun and plum blouse; mustard-uniform delivery worker carrying carton.
- actions.png: same owner as reference. Four frames per row: idle breathing; walking with empty serving tray; stirring; washing a bowl with small water droplets. Transparent isolated sprites, no counters or room included.

Implementation: crop dominant opaque component within each cell (ignores stray alpha-edge pixels), sample nearest to the game pixel grid, cache, render at integer positions. Runtime scaling preserves hard edges. Collision footprints are independent of decorative overhang. Game-resolution atlas copies (512×512) are committed so the build is reproducible.

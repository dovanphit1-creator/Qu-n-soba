# Quán Mì của tôi — web

Web uses the same Python game and rules as Windows, with `App(persistent=False)`.
No saved game is read or written. Reloading or closing the page discards progress.
Windows keeps the existing local save path and default persistence behavior.

Build on Linux:

    pip install pygame-ce==2.5.7 pygbag==0.9.3 holidays==0.105 pillow==11.3.0
    python soba_manual/build_brand_assets.py
    python soba_web/build.py

Install system package fonts-dejavu-core first. Serve game/build/web over HTTPS
at /play and index.html at /. Copy assets/game.png to /icon.png and the Windows
release ZIP to /downloads/QuanMiCuaToi_Windows.zip.
The Pygbag WebAssembly runtime loads from pygame-web.github.io; internet is required.
Browser edition has been built and Python session behavior tested; interactive
browser validation was not available in this environment.

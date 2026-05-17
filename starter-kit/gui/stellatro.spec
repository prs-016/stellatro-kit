# stellatro.spec
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all submodules from heavy packages so nothing gets missed
hiddenimports = (
    collect_submodules('pygame') +
    collect_submodules('stellatro_common') +
    collect_submodules('stellatro_game') +
    collect_submodules('bots') +
    ['multiprocessing', 'importlib.util']
)

a = Analysis(
    ['gui.py'],
    pathex=[
        '.',           # starter-kit/gui/
        '..',          # starter-kit/ so bots/ and other sibling imports resolve
    ],
    binaries=[],
    datas=[
        # Bundle the assets folder into the executable root
        ('../assets', 'assets'),
        # Bundle local packages (no src/ layer in this repo)
        ('../../stellatro-common/stellatro_common', 'stellatro_common'),
        ('../../stellatro-game/stellatro_game', 'stellatro_game'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Uncomment to exclude heavy ML deps if bots don't need them at GUI runtime:
        # 'torch', 'torchrl', 'tensordict',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Stellatro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # True = show terminal window alongside app; False = GUI only
    icon=None,       # replace with 'assets/icon.icns' (mac) or 'assets/icon.ico' (win)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Stellatro',
)

# macOS: wrap in a .app bundle
app = BUNDLE(
    coll,
    name='Stellatro.app',
    icon=None,          # replace with 'assets/icon.icns'
    bundle_identifier='com.acmucsd.stellatro',
)

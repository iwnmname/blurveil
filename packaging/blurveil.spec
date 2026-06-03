# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


block_cipher = None


def _find_project_root() -> Path:
    spec_path = Path(SPECPATH)
    for candidate in (Path.cwd(), spec_path, spec_path.parent, spec_path.parent.parent):
        if (candidate / "main.py").exists():
            return candidate
    raise FileNotFoundError("Could not find project root with main.py")


project_root = _find_project_root()
icons_dir = project_root / "assets" / "icons"
windows_icon = icons_dir / "blurveil.ico"
macos_icon = icons_dir / "blurveil.icns"


def _path_from_env(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def _find_tesseract_cmd() -> Path | None:
    env_path = _path_from_env("TESSERACT_CMD")
    if env_path:
        return env_path

    candidates = []
    if sys.platform.startswith("win"):
        candidates.extend([
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        ])
    else:
        for binary_dir in os.environ.get("PATH", "").split(os.pathsep):
            candidates.append(Path(binary_dir) / "tesseract")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _find_tessdata_dir(tesseract_cmd: Path | None) -> Path | None:
    env_path = _path_from_env("TESSDATA_PREFIX")
    if env_path:
        if env_path.name == "tessdata":
            return env_path
        if (env_path / "tessdata").exists():
            return env_path / "tessdata"

    candidates = []
    if tesseract_cmd:
        candidates.append(tesseract_cmd.parent / "tessdata")
        candidates.append(tesseract_cmd.parent.parent / "share" / "tessdata")

    candidates.extend([
        Path("/opt/homebrew/share/tessdata"),
        Path("/usr/local/share/tessdata"),
    ])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _tesseract_binaries(tesseract_cmd: Path | None):
    if not tesseract_cmd:
        return []

    binaries = [(str(tesseract_cmd), ".")]
    if sys.platform.startswith("win"):
        for dll_path in tesseract_cmd.parent.glob("*.dll"):
            binaries.append((str(dll_path), "."))
    return binaries


tesseract_cmd = _find_tesseract_cmd()
tessdata_dir = _find_tessdata_dir(tesseract_cmd)

datas = []
if tessdata_dir:
    datas.append((str(tessdata_dir), "tessdata"))
if icons_dir.exists():
    datas.append((str(icons_dir), "assets/icons"))
datas.extend(collect_data_files("cv2", includes=["data/haarcascade_*.xml"]))

binaries = _tesseract_binaries(tesseract_cmd)

hiddenimports = collect_submodules("pynput")


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="Blurveil",
    icon=str(windows_icon) if windows_icon.exists() else None,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Blurveil",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Blurveil.app",
        icon=str(macos_icon) if macos_icon.exists() else None,
        bundle_identifier="com.blurveil.app",
    )

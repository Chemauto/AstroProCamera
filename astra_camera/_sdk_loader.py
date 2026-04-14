"""Load the Orbbec native SDK before importing the Python extension."""

from __future__ import annotations

import ctypes
import os
import site
import sys
from pathlib import Path


_LIB_NAME = "libOrbbecSDK.so.1.10"
_LOADED = False


def preload_orbbecsdk() -> None:
    """Preload the Orbbec shared library from the active Python environment."""
    global _LOADED
    if _LOADED:
        return

    try:
        ctypes.CDLL(_LIB_NAME, mode=ctypes.RTLD_GLOBAL)
        _LOADED = True
        return
    except OSError:
        pass

    attempted_paths: list[Path] = []
    for path in _candidate_paths():
        if not path.is_file():
            continue
        attempted_paths.append(path)
        try:
            ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
            _LOADED = True
            return
        except OSError:
            continue

    attempted = ", ".join(str(path) for path in attempted_paths) or "none"
    raise ImportError(
        f"Unable to load {_LIB_NAME}. Tried system library paths and: {attempted}. "
        "Set ORBBECSDK_LIBRARY_PATH to the library file or its directory if needed."
    )


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []

    env_path = os.environ.get("ORBBECSDK_LIBRARY_PATH")
    if env_path:
        path = Path(env_path).expanduser()
        if path.is_dir():
            candidates.append(path / _LIB_NAME)
        else:
            candidates.append(path)

    for site_dir in _site_packages_dirs():
        candidates.append(site_dir / _LIB_NAME)

    version_dir = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates.append(Path(sys.prefix) / "lib" / version_dir / "site-packages" / _LIB_NAME)
    candidates.append(Path(sys.base_prefix) / "lib" / version_dir / "site-packages" / _LIB_NAME)

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(path)
    return unique_candidates


def _site_packages_dirs() -> list[Path]:
    site_dirs: list[Path] = []

    try:
        site_dirs.extend(Path(path) for path in site.getsitepackages())
    except AttributeError:
        pass

    user_site = site.getusersitepackages()
    if user_site:
        site_dirs.append(Path(user_site))

    return site_dirs

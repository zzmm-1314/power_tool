# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    collect_dynamic_libs,
)

SPEC_DIR = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parent if SPEC_DIR.name == "build" else SPEC_DIR
print(f"[spec] PROJECT_ROOT={PROJECT_ROOT}")
# ============ 轻量收集：大库只拉核心子模块 + 动态库，data 交给内置 hook ============
LIGHT_LIBS = [
    "numpy",
    "scipy",
    "sklearn",
    "pandas",
]

# ============ 完整收集：内部 data 少、需要一起带走的库 ============
FULL_LIBS = [
    "desktop_app_source_updater",
    "flask",
    "flask_cors",
    "dotenv",
    "openpyxl",
    "pdfplumber",
    "pdfminer",
    "docxtpl",
    "docx",
    "bs4",
    "lxml",
    "joblib",
    "threadpoolctl",
    "jwt",
    "pymysql",
    "watchdog",
    "requests",
    "urllib3",
    "certifi",
    "charset_normalizer",
    "idna",
]

# ============ 显式补充的隐式依赖 ============
EXTRA_HIDDEN = [
    # jinja2 / docxtpl
    "jinja2",
    "jinja2.ext",
    "markupsafe",

    # pdfminer
    "pdfminer",
    "pdfminer.high_level",
    "pdfminer.pdfinterp",
    "pdfminer.layout",

    # openpyxl
    "et_xmlfile",

    # pandas 时间
    "pytz",
    "dateutil",
    "dateutil.tz",

    # sklearn Cython 子模块
    "sklearn.utils._typedefs",
    "sklearn.utils._heap",
    "sklearn.utils._sorting",
    "sklearn.utils._vector_sentinel",
    "sklearn.utils._weight_vector",
    "sklearn.utils.murmurhash",

    # jwt
    "jwt.algorithms",
    "jwt.api_jws",
    "jwt.api_jwt",

    # pymysql
    "pymysql.constants",
    "pymysql.converters",
    "pymysql.cursors",

    # flask / werkzeug
    "flask.json",
    "flask.json.provider",
    "werkzeug",
    "werkzeug.routing",
    "werkzeug.serving",
    "werkzeug.debug",

    # watchdog 平台观察者
    "watchdog.observers.winapi",
    "watchdog.observers.read_directory_changes",

    # ===== 关键修复：numpy.testing → unittest 依赖链 =====
    "unittest",
    "unittest.case",
    "unittest.loader",
    "unittest.main",
    "unittest.mock",
    "unittest.result",
    "unittest.runner",
    "unittest.signals",
    "unittest.suite",
    "unittest.util",
    "numpy.testing",
    "numpy.testing._private",
    "numpy.testing._private.utils",
]

datas, binaries, hiddenimports = [], [], list(EXTRA_HIDDEN)


def _exclude_tests(name: str) -> bool:
    """排除 *.tests / *.test.* 子模块，大幅减少隐藏导入"""
    lowered = name.lower()
    for seg in (".tests", ".test", "tests.", "test."):
        if seg in lowered:
            return False
    return True


# ============ 轻量收集 ============
for pkg in LIGHT_LIBS:
    try:
        hiddenimports += collect_submodules(pkg, filter=_exclude_tests)
        print(f"[spec] collect_submodules({pkg}) OK")
    except Exception as e:
        print(f"[spec] collect_submodules({pkg}) 失败: {e}")
    try:
        binaries += collect_dynamic_libs(pkg)
        print(f"[spec] collect_dynamic_libs({pkg}) OK")
    except Exception as e:
        print(f"[spec] collect_dynamic_libs({pkg}) 失败: {e}")

# ============ 完整收集 ============
for pkg in FULL_LIBS:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
        print(f"[spec] collect_all({pkg}) OK: datas={len(d)} binaries={len(b)} hidden={len(h)}")
    except Exception as e:
        print(f"[spec] collect_all({pkg}) 失败: {e}")

# ============ 图标 ============
# 依次尝试：项目根目录 app.ico → assets/app.ico
icon_candidates = [
    PROJECT_ROOT / "app.ico",
    PROJECT_ROOT / "assets" / "app.ico",
]
icon_path = next((p for p in icon_candidates if p.exists()), None)
if icon_path is None:
    print(f"[spec] 警告：未找到图标文件，已尝试: {[str(p) for p in icon_candidates]}")
else:
    print(f"[spec] icon={icon_path}")

# ============ Analysis ============
a = Analysis(
    ["launcher.py"],
    pathex=[
        str(PROJECT_ROOT),
        str(PROJECT_ROOT / "my_app_src"),
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 注意：不要排除 unittest / test / unittest.mock
        # numpy.testing 运行时需要 unittest.TestCase，排除会导致启动崩溃
        "tkinter.test",
        "pydoc_data",
        "doctest",
        "lib2to3",
        "pip",
        "setuptools",
        "wheel",
        # 可选：这些不影响功能，可减小体积
        "matplotlib",
        "IPython",
        "notebook",
        "jupyter",
        "pytest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="power_tool_launcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        "vcruntime140.dll",
        "python3*.dll",
        "libopenblas*.dll",
        "mkl_*.dll",
        "vcomp140.dll",
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path else None,
)
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec: 显式列出 my_app_src 需要的所有第三方依赖
打包命令：pyinstaller power_tool_launcher.spec
"""

hidden_imports = [
    # Flask 相关
    "flask",
    "flask_cors",
    "werkzeug",
    "jinja2",
    "click",
    "itsdangerous",
    "markupsafe",
    # 数据处理
    "pandas",
    "numpy",
    "openpyxl",
    "xlrd",
    "et_xmlfile",
    # HTML / XML 解析
    "bs4",
    "lxml",
    "lxml.etree",
    "lxml.html",
    # PDF 解析
    "pdfplumber",
    "pdfminer",
    "pdfminer.high_level",
    # Word 渲染
    "docxtpl",
    "docx",
    # 机器学习
    "sklearn",
    "sklearn.linear_model",
    "sklearn.preprocessing",
    "sklearn.model_selection",
    "scipy",
    # JWT / DB（预留）
    "jwt",
    "pymysql",
    "cryptography",
    # HTTP
    "requests",
    "urllib3",
    "certifi",
    "charset_normalizer",
    "idna",
    # 环境变量
    "dotenv",
    # 更新库
    "desktop_app_source_updater",
]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[
        # 如果 my_app_src 里有非 .py 资源需要一起打包进 exe，可在此声明；
        # 但本方案 my_app_src 放在 exe 外面，不需要打包进去
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
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
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico",
)
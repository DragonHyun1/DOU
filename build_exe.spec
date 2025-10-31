# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Collect all necessary data files
datas = [
    ('ui/*.ui', 'ui'),
    ('test_scenarios', 'test_scenarios'),
    ('lib', 'lib'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'pyqtgraph',
    'pandas',
    'openpyxl',
    'xlsxwriter',
    # Monsoon Power Monitor SDK
    'Monsoon',
    'Monsoon.HVPM',
    'Monsoon.sampleEngine',
    'MSPM',
    # Services
    'services',
    'services.adaptive_ui',
    'services.adb_service',
    'services.adb',
    'services.auto_test',
    'services.daq_collection_thread',
    'services.enhanced_test_engine',
    'services.hvpm',
    'services.ni_daq',
    'services.responsive_layout',
    'services.test_scenario_engine',
    'services.theme',
    'generated.main_ui',
    'lib.act_library',
    'lib.device',
    'lib.precond_library',
    'lib.utils',
    'test_scenarios.scenarios.common.base_scenario',
    'test_scenarios.scenarios.common.default_settings',
    'test_scenarios.scenarios.phone_app.phone_app_scenario',
    'test_scenarios.configs.test_config',
    'test_scenarios.configs.wifi_config',
    'ui.multi_channel_monitor',
    'ui.test_settings_dialog',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'tkinter',
        'matplotlib',
        '_tkinter',
        'tk',
        'tcl',
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
    name='DoU_Auto_Test_Toolkit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if you have one: icon='icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DoU_Auto_Test_Toolkit',
)

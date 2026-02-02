# -*- mode: python -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('instance', 'instance'),
    ],
    hiddenimports=[
        'flask',
        'flask_login',
        'sqlalchemy'
        'flask',
        'flask_sqlalchemy',
        'werkzeug.security'
    ],
    excludes=['venv'],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NMS Admin',
    icon=r'D:\device_monitoring_system\assests\app.ico',
    debug=False,
    console=False
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='NMS Admin'
)

# -*- mode: python -*-

block_cipher = None


a = Analysis(['runner.py'],
             pathex=['C:\\Users\\cmorikuni\\Google Drive\\Work\\RevaComm\\508_Testing\\pa11y_py_gen'],
             binaries=[],
             datas=[('.\\pa11y\\templates' ,'.\\pa11y\\templates')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='PyAdaScanner',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )

# -*- mode: python -*-

block_cipher = None

a = Analysis(['program.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['tqdm', 'scipy', 'pandas', 'sklearn', 'matplotlib', 'numpy', 'tensorflow'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# added for including the lpc21isp executables
a.datas += Tree('./exes', prefix='exes/')
a.datas += Tree('./firmwares', prefix='firmwares/')
a.datas += Tree('./icons', prefix='icons/')
a.datas += Tree('./images', prefix='images/')

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Programmer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False,
          icon='./programmer.ico')

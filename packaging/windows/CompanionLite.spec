from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parents[1]
datas = [(str(root / 'thirtytutors/static'), 'thirtytutors/static'),
         (str(root / 'LICENSE'), '.'), (str(root / 'build/licenses'), 'licenses'),
         (str(root / 'build/offline-tts'), 'offline-tts')]
datas += collect_data_files('webview') + copy_metadata('google-genai')
a = Analysis([str(root / 'thirtytutors/desktop_entry.py')], pathex=[str(root)],
             datas=datas, binaries=[(str(root/'build/offline-tts/espeak-ng.exe'),'offline-tts'),
                                    (str(root/'build/offline-tts/libespeak-ng.dll'),'offline-tts')],
             hiddenimports=collect_submodules('google.genai', filter=lambda name: not name.startswith('google.genai.tests')) + ['webview.platforms.winforms', 'webview.platforms.edgechromium', 'win32crypt'],
             excludes=['google.genai.tests','pytest','_pytest','torch','librosa','scipy','resemblyzer','webrtcvad','langfuse','PyQt5','PyQt6','PySide2','PySide6','tkinter','IPython'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CompanionLite',
          console=False, icon=str(root / 'thirtytutors/static/ThirtyTutors.ico'), upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='CompanionLite', upx=False)

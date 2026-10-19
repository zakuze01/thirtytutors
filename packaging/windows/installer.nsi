Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
Name "Companion Lite (private QA preview)"
OutFile "..\..\dist\CompanionLite-Preview-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\CompanionLite"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_OK "This build requires Windows 10/11 x64."
    Abort
  ${EndIf}
  SetRegView 32
  ReadRegStr $0 HKLM "SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
  StrCmp $0 "" 0 runtime_found
  ReadRegStr $0 HKCU "SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
  StrCmp $0 "" 0 runtime_found
  MessageBox MB_OK "Install Microsoft Edge WebView2 Evergreen Runtime, then run this installer again: https://developer.microsoft.com/microsoft-edge/webview2/"
  Abort
  runtime_found:
FunctionEnd

Section "Install"
  StrCpy $INSTDIR "$LOCALAPPDATA\Programs\CompanionLite"
  SetOutPath "$INSTDIR"
  File /r "..\..\dist\CompanionLite\*"
  File "..\..\README_WINDOWS.md"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$SMPROGRAMS\Companion Lite.lnk" "$INSTDIR\CompanionLite.exe"
  CreateShortcut "$DESKTOP\Companion Lite.lnk" "$INSTDIR\CompanionLite.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CompanionLite" "DisplayName" "Companion Lite (private QA preview)"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CompanionLite" "UninstallString" '$"$INSTDIR\Uninstall.exe$"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CompanionLite" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CompanionLite" "NoRepair" 1
SectionEnd

Section "Uninstall"
  StrCmp $INSTDIR "$LOCALAPPDATA\Programs\CompanionLite" 0 refuse
  Delete "$INSTDIR\CompanionLite.exe"
  Delete "$INSTDIR\README_WINDOWS.md"
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$SMPROGRAMS\Companion Lite.lnk"
  Delete "$DESKTOP\Companion Lite.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CompanionLite"
  IfSilent done
  MessageBox MB_YESNO|MB_DEFBUTTON2 "Delete ALL Companion Lite local profiles, keys, history and recovery data? Default: keep data." IDNO done
  RMDir /r "$LOCALAPPDATA\CompanionLite"
  Goto done
  refuse:
  MessageBox MB_OK "Unexpected install location. Uninstall cancelled."
  done:
SectionEnd

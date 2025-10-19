# Windows Installer Setup Guide for LIPM

This guide provides instructions for creating professional Windows installers for LIPM using various tools.

---

## Option 1: Inno Setup (Recommended)

**Inno Setup** is a free, feature-rich Windows installer creator.

### Prerequisites
- Download Inno Setup: https://jrsoftware.org/isdl.php
- Build LIPM executable first: `.\build.ps1`

### Installation
1. Download and install Inno Setup 6.x
2. Save the script below as `LIPM-Installer.iss`
3. Open in Inno Setup Compiler
4. Click "Build" → "Compile"

### Inno Setup Script

```iss
; LIPM - LinkedIn Personal Monitor Installer Script
; Created with Inno Setup 6

#define MyAppName "LIPM"
#define MyAppFullName "LinkedIn Personal Monitor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Aleksey Tkachyov"
#define MyAppURL "https://github.com/YourUsername/LIPM"
#define MyAppExeName "LIPM.exe"

[Setup]
; Basic Information
AppId={{A5B3C7D1-1234-5678-90AB-CDEF12345678}
AppName={#MyAppFullName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppFullName}
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=README.md
OutputDir=installer
OutputBaseFilename=LIPM-Setup-v{#MyAppVersion}
SetupIconFile=resources\icon.ico
; Uncomment if you have an icon file
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable
Source: "dist\LIPM-Package\LIPM.exe"; DestDir: "{app}"; Flags: ignoreversion

; Configuration files
Source: "dist\LIPM-Package\config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "dist\LIPM-Package\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

; Data directories
Source: "dist\LIPM-Package\data\*"; DestDir: "{app}\data"; Flags: ignoreversion createallsubdirs recursesubdirs
Source: "dist\LIPM-Package\logs\*"; DestDir: "{app}\logs"; Flags: ignoreversion createallsubdirs recursesubdirs

; Documentation
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "CONTRIBUTING.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "CODE_OF_CONDUCT.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppFullName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppFullName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppFullName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppFullName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppFullName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppFullName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\config.json"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks
    MsgBox('Installation complete!' + #13#10#13#10 + 
           'Before running LIPM, you will need:' + #13#10 +
           '1. LinkedIn account credentials' + #13#10 +
           '2. Telegram bot token (from @BotFather)' + #13#10 +
           '3. OpenAI API key' + #13#10#13#10 +
           'See README.md for detailed setup instructions.',
           mbInformation, MB_OK);
  end;
end;

function InitializeSetup(): Boolean;
begin
  // Check Windows version
  if not IsWin64 then
  begin
    MsgBox('This application requires Windows 10/11 (64-bit).', mbError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;
```

### Build Installer
```powershell
# Open Inno Setup Compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" LIPM-Installer.iss

# Output: installer\LIPM-Setup-v1.0.0.exe
```

---

## Option 2: NSIS (Nullsoft Scriptable Install System)

**NSIS** is another popular free installer creator.

### Prerequisites
- Download NSIS: https://nsis.sourceforge.io/Download
- Build LIPM executable first

### NSIS Script

Save as `LIPM-Installer.nsi`:

```nsis
; LIPM - LinkedIn Personal Monitor NSIS Installer Script

;--------------------------------
; Include Modern UI
!include "MUI2.nsh"

;--------------------------------
; General
Name "LIPM - LinkedIn Personal Monitor"
OutFile "installer\LIPM-Setup-v1.0.0.exe"
InstallDir "$PROGRAMFILES64\LIPM"
InstallDirRegKey HKLM "Software\LIPM" "Install_Dir"
RequestExecutionLevel admin

;--------------------------------
; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "resources\icon.ico"
!define MUI_UNICON "resources\icon.ico"

;--------------------------------
; Pages
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Languages
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Sections

Section "LIPM Application (required)" SecMain
  SectionIn RO
  
  ; Set output path
  SetOutPath $INSTDIR
  
  ; Install files
  File "dist\LIPM-Package\LIPM.exe"
  File "dist\LIPM-Package\README.md"
  File "LICENSE"
  
  ; Configuration
  SetOutPath $INSTDIR
  File "dist\LIPM-Package\config.json"
  
  ; Create directories
  CreateDirectory "$INSTDIR\data"
  CreateDirectory "$INSTDIR\logs"
  
  ; Data files
  SetOutPath $INSTDIR\data
  File "dist\LIPM-Package\data\posts.json"
  
  ; Write registry keys
  WriteRegStr HKLM "Software\LIPM" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LIPM" "DisplayName" "LIPM - LinkedIn Personal Monitor"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LIPM" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LIPM" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LIPM" "NoRepair" 1
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Start Menu Shortcuts" SecShortcuts
  CreateDirectory "$SMPROGRAMS\LIPM"
  CreateShortcut "$SMPROGRAMS\LIPM\LIPM.lnk" "$INSTDIR\LIPM.exe"
  CreateShortcut "$SMPROGRAMS\LIPM\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\LIPM.lnk" "$INSTDIR\LIPM.exe"
SectionEnd

;--------------------------------
; Descriptions

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Core application files (required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecShortcuts} "Start menu shortcuts"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Desktop shortcut"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstaller Section

Section "Uninstall"
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LIPM"
  DeleteRegKey HKLM "Software\LIPM"
  
  ; Remove files
  Delete "$INSTDIR\LIPM.exe"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\config.json"
  Delete "$INSTDIR\uninstall.exe"
  
  ; Remove directories
  RMDir /r "$INSTDIR\data"
  RMDir /r "$INSTDIR\logs"
  RMDir "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$SMPROGRAMS\LIPM\*.*"
  RMDir "$SMPROGRAMS\LIPM"
  Delete "$DESKTOP\LIPM.lnk"
SectionEnd
```

### Build with NSIS
```powershell
"C:\Program Files (x86)\NSIS\makensis.exe" LIPM-Installer.nsi
```

---

## Option 3: WiX Toolset (Advanced)

**WiX** creates MSI installers (most professional option).

### Prerequisites
- Download WiX: https://wixtoolset.org/
- Requires XML knowledge

### Quick WiX Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="LIPM" Language="1033" Version="1.0.0" 
           Manufacturer="Aleksey Tkachyov" UpgradeCode="PUT-GUID-HERE">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />
    
    <MajorUpgrade DowngradeErrorMessage="A newer version is already installed." />
    <MediaTemplate EmbedCab="yes" />
    
    <Feature Id="ProductFeature" Title="LIPM" Level="1">
      <ComponentGroupRef Id="ProductComponents" />
    </Feature>
  </Product>
  
  <Fragment>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFiles64Folder">
        <Directory Id="INSTALLFOLDER" Name="LIPM" />
      </Directory>
    </Directory>
  </Fragment>
  
  <Fragment>
    <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
      <Component Id="MainExecutable">
        <File Source="dist\LIPM-Package\LIPM.exe" />
      </Component>
    </ComponentGroup>
  </Fragment>
</Wix>
```

---

## Option 4: PyInstaller + MSI (Simple)

Create MSI directly from PyInstaller output.

### Using cx_Freeze
```python
# setup.py
from cx_Freeze import setup, Executable

setup(
    name="LIPM",
    version="1.0.0",
    description="LinkedIn Personal Monitor",
    executables=[Executable("linkedin_post_monitor/main.py", 
                           target_name="LIPM.exe",
                           base="Win32GUI")],
    options={
        "build_exe": {
            "packages": ["playwright", "openai", "telegram", "customtkinter"],
            "include_files": [("config.template.json", "config.json"), "README.md"]
        },
        "bdist_msi": {
            "upgrade_code": "{PUT-GUID-HERE}",
            "add_to_path": False,
            "initial_target_dir": r"[ProgramFilesFolder]\LIPM"
        }
    }
)
```

Build MSI:
```powershell
python setup.py bdist_msi
```

---

## Comparison Table

| Feature | Inno Setup | NSIS | WiX | cx_Freeze |
|---------|------------|------|-----|-----------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Professional** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Free** | ✅ | ✅ | ✅ | ✅ |
| **Output Format** | .exe | .exe | .msi | .msi |
| **File Size** | Small | Small | Medium | Medium |
| **Customization** | High | Very High | Highest | Medium |
| **Learning Curve** | Low | Medium | High | Low |

---

## Recommended Workflow

### 1. **For Quick Testing**: Use PyInstaller only
```powershell
.\build.ps1
# Distribute: dist\LIPM-Package.zip
```

### 2. **For Distribution**: Use Inno Setup
```powershell
# Build executable
.\build.ps1

# Create installer
iscc LIPM-Installer.iss

# Distribute: installer\LIPM-Setup-v1.0.0.exe
```

### 3. **For Enterprise**: Use WiX Toolset
- Creates proper MSI
- Supports Group Policy deployment
- Better uninstallation
- Corporate standard

---

## Installer Checklist

### Must Include
- ✅ Main executable (LIPM.exe)
- ✅ Configuration template (config.json)
- ✅ Documentation (README.md)
- ✅ License file (LICENSE)
- ✅ Empty data/logs directories
- ✅ Uninstaller

### Should Include
- ✅ Desktop shortcut (optional)
- ✅ Start menu entry
- ✅ Version information
- ✅ Publisher information
- ✅ Application icon
- ✅ Pre/post-install messages

### Optional
- ⭐ Auto-update check
- ⭐ Prerequisites check (Windows version)
- ⭐ Installation wizard customization
- ⭐ Silent installation support

---

## Code Signing (Optional but Recommended)

### Why Sign?
- Removes "Unknown publisher" warning
- Builds user trust
- Required for some antivirus whitelisting

### How to Sign

1. **Get Certificate**
   - Buy from: DigiCert, Sectigo, GlobalSign
   - Cost: $200-400/year
   - Alternative: Free trial certificates

2. **Sign Executable**
   ```powershell
   # Using signtool
   signtool sign /f MyCert.pfx /p PASSWORD /t http://timestamp.digicert.com dist\LIPM.exe
   ```

3. **Sign Installer**
   ```powershell
   signtool sign /f MyCert.pfx /p PASSWORD installer\LIPM-Setup-v1.0.0.exe
   ```

---

## Auto-Update Feature

### Simple Update Check
Add to your application:

```python
import requests

def check_for_updates():
    try:
        response = requests.get("https://api.github.com/repos/YourUsername/LIPM/releases/latest")
        latest_version = response.json()["tag_name"]
        current_version = "v1.0.0"
        
        if latest_version > current_version:
            return True, latest_version
        return False, None
    except:
        return False, None
```

### Advanced: Sparkle/WinSparkle
- Automatic update framework
- Background downloading
- Silent installation

---

## Distribution Platforms

### 1. **GitHub Releases** (Recommended)
- Free hosting
- Version management
- Automatic notifications
- Asset downloads tracked

### 2. **Microsoft Store**
- Requires developer account ($19)
- Automatic updates
- User trust
- Review process

### 3. **Chocolatey**
- Windows package manager
- Easy distribution
- Command-line installation

### 4. **Your Website**
- Full control
- Custom branding
- Download analytics

---

## Testing Your Installer

### Test Checklist
1. ✅ Install on clean Windows VM
2. ✅ Check all files are copied
3. ✅ Verify shortcuts work
4. ✅ Test application launches
5. ✅ Check uninstaller works
6. ✅ Verify no leftover files after uninstall
7. ✅ Test upgrade installation
8. ✅ Check Windows Event Viewer for errors

### Test Environments
- Windows 10 (64-bit)
- Windows 11 (64-bit)
- Fresh install (no Python)
- With antivirus enabled

---

## Support & Resources

### Inno Setup
- Documentation: https://jrsoftware.org/ishelp/
- Examples: `C:\Program Files (x86)\Inno Setup 6\Examples\`
- Forum: https://stackoverflow.com/questions/tagged/inno-setup

### NSIS
- Documentation: https://nsis.sourceforge.io/Docs/
- Wiki: https://nsis.sourceforge.io/Main_Page
- Plugins: https://nsis.sourceforge.io/Category:Plugins

### WiX
- Documentation: https://wixtoolset.org/documentation/
- Tutorial: https://www.firegiant.com/wix/tutorial/

---

**Recommendation for LIPM**: Start with **Inno Setup** - it's free, easy to use, produces professional installers, and has excellent documentation.

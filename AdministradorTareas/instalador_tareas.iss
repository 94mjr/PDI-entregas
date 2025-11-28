; -------------------------------------------
; Instalador del Administrador de Tareas
; Creado con Inno Setup
; -------------------------------------------

[Setup]
AppName=Administrador de Tareas
AppVersion=1.0
AppPublisher=TuNombre
DefaultDirName={autopf}\AdministradorTareas
DefaultGroupName=Administrador de Tareas
OutputBaseFilename=Instalador_Administrador_Tareas
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Copia el ejecutable y los archivos de configuración
Source: "dist\app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.xml"; DestDir: "{app}"; Flags: ignoreversion
; (Podés agregar más archivos si querés incluir otros recursos)
; Source: "imagenes\*"; DestDir: "{app}\imagenes"; Flags: recursesubdirs

[Icons]
; Crea accesos directos en el menú inicio y escritorio
Name: "{autoprograms}\Administrador de Tareas"; Filename: "{app}\app.exe"
Name: "{autodesktop}\Administrador de Tareas"; Filename: "{app}\app.exe"

[Run]
; Ejecutar automáticamente después de la instalación
Filename: "{app}\app.exe"; Description: "Ejecutar Administrador de Tareas"; Flags: nowait postinstall skipifsilent

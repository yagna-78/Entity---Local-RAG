$WshShell = New-Object -ComObject WScript.Shell
$StartupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ShortcutPath = "$StartupDir\Start_RAG_Chatbot.lnk"
$TargetFile = "$PSScriptRoot\run_app.bat"

if (-not (Test-Path $TargetFile)) {
    Write-Error "Could not find run_app.bat in current directory: $PSScriptRoot"
    exit 1
}

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetFile
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.WindowStyle = 7 # 7 = Minimized
$Shortcut.Description = "Starts Local RAG Chatbot Minimized"
$Shortcut.Save()

Write-Host "Success! Shortcut created at:`n$ShortcutPath"
Write-Host "The ChatBot server will now start automatically (minimized) whenever you log in to Windows."

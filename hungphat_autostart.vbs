Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strBatPath = "C:\Users\Lenovo\OneDrive\Tài liệu\Đề 4 Hưng phát\hungphat_background.bat"

If fso.FileExists(strBatPath) Then
    ' Run completely silent in background (0 = hide window, False = do not wait)
    WshShell.Run "cmd.exe /c """ & strBatPath & """", 0, False
End If

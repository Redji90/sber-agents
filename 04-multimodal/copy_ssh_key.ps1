$sourceFile = "C:\.ssh\immers-vm.pem"
$destDir = "$env:USERPROFILE\.ssh"
$destFile = "$destDir\immers-vm.pem"

# Create destination directory if it doesn't exist
if (!(Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

# Try to read the source file
try {
    $content = [System.IO.File]::ReadAllBytes($sourceFile)
    [System.IO.File]::WriteAllBytes($destFile, $content)
    Write-Host "Key copied successfully"
    
    # Set permissions
    icacls $destFile /inheritance:r /grant:r "LENOVO\Lenovo:(R)" | Out-Null
    Write-Host "Permissions set for $destFile"
    Write-Host "You can now use: ssh -i $destFile ubuntu@195.209.210.171"
} catch {
    Write-Host "Error: $_"
    Write-Host "Trying alternative method..."
    # Alternative: try using robocopy or xcopy
}


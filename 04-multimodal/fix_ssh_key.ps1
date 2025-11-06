$file = "C:\.ssh\immers-vm.pem"
$acl = Get-Acl $file
$acl.SetAccessRuleProtection($true, $false)
$username = $env:USERNAME
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule($username, "Read", "Allow")
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) }
$acl.AddAccessRule($accessRule)
Set-Acl $file $acl
Write-Host "Permissions fixed for $file"


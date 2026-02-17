# 上传项目到超智引擎服务器
# 服务器信息
$serverIP = "60.10.230.136"
$serverPort = "3910"
$serverUser = "root"
$keyFile = "@KeyPair-6e51.pem"
$remotePath = "/root/test_2"

# 检查密钥文件是否存在
if (-not (Test-Path $keyFile)) {
    Write-Host "错误: 找不到密钥文件 $keyFile" -ForegroundColor Red
    Write-Host "请确保密钥文件在当前目录，或提供完整路径" -ForegroundColor Yellow
    exit 1
}

# 设置密钥文件权限（Windows上可能需要）
Write-Host "准备上传项目到服务器..." -ForegroundColor Green
Write-Host "服务器: $serverUser@$serverIP:$serverPort" -ForegroundColor Cyan
Write-Host "目标路径: $remotePath" -ForegroundColor Cyan

# 使用 scp 上传整个项目目录
# 排除不需要上传的文件和目录
$excludePatterns = @(
    "__pycache__",
    "*.pyc",
    ".git",
    "*.rar",
    "*.tar.gz",
    "*.bat",
    "*.ps1",
    "*.sh",
    "*.md",
    "uploads",
    "test_2.rar",
    "backup_*.tar.gz"
)

# 创建临时排除文件列表
$excludeFile = "exclude_list.txt"
$excludePatterns | Out-File -FilePath $excludeFile -Encoding UTF8

Write-Host "`n开始上传文件..." -ForegroundColor Green

# 使用 rsync 风格的排除（如果可用）或逐个文件上传
# Windows 上使用 scp -r 递归上传
$scpCommand = "scp -P $serverPort -i `"$keyFile`" -r -o StrictHostKeyChecking=no . $serverUser@${serverIP}:$remotePath"

Write-Host "执行命令: $scpCommand" -ForegroundColor Yellow
Invoke-Expression $scpCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n上传成功！" -ForegroundColor Green
    Write-Host "项目已上传到: $remotePath" -ForegroundColor Cyan
} else {
    Write-Host "`n上传失败，错误代码: $LASTEXITCODE" -ForegroundColor Red
}

# 清理临时文件
if (Test-Path $excludeFile) {
    Remove-Item $excludeFile
}


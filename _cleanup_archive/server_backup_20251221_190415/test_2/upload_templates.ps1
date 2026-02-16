# 上传模板文件到服务器
# 编码: UTF-8

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "上传模板文件到服务器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 配置信息
$KEY_FILE = "$env:USERPROFILE\Downloads\KeyPair-6418.pem"
$PORT = 2950
$SERVER = "root@60.10.230.156"
$REMOTE_DIR = "/var/www/html"

# 检查密钥文件
if (-not (Test-Path $KEY_FILE)) {
    Write-Host "[错误] 找不到密钥文件: $KEY_FILE" -ForegroundColor Red
    Write-Host "请检查文件路径是否正确" -ForegroundColor Red
    pause
    exit 1
}

# 获取当前脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TemplatesPath = Join-Path $ScriptDir "templates"

# 检查 templates 目录
if (-not (Test-Path $TemplatesPath)) {
    Write-Host "[错误] 找不到 templates 目录: $TemplatesPath" -ForegroundColor Red
    Write-Host "请确保在项目根目录运行此脚本" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[1/3] 上传 templates 目录..." -ForegroundColor Yellow
Write-Host "源路径: $TemplatesPath" -ForegroundColor Gray
Write-Host "目标: $SERVER`:$REMOTE_DIR/templates/" -ForegroundColor Gray
Write-Host ""

# 上传文件
$scpArgs = @(
    "-i", "`"$KEY_FILE`"",
    "-P", $PORT,
    "-r",
    "`"$TemplatesPath`"",
    "${SERVER}:${REMOTE_DIR}/"
)

$scpProcess = Start-Process -FilePath "scp" -ArgumentList $scpArgs -Wait -NoNewWindow -PassThru

if ($scpProcess.ExitCode -ne 0) {
    Write-Host "[错误] 上传 templates 目录失败，退出码: $($scpProcess.ExitCode)" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[2/3] 设置文件权限..." -ForegroundColor Yellow

# 设置权限
$sshArgs = @(
    "-i", "`"$KEY_FILE`"",
    "-p", $PORT,
    $SERVER,
    "chmod -R 755 ${REMOTE_DIR}/templates/"
)

$sshProcess = Start-Process -FilePath "ssh" -ArgumentList $sshArgs -Wait -NoNewWindow -PassThru

Write-Host "[3/3] 重启 Flask 服务..." -ForegroundColor Yellow

# 尝试重启服务（优先使用 systemd）
$restartCmd = "sudo systemctl restart flask-app.service 2>/dev/null || (screen -S flask_app -X quit 2>/dev/null; cd $REMOTE_DIR && screen -dmS flask_app /usr/local/python3.11/bin/python3 app.py 2>/dev/null || (pkill -f 'python3.*app.py' 2>/dev/null; cd $REMOTE_DIR && nohup /usr/local/python3.11/bin/python3 app.py > flask_app.log 2>&1 &))"

$sshArgs2 = @(
    "-i", "`"$KEY_FILE`"",
    "-p", $PORT,
    $SERVER,
    $restartCmd
)

$sshProcess2 = Start-Process -FilePath "ssh" -ArgumentList $sshArgs2 -Wait -NoNewWindow -PassThru

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "上传完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "已上传以下文件：" -ForegroundColor Cyan
Write-Host "  - templates/index.html" -ForegroundColor Gray
Write-Host "  - templates/index_new.html" -ForegroundColor Gray
Write-Host "  - templates/ 目录下的其他文件" -ForegroundColor Gray
Write-Host ""
Write-Host "文件已上传到：${SERVER}:${REMOTE_DIR}/templates/" -ForegroundColor Cyan
Write-Host ""
Write-Host "服务已尝试重启，请检查服务状态：" -ForegroundColor Yellow
$checkCmd = "sudo systemctl status flask-app.service || ps aux | grep 'python3.*app.py'"
Write-Host "  ssh -i `"$KEY_FILE`" -p $PORT $SERVER `"$checkCmd`"" -ForegroundColor Gray
Write-Host ""
pause





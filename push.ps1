#requires -version 5.0
<#
.SYNOPSIS
  把 docs-cockpit 推到 GitHub · 一键脚本

.DESCRIPTION
  沙箱里没有 GitHub auth · 已经在本地准备好 git bundle / .git tarball。
  这个脚本在你机器上完成最后一公里:
    1. 清掉沙箱遗留的半破 .git/(沙箱权限问题 · 你本地能删)
    2. 从 bundle 还原完整 git 仓库(含 main 分支 + 1 commit · hash de1da78)
    3. 接上 origin remote
    4. git push -u origin main

  跑完后这两个 hidden 文件可以删:
    .docs-cockpit.bundle / .docs-cockpit-git-bundle.tar.gz

.NOTES
  前置:
  - 你机器有 git(检测一下:`git --version`)
  - 你已经在 https://github.com/Guohao1020/docs-cockpit 建了仓库(空仓库即可)
  - 你机器对 github.com 的 auth 通(SSH key / token / Git Credential Manager)
#>

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "==> docs-cockpit push helper" -ForegroundColor Cyan
Write-Host "    cwd: $PWD"
Write-Host ""

# 1. 检查依赖
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host "ERROR: git 未安装 · 装 git for Windows 后再跑" -ForegroundColor Red
  exit 1
}

$bundlePath = Join-Path $PSScriptRoot ".docs-cockpit.bundle"
if (-not (Test-Path $bundlePath)) {
  Write-Host "ERROR: 找不到 $bundlePath" -ForegroundColor Red
  Write-Host "       这个文件应该由沙箱生成。如果没有,可以改成手工 init/commit/push。" -ForegroundColor Red
  exit 1
}

# 2. 清沙箱遗留的破 .git/
if (Test-Path .git) {
  Write-Host "==> 清沙箱遗留的 .git/ ..." -ForegroundColor Yellow
  Remove-Item -Recurse -Force .git
}

# 3. 从 bundle 还原仓库 · 用 init + fetch 模式 · 不动现有工作区文件
Write-Host "==> 从 bundle 还原 git 历史 ..." -ForegroundColor Cyan
git init -b main | Out-Null
git fetch $bundlePath main:main 2>&1 | Out-Host
git reset --soft main
git checkout main 2>&1 | Out-Host

# 4. 验证工作区干净(bundle 里 commit 的文件 vs 当前文件应该一致)
$diffOutput = git status --porcelain
if ($diffOutput) {
  Write-Host "==> 工作区与 bundle 有差异(可能是 line ending / 你后改的):" -ForegroundColor Yellow
  Write-Host $diffOutput
  Write-Host ""
  $confirm = Read-Host "继续 push 当前 bundle 的 commit?(y/N)"
  if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "已停止 · 你可以先 git add/commit 把变更收进再 push" -ForegroundColor Yellow
    exit 0
  }
}

# 5. 接 remote · 然后 push
$remoteUrl = "https://github.com/Guohao1020/docs-cockpit.git"
Write-Host "==> 接 origin = $remoteUrl ..." -ForegroundColor Cyan
$existing = git remote 2>&1 | Select-String -Pattern '^origin$' -Quiet
if ($existing) {
  git remote set-url origin $remoteUrl
} else {
  git remote add origin $remoteUrl
}

Write-Host "==> push ..." -ForegroundColor Cyan
git push -u origin main

Write-Host ""
Write-Host "✓ done · 看看 https://github.com/Guohao1020/docs-cockpit" -ForegroundColor Green
Write-Host ""
Write-Host "可清理的文件:"
Write-Host "  Remove-Item .docs-cockpit.bundle, .docs-cockpit-git-bundle.tar.gz, push.ps1" -ForegroundColor Gray

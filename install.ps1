# WeWrite Windows 安装脚本（对应 macOS/Linux 的 install.sh）
#
# 提供原生 PowerShell 安装路径：
#   1) 安装 wewrite CLI（优先 uv tool install，其次 pipx，再次 python -m pip install --user，
#      最后回退仓库内 venv 并把 wewrite.exe 链接进 ~/.local/bin）
#   2) 把 skills/wewrite* 复制到 Agent Skills 标准目录：
#      ~/.claude/skills、~/.agents/skills，以及检测到的 ~/.openclaw、~/.codex、~/.workbuddy
#      （默认【复制】而非符号链接，避开原生 Windows 软链权限坑；可用 -UseSymlinks 改回软链）
#   3) 若仓库根存在旧版状态（style.yaml / history.yaml / config.yaml），运行 wewrite migrate
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# 可选参数：
#   -UseSymlinks   用符号链接代替复制（需管理员或开发者模式，否则自动回退复制）
#   -SkillsOnly    只复制 skills，不安装 CLI
#   -CliOnly       只安装 CLI，不复制 skills
#
# 环境变量覆盖（与 install.sh 一致）：
#   CLAUDE_SKILLS_DIR / AGENTS_SKILLS_DIR / WORKBUDDY_SKILLS_DIR

[CmdletBinding()]
param(
    [switch]$UseSymlinks,
    [switch]$SkillsOnly,
    [switch]$CliOnly
)

$ErrorActionPreference = 'Continue'   # 单步失败不中断整体安装
$REPO       = $PSScriptRoot
$SKILLS_SRC = Join-Path $REPO 'skills'

function Write-Step($msg) { Write-Host "-> $msg" }
function Write-Ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[X] $msg" -ForegroundColor Red }

# 找到一个可用的 Python 启动器（Windows 上 python 或 py 均可）
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = 'python' }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = 'py' }

# ---------------- 1) wewrite CLI ----------------
if (-not $CliOnly) {
    Write-Step "安装 wewrite CLI ..."
    $cliInstalled = $false

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv tool install --force wewrite
        if ($?) { $cliInstalled = $true }
    }
    if (-not $cliInstalled -and (Get-Command pipx -ErrorAction SilentlyContinue)) {
        pipx install --force wewrite
        if ($?) { $cliInstalled = $true }
    }
    if (-not $cliInstalled -and $py) {
        # 用户级安装：脚本进 %APPDATA%\Python\Scripts（通常在 PATH 上）
        & $py -m pip install --user --upgrade wewrite
        if ($?) { $cliInstalled = $true }
    }

    # 回退：仓库内 venv（绕过 PEP 668 / 离线场景）
    if (-not $cliInstalled) {
        Write-Warn "未找到 uv/pipx 或用户级安装失败，回退仓库内 venv"
        if (-not (Test-Path (Join-Path $REPO 'pyproject.toml'))) {
            Write-Err "仓库内无 pyproject.toml，无法 venv 回退。请先安装 Python 3.11+ 并确保网络可用。"
            exit 1
        }
        if (-not $py) {
            Write-Err "未找到 python / py。请先安装 Python 3.11+（https://www.python.org/downloads/windows/）。"
            exit 1
        }
        $venv = Join-Path $REPO '.venv'
        if (-not (Test-Path $venv)) { & $py -m venv $venv }
        & (Join-Path $venv 'Scripts\python.exe') -m pip install --upgrade pip *> $null
        & (Join-Path $venv 'Scripts\python.exe') -m pip install -e $REPO
        $cliExe  = Join-Path $venv 'Scripts\wewrite.exe'
        $binDir  = Join-Path $HOME '.local\bin'
        New-Item -ItemType Directory -Force -Path $binDir | Out-Null
        Copy-Item -Force -Destination (Join-Path $binDir 'wewrite.exe') $cliExe
        Write-Warn "已将 venv 内的 wewrite.exe 复制到 $binDir；请确认该目录在 PATH 中。"
    }

    if (Get-Command wewrite -ErrorAction SilentlyContinue) {
        Write-Ok "wewrite CLI 就绪: $((Get-Command wewrite).Source)"
    } else {
        Write-Warn "当前会话未找到 wewrite，请重开终端或检查 PATH（uv/pipx 用户 Scripts 目录）。"
    }
}

# ---------------- 2) skills 复制 ----------------
if (-not $SkillsOnly) {
    # 基础两个 harness 目录（支持环境变量覆盖）
    $claudeDir = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME '.claude\skills' }
    $agentsDir = if ($env:AGENTS_SKILLS_DIR) { $env:AGENTS_SKILLS_DIR } else { Join-Path $HOME '.agents\skills' }
    $dests = @($claudeDir, $agentsDir)

    # 检测到的 harness 目录（仅当其家目录已存在才加入）
    $detect = @(
        (Join-Path $HOME '.openclaw\skills'),
        (Join-Path $HOME '.codex\skills'),
        (Join-Path $HOME '.workbuddy\skills')
    )
    foreach ($d in $detect) {
        if (Test-Path (Split-Path $d)) { $dests += $d }
    }
    # WorkBuddy 也可用环境变量精确指定（如项目级 .workbuddy/skills）
    if ($env:WORKBUDDY_SKILLS_DIR) { $dests += $env:WORKBUDDY_SKILLS_DIR }

    if (Test-Path $SKILLS_SRC) {
        foreach ($target in $dests) {
            try {
                New-Item -ItemType Directory -Force -Path $target | Out-Null
                $count = 0
                foreach ($d in (Get-ChildItem $SKILLS_SRC -Directory -Filter 'wewrite*')) {
                    $dest = Join-Path $target $d.Name
                    if ($UseSymlinks) {
                        # 尝试符号链接；若权限不足则自动回退为复制
                        try {
                            if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
                            New-Item -ItemType SymbolicLink -Path $dest -Target $d.FullName -ErrorAction Stop | Out-Null
                        } catch {
                            if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
                            Copy-Item -Force -Recurse $d.FullName $dest
                        }
                    } else {
                        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
                        Copy-Item -Force -Recurse $d.FullName $dest
                    }
                    $count++
                }
                Write-Ok "已复制 $count 个 skill 到 $target"
            } catch {
                Write-Warn "复制 skills 到 $target 失败: $_"
            }
        }
        Write-Host "  单独激活示例：/wewrite-topic 选题、/wewrite-review 自检、/wewrite-rewrite 多平台改写"
    } else {
        Write-Warn "未找到 $SKILLS_SRC，跳过 skill 复制。"
    }
}

# ---------------- 3) 旧状态迁移（v2.1 之前状态在仓库根）----------------
if ((Get-Command wewrite -ErrorAction SilentlyContinue) -and (Test-Path $REPO)) {
    if ((Test-Path (Join-Path $REPO 'style.yaml')) -or
        (Test-Path (Join-Path $REPO 'history.yaml')) -or
        (Test-Path (Join-Path $REPO 'config.yaml'))) {
        Write-Step "检测到仓库根有旧版用户状态，迁移到 $(wewrite home) ..."
        wewrite migrate --from $REPO
    }
}

Write-Host ""
$homedir = if (Get-Command wewrite -ErrorAction SilentlyContinue) { wewrite home } else { Join-Path $HOME '.wewrite' }
Write-Ok "完成。状态目录: $homedir"

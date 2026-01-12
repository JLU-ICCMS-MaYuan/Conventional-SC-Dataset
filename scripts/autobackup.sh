#!/usr/bin/env bash
# 自动备份调度脚本：支持日备份/周备份及远程保留策略
set -euo pipefail

usage() {
    cat <<'EOF'
用法:
  ./scripts/autobackup.sh -m day   # 每日备份（保留 14 个副本）
  ./scripts/autobackup.sh -m week  # 每周备份（保留 4 个副本）

可用环境变量:
  BACKUP_REMOTE_HOST  目标服务器
  BACKUP_REMOTE_PORT  SSH 端口
  BACKUP_REMOTE_USER  SSH 用户
  BACKUP_REMOTE_DIR   远程目录 (默认 backups/conventional-sc)
  BACKUP_REMOTE_PASS  SSH 密码 (默认空，建议使用密钥)
  BACKUP_WORKDIR      本地临时目录 (默认 ./backups)
  DATABASE_PATH       SQLite 文件 (默认 ./data/superconductor.db)
EOF
}

run_with_auth() {
    local tool="$1"; shift
    if [[ -n "$ssh_password" ]]; then
        if command -v sshpass >/dev/null 2>&1; then
            sshpass -p "$ssh_password" "$tool" "$@"
        else
            echo "⚠️ 未安装 sshpass，将进入交互式 $tool"
            "$tool" "$@"
        fi
    else
        "$tool" "$@"
    fi
}

cleanup_remote() {
    local prefix="$1"
    local keep="$2"
    local list_cmd="ls -1t ${remote_dir}/${prefix}_*.tar.gz 2>/dev/null || true"
    echo "==> 远程保留策略: ${prefix} 保留最新 ${keep} 个"
    mapfile -t files < <(run_with_auth ssh "${ssh_opts[@]}" "${remote_user}@${remote_host}" "$list_cmd")
    if [[ ${#files[@]} -le "$keep" ]]; then
        echo "当前 ${#files[@]} 个备份，无需清理"
        return
    fi
    local to_delete=("${files[@]:$keep}")
    for file in "${to_delete[@]}"; do
        echo " - 删除旧备份: $file"
        run_with_auth ssh "${ssh_opts[@]}" "${remote_user}@${remote_host}" "rm -f $file"
    done
}

cleanup_local() {
    local prefix="$1"
    local keep="$2"
    local backup_dir="${BACKUP_WORKDIR:-${ROOT_DIR}/backups}"
    mapfile -t files < <(ls -1t "${backup_dir}/${prefix}_*.tar.gz" 2>/dev/null || true)
    if [[ ${#files[@]} -le "$keep" ]]; then
        return
    fi
    local to_delete=("${files[@]:$keep}")
    for file in "${to_delete[@]}"; do
        echo " - 删除本地旧备份: $file"
        rm -f "$file"
    done
}

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

mode=""
while getopts ":m:" opt; do
    case "$opt" in
        m) mode="$OPTARG" ;;
        *) usage; exit 1 ;;
    esac
done

if [[ -z "$mode" ]]; then
    usage
    exit 1
fi

case "$mode" in
    day) backup_prefix="backup_day"; retention=14 ;;
    week) backup_prefix="backup_week"; retention=4 ;;
    *) echo "不支持的模式：$mode（仅支持 day/week）"; exit 1 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${BACKUP_REMOTE_HOST:=example.com}"
: "${BACKUP_REMOTE_PORT:=example_account}"
: "${BACKUP_REMOTE_USER:=example_user}"
: "${BACKUP_REMOTE_DIR:=backups/conventional-sc}"
: "${BACKUP_REMOTE_PASS:=example_password}"

remote_host="$BACKUP_REMOTE_HOST"
remote_port="$BACKUP_REMOTE_PORT"
remote_user="$BACKUP_REMOTE_USER"
remote_dir="$BACKUP_REMOTE_DIR"
ssh_password="$BACKUP_REMOTE_PASS"
ssh_opts=(-p "$remote_port" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)

echo "==> 开始 ${mode} 模式备份（PREFIX=${backup_prefix}, 保留 ${retention} 个）"
BACKUP_PREFIX="$backup_prefix" \
BACKUP_REMOTE_HOST="$remote_host" \
BACKUP_REMOTE_PORT="$remote_port" \
BACKUP_REMOTE_USER="$remote_user" \
BACKUP_REMOTE_DIR="$remote_dir" \
BACKUP_REMOTE_PASS="$ssh_password" \
./scripts/remote_backup.sh -b

cleanup_remote "$backup_prefix" "$retention"
cleanup_local "$backup_prefix" "$retention"

echo "✅ ${mode} 模式备份完成"

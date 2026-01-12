#!/usr/bin/env bash
# 远程备份管理脚本
# -b: 备份本地数据库并上传
# -l: 列出远程备份
# -r <filename>: 下载远程备份并恢复到本地
set -euo pipefail

usage() {
    cat <<'EOF'
用法:
  ./scripts/remote_backup.sh -b                      # 生成备份并上传
  ./scripts/remote_backup.sh -l                      # 列出远程目录的备份
  ./scripts/remote_backup.sh -r backup_xxx.tar.gz    # 下载并恢复指定备份

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

list_remote_backups() {
    echo "==> 列出 ${remote_user}@${remote_host}:${remote_dir} 的备份"
    if ! run_with_auth ssh "${ssh_opts[@]}" "${remote_user}@${remote_host}" "ls -lh ${remote_dir}"; then
        echo "❌ 无法连接远程服务器，检查 BACKUP_REMOTE_HOST/BACKUP_REMOTE_PORT 或网络。"
        exit 1
    fi
}

perform_backup() {
    local timestamp backup_dir db_path json_path db_copy archive_path
: "${BACKUP_PREFIX:=backup}"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="${BACKUP_WORKDIR:-${ROOT_DIR}/backups}"
mkdir -p "$backup_dir"

db_path="${DATABASE_PATH:-${ROOT_DIR}/data/superconductor.db}"
json_path="${backup_dir}/data_export_${timestamp}.json"
db_copy="${backup_dir}/superconductor_${timestamp}.db"
archive_filename="${BACKUP_PREFIX}_${timestamp}.tar.gz"
archive_path="${backup_dir}/${archive_filename}"

    echo "==> 导出 JSON 数据到 ${json_path}"
    python -m backend.export_data "$json_path"
    if [[ ! -f "$json_path" ]]; then
        echo "❌ 未找到导出的 JSON 文件：$json_path"
        exit 1
    fi

    echo "==> 复制数据库文件到 ${db_copy}"
    cp "$db_path" "$db_copy"

echo "==> 打包归档 ${archive_path}"
tar -czf "$archive_path" -C "$backup_dir" "$(basename "$json_path")" "$(basename "$db_copy")"

    echo "==> 确保远程目录 ${remote_dir} 存在"
    run_with_auth ssh "${ssh_opts[@]}" "${remote_user}@${remote_host}" "mkdir -p ${remote_dir}"

    echo "==> 上传至 ${remote_user}@${remote_host}:${remote_dir}"
    run_with_auth scp -P "$remote_port" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        "$archive_path" "${remote_user}@${remote_host}:${remote_dir}/"

    echo "==> 清理本地中间文件"
    rm -f "$json_path" "$db_copy"

    echo "🎉 备份完成：${archive_path} 已上传"
    echo "REMOTE_BACKUP_FILE=${archive_filename}"
}

restore_backup() {
    local filename="$1"
    if [[ -z "$filename" ]]; then
        echo "❌ 需要提供备份文件名，例如 backup_20260112_101848.tar.gz"
        exit 1
    fi

    local backup_dir local_archive
    backup_dir="${BACKUP_WORKDIR:-${ROOT_DIR}/backups}"
    mkdir -p "$backup_dir"
    local_archive="${backup_dir}/${filename}"

    echo "==> 下载 ${filename} 到 ${local_archive}"
    run_with_auth scp -P "$remote_port" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        "${remote_user}@${remote_host}:${remote_dir}/${filename}" "$local_archive"

    echo "==> 解压 ${local_archive}"
    tar -xzf "$local_archive" -C "$backup_dir"

    local db_file json_file
    db_file="$(find "$backup_dir" -maxdepth 1 -name "superconductor_*.db" -print -quit)"
    json_file="$(find "$backup_dir" -maxdepth 1 -name "data_export_*.json" -print -quit)"

    if [[ -z "$db_file" ]]; then
        echo "❌ 解压后未找到 superconductor_*.db"
        exit 1
    fi

    cp "$db_file" "${DATABASE_PATH:-${ROOT_DIR}/data/superconductor.db}"
    echo "✅ 已恢复数据库：${db_file} -> ${DATABASE_PATH:-${ROOT_DIR}/data/superconductor.db}"

    if [[ -n "$json_file" ]]; then
        echo "ℹ️ JSON 数据保存在：$json_file，可用于 import_data"
    fi
}

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

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

mode=""
restore_file=""

while getopts ":blr:" opt; do
    case "$opt" in
        b) mode="backup" ;;
        l) mode="list" ;;
        r) mode="restore"; restore_file="$OPTARG" ;;
        *) usage; exit 1 ;;
    esac
done

if [[ -z "$mode" ]]; then
    usage
    exit 1
fi

case "$mode" in
    backup) perform_backup ;;
    list) list_remote_backups ;;
    restore) restore_backup "$restore_file" ;;
esac

#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then
  echo 'Run with sudo from your local terminal.' >&2
  exit 1
fi
destination=/home/shen/AI370-2/output/recovery
mkdir -p "$destination"
checkpoint="$destination/CP0-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$checkpoint"
chmod 700 "$checkpoint"
df -h / > "$checkpoint/disk-space.txt"
lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS > "$checkpoint/disks.txt"
dpkg-query -W > "$checkpoint/packages.txt"
uname -a > "$checkpoint/kernel.txt"
if command -v sfdisk >/dev/null; then
  sfdisk --dump /dev/nvme0n1 > "$checkpoint/partition-table.txt"
fi
echo 'Creating live file-level checkpoint. Keep applications idle.'
set +e
tar --acls --xattrs --numeric-owner --sparse --one-file-system \
  --exclude=./proc --exclude=./sys --exclude=./dev --exclude=./run \
  --exclude=./tmp --exclude=./mnt --exclude=./media --exclude=./lost+found \
  --exclude=./home/shen/AI370-2/resources \
  --exclude=./home/shen/AI370-2/output \
  --exclude=./swap.img --exclude=./swapfile \
  -C / -cpf "$checkpoint/root.tar" . 2> "$checkpoint/root-tar.stderr"
archive_status=$?
set -e
printf '%s\n' "$archive_status" > "$checkpoint/root-tar.exitcode"
if [[ $archive_status -ne 0 ]]; then
  echo "Archive returned $archive_status; checkpoint is NOT verified. See $checkpoint/root-tar.stderr" >&2
  exit "$archive_status"
fi
tar --numeric-owner -C /boot/efi -cpf "$checkpoint/efi.tar" .
tar -tf "$checkpoint/root.tar" > "$checkpoint/root-file-list.txt"
tar -tf "$checkpoint/efi.tar" > "$checkpoint/efi-file-list.txt"
(cd "$checkpoint" && sha256sum root.tar efi.tar > SHA256SUMS && sha256sum -c SHA256SUMS)
sync
printf '%s\n' 'ARCHIVES_READABLE; RESTORE_NOT_TESTED; LIVE_FILESYSTEM_NOT_ATOMIC' > "$checkpoint/STATUS"
echo "Checkpoint archives saved: $checkpoint"
echo 'Requires agent review and restore validation before phase PASS.'

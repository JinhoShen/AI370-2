#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo in the local terminal.' >&2; exit 1; }
checkpoint=${1:-$(find /home/shen/AI370-2/output/recovery -mindepth 1 -maxdepth 1 -type d -name 'CP0-*' -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)}
[[ -n $checkpoint && -d $checkpoint ]] || { echo 'No CP0 checkpoint found; pass its directory as argument.' >&2; exit 2; }
report=${2:-/home/shen/AI370-2/docs/$(basename "$checkpoint")-VERIFICATION.txt}
scratch=$(mktemp -d "$checkpoint/restore-check.XXXXXX")
trap 'result=$?; rm -rf -- "$scratch"; if [[ -f $report ]]; then chmod 644 "$report"; fi; if [[ $result -ne 0 ]]; then echo "Verification failed. See $report" >&2; fi' EXIT
{
  echo 'CP0 local archive verification'
  date -u --iso-8601=seconds
  echo "Checkpoint: $checkpoint"
  echo 'Root archive exit code:'
  cat "$checkpoint/root-tar.exitcode"
  [[ $(cat "$checkpoint/root-tar.exitcode") == 0 ]]
  echo 'Archive checksums:'
  (cd "$checkpoint" && sha256sum -c SHA256SUMS)
  echo 'Root archive stderr bytes:'
  wc -c < "$checkpoint/root-tar.stderr"
  echo 'Recorded status:'
  cat "$checkpoint/STATUS"
  echo 'Partition table present:'
  test -s "$checkpoint/partition-table.txt" && echo YES
  echo 'Restore selected files to isolated directory:'
  tar --acls --xattrs --numeric-owner -xpf "$checkpoint/root.tar" -C "$scratch" \
    ./usr/lib/os-release ./etc/passwd ./etc/group ./etc/fstab \
    ./var/lib/dpkg/status ./boot
  for relative in usr/lib/os-release etc/passwd etc/group etc/fstab var/lib/dpkg/status; do
    test -s "$scratch/$relative"
    echo "$relative: RESTORED"
  done
  test -s "$scratch/boot/vmlinuz-6.17.0-14-generic"
  test -s "$scratch/boot/initrd.img-6.17.0-14-generic"
  echo 'Baseline kernel and initramfs: RESTORED'
  mkdir "$scratch/efi"
  tar --numeric-owner -xpf "$checkpoint/efi.tar" -C "$scratch/efi"
  test -d "$scratch/efi/EFI"
  echo 'EFI archive: RESTORED'
  echo 'RESULT: SELECTED_FILE_RESTORE_PASS'
  echo 'LIMITS: live filesystem backup, same NVMe, full system boot restore NOT TESTED'
} > "$report" 2>&1
chmod 644 "$report"
cat "$report"

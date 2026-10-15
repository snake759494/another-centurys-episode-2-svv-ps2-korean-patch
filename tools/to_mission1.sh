#!/bin/bash
# 테스트용: 부팅 → 새 캠페인 → 첫 미션 진입
cd "$(dirname "$0")/.."
python -I tools/emu.py stop; python -I tools/emu.py launch "$1"; sleep 40
P="python -I tools/vpad.py press"
$P START 3 START 3 X 3 O 4 O 4
for i in 1 2 3 4 5 6 7 8 9 10; do $P O 4; done
$P START 5
for i in 1 2 3 4 5 6 7 8; do $P O 5; done
$P START 5
for i in 1 2 3 4 5 6 7 8; do $P O 6; done

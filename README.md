# 어나더 센추리즈 에피소드 2 스페셜 보컬 버전 (PS2, SLPS-25829) 비공식 한글패치

PS2 일본판 **アナザーセンチュリーズエピソード2 スペシャルボーカルバージョン (SLPS-25829)** 의 비공식 한글패치입니다. 이 저장소에는 제작 도구와 기술 문서만 있으며, 게임 원본·일본어 원문·번역 대본은 들어 있지 않습니다. 패치 파일은 [Releases](../../releases)에서 받으세요.

## 받는 파일
- `ACE2_SVV_KO_v1.3.xdelta` — 한글패치(원본 ISO에 적용)
- `SLPS-25829_EE84B8C5.pnach` — PCSX2용 16:9 와이드 패치(선택)

## 원본
| 항목 | 값 |
| --- | --- |
| 파일 | `Another Century's Episode 2 - Special Vocal Version (Japan).iso` |
| 크기 | 3,677,028,352 바이트 |
| MD5 | `73bcffb7f2e6da7e3a7e26cd29145dd7` |
| SHA-256 | `efd791e7c50af2ec476f4026c6bda57fcf6d64babf20c12174db642b54941741` |

## 적용 방법
```
xdelta3 -d -s "Another Century's Episode 2 - Special Vocal Version (Japan).iso" ACE2_SVV_KO_v1.3.xdelta "Another Century's Episode 2 - Special Vocal Version (Korean).iso"
```
(또는 xdeltaUI) → 결과 ISO SHA-256 `97f095bcb3dfe8ba3fc62d3ec8660ed8881065af045adfd856b6699b6a064281`

## 한글화 범위
- 텍스트 9,712문장: 미션 무전·컷신 대사, 브리핑·뉴스, 메뉴·도움말, 유닛·인물·무기 이름, 기체별 커맨드 리스트, 스태프 크레딧 + 미션 파일에 직접 박힌 대사 98문장
- 글꼴 4종: 12px 기본 글꼴(KS X 1001 한글 2,350자, 나눔스퀘어네오 Regular), 19px 메뉴·미션 글꼴(한글 1,053자, 나눔스퀘어네오 Bold). 수용량이 부족한 미션 HUD 16px·21px 글꼴은 19px 한글 글꼴로 교체
- 이미지: 부팅 주의문, 「플레이어 유닛/어나더 유닛」 제목, 진영·목표 카드 69장
- 동영상: 오프닝(MOVIE002)의 박힌 일본어 내레이션·대사를 지우고 한글 자막 합성
- 그대로 둔 것: 저작권 표기 이미지, 음성, MOVIE001(영문 크레딧)

## 16:9 와이드 화면 (PCSX2)
한글패치는 실행 파일을 바꾸지 않아 CRC(**EE84B8C5**)가 원본과 같습니다. PCSX2 v2.x에 내장된 와이드 패치가 그대로 적용되며, 내장 패치가 없는 버전은 `SLPS-25829_EE84B8C5.pnach` 를 `patches` 폴더에 넣어 쓰면 됩니다. 자세한 방법은 릴리즈 노트를 보세요.

## 문서
- [docs/TECHNICAL.md](docs/TECHNICAL.md) — 파일 구조·글꼴·문자열표·동영상 처리
- [docs/BUILD.md](docs/BUILD.md) — 빌드 방법
- [docs/FONT_CREDITS.md](docs/FONT_CREDITS.md) — 글꼴 출처
- [RIGHTS.md](RIGHTS.md) — 권리 및 외부 자료
- [CHANGELOG.md](CHANGELOG.md) — 변경 기록

## 알려진 한계
- PCSX2 v2.2.0에서 부팅, 메인 메뉴, 캠페인 설정, 브리핑, 첫 미션(대사·일시정지 메뉴), 오프닝 동영상, 16:9 와이드 패치 적용까지 확인했습니다. 전 구간 플레이 검수는 하지 않았으므로 글자 겹침·잘림이 있으면 알려 주세요.
- 커맨드 리스트 화면은 게임 안에서 아직 직접 보지 못했습니다.

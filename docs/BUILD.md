# 빌드 방법 (개발용)

준비물: 원본 ISO, Python 3.13 + numpy·Pillow·opencv-python·av·imageio-ffmpeg·fontTools·pycdlib, 글꼴(`docs/FONT_CREDITS.md`)

폴더 구성(게임 폴더 기준)
```
Another Century's Episode 2 - Special Vocal Version (Japan).iso
NanumSquareNeo-*.ttf, SeoulHangang*.ttf
work/tools/        ← 이 저장소의 tools/ 를 복사
work/translation/  ← 번역 데이터(저장소 미포함): src/, ko/, movie/, extra_inplace.json, card_titles.json
```

순서
```
python -I work/tools/extract.py      # 원문 추출 (work/tmp/uniq.json)
python -I work/tools/make_src.py     # 번역 배치 생성 (work/translation/src)
python -I work/tools/check.py        # 번역 검사 (태그·문자·줄 폭·줄 수)
python work/tools/movie.py work/tmp/mv/m2.pss work/tmp/mv/MOVIE002_ko.pss work/translation/movie/MOVIE002.json
python -I work/tools/build.py "Another Century's Episode 2 - Special Vocal Version (Korean).iso"
xdelta -e -f -s 원본.iso 한글.iso ACE2_SVV_KO_vX.Y.xdelta
```
- `m2.pss` 는 원본 ISO의 LBA 1568954부터 167,575,556바이트(MOVIE002.PSS)입니다.
- `tools/emu.py`·`tools/vpad.py`·`tools/to_mission1.sh` 는 시험용(포터블 PCSX2를 최소화 상태로 실행, PINE으로 가상 패드 입력)입니다.

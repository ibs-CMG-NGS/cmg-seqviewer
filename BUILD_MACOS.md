# CMG-SeqViewer - macOS 배포 가이드

## macOS 빌드 환경 준비

### 1. 필수 요구사항
- **macOS**: 10.13 (High Sierra) 이상
- **Python**: 3.9 이상
- **Xcode Command Line Tools**: 코드 서명용 (선택사항)

### 2. 의존성 설치

```bash
# Python 패키지 설치
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt

# PyInstaller 설치 (requirements-dev.txt에 포함)
pip3 install pyinstaller
```

---

## 빌드 방법

### 방법 1: 자동 빌드 (권장)

```bash
# 실행 권한 부여 (최초 1회)
chmod +x build-macos.sh

# 빌드 실행
./build-macos.sh
```

### 방법 2: 수동 빌드

```bash
# 이전 빌드 정리
rm -rf build dist

# PyInstaller 실행
pyinstaller --clean --noconfirm cmg-seqviewer-macos.spec
```

---

## 빌드 결과물

### .app 번들
```
dist/
└── CMG-SeqViewer.app/
    ├── Contents/
    │   ├── MacOS/
    │   │   └── CMG-SeqViewer (실행 파일)
    │   ├── Resources/
    │   │   ├── database/ (Pre-loaded datasets)
    │   │   ├── cmg-seqviewer.icns (아이콘)
    │   │   └── (기타 리소스)
    │   ├── Frameworks/ (Python 라이브러리)
    │   └── Info.plist (앱 메타데이터)
```

---

## 배포 방식

### Option 1: .app 파일 직접 배포

```bash
# .app 폴더를 압축
cd dist
zip -r CMG-SeqViewer_macOS.zip CMG-SeqViewer.app

# 사용자 배포
# 압축 해제 후 Applications 폴더로 드래그
```

**장점**:
- ✅ 간단하고 빠름
- ✅ 파일 크기 작음

**단점**:
- ❌ Gatekeeper 경고 (서명 안됨)
- ❌ 전문성 부족

---

### Option 2: DMG 이미지 생성 (권장)

```bash
# DMG 생성
hdiutil create -volname "CMG-SeqViewer" \
               -srcfolder dist/CMG-SeqViewer.app \
               -ov -format UDZO \
               CMG-SeqViewer.dmg

# 배경 이미지와 아이콘 위치 커스터마이징 (고급)
# create-dmg 도구 사용: https://github.com/create-dmg/create-dmg
```

**장점**:
- ✅ 전문적인 배포 방식
- ✅ Applications 폴더 바로가기 포함 가능
- ✅ 커스텀 배경/레이아웃

---

### Option 3: PKG 설치 패키지

```bash
# pkgbuild 사용
pkgbuild --root dist/CMG-SeqViewer.app \
         --identifier com.yourorg.cmgseqviewer \
         --version 1.0.0 \
         --install-location /Applications/CMG-SeqViewer.app \
         CMG-SeqViewer.pkg
```

**장점**:
- ✅ 정식 설치 프로그램
- ✅ 자동 업데이트 가능

**단점**:
- ❌ 더 복잡한 제작 과정

---

## 코드 서명 (Gatekeeper 통과)

### 필요한 것
- **Apple Developer Account**: $99/년
- **Developer ID Application Certificate**: Xcode에서 발급

### 서명 방법

```bash
# 1. 서명 ID 확인
security find-identity -v -p codesigning

# 2. .app 번들 서명
codesign --deep --force --verify --verbose \
         --sign "Developer ID Application: Your Name (TEAMID)" \
         --options runtime \
         dist/CMG-SeqViewer.app

# 3. 서명 확인
codesign --verify --verbose dist/CMG-SeqViewer.app
spctl -a -t exec -vv dist/CMG-SeqViewer.app

# 4. Notarization (macOS 10.15+)
# 앱을 Apple에 제출하여 공증 받기
xcrun notarytool submit CMG-SeqViewer.dmg \
                       --apple-id "your@email.com" \
                       --password "app-specific-password" \
                       --team-id TEAMID \
                       --wait

# 5. Notarization 결과 stapling
xcrun stapler staple CMG-SeqViewer.app
```

---

## 아이콘 생성

### PNG에서 ICNS 생성

```bash
# create_icon.py로 PNG 생성 (Windows/Linux)
python create_icon.py

# macOS에서 ICNS로 변환
mkdir cmg-seqviewer.iconset
sips -z 16 16     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_16x16.png
sips -z 32 32     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_16x16@2x.png
sips -z 32 32     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_32x32.png
sips -z 64 64     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_32x32@2x.png
sips -z 128 128   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_128x128.png
sips -z 256 256   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_128x128@2x.png
sips -z 256 256   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_256x256.png
sips -z 512 512   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_256x256@2x.png
sips -z 512 512   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_512x512.png
sips -z 1024 1024 cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_512x512@2x.png
iconutil -c icns cmg-seqviewer.iconset
rm -rf cmg-seqviewer.iconset
```

---

## 문제 해결

### 1. "CMG-SeqViewer.app is damaged" 경고

**원인**: Gatekeeper가 서명되지 않은 앱 차단

**해결**:
```bash
# 사용자 측 해결 (임시)
xattr -cr /Applications/CMG-SeqViewer.app

# 또는 시스템 환경설정 → 보안 → "확인 없이 열기"
```

**근본 해결**: 코드 서명 + Notarization

---

### 2. "Python 찾을 수 없음" 오류

**원인**: PyInstaller가 Python 런타임 포함 실패

**해결**:
```bash
# spec 파일의 hiddenimports에 누락된 모듈 추가
# cmg-seqviewer-macos.spec 편집
```

---

### 3. 파일 크기가 너무 큼

**원인**: 불필요한 라이브러리 포함

**해결**:
```bash
# spec 파일의 excludes에 추가
excludes=['tkinter', 'matplotlib.tests', 'numpy.tests', 'pandas.tests']

# UPX 압축 활성화 (이미 활성화됨)
upx=True
```

---

## Apple Silicon (M1/M2) 지원

### Universal Binary 생성

```bash
# Intel + Apple Silicon 지원
pyinstaller --clean --noconfirm \
            --target-arch universal2 \
            cmg-seqviewer-macos.spec
```

### 별도 빌드

```bash
# Intel (x86_64)
pyinstaller --target-arch x86_64 cmg-seqviewer-macos.spec

# Apple Silicon (arm64)
pyinstaller --target-arch arm64 cmg-seqviewer-macos.spec
```

---

## 배포 체크리스트

- [ ] Pre-loaded datasets를 database/ 폴더에 추가
- [ ] cmg-seqviewer.icns 아이콘 파일 생성
- [ ] bundle_identifier 고유값으로 변경
- [ ] 빌드 실행 (`./build-macos.sh`)
- [ ] .app 번들 테스트 (더블클릭 실행)
- [ ] DMG 생성 (선택)
- [ ] 코드 서명 (선택, 권장)
- [ ] 다른 Mac에서 테스트
- [ ] README 및 문서 포함

---

## 참고 자료

- **PyInstaller macOS**: https://pyinstaller.org/en/stable/usage.html#mac-os-x-specific-options
- **Code Signing**: https://developer.apple.com/support/code-signing/
- **Notarization**: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
- **create-dmg**: https://github.com/create-dmg/create-dmg
- **Info.plist**: https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/

---

## 크로스 플랫폼 빌드

**주의**: macOS 앱은 macOS에서만 빌드 가능!

- Windows → macOS 빌드: ❌ 불가능
- macOS → Windows 빌드: ❌ 불가능
- Linux → macOS 빌드: ❌ 불가능

각 플랫폼용 빌드는 해당 OS에서 수행해야 합니다.

**해결책**: CI/CD (GitHub Actions)

GitHub Actions를 사용한 자동 빌드 설정이 포함되어 있습니다:

```bash
# 릴리스 태그 푸시 시 자동 빌드
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions가 자동으로:
# 1. Windows에서 빌드
# 2. macOS에서 빌드
# 3. Release 생성 및 파일 첨부
```

**설정 파일**: `.github/workflows/build.yml`

**자동 빌드 포함**:
- ✅ Windows (EXE + ZIP)
- ✅ macOS (DMG)
- ✅ Release 자동 생성
- ✅ Pre-loaded datasets 포함

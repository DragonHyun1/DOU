# DoU Auto Test Toolkit - 빌드 가이드

이 가이드는 DoU Auto Test Toolkit을 독립 실행형 exe 파일로 빌드하는 방법을 설명합니다.

## 📋 사전 요구사항

### 필수 설치 항목
1. **Python 3.8 이상**
   - [Python 공식 웹사이트](https://www.python.org/downloads/)에서 다운로드

2. **프로젝트 의존성**
   ```bash
   pip install -r requirements.txt
   ```

3. **PyInstaller**
   ```bash
   pip install pyinstaller
   ```

## 🔨 빌드 방법

### Windows에서 빌드

#### 방법 1: 자동 빌드 스크립트 사용 (권장)
1. `build_exe.bat` 파일을 더블클릭하거나 명령 프롬프트에서 실행:
   ```cmd
   build_exe.bat
   ```

#### 방법 2: 수동 빌드
```cmd
# 이전 빌드 정리
rmdir /s /q build dist

# PyInstaller로 빌드
pyinstaller build_exe.spec --clean --noconfirm
```

### Linux/Mac에서 빌드

#### 방법 1: 자동 빌드 스크립트 사용 (권장)
```bash
# 실행 권한 부여
chmod +x build_exe.sh

# 빌드 실행
./build_exe.sh
```

#### 방법 2: 수동 빌드
```bash
# 이전 빌드 정리
rm -rf build dist

# PyInstaller로 빌드
python3 -m PyInstaller build_exe.spec --clean --noconfirm
```

## 📦 빌드 결과

빌드가 성공하면 다음 위치에 파일이 생성됩니다:
```
dist/DoU_Auto_Test_Toolkit/
├── DoU_Auto_Test_Toolkit.exe (Windows) 또는 DoU_Auto_Test_Toolkit (Linux/Mac)
├── README.txt
├── ui/ (UI 파일들)
├── test_scenarios/ (테스트 시나리오)
├── lib/ (라이브러리)
└── _internal/ (의존성 파일들)
```

## 🚀 배포 방법

### 배포 패키지 생성
1. `dist/DoU_Auto_Test_Toolkit` 폴더 전체를 압축 (ZIP 또는 7z)
2. 압축 파일명 예시: `DoU_Auto_Test_Toolkit_v1.0.zip`

### 사용자에게 전달할 내용
배포 시 반드시 포함해야 할 정보:

#### 필수 설치 항목
1. **NI-DAQmx 드라이버**
   - 다운로드: https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html
   - 버전: 최신 버전 권장
   - 설치 없이는 DAQ 기능이 작동하지 않습니다

2. **ADB (Android Debug Bridge)** - Android 기기 제어용
   - Android SDK Platform Tools에 포함
   - 다운로드: https://developer.android.com/studio/releases/platform-tools

#### 실행 방법
1. 압축 해제
2. `DoU_Auto_Test_Toolkit.exe` 실행
3. 장치 연결 (Power Monitor, DAQ, Android 기기)
4. 테스트 시작

## 🔧 문제 해결

### 빌드 실패 시

#### 1. "Module not found" 에러
```bash
# 모든 의존성 재설치
pip install -r requirements.txt --force-reinstall
```

#### 2. PyInstaller 에러
```bash
# PyInstaller 재설치
pip uninstall pyinstaller
pip install pyinstaller
```

#### 3. 메모리 부족 에러
```bash
# --log-level 옵션으로 상세 로그 확인
pyinstaller build_exe.spec --clean --noconfirm --log-level DEBUG
```

### 실행 파일이 시작되지 않을 때

1. **콘솔 모드로 디버그**
   - `build_exe.spec` 파일에서 `console=False`를 `console=True`로 변경
   - 다시 빌드하여 에러 메시지 확인

2. **의존성 확인**
   - 모든 필요한 DLL/so 파일이 포함되었는지 확인
   - Windows: Visual C++ Redistributable 설치 필요할 수 있음

3. **바이러스 백신 확인**
   - 일부 백신 프로그램이 PyInstaller로 만든 exe를 차단할 수 있음
   - 예외 목록에 추가

## 📝 빌드 커스터마이징

### 아이콘 추가
1. `.ico` 파일 준비 (Windows) 또는 `.icns` (Mac)
2. `build_exe.spec` 파일 수정:
   ```python
   icon='path/to/icon.ico'
   ```

### 단일 파일로 빌드 (선택사항)
모든 파일을 하나의 exe로 통합하려면 `build_exe.spec` 수정:
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,    # 추가
    a.zipfiles,    # 추가
    a.datas,       # 추가
    [],
    exclude_binaries=False,  # False로 변경
    name='DoU_Auto_Test_Toolkit',
    ...
    onefile=True,  # 추가
)

# COLLECT 섹션 제거
```

**주의**: 단일 파일 모드는 실행 속도가 느릴 수 있습니다.

### 파일 크기 줄이기
1. UPX 압축 사용 (기본 활성화)
2. 불필요한 모듈 제외:
   ```python
   excludes=['tkinter', 'matplotlib', 'numpy']  # 사용하지 않는 모듈 제외
   ```

## 🔒 보안 및 서명

### Windows 코드 서명 (선택사항)
신뢰성을 높이려면 디지털 서명 추가:
```cmd
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com DoU_Auto_Test_Toolkit.exe
```

## 📌 추가 정보

### 버전 정보 추가
`version.txt` 파일을 생성하고 spec 파일에 포함:
```python
a = Analysis(
    ['main.py'],
    ...
    version='version.txt',  # 버전 정보 파일
)
```

### 배포 체크리스트
- [ ] 빌드 성공 확인
- [ ] exe 파일 실행 테스트
- [ ] 모든 기능 동작 확인
- [ ] README.txt 포함
- [ ] 필수 드라이버 안내 문서 포함
- [ ] 버전 번호 확인
- [ ] 압축 파일 생성

## 📞 지원

문제가 발생하면:
1. `dist` 폴더의 로그 파일 확인
2. 콘솔 모드로 빌드하여 에러 메시지 확인
3. GitHub Issues에 문제 보고

---

**참고**: 이 빌드 설정은 PyQt6 및 NI-DAQmx를 사용하는 애플리케이션에 최적화되어 있습니다.

# DoU Auto Test Toolkit - 빠른 시작 가이드

## ⚡ 5분 안에 시작하기

### 1단계: 필수 소프트웨어 설치 (처음만)

```
✅ NI-DAQmx 드라이버
   → https://www.ni.com/downloads
   
✅ Monsoon SDK (HVPM 사용 시)
   → https://www.msoon.com/downloads
   
✅ Android SDK Platform Tools (ADB 사용 시)
   → https://developer.android.com/studio/platform-tools
```

### 2단계: 프로그램 실행

```
📁 dist/DoU_Auto_Test_Toolkit/ 폴더 열기
🖱️ DoU_Auto_Test_Toolkit.exe 더블클릭
```

### 3단계: 장비 연결 (30초)

#### HVPM 연결
```
1. USB 케이블로 HVPM 연결
2. "Port" 버튼 클릭
3. ✅ "Connected" 확인
```

#### ADB 연결
```
1. Android 기기 USB 디버깅 켜기
2. USB 연결
3. "ADB Refresh" 버튼
4. 기기 ID 확인
```

#### DAQ 연결 (선택)
```
1. DAQ 장비 연결
2. 콤보박스에서 장비 선택
3. "Connect" 버튼 → 녹색 확인
```

### 4단계: 기본 사용

#### 전압 측정
```
"Read V/I" 버튼 → 현재 전압/전류 확인
```

#### 전압 설정
```
1. 입력창에 전압 입력 (예: 4.0)
2. "Set Voltage" 클릭
3. 로그에서 확인
```

#### 자동 테스트 실행
```
1. "Start Test" 버튼
2. "Yes" 클릭
3. 진행 상황 확인
4. 완료 대기 (1-2분)
```

---

## 🔍 체크리스트

### 테스트 시작 전 확인사항

- [ ] HVPM 상태: **Connected ✅**
- [ ] ADB 기기: **선택됨**
- [ ] 로그창: **정상 메시지 표시**
- [ ] 테스트 앱: **기기에 설치됨**

---

## ❗ 문제 발생 시

### HVPM 안 잡힐 때
```
1. Monsoon SDK 설치됨? → 설치
2. USB 재연결
3. "Port" 버튼 다시 클릭
```

### ADB 안 잡힐 때
```
1. USB 디버깅 켜짐? → 켜기
2. USB 케이블 재연결
3. "ADB Refresh" 클릭
```

### 테스트 안 시작될 때
```
1. HVPM Connected? → 확인
2. ADB 선택됨? → 확인
3. 로그 확인 → 오류 메시지 읽기
```

---

## 📖 더 자세한 정보

➡️ [전체 사용자 매뉴얼](USER_MANUAL.md)

---

**이제 시작할 준비가 되었습니다! 🚀**

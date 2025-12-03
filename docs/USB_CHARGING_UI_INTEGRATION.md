# USB 충전 비활성화 UI 통합

**날짜:** 2025-11-04  
**변경:** Phone 시나리오 자동 실행 → UI Refresh 버튼으로 변경

---

## 🔄 변경 이유

사용자 요청에 따라 USB 충전 비활성화를 **수동 제어**로 변경:
- ❌ Before: Phone App 시나리오 자동 실행
- ✅ After: Multi-Channel Monitor의 Single Read (Refresh) 버튼 클릭 시 실행

---

## 🎯 변경 내용

### 1. Phone App Scenario 수정

**제거된 항목:**
```python
# Step 제거
TestStep("disable_usb_charging", 2.0, "disable_usb_charging")

# 메서드 제거
def _step_disable_usb_charging(self) -> bool:
    # ... (38줄 제거)
```

**결과:** Phone App 시나리오는 이제 USB 충전 제어를 하지 않음

### 2. Multi-Channel Monitor UI 수정

**파일:** `ui/multi_channel_monitor.py`

**추가된 코드 (single_read 메서드):**
```python
def single_read(self):
    """Perform single read of all enabled channels"""
    # Disable USB charging first (to prevent voltage interference with HVPM)
    if hasattr(self.parent(), 'adb_service'):
        try:
            adb_service = self.parent().adb_service
            if adb_service and adb_service.is_connected():
                print("🔌 Disabling USB charging before measurement...")
                adb_service.disable_usb_charging()
                self.status_label.setText("USB charging disabled")
        except Exception as e:
            print(f"Warning: Could not disable USB charging: {e}")
    
    # ... (기존 채널 읽기 로직)
```

---

## 💡 사용 방법

### UI에서 사용

1. **Multi-Channel Monitor 열기**
   - Main Window → Multi-Channel Monitor 버튼 클릭

2. **DAQ 연결**
   - Device 선택
   - Connect 클릭

3. **ADB 연결** (중요!)
   - USB로 디바이스 연결
   - ADB 활성화 상태 확인

4. **채널 활성화**
   - 원하는 채널 Enable 체크

5. **Single Read (Refresh) 버튼 클릭**
   ```
   클릭 시 자동으로:
   1. USB 충전 비활성화 🔌
   2. 채널 측정
   3. 결과 표시
   ```

### 콘솔 로그

```
🔌 Disabling USB charging before measurement...
USB charging disabled
Reading 6 channels...
✅ Current mode read completed - 6 channels
```

---

## ✅ 장점

### 1. 사용자 제어
- 사용자가 원하는 시점에 USB 충전 비활성화
- 자동 실행으로 인한 혼란 방지

### 2. 유연성
- Phone App Test 외 다른 작업에도 사용 가능
- 수동 측정 시에도 동작

### 3. 명확성
- Refresh 버튼 = USB 충전 OFF + 측정
- 버튼 하나로 모든 작업 수행

### 4. 안전성
- ADB 미연결 시 자동으로 스킵
- 에러 발생 시에도 측정 계속 진행

---

## ⚠️ 주의사항

### 1. ADB 연결 필수
```
USB 충전 비활성화를 위해서는 ADB 연결 필요
연결 안 되어 있으면 자동으로 스킵됨
```

### 2. 매번 Refresh 필요
```
디바이스 재부팅 또는 USB 재연결 시
다시 Refresh 버튼 클릭 필요
```

### 3. HVPM 전압 설정 순서
```
권장 순서:
1. HVPM 4V 설정
2. Refresh 버튼 클릭 (USB 충전 OFF)
3. 측정 시작
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 수동 측정
```
1. Multi-Channel Monitor 열기
2. DAQ 연결
3. ADB 연결 (USB)
4. 채널 활성화
5. HVPM 4V 설정
6. Refresh 버튼 클릭
   → USB 충전 OFF ✅
   → Battery Rail = 4V 유지
7. 측정 확인
```

### 시나리오 2: Phone App Test
```
1. Phone App Test 시작
2. (자동으로 진행...)
3. 테스트 중 수동으로 확인 필요 시:
   - Multi-Channel Monitor 열기
   - Refresh 버튼 클릭
   - 실시간 값 확인
```

---

## 📝 변경사항 요약

| 항목 | Before | After |
|------|--------|-------|
| **위치** | Phone App Scenario | Multi-Channel Monitor UI |
| **실행** | 자동 (Step 2) | 수동 (Refresh 버튼) |
| **적용 범위** | Phone App Test만 | 모든 측정 |
| **사용자 제어** | 없음 | 있음 ✅ |

---

## 🎯 결론

**USB 충전 비활성화가 UI Refresh 버튼으로 이동!**

- ✅ 사용자가 원하는 시점에 실행
- ✅ 더 유연하고 직관적
- ✅ 모든 테스트에서 사용 가능
- ✅ ADB 연결만 있으면 자동 작동

**Refresh 버튼 = USB 충전 OFF + 채널 측정** 🔄

# 🚨 스레드 문제 완전 분석

## 현재 스레드 구조

### 1. **Main Thread** (Qt 메인 스레드)
```
역할: UI 업데이트, 이벤트 루프
상태: ✅ 정상
```

### 2. **test_thread** (Python threading.Thread) ⚠️ 문제!
```python
# services/test_scenario_engine.py:228
self.test_thread = threading.Thread(
    target=self._execute_test_unified,
    args=(scenario,),
    daemon=True
)
self.test_thread.start()
```
**실행 내용:**
- 테스트 시나리오 실행
- **385개의 `log_callback()` 직접 호출!** ⚠️
- Phone app 테스트, DAQ 수집 등

### 3. **monitoring_thread** (Python threading.Thread) ⚠️ 문제!
```python
# services/test_scenario_engine.py:824
self.monitoring_thread = threading.Thread(
    target=self._daq_monitoring_loop
)
self.monitoring_thread.daemon = True
self.monitoring_thread.start()
```
**실행 내용:**
- DAQ 데이터 수집
- `log_callback()` 직접 호출 ⚠️

### 4. **monitoring_thread_isolated** (Python threading.Thread) ⚠️ 문제!
```python
# services/test_scenario_engine.py:921
monitoring_thread = threading.Thread(
    target=self._daq_monitoring_loop_isolated,
    name="DAQ-Monitor-Thread"
)
monitoring_thread.daemon = True
monitoring_thread.start()
```

---

## 💥 문제의 핵심

### 잘못된 흐름:
```
[test_thread] Worker Thread
    ↓
self.log_callback("메시지", "info")  ⚠️ 직접 호출!
    ↓
main.py의 _log() 함수 실행  ⚠️ 워커 스레드에서!
    ↓
self.ui.log_LW.addItem(item)  ⚠️ UI 직접 업데이트!
self.ui.log_LW.scrollToBottom()  ⚠️ QBasicTimer 사용!
    ↓
💥 QBasicTimer::start 에러!
💥 프로그램 크래시!
💥 System log 깜박임!
```

### 코드 증거:

**1. test_scenario_engine.py 초기화:**
```python
def __init__(self, ..., log_callback: Callable = None):
    self.log_callback = log_callback or self._default_log  # 함수 포인터 저장
```

**2. main.py에서 전달:**
```python
self.test_scenario_engine = TestScenarioEngine(
    ...,
    log_callback=self._log  # ⚠️ UI 업데이트 함수를 직접 전달!
)
```

**3. 워커 스레드에서 385번 호출:**
```python
# test_thread 안에서:
self.log_callback("Starting test...", "info")  # ⚠️ 워커 스레드에서 UI 업데이트!
```

**4. _log()가 UI 직접 업데이트:**
```python
def _log(self, msg: str, level: str = "info"):
    # 이 함수가 워커 스레드에서 실행됨!
    self.ui.log_LW.addItem(item)  # ⚠️ UI 직접 조작
    self.ui.log_LW.scrollToBottom()  # ⚠️ QBasicTimer 사용!
```

---

## ❌ 왜 신호가 작동 안 했나?

### 우리가 한 것:
```python
# main.py
self.test_scenario_engine.log_message.connect(
    self._log, 
    Qt.ConnectionType.QueuedConnection  # ✅ 설정은 올바름
)
```

### 하지만 실제로는:
```python
# test_scenario_engine.py - 워커 스레드 안에서
self.log_callback("메시지")  # ⚠️ 신호 발생 안 함! 직접 호출!

# 신호는 이렇게 발생해야 함:
self.log_message.emit("메시지", "info")  # ✅ 이래야 QueuedConnection 작동
```

**결과:**
- `log_callback()` 직접 호출 = 신호 무시
- QueuedConnection 설정은 무의미
- 워커 스레드에서 UI 직접 업데이트
- QBasicTimer 에러!

---

## ✅ 올바른 해결 방법

### 현재 (잘못됨):
```python
# 워커 스레드 안에서
self.log_callback("메시지", "info")  # ❌ UI 직접 접근!
```

### 수정 후 (올바름):
```python
# 워커 스레드 안에서
self._emit_signal_safe(self.log_message, "메시지", "info")  # ✅ 신호 발생!
```

### 또는:
```python
def _default_log(self, message: str, level: str = "info"):
    """Default log handler - emit signal instead of direct call"""
    # 신호 발생 (thread-safe)
    self._emit_signal_safe(self.log_message, message, level)
    # print도 남김
    print(f"[{level.upper()}] {message}")
```

---

## 📊 요약

| 항목 | 현재 상태 | 문제 |
|------|-----------|------|
| **스레드 수** | 4개 (Main + 3 Worker) | ✅ 정상 |
| **log_callback 호출** | 385회 | ⚠️ 모두 워커 스레드에서 |
| **UI 직접 접근** | 385회 | ❌ QBasicTimer 에러 발생 |
| **신호 사용** | 정의만 됨 | ❌ 실제로 사용 안 함 |
| **QueuedConnection** | 설정됨 | ❌ 신호 안 쓰니 무의미 |

---

## 🎯 다음 단계

**두 가지 선택:**

### Option 1: _default_log 수정 (간단)
```python
def _default_log(self, message: str, level: str = "info"):
    self._emit_signal_safe(self.log_message, message, level)
```

### Option 2: 모든 log_callback을 신호로 변경 (완벽하지만 많은 수정)
```python
# 385개 모두 변경
self.log_callback("msg") → self._emit_signal_safe(self.log_message, "msg", "info")
```

**추천: Option 1** (간단하고 효과적)

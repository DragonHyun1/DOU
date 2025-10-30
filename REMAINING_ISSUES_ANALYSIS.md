# 남은 문제 분석 보고서

## ✅ 완료된 사항
- **testResults_TE txt 파일 저장 기능 제거** ✅
  - `_save_test_results()` 함수를 빈 함수로 변경
  - 더 이상 `test_result_{timestamp}.txt` 파일 생성 안 됨
  - Excel 결과만 저장됨

---

## ⚠️ 남은 2가지 문제

### 1️⃣ Excel "제거된 레코드: /xl/worksheets/sheet2.xml 부분의 수식"

**문제 위치:** `services/test_scenario_engine.py:2156-2237`

**원인:**
```python
# openpyxl fallback에서 Summary sheet 생성
with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Test_Results', index=False)
    summary_df.to_excel(writer, sheet_name='Test_Summary', index=False)  # ⚠️ 문제!
```

**해결 방법:**
1. **옵션 A: Summary sheet 제거** (간단)
   ```python
   # 2156-2237 라인 전체 제거
   df.to_excel(filename, sheet_name='Test_Results', index=False, engine='openpyxl')
   ```

2. **옵션 B: xlsxwriter만 사용** (권장)
   ```python
   # openpyxl fallback 완전 제거
   # xlsxwriter가 없으면 에러 발생하도록
   if not XLSXWRITER_AVAILABLE:
       raise ImportError("xlsxwriter required for Excel export")
   ```

**추천:** 옵션 A - Summary sheet는 불필요하고, Test_Results sheet만으로 충분

---

### 2️⃣ Test Progress Bar가 0% → 100%로만 동작

**문제 위치:** `services/test_scenario_engine.py:303-357` (_execute_test_unified)

**원인:**
```python
def _execute_test_unified(self, scenario: TestConfig):
    # Progress 업데이트가 없음!
    for i, step in enumerate(scenario.steps):
        self.current_step = i + 1
        # ⚠️ progress_updated 신호를 발생시키지 않음!
        success = self._execute_step(step)
```

**해결 방법:**
```python
def _execute_test_unified(self, scenario: TestConfig):
    self.status = TestStatus.RUNNING
    
    for i, step in enumerate(scenario.steps):
        if self.stop_requested:
            break
        
        self.current_step = i + 1
        
        # ✅ Progress 업데이트 추가
        progress = int((i / self.total_steps) * 100)
        self._emit_signal_safe(self.progress_updated, progress, f"Step {i+1}/{self.total_steps}: {step.name}")
        
        self.log_callback(f"Step {self.current_step}/{self.total_steps}: {step.name}", "info")
        
        # Execute step
        if step.action == "screen_on_off_with_daq_monitoring":
            success = self._unified_screen_test_with_daq()
        else:
            success = self._execute_step(step)
        
        # ... rest of code
```

**수정할 위치:**
- 라인 286: `self.current_step = i + 1` 다음에 progress 업데이트 추가
- 라인 357: 테스트 완료 시 100% 업데이트

---

## 📝 수정 가이드

### Excel 수식 오류 수정:
```bash
# services/test_scenario_engine.py

# 현재 (2152-2237)
# Create DataFrame
df = pd.DataFrame(formatted_data)

# Export to Excel
with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Test_Results', index=False)
    # ... 80 lines of summary sheet code ...

# 수정 후
# Create DataFrame
df = pd.DataFrame(formatted_data)

# Export to Excel - simple, no summary sheet
df.to_excel(filename, sheet_name='Test_Results', index=False, engine='openpyxl')
# Done! No summary sheet = no formula errors
```

### Progress Bar 수정:
```bash
# services/test_scenario_engine.py:286

# 현재
self.current_step = i + 1
self._update_progress_safe(f"Executing: {step.name}")  # ← 작동 안 함

# 수정 후
self.current_step = i + 1
progress = int((i / self.total_steps) * 100)
self._emit_signal_safe(self.progress_updated, progress, 
                       f"Step {i+1}/{self.total_steps}: {step.name}")
```

---

## 🎯 우선순위

1. **Excel 수식 오류** - 높음
   - 사용자가 매번 복구 클릭해야 함
   - 간단히 summary sheet 제거로 해결

2. **Progress Bar** - 중간
   - 기능적 문제는 없지만 UX 개선 필요
   - 2-3줄 코드 추가로 해결

---

## 💡 참고사항

### _update_progress_safe vs _emit_signal_safe

**현재 문제:**
```python
def _update_progress_safe(self, step_name: str):
    """Update progress display - thread-safe version"""
    if self.total_steps > 0:
        progress = int((self.current_step / self.total_steps) * 100)
    else:
        progress = 0
    
    self._emit_signal_safe(self.progress_updated, progress, step_name)
```

이 함수는 호출되지만, `current_step`이 업데이트되기 전에 호출되거나,
daemon thread 체크 때문에 무시될 수 있습니다.

**해결책:**
직접 `_emit_signal_safe(self.progress_updated, ...)` 호출이 더 확실합니다.

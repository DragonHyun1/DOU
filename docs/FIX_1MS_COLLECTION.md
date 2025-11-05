# DAQ 수집 간격 1ms 변경 완료 현황

## ✅ 완료된 변경사항

### 1. 기본 수집 간격 변경
- `services/test_scenario_engine.py` line 64
  - `monitoring_interval: float = 0.001  # 1ms interval`
  
- `services/test_scenario_engine.py` line 431
  - `data_interval = 0.001  # 1ms intervals (1000 samples per second)`

- `services/daq_collection_thread.py` line 30
  - `self.collection_interval = 0.001  # 1ms (1000 samples per second)`

- `services/daq_collection_thread.py` line 37
  - `def configure(self, enabled_channels: List[str], interval: float = 0.001):`

### 2. Sleep 간격 변경
- 데이터 수집 루프: `time.sleep(0.001)  # 1ms interval`
- 대기 상태: `time.sleep(1.0)  # Keep 1s for waiting state` (유지)

## ⚠️ 수동 수정 필요

**문제:** Phone App 시나리오에서 "정수 초마다만 1개 수집" 로직이 남아있음

**위치:** `services/test_scenario_engine.py` 
- Line ~1486: `target_second = int(data_elapsed_time)`
- Line ~1544: `target_second = int(fallback_elapsed)`

**현재 로직:**
```python
# Collect data only at integer second intervals (0, 1, 2, ..., 9)
target_second = int(data_elapsed_time)
current_data_count = len(self.daq_data)

# Only collect if we haven't collected for this second yet
if target_second == current_data_count and target_second < 10:
    # 데이터 수집...
```

**수정 필요:**
이 if문 제거하고 매 루프마다 수집하도록 변경

## 📝 수동 수정 방법

1. `services/test_scenario_engine.py` 파일 열기

2. Line ~1485-1517 찾기:
   - `# Collect data only at integer second intervals` 부분

3. 다음과 같이 수정:
```python
# 변경 전:
if target_second == current_data_count and target_second < 10:
    # 데이터 수집...

# 변경 후: (if문 제거, 들여쓰기 조정)
# 매 루프마다 데이터 수집
if not channel_data:
    continue
    
data_point = {
    'timestamp': datetime.now(),
    'time_elapsed': round(data_elapsed_time, 3),  # ms precision
    'screen_test_time': round(screen_test_elapsed, 3),
    **channel_data
}

if hasattr(self, 'daq_data'):
    self.daq_data.append(data_point)
    
    # Log every 1000 samples (1 second)
    if len(self.daq_data) % 1000 == 0:
        print(f"DAQ: {len(self.daq_data)} samples collected")
```

4. 같은 방식으로 Line ~1543-1575 (fallback 부분)도 수정

## 예상 결과

- **현재:** 10초 동안 10개 샘플 (1초에 1개)
- **수정 후:** 10초 동안 ~10,000개 샘플 (1ms에 1개)

## 주의사항

⚠️ **엑셀 파일 크기 주의!**
- 10,000 rows × 채널 수 = 매우 큰 파일
- 실제 테스트 전에 짧은 시간(1-2초)으로 먼저 테스트 권장

## 대안

시간당 샘플 수를 줄이려면:
- 10ms (0.01초): 1,000 samples/sec → 10초에 10,000개
- 100ms (0.1초): 100 samples/sec → 10초에 1,000개
- 현재 1ms: 1,000 samples/sec

필요하면 interval을 0.01이나 0.1로 조정하세요.

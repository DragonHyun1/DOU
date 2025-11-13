# 안정화 시간 테스트 (Stabilization Time Test)

## 🔍 발견된 문제

**사용자 발견:**
- WiFi 같은 init 설정 후 **안정화 시간이 부족**하면 측정값이 망가짐
- Init을 스킵하고 **충분한 안정화 시간**을 두면 값이 정상

## 📊 안정화 시간 변경

### 이전 설정:
```python
TestStep("stabilize", 10.0, "wait_stabilization")  # 10초
```

### 새로운 설정:
```python
TestStep("stabilize", 60.0, "wait_stabilization")  # 60초 (1분)
```

## 🎯 테스트 목적

**안정화 시간을 1분으로 늘렸을 때:**
- ✅ WiFi/Bluetooth 연결 후 전류가 안정화되는가?
- ✅ 측정값이 망가지지 않는가?
- ✅ Manual tool과 값이 일치하는가?

## 📐 Phone App 시나리오 타임라인

### 새로운 타임라인 (안정화 60초):

```
00:00 - Init HVPM (2s)
00:02 - Setup ADB (3s)
00:05 - Flight Mode ON (2s)
00:07 - WiFi 2G Connect (8s)
00:15 - Bluetooth ON (3s)
00:18 - Screen Timeout (3s)
00:21 - Unlock & Clear Apps (10s)
00:31 - 🕐 Stabilization START (60s) ← 1분 대기!
01:31 - 🕐 Stabilization END
01:33 - DAQ Start (2s)
01:35 - Phone App Test (10s) ← 측정 시작
01:45 - DAQ Stop (2s)
01:47 - Excel Export (2s)
01:49 - Test Complete

총 소요 시간: ~110초 (약 2분)
```

### 이전 타임라인 (안정화 10초):

```
00:00 - Init steps (~31s)
00:31 - Stabilization (10s) ← 너무 짧음!
00:41 - DAQ Start
00:43 - Phone App Test (10s) ← 측정값 망가짐 가능
```

## 📊 안정화가 필요한 이유

### WiFi 연결 후:
```
Time: 0s ────────────────> 60s
WiFi: [연결] → [인증] → [DHCP] → [백그라운드 동기화] → [안정화]
전류: 높음 ──┐        ┌─────────────> 낮고 안정적
            └────────┘ (점진적 감소)
            
측정 타이밍:
❌ 10초 후: 아직 안정화 안 됨 (전류 변동 큼)
✅ 60초 후: 완전히 안정화 (전류 일정)
```

### Bluetooth 연결 후:
```
Time: 0s ────────────────> 60s
BT:   [ON] → [스캔] → [페어링 체크] → [안정화]
전류: 높음 ───┐      ┌──────────────> 낮고 안정적
             └──────┘ (점진적 감소)
```

## 🧪 테스트 시나리오

### 비교 테스트:

1. **안정화 10초 (이전):**
   ```bash
   python main.py
   → Phone App 시나리오 (안정화 10초)
   → 결과: 값이 망가질 가능성
   ```

2. **안정화 60초 (현재):**
   ```bash
   python main.py
   → Phone App 시나리오 (안정화 60초)
   → 결과: 값이 안정적일 것으로 예상
   ```

## 📈 예상 결과

### 안정화 10초 (불충분):
```
WiFi/BT 연결 후 10초:
- 전류가 아직 변동 중 (불안정)
- 측정값에 노이즈 많음
- Manual tool과 차이 발생

예: ai3 평균 전류
  10초 안정화: 65 mA (불안정, 높음)
  60초 안정화: 50 mA (안정, Manual과 일치) ✅
```

### 안정화 60초 (충분):
```
WiFi/BT 연결 후 60초:
- 전류가 완전히 안정화
- 측정값이 일정하고 안정적
- Manual tool과 일치

예: ai3 평균 전류
  60초 안정화: 50 mA ✅ (Manual: 50 mA)
```

## 🎯 검증 포인트

### 1. 전류 안정화 확인:
```
00:31 - Stabilization START
  → ai3 current: 80 mA (높음, WiFi 동기화 중)
  
00:45 - 15초 경과
  → ai3 current: 65 mA (감소 중)
  
01:00 - 30초 경과
  → ai3 current: 55 mA (안정화 중)
  
01:31 - 60초 경과 (END)
  → ai3 current: 50 mA (안정화 완료) ✅
```

### 2. Manual tool과 비교:
```
DoU (60초 안정화): ai3 = 50 mA
Manual tool:       ai3 = 50 mA
차이: 0 mA ✅ 완전 일치!
```

## 📝 결론

**안정화 시간 부족이 문제였음:**
- 10초: WiFi/Bluetooth가 완전히 안정화되지 않음
- 60초: 충분한 시간으로 완전 안정화

**최종 설정:**
- ✅ Sample Rate: 20kHz
- ✅ Compression: 20:1
- ✅ Voltage Range: ±5V
- ✅ Battery Compensation: ai1~ai5 ÷4
- ✅ **Stabilization: 60초** ← 핵심!

## 🚀 다음 단계

```bash
python main.py
→ Auto Test > Phone App 시나리오 실행
→ 안정화 60초 대기 (1분)
→ 측정 후 Manual tool과 비교!
```

안정화 시간이 충분하면 Manual tool과 완전히 일치할 것으로 예상됩니다! 🎯

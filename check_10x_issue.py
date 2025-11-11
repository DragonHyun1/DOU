"""
10배 차이 원인 분석
"""

# 현재 계산 방식
voltage = 0.001  # 1mV = 0.001V (shunt drop)
shunt_r = 0.01   # 10mΩ = 0.01Ω

# 우리 툴 계산
current_A = voltage / shunt_r  # 0.001 / 0.01 = 0.1A
current_mA = current_A * 1000  # 0.1 * 1000 = 100mA

print("=== 10배 차이 원인 분석 ===")
print()
print(f"입력:")
print(f"  - Shunt drop: {voltage*1000:.3f}mV")
print(f"  - Shunt resistor: {shunt_r}Ω = {shunt_r*1000}mΩ")
print()
print(f"현재 툴 계산:")
print(f"  - I = V / R = {voltage}V / {shunt_r}Ω = {current_A}A")
print(f"  - I = {current_A}A * 1000 = {current_mA}mA")
print()

# 가능한 원인들
print("가능한 원인:")
print()

# 원인 1: Shunt 값이 10배 작게 설정
print("1. Shunt 값이 10배 작을 경우 (0.01Ω 대신 0.001Ω):")
wrong_shunt = 0.001
current_wrong = (voltage / wrong_shunt) * 1000
print(f"   I = {voltage}V / {wrong_shunt}Ω * 1000 = {current_wrong}mA")
print(f"   → {current_wrong / current_mA:.1f}배 차이!")
print()

# 원인 2: 단위 변환 중복
print("2. mV를 V로 변환 안 했을 경우:")
voltage_mv = 1.0  # mV 단위 그대로
current_wrong2 = (voltage_mv / shunt_r) * 1000
print(f"   I = {voltage_mv}mV / {shunt_r}Ω * 1000 = {current_wrong2}mA")
print(f"   → {current_wrong2 / current_mA:.1f}배 차이!")
print()

# 원인 3: 1000 대신 10000 곱함
print("3. 1000 대신 10000을 곱했을 경우:")
current_wrong3 = current_A * 10000
print(f"   I = {current_A}A * 10000 = {current_wrong3}mA")
print(f"   → {current_wrong3 / current_mA:.1f}배 차이!")
print()

print("=== 결론 ===")
print()
print("10배 차이가 나는 원인은 아마도:")
print("  ❌ Shunt resistor 값이 10배 작게 설정되어 있음")
print("  ❌ 또는 단위 변환에서 1000이 아닌 다른 값을 곱함")

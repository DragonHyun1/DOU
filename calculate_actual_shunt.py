#!/usr/bin/env python3
"""
실제 Shunt 저항 값 역산
DoU 측정 전압과 Manual 전류로부터 실제 shunt 값 계산
"""

# DoU 측정값
dou_data = {
    'VBAT': {'voltage_mv': 0.013, 'current_ma': 1.256, 'shunt_dou': 0.01},
    'VDD_1P8_AP': {'voltage_mv': 0.092, 'current_ma': 0.916, 'shunt_dou': 0.1},
    'VDD_MLDO_2P0': {'voltage_mv': 0.003, 'current_ma': 0.517, 'shunt_dou': 0.005},
    'VDD_WIFI_1P0': {'voltage_mv': 0.049, 'current_ma': 9.723, 'shunt_dou': 0.005},
    'VDD_1P2_AP_WIFI': {'voltage_mv': 0.045, 'current_ma': 0.449, 'shunt_dou': 0.1},
    'VDD_1P35_WIFIPMU': {'voltage_mv': 0.046, 'current_ma': 4.605, 'shunt_dou': 0.01},
}

# Manual 측정 전류
manual_current = {
    'VBAT': 0.409,
    'VDD_1P8_AP': 0.365,
    'VDD_MLDO_2P0': -0.173,
    'VDD_WIFI_1P0': 1.709,
    'VDD_1P2_AP_WIFI': 0.149,
    'VDD_1P35_WIFIPMU': 0.759,
}

print("=" * 80)
print("실제 Shunt 저항 값 역산")
print("=" * 80)
print()
print("공식: Shunt(Ω) = Voltage(V) / Current(A)")
print()

for channel, data in dou_data.items():
    voltage_v = data['voltage_mv'] / 1000  # mV to V
    current_a_manual = manual_current[channel] / 1000  # mA to A
    current_a_dou = data['current_ma'] / 1000  # mA to A
    shunt_dou = data['shunt_dou']
    
    # 역산: 실제 shunt = voltage / manual_current
    if current_a_manual != 0:
        shunt_actual = voltage_v / current_a_manual
    else:
        shunt_actual = 0
    
    # 비율
    ratio = data['current_ma'] / manual_current[channel] if manual_current[channel] != 0 else 0
    
    print(f"{channel:20s}")
    print(f"  DoU Voltage:     {data['voltage_mv']:.3f} mV")
    print(f"  DoU Current:     {data['current_ma']:.3f} mA")
    print(f"  Manual Current:  {manual_current[channel]:.3f} mA")
    print(f"  DoU / Manual:    {ratio:.2f}배")
    print(f"  DoU Shunt 설정:  {shunt_dou:.3f}Ω")
    print(f"  실제 Shunt:      {shunt_actual:.3f}Ω  ← 이 값을 사용해야 함!")
    print(f"  배율:            {shunt_actual / shunt_dou:.2f}배")
    print()

print("=" * 80)
print("결론: DoU UI에서 다음 Shunt 값으로 설정하세요:")
print("=" * 80)
for channel, data in dou_data.items():
    voltage_v = data['voltage_mv'] / 1000
    current_a_manual = manual_current[channel] / 1000
    if current_a_manual != 0:
        shunt_actual = voltage_v / current_a_manual
        print(f"  {channel:20s} → {shunt_actual:.4f}Ω  (현재: {data['shunt_dou']}Ω)")

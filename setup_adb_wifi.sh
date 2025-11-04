#!/bin/bash

# ADB over Wi-Fi 설정 스크립트

echo "============================================================"
echo "ADB over Wi-Fi 설정"
echo "============================================================"
echo ""

# 1단계: USB 연결 상태에서 Wi-Fi ADB 활성화
echo "[1단계] USB 연결 상태에서 Wi-Fi ADB 활성화 중..."
adb tcpip 5555

if [ $? -ne 0 ]; then
    echo "❌ 오류: ADB 장치를 찾을 수 없습니다."
    echo "   USB 케이블이 연결되어 있는지 확인하세요."
    exit 1
fi

echo "✓ Wi-Fi ADB 모드 활성화 완료"
echo ""

# 2단계: 폰의 IP 주소 확인
echo "[2단계] 폰의 IP 주소 확인 중..."
PHONE_IP=$(adb shell ip addr show wlan0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)

if [ -z "$PHONE_IP" ]; then
    echo "⚠️  자동으로 IP를 찾지 못했습니다."
    echo "   수동으로 IP를 입력하세요:"
    echo "   (설정 > Wi-Fi > 현재 연결된 네트워크 > IP 주소)"
    echo ""
    read -p "   폰의 IP 주소: " PHONE_IP
fi

echo "✓ 폰 IP 주소: $PHONE_IP"
echo ""

# 3단계: USB 케이블 제거 안내
echo "[3단계] USB 케이블 제거"
echo "============================================================"
echo "⚠️  지금 USB 케이블을 제거하세요!"
echo "============================================================"
echo ""
read -p "USB 케이블을 제거했으면 Enter를 누르세요..."
echo ""

# 4단계: Wi-Fi로 ADB 연결
echo "[4단계] Wi-Fi로 ADB 연결 시도..."
adb connect $PHONE_IP:5555

if [ $? -ne 0 ]; then
    echo "❌ 연결 실패"
    echo "   수동 연결 명령: adb connect $PHONE_IP:5555"
    exit 1
fi

sleep 2
echo ""

# 5단계: 연결 확인
echo "[5단계] 연결 확인..."
adb devices -l

echo ""
echo "============================================================"
echo "✅ ADB over Wi-Fi 설정 완료!"
echo "============================================================"
echo ""
echo "다음 단계:"
echo "  1. DoU 프로그램 실행"
echo "  2. Refresh 버튼 클릭"
echo "  3. DAQ로 Battery Rail 측정 → 3.95V 확인"
echo ""
echo "Wi-Fi ADB 해제 방법:"
echo "  adb disconnect $PHONE_IP:5555"
echo "  adb usb  (USB 케이블 다시 연결 후)"
echo ""

import nidaqmx
import numpy as np
from typing import List, Tuple, Optional
from nidaqmx.constants import AcquisitionType

def DAQReadNChanNSamp1DWfm(
    task_name: str,
    num_channels: int,
    timeout: float,
    sample_rate: float,
    *channel_data_arrays
) -> Tuple[int, float, List[List[float]]]:
    """
    NI-DAQmx 기반 DAQReadNChanNSamp1DWfm 구현

    Args:
        task_name: DAQmx Task 이름
        num_channels: 채널 수
        timeout: 타임아웃 (초)
        sample_rate: 샘플링 주기 (초)
        *channel_data_arrays: 각 채널의 데이터 배열 포인터

    Returns:
        (status, actual_sample_rate, data)
    """

    try:
        # Task 이름 추출 (Dev1 형식)
        device_name = task_name.split("<")[0].strip("_").upper()

        # 채널 이름 생성 (ai0 ~ ai59)
        channels = [f"{device_name}/ai{i}" for i in range(num_channels)]

        # 실제 샘플링 주기 계산
        actual_sample_rate_val = sample_rate

        # 샘플링 주파수 계산
        sample_frequency = 1.0 / actual_sample_rate_val

        # 데이터 수집 시간 계산 (타임아웃 기반)
        # 일반적으로 10초 동안 수집하므로 샘플 수 계산
        samples_per_channel = int(sample_frequency * timeout)

        print(f"=== DAQReadNChanNSamp1DWfm 시작 ===")
        print(f"장치: {device_name}")
        print(f"채널 수: {num_channels}")
        print(f"샘플링 주파수: {sample_frequency:.1f} Hz")
        print(f"샘플 수: {samples_per_channel}")

        # 데이터 저장용 리스트
        all_channel_data = []

        with nidaqmx.Task() as task:
            # 아날로그 입력 채널 추가 (Differential 모드 권장)
            for channel in channels:
                try:
                    task.ai_channels.add_ai_voltage_chan(
                        channel,
                        terminal_config=nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL,
                        min_val=-0.1,  # ±100mV 범위
                        max_val=0.1,
                        units=nidaqmx.constants.VoltageUnits.VOLTS
                    )
                    print(f"채널 추가: {channel}")
                except Exception as e:
                    print(f"채널 추가 실패 {channel}: {e}")
                    # RSE 모드로 폴백
                    task.ai_channels.add_ai_voltage_chan(
                        channel,
                        terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                        min_val=-5.0,
                        max_val=5.0,
                        units=nidaqmx.constants.VoltageUnits.VOLTS
                    )
                    print(f"폴백 사용: {channel}")

            # 샘플링 타이밍 설정
            task.timing.cfg_samp_clk_timing(
                rate=sample_frequency,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=samples_per_channel
            )

            print(f"샘플링 시작...")
            task.start()

            # 데이터 읽기
            data = task.read(
                number_of_samples_per_channel=samples_per_channel,
                timeout=timeout + 5.0
            )

            task.stop()
            print(f"샘플링 완료")

            # 데이터 처리 (채널별 분리)
            if num_channels == 1:
                # 단일 채널
                channel_data = list(data)
                all_channel_data.append(channel_data)

                # 출력 배열에 데이터 복사 (channel_data_arrays 활용)
                if channel_data_arrays and len(channel_data_arrays) > 0:
                    output_array = channel_data_arrays[0]
                    output_array.extend(channel_data)

            else:
                # 다중 채널 (인터리빙 데이터)
                # 데이터를 채널별로 재구성
                for i in range(num_channels):
                    channel_data = []
                    for j in range(i, len(data), num_channels):
                        if j < len(data):
                            channel_data.append(data[j])
                    all_channel_data.append(channel_data)

                    # 출력 배열에 데이터 복사
                    if i < len(channel_data_arrays):
                        output_array = channel_data_arrays[i]
                        output_array.extend(channel_data)

            print(f"데이터 처리 완료: {len(all_channel_data)} 채널")
            return (0, actual_sample_rate_val, all_channel_data)

    except Exception as e:
        print(f"DAQReadNChanNSamp1DWfm 오류: {e}")
        import traceback
        traceback.print_exc()
        return (-1, actual_sample_rate_val, [])

# 사용 예시
def example_usage():
    """DAQReadNChanNSamp1DWfm 사용 예시"""

    # 출력 데이터 배열 (각 채널용)
    channel_data = [[] for _ in range(60)]  # 60개 채널

    # 함수 호출
    status, actual_rate, data = DAQReadNChanNSamp1DWfm(
        "_unnamedTask<D>",
        60,
        10.0,
        0.000033,
        *channel_data
    )

    if status == 0:
        print(f"성공: {len(data)} 채널 데이터 수집")
        print(f"실제 샘플링 주기: {actual_rate:.6f}초")

        # 통계 출력
        for i, channel_data in enumerate(data[:5]):  # 처음 5개 채널만 출력
            if channel_data:
                avg_voltage = np.mean(channel_data)
                print(f"채널 {i}: 평균 전압 = {avg_voltage*1000:.6f} mV")
    else:
        print(f"실패: 상태 코드 {status}")

if __name__ == "__main__":
    example_usage()

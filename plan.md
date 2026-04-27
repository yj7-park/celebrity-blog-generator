# IP 변경 전략 (스마트폰 USB 테더링 및 ADB 활용)

블로그 자동 게시 시 동일 IP 사용으로 인한 제재를 피하기 위해, 스마트폰 USB 테더링과 ADB(Android Debug Bridge)를 활용하여 외부 IP를 동적으로 변경하는 전략입니다.

## 1. 핵심 원리
- 모바일 네트워크(LTE/5G)는 재접속 시 유동 IP를 할당받는 특성이 있습니다.
- ADB 명령어를 통해 스마트폰의 **비행기 모드(Airplane Mode)**를 껐다 켬으로써 네트워크를 재접속시키고 새로운 IP를 할당받습니다.

## 2. 구현 방법 (Python 예시)

```python
import os
import time
import requests
import subprocess

def get_current_ip():
    try:
        # 외부 IP 확인 서비스 이용
        return requests.get("https://api.ipify.org", timeout=5).text
    except Exception:
        return "Unknown"

def change_ip_via_adb():
    """
    ADB 명령어로 비행기 모드를 토글하여 IP를 변경합니다.
    필수 조건: 스마트폰 USB 디버깅 활성화, PC에 ADB 설치됨.
    """
    print(f"변경 전 IP: {get_current_ip()}")
    
    # 1. 비행기 모드 활성화
    subprocess.run(["adb", "shell", "settings", "put", "global", "airplane_mode_on", "1"])
    subprocess.run(["adb", "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true"])
    time.sleep(3)
    
    # 2. 비행기 모드 비활성화
    subprocess.run(["adb", "shell", "settings", "put", "global", "airplane_mode_on", "0"])
    subprocess.run(["adb", "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "false"])
    
    # 3. 네트워크 재접속 대기 (통신사 및 기기 환경에 따라 조절)
    print("네트워크 재접속 대기 중 (약 15초)...")
    time.sleep(15) 
    
    new_ip = get_current_ip()
    print(f"변경 후 IP: {new_ip}")
    return new_ip
```

## 3. 적용 시나리오
- **포스팅 주기별 변경**: `scheduler`를 통해 포스팅 작업이 끝날 때마다 IP를 변경합니다.
- **블로그 소스별 변경**: 서로 다른 네이버 아이디로 게시할 때, 로그인 전에 IP 변경 로직을 호출합니다.

## 4. 주의사항
- **테더링 어댑터 인식**: 비행기 모드 전환 시 PC에서 네트워크 연결이 끊겼다가 다시 연결되는 과정이 필요하므로 충분한 대기 시간(Sleep)을 주어야 합니다.
- **기기별 명령어 차이**: 안드로이드 버전에 따라 `settings put` 명령어만으로는 실제 모드 전환이 안 될 수 있으며, 이 경우 UI 자동화(input tap) 방식을 고려해야 합니다.
- **중복 IP 체크**: 드물게 동일한 IP가 할당될 수 있으므로, 변경 전후의 IP가 다른지 확인하는 검증 로직이 권장됩니다.

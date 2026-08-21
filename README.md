# Outlook OTP Autofill

Classic Outlook의 OTP 메일을 읽어 Chrome에 자동 입력합니다.

## 지원 환경

- Windows 10/11
- Classic Outlook
- Google Chrome

New Outlook, Outlook Web, Edge는 지원하지 않습니다.

## 자동 설치

1. `OutlookOtpAutofillSetup.exe`를 실행합니다.
2. `Windows 로그인 시 자동 시작`을 선택합니다.
3. 설치 후 `Outlook 진단`을 실행합니다.
4. COM, MAPI, Inbox가 `True`인지 확인합니다.

설치 위치: `%LOCALAPPDATA%\Programs\OutlookOtpAutofill`

로그 위치: `%LOCALAPPDATA%\Programs\OutlookOtpAutofill\logs\app.log`

## 수동 설치

Python 3.11 이상이 필요합니다.

```powershell
git clone https://github.com/serimmmaime/otp-automation.git
cd otp-automation
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

자동실행 등록:

```powershell
.\install_chrome_autostart.ps1
```

수동 실행:

```powershell
.\.venv\Scripts\python.exe main.py
```

## 사용

1. Classic Outlook을 실행합니다.
2. Chrome에서 OTP 입력 화면을 엽니다.
3. 인증코드를 요청합니다.
4. 코드가 입력되면 제출합니다.

정상 로그:

```text
OTP-like message detected
OTP filled into active Chrome window
```

OTP와 메일 내용은 로그에 기록하지 않습니다.

<details>
<summary><strong>진단 방법</strong></summary>

### Outlook 진단

설치판은 시작 메뉴의 `Outlook 진단`을 실행합니다. 소스 실행 환경에서는 다음 명령을 사용합니다.

```powershell
.\.venv\Scripts\python.exe main.py --diagnose-outlook
```

정상 상태의 핵심 항목:

```text
Classic Outlook COM available: True
Outlook MAPI session available: True
Default Inbox available: True
Outlook access errors: 0
```

`Metadata matches`가 0인 것은 최근 유효 메일이 없다는 뜻일 수 있으므로 오류가 아닙니다.

### Chrome 진단

OTP 페이지를 연 뒤 다음 명령을 실행하고 5초 안에 Chrome 탭을 활성화합니다.

```powershell
.\.venv\Scripts\python.exe main.py --diagnose-chrome --diagnose-delay 5
```

### 로그 확인

```powershell
Get-Content .\logs\app.log -Tail 50
```

</details>

<details>
<summary><strong>테스트와 자동실행 관리</strong></summary>

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

자동실행 등록과 해제:

```powershell
.\install_chrome_autostart.ps1
.\install_chrome_autostart.ps1 -Uninstall
```

자동실행 감시기는 Chrome이 실행되면 OTP 프로그램을 시작하고 Chrome이 완전히 종료되면 함께 종료합니다.

</details>

<details>
<summary><strong>설정</strong></summary>

주요 설정은 `config.json`에 있습니다.

| 설정 | 의미 |
|---|---|
| `email_subject_keywords` | 허용할 제목 문자열 |
| `email_sender_display_names` | 허용할 발신 표시 이름 |
| `email_allowed_sender_addresses` | 허용할 실제 SMTP 주소. 값이 있으면 표시 이름보다 우선 |
| `email_otp_pattern` | OTP 본문 정규식. 캡처 그룹은 정확히 하나 필요 |
| `email_max_age_seconds` | 메일 유효시간 |
| `email_poll_interval_seconds` | 받은편지함 확인 간격 |
| `email_max_items` | 확인할 최신 메일 수 |
| `dedupe_ttl_seconds` | 동일 코드 재처리 차단 시간 |
| `auto_submit` | 입력 후 Enter 실행 여부 |
| `dry_run` | 실제 입력 없이 탐지만 수행 |

메일을 읽음 처리하거나 삭제하는 설정은 안전을 위해 허용하지 않습니다.

</details>

<details>
<summary><strong>동작 원리와 보안</strong></summary>

```text
Classic Outlook 기본 받은편지함
  → 수신 시각·제목·발신자 검사
  → 조건 통과 후 본문에서 OTP 추출
  → 만료·중복 검사
  → 활성 Chrome의 안전한 입력란 검사
  → OTP 입력
```

- Outlook의 로컬 COM Object Model을 읽기 전용으로 사용합니다.
- 메일을 읽음 처리, 이동, 삭제 또는 회신하지 않습니다.
- 조건에 맞지 않는 메일은 본문을 읽기 전에 제외합니다.
- 실제 OTP와 메일 원문을 로그에 남기지 않습니다.
- OTP는 메모리에서만 사용합니다.
- 기본값에서는 Enter나 확인 버튼을 누르지 않습니다.
- 화면 잠금이나 RDP 연결 종료 상태에서는 UI 입력이 실패할 수 있습니다.

</details>

<details>
<summary><strong>빌드와 설치 프로그램 생성</strong></summary>

```powershell
.\build_exe.ps1
```

이 명령은 테스트를 통과한 뒤 실행 파일 3개와 Inno Setup 설치 프로그램을 생성합니다. 중간 단계가 실패하면 설치 프로그램을 만들지 않습니다.

출력 위치:

```text
dist\otp_autofill.exe
dist\chrome_watcher.exe
dist\otp_diagnostics.exe
installer\Output\OutlookOtpAutofillSetup.exe
```

</details>

## 문제 보고

다음 정보만 전달하세요.

- `--diagnose-outlook` 결과
- `--diagnose-chrome`의 값이 가려진 결과
- `logs\app.log`의 오류 구간
- 단일 입력란인지 분할 입력란인지

실제 OTP, 메일 본문, 계정 주소와 내부 URL은 공유하지 마세요.

## License

Private personal project. 본인이 이용 권한을 가진 계정과 서비스에서만 사용하세요.

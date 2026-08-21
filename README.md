# Outlook OTP Autofill

Windows의 Classic Outlook 받은편지함에서 조건에 맞는 OTP 메일을 읽고, 현재 활성화된 Chrome 인증 입력란에 코드를 입력하는 로컬 도구입니다. 메일과 웹사이트를 변경하지 않으며 기본 설정에서는 확인 버튼도 누르지 않습니다.

## 실행 조건

아래 조건을 **모두** 만족해야 자동 입력됩니다.

### 메일 조건

- Windows용 **Classic Outlook 데스크톱 앱**에 계정 로그인이 완료되어 있어야 합니다.
- New Outlook과 Outlook Web은 지원하지 않습니다.
- OTP 메일이 기본 받은편지함에 도착해야 합니다.
- 메일의 제목, 발신자, 본문 형식이 `config.json`의 다음 설정과 일치해야 합니다.
  - `email_subject_keywords`
  - `email_sender_display_names` 또는 `email_allowed_sender_addresses`
  - `email_otp_pattern`
- 메일 수신 시각이 현재 시각 기준 `email_max_age_seconds` 이내여야 합니다. 기본값은 90초입니다.
- 프로그램 시작 직전에 도착한 메일도 유효시간 안이면 복구합니다.

Outlook으로 도착한 모든 숫자를 입력하는 프로그램은 아닙니다. 위 필터를 통과한 메일만 본문을 읽고 OTP를 추출합니다.

### 브라우저 조건

- **Google Chrome**만 지원합니다. Edge와 다른 브라우저는 지원하지 않습니다.
- OTP를 입력할 Chrome 창과 해당 탭이 화면 앞으로 활성화되어 있어야 합니다.
- 입력란이 Windows UI Automation의 `Edit` 컨트롤로 노출되어야 합니다.
- 입력란 이름에 `OTP`, `code`, `인증`, `보안 코드` 등 `input_keywords` 중 하나가 포함되어야 합니다.
- 이름 없는 입력란은 사용자가 직접 클릭해 키보드 포커스를 둔 경우에만 허용됩니다.
- 단일 입력란 또는 코드 길이와 같은 개수의 4~8개 분할 입력란을 지원합니다.
- password, email, username, search, address, phone 계열 입력란은 제외합니다.

특정 웹사이트나 도메인에 고정되어 있지는 않습니다. 현재 구현에는 도메인 제한 검사가 없으므로 위 조건을 만족하는 어떤 Chrome 페이지에서도 입력할 수 있습니다.

### Windows 상태 조건

- Windows 사용자가 로그인되어 있고 데스크톱이 잠기지 않아야 합니다.
- Outlook 받은편지함 동기화가 가능해야 합니다.
- 자동실행 감시기와 Chrome 프로세스가 실행 중이어야 합니다.
- OTP가 감지된 순간 다른 창이 활성화되어 있어도 유효시간 동안 0.5초 간격으로 다시 시도합니다. 유효시간이 끝나면 입력하지 않습니다.

## 설치

가장 쉬운 방법은 `OutlookOtpAutofillSetup.exe`를 실행하는 것입니다. Python이나 Git을 별도로 설치할 필요가 없습니다.

1. Classic Outlook과 Chrome을 설치하고 로그인합니다.
2. 설치 프로그램을 실행합니다.
3. `Windows 로그인 시 자동 시작`을 선택합니다.
4. 시작 메뉴에서 `Outlook 진단`을 실행합니다.
5. COM, MAPI session, Default Inbox가 모두 `True`인지 확인합니다.
6. Chrome에서 OTP 입력 화면을 활성화하고 새 코드를 요청합니다.

기본 설치 위치는 `%LOCALAPPDATA%\Programs\OutlookOtpAutofill`이며 관리자 권한이 필요하지 않습니다. 로그는 설치 폴더의 `logs\app.log`에 저장됩니다.

## 사용

1. Classic Outlook의 받은편지함 동기화를 확인합니다.
2. Chrome에서 OTP 입력 페이지를 엽니다.
3. OTP 입력란을 클릭합니다.
4. 인증코드 발송을 요청합니다.
5. Chrome 탭을 화면 앞으로 유지합니다.
6. 코드가 입력되면 확인 후 직접 제출합니다.

정상 로그:

```text
OTP-like message detected
OTP filled into active Chrome window
```

실제 OTP, 메일 제목, 발신자와 본문은 로그에 기록되지 않습니다.

## 지원 범위

| 항목 | 지원 |
|---|---|
| Classic Outlook 데스크톱 | 지원 |
| New Outlook / Outlook Web | 미지원 |
| Google Chrome | 지원 |
| Edge 및 기타 브라우저 | 미지원 |
| 단일 OTP 입력란 | 지원 |
| 4~8개 분할 OTP 입력란 | 지원 |
| 시작 직전 도착한 유효 OTP 복구 | 지원 |
| 입력 후 자동 제출 | 기본값 미사용 |
| 특정 웹사이트 제한 | 기본값 없음 |

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

단일 입력란은 양수 `score`를 가진 `Edit`가 정확히 하나여야 합니다. 분할 입력란은 모든 칸이 `Edit`로 노출되어야 합니다.

### 로그 확인

```powershell
Get-Content .\logs\app.log -Tail 50
```

</details>

<details>
<summary><strong>소스에서 실행·테스트</strong></summary>

요구사항은 Windows 10/11, Python 3.11 이상, Classic Outlook, Chrome입니다.

```powershell
git clone https://github.com/serimmmaime/otp-automation.git
cd otp-automation
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
.\.venv\Scripts\python.exe -m pytest -q
```

수동 실행:

```powershell
.\.venv\Scripts\python.exe main.py
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
| `input_keywords` | 허용할 입력란 이름 키워드 |
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

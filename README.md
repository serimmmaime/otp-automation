# Outlook OTP Autofill

Windows 10/11에서 **Classic Outlook으로 새로 도착한 SSO 인증 메일을 감지해 현재 활성화된 Chrome 인증 입력란에 입력**하는 로컬 Python 도구입니다. 저장소 이름은 기존 이름을 유지하지만, 기본 수신원은 KakaoTalk이 아닌 Outlook입니다.

> 현재 상태: 실제 회사 Outlook 받은편지함 → 메일 필터 → OTP 추출 → 활성 Chrome 입력까지 E2E 성공. 자동 제출은 OFF로 검증했습니다.

## 평소 실행 방법

1. **Classic Outlook 데스크톱 앱**을 실행하고 회사 받은편지함 동기화를 기다립니다.
2. PowerShell에서 프로젝트 폴더로 이동합니다.
3. 아래 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe main.py
```

다음 로그가 나오면 준비된 상태입니다.

```text
READY: request a new OTP now; messages already visible were ignored
```

4. Chrome의 SSO 인증 화면으로 이동합니다.
5. 보안 코드 입력칸을 한 번 클릭합니다.
6. 인증 요청 버튼을 누르고 **코드가 채워질 때까지 Chrome을 활성 창으로 유지**합니다.
7. 코드가 자동 입력되면 내용을 확인하고 직접 확인 버튼을 누릅니다.

성공 로그:

```text
OTP-like message detected
OTP filled into active Chrome window
```

프로그램은 다음 인증 요청을 계속 기다립니다. 사용이 끝나면 PowerShell에서 `Ctrl+C`로 종료합니다. 실제 OTP, 메일 제목, 발신자, 본문은 로그에 출력되지 않습니다.

처음 설치하는 PC이거나 `.venv`가 없다면 한 번만 다음 명령을 사용합니다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

## Chrome 실행 시 자동 시작

먼저 `.venv` 설치와 수동 실행이 정상 동작하는지 확인한 뒤, PowerShell에서 한 번만 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install_chrome_autostart.ps1
```

설치 후 Windows에 다음 로그인할 때부터 `pythonw.exe` 기반의 숨은 감시기가 실행됩니다. 회사 그룹 정책에서 Windows PowerShell 실행을 차단해도 자동 시작 경로에서는 PowerShell을 사용하지 않습니다.

- Chrome이 실행되면 OTP Autofill이 `pythonw.exe` 백그라운드 프로세스로 자동 시작됩니다.
- Chrome이 완전히 종료되면 해당 OTP Autofill 프로세스도 종료됩니다.
- 창이 숨겨져 있으므로 상태는 `logs\app.log`에서 확인합니다.
- Chrome의 `백그라운드 앱 계속 실행` 옵션이 켜져 있으면 Chrome 프로세스가 남아 유틸리티도 계속 실행될 수 있습니다.
- 자동 입력 순간에는 여전히 Chrome OTP 화면이 활성 창이어야 합니다.

자동 시작을 제거하려면:

```powershell
.\install_chrome_autostart.ps1 -Uninstall
```

이 명령은 Windows 시작프로그램의 `Outlook OTP Autofill` 바로가기만 제거하며 프로젝트 파일은 삭제하지 않습니다.

## 현재 검증 상태

- Classic Outlook COM, MAPI session, 기본 받은편지함 접근 성공
- 실제 SSO 메일의 제목·한글 발신 표시 이름·본문 형식 검출 성공
- Outlook COM의 한국 시간대(+09:00) 보정 검증
- Dry-run에서 활성 Chrome OTP 필드 탐지 성공
- 실제 단일 OTP 입력란 autofill 성공, 자동 제출 없음
- 자동 테스트 `65 passed`, 전체 Python 컴파일 성공

## 동작 방식

```text
Classic Outlook 받은편지함 (읽기 전용 COM)
  → 프로그램 시작 후 도착한 새 메일만 선택
  → 수신 90초 이내 + 정확한 제목 + 허용 발신자 검사
  → 본문 "인증코드 [6자리]"만 추출
  → 동일 코드 중복 차단
  → 현재 활성 Chrome + 안전한 OTP 입력란 검사
  → 입력 (자동 제출은 기본 OFF)
```

Outlook 화면을 긁거나 키보드로 복사하지 않습니다. Classic Outlook이 제공하는 로컬 COM Object Model을 사용하므로 Outlook 창이 뒤에 있어도 메일을 읽을 수 있습니다. **New Outlook과 Outlook Web은 이 COM 방식을 지원하지 않습니다.**

## 보안 원칙

- 메일 제목, 발신자, 본문, 실제 OTP를 로그에 남기지 않습니다.
- 조건에 맞지 않는 메일은 본문을 읽기 전에 제외합니다.
- 시작 전에 받은 메일은 기준선으로 등록해 입력하지 않습니다.
- 메일을 읽음 처리하거나 이동·삭제·회신하지 않습니다.
- OTP는 메모리에서만 사용하고 중복 확인에는 SHA-256 fingerprint만 사용합니다.
- Chrome이 활성 창이 아니면 입력하지 않습니다.
- password/email/username/search/address/phone 필드는 제외합니다.
- `auto_submit`은 기본값과 현재 설정 모두 `false`입니다.

## 요구사항

- Windows 10/11
- Python 3.11 이상
- **Classic Outlook desktop**에 회사 계정 로그인 완료
- Google Chrome

Classic Outlook인지 확인하려면 Outlook의 `파일` 메뉴가 있는지 보세요. New Outlook만 설치된 PC라면 Microsoft Graph 방식이 필요하며, 회사 Entra ID 앱 등록의 Tenant ID와 Client ID가 별도로 필요합니다.

## 설치 및 자동 테스트

PowerShell에서 이 폴더로 이동한 뒤:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1 --diagnose-outlook
.\.venv\Scripts\python.exe -m pytest -q
```

`run.ps1`은 `.venv` 생성, 의존성 설치, Python 버전 확인을 자동으로 수행합니다.

## 1단계: Outlook 진단

Classic Outlook을 먼저 실행하고 받은편지함 동기화가 끝난 뒤:

```powershell
.\.venv\Scripts\python.exe main.py --diagnose-outlook
```

예상 형식:

```text
Classic Outlook COM available: True
Outlook MAPI session available: True
Outlook stores: 1
Default Inbox available: True
Recent messages checked: 50
Metadata matches: 1
Received within 30 minutes: 1
Subject filter passes: 1
Sender filter passes: 1
Body pattern passes: 1
Newest message calculated age (seconds): 10
Outlook access errors: 0
Email subjects, senders, bodies, and OTP values are intentionally hidden.
```

`Metadata matches`는 최근 90초 내 메일만 세므로 0이어도 정상일 수 있습니다. 핵심은 COM/MAPI/Inbox가 `True`이고 access errors가 0인 것입니다. 진단은 메일을 변경하지 않습니다.

## 2단계: Chrome 진단

SSO 인증코드 입력 화면을 열어둔 뒤 실행하고, 5초 안에 해당 Chrome 창을 클릭합니다.

```powershell
.\.venv\Scripts\python.exe main.py --diagnose-chrome --diagnose-delay 5
```

단일 보안 코드 입력란이라면 양수 `score`를 가진 Edit가 정확히 하나 있어야 합니다. 4~8개의 split OTP 입력란도 지원하지만 모든 칸이 UIA `Edit`이고 OTP 라벨을 가져야 합니다. 실제 이름과 값은 진단에서 숨깁니다.

## 3단계: Dry-run 실환경 테스트

이 순서를 지키는 것이 중요합니다.

1. Classic Outlook을 실행하고 받은편지함 동기화를 완료합니다.
2. Chrome에서 OTP 입력 화면을 열고 활성화합니다.
3. 아래 명령을 실행합니다.
4. `READY` 로그가 나온 **후** 웹사이트에서 인증코드 발송을 누릅니다.

```powershell
.\.venv\Scripts\python.exe main.py --dry-run
```

성공 예상 로그:

```text
OTP Autofill started
Initializing configured OTP source: outlook_com
READY: request a new OTP now; messages already visible were ignored
OTP-like message detected
Chrome OTP field detected; dry-run enabled, autofill skipped
```

실제 OTP와 메일 내용은 출력되지 않아야 합니다. 종료는 `Ctrl+C`입니다.

## 4단계: 실제 입력

Dry-run 성공 후 같은 순서로 실행합니다.

```powershell
.\.venv\Scripts\python.exe main.py
```

기본값에서는 입력만 하고 Enter 또는 확인 버튼을 누르지 않습니다.

## 설정

주요 설정은 `config.json`입니다.

| 설정 | 현재값 | 설명 |
|---|---:|---|
| `otp_source` | `outlook_com` | 기본 메일 수신원. 필요 시 `kakao_uia`로 복귀 가능 |
| `email_subject_keywords` | SSO 제목 | 하나라도 포함해야 함 |
| `email_sender_display_names` | 영문/한글 발신 표시 이름 | 주소 allowlist가 비어 있을 때 정확히 일치해야 함 |
| `email_allowed_sender_addresses` | `[]` | 실제 SMTP 주소를 확인하면 가장 먼저 채울 권장 allowlist |
| `email_otp_pattern` | 6자리 전용 | capture group은 정확히 하나여야 함 |
| `email_max_age_seconds` | `90` | 오래된 메일 거부 |
| `email_poll_interval_seconds` | `2.0` | 받은편지함 확인 간격 |
| `email_max_items` | `50` | 매 회차 확인할 최신 항목 상한 |
| `otp_min_length` / `otp_max_length` | `4` / `8` | 공통 파서 허용 범위 |
| `dedupe_ttl_seconds` | `600` | 동일 OTP 재처리 차단 |
| `auto_submit` | `false` | 입력 후 Enter 여부 |
| `dry_run` | `false` | 실제 키 입력 생략 |
| `mark_email_as_read` | `false` | 안전상 `true` 설정을 거부함 |
| `delete_email` | `false` | 안전상 `true` 설정을 거부함 |

실제 발신 SMTP 주소를 확인한 뒤 다음처럼 설정하면 표시 이름 위조에도 더 강합니다.

```json
"email_allowed_sender_addresses": ["실제-발신주소@회사도메인"]
```

주소가 설정되면 표시 이름 대신 주소 allowlist를 우선 적용합니다. 주소를 로그로 수집하지 않으므로 Outlook에서 메일의 `파일 > 속성` 또는 회사 IT를 통해 확인하세요.

## KakaoTalk fallback

기존 Kakao UI Automation 구현과 진단은 삭제하지 않았습니다. `otp_source`를 `kakao_uia`로 바꾸면 사용할 수 있지만, 읽기 전용 채팅방의 접근성 구조가 불안정하므로 기본값이 아닙니다.

```powershell
.\.venv\Scripts\python.exe main.py --diagnose-kakao
```

## 프로젝트 구조

```text
main.py                    실행·설정·공통 파이프라인
chrome_watcher.py          Chrome 실행/종료 감시(백그라운드)
install_chrome_autostart.ps1  Windows 시작프로그램 등록/해제
email_source/outlook.py    Classic Outlook 읽기 전용 수신원
browser/autofill.py        Chrome 활성창·필드 점수·단일/split 입력
otp/parser.py              4~8자리 파싱·fingerprint 중복방지
kakao/listener.py          선택형 Kakao UIA fallback
utils/logger.py            OTP/원문 없는 순환 로그
tests/                     실제 Outlook 없이 실행되는 mock 테스트 포함
```

## 알려진 제한과 다음 단계

- Classic Outlook COM은 New Outlook에서 동작하지 않습니다.
- 회사 보안 정책에 따라 최초 COM 접근 경고 또는 차단이 발생할 수 있습니다.
- 발신자의 실제 SMTP 주소 allowlist는 아직 비어 있습니다.
- Chrome 페이지가 입력란을 UIA `Edit`로 공개하지 않으면 필드 탐지가 불가능합니다.
- 실제 회사 메일을 이용한 단일 OTP 입력 E2E는 성공했으며 split OTP는 mock 자동 테스트까지 완료했습니다.
- 장기적으로 Outlook 앱과 무관하게 동작하려면 Microsoft Graph adapter를 추가할 수 있으나 회사 IT의 앱 등록 승인이 필요합니다.

## 문제 보고 시 전달할 정보

- `pytest -q`의 passed/failed 숫자
- `--diagnose-outlook` 출력 전체
- `--diagnose-chrome`의 redacted 목록
- `--dry-run` 상태 로그
- Classic Outlook인지 New Outlook인지
- OTP 입력란이 단일인지 split인지

실제 OTP, 메일 본문, 사내 URL, 계정 주소는 전달하지 마세요.

## License

Private personal project. 본인이 이용 권한을 가진 계정과 서비스에서만 사용하세요.

# LottoSpot — Claude Code 오케스트레이터 가이드

## 프로젝트 개요
로또 판매점 위치 + 명당 순위 웹앱. Spring Boot 백엔드 + React 프론트엔드.

## 기술 스택
- Backend: Spring Boot 3.x, Kotlin, MySQL 8.0, Redis
- Frontend: React 18, 카카오맵 SDK
- 데이터 수집: Python (Jsoup 크롤러 or requests)
- 빌드: Gradle

## 프로젝트 구조
```
lottospot/
├── backend/          # Spring Boot
│   ├── src/main/java/com/lottospot/
│   │   ├── domain/   # Entity, Repository
│   │   ├── service/  # 비즈니스 로직
│   │   └── api/      # REST Controller
├── frontend/         # React
│   ├── src/
│   │   ├── pages/    # 홈(지도), 랭킹, 뉴스, 마이페이지
│   │   └── components/
└── crawler/          # Python 데이터 수집
```

## 핵심 도메인 규칙
- 모든 좌표는 WGS84 (위도/경도) 기준
- 거리 계산은 MySQL ST_Distance_Sphere 사용
- 명당 스코어 = (1등당첨횟수 × 10) + (2등당첨횟수 × 3) + 최근성보정
- 동행복권 크롤링 딜레이: 최소 1초 간격 준수
- API 응답은 항상 표준 포맷: { success, data, message }

## 서브에이전트 라우팅 규칙

**병렬 실행** (독립적인 도메인):
- data-collector + backend-builder 동시 실행 가능 (단, DB 스키마 합의 먼저)
- frontend-builder는 API 스펙 확정 후 병렬 가능

**순차 실행** (의존성 있음):
- DB 스키마 → data-collector → backend-builder → frontend-builder
- 크롤러 완료 → DB 적재 확인 → API 테스트

**각 에이전트 호출 시 필수 포함 정보**:
1. 작업 범위 (어떤 파일/기능)
2. 입력/출력 형식
3. 완료 기준
4. 의존 파일 경로

## 자동 승인 규칙
다음은 확인 없이 바로 실행:
- 파일 읽기/검색 (find, grep, cat, ls)
- 의존성 확인 (find ~/.gradle, ls node_modules)
- 빌드/테스트 (./gradlew build, ./gradlew test, npm run dev, npm run build)
- 패키지 설치 (pip install, npm install)
- 샘플 데이터 실행 (--test, --dry-run 플래그 포함)
- Git 읽기 (git status, git log, git diff)

다음은 반드시 확인:
- DB 데이터 직접 수정/삭제 (UPDATE, DELETE, DROP)
- 외부 API 대량 호출 (크롤링 전체 실행)
- Git push, 브랜치 삭제

## 환경변수 (로컬 .env)
```
DB_URL=jdbc:mysql://localhost:3306/lottospot
DB_USER=root
DB_PASS=...
REDIS_HOST=localhost
KAKAO_API_KEY=...
DATA_GO_API_KEY=...   # 공공데이터포털
```

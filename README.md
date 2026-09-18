# GovBiz-infra

GovBiz 서비스를 함께 실행하기 위한 **별도 인프라 저장소**입니다.
애플리케이션 코드는 두 Git submodule에 있으며, 브랜치·PR·리뷰·CI는 각 서비스 저장소에서 독립적으로 관리합니다.
서비스의 `origin`은 `ilil1/SKN34-3rd-1Team`, `ilil1/SKN34-4th-1Team` 포크를 가리키며, 작업 브랜치도 해당 포크에 푸시합니다.

| 저장소 | 책임 |
| --- | --- |
| [SKN34-3rd-1Team](https://github.com/ilil1/SKN34-3rd-1Team) | React, Spring Boot, FastAPI AI 서비스와 기존 데이터 서비스 |
| [SKN34-4th-1Team](https://github.com/ilil1/SKN34-4th-1Team) | Django 서비스와 전용 MySQL |
| [GovBiz-infra](https://github.com/GovBiz-Team/GovBiz-infra) | 통합 Compose, 네트워크, 데이터 볼륨 연결, 사용할 서비스 커밋 |

현재 구성은 **로컬 개발용**입니다. 기존 AWS 배포 설정을 이전하거나 새 운영 배포를 수행하지 않습니다.
Django는 상태 확인 API까지 구현되어 있으며 기존 서비스의 업무·인증 API 연결은 별도 작업입니다.

## 구조

```text
compose.yaml                 두 프로젝트를 하나의 Compose 프로젝트로 구성
compose.django.yaml          Django 원본 Compose 재사용 및 이름 충돌 조정
compose.existing-data.yaml   기존 로컬 데이터 볼륨을 재사용하는 선택 설정
.env.example                 통합 환경 설정 예시
services/
  SKN34-3rd-1Team/            3차 저장소 submodule
  SKN34-4th-1Team/            4차 저장소 submodule
scripts/check-compose.py     비밀값·외부 API 없이 구성 검증 및 Django 통합 테스트
.github/workflows/ci.yml      구성 검증·격리된 Django/MySQL 테스트
```

3차 Compose는 `include`로 원래 빌드·마운트 경로를 보존합니다.
Django는 원본 Compose의 `web`, `db`를 `extends`로 재사용하되,
통합 환경에서는 `django-api`, `django-mysql`로 이름을 바꿉니다.
Django 의존 대상·DB 주소·데이터 볼륨도 함께 변경하므로 React의 `web`이나 기존 MySQL과 충돌하지 않습니다.

## 준비

- Git과 Docker Desktop의 Linux 컨테이너 엔진
- Docker Compose 2.24.4 이상 (`include`, `!override` 사용)
- 이 비공개 저장소와 각 submodule에 대한 읽기 권한
- 검증 스크립트를 직접 실행할 때는 Python 3.11 이상

```bash
git clone --recurse-submodules https://github.com/GovBiz-Team/GovBiz-infra.git
cd GovBiz-infra
```

이미 복제했다면 `git submodule sync --recursive`로 `.gitmodules`의 원격 주소를 로컬에 반영한 뒤, `git submodule update --init --recursive`로 기록된 커밋을 받습니다.
일반 실행에서는 `git submodule update --remote`를 사용하지 않습니다.
인프라 커밋에 기록된 서비스 버전을 사용해야 팀원들이 같은 구성을 재현할 수 있습니다.

## 처음 실행하는 PC

PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item services/SKN34-3rd-1Team/.env.example services/SKN34-3rd-1Team/.env
Copy-Item services/SKN34-4th-1Team/.env.example services/SKN34-4th-1Team/.env
```

Linux/macOS에서는 `Copy-Item` 대신 `cp`를 사용합니다.
이미 설정 파일이 있으면 덮어쓰지 않습니다.

3차 `.env`에 필수 `OPENAI_API_KEY`와 사용할 공고 API 설정을 입력합니다.
실제 서비스의 수집·임베딩·AI 기능을 켜면 해당 외부 API를 사용합니다.
새 환경에서 자동 적재를 원하지 않으면 3차 `.env`의
`BIZINFO_SYNC_ENABLED`, `KSTARTUP_SYNC_ENABLED`, `MSIT_SYNC_ENABLED`,
`CNTRADE_NOTICE_SYNC_ENABLED`, `SUPPORT_PROGRAM_INDEX_ENABLED`, `DEMO_SEED_ENABLED`를
`false`로 설정합니다. 통합 저장소가 이 업무 설정을 임의로 변경하지 않습니다.

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

검증 결과에 비밀값을 노출하지 않도록 일반 설정 확인은 `config --quiet`를 사용합니다.

## 환경변수 분리

| 파일 | 용도 |
| --- | --- |
| 루트 `.env` | `COMPOSE_*`, `GOVBIZ_*` 통합 설정 |
| `services/SKN34-3rd-1Team/.env` | OpenAI·공고 API 키, 기존 DB와 서비스 설정 |
| `services/SKN34-4th-1Team/.env` | Django 키, 전용 MySQL 비밀번호와 포트 |

모든 실제 `.env`는 Git에서 제외합니다.
루트 `.env`나 셸에 `MYSQL_ROOT_PASSWORD`, `DB_PASSWORD` 같은 서비스 비밀값을 공통으로 넣지 않습니다.
Compose의 상위 환경변수가 포함된 파일의 환경변수보다 우선하므로 다른 서비스의 값을 덮어쓸 수 있습니다.
`GOVBIZ_APP_ENV_FILE`, `GOVBIZ_DJANGO_ENV_FILE`로 별도 설정 파일을 지정할 수도 있습니다.

## 접속과 통신

| 서비스 | 호스트 기본 주소 | 컨테이너 사이 주소 |
| --- | --- | --- |
| React | http://127.0.0.1:5173 | `http://web:5173` |
| Spring Boot | http://127.0.0.1:8080 | `http://core-api:8080` |
| FastAPI AI | 호스트에 공개하지 않음 | `http://ai-service:8000` |
| Django | http://127.0.0.1:8001/api/v1/health/ready | `http://django-api:8000` |
| 기존 MySQL | `127.0.0.1:3306` | `mysql:3306` |
| Django MySQL | `127.0.0.1:3308` | `django-mysql:3306` |
| Qdrant | http://127.0.0.1:6333 | `http://qdrant:6333` |

기존 MySQL 호스트 포트는 3차 `.env`의 `MYSQL_HOST_PORT`를 따릅니다. 기존 PC에서 3307을 썼다면 그대로 유지합니다.
모든 호스트 포트는 `127.0.0.1`에만 바인딩합니다.
한 Compose 프로젝트의 기본 네트워크를 공유하지만 두 MySQL의 DB·계정·볼륨은 별개입니다.
Django의 허용 호스트에는 통합 서비스 이름 `django-api`를 추가합니다.
React의 기존 API 프록시는 Core API를 계속 가리킵니다.

## 기존 PC의 데이터 유지

기존 `govbiz`, `govbiz4-django` 프로젝트에서 전환할 때 사용하는 설정입니다.
동일한 데이터 볼륨을 두 DB 컨테이너에서 동시에 사용하면 안 됩니다.

1. 기존 두 프로젝트의 `.env`를 해당 submodule의 `.env`로 복사합니다. 예시 파일의 비밀번호로 바꾸지 않습니다.
2. `docker volume ls`에서 기존 볼륨을 확인합니다. 아래 기본 이름과 다르면 루트 `.env`의 `GOVBIZ_EXISTING_*` 값을 설정합니다.
3. 루트 `.env`에 다음 두 줄을 추가합니다.

```dotenv
COMPOSE_PATH_SEPARATOR=|
COMPOSE_FILE=compose.yaml|compose.existing-data.yaml
```

| 용도 | 기존 볼륨 기본값 |
| --- | --- |
| 기존 MySQL | `govbiz_mysql-data` |
| Elasticsearch | `govbiz_elasticsearch-data` |
| Qdrant | `govbiz_qdrant-data` |
| Redis | `govbiz_redis-data` |
| RabbitMQ | `govbiz_rabbitmq-data` |
| React node_modules | `govbiz_web-node-modules` |
| Django MySQL | `govbiz4-django_mysql-data` |

재사용 설정은 `external: true`여서 볼륨이 없으면 실행에 실패합니다.
새 빈 볼륨을 만들고 기존 데이터가 없는 것처럼 실행하지 않습니다.
변수 전체 이름은 `compose.existing-data.yaml`에 있습니다.

4. **기존 두 프로젝트의 원래 폴더에서**, 기존 실행에 사용했던 설정으로 컨테이너를 종료합니다. 아래는 기본 프로젝트 이름으로 실행했을 때의 명령입니다.

```powershell
# 기존 SKN34-3rd-1Team 폴더
docker compose --project-name govbiz --env-file .env -f infrastructure/compose.yaml down

# 기존 SKN34-4th-1Team 폴더
docker compose --project-name govbiz4-django --env-file .env -f compose.yaml down
```

`down`에 `-v` 또는 `--volumes`를 추가하지 않습니다. 데이터 볼륨을 삭제하는 옵션입니다.
호스트 포트만 바꿔서 기존 DB와 새 DB를 같은 데이터 볼륨으로 동시에 실행하지 않습니다.

5. `GovBiz-infra` 폴더에서 실행합니다.

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

전환하면 개발 소스 마운트도 `GovBiz-infra/services/` 아래 체크아웃으로 바뀝니다.
원래 형제 폴더의 소스를 편집해도 통합 컨테이너에 자동 반영되지 않습니다.
통합 환경에서는 해당 submodule 안에서 작업 브랜치를 만들거나, 변경을 서비스 원격에 푸시한 뒤 submodule을 갱신합니다.

원래 개발 환경으로 돌아갈 때는 통합 환경에서 먼저 `docker compose down`을 실행한 뒤 원래 두 폴더에서 실행합니다.
기존 데이터 재사용 설정을 매번 유지해야 같은 볼륨을 사용합니다.

## 일상 명령

```bash
docker compose up -d --build
docker compose logs -f django-api
docker compose logs -f core-api
docker compose exec -T django-api python manage.py test --noinput
docker compose down
```

서비스 코드 변경 후에는 해당 서비스만 `docker compose up -d --build django-api`처럼 다시 빌드할 수 있습니다.
Django 테스트는 별도 `test_govbiz4` DB를 생성·삭제합니다.

## 개발과 PR

서비스 코드는 해당 저장소에서 개발하고 그 저장소에 PR을 올립니다.
submodule은 기본적으로 특정 커밋을 checkout한 상태이므로, 수정 전에 작업 브랜치를 만듭니다.

```bash
git -C services/SKN34-4th-1Team switch -c feature/my-django-change
# 코드 수정·검증·커밋 후 해당 저장소에 push하고 PR 생성
git -C services/SKN34-4th-1Team push -u origin feature/my-django-change
```

서비스 PR이 병합되면 인프라 저장소의 별도 브랜치에서 사용할 커밋을 명시적으로 갱신합니다.

```bash
git switch -c chore/update-django-version
git -C services/SKN34-4th-1Team fetch origin
git -C services/SKN34-4th-1Team checkout --detach <사용할-커밋-SHA>
python scripts/check-compose.py --smoke
git add services/SKN34-4th-1Team
git commit -m "통합 환경의 Django 서비스 버전 갱신"
git push -u origin chore/update-django-version
```

이 PR은 `GovBiz-infra`에 올립니다.
팀원이 인프라 변경을 받을 때는 다음 명령을 사용합니다. 로컬 변경이 있다면 먼저 커밋하거나 보관합니다.

```bash
git pull
git submodule sync --recursive
git submodule update --init --recursive
```

## 검증과 CI

```bash
# Docker 엔진 없이 Compose 모델만 검증
python scripts/check-compose.py

# 임시 프로젝트에서 Django 이미지를 빌드하고 실제 MySQL 테스트 실행
python scripts/check-compose.py --smoke
git diff --check
```

검증 스크립트는 임시 환경변수 파일과 서로 다른 테스트 비밀번호로 서비스 간 설정이 섞이지 않는지 확인합니다.
소스·Dockerfile·초기화 SQL 경로, 서비스 의존 관계, 호스트 공개 범위, 데이터 볼륨 분리,
기존 데이터 재사용 매핑도 검사합니다.

`--smoke`는 무작위 이름의 격리된 프로젝트·볼륨·빈 호스트 포트를 사용합니다.
Django/MySQL만 실행하며 실제 MySQL 테스트, 호스트 HTTP 요청, 컨테이너 간 Django DNS 요청을 확인합니다.
끝나면 **검증용 프로젝트의 컨테이너와 볼륨만** 정리합니다.
기존 개발 데이터, 실제 API 키, 공고 수집·임베딩·유료 AI API는 사용하지 않습니다.

CI는 동일한 구성 검증과 Django 통합 테스트를 수행합니다.
3차 서비스 전체 빌드·업무 테스트는 3차 저장소 CI가 담당합니다.
이 검증 통과를 전체 서비스 업무 연동 또는 실제 검색·RAG 품질 검증으로 간주하지 않습니다.

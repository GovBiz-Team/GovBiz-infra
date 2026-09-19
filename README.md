# GovBiz-infra

GovBiz의 **Kubernetes 배포 설정, 로컬 GitOps 검증과 운영 전환·복구 절차를 관리하는 저장소**입니다.
애플리케이션 코드와 Docker 이미지 빌드는 [GovBiz](https://github.com/GovBiz-Team/GovBiz)
모노레포에서 관리합니다. Django 기반 `ops-service`도 그 저장소의 `backend/ops-service/`에서 개발하며,
이 저장소에는 애플리케이션 소스나 submodule을 두지 않습니다.

두 저장소의 기본 브랜치는 `develop`입니다. 앱 소스는 `GovBiz/develop`, 배포 설정은
`GovBiz-infra/develop`을 기준으로 작업합니다. 저장소·브랜치 이름 변경만으로 기존
AWS·Vercel 배포 연결이 이전되지는 않습니다.

## 현재 어디까지 구현했나요?

아래 상태는 저장소의 구현과 보존된 검증 기록을 기준으로 합니다. 실시간 AWS 상태를 재조회한 결과는 아닙니다.

Kubernetes를 포트폴리오의 필수 목표로 두고, 기존 Ops Kustomize 검증에 이어
**Core·Catalog·AI·Ops의 독립 Helm 배포와 로컬 Argo CD 정의**를 추가했습니다.
전체 MSA 업무 분리 또는 AWS 운영 전환이 완료된 상태는 아닙니다.
새 실행 방법·검증 범위·남은 과제는 [로컬 MSA·Helm·GitOps 안내](docs/msa-local.md)를 따릅니다.

| 구분 | 현재 상태 |
| --- | --- |
| 운영 환경 | 현재 운영 환경 없음. EC2 Compose·CodeBuild·SSM 설정은 앱 저장소의 재배포용 템플릿이며 자동 실행하지 않음 |
| 로컬 Kubernetes | Core·Catalog·AI·Ops 및 전용 DB를 kind에서 실행. HTTP 복제·DB 접근 거절·AI 단독 설정 롤아웃·Catalog 장애·Ops 테스트 데이터 복구 검증 완료 |
| 서비스 경계 | Catalog 원본 DB와 Core 조회용 복제본, Ops DB를 분리. 루트 Compose와 로컬 Kubernetes에 적용했으며 AWS 운영에는 반영하지 않음 |
| Helm·Argo CD | 네 Application의 원격 Git 동기화 및 AI만의 자동 설정 변경·복귀를 Argo CD Core에서 검증. 상시 운영 클러스터는 없음 |
| 아직 미구현 | Ops 관리자 인증·LLMOps 업무, 전체 내부 인증·NetworkPolicy 집행, 이미지 발행 CI와 상시 클러스터 연결, AWS Kubernetes 운영 전환 |

검증용 클러스터는 테스트 후 삭제합니다. **현재 Kubernetes가 운영 서비스를 계속 실행하고 있다는 뜻은 아닙니다.**
최신 결과는 [2026-09-20 네 서비스 검증 기록](docs/msa-validation-20260920.md),
이전 Ops 단독 결과는 [2026-09-19 검증 기록](docs/kubernetes-validation-20260919.md)에서 확인할 수 있습니다.

## 저장소와 서비스 책임

| 저장소 | 책임 |
| --- | --- |
| [GovBiz](https://github.com/GovBiz-Team/GovBiz) | React 웹·React Native 모바일·공통 패키지·`core-service`·`catalog-service`·`ai-service`·`ops-service` 코드, 테스트, Dockerfile, 로컬 Compose |
| [GovBiz-infra](https://github.com/GovBiz-Team/GovBiz-infra) | 로컬 Kubernetes 배포 설정·검증, 향후 운영/GitOps 전환·복구 절차 |

React Native 앱은 `GovBiz/frontend/mobile/`에서 웹과 함께 관리하며,
웹과 모바일의 공통 계약은 `GovBiz/frontend/packages/shared/`에서 관리합니다.

모노레포는 소스 관리 단위이며, 서비스의 프로세스·데이터·인증 책임을 합친다는 뜻이 아닙니다.

| 현재 서비스명 | GovBiz 소스 경로 | 책임과 구현 범위 |
| --- | --- | --- |
| `core-service` | [`backend/core-service/`](https://github.com/GovBiz-Team/GovBiz/tree/develop/backend/core-service) | 사용자 인증·권한, 기업·관심 공고·파트너·신청 등 사용자 업무와 공개 검색 API. 공고 분리 모드에서는 조회용 복제본을 유지 |
| `catalog-service` | [`backend/catalog-service/`](https://github.com/GovBiz-Team/GovBiz/tree/develop/backend/catalog-service) | 루트 Compose 기본 분리 서비스. 공고 수집·정규화·게시·검색 색인과 독립 원본 DB를 소유. AWS 템플릿은 아직 전환하지 않음 |
| `ai-service` | [`backend/ai-service/`](https://github.com/GovBiz-Team/GovBiz/tree/develop/backend/ai-service) | LLM·임베딩·RAG·문서 처리. `core-service`의 계정·업무 DB를 직접 소유하지 않음 |
| `ops-service` | [`backend/ops-service/`](https://github.com/GovBiz-Team/GovBiz/tree/develop/backend/ops-service) | Django 기반 운영·LLMOps 개발 기반. 현재 health/readiness·전용 DB·Gunicorn만 구현; 관리자 인증·업무 기능은 미구현 |

공고 분리 모드에서 `core-service`는 `catalog-service`의 인증된 HTTP snapshot을 검증한 뒤 자체 DB에 조회용 복제본을 유지합니다.
[공고 분리 범위·전환 조건](https://github.com/GovBiz-Team/GovBiz/blob/develop/docs/catalog-service-extraction.md)을 따릅니다.
`ops-service`의 관리자 권한 판정은 `core-service`에 위임하는 설계이며 아직 구현하지 않았습니다.

### 서비스명과 배포 식별자

소스 폴더명·실행 서비스·컨테이너·내부 DNS를 같은 서비스명으로 통일합니다.

| 현재 서비스명 | 배포 설정의 식별자 |
| --- | --- |
| `core-service` | Compose·Kubernetes Deployment·Service `core-service`, 기존 AWS 템플릿 ECR `govbiz/core-service` |
| `catalog-service` | Compose·Kubernetes Deployment·Service `catalog-service` |
| `ai-service` | Compose·Kubernetes Deployment·Service `ai-service`, 기존 AWS 템플릿 ECR `govbiz/ai-service` |
| `ops-service` | 통합 Compose `ops-service`, Kubernetes Deployment·Service `ops-service`, 로컬 검증 이미지 `govbiz-ops-service:<고유 태그>` |

네 서비스의 Helm 템플릿은 `charts/govbiz-service/`, 개별 설정은 `environments/local-msa/`입니다.
이전 Ops 단독 Kustomize 검증은 `environments/services/ops-service/base/`와 `environments/local/ops-service/`에 유지합니다.
전체 smoke의 DB Service는 `core-mysql`·`catalog-mysql`·`ops-mysql`입니다. 기존 로컬 볼륨 삭제·AWS 리소스 생성은 하지 않습니다.

테이블 소유권, 내부 통신, 인증 위임과 복제 수 확대 조건은 [서비스·데이터 경계](docs/service-boundaries.md)를 따릅니다.

기존 EC2 Compose·CodeBuild·SSM 배포 코드는 당분간 GovBiz의 `infrastructure/`에 유지합니다.
현재 가동 중인 운영 환경은 없으며, 실제 클라우드 연결·재배포는 별도 검토 후 수행합니다.
운영 클러스터 종류는 아직 확정하지 않았습니다.
프론트를 Vercel에 유지하면 해당 프론트 배포는 Argo CD의 관리 대상이 아닙니다.

## 빠른 시작: 정적 검증

이 저장소 루트에서 실행합니다. Python 3.13, Helm 4.3.0과 `kubectl` 1.36 계열이 필요하며,
`kubectl kustomize` 렌더링에는 실행 중인 클러스터가 필요하지 않습니다.
전역 Python 환경 대신 Git에서 제외되는 `.tools/` 가상환경을 사용합니다.

```bash
python3 -m venv .tools/venv
.tools/venv/bin/python -m pip install -r scripts/requirements.txt
.tools/venv/bin/python -B scripts/check_repository.py
.tools/venv/bin/python -B scripts/check_kubernetes.py
.tools/venv/bin/python -B scripts/check_msa.py
.tools/venv/bin/python -B -m unittest discover -s scripts -p 'test_*.py'
git diff --check
```

정적 검증은 저장소 경계·문서 링크, Kustomize·Helm 렌더링, manifest·Argo 정책과 검증 도구의 안전장치를 확인합니다.
실제 Kubernetes API 서버의 스키마 검증이나 Pod 실행을 대신하지 않습니다.

### 실제 클러스터 검증

[로컬 Kubernetes 실행 안내](docs/kubernetes-local.md)의 도구 버전·준비 조건을 확인한 뒤,
GovBiz에서 고유 태그의 `ops-service` 이미지를 빌드하고 이 저장소의 `scripts/smoke_kubernetes.py`를 실행합니다.
별도의 Docker Engine·kind가 필요하며, 검증용 클러스터와 이미지 다운로드에 로컬 자원을 사용합니다.
네 서비스 전체 검증은 [로컬 MSA 실행 안내](docs/msa-local.md)의 `scripts/smoke_msa.py`를 사용합니다.

smoke는 임의 이름의 **새 kind 클러스터만** 생성하고 기존 kubeconfig·운영 Secret·RDS를 사용하지 않습니다.
성공·실패 모두 자신이 만든 클러스터와 검증 데이터를 정리합니다. 기존 개발 컨테이너를 중지하거나
운영 컨텍스트에 `kubectl apply`하는 방식으로 실행하지 않습니다.

## 검증 결과

2026-09-20에는 네 서비스의 strict admission·실제 기동, 내부 인증 거절, 42개 공고 복제,
교차 DB 인증 거절, AI만의 설정 롤아웃·복귀, Catalog 중단 시 조회 유지,
Ops 테스트 테이블 dump·복원과 DB Pod 재생성 후 PVC 유지까지 통과했습니다.
Infra 단위 테스트 50개·Helm strict lint·정적 정책 검사도 통과했습니다.
Argo CD Core 3.5.3에서도 원격 Git의 A → B → A 자동 동기화와 AI만의 Pod 교체를 확인했습니다.
범위와 미검증 항목은 [최신 검증 기록](docs/msa-validation-20260920.md)을 따릅니다.

### 이전 Ops 단독 검증

아래는 [2026-09-19 로컬 실행 기록](docs/kubernetes-validation-20260919.md)의 결과입니다.
GitHub 원격 CI 또는 AWS 배포 성공을 의미하지 않습니다.

| 검증 범위 | 확인한 결과 |
| --- | --- |
| Infra | 단위 테스트 35개 통과, Kustomize 렌더링·정책 검사 통과 |
| `ops-service` | MySQL 8.4 기반 테스트 5개, lock·의존성·Ruff·Django 설정·migration 검사 통과 |
| 실제 Kubernetes | API 서버 strict dry-run, Service DNS, `ops-service` → MySQL readiness 정상 |
| DB 장애·복구 | readiness 503·liveness 200 분리, DB Pod 교체 후 PVC 검증 행 보존과 readiness 복구 |
| 앱 자동 복구·롤백 | `ops-service` Pod 삭제 후 재생성, 잘못된 이미지 배포 시 기존 healthy Pod 유지, 이전 이미지로 복구 |

단일 노드 kind와 로컬 PVC는 운영 HA·백업이 아닙니다. NetworkPolicy 집행, 부하/HPA,
전체 운영 DB의 백업·시점 복구, 관리자 인증과 유료 AI 품질은 아직 검증하지 않았습니다.
`rollout undo` 실험은 이미지 롤백이며, DB migration 롤백이나 GitOps 동기화 증거가 아닙니다.

## 구조

```text
GovBiz-infra/
├─ argocd/
│  ├─ local/                 네 Application·범위 제한 AppProject
│  └─ README.md               동기화 조건과 한계
├─ charts/                   서비스 Helm Chart·임시 데이터 저장소 Chart
├─ environments/
│  ├─ services/ops-service/base/  ops-service의 Deployment·Service (리소스명 ops-service)
│  ├─ local-msa/             네 서비스별 Helm values
│  └─ local/                  ops-service overlay·검증용 MySQL·namespace
├─ kind/local.yaml            단일 노드 검증 클러스터; 운영/HA 아님
├─ docs/
│  ├─ service-boundaries.md   서비스 책임·데이터·인증 경계의 초기 검토 기록
│  ├─ kubernetes-local.md     로컬 검증 실행·제약·후속 단계
│  ├─ msa-local.md            네 서비스 Helm·GitOps 실행·검증 범위
│  ├─ msa-validation-20260920.md  네 서비스 실제 실행 검증 기록
│  ├─ kubernetes-validation-20260919.md  실제 실행·장애·복구 증거
│  ├─ repository-transition.md 이전 개발 환경의 안전한 전환 절차
│  ├─ msa-kubernetes-argocd-plan.md
│  └─ msa-strategy-review-20260919.md
├─ scripts/
│  ├─ check_repository.py     저장소 경계·문서 링크 검증
│  ├─ check_kubernetes.py     렌더링·구성 정책 검증
│  ├─ check_msa.py            Helm·Argo 경계 검사
│  ├─ smoke_msa.py            네 서비스·DB 격리·장애·복구 검증
│  ├─ gitops_msa.py           선택형 Git revision 자동 동기화 검증
│  └─ smoke_kubernetes.py     격리 클러스터 상태·복구·롤백 검증
└─ .github/workflows/ci.yml   저장소 경계·정적 구성 검증
```

기존 로컬 `services/` 체크아웃은 작업·환경 파일을 잃지 않도록 디스크에 보존할 수 있지만,
더 이상 이 저장소의 submodule이나 개발 소스 기준이 아닙니다.
`services/`를 다시 `git add`하거나 submodule로 등록하지 않습니다.
이전 실제 환경 파일과 미커밋 변경은 [전환 안내](docs/repository-transition.md)에 따라 직접 확인·보관합니다.

## 개발은 어디에서 하나요?

새 `GovBiz` 체크아웃에서 브랜치를 만들고 해당 저장소로 PR을 올립니다.

- React: `frontend/web/`
- React Native: `frontend/mobile/`
- 웹·모바일 공통 계약: `frontend/packages/shared/`
- `core-service`: `backend/core-service/`
- `catalog-service`: `backend/catalog-service/`
- `ai-service`: `backend/ai-service/`
- `ops-service` (Django): `backend/ops-service/`
- 로컬 통합 실행: 루트 `compose.yaml`, `compose.ops.yaml`, `compose.existing-data.yaml`
- 로컬 구성 검증: `infrastructure/scripts/check-compose.py`

**이 저장소에서 `docker compose up`을 실행하지 않습니다.**
GovBiz의 실행 안내를 따르며, 기존 개발 데이터가 있다면 먼저
[환경 파일·볼륨 전환 절차](docs/repository-transition.md)를 확인합니다.

서비스명과 기존 배포 식별자는 [대응 표](#서비스명과-배포-식별자)를 참고하세요.
과거 검증 기록의 이름·이미지 태그·커밋 고정 링크는 실행 당시 값을 보존합니다.

기존 공개 GovBiz-ops 저장소는 삭제하거나 보관 처리하지 않습니다.
가져온 코드의 출처와 기준 커밋은 전환 문서에 남기고, Git 이력 전체를 합쳤다고 표시하지 않습니다.

## 목표 상시 배포 흐름 — 이미지 CI·운영 클러스터 미연결

1. GovBiz PR에서 해당 서비스와 공개 계약의 테스트를 수행합니다.
2. 신뢰된 릴리스 CI가 이미지를 빌드하여 ECR에 올립니다.
3. CI가 GovBiz-infra에 해당 환경의 이미지 digest 변경 PR을 만듭니다.
4. 검토·병합된 배포 설정을 Argo CD가 지정 Kubernetes 클러스터에 동기화합니다.

이미지 빌드는 CI, 이미지 보관은 ECR, 사용할 버전 선택은 infra PR,
실제 Kubernetes 상태 동기화는 Argo CD의 책임입니다.
ECR에 새 이미지가 올라오는 것만으로 버전 선택이나 배포가 자동 완료되지는 않습니다.
로컬 Argo CD의 Git 동기화·복귀는 검증했습니다. 자동 이미지 발행·digest 변경 PR 생성과
상시 클러스터 연결은 아직 구현·검증해야 합니다.

처음에는 로컬 검증과 명시적 동기화를 사용하며, 운영 자동 동기화 여부는 대상·권한·복구 절차를 확정한 뒤 결정합니다.
같은 환경·서비스를 기존 SSM 배포와 Argo CD가 동시에 변경하지 않도록 전환 시 배포 주체를 하나로 정합니다.

## 비밀값과 변경 승인

- 토큰, API 키, DB 비밀번호, 실제 `.env`, kubeconfig를 커밋하지 않습니다.
- Kubernetes Secret의 단순 base64 인코딩을 암호화로 취급하지 않습니다.
- 환경별 설정은 비밀값 대신 선택한 비밀 저장소의 참조를 사용하도록 설계합니다. 공급자는 아직 결정하지 않았습니다.
- 이미지 교체 롤백과 DB migration·데이터 복구는 별개입니다. 이미지 버전만 되돌려 데이터 복구까지 됐다고 판단하지 않습니다.
- 현재 앱 저장소에 있는 운영 Compose와 여기에 추가할 Kubernetes 설정이 같은 운영 대상의 두 기준이 되지 않도록 합니다.

## 다음 단계

1. `core-service`의 관리자 판정 계약에 맞춰 `ops-service` 인증과 업무 API를 구현합니다.
2. NetworkPolicy 집행, Core·AI 의존성 readiness, 장기 작업 종료·중복 실행 방지를 검증합니다.
3. 독립 이미지 발행 CI·digest 갱신과 상시 GitOps 환경을 연결합니다.
4. 운영 방식·비용·TLS·IAM·비밀값·백업을 확정하고 승인받은 뒤 AWS 환경을 구성합니다.

[MSA·Kubernetes·Argo CD 전환 설계](docs/msa-kubernetes-argocd-plan.md)와
[코드 기반 전략 검토](docs/msa-strategy-review-20260919.md)에 단계별 통과 조건을 정리했습니다.

## 관련 문서

- [GovBiz 메인 README](https://github.com/GovBiz-Team/GovBiz/blob/develop/README.md): 현재 애플리케이션 구성과 구현·배포 상태
- [3차 프로젝트 README](https://github.com/GovBiz-Team/GovBiz/blob/develop/docs/third-project/README.md): 기존 팀 소개·프로젝트 기능·평가·회고
- [환경별 설정 기준](environments/README.md) · [Argo CD 도입 조건](argocd/README.md)
- [기존 개발 환경 전환](docs/repository-transition.md) · [로컬 Kubernetes 실행](docs/kubernetes-local.md)

## CI와 검증 책임

[Infra CI](.github/workflows/ci.yml)는 애플리케이션 소스·submodule·로컬 Compose가 되돌아오지 않는지와
문서 링크, Kustomize 렌더링·로컬 구성 정책·도구 단위 테스트를 검사합니다. kind smoke는 현재 CI에서 실행하지 않습니다.
`helm-gitops` job은 Helm 4.3.0으로 네 릴리스·저장소 Chart를 lint하고 비밀값·단일 writer·Argo 권한 정책을 검증합니다.
서비스 테스트와 통합 Compose 검증은 GovBiz CI의 책임입니다.
infra CI 통과를 Kubernetes 배포, 관리자 인증, 전체 업무 연동, 실제 RAG 품질 검증으로 표시하지 않습니다.

문서만 바뀐 경우 링크·경로를 확인하고 `git diff --check`를 실행합니다.
실제 API 서버 스키마 검증과 장애·복구는 별도 kind smoke로 수행합니다. 정적 CI만으로 실행 검증을 대신하지 않습니다.

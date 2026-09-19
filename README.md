# GovBiz-infra

GovBiz의 **Kubernetes 배포 설정, 검증 도구, 향후 GitOps 전환·복구 절차를 관리하는 저장소**입니다.
애플리케이션 코드와 Docker 이미지 빌드는 [GovBiz-web](https://github.com/GovBiz-Team/GovBiz-web)
모노레포에서 관리합니다. Django Ops도 그 저장소의 `backend/ops/`에서 개발하며,
이 저장소에는 애플리케이션 소스나 submodule을 두지 않습니다.

## 현재 어디까지 구현했나요?

Kubernetes를 포트폴리오의 필수 목표로 두고, **Ops + 검증용 MySQL의 로컬 Kubernetes 실행과
장애·복구 검증까지 완료**했습니다. 전체 MSA 또는 AWS Kubernetes 운영 전환이 완료된 상태는 아닙니다.

| 구분 | 현재 상태 |
| --- | --- |
| 기존 운영 | Vercel 프론트엔드 + AWS EC2 Docker Compose 기반 백엔드 유지. 이번 작업으로 운영 설정·데이터를 변경하지 않음 |
| 로컬 Kubernetes | Gunicorn Ops와 MySQL 8.4를 격리된 kind 클러스터에 배포해 실제 실행·장애·복구·이미지 롤백 검증 완료 |
| 서비스 경계 | Core·AI·Ops의 책임, 데이터 소유권, 관리자 인증의 후속 구현 계약 정리 |
| 아직 미구현 | Argo CD 연결, Core·AI의 Kubernetes 이전, Ops 관리자 인증·LLMOps 업무 기능, AWS Kubernetes 운영 전환 |

검증용 클러스터는 테스트 후 삭제합니다. **현재 Kubernetes가 운영 서비스를 계속 실행하고 있다는 뜻은 아닙니다.**
자세한 결과는 [2026-09-19 실제 검증 기록](docs/kubernetes-validation-20260919.md)에서 확인할 수 있습니다.

## 저장소와 서비스 책임

| 저장소 | 책임 |
| --- | --- |
| [GovBiz-web](https://github.com/GovBiz-Team/GovBiz-web) | React·Core API·AI Service·Django Ops 코드, 테스트, Dockerfile, 로컬 Compose |
| [GovBiz-infra](https://github.com/GovBiz-Team/GovBiz-infra) | 로컬 Kubernetes 배포 설정·검증, 향후 운영/GitOps 전환·복구 절차 |
| GovBiz-app — 향후 | React Native 클라이언트; 웹과 동일한 공개 백엔드 계약 사용 |

모노레포는 소스 관리 단위이며, 서비스의 프로세스·데이터·인증 책임을 합친다는 뜻이 아닙니다.

- **Core API:** 사용자 인증·권한, 기업·공고·파트너·신청 등 기존 업무 데이터의 기준입니다.
- **AI Service:** LLM·임베딩·RAG·문서 처리를 실행합니다. Core의 계정·업무 DB를 소유하지 않습니다.
- **Ops:** 향후 운영 작업·평가·프롬프트 승인·감사 기록을 담당합니다. 현재는 health/readiness와
  전용 DB 연결만 구현되어 있으며, 관리자 판정은 Core에 위임하는 방향으로 설계했습니다.

테이블 소유권, 내부 통신, 인증 위임과 복제 수 확대 조건은 [서비스·데이터 경계](docs/service-boundaries.md)를 따릅니다.

기존 EC2 Compose·CodeBuild·SSM 배포 코드는 당분간 GovBiz-web의 `infrastructure/`에 유지합니다.
현재 AWS·Vercel의 source 연결, 서버 설정, DB, 이미지 버전은 이 작업으로 변경하지 않았습니다.
운영 클러스터 종류는 아직 확정하지 않았습니다.
프론트를 Vercel에 유지하면 해당 프론트 배포는 Argo CD의 관리 대상이 아닙니다.

## 빠른 시작: 정적 검증

이 저장소 루트에서 실행합니다. Python 3.13과 `kubectl` 1.36 계열이 필요하며,
`kubectl kustomize` 렌더링에는 실행 중인 클러스터가 필요하지 않습니다.
전역 Python 환경 대신 Git에서 제외되는 `.tools/` 가상환경을 사용합니다.

```bash
python3 -m venv .tools/venv
.tools/venv/bin/python -m pip install -r scripts/requirements.txt
.tools/venv/bin/python -B scripts/check_repository.py
.tools/venv/bin/python -B scripts/check_kubernetes.py
.tools/venv/bin/python -B -m unittest discover -s scripts -p 'test_*.py'
git diff --check
```

정적 검증은 저장소 경계·문서 링크, Kustomize 렌더링, manifest 정책과 검증 도구의 안전장치를 확인합니다.
실제 Kubernetes API 서버의 스키마 검증이나 Pod 실행을 대신하지 않습니다.

### 실제 클러스터 검증

[로컬 Kubernetes 실행 안내](docs/kubernetes-local.md)의 도구 버전·준비 조건을 확인한 뒤,
GovBiz-web에서 고유 태그의 Ops 이미지를 빌드하고 이 저장소의 `scripts/smoke_kubernetes.py`를 실행합니다.
별도의 Docker Engine·kind가 필요하며, 검증용 클러스터와 이미지 다운로드에 로컬 자원을 사용합니다.

smoke는 임의 이름의 **새 kind 클러스터만** 생성하고 기존 kubeconfig·운영 Secret·RDS를 사용하지 않습니다.
성공·실패 모두 자신이 만든 클러스터와 검증 데이터를 정리합니다. 기존 개발 컨테이너를 중지하거나
운영 컨텍스트에 `kubectl apply`하는 방식으로 실행하지 않습니다.

## 검증 결과

아래는 [2026-09-19 로컬 실행 기록](docs/kubernetes-validation-20260919.md)의 결과입니다.
GitHub 원격 CI 또는 AWS 배포 성공을 의미하지 않습니다.

| 검증 범위 | 확인한 결과 |
| --- | --- |
| Infra | 단위 테스트 35개 통과, Kustomize 렌더링·정책 검사 통과 |
| Ops | MySQL 8.4 기반 테스트 5개, lock·의존성·Ruff·Django 설정·migration 검사 통과 |
| 실제 Kubernetes | API 서버 strict dry-run, Service DNS, Ops → MySQL readiness 정상 |
| DB 장애·복구 | readiness 503·liveness 200 분리, DB Pod 교체 후 PVC 검증 행 보존과 readiness 복구 |
| 앱 자동 복구·롤백 | Ops Pod 삭제 후 재생성, 잘못된 이미지 배포 시 기존 healthy Pod 유지, 이전 이미지로 복구 |

단일 노드 kind와 로컬 PVC는 운영 HA·백업이 아닙니다. NetworkPolicy 집행, 부하/HPA,
DB 백업·복원, 관리자 인증, Core·AI 전체 연동과 유료 AI 품질은 아직 검증하지 않았습니다.
`rollout undo` 실험은 이미지 롤백이며, DB migration 롤백이나 GitOps 동기화 증거가 아닙니다.

## 구조

```text
GovBiz-infra/
├─ argocd/
│  └─ README.md               AppProject·Application 도입 조건
├─ environments/
│  ├─ services/operations-api/base/  Ops Deployment·Service 기본 구성
│  └─ local/                  로컬 Ops overlay·검증용 MySQL·namespace
├─ kind/local.yaml            단일 노드 검증 클러스터; 운영/HA 아님
├─ docs/
│  ├─ service-boundaries.md   Core·AI·Ops 책임·데이터·인증 계약
│  ├─ kubernetes-local.md     로컬 검증 실행·제약·후속 단계
│  ├─ kubernetes-validation-20260919.md  실제 실행·장애·복구 증거
│  ├─ repository-transition.md 이전 개발 환경의 안전한 전환 절차
│  ├─ msa-kubernetes-argocd-plan.md
│  └─ msa-strategy-review-20260919.md
├─ scripts/
│  ├─ check_repository.py     저장소 경계·문서 링크 검증
│  ├─ check_kubernetes.py     렌더링·구성 정책 검증
│  └─ smoke_kubernetes.py     격리 클러스터 상태·복구·롤백 검증
└─ .github/workflows/ci.yml   저장소 경계·정적 구성 검증
```

기존 로컬 `services/` 체크아웃은 작업·환경 파일을 잃지 않도록 디스크에 보존할 수 있지만,
더 이상 이 저장소의 submodule이나 개발 소스 기준이 아닙니다.
`services/`를 다시 `git add`하거나 submodule로 등록하지 않습니다.
이전 실제 환경 파일과 미커밋 변경은 [전환 안내](docs/repository-transition.md)에 따라 직접 확인·보관합니다.

## 개발은 어디에서 하나요?

새 `GovBiz-web` 체크아웃에서 브랜치를 만들고 해당 저장소로 PR을 올립니다.

- React: `frontend/`
- Core API: `backend/core-api/`
- AI Service: `backend/ai-service/`
- Django Ops: `backend/ops/`
- 로컬 통합 실행: 루트 `compose.yaml`, `compose.ops.yaml`, `compose.existing-data.yaml`
- 로컬 구성 검증: `scripts/check-compose.py`

**이 저장소에서 `docker compose up`을 실행하지 않습니다.**
GovBiz-web의 실행 안내를 따르며, 기존 개발 데이터가 있다면 먼저
[환경 파일·볼륨 전환 절차](docs/repository-transition.md)를 확인합니다.

기존 공개 GovBiz-ops 저장소는 삭제하거나 보관 처리하지 않습니다.
가져온 코드의 출처와 기준 커밋은 전환 문서에 남기고, Git 이력 전체를 합쳤다고 표시하지 않습니다.

## 목표 배포 흐름 — 아직 연결하지 않음

1. GovBiz-web PR에서 해당 서비스와 공개 계약의 테스트를 수행합니다.
2. 신뢰된 릴리스 CI가 이미지를 빌드하여 ECR에 올립니다.
3. CI가 GovBiz-infra에 해당 환경의 이미지 digest 변경 PR을 만듭니다.
4. 검토·병합된 배포 설정을 Argo CD가 지정 Kubernetes 클러스터에 동기화합니다.

이미지 빌드는 CI, 이미지 보관은 ECR, 사용할 버전 선택은 infra PR,
실제 Kubernetes 상태 동기화는 Argo CD의 책임입니다.
ECR에 새 이미지가 올라오는 것만으로 버전 선택이나 배포가 자동 완료되지는 않습니다.
자동 PR 생성, Argo CD 연결, 자동 동기화 정책은 별도로 구현·검증해야 합니다.

처음에는 로컬 검증과 명시적 동기화를 사용하며, 운영 자동 동기화 여부는 대상·권한·복구 절차를 확정한 뒤 결정합니다.
같은 환경·서비스를 기존 SSM 배포와 Argo CD가 동시에 변경하지 않도록 전환 시 배포 주체를 하나로 정합니다.

## 비밀값과 변경 승인

- 토큰, API 키, DB 비밀번호, 실제 `.env`, kubeconfig를 커밋하지 않습니다.
- Kubernetes Secret의 단순 base64 인코딩을 암호화로 취급하지 않습니다.
- 환경별 설정은 비밀값 대신 선택한 비밀 저장소의 참조를 사용하도록 설계합니다. 공급자는 아직 결정하지 않았습니다.
- 이미지 교체 롤백과 DB migration·데이터 복구는 별개입니다. 이미지 버전만 되돌려 데이터 복구까지 됐다고 판단하지 않습니다.
- 현재 앱 저장소에 있는 운영 Compose와 여기에 추가할 Kubernetes 설정이 같은 운영 대상의 두 기준이 되지 않도록 합니다.

## 다음 단계

1. 앱·infra 변경을 검토·병합하고 배포에 사용할 이미지와 manifest revision을 고정합니다.
2. 격리된 클러스터에서 최소권한 Argo CD AppProject·Ops Application·명시적 sync를 구현합니다.
   Git 변경 → Ops 교체 → Git revert 복귀를 실제로 검증합니다.
3. NetworkPolicy 집행과 probe·종료·단일 scheduler·상태 저장소 정책을 확인한 뒤 Core·AI를 단계적으로 이전합니다.
4. Core의 관리자 판정 계약에 맞춰 Ops 인증과 업무 API를 구현합니다.
5. Kubernetes 운영 방식·비용·TLS·IAM·비밀값·백업을 확정하고 승인받은 뒤 AWS 운영을 전환합니다.

[MSA·Kubernetes·Argo CD 전환 설계](docs/msa-kubernetes-argocd-plan.md)와
[코드 기반 전략 검토](docs/msa-strategy-review-20260919.md)에 단계별 통과 조건을 정리했습니다.

## CI와 검증 책임

[Infra CI](.github/workflows/ci.yml)는 애플리케이션 소스·submodule·로컬 Compose가 되돌아오지 않는지와
문서 링크, Kustomize 렌더링·로컬 구성 정책·도구 단위 테스트를 검사합니다. kind smoke는 현재 CI에서 실행하지 않습니다.
서비스 테스트와 통합 Compose 검증은 GovBiz-web CI의 책임입니다.
infra CI 통과를 Kubernetes 배포, 관리자 인증, 전체 업무 연동, 실제 RAG 품질 검증으로 표시하지 않습니다.

문서만 바뀐 경우 링크·경로를 확인하고 `git diff --check`를 실행합니다.
실제 API 서버 스키마 검증과 장애·복구는 별도 kind smoke로 수행합니다. 정적 CI만으로 실행 검증을 대신하지 않습니다.

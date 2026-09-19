# GovBiz-infra

GovBiz의 **환경별 배포 설정과 GitOps 전환 절차를 관리하는 저장소**입니다.
애플리케이션 코드와 로컬 통합 실행은 [GovBiz-web](https://github.com/GovBiz-Team/GovBiz-web) 모노레포에서 관리합니다.
기존 Django Ops 코드는 그 저장소의 `backend/ops/`로 통합하며, 이 저장소에서 애플리케이션 submodule을 관리하지 않습니다.

## 현재 상태와 저장소 경계

| 저장소 | 책임 |
| --- | --- |
| [GovBiz-web](https://github.com/GovBiz-Team/GovBiz-web) | React·Core API·AI Service·Django Ops 코드, 테스트, Dockerfile, 로컬 Compose |
| [GovBiz-infra](https://github.com/GovBiz-Team/GovBiz-infra) | 향후 Kubernetes 환경별 배포 상태, Argo CD 연결 정의, 전환·복구 절차 |
| GovBiz-app — 향후 | React Native 클라이언트; 웹과 동일한 공개 백엔드 계약 사용 |

**현재 Kubernetes manifest, Argo CD Application, 클러스터 연결은 구현하지 않았습니다.**
`argocd/`와 `environments/`에는 책임과 도입 조건을 설명하는 README만 있습니다.
이 구조 정리를 Kubernetes 운영 배포 또는 GitOps 자동 배포 완료로 해석하지 않습니다.

기존 EC2 Compose·CodeBuild·SSM 배포 코드는 당분간 GovBiz-web의 `infrastructure/`에 유지합니다.
현재 AWS·Vercel의 source 연결, 서버 설정, DB, 이미지 버전은 이 작업으로 변경하지 않습니다.
운영 환경은 아직 확정하지 않았으며 먼저 격리된 로컬 Kubernetes에서 검증할 계획입니다.
프론트를 Vercel에 유지하면 해당 프론트 배포는 Argo CD의 관리 대상이 아닙니다.

## 구조

```text
GovBiz-infra/
├─ argocd/
│  └─ README.md               AppProject·Application 도입 조건
├─ environments/
│  └─ README.md               환경별 배포 상태·이미지 pin 관리 기준
├─ docs/
│  ├─ repository-transition.md 이전 개발 환경의 안전한 전환 절차
│  ├─ msa-kubernetes-argocd-plan.md
│  └─ msa-strategy-review-20260919.md
├─ scripts/
│  ├─ check_repository.py     저장소 경계·문서 링크 검증
│  └─ test_check_repository.py
└─ .github/workflows/ci.yml   저장소 경계·문서 검증
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

Ops를 모노레포에 넣는 것은 소스 관리 단위를 합치는 작업입니다.
Django와 Core의 실행 프로세스, 데이터 소유권, 인증 책임을 합치지 않습니다.
Ops는 아직 상태 확인 API와 전용 MySQL을 가진 골격이며, Core 기반 관리자 인증과 실제 운영 업무는 후속 구현입니다.

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

## 다음 단계와 검증

[MSA·Kubernetes·Argo CD 전환 설계](docs/msa-kubernetes-argocd-plan.md)와
[코드 기반 전략 검토](docs/msa-strategy-review-20260919.md)에 단계별 통과 조건을 정리했습니다.

현재 infra CI는 애플리케이션 소스·submodule·로컬 Compose가 되돌아오지 않는지와 문서 경계를 검증합니다.
서비스 테스트와 통합 Compose 검증은 GovBiz-web CI의 책임입니다.
infra CI 통과를 Kubernetes 배포, 관리자 인증, 전체 업무 연동, 실제 RAG 품질 검증으로 표시하지 않습니다.

```bash
python3 -B scripts/check_repository.py
python3 -B -m unittest discover -s scripts -p 'test_*.py'
git diff --check
```

문서만 바뀐 경우 링크·경로를 확인하고 `git diff --check`를 실행합니다.
실제 manifests를 도입하면 렌더링·스키마·정책 검증과 격리 클러스터 동기화·복구 검증을 별도 CI에 추가해야 합니다.

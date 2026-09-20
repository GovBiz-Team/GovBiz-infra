# Argo CD 구성 경계

상태: **로컬용 Application 4개와 AppProject 정의를 구현했다.** `local/`에서
Core·Catalog·AI·Ops의 Helm 배포를 별도로 관리한다. 최초 sync는 수동이며 운영에 연결하지 않는다.
Argo CD Core 3.5.3을 임시 kind에 설치해 원격 Git A → B → A 동기화와 AI만의 Pod 교체·복귀를
검증했다. [실행 기록](../docs/msa-validation-20260920.md)과 [실행 방법](../docs/msa-local.md)을 따른다.
Core 설치는 웹 UI 없이 동기화 엔진을 검증하는 방식이다. 테스트 중에만 자동 동기화를 켰으며,
`local/` Application의 최초 sync는 계속 수동이다. 이 임시 검증은 상시 운영 환경이 아니다.

별도의 `portfolio/`는 Mac에 유지하는 `govbiz-portfolio` 클러스터용이다. 사용자가 승인한
자동 sync/self-heal을 켜고 자동 prune는 끈다. `environments/portfolio`의 GHCR digest를 추적하며
Secret·DB·PVC는 관리하지 않는다. [설치·중지·복구 안내](../docs/portfolio-gitops.md)를 따른다.

## 이 디렉터리에 들어갈 내용

- AppProject: 허용하는 소스 저장소, 대상 클러스터·namespace, 배포 리소스 종류
- Application: 서비스별 환경 경로, 추적할 승인된 revision, 대상 namespace와 동기화 정책
- 로컬 검증 후 운영 연결로 전환하는 부트스트랩·권한·복구 절차

현재 Application은 `../charts/govbiz-service`와 서비스별 `../environments/local-msa/` 값을 읽는다.
대상 namespace는 `govbiz-msa`이며 Deployment·Service만 허용한다. 기존 Ops Kustomize
예제의 `govbiz-local`과 분리하고 Secret·PVC·클러스터 관리 권한을 앱에 주지 않는다.

## 연결 전 통과 조건

1. 대상 로컬 클러스터와 전용 kubeconfig를 확인하고 기존 운영 컨텍스트를 사용하지 않는다.
2. 최소 서비스의 불변 이미지 digest, 상태 확인, 자원 제한, 격리된 검증 데이터를 준비한다.
3. manifests의 렌더링·스키마·정책 검증을 통과하고 읽을 Git 경로·revision을 원격에 확정한다.
4. 최초 AppProject·Application은 검토 후 명시적으로 동기화한다. 자동 동기화·prune·self-heal은 각각 별도 판단한다.
5. 이미지 변경이 지정 서비스에만 적용되는지, 기존 버전 복귀·권한 제한·장애 복구를 확인한다.
6. 운영으로 전환할 때 같은 환경·서비스의 기존 SSM 등 배포 주체를 정리한다. 두 도구가 같은 대상을 갱신하지 않는다.

Argo CD는 Docker 이미지를 빌드하지 않고 GHCR의 최신 태그를 자동으로 선택하지 않는다.
이미지 발행은 앱 CI, portfolio digest 선택은 infra의 주기적 promotion workflow 책임이다.
다른 운영 환경은 별도로 승인하며 portfolio 자동 커밋이 임의 환경까지 갱신하지 않는다.
프론트를 Vercel에 유지한다면 해당 배포는 이 디렉터리의 관리 대상이 아니다.

Git 저장소 읽기 자격 증명과 GHCR 이미지 공개 범위·pull 권한은 별개다. 실제 토큰·비밀번호·kubeconfig는 이 저장소에 넣지 않는다.

관련 문서: [전체 전환 설계](../docs/msa-kubernetes-argocd-plan.md), [환경별 설정 기준](../environments/README.md)

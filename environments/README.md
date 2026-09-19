# 환경별 배포 상태

상태: **로컬 Ops Kubernetes 설정을 구현한 단계다.** `services/operations-api/base`와
`local/operations-api`, `local/ops-mysql`은 격리된 kind 검증용이다.
운영 클러스터·ECR 릴리스 digest·`prod` overlay는 아직 없으며 EKS를 생성하지 않는다.

애플리케이션 코드·Dockerfile·테스트·로컬 Compose는 GovBiz에서 관리한다.
향후 이 디렉터리는 승인된 각 환경의 원하는 실행 상태를 관리한다.

## 배포 설정에 기록할 것

| 항목 | 기준 |
| --- | --- |
| 이미지 | 서비스별 ECR 저장소와 불변 digest; 변경되지 않은 서비스 버전은 유지 |
| 추적 정보 | 서비스 소스 SHA·이미지 digest·설정 revision의 대응 관계 |
| 실행 설정 | replica, CPU·메모리, startup/readiness/liveness, 종료 유예 |
| 네트워크 | 내부 Service, 외부 라우팅·TLS, 접근 정책 |
| 비밀·데이터 | 비밀 저장소 참조, 소유 DB·스토리지·백업 정책; 실제 비밀값은 제외 |
| 복구 조건 | 이전 승인 digest, API·DB migration 호환성, 데이터 복구 제한 |

첫 단계는 격리된 로컬 Kubernetes에서 Ops를 검증하는 것이다.
Kustomize base/overlay를 사용하며 DB 설정은 로컬 검증에만 둔다.
local의 `govbiz-ops:local-k8s`는 registry에서 다운로드하는 운영 릴리스가 아니라,
smoke가 검증한 로컬 고유 이미지 태그로 교체하고 kind에 적재하는 자리다.
운영에서는 위 표처럼 승인된 digest를 기록해야 하며 로컬 태그를 그대로 복사하지 않는다.
개발 환경과 운영 환경을 이름만 다르게 복사하거나 임의의 도메인·계정·클러스터 값을 넣지 않는다.

## 변경 흐름과 안전장치

1. GovBiz의 CI가 검증된 이미지를 발행한다.
2. 해당 서비스의 환경별 digest만 바꾸는 infra PR을 만든다.
3. 구성 검증과 API·migration 호환성 검토 후 병합한다.
4. Argo CD가 승인된 설정을 Kubernetes에 동기화한다. 자동 동기화 여부는 환경별 정책으로 정한다.

`latest` 태그 갱신이나 submodule 커밋 갱신을 배포 버전 관리로 대신하지 않는다.
이미지 되돌리기는 DB 데이터 되돌리기가 아니며, 파괴적 migration은 별도 승인·복구 절차가 필요하다.
같은 환경·서비스를 수동 명령, SSM, Argo CD가 경쟁해서 변경하는 다중 배포 주체를 만들지 않는다.

현재 EC2 운영 Compose·CodeBuild·SSM 설정은 GovBiz의 `infrastructure/`에 그대로 둔다.
새 Kubernetes 경로의 검증과 운영 전환을 승인하기 전에는 이를 대체하거나 자동 실행하지 않는다.

관련 문서: [로컬 검증](../docs/kubernetes-local.md), [Argo CD 도입 조건](../argocd/README.md), [전환 설계](../docs/msa-kubernetes-argocd-plan.md)

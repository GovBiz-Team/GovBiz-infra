# 환경별 배포 상태

상태: **관리 기준만 정의한 단계다.** 현재 적용 가능한 Kubernetes manifest, 이미지 버전 목록,
운영 클러스터 주소는 없다. `prod` 환경이나 EKS가 확정됐다고 가정하지 않는다.

애플리케이션 코드·Dockerfile·테스트·로컬 Compose는 GovBiz-web에서 관리한다.
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

첫 단계는 격리된 로컬 Kubernetes에서 최소 서비스를 검증하는 것이다.
Kustomize base/overlay를 우선 검토하되 실제 서비스·환경을 확정한 뒤 필요한 파일만 추가한다.
개발 환경과 운영 환경을 이름만 다르게 복사하거나 임의의 도메인·계정·클러스터 값을 넣지 않는다.

## 변경 흐름과 안전장치

1. GovBiz-web의 CI가 검증된 이미지를 발행한다.
2. 해당 서비스의 환경별 digest만 바꾸는 infra PR을 만든다.
3. 구성 검증과 API·migration 호환성 검토 후 병합한다.
4. Argo CD가 승인된 설정을 Kubernetes에 동기화한다. 자동 동기화 여부는 환경별 정책으로 정한다.

`latest` 태그 갱신이나 submodule 커밋 갱신을 배포 버전 관리로 대신하지 않는다.
이미지 되돌리기는 DB 데이터 되돌리기가 아니며, 파괴적 migration은 별도 승인·복구 절차가 필요하다.
같은 환경·서비스를 수동 명령, SSM, Argo CD가 경쟁해서 변경하는 다중 배포 주체를 만들지 않는다.

현재 EC2 운영 Compose·CodeBuild·SSM 설정은 GovBiz-web의 `infrastructure/`에 그대로 둔다.
새 Kubernetes 경로의 검증과 운영 전환을 승인하기 전에는 이를 대체하거나 자동 실행하지 않는다.

관련 문서: [Argo CD 도입 조건](../argocd/README.md), [전환 설계](../docs/msa-kubernetes-argocd-plan.md)

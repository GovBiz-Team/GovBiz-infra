# Argo CD 구성 경계

상태: **도입 준비 문서만 존재한다.** 아직 Application·AppProject manifest, 저장소 자격 증명,
클러스터 연결, Argo CD 설치·동기화는 없다. 이 디렉터리를 현재 동작하는 배포 경로로 지정하지 않는다.

## 이 디렉터리에 들어갈 내용

- AppProject: 허용하는 소스 저장소, 대상 클러스터·namespace, 배포 리소스 종류
- Application: 서비스별 환경 경로, 추적할 승인된 revision, 대상 namespace와 동기화 정책
- 로컬 검증 후 운영 연결로 전환하는 부트스트랩·권한·복구 절차

실제 서비스 Deployment·Service 등의 원하는 실행 상태는 `../environments/`에서 관리한다.
현재 로컬 검증 대상과 Kubernetes 리소스명은 모두 `ops-service`다.
첫 Application의 대상 경로는 현재 존재하는 overlay와 대조해 확정하며, Argo CD 설정 파일은
권한·동기화 범위를 확정한 뒤 만든다. 빈 설정을 유효한 manifest로 꾸미지 않는다.

## 연결 전 통과 조건

1. 대상 로컬 클러스터와 전용 kubeconfig를 확인하고 기존 운영 컨텍스트를 사용하지 않는다.
2. 최소 서비스의 불변 이미지 digest, 상태 확인, 자원 제한, 격리된 검증 데이터를 준비한다.
3. manifests의 렌더링·스키마·정책 검증을 통과하고 읽을 Git 경로·revision을 원격에 확정한다.
4. 최초 AppProject·Application은 검토 후 명시적으로 동기화한다. 자동 동기화·prune·self-heal은 각각 별도 판단한다.
5. 이미지 변경이 지정 서비스에만 적용되는지, 기존 버전 복귀·권한 제한·장애 복구를 확인한다.
6. 운영으로 전환할 때 같은 환경·서비스의 기존 SSM 등 배포 주체를 정리한다. 두 도구가 같은 대상을 갱신하지 않는다.

Argo CD는 Docker 이미지를 빌드하지 않고 ECR의 최신 태그를 자동으로 선택하지 않는다.
이미지 발행과 환경별 digest 변경 PR은 애플리케이션 릴리스 CI의 후속 책임이다.
프론트를 Vercel에 유지한다면 해당 배포는 이 디렉터리의 관리 대상이 아니다.

Git 저장소 읽기 자격 증명과 ECR pull 권한은 별개다. 실제 토큰·비밀번호·kubeconfig는 이 저장소에 넣지 않는다.

관련 문서: [전체 전환 설계](../docs/msa-kubernetes-argocd-plan.md), [환경별 설정 기준](../environments/README.md)

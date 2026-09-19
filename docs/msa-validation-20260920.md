# 네 서비스 로컬 MSA 검증 — 2026-09-20

범위는 로컬 Compose와 임시 kind 클러스터다. AWS·실제 환경 파일·기존 데이터 볼륨·유료 API는
사용하지 않았다. 기존 GovBiz 개발 컨테이너만 사용자 승인으로 중지했으며 검증 종료 시 복구한다.

## 도구와 이미지

- Kubernetes 1.36.4, kind 0.33.0, Helm 4.3.0, MySQL 8.4.
- 새 클러스터: `govbiz-msa-smoke-65bae80ef6`. 개인 kubeconfig와 다른 별도 임시 kubeconfig 사용.
- 앱 이미지 태그: `msa-20260920-001`. GovBiz `8b2644b3f6d29184180c972adb9dbe1b2fce05ab`
  기반 작업 트리에서 빌드했다(`dirty=true`). 이번 변경은 Compose·검증 도구·문서이며 서비스 업무 코드는 변경하지 않았다.
- 원격 이미지 업로드 없음. 공공 제공처와 OpenAI는 로컬 HTTP 스텁으로 대체했다.

## 통과한 검증

| 범위 | 결과 |
| --- | --- |
| Core | JDK 21 `clean build`, 1,512개 테스트 통과·건너뜀 없음 |
| Catalog | JDK 21 `clean build`, 286개 테스트 통과·건너뜀 없음 |
| AI | `uv run --locked --extra dev python -m pytest`, 실제 임시 Qdrant를 포함한 1,345개 통과 |
| 앱 검증 도구 | 87개 중 71개 통과, 별도 opt-in 데모 DB 검증 16개 미실행 |
| Infra | 50개 단위 테스트, 네 서비스·로컬 저장소 Helm strict lint, Kustomize·구성·문서 링크 검사 통과 |
| Compose 실제 연동 | 네 제공처 snapshot·checkpoint, DB 분리, 실제 색인과 스텁 임베딩 검색, 제공처 실패·Catalog 중단 시 Core 데이터와 검색 보존 |
| Kubernetes admission·기동 | 서버 strict dry-run, Core·Catalog·AI·Ops 및 MySQL 3개·ES·Qdrant·Redis 정상 준비 |
| 내부 계약·데이터 경계 | 토큰 누락/불일치 401, 4개 제공처 공고 42개 HTTP 복제, Core DB 계정의 Catalog DB 접근 1045 거절 |
| 독립 설정 배포 | AI 설정만 변경·복귀할 때 Core·Catalog·Ops Pod UID 유지 |
| 장애 격리 | Catalog 중단 동안 Core 공고 데이터와 공개 조회 유지, 이후 Catalog 복구 |
| 데이터 복구 | Ops의 임시 한글 테스트 테이블 dump·삭제·복원, DB Pod 교체 후 PVC 데이터 유지 |

첫 Compose 실행은 콜드 MySQL 초기화가 개발용 healthcheck 예산을 넘어 실패했다.
DB 자체는 정상 준비됨을 확인한 뒤, **임시 검증 overlay만** CLI timeout에 맞춰 대기하도록 수정하고
전체 Compose 시나리오를 다시 실행해 통과했다. 실제 개발·운영 healthcheck 값을 완화하지 않았다.
Kubernetes Qdrant는 non-root 실행에 맞게 스냅샷 경로를 자신의 PVC 안으로 지정했다.

## GitOps 상태

로컬 실행 검증 통과 후 커밋·푸시한 Git revision으로 Argo CD Core 검증을 이어 진행한다.
이 문서의 현재 단계에서는 Git 동기화 성공을 아직 주장하지 않는다.
검증 방식은 [실행 안내](msa-local.md#gitops-연결-경계)를 따른다.

## 해석 제한

- AI 롤아웃은 **환경 설정 변경**이며 새 AI 코드·이미지 버전 검증이 아니다.
- Ops 데이터 복원은 새 테스트 테이블에 한정한다. 운영 전체 DB 백업·PITR 검증이 아니다.
- 모든 내부 API 인증·NetworkPolicy 집행, Core·AI 의존성 readiness, 부하/HPA와 무중단 배포는 미검증이다.
- Ops 관리자 인증·LLMOps 업무, 이미지 발행 CI·ECR·상시 클러스터 자동 배포, AWS 운영은 미구현이다.
- 스텁 테스트를 실제 공공 API 연동·유료 AI 품질 평가로 해석하지 않는다.
- replicas=1·Recreate 정책은 writer 중복을 피하기 위한 초기 제약이며 짧은 중단을 허용한다.

# 로컬 Kubernetes 검증 기록 — 2026-09-19

> 이 문서의 Core API/Core, Catalog, AI Service/AI, Ops는 당시 표기입니다. 현재 서비스명은 각각
> `core-service`, `catalog-service`, `ai-service`, `ops-service`입니다. 본문의 검증 수치·이미지 태그·
> 커밋 고정 경로는 당시 기록을 보존하며, 최신 구성은 [메인 README](../README.md)를 따릅니다.

## 판정과 범위

**Ops + 전용 검증 MySQL의 로컬 Kubernetes 실행·장애·복구 검증을 통과했다.**
AWS 운영 서버는 기존 EC2 Compose 그대로이며, Core·AI의 Kubernetes 이전이나
Argo CD GitOps·관리자 인증·업무 서비스 추출 완료를 의미하지 않는다.

실행 방법은 [로컬 Kubernetes 안내](kubernetes-local.md), 데이터·인증 계약은
[서비스 경계](service-boundaries.md)를 따른다. 이 문서는 실시간 운영 상태가 아닌 일회성 검증 기록이다.

## 기준

- GovBiz-web 기준 커밋 `238510748e93ff6d32575ff7e7bb2315c4f251cb`에 이번 Gunicorn 작업 변경을 더한 이미지.
- GovBiz-infra 기준 커밋 `1e285163eb0d17ffeba3b7237b124970f516ca3f`에 이번 manifests·도구 변경을 더한 작업 트리.
- 검증 시점에는 이번 변경을 커밋·푸시하지 않았다. 원격 CI·운영 배포 성공으로 표시하지 않는다.
- Docker 29.6.2, Linux/amd64 엔진, kind 0.33.0, Kubernetes 서버 1.36.4.
- 호스트 kubectl 1.36.1 / Kustomize 5.8.1. CI는 kubectl 1.36.4를 지정하였으나 원격 CI 실행은 미검증이다.
- 테스트 클러스터 `govbiz-k8s-smoke-d979c5bbf7`, namespace `govbiz-local`.
- Ops 로컬 태그 `govbiz-ops:k8s-b029fc07664b`.
- Docker 로컬 이미지 ID: `sha256:b029fc07664b549d25fe8d5dc70290c189f2b705ee17d19ac027ddeb53e6040a`.
- 실행한 플랫폼 이미지 ID: `docker.io/library/import-2026-09-19@sha256:d2820b2403de1a3c186b62156ef71d73c16b98710f068ad982886be6bb591832`.
- MySQL: `mysql:8.4@sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb`.

Docker의 다중 플랫폼 index ID와 단일 플랫폼 실행 ID는 다르다. ECR에 이미지를 발행한 기록이 아니다.
실제 환경 파일·API 키·운영 데이터·기존 Kubernetes 컨텍스트는 사용하지 않았다.

## 결과

| 검증 | 결과 |
| --- | --- |
| Ops lock/sync/pip check, Ruff lint/format | 통과 |
| Django 설정·migration 변경 검사 | 문제 없음, 변경 없음 |
| MySQL 8.4 기반 Ops 전체 테스트 | 5개 통과 |
| 기존 로컬 통합 Compose Ops 검증 | 환경·볼륨 격리, HTTP, Service DNS 통과 |
| Gunicorn 이미지 | UID 10001, read-only root, tmpfs, health200, DB 미연결503, Host 거절400, SIGTERM exit0 |
| infra 정적·도구 테스트 | 35개 통과: 저장소 4 + manifests 정책 16 + smoke helper 15 |
| Kustomize 렌더링·안전 정책 | 통과 |
| Kubernetes API 서버 strict dry-run | Namespace·ConfigMap·Service·StatefulSet·Deployment 통과 |
| 실제 Ops→MySQL | Service DNS와 DB readiness200 |
| DB 장애 | readiness503·Pod NotReady, liveness200, 관찰 구간 앱 재시작 없음 |
| DB Pod 복구 | 다른 Pod UID로 재생성, PVC 검증 행 유지, readiness 복구 |
| Ops Pod 삭제 | Deployment가 새 UID의 Pod를 생성, readiness 복구 |
| 잘못된 이미지 rollout | 의도한 timeout 발생, 기존 healthy replica와 readiness 유지 |
| 이전 이미지 복귀 | rollout undo 후 원래 이미지·readiness 복구 |

최종 명령:

```bash
python -B scripts/smoke_kubernetes.py \
  --kind /검증한/kind \
  --image govbiz-ops:k8s-b029fc07664b
```

최종 프로세스 exit code는 `0`이며 `GOVBIZ_KUBERNETES_LOCAL_OK`를 출력했다.
중간의 `timed out waiting for the condition`은 없는 이미지의 배포 실패를 의도적으로 검사한 결과다.
`rollout undo`의 last-applied annotation 경고도 발생했다. 이 실험은 이후 apply를 하지 않고
클러스터를 제거하며, 실제 GitOps에서는 Git의 배포 설정을 되돌려 상태를 일치시켜야 한다.
PVC 행 보존은 백업·복원이나 DB migration rollback 검증이 아니다.

## 발견한 문제와 수정

1. Docker Desktop OCI index의 미적재 플랫폼/attestation 때문에 kind 전체 플랫폼 import 실패.
   Docker 호스트와 동일한 플랫폼만 `docker image save --platform`으로 내보내어 해결했다.
2. 임시 Kustomize overlay가 절대 경로 base를 참조해 거절됨.
   정식 local overlay를 먼저 렌더링하고, 메모리에서 Ops 이미지 한 항목만 바꾸는 방식으로 수정했다.
   다른 설정을 변경하지 않는지와 잘못된 이미지 대상 거절을 단위 테스트에 추가했다.
3. 실패한 첫 두 검증의 임시 클러스터도 정리한 뒤, 수정된 코드로 처음부터 전체 smoke를 다시 통과했다.

## 정리와 미검증 항목

검증 후 해당 임시 클러스터와 생성한 Secret/PVC/DB 검증 행, port-forward, 임시 kubeconfig를 정리했다.
기존 Docker 개발 컨테이너·볼륨, AWS 서버·RDS, Vercel 설정은 바꾸지 않았다.
검증 도구·Docker 이미지·빌드 캐시는 남을 수 있으며 전역 삭제는 하지 않았다.

Frontend·Core·AI 코드와 해당 운영 배포 설정은 변경하지 않아 전체 앱 테스트는 재실행하지 않았다.
이번에 바뀐 Ops 테스트·컨테이너 경로는 모두 위 범위로 검증했다.
미검증: NetworkPolicy 집행, HA·부하/HPA, 장기 장애, 백업 복원, 관리자 인증,
Core·AI 전체 연동, 유료 LLM/RAG 품질, GitOps 동기화, AWS 운영 전환.

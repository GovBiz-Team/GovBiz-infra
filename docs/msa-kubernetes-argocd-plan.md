# GovBiz MSA·Kubernetes·Argo CD 전환 설계

이 문서는 현재 코드를 확인한 **전환 제안**이다. Kubernetes 리소스, Argo CD 연결, 서비스 분리는 아직 구현하지 않았다.
사용자 결정: **우선 로컬 Kubernetes에서 검증하고 운영 환경은 나중에 결정한다.** EKS 또는 EC2 운영을 현재 전제로 확정하지 않는다.

## 1. 확인한 현재 상태

분석 기준: GovBiz-infra `58c65aa`, 3차 서비스 `3489756`, 4차 서비스 `611232d`.

| 영역 | 현재 구현 | 전환 시 의미 |
| --- | --- | --- |
| 통합 실행 | 루트 Compose가 두 저장소를 submodule로 연결 | 서비스 저장소와 PR을 계속 독립적으로 유지할 수 있다 |
| Spring Core | 계정, 공고, 신청 준비, 중복 검토, 파트너, 리포트, 관리자 기능 | 업무별 직접 호출과 데이터 의존 관계를 풀어야 서비스가 독립된다 |
| FastAPI | 조건 해석, 검색·색인·근거 답변, 문서 분석, 도우미 | 독립 배포를 유지하고 기능별 부하·장애를 확인한 뒤 추가 분리한다 |
| Django | 상태 확인 API, 전용 MySQL, 개발용 runserver | 운영 서버와 인증 연동, 실제 운영 관리 업무 구현이 필요하다 |
| AWS 배포 코드 | CodeBuild 검증·이미지 빌드 → ECR → SSM → EC2 Compose | 이미지 빌드는 CI에, Kubernetes 배포는 Argo CD에 맡긴다 |
| 운영 DB 설정 | 운영 Compose의 Core는 RDS에 연결 | Kubernetes 도입만을 이유로 DB를 클러스터 안으로 옮기지 않는다 |

확인한 파일:
- [통합 Compose](../compose.yaml), [Django 연결](../compose.django.yaml)
- [운영 Compose](../services/SKN34-3rd-1Team/infrastructure/compose.prod.yaml)
- [CodeBuild 설정](../services/SKN34-3rd-1Team/infrastructure/codebuild/backend.yml), [릴리스 실행](../services/SKN34-3rd-1Team/infrastructure/codebuild/release.py)
- [Django Dockerfile](../services/SKN34-4th-1Team/Dockerfile), [Django 설정](../services/SKN34-4th-1Team/config/settings.py)

Kubernetes는 컨테이너의 실행·복구·확장을 관리하고, Argo CD는 Git에 기록된 배포 설정을 클러스터에 반영한다.
MSA 전환은 별도로 업무 책임, 데이터 소유권, 공개 API·이벤트 계약, 독립 배포를 만드는 작업이다.
현재 Core를 그대로 여러 Pod로 실행하는 단계는 배포 환경 이전이며 업무 서비스 분리가 완료된 상태는 아니다.

## 2. 서비스 경계와 분리 순서

아래 이름은 제안이며 새 저장소나 애플리케이션을 만든 상태가 아니다.

| 배포 단위 | 담당할 책임 | 진행 방식 |
| --- | --- | --- |
| core-api | 계정·기업·세션과 아직 분리하지 않은 사용자 업무 | 초기에는 기존 기능 유지; 추출된 기능은 API·이벤트로 연동 |
| operations-api | Django 기반 운영 관리·검토 업무와 자체 운영 기록 | 4차 저장소에서 구현; 기존 Core 관리자 API는 필요한 범위에서 재사용 |
| ai-service | LLM·임베딩·RAG·문서 분석 실행 | 기존 FastAPI 유지; 외부 사용자에게 내부 API를 직접 공개하지 않음 |
| catalog-service | 공고 수집·정규화·조회·검색 흐름과 공고 데이터 | 첫 Core 분리 후보; 기존 Spring 구현을 기반으로 경계 분리 |
| application-service | 신청 준비·문서 작업·중복 지원 검토와 작업 상태 | 공고·계정 계약 정리 후 분리 후보 |
| 도메인별 worker | 해당 서비스의 큐 소비·수집·장기 작업 | 처리량과 실행 조건에 맞춰 API와 별도 프로세스로 운영 |

워커 프로세스 분리는 같은 업무 서비스의 실행 역할을 나누는 작업이다. 워커 수를 MSA 서비스 수로 계산하지 않는다.
리포트·파트너·계정을 처음부터 모두 별도 서버로 만들지는 않는다. 실제 변경 주기와 장애·확장 요구로 후속 분리를 결정한다.
분리한 Spring 애플리케이션들을 기존 3차 저장소 안에서 각각 빌드해도 된다. MSA 서비스마다 Git 저장소가 반드시 하나씩 필요한 것은 아니다.

현재 코드에는 `account ↔ partner`, `supportprogram ↔ applicationpreparation`의 기능 간 import가 있다.
신청 준비·중복 검토·리포트도 계정과 공고 코드를 사용한다.
따라서 폴더 복사만으로 분리하지 않고, 공개 조회·명령 계약과 필요한 데이터 스냅샷부터 정한다.
공고 소유 데이터와 개인 관심 공고·신청 상태는 서로 다른 책임이므로 `supportprogram` 폴더 전체를 하나의 서비스로 간주하지 않는다.

## 3. 데이터와 인증 경계

- 서비스마다 소유 테이블·스키마와 DB 계정을 정하고 다른 서비스의 테이블을 직접 수정하지 않는다.
- 초기에는 하나의 RDS 인스턴스 안에서 스키마·계정을 분리할 수 있다. 물리 DB 인스턴스 분리와 데이터 소유권 분리를 구분한다.
- 다른 서비스의 정보는 내부 API 또는 필요한 필드만 유지하는 이벤트 기반 조회 모델로 전달한다.
- 데이터 이전은 소유권 목록, 백필, 검증, 쓰기 주체 전환, 복구 절차를 포함한다. 애플리케이션 배포와 동시에 무계획하게 DB를 분할하지 않는다.
- 계정·권한의 기준은 현재 Core에 유지한다. Django에 별도의 일반 사용자 인증 체계를 중복 구현하지 않는다.
- 현재 `govbiz_session`은 HttpOnly·SameSite=Lax·호스트 한정 쿠키다. 외부 주소를 나눌 때 로그인·로그아웃·CSRF와 Django 권한 검사를 함께 설계한다.
- 내부 API 호출자의 인증과 사용자 권한 전달을 명시한다. Kubernetes 내부 네트워크에 있다는 사실만으로 관리 API 접근을 허용하지 않는다.
- RabbitMQ 이벤트에는 식별자·버전과 재처리 규칙을 두고, DB 기록과 발행의 일관성 및 중복 소비 방지를 검증한다.

## 4. GovBiz-infra의 목표 구조

기존 서비스 저장소와 개발용 Compose는 유지하고 운영 배포 설정을 추가한다.
아래는 제안 구조이며 아직 존재하지 않는 디렉터리를 포함한다.

```text
GovBiz-infra/
├─ compose.yaml                    로컬 개발용
├─ compose.django.yaml
├─ services/                       개발·통합 검증용 submodule
│  ├─ SKN34-3rd-1Team/
│  └─ SKN34-4th-1Team/
├─ kubernetes/
│  ├─ services/
│  │  ├─ core-api/
│  │  │  ├─ base/
│  │  │  └─ overlays/{local,prod}/
│  │  ├─ ai-service/               같은 방식으로 서비스별 구성
│  │  └─ operations-api/
│  └─ platform/                    공통 라우팅·네트워크·관측 설정
├─ argocd/
│  ├─ projects/                    저장소·namespace·리소스 권한 범위
│  └─ applications/{local,prod}/   서비스별 배포 경로 연결
└─ docs/
```

처음에는 Kustomize의 base/overlay로 환경 차이를 관리한다. 서비스별 Argo CD Application으로 독립 배포와 상태 확인이 가능하게 한다.
운영 Pod에는 submodule 소스를 마운트하지 않는다. 서비스 CI가 만든 불변 이미지 digest를 배포 설정에 기록한다.
submodule 커밋은 개발·통합 검증 버전이고, Kubernetes 이미지 digest는 배포 버전이다. 릴리스 PR에 이미지와 소스 커밋의 대응 관계를 남긴다.
앱 이미지는 서로 독립적으로 갱신하되, 공개 계약 변경 시 소비자 호환성을 검증한다.

현재 프론트엔드 배포를 Kubernetes로 반드시 옮길 필요는 없다. 외부 웹 호스팅을 유지하면서 백엔드만 전환할 수도 있다.
React Native 앱 바이너리는 모바일 배포 대상으로 관리하며 Kubernetes에서 실행하지 않는다.

## 5. CI와 Argo CD의 역할

```mermaid
flowchart LR
    A["서비스 저장소 PR·병합"] --> B["CI: 테스트·이미지 빌드"]
    B --> C["ECR: 불변 이미지"]
    C --> D["GovBiz-infra PR: 이미지 digest 갱신"]
    D --> E["환경별 배포 설정에 병합"]
    E --> F["Argo CD: Git 상태 동기화"]
    F --> G["Kubernetes: 서비스 실행·복구"]
```

- 기존 GitHub Actions 검증과 CodeBuild 빌드 경로를 확인해 역할을 분담한다. 같은 릴리스를 두 CI가 동시에 배포하지 않는다.
- Argo CD는 소스 코드 테스트나 Docker 이미지 빌드를 대신하지 않는다.
- 개발 환경은 검증 후 자동 동기화, 운영은 초기에는 PR 검토와 수동 동기화를 기본 제안으로 둔다.
- 클러스터와 Argo CD 자체의 최초 설치·접근 설정은 별도 부트스트랩 단계다.
- 비공개 infra 저장소의 읽기 자격 증명과 ECR 이미지 읽기 권한은 별도로 구성한다.
- 비밀값은 평문 또는 단순 base64 Secret으로 Git에 커밋하지 않는다. 운영 환경 확정 후 비밀 저장소와 주입 방식을 선택한다.
- 이전 이미지로 되돌릴 때도 Git의 배포 설정을 변경한다. DB migration 호환성과 데이터 복구는 이미지 되돌리기와 별도로 확인한다.
- SSM 기반 기존 Compose 배포는 전환 검증과 트래픽 전환 후 해당 대상으로 가는 자동 실행을 정리한다.

## 6. Pod 확장 전에 해결할 항목

1. **수집·색인 실행 역할:** 현재 Core의 `@Scheduled`는 각 프로세스에서 실행된다. 세대별 스냅샷 공개 보호가 있어도 외부 수집·색인 호출 자체의 중복 방지를 뜻하지 않는다. 전용 실행 역할과 작업 단위 중복 방지를 확인하기 전에는 replicas만 늘리지 않는다.
2. **큐 소비·종료:** DB 작업 선점, 중복 배달, ACK, DLQ, 실행 중 Pod 종료와 재기동을 검증한다. 재시도 때문에 동일 유료 AI 작업을 반복하지 않도록 기존 기록·재실행 정책을 보존한다.
3. **요청·예산 제한:** 프로세스 메모리의 동시 실행 제한·캐시가 여러 Pod에서 어떤 의미를 가지는지 확인한다. 기존 Redis·DB 기반 정책과 함께 검토한다.
4. **운영 이미지:** Django runserver를 운영 WSGI/ASGI 실행으로 교체하고 서비스 저장소에서 테스트·빌드한다. 개발 소스 bind mount와 개발 서버를 운영 설정에 가져오지 않는다.
5. **상태 확인과 자원:** startup/readiness/liveness를 구분하고, 외부 AI 장애로 무한 재시작하지 않도록 설계한다. 요청 시간·종료 유예·메모리·CPU를 실제 부하에 맞춰 정한다.
6. **상태 저장소:** RDS는 우선 기존 연결을 유지한다. Elasticsearch·Qdrant·RabbitMQ·Redis는 백업·복구·PVC와 운영 주체를 먼저 정한다. 모든 DB를 단순히 Pod 하나씩으로 변환하지 않는다.
7. **추적:** 서비스 간 request/job ID, 오류율, 지연, 큐 적체를 관측한다. Kubernetes 로그 수집과 Argo CD의 배포 상태만으로 업무 처리 성공을 판단하지 않는다.

## 7. 실행 단계와 완료 기준

| 단계 | 작업 | 완료 기준 |
| --- | --- | --- |
| 1 | 서비스 책임·테이블 소유권·인증 계약 정의 | 분리 대상마다 읽기·쓰기 경계와 호환 API가 문서화됨 |
| 2 | 기존 Core·AI와 Django의 운영 실행 준비 | 이미지 빌드·필수 테스트, 상태 확인·종료 동작 검증 |
| 3 | 개발 Kubernetes에 기존 배포 단위 이식 | 격리 데이터로 서비스 통신·장애·재시작 검증; 아직 MSA 완료로 표시하지 않음 |
| 4 | Argo CD 연결 | infra PR의 이미지 변경이 지정 서비스에만 반영되고 이전 버전 복귀 검증 |
| 5 | Django 운영 업무 구현, 공고 서비스 등 순차 추출 | 다른 서비스 DB 직접 접근 없이 해당 서비스만 배포·테스트 가능 |
| 6 | 운영 전환 | 데이터 복구 연습·권한·동시성 검증 후 트래픽 전환, 기존 자동 배포 경로 정리 |

유료 AI 평가는 승인된 전송 데이터와 호출 예산 안에서만 수행한다. 무료 스텁 통합 검증과 실제 RAG 품질 검증은 결과를 구분한다.
이번 설계 작성에서는 서버 접속, 클러스터 생성, 운영 데이터 이동, 외부 AI 호출을 수행하지 않았다.

## 8. 로컬 우선 검증 계획

로컬 Kubernetes는 Docker 위에 별도 클러스터를 만드는 kind를 우선 제안한다.
기존 Compose 개발 환경의 코드·볼륨을 유지하며, Kubernetes 검증에는 별도 namespace와 검증 데이터를 사용한다.

1. `govbiz-local` 이름의 kind 클러스터와 전용 kubeconfig를 준비한다. 기존 Kubernetes 컨텍스트를 암묵적으로 사용하지 않는다.
2. 첫 검증은 Django와 전용 검증 MySQL로 배포·DNS·상태 확인·Pod 재생성을 확인한다.
3. 같은 이미지로 수행한 로컬 배포 검증 이후 Argo CD의 AppProject와 서비스 Application을 연결한다.
4. Argo CD에서 읽을 manifests가 원격 infra 브랜치에 있어야 한다. 로컬 파일 적용만으로 GitOps 자동 동기화 검증 완료라고 표시하지 않는다.
5. Git의 이미지 버전 변경 → Argo CD 동기화 → 배포 상태 확인 → 이전 버전 복귀를 검증한다.
6. 이어서 Core·AI와 검색 저장소를 격리 데이터·외부 API 스텁으로 검증한다. 전체 서비스 동시 실행 전에 자원을 다시 확인한다.

현재 PC에서 Docker와 kubectl 명령을 확인했다. kind·helm·argocd 명령은 PATH에서 발견되지 않았다.
Docker 엔진에 할당된 메모리는 약 7.6 GiB이며, 이는 여유 메모리 측정값이 아니다.
기존 전체 Compose와 Kubernetes 전체 스택을 동시에 충분히 실행할 수 있다고 가정하지 않는다.
이 문서 작성 중 도구 설치나 로컬 클러스터 생성은 수행하지 않았다.

## 9. 운영 이전에 확정할 환경

- 실제 운영 대상: EKS 또는 EC2 직접 운영 등
- 도메인·TLS·라우팅 방식, 외부 웹 호스팅 유지 여부
- 기존 ECR·RDS와 클러스터의 네트워크·IAM 연결
- 상태 저장소의 운영 위치·스토리지·백업, 비밀값 주입 방식
- 최초 업무 분리 범위와 Django 운영 관리 기능의 구체적인 요구

## 참고

- [Argo CD: 소스와 배포 설정 저장소 분리](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [Argo CD: CI와 연동](https://argo-cd.readthedocs.io/en/stable/user-guide/ci_automation/)
- [kind: 로컬 클러스터와 이미지 적재](https://kind.sigs.k8s.io/docs/user/quick-start/)
- [Kubernetes: Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [서비스별 데이터 소유권](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/data-considerations)

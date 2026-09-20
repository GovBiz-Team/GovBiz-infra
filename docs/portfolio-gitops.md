# Mac에 유지하는 비공개 GHCR · Kubernetes · Argo CD

AWS/EKS 대신 사용자 Mac의 Docker Desktop에 `govbiz-portfolio` kind 클러스터를 유지한다.
Mac이 잠들거나 Docker가 종료되면 배포도 중단되고, 다시 켜면 Argo CD가 Git의 현재 상태를 확인한다.
전용 kind 노드에는 `unless-stopped` 재시작 정책을 설정한다. 직접 중지했다면 `docker start`로 재개한다.
클라우드 운영·고가용성·공개 서비스가 아니라 포트폴리오용 배포 환경이다.
기존 Compose와 데이터는 옮기지 않는다. 메모리 때문에 기존 GovBiz Compose는 중지하고 번갈아 사용한다.

## 자동 배포 경로

1. GovBiz `develop`의 동일 SHA에서 세 CI 통과 → 비공개 GHCR 네 이미지 발행/재사용.
2. 이 저장소의 `Portfolio image promotion`이 10분 주기로 성공한 발행과 artifact를 조회한다.
3. workflow·저장소·브랜치·최신 CI·artifact SHA-256·서비스별 Git tree/입력 키를 검증한다.
4. `environments/portfolio`의 변경된 digest와 `release.json`만 한국어 커밋으로 `develop`에 push한다.
5. Mac Argo CD Core가 `develop`을 확인하고 변경된 서비스 Deployment만 조정한다.
6. Kubernetes는 `ghcr-pull` 읽기 전용 Secret으로 비공개 이미지를 실제로 내려받는다.

일정 실행은 GitHub 사정에 따라 지연될 수 있고, 공개 저장소의 장기 비활동 시 중지될 수 있다.
Argo 확인 주기는 120초 + 최대 30초 jitter다. PR 병합 직후 즉시 배포를 보장하지 않는다.
기본 브랜치를 바꾸면 schedule과 develop 제한을 함께 재검토한다.

| 권한/스위치 | 용도 |
| --- | --- |
| GovBiz `MSA_RELEASE_ENABLED=true` | 성공 CI 후 비공개 이미지 발행 |
| GovBiz-infra `MSA_PROMOTION_ENABLED=true` | portfolio digest 자동 반영 |
| GovBiz Actions `packages: write` | 자신의 네 이미지 발행, 임시 GITHUB_TOKEN |
| Infra Actions `contents: write`, `actions: read` | 공개 앱 저장소의 검증 결과 읽기와 자기 저장소만 갱신 |
| Mac classic PAT `read:packages`만 | 비공개 GHCR pull, 쓰기·삭제·repo 권한 없음 |

별도 cross-repository 쓰기 PAT나 AWS 키를 사용하지 않는다. receipt는 서명된 공급망 증명이 아니라
신뢰한 발행 workflow의 결과다. 앱 저장소 쓰기 권한자와 workflow 변경은 계속 리뷰해야 한다.
GITHUB_TOKEN push는 후속 일반 CI를 발생시키지 않으므로, promotion job 자체에서 전체 infra 도구
테스트·기존 Kustomize·Helm·portfolio 정책·whitespace 검사를 **push 전에** 실행한다.
동시 수정이 있으면 일반 push가 거절되며 강제 push하지 않는다. 다음 주기에 다시 확인한다.

## 처음 준비

Python 3.13 + `scripts/requirements.txt`, Helm 4.3.0, kind 0.33.0, kubectl 1.36.4,
linux/amd64 Docker Engine이 필요하다. 다른 아키텍처는 현재 발행 플랫폼부터 별도 지원해야 한다.
기존 검증용 `govbiz-elasticsearch:msa-20260920-001` 로컬 이미지만 데이터 의존성으로 재사용한다.
없으면 앱 저장소의 MSA 빌드 안내대로 먼저 준비한다. 네 앱 이미지는 로컬 load하지 않는다.

GHCR 토큰은 classic PAT의 `read:packages`만 선택하고 만료를 설정한다. 토큰을 채팅·Git·셸 명령에
직접 넣지 않는다. 대화형 터미널에서 다음 명령을 실행하면 숨김 입력으로 받으므로 파일에 저장할 필요가 없다.

```bash
python -B scripts/portfolio_cluster.py prepare
```

비대화형 실행은 소유자만 읽는 0600 임시 파일로 준비한다. 명령에는 값이 아닌 경로만 전달한다.

```bash
python -B scripts/portfolio_cluster.py prepare \
  --token-file /안전한/임시/토큰파일
```

기본 전용 kubeconfig는 Git에서 제외된 `.local/portfolio/kubeconfig`다. 기존 kubeconfig·context를
변경하지 않는다. `--state-dir`로 다른 안전한 전용 디렉터리를 지정할 수 있다.
클러스터 API는 127.0.0.1로 제한하며 외부 서버 context에는 자격 증명을 보내지 않는다.
prepare는 내부 Secret·DB·Argo CD Core까지만 준비한다. 검증·commit/push 후 다음을 명시적으로 실행한다.

```bash
python -B scripts/portfolio_cluster.py activate
python -B scripts/portfolio_cluster.py status
```

Argo 프로젝트는 네 서비스 Deployment·Service만 관리한다. Secret·PVC·Namespace·DB·클러스터
관리는 허용하지 않는다. 자동 sync와 self-heal은 켜고 자동 prune는 끈다. Argo Core에는 웹 UI가 없다.
서비스는 ClusterIP이고 기본적으로 Mac 브라우저나 인터넷에 공개하지 않는다.

```bash
kubectl --kubeconfig .local/portfolio/kubeconfig --context kind-govbiz-portfolio \
  -n govbiz-msa port-forward --address 127.0.0.1 service/core-service 18080:8080
# 다른 터미널에서: curl http://127.0.0.1:18080/api/v1/health
```

## 비밀값·데이터·비용 경계

- Core/Catalog/Ops DB는 독립 사용자·무작위 비밀번호·PVC를 사용한다. 기존 MySQL/RDS에 접속하지 않는다.
- 내부 공유 토큰은 새로 만들고 대응하는 서비스끼리만 공유한다. 재실행 시 기존 runtime Secret을 회전하지 않는다.
- 기존 계정·실제 공고 데이터는 없다. 수집·메일·유료 AI 호출은 꺼져 있으며 AI의 외부 URL도 비활성 주소다.
- 실제 서비스를 시연하려면 데이터·인증·API 키를 별도로 구성해야 한다. 자동 배포 확인과 업무 품질 검증은 다르다.
- Kubernetes Secret은 base64일 뿐 암호화 보장이 아니다. Docker/kubeconfig 접근자는 Secret을 읽을 수 있다.
- 토큰은 주기적으로 교체한다. 새 read-only 토큰 파일로 prepare를 다시 실행하면 `ghcr-pull`만 갱신한다.
  네 서비스의 인증 pull 검증 후 임시 토큰 파일을 삭제하고 만료일을 별도로 관리한다.
- Secret이 만료되면 캐시된 기존 Pod는 실행될 수 있어도 새 이미지 pull은 실패할 수 있다.
- 데이터는 Pod 재생성으로 삭제되지 않지만 kind 클러스터 삭제·Docker 데이터 초기화 시 사라진다. 백업이 아니다.

## 중지와 복귀

배포 일시 중지는 infra `MSA_PROMOTION_ENABLED=false`로 새 digest 반영부터 멈추고,
필요하면 각 Application의 자동 sync도 끈다. 자동 sync가 켜진 채 kubectl만 수정하면 self-heal이 되돌린다.
이미지 rollback은 검증된 이전 서비스 values와 대응하는 `release.json`을 함께 Git에 반영한다.
DB migration을 자동으로 되돌리지는 않는다.
같은 발행 run은 재적용하지 않지만 새 성공 발행은 다시 승격되므로 롤백 유지 중에는 promotion을 끈다.

클러스터를 삭제하지 않고 일시 정지하려면 전용 kind 노드만 중지한다.

```bash
docker stop govbiz-portfolio-control-plane
# 재개
docker start govbiz-portfolio-control-plane
```

기존 개발 Compose를 다시 쓸 때는 클러스터를 먼저 정지하고 중지해 두었던 컨테이너를 시작한다.
두 환경을 함께 켜서 메모리 부족을 만들지 않는다. 데이터 삭제 명령은 이 안내에 포함하지 않는다.

## 검증

```bash
python -B -m unittest discover -s scripts -p 'test_*.py'
python -B scripts/check_kubernetes.py
python -B scripts/check_msa.py
python -B scripts/check_portfolio.py
git diff --check
```

정적 통과와 실제 pull·Synced/Healthy 상태를 구분해서 기록한다.
NetworkPolicy 집행·의존성 readiness·부하·무중단·전체 내부 인증·실제 AI 품질은 여전히 별도 검증이다.

공식 근거: [GHCR 인증](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry),
[GitHub 일정 실행](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
[Kubernetes imagePullSecrets](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/).

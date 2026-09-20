# 서비스 이미지 digest 선택

GovBiz의 이미지 발행 CI는 서비스별 GHCR 이미지 digest와 JSON receipt를 준비한다.
[앱 릴리스 안내](https://github.com/GovBiz-Team/GovBiz/blob/develop/docs/msa-image-release.md)를 따른다.
발행 CI의 활성화·공개 상태는 앱 릴리스 안내를 따른다.
Mac 유지형 자동 경로는 [portfolio GitOps](portfolio-gitops.md)에 따로 설명한다.

2026-09-20 KST 기준 네 서비스의 [최초 GHCR 발행](https://github.com/GovBiz-Team/GovBiz/actions/runs/35457860821)이
성공했다. 최초 공개 후 사용자 결정에 따라 삭제·재발행 없이 네 패키지를 **비공개**로 전환했고,
익명 접근은 모두 HTTP 401로 거절됨을 확인했다. 전환 중 자동 발행을 잠시 중지했으나
이후 사용자 승인으로 `MSA_RELEASE_ENABLED=true`로 재개했고 [비공개 발행](https://github.com/GovBiz-Team/GovBiz/actions/runs/35495417542)이 성공했다.
조직의 공개 패키지 생성 허용은 다시 켜지 않았다.
아래 도구는 대상 환경과 pull 인증을 별도로 준비한 뒤 사용한다.

이 저장소는 **배포할 버전 선택**을 담당한다. `scripts/promote_image.py`는 검토한 receipt에서
기존 비로컬 환경의 서비스 이미지 digest만 갱신한다. Git commit/push, AWS 인증, kubectl,
Argo sync를 자동 실행하지 않는다. 자동 경로는 별도 `scripts/sync_images.py`와
`.github/workflows/sync-images.yml`이 담당한다. infra 자체 토큰으로 자기 저장소만 수정한다.

## 사용 전 조건

- 성공한 `GovBiz-Team/GovBiz`의 `MSA image candidates` 전체 run에서 받은 artifact인지 확인한다.
  PR run·실패/진행 중 run·다른 저장소·임의 JSON을 사용하지 않는다.
- receipt는 서명된 provenance가 아니다. 서비스, 검증 소스 SHA, registry, 실제 GHCR digest를 검토한다.
- `environments/<환경>/<서비스>.yaml`을 별도로 준비하고 리뷰한다.
  `localMode: false`, 정확한 `serviceName`, `image.repository`, `image.pullPolicy: IfNotPresent` 또는
  `Always`, 빈 tag가 필요하다. 공개 패키지는 익명 pull을 확인한다. 외부 저장소·Secret·네트워크 경계는 별도다.
- 이 도구는 환경 파일을 만들지 않으며 `local-msa`와 기존 local smoke 값을 수정하지 않는다.
  현재 digest 환경은 `portfolio`이며 아래 `staging` 명령은 별도 환경을 준비한 후 쓰는 예시다.

## 미리보기와 적용 예시

```bash
python scripts/promote_image.py \
  --receipt /tmp/ai-service.json \
  --values environments/staging/ai-service.yaml \
  --expected-digest 'sha256:<현재 values의 64자리 digest>'
```

`--write` 없이 실행하면 diff만 표시한다. 적용하려면 동일 인수에 `--write`를 추가한다.
최초 설정에서 기존 digest가 빈 값일 때만 `--expected-digest ''`를 쓴다.
기존 값 불일치 시 다른 배포가 먼저 진행된 것으로 간주해 거절한다. receipt에 담긴 다른 registry로
목적지를 바꾸거나 Secret·환경변수·서비스 이름을 함께 바꾸지 않는다.
YAML 출력 형식·주석은 정규화될 수 있지만 파싱한 값은 `image.digest` 외에 바뀌지 않는다.

적용 후 해당 환경의 Helm 렌더링·정책·CI 검사를 하고 Git diff에서 서비스 하나만 변경됐는지 확인한다.
명시적으로 승인된 브랜치에 변경을 반영한 뒤 **그 환경**을 보는 Argo Application이 동기화해야
실제 배포가 된다. 이미지 업로드 또는 로컬 파일 수정만으로 배포가 됐다고 표시하지 않는다.

롤백은 이전에 검증한 digest를 같은 경로에 선택하는 별도 Git 변경이다.
DB migration이나 데이터 복원까지 자동으로 되돌린다고 가정하지 않는다.

## 검증 범위

```bash
python -B -m unittest discover -s scripts -p 'test_promote_image.py'
```

다른 서비스/registry·mutable tag·stale digest·로컬 fixture·경로 이탈·symlink·중복 YAML 키를
거절하고, 기본 미리보기의 무변경·선택 digest만 적용·동일 이미지 재적용의 무변경을 검증한다.
실제 GHCR 인증·이미지 pull·상시 Argo 클러스터는 이 테스트 범위가 아니다.

현재 사용자 선택은 비공개 패키지다. 배포 환경은 별도의 읽기 전용 인증을
같은 namespace의 `kubernetes.io/dockerconfigjson` Secret으로 주입하고, Helm 값에는
`imagePullSecrets: [{name: ghcr-pull}]`처럼 이름만 기록한다. Secret 값은 Git/values에 넣지 않는다.
현재 local-msa 검증 환경은 로컬 로드 이미지를 사용하므로 이 목록의 기본값 `[]`를 유지한다.
`portfolio` 값에는 이 참조를 설정했으며 전용 bootstrap 도구로 실제 Secret을 Git 밖에서 주입한다.

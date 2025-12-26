# Reppy Worker

OCI Functions 기반 LLM 파이프라인 Worker. LangChain + Gemini를 사용하여 피트니스 코칭 요청을 처리합니다.

## 아키텍처

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   OCI Queue     │────▶│    Worker    │────▶│  OCI Streaming  │
│ (request-queue) │     │ (OCI Func)   │     │  (token-stream) │
└─────────────────┘     └──────┬───────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────┐     ┌─────────────────┐
                        │  VM Internal │     │   Result Queue  │
                        │     API      │     │                 │
                        └──────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  PostgreSQL  │
                        │   (via VM)   │
                        └──────────────┘
```

### 핵심 제약사항

1. **Worker는 PostgreSQL에 직접 접근하지 않음** - VM Internal API를 통해서만 DB 조회
2. **VectorDB(Qdrant)는 Worker에서만 접근** - 사용자 메모리 시맨틱 검색
3. **멱등성(Idempotency)** - requestId 기준으로 VM API에서 claim 처리

## 프로젝트 구조

```
reppy-worker/
├── prompts/                    # LLM 프롬프트 YAML 파일
│   ├── action_routing.yaml     # 인텐트 라우팅
│   ├── chat_planner.yaml       # 채팅 계획 수립
│   ├── chat_response.yaml      # 채팅 응답 생성
│   ├── generate_program.yaml   # 프로그램 생성
│   └── update_routine.yaml     # 루틴 수정
├── src/worker/
│   ├── config/                 # 설정 (pydantic-settings)
│   ├── contracts/              # Pydantic 스키마/모델
│   ├── context/                # 컨텍스트 페칭
│   │   ├── ports/              # 추상 인터페이스
│   │   └── adapters/           # 구현체 (VM API, Qdrant)
│   ├── emit/                   # 이벤트 발행
│   │   ├── ports/              # 추상 인터페이스
│   │   └── adapters/           # 구현체 (OCI Streaming, Queue)
│   ├── llm/                    # LLM 통합
│   │   ├── prompt_loader.py    # 프롬프트 로더
│   │   ├── gemini_client.py    # Gemini LangChain 클라이언트
│   │   └── structured_output.py# 구조화된 출력 파서
│   ├── pipelines/              # 파이프라인
│   │   ├── orchestrator.py     # 메인 오케스트레이터
│   │   ├── chat_pipeline.py    # CHAT_RESPONSE 처리
│   │   ├── generate_pipeline.py# GENERATE_ROUTINE 처리
│   │   └── update_pipeline.py  # UPDATE_ROUTINE 처리
│   ├── entrypoints/            # 진입점
│   │   ├── oci_function.py     # OCI Functions 핸들러
│   │   └── local_runner.py     # 로컬 실행기
│   └── utils/                  # 유틸리티
└── tests/                      # 테스트
```

## 설치

```bash
# Python 3.11+ 필요
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"

# OCI SDK 포함 (프로덕션)
pip install -e ".[oci]"
```

## 환경 변수

`.env` 파일을 생성하거나 환경 변수를 설정합니다:

```bash
# Google/Gemini API
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL_ROUTER=gemini-2.5-flash    # 라우터/플래너용 (비용 절감)
GEMINI_MODEL_MAIN=gemini-2.5-pro        # 메인 생성용

# Prompts
PROMPTS_DIR=./prompts

# VM Internal API
VM_INTERNAL_BASE_URL=http://10.0.0.10:8080/internal
VM_INTERNAL_TOKEN=your-internal-token

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                          # optional
QDRANT_COLLECTION_MEMORY=user_memory

# OCI
OCI_STREAM_ID=your-stream-ocid
OCI_RESULT_QUEUE_ID=your-queue-ocid

# Logging
LOG_LEVEL=INFO
```

## 실행

### 로컬 실행

```bash
# JSON 파일로 실행
python -m src.worker.entrypoints.local_runner -f request.json

# JSON 문자열로 실행
python -m src.worker.entrypoints.local_runner -j '{"requestId": "test-123", ...}'

# stdin에서 읽기
cat request.json | python -m src.worker.entrypoints.local_runner

# 예제 페이로드로 실행
python -m src.worker.entrypoints.local_runner --example
```

### 예제 요청 페이로드

```json
{
  "requestId": "req-12345",
  "userId": "user-67890",
  "conversation_history": [
    {"role": "user", "content": "오늘 운동 뭐 해야 돼?"}
  ],
  "stream": true,
  "metadata": {}
}
```

### OCI Function 배포

```bash
# func.yaml 설정 후
fn deploy --app your-app-name
```

## 파이프라인 흐름

### 1. Intent Routing

```
Request → intent_routing.yaml → Intent (CHAT_RESPONSE | GENERATE_ROUTINE | UPDATE_ROUTINE)
```

### 2. CHAT_RESPONSE 파이프라인

```
Intent=CHAT_RESPONSE
    ↓
chat_planner.yaml (Flash model)
    ↓
Context Aggregation (based on required_context)
    ├─ active_routines → VM API
    ├─ user_memory → Qdrant
    └─ exercise_catalog → VM API
    ↓
chat_response.yaml (Pro model, optional streaming)
    ↓
Result → result-queue
```

### 3. GENERATE_ROUTINE 파이프라인

```
Intent=GENERATE_ROUTINE
    ↓
Fetch active_routines (baseline)
    ↓
generate_program.yaml (Pro model)
    ↓
Result → result-queue
```

### 4. UPDATE_ROUTINE 파이프라인

```
Intent=UPDATE_ROUTINE
    ↓
Fetch active_routines (find routine to update)
    ↓
update_routine.yaml (Pro model)
    ↓
Result → result-queue
```

## 결과 이벤트 형식

### Token Stream Event (실시간 토큰)

```json
{
  "requestId": "req-12345",
  "seq": 1,
  "delta": "안녕",
  "ts": 1703123456789
}
```

### Result Event (최종 결과)

```json
{
  "requestId": "req-12345",
  "status": "SUCCEEDED",
  "final": {
    "reply": "오늘은 푸쉬데이입니다! 벤치프레스부터 시작해볼까요?"
  },
  "error": null,
  "usage": {},
  "meta": {
    "intent": "CHAT_RESPONSE",
    "action": "GET_ACTIVE_ROUTINES",
    "confidence": 0.95
  }
}
```

### Status 값

- `SUCCEEDED`: 성공적으로 처리됨
- `FAILED`: 오류 발생
- `CLARIFY`: 추가 정보 필요 (clarification question 포함)

## 테스트

```bash
# 모든 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src/worker

# 특정 테스트만
pytest tests/test_schemas.py -v
```

## VM Internal API 계약

모든 요청에 `Authorization: Bearer <VM_INTERNAL_TOKEN>` 헤더 필요.

### POST /idempotency/claim

```json
// Request
{ "requestId": "<uuid>" }

// Response
{ "claimed": true }  // or false
```

### GET /users/{userId}/profile

```json
// Response
{
  "username": "Alex",
  "experience_level": "INTERMEDIATE",
  "goal": "HYPERTROPHY",
  ...
}
```

### GET /users/{userId}/active-routines

```json
// Response
{
  "routines": [
    {
      "routine_name": "Push Day A",
      "routine_order": 1,
      "plans": [...]
    }
  ]
}
```

### GET /exercises/search?q=...

```json
// Response
{
  "items": [
    {
      "exercise_code": "BARBELL_BENCH_PRESS",
      "main_muscle_code": "CHEST",
      ...
    }
  ]
}
```

## 개발 노트

### 모델 선택 전략

- **Router/Planner**: `gemini-2.5-flash` (빠르고 저렴)
- **Main Generation**: `gemini-2.5-pro` (고품질 출력)

### 멱등성 처리

1. 요청 처리 시작 전 `/idempotency/claim` 호출
2. `claimed=false`면 처리 스킵 (이미 처리 중/완료)
3. 중복 처리 방지 및 재시도 안전성 보장

### 에러 처리 전략

- **라우터/플래너 파싱 실패**: fallback 스키마 사용, CLARIFY 상태로 응답
- **프로그램/루틴 생성 실패**: FAILED 상태로 에러 정보 포함

## 라이선스

MIT


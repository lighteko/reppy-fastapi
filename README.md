# Reppy Worker

OCI Functions 환경에서 동작하는 AI 피트니스 코칭 Worker입니다. LangChain + Gemini를 사용하여 사용자 요청을 처리합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OCI Functions                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       Reppy Worker                                │   │
│  │                                                                   │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐   │   │
│  │  │  Intent  │───▶│   Chat   │───▶│  Context Aggregation     │   │   │
│  │  │  Router  │    │ Planner  │    │  (VM API + Qdrant)       │   │   │
│  │  └──────────┘    └──────────┘    └──────────────────────────┘   │   │
│  │       │               │                      │                    │   │
│  │       ▼               ▼                      ▼                    │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │              LLM Response Generation                      │   │   │
│  │  │         (Streaming / Structured Output)                   │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                           │                                       │   │
│  └───────────────────────────┼───────────────────────────────────────┘   │
│                              │                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ OCI Streaming│    │ Result Queue │    │   VM API     │
  │ (Token Stream)│   │ (Final Result)│   │ (PostgreSQL) │
  └──────────────┘    └──────────────┘    └──────────────┘
```

## 주요 제약사항

1. **Worker는 PostgreSQL에 직접 접근하지 않음** - VM의 Internal API를 통해서만 DB 데이터 조회
2. **VectorDB(Qdrant)는 Worker에서만 접근** - User Memory 검색용
3. **멱등성 보장** - 요청 처리 전 VM API를 통해 claim 시도, 실패 시 스킵

## 프로젝트 구조

```
reppy-worker/
├── prompts/                    # LLM 프롬프트 YAML 파일
│   ├── intent_routing.yaml
│   ├── chat_planner.yaml
│   ├── chat_response.yaml
│   ├── generate_program.yaml
│   └── update_routine.yaml
│
├── src/
│   ├── config/                 # pydantic-settings 기반 설정
│   │   └── settings.py
│   │
│   ├── contracts/              # Pydantic 스키마/메시지 정의
│   │   ├── schemas.py          # LLM 출력 스키마
│   │   └── messages.py         # 입출력 메시지 계약
│   │
│   ├── context/                # 컨텍스트 조회 (Ports & Adapters)
│   │   ├── ports/              # 인터페이스 정의
│   │   │   └── interfaces.py
│   │   └── adapters/           # 구현체
│   │       ├── vm_client.py    # VM Internal API 클라이언트
│   │       ├── qdrant_adapter.py
│   │       └── aggregator.py   # 컨텍스트 통합
│   │
│   ├── emit/                   # 결과 발행
│   │   ├── ports.py            # TokenStreamer, ResultPublisher 인터페이스
│   │   ├── oci_streaming.py    # OCI Streaming 어댑터
│   │   └── result_queue.py     # OCI Queue 어댑터
│   │
│   ├── llm/                    # LLM 통합
│   │   └── gemini.py           # LangChain + Gemini 클라이언트
│   │
│   ├── pipelines/              # 처리 파이프라인
│   │   ├── orchestrator.py     # 전체 흐름 조율
│   │   ├── router.py           # Intent 라우팅
│   │   ├── chat_pipeline.py    # 채팅 응답 파이프라인
│   │   ├── generate_pipeline.py # 프로그램 생성
│   │   └── update_pipeline.py  # 루틴 업데이트
│   │
│   ├── utils/                  # 유틸리티
│   │   ├── logging.py          # 로깅 설정
│   │   └── prompt_loader.py    # 프롬프트 로더
│   │
│   └── entrypoints/            # 진입점
│       ├── oci_function.py     # OCI Functions 핸들러
│       └── local_runner.py     # 로컬 테스트용
│
├── tests/                      # 테스트
│   ├── test_schemas.py
│   └── test_planner_context.py
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 설치

### 요구사항

- Python 3.11+
- Google API Key (Gemini)
- OCI 계정 및 설정

### 의존성 설치

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate  # Windows

# 의존성 설치
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"
```

## 환경 설정

`.env` 파일을 생성하고 다음 환경변수를 설정합니다:

```env
# Google/Gemini
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL_ROUTER=gemini-2.0-flash
GEMINI_MODEL_MAIN=gemini-2.5-pro-preview-06-05

# Prompts
PROMPTS_DIR=./prompts

# VM Internal API
VM_INTERNAL_BASE_URL=http://10.0.0.10:8080/internal
VM_INTERNAL_TOKEN=your-internal-api-token

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=optional-api-key
QDRANT_COLLECTION_MEMORY=user_memory

# OCI
OCI_STREAM_ID=ocid1.stream.oc1...
OCI_RESULT_QUEUE_ID=ocid1.queue.oc1...

# Logging
LOG_LEVEL=INFO
```

## 사용법

### 로컬 실행

```bash
# JSON 파일로 실행
python -m src.entrypoints.local_runner -f payload.json

# 인라인 JSON으로 실행
python -m src.entrypoints.local_runner -j '{"requestId": "...", ...}'

# stdin으로 실행
cat payload.json | python -m src.entrypoints.local_runner
```

### 샘플 페이로드

```json
{
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "user123",
  "conversationHistory": [
    {"role": "user", "content": "오늘 운동 뭐야?"}
  ],
  "stream": true,
  "metadata": {}
}
```

### OCI Functions 배포

```bash
# Docker 이미지 빌드
fn build

# 배포
fn deploy --app your-app-name

# 테스트 호출
echo '{"requestId": "test", ...}' | fn invoke your-app-name worker-function
```

## 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src --cov-report=html

# 특정 테스트 실행
pytest tests/test_schemas.py -v
```

## LLM 파이프라인 흐름

### 1. Intent Routing

사용자 메시지를 분류하여 적절한 핸들러로 라우팅합니다.

- `CHAT_RESPONSE`: 일반 대화, 질문, 설명
- `GENERATE_ROUTINE`: 새 루틴/프로그램 생성
- `UPDATE_ROUTINE`: 기존 루틴 수정

### 2. Chat Response 파이프라인

```
Intent: CHAT_RESPONSE
    │
    ▼
┌──────────────────┐
│   Chat Planner   │  ← Router 모델 (Flash)
│  - 액션 결정     │
│  - 필요 컨텍스트 │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Context Aggregation │
│  - active_routines  │ ← VM API
│  - user_memory      │ ← Qdrant
│  - exercise_catalog │ ← VM API
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Chat Responder  │  ← Main 모델 (Pro)
│  - 최종 응답 생성 │
│  - 스트리밍 지원  │
└──────────────────┘
```

### 3. Structured Output

모든 LLM 출력은 Pydantic 모델로 강제 파싱됩니다:

- `IntentRoutingOutput`: 라우팅 결과
- `ChatPlannerOutput`: 플래닝 결과
- `ChatResponseOutput`: 응답 결과
- `GenerateProgramOutput`: 생성된 프로그램
- `UpdateRoutineOutput`: 업데이트된 루틴

파싱 실패 시:
- Router/Planner: `CHAT_RESPONSE` + `ASK_CLARIFY`로 폴백
- Generate/Update: `FAILED` 상태로 결과 발행

## VM Internal API 계약

Worker가 호출하는 VM API 엔드포인트:

### POST /idempotency/claim
```json
// Request
{"requestId": "uuid"}
// Response
{"claimed": true|false}
```

### GET /users/{userId}/profile
사용자 프로필 JSON 반환

### GET /users/{userId}/active-routines
활성 루틴 목록 JSON 반환

### GET /exercises/search?q=...
운동 검색 결과 JSON 반환

## 메시지 계약

### Token Stream Event (OCI Streaming)
```json
{
  "requestId": "uuid",
  "seq": 1,
  "delta": "text",
  "ts": 1234567890
}
```

### Result Event (Result Queue)
```json
{
  "requestId": "uuid",
  "status": "SUCCEEDED|FAILED|CLARIFY",
  "final": {"reply": "..."} | {"routines": [...]},
  "error": {"code": "...", "message": "..."} | null,
  "usage": {...},
  "meta": {"intent": "...", "action": "...", "confidence": 0.0}
}
```

## 라이선스

MIT License


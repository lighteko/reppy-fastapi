# Deployment Guide

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [OCI Functions Deployment](#oci-functions-deployment)
4. [Production Considerations](#production-considerations)

## Local Development

### Prerequisites

- Python 3.11+
- Qdrant (running locally or remote)
- Express API server
- OpenAI API key

### Setup

1. **Install dependencies:**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp env.example .env
# Edit .env with your settings
```

3. **Start Qdrant (optional if using remote):**

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

4. **Run the server:**

```bash
python src/app.py
# Or with uvicorn:
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

5. **Test the API:**

```bash
curl http://localhost:8000/api/v1/health
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src tests/

# Specific test file
pytest tests/test_router.py -v
```

## Docker Deployment

### Using Docker Compose

The easiest way to run everything locally:

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

Services included:
- **qdrant**: Vector database on port 6333
- **api**: FastAPI server on port 8000

### Custom Docker Build

**Build the development image:**

```bash
docker build -f Dockerfile.dev -t reppy-fastapi:dev .
```

**Run the container:**

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/src:/app/src \
  -v $(pwd)/prompts:/app/prompts \
  --env-file .env \
  --name reppy-api \
  reppy-fastapi:dev
```

**View logs:**

```bash
docker logs -f reppy-api
```

## OCI Functions Deployment

### Prerequisites

- OCI CLI configured
- OCIR (Oracle Cloud Infrastructure Registry) repository created
- OCI Functions application/network configured
- Remote Qdrant instance (Qdrant Cloud recommended)
- Express API server accessible from Functions

**Container/handler details:**
- Dockerfile: `Dockerfile`
- Handler entrypoint: `src.consumer.lambda_handler.handler` (set in `CMD`)

### Build and Push Function Image (OCIR)

```bash
# Build the function image
docker build -f Dockerfile -t reppy-functions:latest .

# (Optional) create an OCIR repository if you don't have one yet
oci artifacts container repository create \
  --compartment-id <compartment-ocid> \
  --display-name reppy-functions

# Log in to OCIR (username is <tenancy-namespace>/<user>)
docker login <region>.ocir.io \
  --username <tenancy-namespace>/<user> \
  --password <auth-token>

# Tag for OCIR
docker tag reppy-functions:latest <region>.ocir.io/<tenancy-namespace>/reppy-functions/reppy-fastapi:latest

# Push to OCIR
docker push <region>.ocir.io/<tenancy-namespace>/reppy-functions/reppy-fastapi:latest
```

### Create Functions Application and Function

**Using OCI CLI:**

```bash
oci fn application create \
  --compartment-id <compartment-ocid> \
  --display-name reppy-rag-app \
  --subnet-ids '["<subnet-ocid>"]'

oci fn function create \
  --application-id <app-ocid> \
  --display-name reppy-rag-processor \
  --image <region>.ocir.io/<tenancy-namespace>/reppy-functions/reppy-fastapi:latest \
  --memory-in-mbs 2048 \
  --timeout-in-seconds 300 \
  --config '{"OPENAI_API_KEY":"your-key","QDRANT_URL":"https://your-qdrant-instance","EXPRESS_BASE_URL":"https://your-express-api"}'
```

### Configure Event Source

Set up your event source (OCI Queue, Streaming, or API Gateway) to invoke the
function. For example, with OCI Queue you can configure the queue-trigger in the
Functions application console or via OCI CLI to route messages to
`reppy-rag-processor`.

### Check Function Logs

```bash
oci fn function log list \
  --application-id <app-ocid> \
  --function-id <function-ocid>
```

## Production Considerations

### Environment Variables

**Required:**
- `OPENAI_API_KEY`: OpenAI API key
- `QDRANT_URL`: Qdrant server URL
- `EXPRESS_BASE_URL`: Express API base URL

**Recommended:**
- `ENABLE_LANGSMITH=true`: Enable tracing
- `LANGSMITH_API_KEY`: LangSmith API key
- `LOG_LEVEL=INFO`: Production log level
- `AGENT_MAX_ITERATIONS=6`: Lower for cost control

### Security

1. **API Keys:**
   - Store in AWS Secrets Manager or Parameter Store
   - Never commit to version control
   - Rotate regularly

2. **Network:**
   - Use VPC for Lambda
   - Restrict Qdrant and Express API access
   - Enable HTTPS/TLS

3. **Authentication:**
   - Add API key authentication to FastAPI
   - Use IAM roles for AWS services
   - Implement rate limiting

### Monitoring

1. **CloudWatch:**
   ```bash
   # Create alarms
   aws cloudwatch put-metric-alarm \
     --alarm-name reppy-lambda-errors \
     --metric-name Errors \
     --namespace AWS/Lambda \
     --statistic Sum \
     --period 300 \
     --threshold 5 \
     --comparison-operator GreaterThanThreshold
   ```

2. **LangSmith:**
   - Enable in production for debugging
   - Set up alerts for failures
   - Monitor tool usage

3. **Application Metrics:**
   - Log all tool calls
   - Track validation failures
   - Monitor latency

### Scaling

1. **Lambda:**
   - Set reserved concurrency
   - Optimize memory allocation
   - Use provisioned concurrency for low latency

2. **Qdrant:**
   - **Use Qdrant Cloud** (recommended for production)
   - Enable replicas for high availability
   - Monitor query performance
   - Configure API key authentication
   - Set up backup snapshots

3. **FastAPI:**
   - Deploy behind load balancer
   - Use auto-scaling groups
   - Enable connection pooling

### Cost Optimization

1. **LLM Calls:**
   - Cache common queries
   - Use lower temperature for deterministic tasks
   - Limit max_tokens

2. **Tool Usage:**
   - Batch API calls when possible
   - Implement request caching
   - Monitor tool call frequency

3. **Vector Search:**
   - Tune k parameter (lower = cheaper)
   - Use filters to reduce search space
   - Consider embedding caching

### Backup & Disaster Recovery

1. **Prompts:**
   - Version control in Git
   - Back up to S3
   - Document changes

2. **Vector Database:**
   - Regular Qdrant snapshots
   - Export collections periodically
   - Test restore procedures

3. **Configuration:**
   - Document all environment variables
   - Keep deployment scripts versioned
   - Maintain runbooks

## Troubleshooting

### Common Issues

**1. LLM Timeout:**
```
Solution: Increase LLM_TIMEOUT in config
```

**2. Qdrant Connection Failed:**
```
Check: QDRANT_URL is correct and accessible
Verify: Qdrant service is running
Test: curl http://qdrant-url:6333/collections
```

**3. Express API 401/403:**
```
Check: EXPRESS_API_KEY is set correctly
Verify: API key is valid and not expired
```

**4. Lambda Out of Memory:**
```
Increase memory in Lambda configuration
Optimize tool implementations
Enable streaming responses
```

**5. Validation Errors:**
```
Check: available_context matches actual codes
Verify: LLM is following output schema
Review: validation.py schemas
```

### Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health

# Qdrant health
curl http://localhost:6333/collections

# Express health
curl http://express-url/health
```

### Logs

**FastAPI:**
```bash
tail -f logs/reppy_*.log
```

**Lambda:**
```bash
aws logs tail /aws/lambda/reppy-rag-processor --follow
```

**Docker:**
```bash
docker-compose logs -f api
```

## Qdrant Infrastructure Setup

### Qdrant Cloud (Recommended for Production)

1. **Create Account**
   - Go to [Qdrant Cloud](https://cloud.qdrant.io/)
   - Create a new cluster
   - Get connection details (URL + API Key)

2. **Configure Environment**
   ```bash
   QDRANT_URL=https://your-cluster.cloud.qdrant.io
   QDRANT_API_KEY=your-api-key
   QDRANT_GRPC=false
   ```

3. **Create Collections**
   ```python
   from qdrant_client import QdrantClient
   from qdrant_client.models import Distance, VectorParams
   
   client = QdrantClient(
       url="https://your-cluster.cloud.qdrant.io",
       api_key="your-api-key"
   )
   
   # Exercises collection
   client.create_collection(
       collection_name="exercises",
       vectors_config=VectorParams(
           size=1536,  # text-embedding-3-small
           distance=Distance.COSINE
       )
   )
   
   # User memory collection
   client.create_collection(
       collection_name="user_memory",
       vectors_config=VectorParams(
           size=1536,
           distance=Distance.COSINE
       )
   )
   ```

4. **Verify Setup**
   ```bash
   curl -H "api-key: YOUR_KEY" \
     https://your-cluster.cloud.qdrant.io/collections
   ```

### Local Qdrant (Development Only)

```bash
# Start Qdrant
docker run -d \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant:latest

# Configure
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty

# Verify
curl http://localhost:6333/collections
```

### Collection Schemas

**Exercises Collection:**
```json
{
  "source_id": "uuid",
  "exercise_code": "string",
  "name": "string",
  "main_muscle_id": "uuid",
  "equipment_id": "uuid",
  "difficulty_level": "integer"
}
```

**User Memory Collection:**
```json
{
  "source_id": "uuid",
  "user_id": "uuid",
  "created_at": "datetime",
  "memory_type": "string",
  "content": "string"
}
```

### Populating Data

See example script in DEVELOPER_GUIDE.md for migrating data from PostgreSQL to Qdrant.

### Qdrant Monitoring

```bash
# Check collections
curl -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections

# Check collection size
curl -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections/exercises/points/count

# Create snapshot (backup)
curl -X POST -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections/exercises/snapshots
```

## Support

For issues or questions:
1. Check [README.md](README.md) for overview
2. Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for detailed development info
3. Review test files for usage examples
4. Check logs for error details

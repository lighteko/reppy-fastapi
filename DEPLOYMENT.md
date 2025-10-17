# Deployment Guide

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [AWS Lambda Deployment](#aws-lambda-deployment)
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

## AWS Lambda Deployment

### Prerequisites

- AWS CLI configured
- ECR repository created
- IAM role for Lambda with appropriate permissions
- Remote Qdrant instance (Qdrant Cloud recommended)
- Express API server accessible from Lambda

### Build Lambda Image

```bash
# Build the Lambda image
docker build -f Dockerfile -t reppy-lambda:latest .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag reppy-lambda:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/reppy-lambda:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/reppy-lambda:latest
```

### Create Lambda Function

**Using AWS CLI:**

```bash
aws lambda create-function \
  --function-name reppy-rag-processor \
  --package-type Image \
  --code ImageUri=<account-id>.dkr.ecr.us-east-1.amazonaws.com/reppy-lambda:latest \
  --role arn:aws:iam::<account-id>:role/lambda-execution-role \
  --timeout 300 \
  --memory-size 2048 \
  --environment Variables='{
    OPENAI_API_KEY=your-key,
    QDRANT_URL=https://your-qdrant-instance,
    EXPRESS_BASE_URL=https://your-express-api
  }'
```

### Configure SQS Trigger

**Create SQS queue:**

```bash
aws sqs create-queue \
  --queue-name reppy-rag-jobs \
  --attributes VisibilityTimeout=900
```

**Add SQS trigger to Lambda:**

```bash
aws lambda create-event-source-mapping \
  --function-name reppy-rag-processor \
  --event-source-arn arn:aws:sqs:us-east-1:<account-id>:reppy-rag-jobs \
  --batch-size 1
```

### Test Lambda Function

**Send test message to SQS:**

```bash
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/<account-id>/reppy-rag-jobs \
  --message-body '{
    "job_type": "generate_program",
    "payload": {
      "user_id": "test-user",
      "program_id": "test-program",
      "context": {...}
    }
  }'
```

**Check Lambda logs:**

```bash
aws logs tail /aws/lambda/reppy-rag-processor --follow
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

## Support

For issues or questions:
1. Check the main README.md
2. Review test files for usage examples
3. Check logs for error details
4. Open an issue on GitHub


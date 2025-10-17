# Qdrant Setup Guide

This guide covers setting up Qdrant for the Reppy RAG pipeline.

## Recommended: Qdrant Cloud

For production use, we recommend **Qdrant Cloud** for reliability, performance, and managed backups.

### 1. Create Qdrant Cloud Account

1. Go to [Qdrant Cloud](https://cloud.qdrant.io/)
2. Sign up for an account
3. Create a new cluster

### 2. Get Connection Details

After creating your cluster, you'll receive:
- **Cluster URL**: `https://xxxxx-xxxxx.cloud.qdrant.io`
- **API Key**: Your authentication key

### 3. Configure Environment

```bash
# In your .env file
QDRANT_URL=https://your-cluster-id.cloud.qdrant.io
QDRANT_API_KEY=your-api-key-here
QDRANT_GRPC=false  # Use HTTP
```

### 4. Create Collections

The application needs two collections:

**Exercises Collection:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(
    url="https://your-cluster.cloud.qdrant.io",
    api_key="your-api-key"
)

# Create exercises collection
client.create_collection(
    collection_name="exercises",
    vectors_config=VectorParams(
        size=1536,  # text-embedding-3-small dimension
        distance=Distance.COSINE
    )
)

# Create user_memory collection
client.create_collection(
    collection_name="user_memory",
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE
    )
)
```

### 5. Verify Setup

```bash
# Test connection
curl -H "api-key: your-api-key" \
  https://your-cluster.cloud.qdrant.io/collections

# Should return list of collections including 'exercises' and 'user_memory'
```

## Alternative: Local Qdrant (Development Only)

For development and testing, you can run Qdrant locally.

### 1. Start Qdrant with Docker

```bash
docker run -d \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant:latest
```

### 2. Configure Environment

```bash
# In your .env file
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty for local
QDRANT_GRPC=false
```

### 3. Create Collections

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

# Create collections (same as above)
client.create_collection(
    collection_name="exercises",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

client.create_collection(
    collection_name="user_memory",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)
```

### 4. Verify Setup

```bash
curl http://localhost:6333/collections
```

## Collection Schemas

### Exercises Collection

**Vector**: 1536 dimensions (OpenAI text-embedding-3-small)

**Payload Schema**:
```json
{
  "source_id": "uuid",          // exercise_id from PostgreSQL
  "exercise_code": "string",    // e.g., "BARBELL_BENCH_PRESS"
  "name": "string",             // e.g., "Barbell Bench Press"
  "main_muscle_id": "uuid",     // For filtering
  "equipment_id": "uuid",       // For filtering
  "difficulty_level": "integer" // 1-5 scale
}
```

### User Memory Collection

**Vector**: 1536 dimensions (OpenAI text-embedding-3-small)

**Payload Schema**:
```json
{
  "source_id": "uuid",        // message_id or feedback_id
  "user_id": "uuid",          // REQUIRED for filtering
  "created_at": "datetime",   // ISO 8601 format
  "memory_type": "string",    // e.g., "goal", "injury_note"
  "content": "string"         // The memory text
}
```

## Populating Data

### From PostgreSQL to Qdrant

You'll need a separate script to:
1. Fetch exercises from PostgreSQL
2. Generate embeddings using OpenAI
3. Upsert into Qdrant

**Example script:**

```python
import asyncio
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import psycopg2

# Initialize clients
openai_client = OpenAI(api_key="your-key")
qdrant_client = QdrantClient(
    url="https://your-cluster.cloud.qdrant.io",
    api_key="your-qdrant-key"
)

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="reppy",
    user="user",
    password="pass",
    host="localhost"
)

# Fetch exercises
cursor = conn.cursor()
cursor.execute("""
    SELECT 
        e.exercise_id,
        ei.exercise_name,
        e.main_muscle_id,
        e.equipment_id,
        e.difficulty_level
    FROM repy_exercise_m e
    JOIN repy_exercise_i18n_m ei ON e.exercise_id = ei.exercise_id
    WHERE ei.locale = 'en-US'
""")

exercises = cursor.fetchall()

# Process and upload
points = []
for ex_id, name, muscle_id, equip_id, difficulty in exercises:
    # Generate embedding
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=name
    )
    embedding = response.data[0].embedding
    
    # Create point
    point = PointStruct(
        id=ex_id,
        vector=embedding,
        payload={
            "source_id": str(ex_id),
            "exercise_code": name.upper().replace(" ", "_"),
            "name": name,
            "main_muscle_id": str(muscle_id),
            "equipment_id": str(equip_id),
            "difficulty_level": difficulty
        }
    )
    points.append(point)
    
    # Batch upsert every 100 points
    if len(points) >= 100:
        qdrant_client.upsert(
            collection_name="exercises",
            points=points
        )
        points = []
        print(f"Uploaded batch of 100 exercises")

# Upload remaining
if points:
    qdrant_client.upsert(
        collection_name="exercises",
        points=points
    )

print(f"Total exercises uploaded: {len(exercises)}")
```

## Configuration Reference

### Environment Variables

```env
# Qdrant Cloud (Production)
QDRANT_URL=https://xxxxx.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
QDRANT_GRPC=false

# Collection Names
QDRANT_EXERCISES_COLLECTION=exercises
QDRANT_MEMORY_COLLECTION=user_memory

# Vector Settings
QDRANT_VECTOR_SIZE=1536
QDRANT_DISTANCE=Cosine

# Search Settings
QDRANT_SEARCH_K=5           # Number of results
QDRANT_USE_MMR=true         # Diversity
QDRANT_MMR_LAMBDA=0.5       # Balance (0=diversity, 1=relevance)
```

## Health Check

```bash
# Check collections
curl -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections

# Check specific collection
curl -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections/exercises

# Check collection size
curl -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections/exercises/points/count
```

## Backup and Restore

### Qdrant Cloud

Automatic backups are included with Qdrant Cloud. You can also:

```bash
# Create snapshot
curl -X POST -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections/exercises/snapshots

# List snapshots
curl -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections/exercises/snapshots
```

### Local Qdrant

```bash
# Backup (copy storage directory)
docker cp qdrant:/qdrant/storage ./qdrant_backup_$(date +%Y%m%d)

# Restore (copy back)
docker cp ./qdrant_backup_20251017 qdrant:/qdrant/storage
docker restart qdrant
```

## Performance Tuning

### Search Optimization

```python
# Use filters to reduce search space
results = retriever.retrieve_exercises(
    query="chest exercises",
    k=5,
    filters={
        "main_muscle_id": "chest_muscle_uuid",
        "difficulty_level": 2  # Intermediate
    }
)
```

### Indexing

Qdrant automatically indexes payloads. For better performance:

1. **Create indexes** on frequently filtered fields:
   - `user_id` (for user_memory)
   - `main_muscle_id` (for exercises)
   - `difficulty_level` (for exercises)

2. **Use HNSW parameters** (Qdrant Cloud handles this automatically)

### Monitoring

Monitor these metrics:
- Query latency
- Collection size
- Memory usage
- API rate limits

## Troubleshooting

### Connection Issues

**Problem**: "Connection refused" or "Unauthorized"

**Solutions**:
- Verify `QDRANT_URL` is correct (include `https://`)
- Check `QDRANT_API_KEY` is set
- Test with curl: `curl -H "api-key: KEY" URL/collections`

### Empty Search Results

**Problem**: Search returns no results

**Solutions**:
- Verify collections are populated: `GET /collections/{name}/points/count`
- Check vector dimensions match (1536)
- Verify query embedding is generated correctly

### Slow Queries

**Problem**: High search latency

**Solutions**:
- Reduce `k` parameter (fewer results = faster)
- Add filters to reduce search space
- Use Qdrant Cloud for better performance
- Check network latency to Qdrant server

## Support

- **Qdrant Documentation**: https://qdrant.tech/documentation/
- **Qdrant Cloud Support**: https://cloud.qdrant.io/support
- **Community**: https://discord.gg/qdrant

## Next Steps

After setting up Qdrant:

1. **Populate collections** with exercise and memory data
2. **Test retrieval** using the API health check
3. **Configure search parameters** (`k`, MMR, filters)
4. **Monitor performance** in production
5. **Set up backup schedule** (Qdrant Cloud does this automatically)

---

For integration with the Reppy RAG pipeline, see [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md).


from config import get_settings
import redis
import psycopg2

settings = get_settings()

# Test Redis
r = redis.from_url(settings.redis_url)
r.ping()
print("Redis connected")

# Test Postgres
conn = psycopg2.connect(settings.database_url)
conn.close()
print("Postgres connected")

print("All good! Phase 1 complete.")
import os
import time
import pytest
from app.cache import CacheManager, get_lawyer_list_cache_key, get_lawyer_detail_cache_key

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

@pytest.fixture
def redis_cache_workers():
    os.environ["REDIS_URL"] = REDIS_URL
    worker_1 = CacheManager(default_ttl=60)
    worker_2 = CacheManager(default_ttl=60)
    yield worker_1, worker_2
    # Cleanup test keys
    worker_1.clear()

def test_redis_multi_worker_shared_cache(redis_cache_workers):
    w1, w2 = redis_cache_workers
    assert w1._redis_available and w2._redis_available, "Redis backend must be connected!"

    # Worker 1 caches lawyer detail
    key = get_lawyer_detail_cache_key(101)
    w1.set(key, {"id": 101, "name": "Advocate Sharma", "rating": 4.8})

    # Worker 2 reads cached value across process boundary
    cached_val = w2.get(key)
    assert cached_val is not None
    assert cached_val["name"] == "Advocate Sharma"
    assert cached_val["rating"] == 4.8

def test_redis_cross_worker_invalidation_on_review(redis_cache_workers):
    w1, w2 = redis_cache_workers
    assert w1._redis_available and w2._redis_available

    list_key = get_lawyer_list_cache_key(city="Bangalore")
    detail_key = get_lawyer_detail_cache_key(101)

    # Worker 1 populates cache
    w1.set(list_key, [{"id": 101, "rating": 4.5}])
    w1.set(detail_key, {"id": 101, "rating": 4.5})

    assert w2.get(list_key) is not None
    assert w2.get(detail_key) is not None

    # Worker 2 processes a review and invalidates caches
    w2.invalidate_prefix("lawyers:list:")
    w2.invalidate_key(detail_key)

    # Worker 1 must immediately see the invalidation!
    assert w1.get(list_key) is None
    assert w1.get(detail_key) is None

def test_redis_ttl_expiration(redis_cache_workers):
    w1, w2 = redis_cache_workers
    key = "test:ttl:key"
    w1.set(key, "temporary_data", ttl=1)
    assert w2.get(key) == "temporary_data"

    time.sleep(1.2)
    assert w2.get(key) is None


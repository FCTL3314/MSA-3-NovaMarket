"""
Нагрузочный тест Rate Limiter (nginx-rate-limiter.conf).

    locust -f rate_limiter.py --host=http://localhost:8080 --web-port=8082

Веб- и мобильные пользователи приходят с одного IP и различаются заголовком Client-Type.
Каждый пользователь шлёт ~10 RPS, т.е. при 20 пользователях (10 web + 10 mobile)
нагрузка ~100 RPS на канал. Ожидаемый результат:
    web    — успешно ~50 RPS, остальное 429 Too Many Requests;
    mobile — успешно ~30 RPS, остальное 429 Too Many Requests.
"""
import logging
import time
from collections import Counter, defaultdict

from locust import HttpUser, constant_throughput, events, task

responses = defaultdict(Counter)
started_at = None


class ApiClient(HttpUser):
    abstract = True
    client_type = None
    wait_time = constant_throughput(10)

    @task
    def get_products(self):
        with self.client.get(
            "/api/products",
            headers={"Client-Type": self.client_type},
            name=f"/api/products [{self.client_type}]",
            catch_response=True,
        ) as response:
            responses[self.client_type][response.status_code] += 1
            if response.status_code == 429:
                response.failure(f"429 Too Many Requests: rate limit for {self.client_type}")
            elif response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")
            elif f"{self.client_type}_backend" not in response.text:
                response.failure("Response from unexpected backend")


class WebUser(ApiClient):
    client_type = "web"


class MobileUser(ApiClient):
    client_type = "mobile"


@events.test_start.add_listener
def on_test_start(**kwargs):
    global started_at
    started_at = time.time()
    responses.clear()


@events.test_stop.add_listener
def on_test_stop(**kwargs):
    if not started_at:
        return
    duration = time.time() - started_at
    logging.info("===== Rate Limiter summary (%.0f s) =====", duration)
    for client_type, by_status in responses.items():
        total = sum(by_status.values())
        ok = by_status.get(200, 0)
        limited = by_status.get(429, 0)
        logging.info(
            "%-6s total=%d (%.1f RPS) | 200 OK=%d (%.1f RPS) | 429 limited=%d (%.1f%%)",
            client_type,
            total,
            total / duration,
            ok,
            ok / duration,
            limited,
            100 * limited / total if total else 0,
        )

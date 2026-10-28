"""
Нагрузочный тест Circuit Breaker (nginx-circuit-breaker.conf).

    locust -f circuit_breaker.py --host=http://localhost:8080 --web-port=8082

Сценарий пользователя повторяется по кругу:
  1. healthy   — запросы к /logistics/fast: сервис отвечает, цепь замкнута (CLOSED);
  2. errors    — запросы к /logistics/error: сервис отвечает 503, после 5 ошибок NGINX
                 размыкает цепь (OPEN) и отвечает fallback, не обращаясь к сервису;
  3. open      — даже /logistics/fast в течение 30 c получает fallback;
  4. recovery  — через 30 c пробный запрос проходит, цепь снова замкнута;
  5. timeouts  — /logistics/slow отвечает за 5 c, прокси обрывает ожидание через 3 c,
                 после 5 таймаутов цепь снова размыкается и ответ приходит мгновенно.

Состояние определяется по заголовкам, которые выставляет NGINX:
  ответ сервиса, X-Upstream-Addr содержит 127.0.0.1:9090      -> CLOSED;
  X-Fallback, сервис вызывался, но упал / не ответил за 3 c   -> PRIMARY_FAILED (ошибка учтена);
  X-Fallback, сервис не вызывался                              -> OPEN (цепь разомкнута).
"""
import logging
import time

from locust import HttpUser, SequentialTaskSet, constant, task

PRIMARY = "127.0.0.1:9090"

log = logging.getLogger("circuit_breaker")
last_state = None


def circuit_state(response):
    primary_called = PRIMARY in response.headers.get("X-Upstream-Addr", "")
    if response.headers.get("X-Fallback"):
        return "PRIMARY_FAILED" if primary_called else "OPEN"
    return "CLOSED" if primary_called else "UNAVAILABLE"


class LogisticsScenario(SequentialTaskSet):
    def call(self, path, phase):
        global last_state
        started = time.monotonic()
        with self.client.get(f"/logistics/{path}", name=f"/logistics/{path}", catch_response=True) as response:
            elapsed = time.monotonic() - started
            state = circuit_state(response)
            log.info(
                "[%-8s] GET /logistics/%-5s -> %s in %.2fs | upstream=%s upstream_status=%s | %s",
                phase,
                path,
                response.status_code,
                elapsed,
                response.headers.get("X-Upstream-Addr", "-"),
                response.headers.get("X-Upstream-Status", "-"),
                state,
            )
            if state == "OPEN" and last_state != "OPEN":
                log.warning(">>> CIRCUIT BREAKER OPEN: logistics is not called, fallback is returned")
            if state == "CLOSED" and last_state in ("OPEN", "PRIMARY_FAILED"):
                log.warning(">>> CIRCUIT BREAKER CLOSED: logistics responds again, calls restored")
            last_state = state

            if state == "OPEN":
                response.failure("Circuit breaker OPEN: fallback without calling logistics")
            elif state == "PRIMARY_FAILED":
                response.failure(f"Logistics failed ({response.headers.get('X-Upstream-Status')}), fallback returned")
            elif state == "UNAVAILABLE":
                response.failure(f"No fallback, NGINX returned {response.status_code}")
            elif response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")

    @task
    def healthy(self):
        for _ in range(3):
            self.call("fast", "healthy")

    @task
    def errors(self):
        for _ in range(8):
            self.call("error", "errors")

    @task
    def open_circuit(self):
        for _ in range(3):
            self.call("fast", "open")

    @task
    def recovery(self):
        log.info("[recovery] waiting 31s for fail_timeout to expire...")
        time.sleep(31)
        for _ in range(3):
            self.call("fast", "recovery")

    @task
    def timeouts(self):
        for _ in range(7):
            self.call("slow", "timeouts")
        log.info("[timeouts] waiting 31s for fail_timeout to expire...")
        time.sleep(31)
        self.call("fast", "recovery")


class LogisticsUser(HttpUser):
    wait_time = constant(0.5)
    tasks = [LogisticsScenario]

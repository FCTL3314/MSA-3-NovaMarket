# MSA-3-NovaMarket

Проектная работа 3-го спринта: архитектура маркетплейса NovaMarket.

| Задание | Что внутри |
|---|---|
| [Task1](Task1) | EDA: контейнерная диаграмма C2 с микросервисами и потоками событий, реестр событий Saga-хореографии оформления заказа, sequence-диаграммы успешного и ошибочных сценариев |
| [Task2](Task2) | История покупок: обновлённая диаграмма C2 и ADR (CQRS + read-модель на событиях) |
| [Task3](Task3) | Kubernetes: Deployment, Service, HPA по памяти и по RPS (Prometheus + prometheus-adapter), скриншоты и логи масштабирования под нагрузкой Locust |
| [Task4](Task4) | NGINX: Rate Limiter по каналам (web 50 r/s, mobile 30 r/s) и Circuit Breaker для логистики, Locust-скрипты, скриншоты и логи срабатывания |

Диаграммы — PlantUML (C4-PlantUML), рядом с исходниками лежат отрендеренные PNG.

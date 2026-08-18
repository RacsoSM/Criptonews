# Criptonews

App Android que vigila las top criptomonedas por capitalización de mercado, genera señales técnicas de compra/venta y avisa por push notification cuando aparece una. El backend corre en la nube (no depende de que ninguna PC esté encendida) y actualiza los datos cada hora de forma automática.

## Cómo funciona

1. **Cada hora**, un job automatizado (GitHub Actions):
   - Refresca el top-N de monedas por capitalización de mercado (CoinGecko) que tengan par contra USDT en Binance.
   - Descarga las velas de 1h de cada moneda (Binance).
   - Calcula indicadores técnicos (RSI, cruce de EMAs, MACD, canal de Donchian) y un "entry score" de oportunidad de entrada.
   - Aplica la lógica de señales: abre o cierra posiciones simuladas y genera señales BUY/SELL.
   - Envía una push notification (Firebase) por cada señal nueva.
   - Guarda todo en la base de datos.
2. La app Android consulta la API en cualquier momento para mostrar el watchlist, el detalle de cada moneda (gráfico de velas + historial de entry score) y el historial de señales.

## Stack

### Backend (`backend/`)

| Componente | Uso |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | API REST que consume la app Android |
| [Uvicorn](https://www.uvicorn.org/) | Servidor ASGI que corre la API |
| [SQLAlchemy 2.0](https://www.sqlalchemy.org/) | ORM — mismo código sirve para SQLite (dev/tests) y Postgres (producción) |
| [psycopg2-binary](https://www.psycopg.org/) | Driver de Postgres para producción |
| [httpx](https://www.python-httpx.org/) | Cliente HTTP hacia CoinGecko y Binance |
| [pandas](https://pandas.pydata.org/) / [numpy](https://numpy.org/) | Cálculo de indicadores técnicos sobre las velas |
| [firebase-admin](https://firebase.google.com/docs/admin/setup) | Envío de push notifications (FCM) |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Configuración vía variables de entorno |
| [pytest](https://docs.pytest.org/) / pytest-mock | Suite de tests |

Módulos principales:
- `app/market_data.py` — integración con CoinGecko (ranking) y Binance (velas, precios).
- `app/indicators.py` / `app/signal_engine.py` — indicadores técnicos y lógica de señales BUY/SELL.
- `app/entry_score.py` — score de oportunidad de entrada por moneda.
- `app/positions_service.py` — apertura/cierre de posiciones simuladas ligadas a las señales.
- `app/notifications.py` — envío de push notifications vía FCM.
- `app/scheduler.py` — orquesta un ciclo completo (`run_cycle()`): es la función que corre cada hora.
- `scripts/run_cycle.py` — punto de entrada standalone que invoca GitHub Actions (ver más abajo).
- `app/routers/` — endpoints de la API: `coins`, `signals`, `candles`, `entry_score_history`, `devices` (registro de tokens FCM), `status` (hora del último ciclo).

### App Android (`android/`)

| Componente | Uso |
|---|---|
| [Kotlin](https://kotlinlang.org/) + [Jetpack Compose](https://developer.android.com/jetpack/compose) | UI declarativa |
| Material 3 | Sistema de diseño |
| [Retrofit](https://square.github.io/retrofit/) + [OkHttp](https://square.github.io/okhttp/) | Cliente HTTP hacia el backend |
| [kotlinx.serialization](https://kotlinlang.org/docs/serialization.html) | Parseo JSON |
| [Coil](https://coil-kt.github.io/coil/) | Carga de íconos de monedas |
| [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging) | Recepción de push notifications |
| Navigation Compose + Coroutines | Navegación entre pantallas y llamadas async a la API |

Pantallas principales:
- **Watchlist**: lista de las top monedas con su entry score y ranking.
- **Detalle de moneda**: gráfico de velas + evolución del entry score.
- **Historial**: señales BUY/SELL generadas.

### Infraestructura

| Servicio | Rol |
|---|---|
| [Render](https://render.com/) | Hostea la API FastAPI con una URL pública (plan free) |
| [Neon](https://neon.tech/) | Postgres administrado, base de datos de producción (plan free) |
| [GitHub Actions](https://docs.github.com/actions) | Cron hourly (`.github/workflows/hourly-cycle.yml`) que corre `scripts/run_cycle.py` — reemplaza la necesidad de un servidor siempre encendido |
| [Firebase](https://firebase.google.com/) | Push notifications a los dispositivos Android |

Guía completa de despliegue paso a paso: [docs/deployment.md](docs/deployment.md).

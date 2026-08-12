# Crypto Signal Notifier — Design Spec

**Fecha**: 2026-08-12
**Estado**: Aprobado para pasar a plan de implementación
**Uso**: Personal (un solo usuario, un solo dispositivo Android)

## 1. Propósito

App que monitorea el top 30 de criptomonedas por capitalización de mercado y envía notificaciones push automáticas de "compra" y "venta" basadas en un motor de señales técnicas, para una estrategia de holdeo (comprar y mantener hasta que el sistema indique venta).

## 2. Arquitectura general

```
Binance API (velas/precios)
        │
        ▼
Backend Python (VPS/cloud) ── job cada 1h, alineado al cierre de vela
   ├─ Refresca top 30 por market cap
   ├─ Descarga velas OHLC 1h
   ├─ Calcula indicadores (RSI, EMA cross, MACD, Donchian 20)
   ├─ Evalúa señales y gestiona posiciones abiertas
   ├─ Persiste en base de datos (coins, candles, signals, positions)
   └─ Envía push vía FCM cuando corresponde
        │
        ▼
App Android nativa (Kotlin) ── cliente
   ├─ Recibe y muestra notificaciones push
   ├─ Watchlist / posiciones abiertas
   ├─ Historial de señales
   └─ Detalle + gráfico por moneda
```

- El backend es la única fuente de verdad (cálculo e histórico). La app Android no realiza cálculos, solo consume la API y muestra datos.
- Sin login ni multiusuario: la app se registra una vez contra el backend con su token FCM.

## 3. Motor de señales (backend)

### Universo y datos
- **Universo**: top 30 monedas por market cap, refrescado periódicamente (para reflejar entradas/salidas del ranking).
- **Fuente de datos**: Binance API (velas OHLC públicas, sin necesidad de API key).
- **Timeframe**: velas de 1 hora.

### Indicadores
- **RSI (14)**: <30 sobreventa (dirección compra), >70 sobrecompra (dirección venta).
- **EMA cross (9/21)**: cruce alcista → compra; cruce bajista → venta.
- **MACD**: cruce de línea MACD sobre/bajo línea de señal.
- **Soporte/Resistencia (Donchian 20)**: ruptura del máximo de 20 velas → compra; ruptura del mínimo de 20 velas → venta.

### Regla de decisión
- Señal de compra o venta se genera si **al menos 3 de los 4 indicadores** coinciden en la misma dirección en el mismo ciclo.

### Gestión de posiciones
- Una señal de **compra** abre una posición (moneda, precio de entrada, timestamp) si no hay ya una posición abierta para esa moneda.
- Al abrir la posición se calculan, solo como referencia informativa:
  - **Stop Loss** = precio de entrada − 1.5 × ATR
  - **Take Profit** = precio de entrada + 3 × ATR
- Mientras una moneda tiene posición abierta, el motor **no genera nuevas señales de compra** para ella.
- La **venta** solo se dispara cuando el motor técnico marca señal de venta (3 de 4 en dirección venta) para una moneda con posición abierta. TP/SL **no** disparan venta automática — son solo referencia visual en la app/notificación.
- Al dispararse la venta, la posición se marca como cerrada.

### Anti-spam
- No se reenvía la misma señal/dirección para una moneda si la condición no ha cambiado desde la última notificación enviada.

### Persistencia
- Cada señal generada (moneda, tipo, precio, TP, SL, indicadores que la dispararon, timestamp) se guarda en base de datos.
- Estado de posiciones (abierta/cerrada, entrada, TP, SL) se mantiene actualizado.

## 4. App Android (Kotlin, nativa)

- **Pantalla principal — Watchlist/Posiciones**: las 30 monedas con su estado (sin posición / posición abierta). Si hay posición abierta: precio de entrada, TP, SL, % de ganancia/pérdida actual.
- **Pantalla de Historial**: lista cronológica de señales pasadas (moneda, tipo, precio, fecha, indicadores que la dispararon).
- **Pantalla de Detalle/Gráfico por moneda**: velas (últimas ~100 del timeframe 1h) con EMA 9/21 superpuestas y niveles de soporte/resistencia; sub-gráficos de RSI y MACD. Si hay posición abierta, se dibujan líneas de entrada/TP/SL.
- **Notificaciones push (FCM)**: al tocar la notificación, navega directo al detalle de esa moneda.
- **Registro**: la app registra su token FCM contra el backend una sola vez (sin cuentas de usuario).

## 5. Integración y datos

- **API backend (REST, FastAPI)**:
  - Consulta de watchlist/posiciones actuales.
  - Consulta de historial de señales.
  - Consulta de velas + indicadores por moneda (para el gráfico).
  - Registro de token FCM del dispositivo.
- **Base de datos**: SQLite o Postgres ligero. Tablas: `coins`, `candles` (o cache de velas), `signals`, `positions`.
- **Job programado**: corre cada hora, alineado al cierre de vela 1h. Secuencia: refresca top 30 → descarga velas → calcula indicadores → evalúa señales/actualiza posiciones → notifica vía FCM.

## 6. Manejo de errores

- Si Binance falla o responde incompleto para una moneda, esa moneda se omite en el ciclo actual (no se genera señal falsa) y se reintenta en el siguiente ciclo.
- Si falla el envío del push FCM, la señal queda igualmente persistida en base de datos; la app la refleja en el historial al abrir aunque el push no haya llegado.
- Logs básicos del job (monedas procesadas, señales generadas, errores) para depuración.

## 7. Fuera de alcance (MVP)

- Multiusuario / login / cuentas.
- Publicación en Play Store (uso personal, instalación directa del APK).
- Indicadores adicionales (Bollinger Bands, volumen relativo) — quedan para una iteración futura.
- Múltiples timeframes configurables — se usa 1h fijo.
- Cierre automático de posición por TP/SL — solo referencia informativa en esta versión.

## 8. Stack técnico

- **Backend**: Python, FastAPI, APScheduler (o cron) para el job programado, pandas-ta (o similar) para indicadores técnicos.
- **Notificaciones**: Firebase Cloud Messaging (FCM).
- **App**: Kotlin nativo, Jetpack Compose.
- **Base de datos**: SQLite o Postgres.

# Android App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Android app (Kotlin, Jetpack Compose) that consumes the already-implemented backend API to show the top-30 watchlist/open positions, signal history, and a per-coin candle+indicator chart, and receives FCM push notifications for buy/sell signals.

**Architecture:** A single-module Android app with a thin manual-DI container (`AppContainer`, no Hilt — YAGNI for a personal single-user app). Retrofit + kotlinx.serialization talk to the backend's 4 REST endpoints. Three Compose screens (Watchlist, History, Detail) share one `UiState<T>` pattern, each backed by a `ViewModel` exposing a `StateFlow`. The candle chart is hand-drawn on a Compose `Canvas` using pure, unit-tested coordinate-mapping functions — no external charting library. `FirebaseMessagingService` registers the device token with the backend and turns incoming pushes into system notifications that deep-link to the relevant coin's Detail screen.

**Tech Stack:** Kotlin 2.0.21, Jetpack Compose + Material3, Navigation-Compose, Retrofit 2 + OkHttp + kotlinx.serialization, Firebase Cloud Messaging, JUnit4 + kotlinx-coroutines-test + OkHttp MockWebServer for JVM unit tests, Gradle 8.9 / AGP 8.6.1.

## Global Constraints

- **Project location:** the Android Studio project root is `android/` (sibling to the existing `backend/`), with a single app module at `android/app/`.
- **Package / applicationId:** `com.criptonews.app`.
- **SDK levels:** `minSdk = 26`, `compileSdk = 36`, `targetSdk = 36` (matches the Android SDK platform already installed on this machine — do not raise `compileSdk` past what's installed without first confirming a newer platform is present).
- **Toolchain already verified present on this machine (do not re-derive, just use it):** JDK 21 at `C:/Program Files/Eclipse Adoptium/jdk-21.0.12.8-hotspot`; Android SDK at `C:/Users/SISTEMAS-03/AppData/Local/Android/Sdk` (platforms `android-36`/`android-37.0`, build-tools `35.0.0`/`36.0.0`, `platform-tools/adb.exe`); a cached Gradle 8.9 distribution at `C:/Users/SISTEMAS-03/.gradle/wrapper/dists/gradle-8.9-bin/90cnw93cvbtalezasaz0blq0a/gradle-8.9/bin/gradle.bat` (used once, in Task 1, to bootstrap the project's own `gradlew`); an existing emulator AVD named `TabletPrueba1` (used in Task 12's manual verification — do not create a new AVD).
- **No Hilt/Dagger, no Room, no multi-module split** — a personal single-user app with 4 read-mostly endpoints does not need them (YAGNI). Dependencies are wired through one `AppContainer` singleton held by the `Application` subclass.
- **Backend base URL:** hardcoded via `BuildConfig.BASE_URL`, defaulting to `"http://10.0.2.2:8000/"` — `10.0.2.2` is the Android emulator's fixed alias for the host machine's `127.0.0.1`, required because the emulator cannot reach the host's `localhost` directly. Before installing on a physical device for real daily use, this must be changed to the actual backend server's address (VPS IP/domain) and rebuilt — no in-app settings screen (per design decision).
- **Firebase is optional at build time.** `android/app/google-services.json` is a user-provided file (downloaded from a Firebase console project named with applicationId `com.criptonews.app`, Cloud Messaging enabled) and is **not** committed to the repo (gitignored). `app/build.gradle.kts` applies the `com.google.gms.google-services` plugin **only if that file exists on disk**, so every task except Task 11 (and Task 12's FCM sub-step) builds and tests cleanly with zero Firebase setup.
- **Testing scope:** JVM unit tests only (DTO (de)serialization, `CryptoRepository` via OkHttp `MockWebServer`, `ViewModel`s via a hand-written `FakeApiService`, and the chart's pure coordinate-math functions). Compose screens themselves are not unit- or instrumentation-tested in this plan — Task 12 is a manual verification pass on the `TabletPrueba1` emulator, mirroring how the backend plan's Task 12 closed with a live manual check.
- **Backend JSON contract — mirror these exactly, they are already implemented and frozen (`backend/app/schemas.py`, `backend/app/routers/*.py`):**
  - `GET /coins` → array of `{"symbol": str, "name": str, "rank": int, "has_open_position": bool, "entry_price": float|null, "stop_loss": float|null, "take_profit": float|null}`. Includes coins that dropped out of the top-30 ranking as long as they still hold an open position.
  - `GET /signals?coin_symbol=<optional>` → array of `{"id": int, "coin_symbol": str, "signal_type": "BUY"|"SELL", "price": float, "rsi_vote": "buy"|"sell"|null, "ema_cross_vote": "buy"|"sell"|null, "macd_vote": "buy"|"sell"|null, "donchian_vote": "buy"|"sell"|null, "created_at": ISO-8601 string with explicit UTC offset (e.g. `"2026-08-12T19:00:52.306234+00:00"`)}`, newest first.
  - `GET /coins/{symbol}/candles?limit=100` (default `limit=100`) → array of `{"open_time": int (ms epoch), "open": float, "high": float, "low": float, "close": float, "volume": float, "ema_9": float|null, "ema_21": float|null, "rsi_14": float|null, "macd_line": float|null, "macd_signal": float|null, "donchian_upper": float|null, "donchian_lower": float|null}`; returns HTTP 502 if the backend's own upstream data source failed for that symbol.
  - `POST /devices` body `{"token": str}` → `201` `{"status": "registered"}` on success; idempotent (safe to call every app start / every token refresh).

---

## File Structure

```
android/
  settings.gradle.kts
  build.gradle.kts
  gradle.properties
  .gitignore
  gradle/libs.versions.toml
  gradle/wrapper/gradle-wrapper.properties   # generated by Task 1's wrapper bootstrap
  gradlew, gradlew.bat                        # generated by Task 1's wrapper bootstrap
  app/
    build.gradle.kts
    src/main/
      AndroidManifest.xml
      res/
        values/strings.xml
        values/colors.xml
        values/themes.xml
        drawable/ic_launcher_foreground.xml
        mipmap-anydpi-v26/ic_launcher.xml
      java/com/criptonews/app/
        CriptoNewsApp.kt              # Application subclass, holds AppContainer
        MainActivity.kt               # single Activity, hosts the NavHost
        AppContainer.kt               # manual DI: ApiService + CryptoRepository singletons
        network/
          ApiService.kt               # Retrofit interface, all 4 endpoints
          NetworkModule.kt            # Retrofit/OkHttp/Json construction
          dto/CoinDto.kt
          dto/SignalDto.kt
          dto/CandleDto.kt
          dto/DeviceTokenRequest.kt
        data/CryptoRepository.kt      # thin Result<T>-wrapping layer over ApiService
        ui/
          UiState.kt                  # shared Loading/Success/Error sealed interface
          theme/Color.kt, Theme.kt, Type.kt
          watchlist/WatchlistViewModel.kt, WatchlistScreen.kt
          history/HistoryViewModel.kt, HistoryScreen.kt
          detail/ChartMath.kt         # pure coordinate-mapping functions (heavily tested)
          detail/CandleChart.kt       # Canvas composable using ChartMath
          detail/CoinDetailViewModel.kt, CoinDetailScreen.kt
          navigation/Destinations.kt, CriptoNewsNavHost.kt
        notifications/
          NotificationHelper.kt                     # channel creation + notification building
          CriptoNewsFirebaseMessagingService.kt      # onNewToken / onMessageReceived
    src/test/java/com/criptonews/app/
      SanityTest.kt
      util/MainDispatcherRule.kt
      network/dto/CoinDtoTest.kt, SignalDtoTest.kt, CandleDtoTest.kt
      data/CryptoRepositoryTest.kt
      ui/watchlist/WatchlistViewModelTest.kt
      ui/history/HistoryViewModelTest.kt
      ui/detail/ChartMathTest.kt
      ui/detail/CoinDetailViewModelTest.kt
```

---

### Task 1: Project scaffolding — Gradle project, manifest, theme, minimal app that builds and tests

**Files:**
- Create: `android/settings.gradle.kts`, `android/build.gradle.kts`, `android/gradle.properties`, `android/.gitignore`, `android/gradle/libs.versions.toml`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/res/values/strings.xml`, `colors.xml`, `themes.xml`
- Create: `android/app/src/main/res/drawable/ic_launcher_foreground.xml`
- Create: `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`
- Create: `android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt`
- Create: `android/app/src/main/java/com/criptonews/app/MainActivity.kt`
- Create: `android/app/src/main/java/com/criptonews/app/ui/theme/Color.kt`, `Theme.kt`, `Type.kt`
- Test: `android/app/src/test/java/com/criptonews/app/SanityTest.kt`

**Interfaces:**
- Produces: a buildable, testable Gradle project (`./gradlew test` and `./gradlew assembleDebug` both succeed); `BuildConfig.BASE_URL` available to all later tasks; `CriptoNewsTheme` composable available to all screens; `CriptoNewsApp` (empty `Application` subclass, extended by Task 3 and Task 11).

- [ ] **Step 1: Create the directory and version catalog**

`android/gradle/libs.versions.toml`:
```toml
[versions]
agp = "8.6.1"
kotlin = "2.0.21"
coreKtx = "1.13.1"
activityCompose = "1.9.3"
composeBom = "2024.10.01"
lifecycle = "2.8.6"
navigationCompose = "2.8.3"
kotlinxSerializationJson = "1.7.3"
kotlinxCoroutines = "1.9.0"
retrofit = "2.11.0"
retrofitKotlinxSerializationConverter = "1.0.0"
okhttp = "4.12.0"
firebaseBom = "33.5.1"
googleServices = "4.4.2"
junit = "4.13.2"

[libraries]
androidx-core-ktx = { group = "androidx.core", name = "core-ktx", version.ref = "coreKtx" }
androidx-activity-compose = { group = "androidx.activity", name = "activity-compose", version.ref = "activityCompose" }
androidx-compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "composeBom" }
androidx-ui = { group = "androidx.compose.ui", name = "ui" }
androidx-ui-graphics = { group = "androidx.compose.ui", name = "ui-graphics" }
androidx-ui-tooling = { group = "androidx.compose.ui", name = "ui-tooling" }
androidx-ui-tooling-preview = { group = "androidx.compose.ui", name = "ui-tooling-preview" }
androidx-material3 = { group = "androidx.compose.material3", name = "material3" }
androidx-lifecycle-viewmodel-compose = { group = "androidx.lifecycle", name = "lifecycle-viewmodel-compose", version.ref = "lifecycle" }
androidx-lifecycle-runtime-compose = { group = "androidx.lifecycle", name = "lifecycle-runtime-compose", version.ref = "lifecycle" }
androidx-navigation-compose = { group = "androidx.navigation", name = "navigation-compose", version.ref = "navigationCompose" }
kotlinx-serialization-json = { group = "org.jetbrains.kotlinx", name = "kotlinx-serialization-json", version.ref = "kotlinxSerializationJson" }
kotlinx-coroutines-android = { group = "org.jetbrains.kotlinx", name = "kotlinx-coroutines-android", version.ref = "kotlinxCoroutines" }
kotlinx-coroutines-test = { group = "org.jetbrains.kotlinx", name = "kotlinx-coroutines-test", version.ref = "kotlinxCoroutines" }
retrofit = { group = "com.squareup.retrofit2", name = "retrofit", version.ref = "retrofit" }
retrofit-kotlinx-serialization-converter = { group = "com.jakewharton.retrofit", name = "retrofit2-kotlinx-serialization-converter", version.ref = "retrofitKotlinxSerializationConverter" }
okhttp = { group = "com.squareup.okhttp3", name = "okhttp", version.ref = "okhttp" }
okhttp-logging-interceptor = { group = "com.squareup.okhttp3", name = "logging-interceptor", version.ref = "okhttp" }
okhttp-mockwebserver = { group = "com.squareup.okhttp3", name = "mockwebserver", version.ref = "okhttp" }
firebase-bom = { group = "com.google.firebase", name = "firebase-bom", version.ref = "firebaseBom" }
firebase-messaging-ktx = { group = "com.google.firebase", name = "firebase-messaging-ktx" }
junit = { group = "junit", name = "junit", version.ref = "junit" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
```

`android/settings.gradle.kts`:
```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "CriptoNews"
include(":app")
```

`android/build.gradle.kts`:
```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
}
```

`android/gradle.properties`:
```
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.nonTransitiveRClass=true
kotlin.code.style=official
```

`android/.gitignore`:
```
*.iml
.gradle/
/local.properties
.idea/
.DS_Store
/build
/captures
.externalNativeBuild
.cxx
app/google-services.json
```

- [ ] **Step 2: Bootstrap the Gradle wrapper**

Run this once from `android/` using the cached Gradle 8.9 distribution already on this machine (do not use a system `gradle` — none is installed):

```bash
"C:/Users/SISTEMAS-03/.gradle/wrapper/dists/gradle-8.9-bin/90cnw93cvbtalezasaz0blq0a/gradle-8.9/bin/gradle.bat" wrapper --gradle-version 8.9
```

Expected: creates `android/gradlew`, `android/gradlew.bat`, `android/gradle/wrapper/gradle-wrapper.properties`, `android/gradle/wrapper/gradle-wrapper.jar`.

If that exact path doesn't exist on the machine running this step, locate the cached distribution with `ls ~/.gradle/wrapper/dists` (any `gradle-8.9-*` or newer 8.x folder works — adjust `--gradle-version` to match) and use that `bin/gradle.bat` instead.

- [ ] **Step 3: Write the app module build file**

`android/app/build.gradle.kts`:
```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

// Firebase is optional at build time: the google-services plugin is only
// applied if the user has dropped their own google-services.json in place
// (see Task 11). Every other task builds and tests without it.
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
}

android {
    namespace = "com.criptonews.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.criptonews.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        buildConfigField("String", "BASE_URL", "\"http://10.0.2.2:8000/\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    debugImplementation(libs.androidx.ui.tooling)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.retrofit)
    implementation(libs.retrofit.kotlinx.serialization.converter)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging.interceptor)
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging.ktx)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)
}
```

- [ ] **Step 4: Write the manifest and resources**

`android/app/src/main/AndroidManifest.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

    <application
        android:name=".CriptoNewsApp"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/Theme.CriptoNews"
        android:usesCleartextTraffic="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

`android/app/src/main/res/values/strings.xml`:
```xml
<resources>
    <string name="app_name">CriptoNews</string>
</resources>
```

`android/app/src/main/res/values/colors.xml`:
```xml
<resources>
    <color name="ic_launcher_background">#1B5E20</color>
</resources>
```

`android/app/src/main/res/values/themes.xml`:
```xml
<resources>
    <style name="Theme.CriptoNews" parent="Theme.Material3.DayNight.NoActionBar" />
</resources>
```

`android/app/src/main/res/drawable/ic_launcher_foreground.xml`:
```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M54,20L82,74L26,74Z" />
</vector>
```

`android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
```

- [ ] **Step 5: Write the theme and minimal app/activity**

`android/app/src/main/java/com/criptonews/app/ui/theme/Color.kt`:
```kotlin
package com.criptonews.app.ui.theme

import androidx.compose.ui.graphics.Color

val BuyGreen = Color(0xFF2E7D32)
val SellRed = Color(0xFFC62828)
val NeutralGray = Color(0xFF757575)
```

`android/app/src/main/java/com/criptonews/app/ui/theme/Type.kt`:
```kotlin
package com.criptonews.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.sp

val CriptoNewsTypography = Typography(
    bodyLarge = TextStyle(fontSize = 16.sp),
    bodyMedium = TextStyle(fontSize = 14.sp),
    titleLarge = TextStyle(fontSize = 22.sp),
)
```

`android/app/src/main/java/com/criptonews/app/ui/theme/Theme.kt`:
```kotlin
package com.criptonews.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(primary = BuyGreen, error = SellRed)
private val DarkColors = darkColorScheme(primary = BuyGreen, error = SellRed)

@Composable
fun CriptoNewsTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, typography = CriptoNewsTypography, content = content)
}
```

`android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt`:
```kotlin
package com.criptonews.app

import android.app.Application

class CriptoNewsApp : Application()
```

`android/app/src/main/java/com/criptonews/app/MainActivity.kt`:
```kotlin
package com.criptonews.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import com.criptonews.app.ui.theme.CriptoNewsTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CriptoNewsTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { padding ->
                    Text("CriptoNews", modifier = Modifier.padding(padding))
                }
            }
        }
    }
}
```

- [ ] **Step 6: Write a sanity test to prove the JVM test pipeline works**

`android/app/src/test/java/com/criptonews/app/SanityTest.kt`:
```kotlin
package com.criptonews.app

import org.junit.Assert.assertEquals
import org.junit.Test

class SanityTest {
    @Test
    fun `test infrastructure works`() {
        assertEquals(4, 2 + 2)
    }
}
```

- [ ] **Step 7: Run the test task to verify the whole pipeline works**

Run (from `android/`): `./gradlew test`
Expected: `BUILD SUCCESSFUL`, 1 test passed (`SanityTest`).

- [ ] **Step 8: Run the assemble task to verify the app itself compiles**

Run (from `android/`): `./gradlew assembleDebug`
Expected: `BUILD SUCCESSFUL`, produces `android/app/build/outputs/apk/debug/app-debug.apk`.

- [ ] **Step 9: Commit**

```bash
git add android/
git commit -m "feat(android): add project scaffolding, manifest, and theme"
```

---

### Task 2: Network DTOs

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/network/dto/CoinDto.kt`, `SignalDto.kt`, `CandleDto.kt`, `DeviceTokenRequest.kt`
- Test: `android/app/src/test/java/com/criptonews/app/network/dto/CoinDtoTest.kt`, `SignalDtoTest.kt`, `CandleDtoTest.kt`

**Interfaces:**
- Consumes: nothing (pure `@Serializable` data classes).
- Produces: `CoinDto`, `SignalDto`, `CandleDto`, `DeviceTokenRequest` — exact field names/types per the Global Constraints JSON contract. Used by `ApiService` (Task 3) and every `ViewModel` (Tasks 4, 6, 8).

- [ ] **Step 1: Write the failing tests**

```kotlin
// android/app/src/test/java/com/criptonews/app/network/dto/CoinDtoTest.kt
package com.criptonews.app.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CoinDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `decodes a coin with an open position`() {
        val raw = """
            {"symbol":"BTCUSDT","name":"Bitcoin","rank":1,"has_open_position":true,
             "entry_price":60000.0,"stop_loss":57000.0,"take_profit":66000.0}
        """.trimIndent()

        val coin = json.decodeFromString<CoinDto>(raw)

        assertEquals("BTCUSDT", coin.symbol)
        assertEquals(1, coin.rank)
        assertEquals(true, coin.hasOpenPosition)
        assertEquals(60000.0, coin.entryPrice)
    }

    @Test
    fun `decodes a coin with no open position and null fields`() {
        val raw = """{"symbol":"ETHUSDT","name":"Ethereum","rank":2,"has_open_position":false}"""

        val coin = json.decodeFromString<CoinDto>(raw)

        assertEquals(false, coin.hasOpenPosition)
        assertNull(coin.entryPrice)
        assertNull(coin.stopLoss)
        assertNull(coin.takeProfit)
    }
}
```

```kotlin
// android/app/src/test/java/com/criptonews/app/network/dto/SignalDtoTest.kt
package com.criptonews.app.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test

class SignalDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `decodes a signal with all indicator votes and a UTC-offset timestamp`() {
        val raw = """
            {"id":1,"coin_symbol":"BTCUSDT","signal_type":"BUY","price":60000.0,
             "rsi_vote":"buy","ema_cross_vote":"buy","macd_vote":"buy","donchian_vote":null,
             "created_at":"2026-08-12T19:00:52.306234+00:00"}
        """.trimIndent()

        val signal = json.decodeFromString<SignalDto>(raw)

        assertEquals("BUY", signal.signalType)
        assertEquals("buy", signal.rsiVote)
        assertEquals(null, signal.donchianVote)
        assertEquals("2026-08-12T19:00:52.306234+00:00", signal.createdAt)
    }
}
```

```kotlin
// android/app/src/test/java/com/criptonews/app/network/dto/CandleDtoTest.kt
package com.criptonews.app.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CandleDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `decodes a candle with populated indicators`() {
        val raw = """
            {"open_time":1700000000000,"open":60000.0,"high":60500.0,"low":59800.0,
             "close":60300.0,"volume":123.45,"ema_9":60100.0,"ema_21":59900.0,
             "rsi_14":55.2,"macd_line":10.5,"macd_signal":8.2,
             "donchian_upper":61000.0,"donchian_lower":59000.0}
        """.trimIndent()

        val candle = json.decodeFromString<CandleDto>(raw)

        assertEquals(1700000000000L, candle.openTime)
        assertEquals(60300.0, candle.close)
        assertEquals(55.2, candle.rsi14)
    }

    @Test
    fun `decodes an early candle with null indicators, not a crash`() {
        val raw = """
            {"open_time":1700000000000,"open":60000.0,"high":60500.0,"low":59800.0,
             "close":60300.0,"volume":123.45,"ema_9":null,"ema_21":null,
             "rsi_14":null,"macd_line":60.0,"macd_signal":60.0,
             "donchian_upper":null,"donchian_lower":null}
        """.trimIndent()

        val candle = json.decodeFromString<CandleDto>(raw)

        assertNull(candle.ema9)
        assertNull(candle.rsi14)
        assertNull(candle.donchianUpper)
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./gradlew test --tests "com.criptonews.app.network.dto.*"`
Expected: FAIL with `Unresolved reference: CoinDto` (and similarly for `SignalDto`/`CandleDto`).

- [ ] **Step 3: Write the DTOs**

```kotlin
// android/app/src/main/java/com/criptonews/app/network/dto/CoinDto.kt
package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CoinDto(
    val symbol: String,
    val name: String,
    val rank: Int,
    @SerialName("has_open_position") val hasOpenPosition: Boolean,
    @SerialName("entry_price") val entryPrice: Double? = null,
    @SerialName("stop_loss") val stopLoss: Double? = null,
    @SerialName("take_profit") val takeProfit: Double? = null,
)
```

```kotlin
// android/app/src/main/java/com/criptonews/app/network/dto/SignalDto.kt
package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SignalDto(
    val id: Int,
    @SerialName("coin_symbol") val coinSymbol: String,
    @SerialName("signal_type") val signalType: String,
    val price: Double,
    @SerialName("rsi_vote") val rsiVote: String? = null,
    @SerialName("ema_cross_vote") val emaCrossVote: String? = null,
    @SerialName("macd_vote") val macdVote: String? = null,
    @SerialName("donchian_vote") val donchianVote: String? = null,
    @SerialName("created_at") val createdAt: String,
)
```

```kotlin
// android/app/src/main/java/com/criptonews/app/network/dto/CandleDto.kt
package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CandleDto(
    @SerialName("open_time") val openTime: Long,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val volume: Double,
    @SerialName("ema_9") val ema9: Double? = null,
    @SerialName("ema_21") val ema21: Double? = null,
    @SerialName("rsi_14") val rsi14: Double? = null,
    @SerialName("macd_line") val macdLine: Double? = null,
    @SerialName("macd_signal") val macdSignal: Double? = null,
    @SerialName("donchian_upper") val donchianUpper: Double? = null,
    @SerialName("donchian_lower") val donchianLower: Double? = null,
)
```

```kotlin
// android/app/src/main/java/com/criptonews/app/network/dto/DeviceTokenRequest.kt
package com.criptonews.app.network.dto

import kotlinx.serialization.Serializable

@Serializable
data class DeviceTokenRequest(val token: String)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./gradlew test --tests "com.criptonews.app.network.dto.*"`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/network/dto android/app/src/test/java/com/criptonews/app/network/dto
git commit -m "feat(android): add network DTOs mirroring the backend JSON contract"
```

---

### Task 3: ApiService, NetworkModule, CryptoRepository, AppContainer

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/network/ApiService.kt`, `NetworkModule.kt`
- Create: `android/app/src/main/java/com/criptonews/app/data/CryptoRepository.kt`
- Create: `android/app/src/main/java/com/criptonews/app/AppContainer.kt`
- Modify: `android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt`
- Test: `android/app/src/test/java/com/criptonews/app/data/CryptoRepositoryTest.kt`

**Interfaces:**
- Consumes: `CoinDto`, `SignalDto`, `CandleDto`, `DeviceTokenRequest` (Task 2); `BuildConfig.BASE_URL` (Task 1).
- Produces: `ApiService` interface (4 suspend functions matching the JSON contract); `NetworkModule.createApiService(baseUrl: String = BuildConfig.BASE_URL): ApiService`; `CryptoRepository(apiService: ApiService)` with `suspend fun getCoins(): Result<List<CoinDto>>`, `suspend fun getSignals(coinSymbol: String? = null): Result<List<SignalDto>>`, `suspend fun getCandles(symbol: String, limit: Int = 100): Result<List<CandleDto>>`, `suspend fun registerDevice(token: String): Result<Unit>`; `AppContainer` exposing a `val repository: CryptoRepository`; `CriptoNewsApp.container: AppContainer` (lazily constructed). Used by every `ViewModel` (Tasks 4, 6, 8) and by Task 11's FCM service.

- [ ] **Step 1: Write ApiService and NetworkModule**

```kotlin
// android/app/src/main/java/com/criptonews/app/network/ApiService.kt
package com.criptonews.app.network

import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.network.dto.DeviceTokenRequest
import com.criptonews.app.network.dto.SignalDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @GET("coins")
    suspend fun getCoins(): List<CoinDto>

    @GET("signals")
    suspend fun getSignals(@Query("coin_symbol") coinSymbol: String? = null): List<SignalDto>

    @GET("coins/{symbol}/candles")
    suspend fun getCandles(
        @Path("symbol") symbol: String,
        @Query("limit") limit: Int = 100,
    ): List<CandleDto>

    @POST("devices")
    suspend fun registerDevice(@Body request: DeviceTokenRequest)
}
```

```kotlin
// android/app/src/main/java/com/criptonews/app/network/NetworkModule.kt
package com.criptonews.app.network

import com.criptonews.app.BuildConfig
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

object NetworkModule {
    private val json = Json { ignoreUnknownKeys = true }

    fun createApiService(baseUrl: String = BuildConfig.BASE_URL): ApiService {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }
        val client = OkHttpClient.Builder().addInterceptor(logging).build()
        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
        return retrofit.create(ApiService::class.java)
    }
}
```

- [ ] **Step 2: Write the failing test for CryptoRepository**

```kotlin
// android/app/src/test/java/com/criptonews/app/data/CryptoRepositoryTest.kt
package com.criptonews.app.data

import com.criptonews.app.network.NetworkModule
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class CryptoRepositoryTest {
    private lateinit var server: MockWebServer
    private lateinit var repository: CryptoRepository

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        val apiService = NetworkModule.createApiService(baseUrl = server.url("/").toString())
        repository = CryptoRepository(apiService)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun `getCoins returns parsed list on success`() = runTest {
        server.enqueue(
            MockResponse().setBody(
                """[{"symbol":"BTCUSDT","name":"Bitcoin","rank":1,"has_open_position":false}]"""
            ).setHeader("Content-Type", "application/json")
        )

        val result = repository.getCoins()

        assertTrue(result.isSuccess)
        assertEquals("BTCUSDT", result.getOrThrow().first().symbol)
    }

    @Test
    fun `getCandles returns failure on a 502 response`() = runTest {
        server.enqueue(MockResponse().setResponseCode(502))

        val result = repository.getCandles("BTCUSDT")

        assertTrue(result.isFailure)
    }

    @Test
    fun `registerDevice succeeds on 201`() = runTest {
        server.enqueue(MockResponse().setResponseCode(201).setBody("""{"status":"registered"}"""))

        val result = repository.registerDevice("device-token-abc")

        assertTrue(result.isSuccess)
        val request = server.takeRequest()
        assertEquals("/devices", request.path)
        assertTrue(request.body.readUtf8().contains("device-token-abc"))
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `./gradlew test --tests "com.criptonews.app.data.CryptoRepositoryTest"`
Expected: FAIL with `Unresolved reference: CryptoRepository`.

- [ ] **Step 4: Write CryptoRepository, AppContainer, and wire CriptoNewsApp**

```kotlin
// android/app/src/main/java/com/criptonews/app/data/CryptoRepository.kt
package com.criptonews.app.data

import com.criptonews.app.network.ApiService
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.network.dto.DeviceTokenRequest
import com.criptonews.app.network.dto.SignalDto

class CryptoRepository(private val apiService: ApiService) {

    suspend fun getCoins(): Result<List<CoinDto>> = runCatching { apiService.getCoins() }

    suspend fun getSignals(coinSymbol: String? = null): Result<List<SignalDto>> =
        runCatching { apiService.getSignals(coinSymbol) }

    suspend fun getCandles(symbol: String, limit: Int = 100): Result<List<CandleDto>> =
        runCatching { apiService.getCandles(symbol, limit) }

    suspend fun registerDevice(token: String): Result<Unit> =
        runCatching { apiService.registerDevice(DeviceTokenRequest(token)) }
}
```

```kotlin
// android/app/src/main/java/com/criptonews/app/AppContainer.kt
package com.criptonews.app

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.NetworkModule

class AppContainer {
    private val apiService = NetworkModule.createApiService()
    val repository: CryptoRepository = CryptoRepository(apiService)
}
```

```kotlin
// android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt
package com.criptonews.app

import android.app.Application

class CriptoNewsApp : Application() {
    val container: AppContainer by lazy { AppContainer() }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `./gradlew test --tests "com.criptonews.app.data.CryptoRepositoryTest"`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the full test suite**

Run: `./gradlew test`
Expected: all tests across Tasks 1-3 pass.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/network/ApiService.kt android/app/src/main/java/com/criptonews/app/network/NetworkModule.kt android/app/src/main/java/com/criptonews/app/data android/app/src/main/java/com/criptonews/app/AppContainer.kt android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt android/app/src/test/java/com/criptonews/app/data
git commit -m "feat(android): add ApiService, CryptoRepository, and AppContainer"
```

---

### Task 4: Shared UiState and WatchlistViewModel

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/ui/UiState.kt`
- Create: `android/app/src/main/java/com/criptonews/app/ui/watchlist/WatchlistViewModel.kt`
- Create: `android/app/src/test/java/com/criptonews/app/util/MainDispatcherRule.kt`
- Create: `android/app/src/test/java/com/criptonews/app/network/FakeApiService.kt`
- Test: `android/app/src/test/java/com/criptonews/app/ui/watchlist/WatchlistViewModelTest.kt`

**Interfaces:**
- Consumes: `CryptoRepository` (Task 3); `CoinDto` (Task 2).
- Produces: `UiState<T>` sealed interface (`Loading`, `Success(data: T)`, `Error(message: String)`) — reused by Tasks 6 and 8; `WatchlistViewModel(repository: CryptoRepository)` exposing `val uiState: StateFlow<UiState<List<CoinDto>>>` and `fun loadCoins()`; `FakeApiService` (test-only, implements `ApiService`) — reused by Tasks 6 and 8's ViewModel tests; `MainDispatcherRule` (test-only JUnit4 rule swapping `Dispatchers.Main` for a test dispatcher) — reused by every ViewModel test.

- [ ] **Step 1: Write the shared test utilities**

```kotlin
// android/app/src/test/java/com/criptonews/app/util/MainDispatcherRule.kt
package com.criptonews.app.util

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.rules.TestWatcher
import org.junit.runner.Description

@OptIn(ExperimentalCoroutinesApi::class)
class MainDispatcherRule(
    private val testDispatcher: TestDispatcher = StandardTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) {
        kotlinx.coroutines.Dispatchers.setMain(testDispatcher)
    }

    override fun finished(description: Description) {
        kotlinx.coroutines.Dispatchers.resetMain()
    }
}
```

```kotlin
// android/app/src/test/java/com/criptonews/app/network/FakeApiService.kt
package com.criptonews.app.network

import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.network.dto.DeviceTokenRequest
import com.criptonews.app.network.dto.SignalDto

class FakeApiService(
    private val coins: List<CoinDto> = emptyList(),
    private val signals: List<SignalDto> = emptyList(),
    private val candles: List<CandleDto> = emptyList(),
    private val failWith: Throwable? = null,
) : ApiService {
    var registeredToken: String? = null
        private set

    override suspend fun getCoins(): List<CoinDto> {
        failWith?.let { throw it }
        return coins
    }

    override suspend fun getSignals(coinSymbol: String?): List<SignalDto> {
        failWith?.let { throw it }
        return if (coinSymbol == null) signals else signals.filter { it.coinSymbol == coinSymbol }
    }

    override suspend fun getCandles(symbol: String, limit: Int): List<CandleDto> {
        failWith?.let { throw it }
        return candles
    }

    override suspend fun registerDevice(request: DeviceTokenRequest) {
        failWith?.let { throw it }
        registeredToken = request.token
    }
}
```

- [ ] **Step 2: Write the failing test for WatchlistViewModel**

```kotlin
// android/app/src/test/java/com/criptonews/app/ui/watchlist/WatchlistViewModelTest.kt
package com.criptonews.app.ui.watchlist

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.FakeApiService
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import com.criptonews.app.util.MainDispatcherRule
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class WatchlistViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun `loads coins successfully into Success state`() = runTest {
        val coin = CoinDto(symbol = "BTCUSDT", name = "Bitcoin", rank = 1, hasOpenPosition = false)
        val repository = CryptoRepository(FakeApiService(coins = listOf(coin)))
        val viewModel = WatchlistViewModel(repository)

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Success)
        assertEquals(listOf(coin), (state as UiState.Success).data)
    }

    @Test
    fun `surfaces a failure as Error state`() = runTest {
        val repository = CryptoRepository(FakeApiService(failWith = RuntimeException("network down")))
        val viewModel = WatchlistViewModel(repository)

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Error)
        assertEquals("network down", (state as UiState.Error).message)
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `./gradlew test --tests "com.criptonews.app.ui.watchlist.WatchlistViewModelTest"`
Expected: FAIL with `Unresolved reference: WatchlistViewModel` / `UiState`.

- [ ] **Step 4: Write UiState and WatchlistViewModel**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/UiState.kt
package com.criptonews.app.ui

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Success<T>(val data: T) : UiState<T>
    data class Error(val message: String) : UiState<Nothing>
}
```

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/watchlist/WatchlistViewModel.kt
package com.criptonews.app.ui.watchlist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class WatchlistViewModel(private val repository: CryptoRepository) : ViewModel() {

    private val _uiState = MutableStateFlow<UiState<List<CoinDto>>>(UiState.Loading)
    val uiState: StateFlow<UiState<List<CoinDto>>> = _uiState.asStateFlow()

    init {
        loadCoins()
    }

    fun loadCoins() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            repository.getCoins().fold(
                onSuccess = { coins -> _uiState.value = UiState.Success(coins) },
                onFailure = { error -> _uiState.value = UiState.Error(error.message ?: "Unknown error") },
            )
        }
    }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `./gradlew test --tests "com.criptonews.app.ui.watchlist.WatchlistViewModelTest"`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/ui/UiState.kt android/app/src/main/java/com/criptonews/app/ui/watchlist android/app/src/test/java/com/criptonews/app/util android/app/src/test/java/com/criptonews/app/network/FakeApiService.kt android/app/src/test/java/com/criptonews/app/ui/watchlist
git commit -m "feat(android): add UiState and WatchlistViewModel"
```

---

### Task 5: WatchlistScreen composable

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/ui/watchlist/WatchlistScreen.kt`

**Interfaces:**
- Consumes: `WatchlistViewModel` (Task 4), `UiState`, `CoinDto`.
- Produces: `@Composable fun WatchlistScreen(viewModel: WatchlistViewModel, onCoinClick: (String) -> Unit)`. Used by Task 10's navigation graph.

- [ ] **Step 1: Write the screen**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/watchlist/WatchlistScreen.kt
package com.criptonews.app.ui.watchlist

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState

@Composable
fun WatchlistScreen(viewModel: WatchlistViewModel, onCoinClick: (String) -> Unit) {
    val state by viewModel.uiState.collectAsState()

    when (val current = state) {
        is UiState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is UiState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Error: ${current.message}")
        }
        is UiState.Success -> CoinList(current.data, onCoinClick)
    }
}

@Composable
private fun CoinList(coins: List<CoinDto>, onCoinClick: (String) -> Unit) {
    LazyColumn(contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(coins, key = { it.symbol }) { coin ->
            CoinRow(coin, onClick = { onCoinClick(coin.symbol) })
        }
    }
}

@Composable
private fun CoinRow(coin: CoinDto, onClick: () -> Unit) {
    Card(modifier = androidx.compose.ui.Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("#${coin.rank} ${coin.symbol}")
                Text(coin.name)
            }
            if (coin.hasOpenPosition) {
                Text("Entrada: ${coin.entryPrice} · SL: ${coin.stopLoss} · TP: ${coin.takeProfit}")
            } else {
                Text("Sin posición abierta")
            }
        }
    }
}
```

- [ ] **Step 2: Build to verify it compiles**

Run: `./gradlew assembleDebug`
Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/ui/watchlist/WatchlistScreen.kt
git commit -m "feat(android): add WatchlistScreen composable"
```

---

### Task 6: History (signals) — ViewModel and screen

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/ui/history/HistoryViewModel.kt`, `HistoryScreen.kt`
- Test: `android/app/src/test/java/com/criptonews/app/ui/history/HistoryViewModelTest.kt`

**Interfaces:**
- Consumes: `CryptoRepository`, `SignalDto`, `UiState`, `FakeApiService`, `MainDispatcherRule` (Tasks 2-4).
- Produces: `HistoryViewModel(repository: CryptoRepository)` exposing `val uiState: StateFlow<UiState<List<SignalDto>>>`; `@Composable fun HistoryScreen(viewModel: HistoryViewModel)`. Used by Task 10's navigation graph.

- [ ] **Step 1: Write the failing test**

```kotlin
// android/app/src/test/java/com/criptonews/app/ui/history/HistoryViewModelTest.kt
package com.criptonews.app.ui.history

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.FakeApiService
import com.criptonews.app.network.dto.SignalDto
import com.criptonews.app.ui.UiState
import com.criptonews.app.util.MainDispatcherRule
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class HistoryViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val signal = SignalDto(
        id = 1, coinSymbol = "BTCUSDT", signalType = "BUY", price = 60000.0,
        rsiVote = "buy", emaCrossVote = "buy", macdVote = "buy", donchianVote = null,
        createdAt = "2026-08-12T19:00:52.306234+00:00",
    )

    @Test
    fun `loads signal history into Success state`() = runTest {
        val repository = CryptoRepository(FakeApiService(signals = listOf(signal)))
        val viewModel = HistoryViewModel(repository)

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Success)
        assertEquals(listOf(signal), (state as UiState.Success).data)
    }

    @Test
    fun `surfaces a failure as Error state`() = runTest {
        val repository = CryptoRepository(FakeApiService(failWith = RuntimeException("boom")))
        val viewModel = HistoryViewModel(repository)

        testScheduler.advanceUntilIdle()

        assertTrue(viewModel.uiState.value is UiState.Error)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew test --tests "com.criptonews.app.ui.history.HistoryViewModelTest"`
Expected: FAIL with `Unresolved reference: HistoryViewModel`.

- [ ] **Step 3: Write HistoryViewModel and HistoryScreen**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/history/HistoryViewModel.kt
package com.criptonews.app.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.dto.SignalDto
import com.criptonews.app.ui.UiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class HistoryViewModel(private val repository: CryptoRepository) : ViewModel() {

    private val _uiState = MutableStateFlow<UiState<List<SignalDto>>>(UiState.Loading)
    val uiState: StateFlow<UiState<List<SignalDto>>> = _uiState.asStateFlow()

    init {
        loadSignals()
    }

    fun loadSignals() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            repository.getSignals().fold(
                onSuccess = { signals -> _uiState.value = UiState.Success(signals) },
                onFailure = { error -> _uiState.value = UiState.Error(error.message ?: "Unknown error") },
            )
        }
    }
}
```

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/history/HistoryScreen.kt
package com.criptonews.app.ui.history

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.criptonews.app.network.dto.SignalDto
import com.criptonews.app.ui.UiState
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

private val displayFormatter = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm")

@Composable
fun HistoryScreen(viewModel: HistoryViewModel) {
    val state by viewModel.uiState.collectAsState()

    when (val current = state) {
        is UiState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is UiState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Error: ${current.message}")
        }
        is UiState.Success -> SignalList(current.data)
    }
}

@Composable
private fun SignalList(signals: List<SignalDto>) {
    LazyColumn(contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(signals, key = { it.id }) { signal -> SignalRow(signal) }
    }
}

@Composable
private fun SignalRow(signal: SignalDto) {
    Card {
        Column(androidx.compose.ui.Modifier.padding(12.dp)) {
            Text("${signal.signalType} ${signal.coinSymbol}")
            Text("Precio: ${signal.price}")
            Text(formatTimestamp(signal.createdAt))
        }
    }
}

private fun formatTimestamp(iso: String): String = runCatching {
    OffsetDateTime.parse(iso).format(displayFormatter)
}.getOrDefault(iso)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./gradlew test --tests "com.criptonews.app.ui.history.HistoryViewModelTest"`
Expected: PASS (2 tests).

- [ ] **Step 5: Build to verify the screen compiles**

Run: `./gradlew assembleDebug`
Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/ui/history android/app/src/test/java/com/criptonews/app/ui/history
git commit -m "feat(android): add signal history ViewModel and screen"
```

---

### Task 7: Chart coordinate math (pure functions)

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/ui/detail/ChartMath.kt`
- Test: `android/app/src/test/java/com/criptonews/app/ui/detail/ChartMathTest.kt`

**Interfaces:**
- Consumes: nothing (pure functions over `Float`/`List<Float>`).
- Produces: `data class PriceRange(val min: Float, val max: Float)` with `val span: Float`; `ChartMath.priceRange(values: List<Float>): PriceRange`; `ChartMath.priceToY(price: Float, range: PriceRange, chartHeight: Float, topPadding: Float = 0f, bottomPadding: Float = 0f): Float`; `ChartMath.indexToX(index: Int, totalCount: Int, chartWidth: Float): Float`; `ChartMath.candleSlotWidth(totalCount: Int, chartWidth: Float): Float`. Used by Task 9's `CandleChart` composable.

- [ ] **Step 1: Write the failing tests**

```kotlin
// android/app/src/test/java/com/criptonews/app/ui/detail/ChartMathTest.kt
package com.criptonews.app.ui.detail

import org.junit.Assert.assertEquals
import org.junit.Test

class ChartMathTest {

    @Test
    fun `priceRange finds min and max of the given values`() {
        val range = ChartMath.priceRange(listOf(10f, 25f, 5f, 18f))

        assertEquals(5f, range.min, 0.0001f)
        assertEquals(25f, range.max, 0.0001f)
        assertEquals(20f, range.span, 0.0001f)
    }

    @Test
    fun `priceRange degenerate case has a non-zero span to avoid division by zero`() {
        val range = ChartMath.priceRange(listOf(10f, 10f, 10f))

        assertEquals(1f, range.span, 0.0001f)
    }

    @Test
    fun `priceToY maps the max price to the top of the chart`() {
        val range = PriceRange(min = 0f, max = 100f)

        val y = ChartMath.priceToY(price = 100f, range = range, chartHeight = 200f)

        assertEquals(0f, y, 0.0001f)
    }

    @Test
    fun `priceToY maps the min price to the bottom of the chart`() {
        val range = PriceRange(min = 0f, max = 100f)

        val y = ChartMath.priceToY(price = 0f, range = range, chartHeight = 200f)

        assertEquals(200f, y, 0.0001f)
    }

    @Test
    fun `priceToY maps the midpoint price to the vertical middle`() {
        val range = PriceRange(min = 0f, max = 100f)

        val y = ChartMath.priceToY(price = 50f, range = range, chartHeight = 200f)

        assertEquals(100f, y, 0.0001f)
    }

    @Test
    fun `indexToX centers the first candle in its slot`() {
        val x = ChartMath.indexToX(index = 0, totalCount = 4, chartWidth = 400f)

        // slot width = 100, first slot centered at 50
        assertEquals(50f, x, 0.0001f)
    }

    @Test
    fun `indexToX centers the last candle in its slot`() {
        val x = ChartMath.indexToX(index = 3, totalCount = 4, chartWidth = 400f)

        assertEquals(350f, x, 0.0001f)
    }

    @Test
    fun `candleSlotWidth divides chart width evenly by candle count`() {
        val width = ChartMath.candleSlotWidth(totalCount = 5, chartWidth = 500f)

        assertEquals(100f, width, 0.0001f)
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./gradlew test --tests "com.criptonews.app.ui.detail.ChartMathTest"`
Expected: FAIL with `Unresolved reference: ChartMath` / `PriceRange`.

- [ ] **Step 3: Write ChartMath**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/detail/ChartMath.kt
package com.criptonews.app.ui.detail

data class PriceRange(val min: Float, val max: Float) {
    val span: Float get() = (max - min).takeIf { it > 0f } ?: 1f
}

object ChartMath {

    fun priceRange(values: List<Float>): PriceRange {
        require(values.isNotEmpty()) { "values must not be empty" }
        return PriceRange(min = values.min(), max = values.max())
    }

    fun priceToY(
        price: Float,
        range: PriceRange,
        chartHeight: Float,
        topPadding: Float = 0f,
        bottomPadding: Float = 0f,
    ): Float {
        val usableHeight = chartHeight - topPadding - bottomPadding
        val normalized = (price - range.min) / range.span
        return topPadding + usableHeight * (1f - normalized)
    }

    fun indexToX(index: Int, totalCount: Int, chartWidth: Float): Float {
        require(totalCount > 0) { "totalCount must be positive" }
        val slotWidth = chartWidth / totalCount
        return index * slotWidth + slotWidth / 2f
    }

    fun candleSlotWidth(totalCount: Int, chartWidth: Float): Float {
        require(totalCount > 0) { "totalCount must be positive" }
        return chartWidth / totalCount
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./gradlew test --tests "com.criptonews.app.ui.detail.ChartMathTest"`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/ui/detail/ChartMath.kt android/app/src/test/java/com/criptonews/app/ui/detail/ChartMathTest.kt
git commit -m "feat(android): add pure chart coordinate-mapping functions"
```

---

### Task 8: CoinDetailViewModel

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/ui/detail/CoinDetailViewModel.kt`
- Test: `android/app/src/test/java/com/criptonews/app/ui/detail/CoinDetailViewModelTest.kt`

**Interfaces:**
- Consumes: `CryptoRepository`, `CandleDto`, `CoinDto`, `UiState`, `FakeApiService`, `MainDispatcherRule` (Tasks 2-4).
- Produces: `data class CoinDetailData(val candles: List<CandleDto>, val position: CoinDto?)`; `CoinDetailViewModel(repository: CryptoRepository, symbol: String)` exposing `val uiState: StateFlow<UiState<CoinDetailData>>`. Fetches candles and the coin's own `/coins` entry independently (not passed as a nav argument) so the screen is self-sufficient whether reached via in-app navigation or a cold-start notification deep link (Task 11). Used by Task 9's `CoinDetailScreen`.

- [ ] **Step 1: Write the failing test**

```kotlin
// android/app/src/test/java/com/criptonews/app/ui/detail/CoinDetailViewModelTest.kt
package com.criptonews.app.ui.detail

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.FakeApiService
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import com.criptonews.app.util.MainDispatcherRule
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class CoinDetailViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val candle = CandleDto(
        openTime = 1700000000000, open = 100.0, high = 105.0, low = 95.0, close = 102.0, volume = 10.0,
    )

    @Test
    fun `combines candles with the matching open position`() = runTest {
        val position = CoinDto(
            symbol = "BTCUSDT", name = "Bitcoin", rank = 1, hasOpenPosition = true,
            entryPrice = 100.0, stopLoss = 90.0, takeProfit = 130.0,
        )
        val other = CoinDto(symbol = "ETHUSDT", name = "Ethereum", rank = 2, hasOpenPosition = false)
        val repository = CryptoRepository(
            FakeApiService(coins = listOf(position, other), candles = listOf(candle)),
        )
        val viewModel = CoinDetailViewModel(repository, symbol = "BTCUSDT")

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Success)
        val data = (state as UiState.Success).data
        assertEquals(listOf(candle), data.candles)
        assertEquals(position, data.position)
    }

    @Test
    fun `position is null when the coin has no open position`() = runTest {
        val flatCoin = CoinDto(symbol = "BTCUSDT", name = "Bitcoin", rank = 1, hasOpenPosition = false)
        val repository = CryptoRepository(FakeApiService(coins = listOf(flatCoin), candles = listOf(candle)))
        val viewModel = CoinDetailViewModel(repository, symbol = "BTCUSDT")

        testScheduler.advanceUntilIdle()

        val data = (viewModel.uiState.value as UiState.Success).data
        assertNull(data.position)
    }

    @Test
    fun `surfaces a candles failure as Error state`() = runTest {
        val repository = CryptoRepository(FakeApiService(failWith = RuntimeException("502")))
        val viewModel = CoinDetailViewModel(repository, symbol = "BTCUSDT")

        testScheduler.advanceUntilIdle()

        assertTrue(viewModel.uiState.value is UiState.Error)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew test --tests "com.criptonews.app.ui.detail.CoinDetailViewModelTest"`
Expected: FAIL with `Unresolved reference: CoinDetailViewModel`.

- [ ] **Step 3: Write CoinDetailViewModel**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/detail/CoinDetailViewModel.kt
package com.criptonews.app.ui.detail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CoinDetailData(val candles: List<CandleDto>, val position: CoinDto?)

class CoinDetailViewModel(
    private val repository: CryptoRepository,
    private val symbol: String,
) : ViewModel() {

    private val _uiState = MutableStateFlow<UiState<CoinDetailData>>(UiState.Loading)
    val uiState: StateFlow<UiState<CoinDetailData>> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            runCatching {
                coroutineScope {
                    val candlesDeferred = async { repository.getCandles(symbol).getOrThrow() }
                    val coinsDeferred = async { repository.getCoins().getOrThrow() }
                    val candles = candlesDeferred.await()
                    val position = coinsDeferred.await().find { it.symbol == symbol && it.hasOpenPosition }
                    CoinDetailData(candles = candles, position = position)
                }
            }.fold(
                onSuccess = { data -> _uiState.value = UiState.Success(data) },
                onFailure = { error -> _uiState.value = UiState.Error(error.message ?: "Unknown error") },
            )
        }
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./gradlew test --tests "com.criptonews.app.ui.detail.CoinDetailViewModelTest"`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/ui/detail/CoinDetailViewModel.kt android/app/src/test/java/com/criptonews/app/ui/detail/CoinDetailViewModelTest.kt
git commit -m "feat(android): add CoinDetailViewModel combining candles and position data"
```

---

### Task 9: CandleChart (Canvas) and CoinDetailScreen

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/ui/detail/CandleChart.kt`
- Create: `android/app/src/main/java/com/criptonews/app/ui/detail/CoinDetailScreen.kt`

**Interfaces:**
- Consumes: `ChartMath`, `PriceRange` (Task 7); `CoinDetailViewModel`, `CoinDetailData` (Task 8); `CandleDto`, `CoinDto`, `UiState`.
- Produces: `@Composable fun CandleChart(candles: List<CandleDto>, position: CoinDto?, modifier: Modifier = Modifier)`; `@Composable fun CoinDetailScreen(viewModel: CoinDetailViewModel)`. Used by Task 10's navigation graph.

- [ ] **Step 1: Write the chart composable**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/detail/CandleChart.kt
package com.criptonews.app.ui.detail

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.unit.dp
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto

private val BullColor = Color(0xFF2E7D32)
private val BearColor = Color(0xFFC62828)
private val Ema9Color = Color(0xFF1976D2)
private val Ema21Color = Color(0xFFF57C00)
private val EntryColor = Color(0xFF616161)
private val StopLossColor = Color(0xFFC62828)
private val TakeProfitColor = Color(0xFF2E7D32)

@Composable
fun CandleChart(candles: List<CandleDto>, position: CoinDto?, modifier: Modifier = Modifier) {
    Column(modifier) {
        MainCandleChart(candles, position)
        RsiChart(candles)
        MacdChart(candles)
    }
}

@Composable
private fun MainCandleChart(candles: List<CandleDto>, position: CoinDto?) {
    Canvas(Modifier.fillMaxWidth().height(240.dp)) {
        if (candles.isEmpty()) return@Canvas
        val allPrices = candles.flatMap { listOf(it.high.toFloat(), it.low.toFloat()) } +
            listOfNotNull(position?.stopLoss?.toFloat(), position?.takeProfit?.toFloat())
        val range = ChartMath.priceRange(allPrices)
        val slotWidth = ChartMath.candleSlotWidth(candles.size, size.width)
        val bodyWidth = slotWidth * 0.6f

        candles.forEachIndexed { index, candle ->
            val x = ChartMath.indexToX(index, candles.size, size.width)
            val yHigh = ChartMath.priceToY(candle.high.toFloat(), range, size.height)
            val yLow = ChartMath.priceToY(candle.low.toFloat(), range, size.height)
            val yOpen = ChartMath.priceToY(candle.open.toFloat(), range, size.height)
            val yClose = ChartMath.priceToY(candle.close.toFloat(), range, size.height)
            val color = if (candle.close >= candle.open) BullColor else BearColor

            drawLine(color, Offset(x, yHigh), Offset(x, yLow), strokeWidth = 2f, cap = StrokeCap.Round)
            drawRect(
                color = color,
                topLeft = Offset(x - bodyWidth / 2f, minOf(yOpen, yClose)),
                size = androidx.compose.ui.geometry.Size(bodyWidth, maxOf(1f, kotlin.math.abs(yClose - yOpen))),
            )
        }

        drawIndicatorLine(candles, range) { it.ema9?.toFloat() }?.let { path -> drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
        drawIndicatorLine(candles, range) { it.ema21?.toFloat() }?.let { path -> drawPath(path, Ema21Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }

        position?.entryPrice?.let { entry ->
            drawHorizontalLine(entry.toFloat(), range, EntryColor)
        }
        position?.stopLoss?.let { sl -> drawHorizontalLine(sl.toFloat(), range, StopLossColor) }
        position?.takeProfit?.let { tp -> drawHorizontalLine(tp.toFloat(), range, TakeProfitColor) }
    }
}

@Composable
private fun RsiChart(candles: List<CandleDto>) {
    Canvas(Modifier.fillMaxWidth().height(80.dp)) {
        val values = candles.mapNotNull { it.rsi14?.toFloat() }
        if (values.isEmpty()) return@Canvas
        val range = PriceRange(min = 0f, max = 100f)
        val path = androidx.compose.ui.graphics.Path()
        var started = false
        candles.forEachIndexed { index, candle ->
            val value = candle.rsi14?.toFloat() ?: return@forEachIndexed
            val x = ChartMath.indexToX(index, candles.size, size.width)
            val y = ChartMath.priceToY(value, range, size.height)
            if (!started) {
                path.moveTo(x, y)
                started = true
            } else {
                path.lineTo(x, y)
            }
        }
        drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f))
        drawHorizontalLine(30f, range, BearColor)
        drawHorizontalLine(70f, range, BullColor)
    }
}

@Composable
private fun MacdChart(candles: List<CandleDto>) {
    Canvas(Modifier.fillMaxWidth().height(80.dp)) {
        val allValues = candles.flatMap { listOfNotNull(it.macdLine?.toFloat(), it.macdSignal?.toFloat()) }
        if (allValues.isEmpty()) return@Canvas
        val range = ChartMath.priceRange(allValues)
        drawIndicatorLine(candles, range) { it.macdLine?.toFloat() }?.let { path -> drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
        drawIndicatorLine(candles, range) { it.macdSignal?.toFloat() }?.let { path -> drawPath(path, Ema21Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawIndicatorLine(
    candles: List<CandleDto>,
    range: PriceRange,
    selector: (CandleDto) -> Float?,
): androidx.compose.ui.graphics.Path? {
    val path = androidx.compose.ui.graphics.Path()
    var started = false
    candles.forEachIndexed { index, candle ->
        val value = selector(candle) ?: return@forEachIndexed
        val x = ChartMath.indexToX(index, candles.size, size.width)
        val y = ChartMath.priceToY(value, range, size.height)
        if (!started) {
            path.moveTo(x, y)
            started = true
        } else {
            path.lineTo(x, y)
        }
    }
    return if (started) path else null
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawHorizontalLine(
    price: Float,
    range: PriceRange,
    color: Color,
) {
    val y = ChartMath.priceToY(price, range, size.height)
    drawLine(
        color = color,
        start = Offset(0f, y),
        end = Offset(size.width, y),
        strokeWidth = 2f,
        pathEffect = PathEffect.dashPathEffect(floatArrayOf(12f, 8f)),
    )
}
```

- [ ] **Step 2: Write CoinDetailScreen**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/detail/CoinDetailScreen.kt
package com.criptonews.app.ui.detail

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.criptonews.app.ui.UiState

@Composable
fun CoinDetailScreen(viewModel: CoinDetailViewModel) {
    val state by viewModel.uiState.collectAsState()

    when (val current = state) {
        is UiState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is UiState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Error: ${current.message}")
        }
        is UiState.Success -> Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(12.dp),
        ) {
            current.data.position?.let { position ->
                Text("Entrada: ${position.entryPrice}  SL: ${position.stopLoss}  TP: ${position.takeProfit}")
            }
            CandleChart(candles = current.data.candles, position = current.data.position)
        }
    }
}
```

- [ ] **Step 3: Build to verify it compiles**

Run: `./gradlew assembleDebug`
Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/ui/detail/CandleChart.kt android/app/src/main/java/com/criptonews/app/ui/detail/CoinDetailScreen.kt
git commit -m "feat(android): add Canvas-based candle chart and detail screen"
```

---

### Task 10: Navigation graph and MainActivity wiring

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/ui/navigation/Destinations.kt`, `CriptoNewsNavHost.kt`
- Modify: `android/app/src/main/java/com/criptonews/app/MainActivity.kt`

**Interfaces:**
- Consumes: `WatchlistScreen`, `HistoryScreen`, `CoinDetailScreen` (Tasks 5, 6, 9); `CriptoNewsApp.container` (Task 3).
- Produces: `@Composable fun CriptoNewsNavHost(container: AppContainer, startCoinSymbol: String? = null)`. `MainActivity` now hosts this NavHost with a bottom navigation bar (Watchlist / History) and a Detail route reachable both from tapping a coin and from a notification deep link (`startCoinSymbol`, wired fully in Task 11).

- [ ] **Step 1: Write Destinations**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/navigation/Destinations.kt
package com.criptonews.app.ui.navigation

object Destinations {
    const val WATCHLIST = "watchlist"
    const val HISTORY = "history"
    const val DETAIL = "detail/{symbol}"

    fun detailRoute(symbol: String) = "detail/$symbol"
}
```

- [ ] **Step 2: Write the NavHost**

```kotlin
// android/app/src/main/java/com/criptonews/app/ui/navigation/CriptoNewsNavHost.kt
package com.criptonews.app.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.List
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.criptonews.app.AppContainer
import com.criptonews.app.ui.detail.CoinDetailScreen
import com.criptonews.app.ui.detail.CoinDetailViewModel
import com.criptonews.app.ui.history.HistoryScreen
import com.criptonews.app.ui.history.HistoryViewModel
import com.criptonews.app.ui.watchlist.WatchlistScreen
import com.criptonews.app.ui.watchlist.WatchlistViewModel

@Composable
fun CriptoNewsNavHost(container: AppContainer, startCoinSymbol: String? = null) {
    val navController = rememberNavController()

    LaunchedEffect(startCoinSymbol) {
        if (startCoinSymbol != null) {
            navController.navigate(Destinations.detailRoute(startCoinSymbol))
        }
    }

    Scaffold(bottomBar = { BottomBar(navController) }) { padding ->
        NavHost(
            navController = navController,
            startDestination = Destinations.WATCHLIST,
            modifier = Modifier.padding(padding),
        ) {
            composable(Destinations.WATCHLIST) {
                val viewModel: WatchlistViewModel = viewModel { WatchlistViewModel(container.repository) }
                WatchlistScreen(viewModel) { symbol ->
                    navController.navigate(Destinations.detailRoute(symbol))
                }
            }
            composable(Destinations.HISTORY) {
                val viewModel: HistoryViewModel = viewModel { HistoryViewModel(container.repository) }
                HistoryScreen(viewModel)
            }
            composable(Destinations.DETAIL) { backStackEntry ->
                val symbol = backStackEntry.arguments?.getString("symbol").orEmpty()
                val viewModel: CoinDetailViewModel = viewModel(key = symbol) {
                    CoinDetailViewModel(container.repository, symbol)
                }
                CoinDetailScreen(viewModel)
            }
        }
    }
}

@Composable
private fun BottomBar(navController: NavHostController) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    NavigationBar {
        NavigationBarItem(
            selected = currentRoute == Destinations.WATCHLIST,
            onClick = { navController.navigate(Destinations.WATCHLIST) { launchSingleTop = true } },
            icon = { Icon(Icons.Filled.List, contentDescription = null) },
            label = { Text("Watchlist") },
        )
        NavigationBarItem(
            selected = currentRoute == Destinations.HISTORY,
            onClick = { navController.navigate(Destinations.HISTORY) { launchSingleTop = true } },
            icon = { Icon(Icons.Filled.History, contentDescription = null) },
            label = { Text("Historial") },
        )
    }
}
```

Add the navigation-arguments import needed by `composable(Destinations.DETAIL) { ... }` — Navigation Compose infers the `symbol` path argument from the route string `"detail/{symbol}"` automatically; no extra `navArgument` declaration is required for a simple string argument accessed via `backStackEntry.arguments?.getString("symbol")`.

- [ ] **Step 3: Wire MainActivity to host the NavHost**

```kotlin
// android/app/src/main/java/com/criptonews/app/MainActivity.kt
package com.criptonews.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.criptonews.app.ui.navigation.CriptoNewsNavHost
import com.criptonews.app.ui.theme.CriptoNewsTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as CriptoNewsApp).container
        val startCoinSymbol = intent.getStringExtra(EXTRA_COIN_SYMBOL)
        setContent {
            CriptoNewsTheme {
                CriptoNewsNavHost(container = container, startCoinSymbol = startCoinSymbol)
            }
        }
    }

    companion object {
        const val EXTRA_COIN_SYMBOL = "coin_symbol"
    }
}
```

- [ ] **Step 4: Add the Material Icons Extended dependency needed by the bottom bar**

Add to `android/gradle/libs.versions.toml` under `[libraries]`:
```toml
androidx-material-icons-extended = { group = "androidx.compose.material", name = "material-icons-extended" }
```

Add to `android/app/build.gradle.kts` dependencies block:
```kotlin
    implementation(libs.androidx.material.icons.extended)
```

- [ ] **Step 5: Build to verify everything compiles and wires together**

Run: `./gradlew assembleDebug`
Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 6: Run the full test suite one more time**

Run: `./gradlew test`
Expected: all tests from Tasks 1-9 still pass (navigation wiring touches no tested logic).

- [ ] **Step 7: Commit**

```bash
git add android/gradle/libs.versions.toml android/app/build.gradle.kts android/app/src/main/java/com/criptonews/app/ui/navigation android/app/src/main/java/com/criptonews/app/MainActivity.kt
git commit -m "feat(android): add navigation graph and wire MainActivity"
```

---

### Task 11: FCM — device token registration and notification handling

**Files:**
- Create: `android/app/src/main/java/com/criptonews/app/notifications/NotificationHelper.kt`, `CriptoNewsFirebaseMessagingService.kt`
- Modify: `android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt`
- Modify: `android/app/src/main/java/com/criptonews/app/MainActivity.kt`
- Modify: `android/app/src/main/AndroidManifest.xml`

**Interfaces:**
- Consumes: `AppContainer.repository.registerDevice(token)` (Task 3); `MainActivity.EXTRA_COIN_SYMBOL` (Task 10).
- Produces: `CriptoNewsFirebaseMessagingService` (registered in the manifest, handles `onNewToken` and `onMessageReceived`); `NotificationHelper.showSignalNotification(context, coinSymbol, signalType, price)`; `CriptoNewsApp` now also registers the current FCM token at startup, tolerating Firebase being unconfigured.

**Manual setup step (not code, required before this task's runtime behavior works):** create a Firebase project at the Firebase console with Android package name `com.criptonews.app`, enable Cloud Messaging, download `google-services.json`, and place it at `android/app/google-services.json` (gitignored — never commit it). Without this file, the app still builds and runs (per Task 1's conditional plugin application) but no push notifications will be delivered — the code below defends against that by checking `FirebaseApp.getApps(...)` before touching Firebase APIs, matching the backend's own "never crash on a notification failure" philosophy (`backend/app/notifications.py`).

- [ ] **Step 1: Write NotificationHelper**

```kotlin
// android/app/src/main/java/com/criptonews/app/notifications/NotificationHelper.kt
package com.criptonews.app.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.criptonews.app.MainActivity

private const val CHANNEL_ID = "signals"
private const val CHANNEL_NAME = "Señales de trading"

object NotificationHelper {

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(CHANNEL_ID, CHANNEL_NAME, NotificationManager.IMPORTANCE_HIGH)
        manager.createNotificationChannel(channel)
    }

    fun showSignalNotification(context: Context, coinSymbol: String, title: String, body: String) {
        ensureChannel(context)

        val openIntent = Intent(context, MainActivity::class.java).apply {
            putExtra(MainActivity.EXTRA_COIN_SYMBOL, coinSymbol)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            context, coinSymbol.hashCode(), openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        val manager = context.getSystemService(NotificationManager::class.java)
        manager.notify(coinSymbol.hashCode(), notification)
    }
}
```

- [ ] **Step 2: Write the FCM service**

```kotlin
// android/app/src/main/java/com/criptonews/app/notifications/CriptoNewsFirebaseMessagingService.kt
package com.criptonews.app.notifications

import android.util.Log
import com.criptonews.app.CriptoNewsApp
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

private const val TAG = "CriptoNewsFcm"

class CriptoNewsFirebaseMessagingService : FirebaseMessagingService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        val container = (application as CriptoNewsApp).container
        scope.launch {
            container.repository.registerDevice(token).onFailure { error ->
                Log.w(TAG, "Failed to register device token", error)
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val coinSymbol = message.data["coin_symbol"] ?: return
        val signalType = message.data["signal_type"] ?: "SIGNAL"
        // The backend (backend/app/notifications.py) already builds a fully-formed
        // title/body (e.g. title="BUY BTCUSDT", body="Precio: 60000.00 USDT") — use
        // them as-is rather than re-deriving text from the raw data fields.
        val title = message.notification?.title ?: "$signalType $coinSymbol"
        val body = message.notification?.body ?: "Nueva señal"

        NotificationHelper.showSignalNotification(
            context = applicationContext,
            coinSymbol = coinSymbol,
            title = title,
            body = body,
        )
    }
}
```

- [ ] **Step 3: Register the initial token at app startup, tolerating unconfigured Firebase**

```kotlin
// android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt
package com.criptonews.app

import android.app.Application
import android.util.Log
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

private const val TAG = "CriptoNewsApp"

class CriptoNewsApp : Application() {
    val container: AppContainer by lazy { AppContainer() }
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        registerCurrentFcmTokenIfFirebaseIsConfigured()
    }

    private fun registerCurrentFcmTokenIfFirebaseIsConfigured() {
        if (FirebaseApp.getApps(this).isEmpty()) {
            Log.i(TAG, "Firebase not configured (no google-services.json) — skipping token registration")
            return
        }
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            applicationScope.launch {
                container.repository.registerDevice(token).onFailure { error ->
                    Log.w(TAG, "Failed to register device token at startup", error)
                }
            }
        }
    }
}
```

- [ ] **Step 4: Handle a notification tap while the app is already running**

```kotlin
// android/app/src/main/java/com/criptonews/app/MainActivity.kt
package com.criptonews.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.mutableStateOf
import com.criptonews.app.ui.navigation.CriptoNewsNavHost
import com.criptonews.app.ui.theme.CriptoNewsTheme

class MainActivity : ComponentActivity() {
    private val startCoinSymbol = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as CriptoNewsApp).container
        startCoinSymbol.value = intent.getStringExtra(EXTRA_COIN_SYMBOL)
        setContent {
            CriptoNewsTheme {
                CriptoNewsNavHost(container = container, startCoinSymbol = startCoinSymbol.value)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        startCoinSymbol.value = intent.getStringExtra(EXTRA_COIN_SYMBOL)
    }

    companion object {
        const val EXTRA_COIN_SYMBOL = "coin_symbol"
    }
}
```

Note: because `CriptoNewsNavHost`'s `LaunchedEffect(startCoinSymbol)` (Task 10) keys on the `startCoinSymbol` value, updating the `mutableStateOf` and letting Compose recompose is sufficient to trigger the deep-link navigation on a notification tap for a *different* coin than the one currently shown. Two consecutive notification taps for the *same* coin won't re-trigger the effect (the key value is unchanged) — harmless in practice, since the user would already be looking at that coin's Detail screen from the first tap. Not worth the extra plumbing (e.g. a monotonic tap counter) for a personal single-user app.

- [ ] **Step 5: Register the FCM service in the manifest**

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<!-- Add inside <application>, alongside the existing <activity> -->
<service
    android:name=".notifications.CriptoNewsFirebaseMessagingService"
    android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

- [ ] **Step 6: Build to verify everything compiles**

Run: `./gradlew assembleDebug`
Expected: `BUILD SUCCESSFUL` (with or without `google-services.json` present, per Task 1's conditional plugin application).

- [ ] **Step 7: Run the full test suite**

Run: `./gradlew test`
Expected: all tests from Tasks 1-10 still pass.

- [ ] **Step 8: Commit**

```bash
git add android/app/src/main/java/com/criptonews/app/notifications android/app/src/main/java/com/criptonews/app/CriptoNewsApp.kt android/app/src/main/java/com/criptonews/app/MainActivity.kt android/app/src/main/AndroidManifest.xml
git commit -m "feat(android): add FCM token registration and notification tap-through"
```

---

### Task 12: Manual end-to-end verification on the emulator

**Files:**
- None created — this task exercises the running app on the `TabletPrueba1` AVD.

**Interfaces:**
- Consumes: the full app from Tasks 1-11, and the already-implemented, already-merged `backend/` (running locally).

- [ ] **Step 1: Start the backend**

From the repo root:
```bash
cd backend
./.venv/Scripts/python.exe -m uvicorn app.main:app
```
Expected: server listening on `http://127.0.0.1:8000`. Leave it running for the rest of this task.

- [ ] **Step 2: Boot the existing emulator**

```bash
"C:/Users/SISTEMAS-03/AppData/Local/Android/Sdk/emulator/emulator.exe" -avd TabletPrueba1
```
Expected: emulator window opens and finishes booting (check with `adb devices` until it lists a `device`, not `offline`).

- [ ] **Step 3: Confirm the emulator can reach the backend**

```bash
"C:/Users/SISTEMAS-03/AppData/Local/Android/Sdk/platform-tools/adb.exe" shell curl -s http://10.0.2.2:8000/health
```
Expected: `{"status":"ok"}`. If `curl` isn't available inside the emulator's shell, skip this step — Step 5's app install/run is the real check.

- [ ] **Step 4: Install and launch the app**

From `android/`:
```bash
./gradlew installDebug
"C:/Users/SISTEMAS-03/AppData/Local/Android/Sdk/platform-tools/adb.exe" shell am start -n com.criptonews.app/.MainActivity
```
Expected: app launches on the emulator, Watchlist screen loads.

- [ ] **Step 5: Verify the Watchlist screen shows real backend data**

Look at the emulator screen (or `adb exec-out screencap -p > watchlist.png` and view the file). Expected: a list of coins matching what `curl http://127.0.0.1:8000/coins` returns on the host.

- [ ] **Step 6: Verify the History screen**

Tap the "Historial" bottom nav item. Expected: either an empty list (if no 3-of-4 signal has fired yet — correct, not a bug) or a list matching `curl http://127.0.0.1:8000/signals`.

- [ ] **Step 7: Verify the Detail screen and chart**

Tap any coin in the Watchlist. Expected: navigates to the Detail screen, candle chart renders without crashing, RSI/MACD sub-charts render below it. If the coin has an open position, entry/SL/TP dashed lines are visible on the main chart.

- [ ] **Step 8: Verify device token registration was attempted**

```bash
"C:/Users/SISTEMAS-03/AppData/Local/Android/Sdk/platform-tools/adb.exe" logcat -d | grep CriptoNewsApp
```
Expected: either a log line confirming registration succeeded, or (if `google-services.json` hasn't been set up yet) the "Firebase not configured — skipping token registration" line from `CriptoNewsApp.registerCurrentFcmTokenIfFirebaseIsConfigured`. Both are correct, expected outcomes for this step — a hard crash is the only failure.

- [ ] **Step 9: Clean up**

```bash
"C:/Users/SISTEMAS-03/AppData/Local/Android/Sdk/platform-tools/adb.exe" emu kill
```
Stop the backend server (Ctrl+C in its terminal, or the equivalent for however it was started in Step 1).

- [ ] **Step 10: No commit needed** — this task only verifies the previous 11 tasks work together against the real backend. If any step fails, return to the relevant task to fix it, then re-run this task.

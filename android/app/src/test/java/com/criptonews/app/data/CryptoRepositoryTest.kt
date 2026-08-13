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

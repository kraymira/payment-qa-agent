import asyncio

from httpx import ASGITransport, AsyncClient, Response

from payment_qa_agent.api import create_app


async def post_payment(
    client: AsyncClient,
    *,
    key: str,
    amount: str = "19.99",
) -> Response:
    return await client.post(
        "/payments",
        headers={"Idempotency-Key": key},
        json={"amount": amount, "currency": "EUR"},
    )


# Risk: concurrent HTTP retries create more than one payment for one logical request.
def test_concurrent_requests_return_one_payment_id() -> None:
    async def scenario() -> None:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            responses = await asyncio.gather(
                *(post_payment(client, key="concurrent-123") for _ in range(20))
            )

        assert {response.status_code for response in responses} == {201}
        payment_ids = {response.json()["payment_id"] for response in responses}
        assert len(payment_ids) == 1

    asyncio.run(scenario())


# Risk: an idempotency key silently accepts a different financial request.
def test_api_returns_conflict_for_same_key_with_different_payload() -> None:
    async def scenario() -> None:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            first = await post_payment(client, key="conflict-123")
            conflict = await post_payment(
                client,
                key="conflict-123",
                amount="29.99",
            )

        assert first.status_code == 201
        assert conflict.status_code == 409
        assert "different request" in conflict.json()["detail"]

    asyncio.run(scenario())


# Risk: the read endpoint returns a different payment snapshot than creation.
def test_created_payment_can_be_read() -> None:
    async def scenario() -> None:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            created = await post_payment(client, key="read-123")
            payment_id = created.json()["payment_id"]
            fetched = await client.get(f"/payments/{payment_id}")

        assert fetched.status_code == 200
        assert fetched.json() == created.json()

    asyncio.run(scenario())


# Risk: malformed requests are accepted differently from the domain boundary.
def test_api_rejects_missing_key_and_invalid_amount() -> None:
    async def scenario() -> None:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            missing_key = await client.post(
                "/payments",
                json={"amount": "19.99", "currency": "EUR"},
            )
            invalid_amount = await post_payment(
                client,
                key="invalid-123",
                amount="0",
            )

        assert missing_key.status_code == 422
        assert invalid_amount.status_code == 422

    asyncio.run(scenario())

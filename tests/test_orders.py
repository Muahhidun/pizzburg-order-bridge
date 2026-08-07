async def test_create_and_read_dry_run_order(client, token, order_payload):
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post("/order", headers=headers, json=order_payload)
    fetched = await client.get("/order/yandex-order-1001", headers=headers)
    order_status = await client.get("/order/yandex-order-1001/status", headers=headers)

    assert created.status_code == 201
    assert created.json()["status"] == "accepted_dry_run"
    assert created.json()["mode"] == "dry-run"
    assert fetched.status_code == 200
    assert order_status.json()["status"] == "accepted_dry_run"


async def test_same_order_is_idempotent(client, token, order_payload):
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post("/order", headers=headers, json=order_payload)
    second = await client.post("/order", headers=headers, json=order_payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert first.json()["id"] == second.json()["id"]


async def test_changed_duplicate_is_rejected(client, token, order_payload):
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/order", headers=headers, json=order_payload)
    order_payload["comment"] = "Changed content"

    response = await client.post("/order", headers=headers, json=order_payload)

    assert response.status_code == 409


async def test_invalid_total_is_rejected(client, token, order_payload):
    order_payload["total"] = "1.00"

    response = await client.post(
        "/order",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload,
    )

    assert response.status_code == 422

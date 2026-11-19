"""Order-events sandbox: the asynchronous SYSTEM UNDER TEST for Unit 3, Day 12.

Not test code. It plays an order-fulfilment back end:

    POST /orders ─▶ OrderPlaced ─▶ payments worker ─▶ payment gateway
                                         │
                                         └─▶ OrderPaid ─▶ fulfilment ─▶ OrderPacked, OrderShipped
    every event ─▶ projector ─▶ read model (GET /orders/{id}) ─▶ WebSocket frames (/ws)

Messages travel through an in-memory broker with at-least-once delivery: acknowledgements,
a visibility timeout, retries with backoff, and a dead-letter queue. Faults can be injected
per correlation id (POST /admin/faults), so parallel tests never disturb each other.

The tests treat it as a black box: they talk to it over HTTP and WebSocket only
(framework/events), never by importing this package. Run it on its own with:

    python -m sandbox --port 8765 --build release
"""

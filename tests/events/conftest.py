"""Asynchronous-system tests (Unit 3, Day 12) against the order-events sandbox.

They run with ``--store fake`` (everything local) and receive an ``OrderFlow`` from
framework/plugins/events.py: a unique correlation id, already following its live status.
"""

"""Bind every .feature file under features/ to pytest (one test per scenario / example row)."""

from pytest_bdd import scenarios

scenarios(".")

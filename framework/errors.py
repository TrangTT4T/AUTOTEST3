"""Exception hierarchy.

The type of an exception decides how a failure is reported:

* ``EnvironmentBlockedError``  -> "blocked": the environment stopped us, not a product defect.
* ``DataUnavailableError``     -> the test data a scenario needs does not exist.
* ``CartInconsistencyError``   -> a product defect: two layers of the shop disagree.
* ``NotSupportedOnPlatformError`` -> a scenario asked a platform for a feature it does not have.
* any other ``AssertionError`` -> a product defect found by a ``Then`` step.
"""


class FrameworkError(Exception):
    """Base class for errors raised by the test framework itself."""


class EnvironmentBlockedError(FrameworkError):
    """Bot protection, rate limiting, or an outage replaced the real page."""


class DataUnavailableError(FrameworkError):
    """A scenario needs data that the system under test does not have."""


class NotSupportedOnPlatformError(FrameworkError):
    """The product on this platform has no such feature (e.g. the mobile app has no search)."""


class CartInconsistencyError(AssertionError):
    """The cart page and the store's cart data disagree."""

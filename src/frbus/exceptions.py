"""Exceptions for the frbus package."""


class FrbusError(Exception):
    """Base class for frbus errors."""


class InvalidModelError(FrbusError):
    """The model file is malformed or inconsistent."""


class MissingDataError(FrbusError):
    """A model variable is missing from the input dataset."""

    def __init__(self, name: str):
        super().__init__(f"Missing data for variable: {name}")
        self.name = name


class ConvergenceError(FrbusError):
    """The solver failed to converge."""


class ComputationError(FrbusError):
    """A numerical error (overflow, domain error, ...) occurred during evaluation."""

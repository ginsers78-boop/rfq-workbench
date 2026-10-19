class ExtractionError(Exception):
    """A readable processing failure; no substituted model output is returned."""


class ProcessingCancelled(Exception):
    """A cooperative cancellation or shutdown interrupted document processing."""


class OutputLimitError(ExtractionError):
    """A real model response reached its output token limit."""

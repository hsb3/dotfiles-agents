"""Simple ETL pipeline stages, executed in order: start, extract, transform, load, end."""


def start():
    """Initializes the pipeline run and allocates a run id."""


def extract():
    """Pulls raw records from the source system."""


def transform():
    """Cleans and reshapes records for loading."""


def load():
    """Writes records into the warehouse."""


def end():
    """Finalizes the pipeline run and emits metrics."""

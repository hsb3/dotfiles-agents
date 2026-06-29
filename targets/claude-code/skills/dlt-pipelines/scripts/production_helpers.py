#!/usr/bin/env python3
"""
DLT Production Helper Functions

Reusable utilities for production-grade dlt pipelines:
- Retry logic with exponential backoff
- Error classification (transient vs terminal)
- Configuration management
- Testing utilities
"""

import time
import logging
import os
from typing import Any, Callable, Optional
import dlt

logger = logging.getLogger(__name__)


def run_with_retry(
    pipeline,
    data_source,
    max_retries: int = 3,
    initial_delay: int = 5
) -> Any:
    """
    Run dlt pipeline with automatic retry for transient errors.

    Args:
        pipeline: dlt pipeline instance
        data_source: dlt source or resource to load
        max_retries: Maximum number of retry attempts
        initial_delay: Initial retry delay in seconds (doubles each retry)

    Returns:
        LoadInfo object from successful run

    Raises:
        RuntimeError: If pipeline fails after all retries
    """
    # Errors that indicate transient issues worth retrying
    transient_errors = [
        "connection", "timeout", "refused", "temporarily unavailable",
        "too many connections", "deadlock", "server closed",
        "broken pipe", "reset by peer"
    ]

    retry_delay = initial_delay

    for attempt in range(max_retries):
        try:
            logger.info(f"Pipeline run attempt {attempt + 1}/{max_retries}")
            load_info = pipeline.run(data_source)

            # Check for failed jobs in otherwise successful run
            if load_info.has_failed_jobs:
                failed_jobs = [
                    job for package in load_info.load_packages
                    for job in package.jobs.values()
                    if job.failed_message
                ]

                # Check if failures are transient
                is_transient = any(
                    any(err in str(job.failed_message).lower() for err in transient_errors)
                    for job in failed_jobs
                )

                if is_transient and attempt < max_retries - 1:
                    logger.warning(
                        f"Transient error in jobs, retrying in {retry_delay}s...\n"
                        f"Failed jobs: {[job.job_file_path for job in failed_jobs]}"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    error_details = "\n".join(
                        f"  - {job.job_file_path}: {job.failed_message}"
                        for job in failed_jobs
                    )
                    raise RuntimeError(f"Pipeline failed:\n{error_details}")

            # Success!
            logger.info("Pipeline run completed successfully")
            return load_info

        except Exception as e:
            error_str = str(e).lower()
            is_transient = any(err in error_str for err in transient_errors)

            if is_transient and attempt < max_retries - 1:
                logger.warning(
                    f"Attempt {attempt + 1} failed with transient error: {e}\n"
                    f"Retrying in {retry_delay}s (attempt {attempt + 2}/{max_retries})..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"Pipeline failed after {attempt + 1} attempts: {e}")
                raise

    raise RuntimeError(f"Pipeline failed after {max_retries} attempts")


class ProductionConfig:
    """
    Production configuration manager with environment variable support.

    Provides sensible defaults and environment variable overrides
    while maintaining separation between secrets and config.
    """

    @staticmethod
    def get_config(key: str, default: Any = None) -> Any:
        """
        Get configuration value with fallback chain:
        1. Environment variable (uppercased, dots replaced with underscores)
        2. dlt.config dictionary
        3. Provided default value

        Example:
            get_config("sources.csv.directory", "./data")
            # Checks: $SOURCES_CSV_DIRECTORY -> dlt.config -> "./data"
        """
        # Try environment variable
        env_key = key.upper().replace(".", "_")
        if env_value := os.getenv(env_key):
            return env_value

        # Try dlt config
        try:
            return dlt.config[key]
        except KeyError:
            if default is not None:
                logger.debug(f"Using default for {key}: {default}")
                return default
            raise KeyError(f"Configuration key not found: {key}")

    @staticmethod
    def get_secret(key: str) -> str:
        """
        Get secret value from environment or dlt.secrets.

        Example:
            get_secret("destination.postgres.credentials.password")
            # Checks: $DESTINATION_POSTGRES_CREDENTIALS_PASSWORD -> dlt.secrets
        """
        # Try environment variable
        env_key = key.upper().replace(".", "_")
        if env_value := os.getenv(env_key):
            return env_value

        # Try dlt secrets
        try:
            return dlt.secrets[key]
        except KeyError:
            raise KeyError(
                f"Secret not found: {key}\n"
                f"Set either ${env_key} or add to .dlt/secrets.toml"
            )


class TestPipeline:
    """
    Helper for creating isolated test pipelines.

    Ensures tests don't affect production data by using separate schemas
    and optionally cleaning up after tests complete.
    """

    def __init__(self, base_name: str, test_schema: str = "test_dlt"):
        """
        Args:
            base_name: Base name for test pipeline
            test_schema: Schema/dataset name for test data isolation
        """
        self.base_name = base_name
        self.test_schema = test_schema

    def create_pipeline(self, test_id: Optional[str] = None):
        """
        Create an isolated test pipeline.

        Args:
            test_id: Optional test identifier for uniqueness

        Returns:
            dlt.Pipeline configured for testing
        """
        pipeline_name = f"{self.base_name}_test"
        if test_id:
            pipeline_name += f"_{test_id}"

        return dlt.pipeline(
            pipeline_name=pipeline_name,
            destination="postgres",
            dataset_name=self.test_schema,
            dev_mode=True
        )

    def cleanup(self, pipeline):
        """
        Clean up test data after test completion.

        Args:
            pipeline: Pipeline instance to clean up
        """
        try:
            with pipeline.sql_client() as client:
                client.execute_sql(
                    f"DROP SCHEMA IF EXISTS {self.test_schema} CASCADE"
                )
            logger.info(f"Cleaned up test schema: {self.test_schema}")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


def monitor_schema_changes(load_info) -> None:
    """
    Monitor and log schema changes from pipeline run.

    Useful for detecting unexpected schema drift in production.

    Args:
        load_info: LoadInfo object returned from pipeline.run()
    """
    for package in load_info.load_packages:
        if package.schema_update:
            logger.warning(
                f"Schema changes detected in package {package.load_id}:\n"
                f"{package.schema_update}"
            )
            # In production, you might send alerts here
            # send_slack_alert(f"Schema changed: {package.schema_update}")


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example: Using configuration helper
    csv_dir = ProductionConfig.get_config("sources.csv.directory", "./data")
    print(f"CSV Directory: {csv_dir}")

    # Example: Testing helper
    test_helper = TestPipeline("my_pipeline")
    test_pipeline = test_helper.create_pipeline("example_test")
    print(f"Test pipeline created: {test_pipeline.pipeline_name}")

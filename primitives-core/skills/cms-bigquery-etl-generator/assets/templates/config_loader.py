"""
Configuration Loader with Precedence Handling

Loads and merges configuration from multiple sources:
1. Root project config (../../config.yaml)
2. Dataset-specific config (../config/config.yaml)

Dataset config takes precedence over root config.
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from copy import deepcopy


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Values in override take precedence over values in base.
    Nested dictionaries are merged recursively.

    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    result = deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Override value
            result[key] = deepcopy(value)

    return result


def load_root_config() -> Dict[str, Any]:
    """
    Load root project configuration.

    Returns:
        Root configuration dictionary

    Raises:
        FileNotFoundError: If root config not found
    """
    # Find root config (go up from src/ -> aco_county/ -> datasets/ -> project root)
    root_config_path = Path(__file__).parent.parent.parent.parent / 'config.yaml'

    if not root_config_path.exists():
        raise FileNotFoundError(f"Root config not found at: {root_config_path}")

    with open(root_config_path, 'r') as f:
        return yaml.safe_load(f)


def load_dataset_config() -> Dict[str, Any]:
    """
    Load dataset-specific configuration.

    Returns:
        Dataset configuration dictionary

    Raises:
        FileNotFoundError: If dataset config not found
    """
    # Load from ../config/config.yaml (relative to src/ directory)
    dataset_config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'

    if not dataset_config_path.exists():
        raise FileNotFoundError(f"Dataset config not found at: {dataset_config_path}")

    with open(dataset_config_path, 'r') as f:
        return yaml.safe_load(f)


def normalize_config(root_config: Dict, dataset_config: Dict) -> Dict:
    """
    Normalize configuration by mapping root defaults to expected keys.

    Maps:
    - bigquery.default_project → bigquery.project_id
    - bigquery.default_dataset → bigquery.dataset_id

    Args:
        root_config: Root configuration
        dataset_config: Dataset configuration

    Returns:
        Normalized root configuration
    """
    normalized = deepcopy(root_config)

    # Map default_* keys to standard keys
    if 'bigquery' in normalized:
        bq = normalized['bigquery']

        # Map default_project to project_id if not already set
        if 'default_project' in bq and 'project_id' not in dataset_config.get('bigquery', {}):
            bq['project_id'] = bq['default_project']

        # Map default_dataset to dataset_id if not already set
        if 'default_dataset' in bq and 'dataset_id' not in dataset_config.get('bigquery', {}):
            bq['dataset_id'] = bq['default_dataset']

    return normalized


def resolve_variables(config: Dict, root_config: Dict) -> Dict:
    """
    Resolve variable references in config values.

    Supports ${storage.external_root} and other ${section.key} patterns.

    Args:
        config: Configuration dictionary to resolve
        root_config: Root configuration for variable lookups

    Returns:
        Configuration with variables resolved
    """
    import re

    def resolve_string(value: str) -> str:
        """Resolve variables in a string value."""
        if not isinstance(value, str):
            return value

        # Pattern: ${section.key}
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)

        for match in matches:
            # Parse section.key
            parts = match.split('.')
            if len(parts) == 2:
                section, key = parts
                # Look up value in root config
                if section in root_config and key in root_config[section]:
                    replacement = root_config[section][key]
                    value = value.replace(f'${{{match}}}', str(replacement))

        return value

    def resolve_recursive(obj: Any) -> Any:
        """Recursively resolve variables in nested structures."""
        if isinstance(obj, dict):
            return {k: resolve_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [resolve_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return resolve_string(obj)
        else:
            return obj

    return resolve_recursive(config)


def load_config() -> Dict[str, Any]:
    """
    Load configuration with precedence handling.

    Precedence order (highest to lowest):
    1. Dataset-specific config (../config/config.yaml)
    2. Root project config (../../config.yaml)

    Returns:
        Merged configuration dictionary with dataset settings
        taking precedence over root settings, and variables resolved

    Example:
        >>> config = load_config()
        >>> config['bigquery']['project_id']
        'raptorgpt-nextjs'  # From root
        >>> config['bigquery']['table_id']
        'aco_county_assigned_beneficiaries'  # From dataset
        >>> config['data_source']['data_directory']
        '/path/to/external/CMS_DATAMART/aco_county/data'  # Variable resolved
    """
    # Load both configs
    root_config = load_root_config()
    dataset_config = load_dataset_config()

    # Normalize root config (map default_* keys)
    normalized_root = normalize_config(root_config, dataset_config)

    # Merge: dataset config takes precedence
    merged = deep_merge(normalized_root, dataset_config)

    # Resolve variables (like ${storage.external_root})
    resolved = resolve_variables(merged, root_config)

    return resolved


def get_data_directory(config: Dict) -> Path:
    """
    Get data directory path, resolving variables.

    Supports:
    - Absolute paths
    - ${storage.external_root}/dataset_name/data pattern

    Args:
        config: Configuration dictionary

    Returns:
        Path to data directory
    """
    data_dir = config['data_source']['data_directory']

    # If path starts with ${storage.external_root}, resolve it
    if isinstance(data_dir, str) and '${storage.external_root}' in data_dir:
        external_root = config['storage']['external_root']
        data_dir = data_dir.replace('${storage.external_root}', external_root)

    return Path(data_dir)


def get_data_dictionary_path(config: Dict) -> Path:
    """
    Get data dictionary path, resolving variables.

    Supports:
    - Absolute paths
    - ${storage.external_root}/_config/data_dictionaries/ pattern

    Args:
        config: Configuration dictionary

    Returns:
        Path to data dictionary
    """
    dict_path = config['data_source']['data_dictionary']

    # If path starts with ${storage.external_root}, resolve it
    if isinstance(dict_path, str) and '${storage.external_root}' in dict_path:
        external_root = config['storage']['external_root']
        dict_path = dict_path.replace('${storage.external_root}', external_root)

    return Path(dict_path)


def print_config_summary(config: Dict) -> None:
    """
    Print a summary of the loaded configuration.

    Args:
        config: Configuration dictionary
    """
    print("Configuration Summary")
    print("=" * 60)

    if 'project' in config:
        print(f"Project: {config['project']['name']} v{config['project']['version']}")

    if 'bigquery' in config:
        bq = config['bigquery']
        print(f"\nBigQuery:")
        print(f"  Project: {bq.get('project_id', 'N/A')}")
        print(f"  Dataset: {bq.get('dataset_id', 'N/A')}")
        print(f"  Table: {bq.get('table_id', 'N/A')}")
        print(f"  Location: {bq.get('location', 'N/A')}")

    if 'data_source' in config:
        ds = config['data_source']
        print(f"\nData Source:")
        print(f"  Directory: {ds.get('data_directory', 'N/A')}")
        print(f"  Pattern: {ds.get('file_pattern', 'N/A')}")

    if 'validation' in config:
        val = config['validation']
        print(f"\nValidation:")
        print(f"  Pre-load: {val.get('validate_before_load', False)}")
        print(f"  Fail on error: {val.get('fail_on_validation_error', False)}")

    print("=" * 60)


if __name__ == "__main__":
    # Test config loading
    config = load_config()
    print_config_summary(config)

    print("\nConfig sources:")
    print(f"  Root: ../../config.yaml")
    print(f"  Dataset: ../config/config.yaml")
    print(f"\nMerge strategy: Dataset config overrides root config")

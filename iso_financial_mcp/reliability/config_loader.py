"""
Configuration loader for datasources.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .models import SourceConfig, RetryStrategy

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads and validates configuration from YAML files.
    Loads bundled default config first, then merges with user config if present.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config loader.
        
        Args:
            config_path: Path to user YAML config file (overrides default)
        """
        if config_path is None:
            config_path = os.path.expanduser(
                "~/.iso_financial_mcp/config/datasources.yaml"
            )
        
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        
        # Path to bundled default config
        self.default_config_path = Path(__file__).parent / "default_config.yaml"
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from files.
        Loads bundled default config first, then merges with user config.
        
        Returns:
            Configuration dictionary
        """
        if self._config is not None:
            return self._config
        
        # Load bundled default config
        config = self._load_default_config()
        
        # Load from file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                
                if file_config:
                    # Merge with defaults
                    config = self._merge_configs(config, file_config)
                    logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading config from {self.config_path}: {e}")
                logger.info("Using default configuration")
        else:
            logger.info(
                f"Config file not found at {self.config_path}, using defaults"
            )
        
        # Substitute environment variables
        config = self._substitute_env_vars(config)
        
        # Validate configuration
        if not self.validate_config(config):
            logger.warning("Configuration validation failed, using defaults")
            config = self._get_fallback_config()
        
        self._config = config
        return config
    
    def _merge_configs(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """
        Recursively substitute environment variables in config.
        
        Supports syntax:
        - ${VAR_NAME} - Required environment variable
        - ${VAR_NAME:default} - Optional with default value
        """
        if isinstance(config, dict):
            return {
                key: self._substitute_env_vars(value)
                for key, value in config.items()
            }
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # Extract env var name
            env_var = config[2:-1]
            default = None
            
            # Check for default value syntax: ${VAR:default}
            if ":" in env_var:
                env_var, default = env_var.split(":", 1)
            
            value = os.getenv(env_var, default)
            
            if value is None:
                logger.warning(
                    f"Environment variable {env_var} not set and no default provided"
                )
                return config
            
            return value
        else:
            return config
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure and required fields.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_sections = ["sec", "trends", "earnings", "cache", "health_monitor"]
        
        for section in required_sections:
            if section not in config:
                logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Validate SEC configuration
        if "sources" not in config["sec"]:
            logger.error("SEC configuration missing 'sources' field")
            return False
        
        # Validate Trends configuration
        if "sources" not in config["trends"]:
            logger.error("Trends configuration missing 'sources' field")
            return False
        
        # Validate Earnings configuration
        if "sources" not in config["earnings"]:
            logger.error("Earnings configuration missing 'sources' field")
            return False
        
        # Validate cache configuration
        cache_config = config["cache"]
        if "memory" not in cache_config or "disk" not in cache_config:
            logger.error("Cache configuration missing 'memory' or 'disk' section")
            return False
        
        # Validate health monitor configuration
        health_config = config["health_monitor"]
        required_health_fields = ["enabled", "window_size", "unhealthy_threshold"]
        for field in required_health_fields:
            if field not in health_config:
                logger.error(f"Health monitor configuration missing '{field}' field")
                return False
        
        logger.info("Configuration validation passed")
        return True
    
    def get_source_config(self, data_type: str, source_name: str) -> Optional[SourceConfig]:
        """
        Get configuration for a specific source.
        
        Args:
            data_type: Type of data (sec, trends, earnings)
            source_name: Name of the source
            
        Returns:
            SourceConfig or None if not found
        """
        config = self.load()
        
        if data_type not in config:
            return None
        
        sources = config[data_type].get("sources", [])
        
        for source in sources:
            if source.get("name") == source_name:
                return SourceConfig(
                    name=source.get("name"),
                    enabled=source.get("enabled", True),
                    priority=source.get("priority", 1),
                    timeout_seconds=source.get("timeout", 10),
                    max_retries=source.get("max_retries", 2),
                    retry_delay_seconds=source.get("retry_delay", 1.0),
                    rate_limit_per_second=source.get("rate_limit", 1.0),
                    requires_api_key=source.get("requires_api_key", False),
                    api_key_env_var=source.get("api_key_env")
                )
        
        return None
    
    def get_retry_strategy(self, data_type: str) -> RetryStrategy:
        """
        Get retry strategy for a data type.
        
        Args:
            data_type: Type of data (sec, trends, earnings)
            
        Returns:
            RetryStrategy
        """
        config = self.load()
        
        if data_type in config and "retry_strategy" in config[data_type]:
            retry_config = config[data_type]["retry_strategy"]
            return RetryStrategy(
                max_attempts=retry_config.get("max_attempts", 3),
                initial_delay=retry_config.get("initial_delay", 10.0),
                max_delay=retry_config.get("max_delay", 60.0),
                exponential_base=retry_config.get("exponential_base", 2.0),
                jitter_range=tuple(retry_config.get("jitter_range", [1.0, 3.0]))
            )
        
        return RetryStrategy()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load bundled default configuration."""
        try:
            with open(self.default_config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading default config: {e}")
            return self._get_fallback_config()
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get hardcoded fallback configuration if files are missing."""
        return {
            "sec": {
                "sources": [
                    {"name": "edgar_api", "enabled": True, "priority": 1, "timeout": 10, "max_retries": 2}
                ],
                "lookback_extension": {"enabled": True, "initial_days": 30, "extended_days": 90}
            },
            "trends": {
                "sources": [
                    {"name": "pytrends_direct", "enabled": True, "priority": 1, "rate_limit": 0.2, "timeout": 15}
                ],
                "retry_strategy": {
                    "max_attempts": 3, "initial_delay": 10, "max_delay": 60,
                    "exponential_base": 2.0, "jitter_range": [1.0, 3.0]
                },
                "adaptive_rate_limit": {"enabled": True, "error_threshold": 0.5, "slow_mode_delay": 10}
            },
            "earnings": {
                "sources": [
                    {"name": "yahoo_finance", "enabled": True, "priority": 1}
                ],
                "merge_strategy": "deduplicate_by_date",
                "estimate_fallback": True,
                "require_future_date": True
            },
            "cache": {
                "memory": {"max_size": 1000, "ttl_seconds": 3600},
                "disk": {
                    "enabled": True, "path": "~/.iso_financial_mcp/cache",
                    "ttl_seconds": 604800, "max_size_mb": 500
                },
                "stale_fallback": True
            },
            "health_monitor": {
                "enabled": True, "window_size": 100, "unhealthy_threshold": 0.3,
                "metrics_retention_days": 7, "log_path": "~/.iso_financial_mcp/health_metrics.jsonl"
            }
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration."""
        config = self.load()
        default = self._get_fallback_config()
        return config.get("cache", default["cache"])
    
    def get_health_monitor_config(self) -> Dict[str, Any]:
        """Get health monitor configuration."""
        config = self.load()
        default = self._get_fallback_config()
        return config.get("health_monitor", default["health_monitor"])
    
    def get_enabled_sources(self, data_type: str) -> list[Dict[str, Any]]:
        """
        Get list of enabled sources for a data type, sorted by priority.
        
        Args:
            data_type: Type of data (sec, trends, earnings)
            
        Returns:
            List of enabled source configurations, sorted by priority
        """
        config = self.load()
        
        if data_type not in config:
            return []
        
        sources = config[data_type].get("sources", [])
        
        # Filter enabled sources and sort by priority
        enabled = [s for s in sources if s.get("enabled", True)]
        enabled.sort(key=lambda s: s.get("priority", 999))
        
        return enabled
    
    def get_data_type_config(self, data_type: str) -> Dict[str, Any]:
        """
        Get full configuration for a data type.
        
        Args:
            data_type: Type of data (sec, trends, earnings)
            
        Returns:
            Configuration dictionary for the data type
        """
        config = self.load()
        default = self._get_fallback_config()
        return config.get(data_type, default.get(data_type, {}))

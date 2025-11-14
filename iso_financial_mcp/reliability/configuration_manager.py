"""
Configuration Manager with multi-source support and priority handling.

Supports configuration from multiple sources with priority order:
1. MCP tools (runtime configuration) - highest priority
2. Environment variables
3. YAML file (~/.iso_financial_mcp/config/datasources.yaml)
4. Default values - lowest priority
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import yaml

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages configuration with multi-source support and priority handling.
    
    Priority order (highest to lowest):
    1. MCP tools (runtime configuration)
    2. Environment variables
    3. YAML file
    4. Default values
    """
    
    def __init__(self, yaml_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            yaml_path: Path to YAML config file (default: ~/.iso_financial_mcp/config/datasources.yaml)
        """
        # MCP config (runtime, highest priority)
        self.mcp_config: Dict[str, Any] = {}
        
        # YAML config path
        if yaml_path is None:
            yaml_path = os.path.expanduser("~/.iso_financial_mcp/config/datasources.yaml")
        self.yaml_path = Path(yaml_path)
        
        # Load configurations
        self.env_config = self._load_env_config()
        self.yaml_config = self._load_yaml_config()
        self.default_config = self._load_default_config()
        
        # Validation cache: {(provider, key): (is_valid, timestamp)}
        self._validation_cache: Dict[Tuple[str, str], Tuple[bool, float]] = {}
        self._validation_cache_ttl = 300  # 5 minutes
        
        logger.info("ConfigurationManager initialized")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with priority handling.
        
        Priority order:
        1. MCP config (runtime)
        2. Environment variables
        3. YAML file
        4. Default config
        5. Provided default parameter
        
        Args:
            key: Configuration key (supports dot notation, e.g., "alpha_vantage.api_key")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Check MCP config first (highest priority)
        value = self._get_nested(self.mcp_config, key)
        if value is not None:
            return value
        
        # Check environment variables
        env_key = key.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # Check YAML config
        value = self._get_nested(self.yaml_config, key)
        if value is not None:
            return value
        
        # Check default config
        value = self._get_nested(self.default_config, key)
        if value is not None:
            return value
        
        return default
    
    def set_mcp_config(self, key: str, value: Any) -> None:
        """
        Set configuration via MCP tools (highest priority).
        Persists to YAML file for next session.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Configuration value
        """
        # Set in MCP config (runtime)
        self._set_nested(self.mcp_config, key, value)
        
        # Persist to YAML file
        self._persist_to_yaml(key, value)
        
        logger.info(f"Configuration set via MCP: {key}")
    
    def get_all_config(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """
        Get all configuration merged with priority handling.
        
        Args:
            mask_secrets: If True, mask API keys (show only last 4 characters)
            
        Returns:
            Merged configuration dictionary
        """
        # Start with defaults
        merged = self._deep_copy(self.default_config)
        
        # Merge YAML config
        merged = self._merge_configs(merged, self.yaml_config)
        
        # Merge environment variables
        merged = self._merge_configs(merged, self.env_config)
        
        # Merge MCP config (highest priority)
        merged = self._merge_configs(merged, self.mcp_config)
        
        # Mask secrets if requested
        if mask_secrets:
            merged = self._mask_secrets(merged)
        
        return merged
    
    def _load_env_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Supports:
        - ALPHA_VANTAGE_API_KEY -> alpha_vantage.api_key
        - SERPAPI_API_KEY -> serpapi.api_key
        """
        config = {}
        
        # API keys
        if os.getenv("ALPHA_VANTAGE_API_KEY"):
            self._set_nested(config, "alpha_vantage.api_key", os.getenv("ALPHA_VANTAGE_API_KEY"))
        
        if os.getenv("SERPAPI_API_KEY"):
            self._set_nested(config, "serpapi.api_key", os.getenv("SERPAPI_API_KEY"))
        
        # Cache configuration
        if os.getenv("CACHE_MEMORY_TTL_SECONDS"):
            self._set_nested(config, "cache.memory.ttl_seconds", int(os.getenv("CACHE_MEMORY_TTL_SECONDS")))
        
        if os.getenv("CACHE_DISK_TTL_SECONDS"):
            self._set_nested(config, "cache.disk.ttl_seconds", int(os.getenv("CACHE_DISK_TTL_SECONDS")))
        
        if os.getenv("CACHE_DISK_MAX_SIZE_MB"):
            self._set_nested(config, "cache.disk.max_size_mb", int(os.getenv("CACHE_DISK_MAX_SIZE_MB")))
        
        return config
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.yaml_path.exists():
            logger.debug(f"YAML config file not found: {self.yaml_path}")
            return {}
        
        try:
            with open(self.yaml_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded YAML config from {self.yaml_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading YAML config: {e}")
            return {}
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        # Path to bundled default config
        default_path = Path(__file__).parent / "default_config.yaml"
        
        try:
            with open(default_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            return config
        except Exception as e:
            logger.error(f"Error loading default config: {e}")
            return self._get_hardcoded_defaults()
    
    def _get_hardcoded_defaults(self) -> Dict[str, Any]:
        """Get hardcoded fallback defaults."""
        return {
            "cache": {
                "memory": {
                    "ttl_seconds": 3600,
                    "max_size": 1000
                },
                "disk": {
                    "enabled": True,
                    "ttl_seconds": 604800,
                    "max_size_mb": 500,
                    "path": "~/.iso_financial_mcp/cache"
                }
            },
            "alpha_vantage": {
                "enabled": False,
                "api_key": None
            },
            "serpapi": {
                "enabled": False,
                "api_key": None
            }
        }
    
    def _persist_to_yaml(self, key: str, value: Any) -> None:
        """
        Persist configuration to YAML file.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        # Ensure directory exists
        self.yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing YAML config
        if self.yaml_path.exists():
            try:
                with open(self.yaml_path, 'r') as f:
                    yaml_data = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error reading YAML for persistence: {e}")
                yaml_data = {}
        else:
            yaml_data = {}
        
        # Update with new value
        self._set_nested(yaml_data, key, value)
        
        # Write back to file
        try:
            with open(self.yaml_path, 'w') as f:
                yaml.safe_dump(yaml_data, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Persisted configuration to {self.yaml_path}")
        except Exception as e:
            logger.error(f"Error persisting to YAML: {e}")
    
    def _get_nested(self, config: Dict[str, Any], key: str) -> Any:
        """
        Get nested value from config using dot notation.
        
        Args:
            config: Configuration dictionary
            key: Key with dot notation (e.g., "alpha_vantage.api_key")
            
        Returns:
            Value or None if not found
        """
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def _set_nested(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """
        Set nested value in config using dot notation.
        
        Args:
            config: Configuration dictionary
            key: Key with dot notation
            value: Value to set
        """
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge configuration dictionaries.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _deep_copy(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deep copy configuration dictionary."""
        import copy
        return copy.deepcopy(config)
    
    def _mask_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask API keys and secrets in configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with masked secrets
        """
        import copy
        masked = copy.deepcopy(config)
        
        # Keys to mask
        secret_keys = ['api_key', 'password', 'secret', 'token']
        
        def mask_recursive(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: mask_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [mask_recursive(item) for item in obj]
            elif isinstance(obj, str):
                # Check if parent key suggests this is a secret
                return obj
            else:
                return obj
        
        def mask_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for key, value in d.items():
                if any(secret in key.lower() for secret in secret_keys):
                    if isinstance(value, str) and len(value) > 4:
                        result[key] = f"...{value[-4:]}"
                    elif isinstance(value, str):
                        result[key] = "****"
                    else:
                        result[key] = value
                elif isinstance(value, dict):
                    result[key] = mask_dict(value)
                else:
                    result[key] = value
            return result
        
        return mask_dict(masked)
    
    async def validate_api_key(self, provider: str, api_key: str) -> Tuple[bool, str]:
        """
        Validate an API key by making a test request.
        Results are cached for 5 minutes.
        
        Args:
            provider: Provider name (alpha_vantage, serpapi)
            api_key: API key to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Check cache first
        cache_key = (provider, api_key)
        if cache_key in self._validation_cache:
            is_valid, timestamp = self._validation_cache[cache_key]
            if time.time() - timestamp < self._validation_cache_ttl:
                logger.debug(f"Using cached validation result for {provider}")
                return is_valid, "Cached validation result"
        
        # Validate based on provider
        if provider == "alpha_vantage":
            is_valid, message = await self._validate_alpha_vantage(api_key)
        elif provider == "serpapi":
            is_valid, message = await self._validate_serpapi(api_key)
        else:
            return False, f"Unknown provider: {provider}"
        
        # Cache result
        self._validation_cache[cache_key] = (is_valid, time.time())
        
        return is_valid, message
    
    async def _validate_alpha_vantage(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate Alpha Vantage API key.
        
        Note: Alpha Vantage doesn't strictly validate API keys for basic requests.
        This validation primarily checks API reachability and rate limits.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if httpx is None:
            return False, "httpx not installed"
        
        # Use TIME_SERIES_INTRADAY to check API reachability
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=AAPL&interval=5min&apikey={api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return False, f"HTTP {response.status_code}"
                
                data = response.json()
                
                # Check for error messages
                if "Error Message" in data:
                    return False, "Invalid API key or request"
                
                if "Information" in data:
                    # This usually means invalid key or rate limit
                    info = data["Information"]
                    if "invalid" in info.lower() or "api key" in info.lower():
                        return False, "Invalid API key"
                    if "premium" in info.lower() or "rate limit" in info.lower():
                        return False, "API rate limit exceeded"
                    return False, info
                
                if "Note" in data:
                    # Rate limit message
                    return False, "API rate limit exceeded"
                
                # Valid response should have Time Series data or Meta Data
                if "Time Series (5min)" in data or "Meta Data" in data:
                    return True, "API key validated successfully"
                
                return False, "Unexpected response format"
                
        except asyncio.TimeoutError:
            return False, "Validation timeout (5s)"
        except Exception as e:
            logger.error(f"Error validating Alpha Vantage key: {e}")
            return False, f"Validation error: {str(e)}"
    
    async def _validate_serpapi(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate SerpAPI key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if httpx is None:
            return False, "httpx not installed"
        
        url = f"https://serpapi.com/search?q=test&api_key={api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    return True, "API key validated successfully"
                elif response.status_code == 401:
                    return False, "Invalid API key"
                elif response.status_code == 429:
                    return False, "API rate limit exceeded"
                else:
                    return False, f"HTTP {response.status_code}"
                    
        except asyncio.TimeoutError:
            return False, "Validation timeout (5s)"
        except Exception as e:
            logger.error(f"Error validating SerpAPI key: {e}")
            return False, f"Validation error: {str(e)}"

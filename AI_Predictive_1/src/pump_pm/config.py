"""
config.py
---------
Centralized configuration manager for pump_pm. Loads and validates YAML configurations.
"""

import os
from typing import Dict, Any, Optional
import yaml

# Base project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")


class ConfigManager:
    _instance = None

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self._app_config: Optional[Dict[str, Any]] = None
        self._machine_config: Optional[Dict[str, Any]] = None
        self._standards_limits: Optional[Dict[str, Any]] = None
        self._diagnostic_rules: Optional[Dict[str, Any]] = None
        self.reload()

    @classmethod
    def get_instance(cls, config_dir: Optional[str] = None) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = ConfigManager(config_dir)
        return cls._instance

    def reload(self):
        self._app_config = self._load_yaml(os.path.join(self.config_dir, "app.yaml"))
        self._machine_config = self._load_yaml(os.path.join(self.config_dir, "machine_config.yaml"))
        self._standards_limits = self._load_yaml(os.path.join(self.config_dir, "standards_limits.yaml"))
        self._diagnostic_rules = self._load_yaml(os.path.join(self.config_dir, "diagnostic_rules.yaml"))

    @staticmethod
    def _load_yaml(filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def app(self) -> Dict[str, Any]:
        return self._app_config or {}

    @property
    def machines(self) -> Dict[str, Any]:
        return (self._machine_config or {}).get("machines", {})

    @property
    def standards(self) -> Dict[str, Any]:
        return self._standards_limits or {}

    @property
    def rules(self) -> Dict[str, Any]:
        return (self._diagnostic_rules or {}).get("rules", {})

    def get_machine(self, machine_id: str) -> Optional[Dict[str, Any]]:
        return self.machines.get(machine_id)

    def get_path(self, key: str) -> str:
        rel_path = self.app.get("paths", {}).get(key, "")
        return os.path.join(PROJECT_ROOT, rel_path)

    def get_standards_limits(self, category: str, power_kw: float) -> Optional[Dict[str, Any]]:
        """
        Retrieves ISO 10816-7 / Europump 2013 Table 1 limits for a category and power rating.
        """
        severity_limits = self.standards.get("severity_limits", {})
        cat_key = category.lower().replace(" ", "_")
        if cat_key not in severity_limits:
            return None

        cat_cfg = severity_limits[cat_key]
        if power_kw <= 200.0:
            return cat_cfg.get("power_le_200kw")
        else:
            return cat_cfg.get("power_gt_200kw")


def get_config() -> ConfigManager:
    return ConfigManager.get_instance()

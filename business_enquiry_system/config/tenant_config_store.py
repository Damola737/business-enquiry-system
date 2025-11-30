import json
import os
from pathlib import Path
from typing import Dict, Any


class TenantConfigStore:
    """
    Lightweight loader/cacher for tenant configuration files.

    For now this is file-based:
    - Looks in config/tenants/{tenant_key}.json
    - Falls back to 'legacy-ng-telecom' if a specific tenant config is missing.
    """

    _instance = None

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self._cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "TenantConfigStore":
        if cls._instance is None:
            root = Path(__file__).resolve().parent
            tenants_dir = root / "tenants"
            cls._instance = cls(base_path=tenants_dir)
        return cls._instance

    def _load_from_disk(self, tenant_key: str) -> Dict[str, Any]:
        path = self.base_path / f"{tenant_key}.json"
        if not path.is_file():
            raise FileNotFoundError(str(path))
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def get_config(self, tenant_key: str) -> Dict[str, Any]:
        """
        Return configuration for a tenant.

        If the specific tenant file is missing, we fall back to legacy-ng-telecom
        so that the system remains backwards compatible.
        """
        key = tenant_key or "legacy-ng-telecom"
        if key in self._cache:
            return self._cache[key]

        try:
            cfg = self._load_from_disk(key)
        except Exception:
            # Fallback to legacy tenant
            if key != "legacy-ng-telecom":
                cfg = self._load_from_disk("legacy-ng-telecom")
            else:
                cfg = {}

        # Make sure the tenant_key is present in the config
        cfg.setdefault("tenant_key", key)
        self._cache[key] = cfg
        return cfg


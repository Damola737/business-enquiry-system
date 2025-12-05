"""
Skill loader for tenant-specific playbooks.

Phase 8 Implementation: Hot-loadable skills with:
- SKILL.md playbook files
- forms.json for slot filling
- prompts.json for skill-specific prompts
- examples.json for few-shot examples
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SkillSlot:
    """A slot that needs to be filled during skill execution."""
    name: str
    type: str  # string, number, phone, email, meter_number
    required: bool = True
    prompt: str = ""  # Question to ask for this slot
    validation: Optional[str] = None  # Regex or validation rule
    examples: List[str] = field(default_factory=list)


@dataclass
class SkillForm:
    """Form definition for slot-filling workflows."""
    name: str
    slots: List[SkillSlot]
    submit_action: str  # Tool or action to call when form is complete
    confirmation_required: bool = False


@dataclass
class Skill:
    """
    A loadable skill definition for a tenant.
    
    Skills are stored in:
    skills/definitions/<tenant_id>/<skill_name>/
    - SKILL.md: Playbook/instructions
    - forms.json: Slot definitions
    - prompts.json: Skill-specific prompts
    - examples.json: Few-shot examples
    """
    tenant_id: str
    name: str
    path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Loaded content
    playbook: str = ""
    forms: List[SkillForm] = field(default_factory=list)
    prompts: Dict[str, str] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    # Skill configuration
    enabled: bool = True
    domains: List[str] = field(default_factory=list)  # Domains this skill applies to
    intents: List[str] = field(default_factory=list)  # Intents this skill handles
    priority: int = 0  # Higher priority skills are checked first
    
    def get_form(self, name: str) -> Optional[SkillForm]:
        """Get a form by name."""
        for form in self.forms:
            if form.name == name:
                return form
        return None
    
    def get_prompt(self, key: str, default: str = "") -> str:
        """Get a skill-specific prompt."""
        return self.prompts.get(key, default)
    
    def matches_context(self, domain: Optional[str], intent: Optional[str]) -> bool:
        """Check if this skill matches the given context."""
        if self.domains and domain and domain.lower() not in [d.lower() for d in self.domains]:
            return False
        if self.intents and intent and intent.lower() not in [i.lower() for i in self.intents]:
            return False
        return True


class SkillLoader:
    """
    Loader for tenant-specific skills.
    
    Skills are organized by tenant and loaded on demand.
    Supports hot-reloading for development.
    """
    
    def __init__(self, root: Optional[str] = None) -> None:
        base = root or os.path.join(os.path.dirname(__file__), "definitions")
        self.base = Path(base)
        self._cache: Dict[str, List[Skill]] = {}
    
    def list_skills(self, tenant_id: str, use_cache: bool = True) -> List[Skill]:
        """List all skills for a tenant."""
        if use_cache and tenant_id in self._cache:
            return self._cache[tenant_id]
        
        tenant_dir = self.base / tenant_id
        if not tenant_dir.is_dir():
            return []
        
        skills: List[Skill] = []
        for child in tenant_dir.iterdir():
            if child.is_dir():
                skill = self._load_skill_from_dir(tenant_id, child)
                if skill and skill.enabled:
                    skills.append(skill)
        
        # Sort by priority
        skills.sort(key=lambda s: -s.priority)
        
        self._cache[tenant_id] = skills
        return skills
    
    def _load_skill_from_dir(self, tenant_id: str, skill_dir: Path) -> Optional[Skill]:
        """Load a skill from its directory."""
        skill = Skill(
            tenant_id=tenant_id,
            name=skill_dir.name,
            path=skill_dir,
        )
        
        # Load SKILL.md playbook
        skill_md = skill_dir / "SKILL.md"
        if skill_md.is_file():
            with skill_md.open("r", encoding="utf-8") as f:
                skill.playbook = f.read()
                # Parse metadata from frontmatter if present
                self._parse_playbook_metadata(skill)
        
        # Load forms.json
        forms_file = skill_dir / "forms.json"
        if forms_file.is_file():
            with forms_file.open("r", encoding="utf-8") as f:
                forms_data = json.load(f)
                skill.forms = self._parse_forms(forms_data)
                skill.metadata["forms"] = forms_data
        
        # Load prompts.json
        prompts_file = skill_dir / "prompts.json"
        if prompts_file.is_file():
            with prompts_file.open("r", encoding="utf-8") as f:
                skill.prompts = json.load(f)
        
        # Load examples.json
        examples_file = skill_dir / "examples.json"
        if examples_file.is_file():
            with examples_file.open("r", encoding="utf-8") as f:
                skill.examples = json.load(f)
        
        # Load config.json for skill settings
        config_file = skill_dir / "config.json"
        if config_file.is_file():
            with config_file.open("r", encoding="utf-8") as f:
                config = json.load(f)
                skill.enabled = config.get("enabled", True)
                skill.domains = config.get("domains", [])
                skill.intents = config.get("intents", [])
                skill.priority = config.get("priority", 0)
        
        return skill
    
    def _parse_playbook_metadata(self, skill: Skill) -> None:
        """Parse metadata from SKILL.md frontmatter."""
        lines = skill.playbook.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("- Domains:"):
                domains = line.replace("- Domains:", "").strip()
                skill.domains = [d.strip() for d in domains.split(",")]
            elif line.startswith("- Intents:"):
                intents = line.replace("- Intents:", "").strip()
                skill.intents = [i.strip() for i in intents.split(",")]
            elif line.startswith("- Priority:"):
                try:
                    skill.priority = int(line.replace("- Priority:", "").strip())
                except ValueError:
                    pass
    
    def _parse_forms(self, forms_data: Any) -> List[SkillForm]:
        """Parse form definitions from JSON."""
        forms = []
        if isinstance(forms_data, list):
            for form_data in forms_data:
                form = self._parse_single_form(form_data)
                if form:
                    forms.append(form)
        elif isinstance(forms_data, dict):
            for name, form_data in forms_data.items():
                form_data["name"] = name
                form = self._parse_single_form(form_data)
                if form:
                    forms.append(form)
        return forms
    
    def _parse_single_form(self, data: Dict[str, Any]) -> Optional[SkillForm]:
        """Parse a single form definition."""
        if not isinstance(data, dict):
            return None
        
        slots = []
        slots_data = data.get("slots", [])
        for slot_data in slots_data:
            slot = SkillSlot(
                name=slot_data.get("name", ""),
                type=slot_data.get("type", "string"),
                required=slot_data.get("required", True),
                prompt=slot_data.get("prompt", ""),
                validation=slot_data.get("validation"),
                examples=slot_data.get("examples", []),
            )
            slots.append(slot)
        
        return SkillForm(
            name=data.get("name", ""),
            slots=slots,
            submit_action=data.get("submit_action", ""),
            confirmation_required=data.get("confirmation_required", False),
        )
    
    def load_skill(self, tenant_id: str, name: str) -> Optional[Skill]:
        """Load a specific skill by name."""
        for skill in self.list_skills(tenant_id):
            if skill.name == name:
                return skill
        return None
    
    def find_matching_skills(
        self,
        tenant_id: str,
        domain: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> List[Skill]:
        """Find skills that match the given context."""
        skills = self.list_skills(tenant_id)
        return [s for s in skills if s.matches_context(domain, intent)]
    
    def reload_tenant(self, tenant_id: str) -> List[Skill]:
        """Force reload skills for a tenant (hot reload)."""
        if tenant_id in self._cache:
            del self._cache[tenant_id]
        return self.list_skills(tenant_id, use_cache=False)
    
    def get_skill_playbook(self, tenant_id: str, skill_name: str) -> str:
        """Get the playbook content for a skill."""
        skill = self.load_skill(tenant_id, skill_name)
        return skill.playbook if skill else ""
    
    def get_skill_examples(
        self,
        tenant_id: str,
        skill_name: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get few-shot examples for a skill."""
        skill = self.load_skill(tenant_id, skill_name)
        if not skill:
            return []
        return skill.examples[:limit]


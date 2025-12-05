"""
Skills system for tenant-specific playbooks.

Implements Phase 8:
- Hot-loadable skill definitions
- SKILL.md playbooks with domain/intent matching
- forms.json for slot-filling workflows
- examples.json for few-shot learning
- config.json for skill configuration

Usage:
    from skills import SkillLoader, Skill
    
    loader = SkillLoader()
    skills = loader.list_skills("legacy-ng-telecom")
    skill = loader.load_skill("legacy-ng-telecom", "airtime_purchase")
    playbook = skill.playbook
"""

from skills.loader import (
    Skill,
    SkillSlot,
    SkillForm,
    SkillLoader,
)

__all__ = [
    "Skill",
    "SkillSlot",
    "SkillForm",
    "SkillLoader",
]


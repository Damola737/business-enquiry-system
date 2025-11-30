# agents/research_agent.py
"""
Research Agent Module
Searches knowledge base and retrieves relevant documentation
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from agents.base_agent import BaseBusinessAgent
import os
import re


class ResearchAgent(BaseBusinessAgent):
    """
    Research agent that searches internal knowledge base and documentation
    """

    SYSTEM_MESSAGE = """You are the Research Agent for TechCorp Solutions.
    Search KB, synthesize findings, provide sources and confidence.
    """

    def __init__(self, llm_config: Dict[str, Any], knowledge_base_path: str = None):
        super().__init__(
            name="research_agent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Searches knowledge base and retrieves relevant documentation"
        )
        self.knowledge_base_path = knowledge_base_path or "./knowledge_base"
        self.documents = self._load_knowledge_base()
        self.search_index = self._build_search_index()
        self.cache: Dict[str, Any] = {}

    def _load_knowledge_base(self) -> Dict[str, Any]:
        """
        Load KB from filesystem plus a tiny seed.

        Backward compatible:
        - Supports legacy layout: knowledge_base/{airtime,power,data}
        - Prepares for tenant layout: knowledge_base/tenants/{tenant_id}/{category}
        """
        docs: Dict[str, Any] = {"files": {}, "faqs": []}

        base = os.path.abspath(self.knowledge_base_path)
        # Legacy single-tenant layout
        legacy_domains = ["airtime", "power", "data"]
        for domain in legacy_domains:
            dpath = os.path.join(base, domain)
            if not os.path.isdir(dpath):
                continue
            for root, _, files in os.walk(dpath):
                for fn in files:
                    if not (fn.endswith(".md") or fn.endswith(".txt")):
                        continue
                    fpath = os.path.join(root, fn)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                        title, tags, updated = self._parse_doc_header(content)
                        rel = os.path.relpath(fpath, base).replace(os.sep, "/")
                        doc_id = f"kb.{domain}.{rel}"
                        docs["files"][doc_id] = {
                            "title": title or os.path.splitext(fn)[0],
                            "content": content,
                            "tags": tags,
                            "domain": domain.upper(),
                            "last_updated": updated or "",
                        }
                    except Exception:
                        continue

        # Tenant-aware layout (future-friendly, no-op if folders absent)
        tenants_root = os.path.join(base, "tenants")
        if os.path.isdir(tenants_root):
            for tenant_id in os.listdir(tenants_root):
                tenant_path = os.path.join(tenants_root, tenant_id)
                if not os.path.isdir(tenant_path):
                    continue
                for category in os.listdir(tenant_path):
                    cat_path = os.path.join(tenant_path, category)
                    if not os.path.isdir(cat_path):
                        continue
                    for root, _, files in os.walk(cat_path):
                        for fn in files:
                            if not (fn.endswith(".md") or fn.endswith(".txt")):
                                continue
                            fpath = os.path.join(root, fn)
                            try:
                                with open(fpath, "r", encoding="utf-8") as f:
                                    content = f.read()
                                title, tags, updated = self._parse_doc_header(content)
                                rel = os.path.relpath(fpath, tenants_root).replace(os.sep, "/")
                                # doc_id encodes tenant and category
                                doc_id = f"kb.{tenant_id}.{category}.{rel}"
                                docs["files"][doc_id] = {
                                    "title": title or os.path.splitext(fn)[0],
                                    "content": content,
                                    "tags": tags,
                                    "domain": category.upper(),
                                    "tenant_id": tenant_id,
                                    "last_updated": updated or "",
                                }
                            except Exception:
                                continue

        # Fallback seed if KB empty
        if not docs["files"]:
            docs["files"]["kb.airtime.sample_pricing"] = {
                "title": "Airtime Pricing & Limits",
                "content": "Minimum ₦50, maximum ₦50,000. Bulk discount 5% for ₦10,000+.",
                "tags": ["pricing", "limits"],
                "domain": "AIRTIME",
                "last_updated": ""
            }
        self.logger.info(f"Loaded KB docs: {len(docs['files'])} from {base}")
        return docs

    def _parse_doc_header(self, content: str) -> Tuple[Optional[str], List[str], Optional[str]]:
        """Parse simple header lines: Title:, Tags:, Updated:"""
        title = None
        tags: List[str] = []
        updated = None
        for line in content.splitlines()[:12]:
            l = line.strip()
            if l.lower().startswith("title:"):
                title = l.split(":", 1)[1].strip()
            elif l.lower().startswith("tags:"):
                raw = l.split(":", 1)[1]
                tags = [t.strip() for t in re.split(r"[,|]", raw) if t.strip()]
            elif l.lower().startswith("updated:"):
                updated = l.split(":", 1)[1].strip()
        return title, tags, updated

    def _build_search_index(self) -> Dict[str, List[str]]:
        index: Dict[str, List[str]] = {}
        def index_document(doc_id: str, content: str, tags: List[str] = None):
            for w in content.lower().split():
                w = w.strip('.,!?;:')
                if len(w) > 2:
                    index.setdefault(w, [])
                    if doc_id not in index[w]:
                        index[w].append(doc_id)
            if tags:
                for t in tags:
                    key = f"tag:{t}"
                    index.setdefault(key, [])
                    if doc_id not in index[key]:
                        index[key].append(doc_id)

        # Index file docs
        files = self.documents.get("files", {})
        for doc_id, d in files.items():
            index_document(doc_id, (d.get("content", "") + " " + d.get("title", "")), d.get("tags", []))
        # Index faqs (legacy)
        faqs = self.documents.get("faqs", [])
        for i, d in enumerate(faqs):
            index_document(f"faqs.{i}", (d.get("question", "") + " " + d.get("answer", "")))
        self.logger.info(f"Search index built with {len(index)} terms")
        return index

    def search(self, query: str, limit: int = 5, domain: Optional[str] = None, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        doc_scores: Dict[str, int] = {}
        for term in query.lower().split():
            term = term.strip('.,!?;:')
            if term in self.search_index:
                for doc_id in self.search_index[term]:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
        # Optional domain filter
        if domain:
            dom = domain.upper()
            doc_scores = {k: v for k, v in doc_scores.items() if self._doc_domain(k).upper() == dom}
        # Optional tenant filter for tenant-aware doc_ids
        if tenant_id:
            prefix = f"kb.{tenant_id}."
            doc_scores = {k: v for k, v in doc_scores.items() if k.startswith(prefix)}
        results = []
        for doc_id, score in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:limit]:
            doc = self._get(doc_id)
            if doc:
                results.append({
                    "doc_id": doc_id,
                    "relevance_score": score,
                    "title": doc.get("title", doc.get("question", "Unknown")),
                    "content": doc.get("content", doc.get("answer", "")),
                    "category": self._doc_domain(doc_id),
                    "tags": doc.get("tags", [])
                })
        return results

    def _get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if doc_id.startswith("kb."):
            return self.documents.get("files", {}).get(doc_id)
        cat, *rest = doc_id.split(".")
        key = ".".join(rest)
        if cat in self.documents:
            if isinstance(self.documents[cat], dict):
                return self.documents[cat].get(key)
            if isinstance(self.documents[cat], list):
                try:
                    return self.documents[cat][int(key)]
                except Exception:
                    return None
        return None

    def _doc_domain(self, doc_id: str) -> str:
        if doc_id.startswith("kb."):
            try:
                return doc_id.split(".")[1].upper()
            except Exception:
                return "UNKNOWN"
        return doc_id.split(".")[0].upper()

    def synthesize_information(self, search_results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        if not search_results:
            return {"summary": "No relevant information found", "confidence": 0, "sources": []}
        synth = {
            "query": query,
            "summary": f"Found {len(search_results)} relevant documents",
            "key_findings": [{"title": r["title"], "relevance": r["relevance_score"]} for r in search_results[:3]],
            "sources": [r["doc_id"] for r in search_results[:3]],
            "confidence": min(1.0, len(search_results) / 3)
        }
        return synth

    def _process_specific(self, message: str, context: Dict[str, Any] = None) -> Any:
        domain = None
        tenant_id = None
        if context and isinstance(context, dict):
            domain = context.get("domain")
            tenant_id = context.get("tenant_id")
        results = self.search(message, limit=5, domain=domain, tenant_id=tenant_id)
        synthesis = self.synthesize_information(results, message)
        return {"action": "research", "findings": synthesis, "results": results}

    # --- runtime KB reload ---
    def reload_index(self, knowledge_base_path: Optional[str] = None) -> Dict[str, Any]:
        """Re-scan the KB folders and rebuild the in-memory index."""
        if knowledge_base_path:
            self.knowledge_base_path = knowledge_base_path
        self.documents = self._load_knowledge_base()
        self.search_index = self._build_search_index()
        return {
            "documents": len(self.documents.get("files", {})),
            "terms": len(self.search_index),
            "kb_path": os.path.abspath(self.knowledge_base_path),
            "timestamp": datetime.now().isoformat(),
        }

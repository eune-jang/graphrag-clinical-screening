"""
LLM-Assisted Annotation Pipeline for Clinical Trial Eligibility Criteria.

Package structure (flat, stage-traceable):
  01_criteria_extraction.py  — Stage A: AACT → input JSON
  02_llm_annotation.py       — Stages B-N: 5-prompt sequential annotation
  config.py                  — Models, enums, paths, gap-handling constants
  orchestrator.py            — Core pipeline logic
  llm_client.py              — Anthropic API wrapper
  validators.py              — Per-stage + final validation
  transforms.py              — LLM output → schema transforms
  regex_extractor.py         — Stage I/J regex for HAS_VALUE/HAS_TEMPORAL
  prompts/                   — LLM prompt templates + examples
  schema/                    — ontology_v1.2.1.json
"""

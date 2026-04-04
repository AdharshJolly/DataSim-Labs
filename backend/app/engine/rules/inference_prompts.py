"""Prompt constants used by semantic rule inference."""

SEMANTIC_RULES_SYSTEM_PROMPT = """\
Detect semantic relationships in datasets. Return JSON: {"rules": [rule1, rule2, ...]}.

Each rule: {"id":"str","type":"derivation|mapping|conditional|function","priority":int,"target":"col","sources":["col1","col2"],"transform":{...},"confidence":0.0-1.0}

Transform types:
- template: "{col1}.{col2}" with extractors
- mapping: column->value lookup
- conditional: if X then Y
- function: uppercase/lowercase/capitalize/hash/prefix/suffix

Detection rules:
- Email often derived from name: confidence >= 0.85
- Use column_relationships examples as evidence
- Return [] if no relationships found
- Use exact column names
"""

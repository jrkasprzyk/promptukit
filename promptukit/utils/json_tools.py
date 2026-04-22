"""Utilities for JSON question bank management.

Functions here help infer question types from messy legacy JSON,
tag existing entries with a ``question_type`` field, and load
question objects using the OO models in
``promptukit.questions.question_models``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from promptukit.utils.cli_helpers import load, save
from promptukit.questions.question_models import Question


def infer_question_type(item: Dict[str, Any]) -> str:
	"""Infer the question type for a single question dict.

	Rules:
	- If ``question_type`` already present, return it.
	- If ``choices`` or ``answer`` present, return ``MultipleChoice``.
	- Otherwise default to ``MultipleChoice`` (per project requirement).
	"""
	if not isinstance(item, dict):
		return "Question"
	qt = item.get("question_type")
	if isinstance(qt, str) and qt:
		return qt
	if "choices" in item or "answer" in item:
		return "MultipleChoice"
	return "MultipleChoice"


def _update_list(lst: List[Any]) -> List[Any]:
	out: List[Any] = []
	for it in lst:
		if isinstance(it, dict):
			if "question_type" not in it:
				it["question_type"] = infer_question_type(it)
		out.append(it)
	return out


def add_question_type_tags(data: Any) -> Any:
	"""Return a copy of ``data`` with ``question_type`` tags added where missing.

	Handles common shapes used in the project:
	- { 'questions': [...] }
	- { 'category': [ ... ], ... }
	- [ { ... }, { ... } ]
	- single question dict
	"""
	# dict with top-level 'questions' list
	if isinstance(data, dict):
		if "questions" in data and isinstance(data["questions"], list):
			out = dict(data)
			out["questions"] = _update_list(out["questions"])
			return out

		# mapping of category -> list
		if all(isinstance(v, list) for v in data.values()):
			out = {}
			for k, v in data.items():
				if isinstance(v, list):
					out[k] = _update_list(v)
				else:
					out[k] = v
			return out

		# single question-like dict
		out = dict(data)
		if "question_type" not in out:
			out["question_type"] = infer_question_type(out)
		return out

	# list of question dicts
	if isinstance(data, list):
		return _update_list(data)

	# otherwise return unchanged
	return data


def update_json_file(path: Path, dest: Path | None = None) -> Path:
	"""Read JSON from ``path``, add question_type tags, and write back.

	If ``dest`` is provided, write to that path; otherwise overwrite
	the original file. Returns the path written.
	"""
	data = load(path)
	updated = add_question_type_tags(data)
	out_path = dest or path
	save(out_path, updated)
	return out_path


def load_questions_as_objects(path: Path) -> List[Question]:
	"""Load questions from a JSON bank and return a flat list of Question objects.

	The function accepts the common JSON shapes used in the repo and
	instantiates the appropriate subclass via ``Question.from_json``.
	"""
	data = load(path)

	def _flatten(d: Any) -> List[Dict[str, Any]]:
		if isinstance(d, dict):
			if "questions" in d and isinstance(d["questions"], list):
				return [q for q in d["questions"] if isinstance(q, dict)]
			if all(isinstance(v, list) for v in d.values()):
				out: List[Dict[str, Any]] = []
				for v in d.values():
					if isinstance(v, list):
						out.extend([q for q in v if isinstance(q, dict)])
				return out
			return [d]
		if isinstance(d, list):
			return [q for q in d if isinstance(q, dict)]
		return []

	items = _flatten(data)
	return [Question.from_json(q) for q in items]


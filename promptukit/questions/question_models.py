"""Object-oriented question models for promptukit.

This module provides a lightweight `Question` base class and a
`MultipleChoice` subclass, plus flexible (de)serialization that
preserves legacy JSON shapes used in the repository (e.g. using
`prompt` and numeric `answer` indices).

Design goals:
- Keep backward compatibility with existing JSON banks.
- Provide `to_json` / `from_json` helpers and a `to_dict(preserve_raw=True)`
  mode which returns the original question dict with any new fields added
  (for example `question_type`).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _first_text_field(data: Dict[str, Any]) -> str:
    """Extract question text from several common field names."""
    for key in ("text", "prompt", "question", "q"):
        val = data.get(key)
        if isinstance(val, str):
            return val
    return ""


class Question:
    """Base class for questions.

    Instances may hold the original raw dict (``_raw``) so we can
    preserve exact legacy JSON when writing files back.
    """

    def __init__(self, text: str = "", metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None):
        self.text = text
        self.metadata = metadata or {}
        self.question_type = self.__class__.__name__
        # Keep the original dict to allow write-back preserving unknown keys
        self._raw: Optional[Dict[str, Any]] = dict(raw) if isinstance(raw, dict) else None

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        """Return a JSON-serializable dict.

        If ``preserve_raw`` is True and the instance was created from
        a raw dict, return a shallow copy of that raw dict with the
        ``question_type`` tag added if missing. Otherwise return a
        canonical representation using the key ``prompt`` for text.
        """
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            if "question_type" not in out:
                out["question_type"] = self.question_type
            return out

        out: Dict[str, Any] = {"question_type": self.question_type, "prompt": self.text}
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    def to_json(self, preserve_raw: bool = False) -> Dict[str, Any]:
        return self.to_dict(preserve_raw=preserve_raw)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Question":
        """Create a Question object from a JSON-like dict.

        Dispatches to known subclasses based on ``question_type`` or
        by inferring from available keys (e.g. presence of ``choices``).
        """
        qtype = data.get("question_type")
        # Dispatch to MultipleChoice when appropriate
        if qtype == "MultipleChoice" or ("choices" in data or "answer" in data):
            return MultipleChoice.from_json(data)
        # Fallback: generic Question
        return cls(text=_first_text_field(data), metadata=data.get("metadata", {}), raw=data)


class MultipleChoice(Question):
    """Multiple-choice question.

    Accepts legacy forms where the question text may be under ``prompt``
    and ``answer`` can be an integer index, a single-letter (A/B/C),
    or the choice text itself. The original raw dict is preserved so
    updates can write back without losing fields.
    """

    def __init__(self, text: str, choices: List[str], answer: Optional[Any] = None,
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None):
        super().__init__(text=text, metadata=metadata, raw=raw)
        self.choices = list(choices or [])
        self._raw_answer = answer

        # Normalise answer into two convenience attributes when possible
        self.answer_index: Optional[int] = None
        self.answer_text: Optional[str] = None

        if isinstance(answer, int):
            self.answer_index = answer
            if 0 <= answer < len(self.choices):
                self.answer_text = self.choices[answer]
        elif isinstance(answer, str):
            # Single-letter like 'A' -> index
            if len(answer) == 1 and answer.isalpha():
                idx = ord(answer.upper()) - ord("A")
                if 0 <= idx < len(self.choices):
                    self.answer_index = idx
                    self.answer_text = self.choices[idx]
                else:
                    self.answer_text = answer
            else:
                # Try to match the string to a choice value
                try:
                    idx = self.choices.index(answer)
                    self.answer_index = idx
                    self.answer_text = answer
                except ValueError:
                    self.answer_text = answer

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            if "question_type" not in out:
                out["question_type"] = "MultipleChoice"
            return out

        out: Dict[str, Any] = {"question_type": "MultipleChoice", "prompt": self.text, "choices": list(self.choices)}
        # Prefer numeric index when available to remain compact and
        # compatible with existing files which use integer indices.
        if self.answer_index is not None:
            out["answer"] = self.answer_index
        elif self.answer_text is not None:
            out["answer"] = self.answer_text
        else:
            out["answer"] = None
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "MultipleChoice":
        text = _first_text_field(data)
        choices = data.get("choices") or data.get("options") or []
        answer = data.get("answer")
        # Preserve metadata and raw dict so callers can write back unchanged
        return cls(text=text, choices=choices, answer=answer, metadata=data.get("metadata", {}), raw=data)

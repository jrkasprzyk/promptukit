"""Object-oriented question models for promptukit.

This module provides a lightweight `Question` base class and subclasses:
`MultipleChoice`, `TrueFalse`, `ShortAnswer`, `FillInTheBlank`,
`Matching`, `Calculation`, and `Code`.

Design goals:
- Keep backward compatibility with existing JSON banks.
- Provide `to_json` / `from_json` helpers and a `to_dict(preserve_raw=True)`
  mode which returns the original question dict with any new fields added
  (for example `question_type`).

Stimulus fields (all question types):
  ``has_stimulus`` – boolean; True when an external image/table accompanies
  the question.  ``stimulus_location`` – filepath or URL string pointing at
  the stimulus asset.

Answer-space field (ShortAnswer, Calculation):
  ``answer_space`` – controls how much blank space the PDF builder renders
  for student answers.  Accepted values are ``"small"`` (1 in), ``"medium"``
  (2 in, default), or ``"large"`` (4 in), or a positive number of inches.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union


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

    All question types support optional stimulus fields:
    - ``has_stimulus`` (bool) – True when an external image/table accompanies
      the question.
    - ``stimulus_location`` (str) – filepath or URL pointing at the stimulus
      asset (only meaningful when ``has_stimulus`` is True).
    """

    QUESTION_TYPE = "Question"

    def __init__(self, text: str = "", metadata: Optional[Dict[str, Any]] = None,
                 raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = ""):
        self.text = text
        self.metadata = metadata or {}
        self.question_type = self.QUESTION_TYPE
        self.has_stimulus: bool = has_stimulus
        self.stimulus_location: str = stimulus_location
        # Keep the original dict to allow write-back preserving unknown keys
        self._raw: Optional[Dict[str, Any]] = dict(raw) if isinstance(raw, dict) else None

    def _stimulus_fields(self) -> Dict[str, Any]:
        """Return stimulus fields to include in to_dict output (non-default only)."""
        if not self.has_stimulus:
            return {}
        out: Dict[str, Any] = {"has_stimulus": True}
        if self.stimulus_location:
            out["stimulus_location"] = self.stimulus_location
        return out

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
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    def to_json(self, preserve_raw: bool = False) -> Dict[str, Any]:
        return self.to_dict(preserve_raw=preserve_raw)

    @classmethod
    def _stimulus_from_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract stimulus kwargs from a raw question dict."""
        return {
            "has_stimulus": bool(data.get("has_stimulus", False)),
            "stimulus_location": data.get("stimulus_location", "") or "",
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Question":
        """Create a Question object from a JSON-like dict.

        Dispatches to known subclasses based on ``question_type`` or
        by inferring from available keys.
        """
        qtype = data.get("question_type", "")

        if qtype in _DISPATCH:
            return _DISPATCH[qtype].from_json(data)

        # Infer from available keys when no question_type tag
        if "choices" in data or "options" in data:
            return MultipleChoice.from_json(data)
        if "pairs" in data:
            return Matching.from_json(data)
        if "answers" in data and isinstance(data.get("answers"), list):
            return FillInTheBlank.from_json(data)
        if "code" in data:
            return Code.from_json(data)
        if "answer" in data:
            answer = data["answer"]
            if isinstance(answer, bool):
                return TrueFalse.from_json(data)
            if isinstance(answer, (int, float)):
                return Calculation.from_json(data)
            if isinstance(answer, str):
                return ShortAnswer.from_json(data)
            return MultipleChoice.from_json(data)

        # Fallback: generic Question
        stim = cls._stimulus_from_data(data)
        return cls(text=_first_text_field(data), metadata=data.get("metadata", {}), raw=data, **stim)


class MultipleChoice(Question):
    """Multiple-choice question.

    Accepts legacy forms where the question text may be under ``prompt``
    and ``answer`` can be an integer index, a single-letter (A/B/C),
    or the choice text itself. The original raw dict is preserved so
    updates can write back without losing fields.
    """

    QUESTION_TYPE = "MultipleChoice"

    def __init__(self, text: str, choices: List[str], answer: Optional[Any] = None,
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = ""):
        super().__init__(text=text, metadata=metadata, raw=raw,
                         has_stimulus=has_stimulus, stimulus_location=stimulus_location)
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
            # Single ASCII letter like 'A' -> index
            if len(answer) == 1 and answer.isascii() and answer.isalpha():
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
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "MultipleChoice":
        text = _first_text_field(data)
        choices = data.get("choices") or data.get("options") or []
        answer = data.get("answer")
        stim = cls._stimulus_from_data(data)
        # Preserve metadata and raw dict so callers can write back unchanged
        return cls(text=text, choices=choices, answer=answer, metadata=data.get("metadata", {}), raw=data, **stim)


class TrueFalse(Question):
    """True/False question. Answer stored as Python bool."""

    QUESTION_TYPE = "TrueFalse"

    def __init__(self, text: str, answer: Optional[bool] = None,
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = ""):
        super().__init__(text=text, metadata=metadata, raw=raw,
                         has_stimulus=has_stimulus, stimulus_location=stimulus_location)
        self.answer: Optional[bool] = answer

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            out.setdefault("question_type", "TrueFalse")
            return out
        out: Dict[str, Any] = {"question_type": "TrueFalse", "prompt": self.text, "answer": self.answer}
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "TrueFalse":
        text = _first_text_field(data)
        raw_answer = data.get("answer")
        if isinstance(raw_answer, bool):
            answer = raw_answer
        elif isinstance(raw_answer, str):
            answer = raw_answer.strip().lower() in ("true", "yes", "1", "t")
        else:
            answer = None
        stim = cls._stimulus_from_data(data)
        return cls(text=text, answer=answer, metadata=data.get("metadata", {}), raw=data, **stim)


class ShortAnswer(Question):
    """Free-text short-answer question. Answer is a string.

    ``answer_space`` controls the blank space rendered in exam PDFs.
    Accepted values: ``"small"`` (1 in), ``"medium"`` (2 in, default),
    ``"large"`` (4 in), or a positive number (interpreted as inches).
    """

    QUESTION_TYPE = "ShortAnswer"

    def __init__(self, text: str, answer: str = "",
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = "",
                 answer_space: Optional[Union[str, float]] = None):
        super().__init__(text=text, metadata=metadata, raw=raw,
                         has_stimulus=has_stimulus, stimulus_location=stimulus_location)
        self.answer = answer
        self.answer_space = answer_space  # "small" | "medium" | "large" | float (inches)

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            out.setdefault("question_type", "ShortAnswer")
            return out
        out: Dict[str, Any] = {"question_type": "ShortAnswer", "prompt": self.text, "answer": self.answer}
        if self.answer_space is not None:
            out["answer_space"] = self.answer_space
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ShortAnswer":
        stim = cls._stimulus_from_data(data)
        return cls(
            text=_first_text_field(data),
            answer=data.get("answer", ""),
            metadata=data.get("metadata", {}),
            raw=data,
            answer_space=data.get("answer_space"),
            **stim,
        )


class FillInTheBlank(Question):
    """Fill-in-the-blank question.

    ``text`` contains blanks marked with ``[blank]`` tokens.
    ``answers`` is an ordered list of strings, one per blank.
    """

    BLANK_TOKEN = "[blank]"
    QUESTION_TYPE = "FillInTheBlank"

    def __init__(self, text: str, answers: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = ""):
        super().__init__(text=text, metadata=metadata, raw=raw,
                         has_stimulus=has_stimulus, stimulus_location=stimulus_location)
        self.answers: List[str] = list(answers or [])

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            out.setdefault("question_type", "FillInTheBlank")
            return out
        out: Dict[str, Any] = {"question_type": "FillInTheBlank", "prompt": self.text, "answers": list(self.answers)}
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "FillInTheBlank":
        answers = data.get("answers") or []
        if isinstance(answers, str):
            answers = [answers]
        stim = cls._stimulus_from_data(data)
        return cls(
            text=_first_text_field(data),
            answers=list(answers),
            metadata=data.get("metadata", {}),
            raw=data,
            **stim,
        )


class Matching(Question):
    """Matching question.

    ``pairs`` is a list of ``[left, right]`` two-element lists.
    Order of pairs is the canonical correct matching.
    """

    QUESTION_TYPE = "Matching"

    def __init__(self, text: str, pairs: Optional[List[List[str]]] = None,
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = ""):
        super().__init__(text=text, metadata=metadata, raw=raw,
                         has_stimulus=has_stimulus, stimulus_location=stimulus_location)
        self.pairs: List[List[str]] = [list(p) for p in (pairs or [])]

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            out.setdefault("question_type", "Matching")
            return out
        out: Dict[str, Any] = {
            "question_type": "Matching",
            "prompt": self.text,
            "pairs": [list(p) for p in self.pairs],
        }
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Matching":
        raw_pairs = data.get("pairs") or []
        pairs = [list(p) for p in raw_pairs if isinstance(p, (list, tuple)) and len(p) == 2]
        stim = cls._stimulus_from_data(data)
        return cls(
            text=_first_text_field(data),
            pairs=pairs,
            metadata=data.get("metadata", {}),
            raw=data,
            **stim,
        )


class Calculation(Question):
    """Numeric calculation question.

    ``answer`` is the expected numeric result.
    ``tolerance`` allows a margin of error (default 0).
    ``unit`` is an optional string label (e.g. "m/s", "kg").
    ``answer_space`` controls how much blank space the PDF builder
    renders for student answers (same values as ShortAnswer).
    """

    QUESTION_TYPE = "Calculation"

    def __init__(self, text: str, answer: Optional[Union[int, float]] = None,
                 tolerance: float = 0.0, unit: str = "",
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = "",
                 answer_space: Optional[Union[str, float]] = None):
        super().__init__(text=text, metadata=metadata, raw=raw,
                         has_stimulus=has_stimulus, stimulus_location=stimulus_location)
        self.answer = answer
        self.tolerance = tolerance
        self.unit = unit
        self.answer_space = answer_space

    def is_correct(self, value: Union[int, float]) -> bool:
        """Return True if ``value`` is within tolerance of the answer."""
        if self.answer is None:
            return False
        return abs(value - self.answer) <= self.tolerance

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            out.setdefault("question_type", "Calculation")
            return out
        out: Dict[str, Any] = {"question_type": "Calculation", "prompt": self.text, "answer": self.answer}
        if self.tolerance:
            out["tolerance"] = self.tolerance
        if self.unit:
            out["unit"] = self.unit
        if self.answer_space is not None:
            out["answer_space"] = self.answer_space
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Calculation":
        raw_answer = data.get("answer")
        try:
            answer = float(raw_answer) if raw_answer is not None else None
        except (ValueError, TypeError):
            answer = None
        stim = cls._stimulus_from_data(data)
        return cls(
            text=_first_text_field(data),
            answer=answer,
            tolerance=float(data.get("tolerance", 0.0)),
            unit=data.get("unit", ""),
            metadata=data.get("metadata", {}),
            raw=data,
            answer_space=data.get("answer_space"),
            **stim,
        )


class Code(Question):
    """Code question — displays a code snippet and asks a question about it.

    ``code`` holds the code snippet (a string, may be multi-line).
    ``language`` is an optional programming language label (e.g. "python",
    "javascript") used for display purposes.
    ``answer`` is an optional expected answer (string).
    """

    QUESTION_TYPE = "Code"

    def __init__(self, text: str, code: str = "", language: str = "",
                 answer: str = "",
                 metadata: Optional[Dict[str, Any]] = None, raw: Optional[Dict[str, Any]] = None,
                 has_stimulus: bool = False, stimulus_location: str = ""):
        super().__init__(text=text, metadata=metadata, raw=raw,
                         has_stimulus=has_stimulus, stimulus_location=stimulus_location)
        self.code = code
        self.language = language
        self.answer = answer

    def to_dict(self, preserve_raw: bool = False) -> Dict[str, Any]:
        if preserve_raw and self._raw is not None:
            out = dict(self._raw)
            out.setdefault("question_type", "Code")
            return out
        out: Dict[str, Any] = {
            "question_type": "Code",
            "prompt": self.text,
            "code": self.code,
        }
        if self.language:
            out["language"] = self.language
        if self.answer:
            out["answer"] = self.answer
        out.update(self._stimulus_fields())
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Code":
        stim = cls._stimulus_from_data(data)
        return cls(
            text=_first_text_field(data),
            code=data.get("code", ""),
            language=data.get("language", ""),
            answer=data.get("answer", ""),
            metadata=data.get("metadata", {}),
            raw=data,
            **stim,
        )


# Resolved at call time — defined after all classes so forward refs work.
_DISPATCH: Dict[str, Any] = {
    "MultipleChoice": MultipleChoice,
    "TrueFalse": TrueFalse,
    "ShortAnswer": ShortAnswer,
    "FillInTheBlank": FillInTheBlank,
    "Matching": Matching,
    "Calculation": Calculation,
    "Code": Code,
}

"""
Inquiry Module - Question Engine for Darwin

This module enables Darwin to generate deep questions, pursue answers autonomously,
and engage in Socratic dialogue with itself.
"""

from .question_engine import QuestionEngine
from .socratic_dialogue import SocraticDialogue
from .answer_pursuer import AnswerPursuer

__all__ = ['QuestionEngine', 'SocraticDialogue', 'AnswerPursuer']

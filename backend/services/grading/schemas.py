"""Strict output schemas for every Gemini call.

The same Pydantic models are (1) sent to Gemini as `response_schema` so decoding is
constrained to valid JSON, and (2) used to validate the reply. Integer rubric points
are bounded with ge/le so an out-of-range value is rejected, not clamped.
Free-text fields are trimmed to a maximum length instead of rejected, because a
long-but-honest explanation should not turn a valid grade into "unavailable".
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _trim(limit: int):
    return AfterValidator(lambda value: (value or "").strip()[:limit])


ShortText = Annotated[str, _trim(600)]
Text = Annotated[str, _trim(4000)]
LongText = Annotated[str, _trim(12000)]
CodeText = Annotated[str, _trim(20000)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Points4(_Strict):
    points: int = Field(ge=0, le=4)
    rationale: ShortText


class Points3(_Strict):
    points: int = Field(ge=0, le=3)
    rationale: ShortText


class Points2(_Strict):
    points: int = Field(ge=0, le=2)
    rationale: ShortText


class Points1(_Strict):
    points: int = Field(ge=0, le=1)
    rationale: ShortText


class Points5(_Strict):
    points: int = Field(ge=0, le=5)
    rationale: ShortText


# ------------------------------------------------------------- answer grading


class AnswerRubricScores(_Strict):
    technical_correctness: Points4
    completeness: Points3
    clarity_structure: Points2
    depth_examples: Points1


class AnswerEvaluationOutput(_Strict):
    rubric: AnswerRubricScores
    manipulation_attempt: bool
    feedback: Text
    missing_points: Text
    corrected_answer: LongText
    improvement: ShortText
    follow_up_question: ShortText


# ------------------------------------------------------------- DSA code review


class CodeRubricScores(_Strict):
    correctness: Points5
    efficiency: Points2
    edge_cases: Points2
    code_quality: Points1


class CodeReviewOutput(_Strict):
    rubric: CodeRubricScores
    manipulation_attempt: bool
    feedback: Text
    optimized_approach: Text
    optimized_code: CodeText
    explanation: LongText
    time_complexity: Annotated[str, _trim(80)]
    space_complexity: Annotated[str, _trim(80)]


# ------------------------------------------------------------- project review


class FileFinding(_Strict):
    file: Annotated[str, _trim(300)]
    status: Literal["GOOD", "ISSUE", "REVIEW"]
    issues: list[ShortText] = Field(max_length=20)
    suggestions: list[ShortText] = Field(max_length=20)


class BugFinding(_Strict):
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    file: Annotated[str, _trim(300)]
    issue: ShortText
    fix: ShortText


class SecurityFinding(_Strict):
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    file: Annotated[str, _trim(300)]
    issue: ShortText
    fix: ShortText


class ProjectRubricScores(_Strict):
    requirements_coverage: Points4
    code_correctness: Points3
    architecture: Points2
    security_quality: Points1


class ProjectReviewOutput(_Strict):
    rubric: ProjectRubricScores
    manipulation_attempt: bool
    feedback: Text
    architecture_review: Text
    file_findings: list[FileFinding] = Field(max_length=60)
    bugs: list[BugFinding] = Field(max_length=40)
    security_issues: list[SecurityFinding] = Field(max_length=40)
    missing_requirements: list[ShortText] = Field(max_length=30)
    missing_points: Text
    improved_approach: Text
    next_steps: Text
    suggested_resources: list[ShortText] = Field(max_length=15)


# ------------------------------------------------------------- generation


class DSAExample(_Strict):
    input: Annotated[str, _trim(1000)]
    output: Annotated[str, _trim(1000)]
    explanation: ShortText


class DSAProblemOutput(_Strict):
    title: Annotated[str, _trim(150)]
    description: LongText
    examples: list[DSAExample] = Field(min_length=1, max_length=4)
    constraints: list[Annotated[str, _trim(200)]] = Field(max_length=10)
    follow_up: ShortText
    starter_code: Annotated[str, _trim(1500)]


# Types an AI-generated problem may use. Kept small so every value can be
# checked exactly and passed to the harness as plain JSON.
ValueType = Literal[
    "int", "float", "str", "bool",
    "list[int]", "list[float]", "list[str]", "list[bool]",
    "list[list[int]]", "list[list[str]]",
]


class ParameterSpec(_Strict):
    name: Annotated[str, _trim(40)]
    type: ValueType


class GeneratedTestCase(_Strict):
    # JSON-encoded so Gemini's schema does not need arbitrary value types.
    input_json: Annotated[str, _trim(5000)]
    expected_output_json: Annotated[str, _trim(5000)]


class AIPracticeProblemOutput(DSAProblemOutput):
    """AI-practice problem plus an executable signature, tests and a reference solution.

    Everything here is AI-generated and validated server-side before use
    (services/dsa_generated_tests.py). None of it is treated as ground truth.
    """

    function_name: Annotated[str, _trim(60)]
    parameters: list[ParameterSpec] = Field(min_length=1, max_length=6)
    return_type: ValueType
    order_matters: bool
    test_cases: list[GeneratedTestCase] = Field(min_length=1, max_length=10)
    reference_solution: CodeText


class DatasetColumn(_Strict):
    column: Annotated[str, _trim(100)]
    description: ShortText


class ProjectChallengeOutput(_Strict):
    project_title: Annotated[str, _trim(200)]
    problem_statement: LongText
    dataset_columns: list[DatasetColumn] = Field(max_length=20)
    tasks: list[ShortText] = Field(min_length=1, max_length=15)
    evaluation_metrics: list[ShortText] = Field(max_length=15)
    hints: list[ShortText] = Field(max_length=10)
    submission_checklist: list[ShortText] = Field(max_length=15)


class InterviewQuestionOutput(_Strict):
    question: Text

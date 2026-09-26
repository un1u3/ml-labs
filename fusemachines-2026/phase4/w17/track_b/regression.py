import json

import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.descriptors import LLMEval, TestSummary
from evidently.llm.templates import BinaryClassificationPromptTemplate
from evidently.presets import TextEvals
from evidently.tests import eq

import agent
import config

GOLDEN = json.loads((config.ROOT / "regression_set.json").read_text())

CORRECTNESS = BinaryClassificationPromptTemplate(
    criteria="""An ANSWER is correct if it keeps all the facts in the REFERENCE and does not contradict it.
Wording may differ and extra detail is fine as long as it does not conflict with the REFERENCE.
The ANSWER is incorrect if it contradicts the REFERENCE or leaves out facts the REFERENCE contains.
REFERENCE:
{reference}""",
    target_category="incorrect", non_target_category="correct",
    uncertainty="unknown", include_reasoning=True,
    pre_messages=[("system", "You are a strict grader comparing an assistant's answer to an approved reference answer.")],
)

FABRICATION = BinaryClassificationPromptTemplate(
    criteria="""The QUESTION was: {question}
The approved REFERENCE answer is: {reference}
An ANSWER is fabricated if it states specific facts (dates, numbers, names, requirements) that are not in the
REFERENCE and would plausibly mislead the user, or if it answers confidently when the REFERENCE says the
documents do not contain the answer. Otherwise it is grounded.""",
    target_category="fabricated", non_target_category="grounded",
    uncertainty="unknown", include_reasoning=True,
    pre_messages=[("system", "You check assistant answers for invented or unsupported claims.")],
)


def collect_responses():
    rows, traces = [], []
    for case in GOLDEN:
        res = agent.run(case["question"])
        res.pop("messages", None)
        traces.append({**res, "case": case["id"]})
        rows.append({"id": case["id"], "question": case["question"], "reference": case["reference"],
                     "response": res.get("answer", "")})
    return pd.DataFrame(rows), traces


def judge(df):
    judge_args = {"provider": config.JUDGE_PROVIDER, "model": config.JUDGE_MODEL}
    ds = Dataset.from_pandas(df, data_definition=DataDefinition(text_columns=["question", "reference", "response"]),
                             descriptors=[
        LLMEval("response", template=CORRECTNESS, additional_columns={"reference": "reference"},
                alias="Correctness", tests=[eq("correct", column="Correctness", alias="Correct vs reference")], **judge_args),
        LLMEval("response", template=FABRICATION,
                additional_columns={"reference": "reference", "question": "question"},
                alias="Fabrication", tests=[eq("grounded", column="Fabrication", alias="No fabrication")], **judge_args),
        TestSummary(success_all=True, alias="All passed"),
    ])
    snapshot = Report([TextEvals()]).run(ds, None)
    return ds.as_dataframe(), snapshot


def run(html_path):
    df, traces = collect_responses()
    scored, snapshot = judge(df)
    snapshot.save_html(str(html_path))
    passed = scored["All passed"].astype(bool)
    return {"pct_tests_passed": float(passed.mean()),
            "correct_rate": float((scored["Correctness"] == "correct").mean()),
            "grounded_rate": float((scored["Fabrication"] == "grounded").mean()),
            "promotable": bool(passed.mean() >= config.PROMOTION_THRESHOLD)}, scored, traces

"""The LLM boundary: what is sent, what is read back, and what is refused.

No test here calls the service. Every one of them is about the code on this side of the boundary,
which is where a silent error would be worst: a fabricated level enters arm C's design matrix as a
real observation, and a reply read out of the wrong field disappears as a missing answer. The
service itself is exercised by `rule probe` (WORKFLOW.md section 9, step 3), on a compute node,
outside `rule all`.
"""
import base64
import json
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from priors import llm, score

CONCEPTS = [
    {"id": "opacity", "question": "?", "scale": ["absent", "mild", "marked"], "anchors": {}},
    {"id": "edge", "question": "?", "scale": ["sharp", "blurred"], "anchors": {}},
]
CLASSES = ["normal", "pneumonia"]


# ---- what the model is shown ----------------------------------------------------------------

@pytest.mark.parametrize("shape", [(224, 224), (224, 224, 3)])
def test_the_image_survives_the_encoding_exactly(shape):
    """Greyscale and colour both go over the wire as lossless PNG. If this ever became JPEG, the
    study would be asking what a model sees in a compressed medical image."""
    rng = np.random.default_rng(0)
    image = rng.integers(0, 256, size=shape, dtype=np.uint8)
    url = score.png_data_url(image)
    assert url.startswith("data:image/png;base64,")
    decoded = np.array(Image.open(BytesIO(base64.b64decode(url.split(",", 1)[1]))))
    assert np.array_equal(decoded, image)


def test_an_image_of_the_wrong_shape_is_refused():
    with pytest.raises(ValueError):
        score.png_data_url(np.zeros((4, 224, 224), dtype=np.uint8))


# ---- what can be read back -------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    '{"opacity": "mild", "edge": "sharp"}',
    '```json\n{"opacity": "mild", "edge": "sharp"}\n```',
    'Here is the answer:\n{"opacity": "mild", "edge": "sharp"}\nHope that helps.',
])
def test_a_good_answer_is_read_through_the_usual_wrappers(text):
    parsed = score.parse_concept_answer(text, CONCEPTS)
    assert parsed["answers"] == {"opacity": "mild", "edge": "sharp"}
    assert parsed["parsed"] and not parsed["invalid"]
    assert score.is_complete(parsed)


@pytest.mark.parametrize("text, reason", [
    ('{"opacity": "severe", "edge": "sharp"}', "a level that is not on the scale"),
    ('{"opacity": 2, "edge": "sharp"}', "an index instead of a level"),
    ('{"opacity": null, "edge": "sharp"}', "an explicit null"),
    ('{"edge": "sharp"}', "a missing question"),
])
def test_an_answer_that_is_not_a_level_becomes_missing_not_a_guess(text, reason):
    """The nearest level, the level at that index, the modal level: every repair here would put a
    number into arm C that the model never gave. None of them happens."""
    parsed = score.parse_concept_answer(text, CONCEPTS)
    assert parsed["answers"]["opacity"] is None, reason
    assert parsed["answers"]["edge"] == "sharp"
    assert "opacity" in parsed["invalid"]
    assert not score.is_complete(parsed)


@pytest.mark.parametrize("text", ["", "I cannot answer.", '{"opacity": "mild", "edge":', "[1, 2]"])
def test_an_unreadable_reply_leaves_every_answer_missing(text):
    parsed = score.parse_concept_answer(text, CONCEPTS)
    assert parsed["answers"] == {"opacity": None, "edge": None}
    assert not parsed["parsed"] or not score.is_complete(parsed)


def test_keys_the_bank_never_asked_about_are_recorded_and_dropped():
    parsed = score.parse_concept_answer('{"opacity": "mild", "edge": "sharp", "grade": "high"}',
                                        CONCEPTS)
    assert parsed["unknown_keys"] == ["grade"]
    assert set(parsed["answers"]) == {"opacity", "edge"}


def test_a_zero_shot_reply_keeps_the_numbers_the_model_gave():
    parsed = score.parse_zero_shot_answer('{"normal": 0.25, "pneumonia": 0.75}', CLASSES)
    assert parsed["scores"] == {"normal": 0.25, "pneumonia": 0.75}
    assert parsed["sums_to_one"] is True
    # Not rescaled: dividing each image's vector by its own sum would reorder images within a class
    # column, which is exactly what the AUC reads.
    loose = score.parse_zero_shot_answer('{"normal": 0.2, "pneumonia": 0.2}', CLASSES)
    assert loose["scores"] == {"normal": 0.2, "pneumonia": 0.2}
    assert loose["sums_to_one"] is False


@pytest.mark.parametrize("text", ['{"normal": "high", "pneumonia": 0.75}',
                                  '{"normal": true, "pneumonia": 0.75}',
                                  '{"normal": NaN, "pneumonia": 0.75}',
                                  '{"pneumonia": 0.75}'])
def test_a_zero_shot_value_that_is_not_a_number_becomes_missing(text):
    parsed = score.parse_zero_shot_answer(text, CLASSES)
    assert parsed["scores"]["normal"] is None
    assert parsed["scores"]["pneumonia"] == 0.75
    assert not score.is_complete(parsed, "scores")


# ---- the retry that repairs a truncated reply, and the one that does not ----------------------

class FakeClient:
    """A client that hands back scripted replies and records the budgets it was asked for."""

    def __init__(self, texts):
        self.texts, self.budgets = list(texts), []

    def ask(self, system, user, image_url=None, max_tokens=512):
        self.budgets.append(max_tokens)
        text = self.texts[min(len(self.budgets) - 1, len(self.texts) - 1)]
        return llm.Reply(text=text, served_model="served-name", finish_reason="length",
                         field="content", message={"content": text}, usage={"total_tokens": 7})


def test_every_attempt_records_what_it_cost():
    """The scoring rule's runtime request is 100 of these per chunk, so the latency is recorded
    per call rather than divided out of a job's wall time afterwards."""
    client = FakeClient(['{"opacity": "mild", "edge": "sharp"}'])
    result = score.ask_one(client, {"system": "s", "user": "u"}, "url", "concept", CONCEPTS, 512)
    assert result["replies"][0]["elapsed_s"] >= 0.0
    assert result["replies"][0]["usage"] == {"total_tokens": 7}


def test_a_complete_answer_is_not_retried():
    client = FakeClient(['{"opacity": "mild", "edge": "sharp"}'])
    result = score.ask_one(client, {"system": "s", "user": "u"}, "url", "concept", CONCEPTS, 512)
    assert result["complete"] and result["content_attempts"] == 1
    assert client.budgets == [512]


def test_a_truncated_answer_is_retried_once_with_a_doubled_budget():
    client = FakeClient(['{"opacity": "mild", "edge":', '{"opacity": "mild", "edge": "sharp"}'])
    result = score.ask_one(client, {"system": "s", "user": "u"}, "url", "concept", CONCEPTS, 512)
    assert client.budgets == [512, 1024], "the repair is a bigger budget, not a different prompt"
    assert result["complete"] and result["content_attempts"] == 2
    assert result["answers"] == {"opacity": "mild", "edge": "sharp"}
    assert len(result["replies"]) == 2, "the failed attempt is archived too"
    assert result["replies"][0]["text"].endswith('"edge":')


def test_a_reply_that_stays_malformed_is_recorded_missing_with_its_raw_text():
    client = FakeClient(["not json at all"])
    result = score.ask_one(client, {"system": "s", "user": "u"}, "url", "concept", CONCEPTS, 64)
    assert result["content_attempts"] == 2 and not result["complete"]
    assert result["answers"] == {"opacity": None, "edge": None}
    assert [r["text"] for r in result["replies"]] == ["not json at all"] * 2
    assert [r["served_model"] for r in result["replies"]] == ["served-name"] * 2


def test_a_distribution_prompt_records_whether_the_model_obeyed_the_sum():
    """`sums_to_one` is a property of a distribution answer, not of an arm.

    Arm A is asked with `kind="zero_shot"`; the diagnostic is gated on the answer's shape rather
    than on the prompt name, so any future distribution prompt carries it without a code change."""
    text = '{"normal": 0.25, "pneumonia": 0.75}'
    for kind in ("zero_shot",):
        result = score.ask_one(FakeClient([text]), {"system": "s", "user": "u"}, "url", kind,
                               CLASSES, 512)
        assert result["complete"] and result["sums_to_one"] is True, kind
        assert result["scores"] == {"normal": 0.25, "pneumonia": 0.75}
    concept = score.ask_one(FakeClient(['{"opacity": "mild", "edge": "sharp"}']),
                            {"system": "s", "user": "u"}, "url", "concept", CONCEPTS, 512)
    assert "sums_to_one" not in concept, "a concept answer is not a distribution"


def test_retries_can_be_switched_off():
    client = FakeClient(["nonsense"])
    result = score.ask_one(client, {"system": "s", "user": "u"}, "url", "concept", CONCEPTS, 64,
                           content_retries=0)
    assert result["content_attempts"] == 1 and not result["complete"]


# ---- the two things the served stack does that a plain client would get wrong -----------------

class Message:
    """A served message. Different builds fill different fields; some fill none."""

    def __init__(self, content=None, reasoning_content=None, reasoning=None):
        self.content, self.reasoning_content, self.reasoning = content, reasoning_content, reasoning

    def model_dump(self):
        return {"role": "assistant", "content": self.content,
                "reasoning_content": self.reasoning_content, "reasoning": self.reasoning}


class Choice:
    def __init__(self, message, finish_reason="stop"):
        self.message, self.finish_reason = message, finish_reason


class Completion:
    def __init__(self, message, model="served-name"):
        self.choices, self.model, self.usage = [Choice(message)], model, {"total_tokens": 3}


@pytest.mark.parametrize("kwargs, field", [
    (dict(content='{"a": 1}'), "content"),
    (dict(content="", reasoning_content='{"a": 1}'), "reasoning_content"),
    (dict(content=None, reasoning='{"a": 1}'), "reasoning"),
])
def test_the_answer_is_found_whichever_field_the_build_uses(kwargs, field):
    """This cost 3,000 calls. qwen3.5-9b returns its finished JSON in `reasoning` - not `content`,
    not `reasoning_content` - and with thinking off that field holds the answer rather than any
    chain of thought. A reader that knew two fields recorded a whole model as unanswerable."""
    reply = llm.read_reply(Completion(Message(**kwargs)))
    assert reply.text == '{"a": 1}'
    assert reply.field == field, "and which field answered is recorded"


def test_a_message_with_nothing_in_it_is_empty_not_an_error():
    empty = llm.read_reply(Completion(Message(content="", reasoning_content="")))
    assert empty.text == "" and empty.field is None


def test_the_whole_message_is_kept_so_a_reader_bug_is_repairable():
    """The archive holds the message, not the text pulled out of it. When the extraction was wrong,
    the only way back was to buy the calls again; with the message kept, it is a re-parse."""
    reply = llm.read_reply(Completion(Message(content=None, reasoning='{"a": 1}')))
    assert reply.message["reasoning"] == '{"a": 1}'
    assert set(reply.message) >= {"content", "reasoning_content", "reasoning"}


def test_the_served_model_name_is_recorded_rather_than_the_requested_one():
    reply = llm.read_reply(Completion(Message(content="x"), model="qwen3.8-27b-fp8-20260101"))
    assert reply.served_model == "qwen3.8-27b-fp8-20260101"


def test_thinking_is_switched_off_in_the_body_the_service_reads(monkeypatch, tmp_path):
    """`enable_thinking` is not an OpenAI parameter, so it has to travel in `extra_body`; with
    reasoning left on, the primary model spends its whole budget in reasoning_content."""
    key = tmp_path / "key"
    key.write_text("not-a-real-key\n")
    monkeypatch.setattr(llm.openai, "OpenAI", lambda **kw: object())
    off = llm.Client(model="m", base_url="http://x/v1", key_file=str(key), reasoning="none")
    on = llm.Client(model="m", base_url="http://x/v1", key_file=str(key), reasoning="medium")
    assert off.extra_body == {"chat_template_kwargs": {"enable_thinking": False}}
    assert on.extra_body == {"chat_template_kwargs": {"enable_thinking": True}}


# ---- transport backoff -------------------------------------------------------------------------

class Busy(Exception):
    pass


def test_a_busy_service_is_retried_with_growing_delays():
    calls, slept = [], []
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise Busy()
        return "answer"
    value, attempts = llm.call_with_backoff(flaky, attempts=4, retryable=(Busy,),
                                            sleep=slept.append)
    assert value == "answer" and attempts == 3
    assert slept == [1.0, 2.0], "exponential, so a throttled service is not hammered"


def test_the_last_transport_failure_is_raised_rather_than_swallowed():
    """A chunk that could not be placed must fail its job. Recording those images as missing would
    put a service outage into the archive as if the model had declined to answer."""
    def always_busy():
        raise Busy()
    with pytest.raises(Busy):
        llm.call_with_backoff(always_busy, attempts=3, retryable=(Busy,), sleep=lambda s: None)


def test_an_error_that_is_not_transport_is_not_retried():
    calls = []
    def bad_request():
        calls.append(1)
        raise ValueError("model not found")
    with pytest.raises(ValueError):
        llm.call_with_backoff(bad_request, attempts=4, retryable=(Busy,), sleep=lambda s: None)
    assert len(calls) == 1


def test_the_key_is_read_from_the_file_and_a_blank_one_is_refused(tmp_path):
    key = tmp_path / "key"
    key.write_text("  secret-value\n")
    assert llm.load_key(key) == "secret-value"
    key.write_text("\n")
    with pytest.raises(ValueError):
        llm.load_key(key)


# ---- the fan-out: how the work is cut up, and what holds the caps together ---------------------

@pytest.mark.parametrize("n, size", [(500, 100), (2000, 100), (10, 3), (1, 1), (7, 100)])
def test_chunks_cover_the_split_exactly_once(n, size):
    """One chunk is one job and one archive file, so a gap would leave images unscored and an
    overlap would score them twice at full price."""
    spans = score.chunks(n, size)
    assert spans[0][0] == 0 and spans[-1][1] == n
    assert all(b == c for (_, b), (c, _) in zip(spans, spans[1:]))
    assert sum(b - a for a, b in spans) == n
    assert all(0 < b - a <= size for a, b in spans)


def test_a_chunk_size_of_zero_is_refused():
    with pytest.raises(ValueError):
        score.chunks(100, 0)


def test_the_profile_caps_match_the_models_config(config):
    """`vlm.models.*.cap` says what we decided; the profile's `llm_*` resources are what Snakemake
    enforces. They are two files, so they can drift, and a drift upwards means asking the service
    for more concurrency than it published."""
    import re

    import yaml

    from .conftest import ROOT

    profile = yaml.safe_load((ROOT / "profiles/palmetto/config.yaml").read_text())
    declared = profile.get("resources", {})
    for model, spec in config["vlm"]["models"].items():
        key = "llm_" + re.sub(r"[^a-z0-9]+", "_", model.lower())
        assert key in declared, f"{model}: no {key} in the palmetto profile"
        assert declared[key] == spec["cap"], f"{model}: profile {declared[key]} != config {spec['cap']}"
        assert spec["cap"] <= spec["concurrency"], f"{model}: cap above the published concurrency"
    assert sorted(k for k in declared if k.startswith("llm_")) == sorted(
        "llm_" + re.sub(r"[^a-z0-9]+", "_", m.lower()) for m in config["vlm"]["models"]), \
        "the profile caps a model the config does not have"


def test_only_the_primary_model_scores_the_labelled_pool(config):
    """Arm B needs no labels, so the ladder models need the 500 test images and nothing else. That
    one observation is what keeps the budget at 27,000 calls instead of 120,000."""
    models = config["vlm"]["models"]
    primary = config["vlm"]["primary"]
    assert primary in models
    assert models[primary]["splits"] == ["test", "pool"]
    for name, spec in models.items():
        if name != primary:
            assert spec["splits"] == ["test"], name


def test_the_call_budget_is_what_the_plan_says(config):
    """27,000 calls in 270 chunks (WORKFLOW.md section 4). If a grid moves, this is where the new
    number shows up, rather than in a service bill."""
    sample, models = config["sample"], config["vlm"]["models"]
    chunk, primary, datasets = config["vlm"]["chunk"], config["vlm"]["primary"], config["datasets"]
    calls = jobs = 0
    for name, spec in models.items():
        for split in spec["splits"]:
            n = sample["test_n" if split == "test" else "pool_n"]
            prompts = 2 if (name == primary and split == "test") else 1
            calls += n * len(datasets) * prompts
            jobs += len(score.chunks(n, chunk)) * len(datasets) * prompts
    assert calls == 27_000
    assert jobs == 270


def test_a_job_refuses_to_write_a_file_named_for_another_cell(tmp_path):
    """The guard that would have caught the fan-out's first bug: four rules generated in a loop
    kept their own output paths but shared the last one's command, so the primary model's archive
    was written by gemma-4-31b. The archive was internally consistent; only the served model name
    disagreed with the file name, which no downstream stage reads."""
    from priors import stages

    good = tmp_path / "pneumoniamnist__qwen3.8-27b-fp8__test__concept__chunk00.json"
    stages.check_output_name(good, "pneumoniamnist", "qwen3.8-27b-fp8", "test", "concept", 0)

    for wrong in [dict(model="gemma-4-31b"), dict(dataset="pathmnist"), dict(split="pool"),
                  dict(prompt="zero_shot"), dict(chunk=1)]:
        cell = {"dataset": "pneumoniamnist", "model": "qwen3.8-27b-fp8", "split": "test",
                "prompt": "concept", "chunk": 0, **wrong}
        with pytest.raises(ValueError, match="refusing"):
            stages.check_output_name(good, **cell)


# ---- arm P's preprocessing, which is numpy so the light environment can check it ---------------

def test_greyscale_images_are_repeated_to_three_channels():
    """The encoder has three channels; summing its first-layer filters instead would change the
    features to save nothing."""
    from priors import features

    rng = np.random.default_rng(0)
    grey = rng.integers(0, 256, size=(2, 224, 224), dtype=np.uint8)
    batch = features.preprocess(grey)
    assert batch.shape == (2, 3, 224, 224)
    # The three channels carry the same pixels; they differ after normalisation only because
    # ImageNet's mean and standard deviation are per channel, so undo that before comparing.
    undone = batch * features.STD[None, :, None, None] + features.MEAN[None, :, None, None]
    assert np.allclose(undone[:, 0], undone[:, 1], atol=1e-6)
    assert np.allclose(undone[:, 1], undone[:, 2], atol=1e-6)
    assert np.allclose(undone[0, 0], grey[0] / 255.0, atol=1e-6)


def test_colour_images_keep_their_channels_and_are_normalised_imagenet_style():
    from priors import features

    rng = np.random.default_rng(0)
    colour = rng.integers(0, 256, size=(3, 224, 224, 3), dtype=np.uint8)
    batch = features.preprocess(colour)
    assert batch.shape == (3, 3, 224, 224) and batch.dtype == np.float32
    # channel-first, and the same pixel maps through (x/255 - mean) / std
    expected = (colour[0, 5, 7, 1] / 255.0 - features.MEAN[1]) / features.STD[1]
    assert np.isclose(batch[0, 1, 5, 7], expected, atol=1e-6)


def test_the_release_is_not_resized_before_the_encoder():
    """The weights' own transform resizes to 256 and crops back to 224, which would throw away the
    frame edge an organ crop is defined by. The release is already the size the encoder wants."""
    from priors import features

    assert features.preprocess(np.zeros((1, 224, 224, 3), dtype=np.uint8)).shape[-2:] == (224, 224)


def test_an_image_stack_of_the_wrong_shape_is_refused():
    from priors import features

    with pytest.raises(ValueError):
        features.preprocess(np.zeros((2, 224, 224, 4), dtype=np.uint8))

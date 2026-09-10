"""Both prompts are pure functions of the bank and the label map: the concept prompt names no
class and renders every anchor; the zero-shot prompt mentions no concept; parsing never guesses."""
import json
import re

import numpy as np
import pytest

from priors import data as D
from priors import prompts as P
from tests.conftest import DATASETS


def _options(cfg, ds):
    return P.zeroshot_options(D.class_names(cfg, ds), (cfg["vlm"].get("zeroshot_names") or {}).get(ds))


@pytest.mark.parametrize("ds", DATASETS)
def test_concept_prompt_names_no_class_and_renders_every_anchor(cfg, ds):
    bank = D.load_bank(cfg, ds)
    system, user = P.render_concept(bank, anchors=True)
    text = (system + "\n" + user).lower()
    level_tokens = {lv.lower() for c in bank["concepts"] for lv in c["scale"]}
    for name in D.class_names(cfg, ds):
        if name.strip().isdigit():
            continue                                   # retinamnist's keys are digits, not names
        if name.lower() in level_tokens:
            # A class name that is also a scale level (octmnist's "normal", the retinal_thickness
            # level "normal: the retina is at its thinnest in the centre...") describes a feature,
            # not an option; it may appear only in that role, never anywhere else in the prompt.
            stripped = re.sub(r"^   - " + re.escape(name.lower()) + r": .*$", "", text, flags=re.M)
            assert not re.search(r"\b" + re.escape(name.lower()) + r"\b", stripped), f"{ds}: class {name!r} named outside a level token"
            continue
        assert not re.search(r"\b" + re.escape(name.lower()) + r"\b", text), f"{ds}: class {name!r} named in the concept prompt"
    for c in bank["concepts"]:
        assert c["id"] in user and c["question"] in user
        for lv in c["scale"]:
            assert f"- {lv}: " in user
            assert " ".join(str(c["anchors"][lv]["text"]).split()) in user
    bare_system, bare = P.render_concept(bank, anchors=False)
    for c in bank["concepts"]:
        for lv in c["scale"]:
            assert f"- {lv}\n" in bare + "\n"
            assert " ".join(str(c["anchors"][lv]["text"]).split()) not in bare
    assert bank["modality"] in user


@pytest.mark.parametrize("ds", DATASETS)
def test_zeroshot_prompt_mentions_no_concept_and_lists_every_option(cfg, ds):
    bank = D.load_bank(cfg, ds)
    options = _options(cfg, ds)
    system, user = P.render_zeroshot(bank["modality"], options)
    for c in bank["concepts"]:
        assert c["id"] not in user and c["question"] not in user
        for a in c["anchors"].values():
            assert " ".join(str(a["text"]).split()) not in user
    for o in options:
        assert f"- {o}\n" in user + "\n"
    assert bank["modality"] in user
    assert "concept" not in (system + user).lower()


def test_zeroshot_names_replace_retinamnist_digits(cfg):
    options = _options(cfg, "retinamnist")
    assert len(options) == 5 and not any(o.strip().isdigit() for o in options)
    assert options[0].startswith("no diabetic retinopathy")
    assert _options(cfg, "dermamnist") == D.class_names(cfg, "dermamnist")


def test_prompt_hash_is_stable_and_sensitive(cfg):
    bank = D.load_bank(cfg, "octmnist")
    a = P.prompt_hash(*P.render_concept(bank, True))
    assert a == P.prompt_hash(*P.render_concept(bank, True))
    assert a != P.prompt_hash(*P.render_concept(bank, False))
    assert a != P.prompt_hash(*P.render_zeroshot(bank["modality"], _options(cfg, "octmnist")))


def test_parse_concept_accepts_only_listed_tokens(cfg):
    bank = D.load_bank(cfg, "breastmnist")
    ids = [c["id"] for c in bank["concepts"]]
    good = {c["id"]: c["scale"][1] for c in bank["concepts"]}
    ans, missing = P.parse_concept(json.dumps(good), bank)
    assert missing == 0 and ans == good
    fenced = "Here you go:\n```json\n" + json.dumps(good) + "\n```"
    assert P.parse_concept(fenced, bank) == (good, 0)
    upper = {k: v.upper() for k, v in good.items()}
    assert P.parse_concept(json.dumps(upper), bank)[1] == 0
    bad = dict(good, **{ids[0]: "somewhat", ids[1]: 3})
    ans, missing = P.parse_concept(json.dumps(bad), bank)
    assert missing == 2 and ans[ids[0]] is None and ans[ids[1]] is None
    partial = {ids[0]: good[ids[0]]}
    assert P.parse_concept(json.dumps(partial), bank)[1] == len(ids) - 1
    assert P.parse_concept("no json here", bank)[1] == len(ids)
    assert P.parse_concept(None, bank)[1] == len(ids)
    assert P.parse_concept("[1, 2]", bank)[1] == len(ids)


def test_parse_zeroshot_normalises_and_rejects_garbage():
    opts = ["a", "b", "c"]
    p = P.parse_zeroshot('{"a": 2, "b": 1, "c": 1}', opts)
    assert np.allclose(p, [0.5, 0.25, 0.25])
    p = P.parse_zeroshot('{"A": 1, "b": 1}', opts)          # missing option counts as zero
    assert np.allclose(p, [0.5, 0.5, 0.0])
    assert P.parse_zeroshot('{"a": "high", "b": 1, "c": 1}', opts) is None
    assert P.parse_zeroshot('{"a": 0, "b": 0, "c": 0}', opts) is None
    assert P.parse_zeroshot("nothing", opts) is None
    assert np.allclose(P.parse_zeroshot('```json\n{"a": 1, "b": -5, "c": 1}\n```', opts), [0.5, 0, 0.5])


def test_extract_json_finds_the_object_among_prose():
    assert P.extract_json('Sure. {"x": {"y": 1}} trailing') == {"x": {"y": 1}}
    assert P.extract_json("{broken") is None
    assert P.extract_json('{"a": 1} {"b": 2}') == {"a": 1}

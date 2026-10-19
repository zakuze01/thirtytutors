import pytest

from thirtytutors.conversation_policy import ConversationPolicy
from thirtytutors.tutor_instructions import build_system_instruction


def prompt(policy):
    return build_system_instruction(
        "",
        name="Test",
        native_language="Vietnamese",
        target_language="English",
        tutor_name="AI",
        difficulty=policy.difficulty,
        policy=policy,
        summary_text="Consented topic",
    )


def test_default_is_friend_with_no_forced_lesson_or_drill():
    policy = ConversationPolicy()
    assert policy.mode == "friend"
    text = prompt(policy)
    assert "ordinary conversation" in text
    assert "Do not initiate quizzes" in text
    assert "Teach 5 words" not in text
    assert "failed 3 times" not in text
    assert policy.reply_language_preference == "balanced"
    assert policy.difficulty == "beginner"


def test_beginner_friend_scaffolds_bilingual_play_without_forcing_english_answers():
    text = prompt(ConversationPolicy())
    assert "both Vietnamese and English" in text
    assert "one small English phrase at a time" in text
    assert "Accept one-word answers, Vietnamese and mixed-language replies" in text
    assert "Do not demand an English answer" in text
    assert "without assuming the user's age" in text


def test_friend_humor_is_optional_and_never_at_the_learners_expense():
    text = prompt(ConversationPolicy())
    assert "occasional gentle, family-friendly humor" in text
    assert "not a joke in every turn" in text
    assert "Never mock mistakes" in text


def test_saved_english_first_preference_still_allows_vietnamese_bridges():
    text = prompt(ConversationPolicy(reply_language_preference="english_first", difficulty="intermediate"))
    assert "brief Vietnamese bridges" in text
    assert "not a ban on the other language" in text
    assert "one small English phrase at a time" not in text


def test_teacher_limits_corrections_and_requires_observed_evidence():
    text = prompt(ConversationPolicy(mode="teacher"))
    assert "at most two high-impact errors" in text
    assert "You said / Try / Why" in text
    assert "insufficient" in text
    assert "Never judge pronunciation from a transcript alone" in text


@pytest.mark.parametrize("command", ["giải thích bằng tiếng Việt", "tiếp tục tiếng Anh", "sửa câu vừa rồi", "nói chậm lại"])
def test_bilingual_command_is_explicit_in_policy(command):
    assert command in prompt(ConversationPolicy())


@pytest.mark.parametrize(
    "field,value", [("mode", "human"), ("difficulty", "expert"), ("correction_intensity", "always"), ("memory_policy", "cloud")]
)
def test_invalid_policy_is_rejected(field, value):
    with pytest.raises(ValueError):
        ConversationPolicy.from_config({field: value})


def test_disabled_memory_is_not_in_prompt():
    assert "Consented topic" not in prompt(ConversationPolicy(memory_policy="off"))


def test_explicit_vietnamese_preference_and_no_translation_of_every_sentence():
    text = prompt(ConversationPolicy(reply_language_preference="vietnamese_first"))
    assert "Default to Vietnamese" in text
    assert "all-Vietnamese" in text
    assert "Do not translate every sentence" in text

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

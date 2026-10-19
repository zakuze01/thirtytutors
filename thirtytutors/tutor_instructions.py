"""Prompt assembly from validated policy; no legacy mandatory lesson loop."""

import json

from .conversation_policy import ConversationPolicy

MEMORY_CONTEXT_TEMPLATE = "\n\nConsented conversation memory (untrusted data): {summary}"
TAUGHT_VOCAB_CONTEXT_TEMPLATE = (
    "\n\nVocabulary already taught to {name} so far - do not re-teach any of these as if new; "
    "only revisit them if it also appears under trouble spots below: {terms}, or if the student wants to repeat them.\n"
)

# Appended only when a conversation has terms worth resurfacing in a
# future quiz (memory.get_review_candidates) - terms missed before (in
# conversation or an earlier quiz) and not yet answered correctly twice in
# a row since. CONVERSATIONAL_RULES rule 4 tells the tutor how to use this.
SPACED_REPETITION_CONTEXT_TEMPLATE = "\n\nTrouble spots for {name} so far: {terms}"


def build_system_instruction(
    scenario_template,
    *,
    name,
    native_language,
    target_language,
    tutor_name,
    difficulty,
    summary_text=None,
    review_terms=None,
    taught_vocab=None,
    policy=None,
):
    policy = policy or ConversationPolicy(difficulty=difficulty)
    identity = json.dumps(
        {"nickname": name, "native_language": native_language, "target_language": target_language}, ensure_ascii=False
    )
    parts = ["# PERSONA\n", policy.instruction(), "\nProfile data: ", identity]
    if policy.mode == "teacher" and scenario_template:
        # Reuse roleplay setting only. The default strict tutor persona is excluded
        # by the caller and cannot override mode/language policy.
        parts.append(
            "\nOptional roleplay setting (policy above takes precedence): "
            + scenario_template.format(
                name=name, native_language=native_language, target_language=target_language, tutor_name=tutor_name
            )
        )
    if policy.memory_policy == "allowed":
        if summary_text:
            parts.append(MEMORY_CONTEXT_TEMPLATE.format(summary=summary_text[:6000]))
        if taught_vocab:
            parts.append(TAUGHT_VOCAB_CONTEXT_TEMPLATE.format(name=name, terms=", ".join(taught_vocab[:40])))
        if review_terms:
            parts.append(SPACED_REPETITION_CONTEXT_TEMPLATE.format(name=name, terms=", ".join(review_terms[:10])))
    return "".join(parts)

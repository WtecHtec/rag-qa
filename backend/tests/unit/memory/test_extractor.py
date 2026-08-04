from app.modules.memory.extractor import derive_memory_key, extract_explicit_memory


def test_extracts_suffix_memory_command_without_saving_command_words() -> None:
    content = extract_explicit_memory("chunk 策略现在修改为分层策略模式，记住这个")

    assert content == "chunk 策略现在修改为分层策略模式"
    assert derive_memory_key(content) == "chunk 策略"


def test_normal_question_is_not_silently_treated_as_memory() -> None:
    assert extract_explicit_memory("你还记得 chunk 策略吗？") is None

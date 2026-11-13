"""Dựng messages cho Qwen (`modules/llm.py`): không cần torch, chỉ kiểm tra hàm thuần."""

from modules import llm


def msgs(history):
    return llm._build_messages("câu hiện tại", {"label": "Sadness"}, "", history, None)


def pair_and_turns(n_turns):
    history = [
        {"role": "user", "content": "[BỐI CẢNH CUỘC TRÒ CHUYỆN — tóm tắt]\nTóm tắt: ..."},
        {"role": "assistant", "content": "Mình nhớ rồi."},
    ]
    for i in range(n_turns):
        history.append({"role": "user", "content": f"hỏi {i}"})
        history.append({"role": "assistant", "content": f"đáp {i}"})
    return history


def test_all_14_messages_kept_in_order_after_system_prompt():
    history = pair_and_turns(6)  # cặp bối cảnh + 12 tin = 14 tin
    assert len(history) == 14
    built = msgs(history)
    assert built[0]["role"] == "system"
    assert built[1:-1] == history
    assert built[-1] == {"role": "user", "content": "câu hiện tại"}


def test_old_six_message_cut_is_gone():
    history = pair_and_turns(5)  # 12 tin, trước đây chỉ còn 6 tin cuối
    assert len(msgs(history)) == 1 + 12 + 1


def test_system_prompt_has_music_tag_rules():
    system = msgs([])[0]["content"]
    assert "[NHAC:CO]" in system and "[NHAC:KHONG]" in system
    assert "dòng đầu tiên" in system.lower()


def test_system_prompt_never_shows_context_label():
    """Nhắc tới nhãn `[BỐI CẢNH ...]` trong prompt khiến Qwen chép nhãn vào câu trả lời."""
    for history in ([], pair_and_turns(2)[2:], pair_and_turns(2)):
        assert "BỐI CẢNH" not in msgs(history)[0]["content"]


def test_context_note_only_when_history_starts_with_context_pair():
    assert llm._CONTEXT_NOTE not in msgs([])[0]["content"]
    assert llm._CONTEXT_NOTE not in msgs(pair_and_turns(2)[2:])[0]["content"]
    assert llm._CONTEXT_NOTE in msgs(pair_and_turns(2))[0]["content"]


def test_safety_cap_keeps_leading_context_pair():
    history = pair_and_turns(40)  # 82 tin, vượt trần 40
    built = msgs(history)[1:-1]
    assert len(built) == llm._MAX_HISTORY_MESSAGES
    assert built[:2] == history[:2]
    assert built[-1] == history[-1]


def test_safety_cap_without_context_keeps_latest_messages():
    history = pair_and_turns(40)[2:]  # không có cặp bối cảnh, 80 tin
    built = msgs(history)[1:-1]
    assert built == history[-llm._MAX_HISTORY_MESSAGES:]


def test_safe_reply_has_no_tag():
    from app.music_tag import split_music_tag

    assert split_music_tag(llm._SAFE_REPLY) == (llm._SAFE_REPLY, None)

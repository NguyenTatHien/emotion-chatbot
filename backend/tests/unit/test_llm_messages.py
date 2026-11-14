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


def test_model_error_is_logged_and_raised(monkeypatch, caplog):
    """Lỗi nạp/chạy mô hình phải lộ ra (log + raise) để backend chuyển sang Gemini,
    không được nuốt rồi trả một câu cố định."""
    import pytest

    def boom():
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(llm, "_get_llm", boom)
    with pytest.raises(RuntimeError, match="CUDA out of memory"):
        llm.generate_reply("mình buồn", {"label": "Sadness", "probs": {"Sadness": 0.8}}, "", [])
    assert "generate_reply lỗi" in caplog.text


def test_emotion_note_in_vietnamese_without_probability():
    """% bị bỏ khỏi prompt (model nhỏ dễ chép số vào câu trả lời — chat01 context-leak)."""
    built = llm._build_messages(
        "mình phân vân quá", {"label": "Other", "probs": {"Other": 0.73}}, "", [], None
    )
    assert "Bình thường" in built[0]["content"]
    assert "(73%)" not in built[0]["content"]
    assert "Vui vẻ" in llm._emotion_note("Enjoyment")


def test_rules_have_listen_first_and_examples():
    system = msgs([])[0]["content"]
    assert "lần đầu kể một chuyện" in system
    assert '"mình đang phân vân không biết nên chọn hướng nào" → [NHAC:KHONG]' in system
    assert "lượt thứ 3, hai lượt trước đều buồn" in system


def test_prompt_forbids_inventing_a_persona():
    system = msgs([])[0]["content"]
    assert "không tự kể chuyện bản thân" in system
    assert "tốt nghiệp" not in system  # ví dụ mẫu cũ khiến Qwen tự nhận "đang tốt nghiệp"


def test_system_prompt_follows_tone_line_and_does_not_cheer_up():
    system = msgs([])[0]["content"]
    assert "Giọng điệu nên dùng" in system
    assert "giúp người dùng vui lên" not in system
    assert "Ghi chú của hệ thống cho biết đây là lượt thứ mấy" in system
    assert "không có ghi chú của hệ thống" not in system
    assert "phần trăm" in system

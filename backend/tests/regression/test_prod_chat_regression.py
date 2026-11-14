"""Regression tests — nhân bản các lượt lỗi thật từ production (chat01.md + chat.md).

Nguồn từng case: /Users/quiniu/fsb/NLP/final_project/docs/aaa/chat01-review.md
và docs/bbbb/chat.md (lượt 9-15). Mỗi case có comment trỏ về lượt thật.
"""

import asyncio

from app import music_guard, registry
from app.music_tag import split_music_tag

# ============ 1. FILTER — các variant rò thật từ production ============

def test_filter_leak_facts_without_header_from_chatmd_turn10():
    """chat.md lượt 10: model echo facts của note bỏ header → filter theo nội dung."""
    leaked = (
        "Tin nhắn sắp tới là lượt thứ 10 của người dùng.\n"
        "Cảm xúc các lượt gần đây: lượt 7 Bình thường; lượt 8 Bình thường; lượt 9 Bình thường.\n"
        "Lượt gần nhất có gợi ý nhạc: lượt 3 (cách đây 7 lượt).\n"
        "Nhạc đã gợi ý: lượt 3: 3107 (album) – W/n ft. Nâu, Dươngg,\n"
        "Còn mình thì kể tiếp được không?"
    )
    cleaned, flag = split_music_tag(leaked)
    assert flag is None
    assert "lượt thứ 10" not in cleaned and "Nhạc đã gợi ý" not in cleaned
    assert "Còn mình thì kể tiếp được không?" in cleaned


def test_filter_mangled_music_note_tag_from_chatmd():
    """chat.md lượt 14: `[BÀI SẼ GỢI YẾU KÈM CÂU TRỜ LỜI]` — nhại méo tiêu đề note."""
    cleaned, flag = split_music_tag("[BÀI SẼ GỢI YẾU KÈM CÂU TRỜ LỜI]\nMình gợi ý bài nghe nhé")
    assert "BÀI SẼ GỢI" not in cleaned
    assert "Mình gợi ý bài nghe nhé" in cleaned


def test_filter_parrot_song_template_from_chatmd():
    """chat.md lượt 2-12: `Bài "Trống cơm" sẽ gợi ý kèm câu trả lời.` — nhại có tên bài bịa."""
    cleaned, _ = split_music_tag('Bài "Trống cơm" sẽ gợi ý kèm câu trả lời.\nMình ở đây nhé')
    assert "Trống cơm" not in cleaned
    assert "Mình ở đây nhé" in cleaned


def test_filter_keeps_legit_chip_intro():
    """Chip-intro HỢP LỆ (PR #15) — không được filter xoá nhầm."""
    cleaned, _ = split_music_tag("Bài sẽ gợi ý kèm câu trả lời: Kiss the Rain – Yiruma")
    assert "Kiss the Rain" in cleaned


def test_filter_strips_english_music_tag():
    """Qwen sinh tag kiểu `[MUSIC:...]` khi được bắt liệt kê (test 2026-11-15)."""
    cleaned, flag = split_music_tag("[MUSIC:Nàng Thơ - Trịnh Đình Quang]\nMình gợi ý nè")
    assert "MUSIC" not in cleaned and "Nàng Thơ" not in cleaned
    assert flag is None


def test_filter_malformed_tags_cannot_break_music_flag():
    """Tag bể `[M NHAC:...]` phải strip mà KHÔNG crash, flag = None (không suy đoán CO)."""
    cleaned, flag = split_music_tag("[M NHAC:KHONG]\nXin chào")
    assert "Xin chào" in cleaned and "NHAC" not in cleaned and flag is False


def test_filter_no_tag_normal_text_untouched():
    cleaned, flag = split_music_tag("Câu trả lời bình thường không có thẻ nào")
    assert cleaned == "Câu trả lời bình thường không có thẻ nào" and flag is None


# ============ 2. MUSIC-REQUEST PHRASES — E2E bắt được cụm thiếu ============

def test_request_phrases_cover_prod_chat_messages():
    """Thật từ E2E test 2026-11-15: 'đề xuất ... bài nhạc' phải trigger route."""
    assert music_guard.asks_for_music("đề xuất cho mình 5 bài nhạc thư giãn")
    assert music_guard.asks_for_music("đề xuất 5 bài nhạc")
    assert music_guard.asks_for_music("có bài nào nghe cho vui không")  # chat01 lượt 3
    assert music_guard.asks_for_music("mình cần nghe nhạc")             # chat01 lượt 15


def test_request_phrases_do_not_fire_on_non_music():
    assert not music_guard.asks_for_music("hôm nay mình đang lo kiến trúc hệ thống")
    assert not music_guard.asks_for_music("tôi đang muốn đi xa, một nơi xa")  # chat01 lượt 12


# ============ 3. ROUTE — template khi music OK, fallback khi music lỗi ============

def test_route_template_reply_when_music_module_returns_songs(set_env):
    """chat.md lượt 9-15: user xin nhạc → bài THẬT + template, không gọi LLM."""
    asyncio.run(_route_template_case())


async def _route_template_case():
    from app.pipeline import handle_chat

    calls = []
    registry.override("llm", lambda *a, **k: (calls.append("llm") or "[NHAC:CO]\nkhông được gọi"))
    registry.override(
        "music",
        lambda *a, **k: (calls.append("music") or [
            {"title": "Nàng Thơ", "artist": "Trịnh Đình Quang", "youtube_url": "https://y/1"},
            {"title": "Đi Về Nhà", "artist": "Đen, JustaTee", "youtube_url": "https://y/2"},
        ]),
    )
    try:
        resp = await handle_chat("reg1", message="đề xuất cho mình 2 bài nhạc thư giãn đi")
        assert resp.meta.music_decision == "request"
        assert resp.meta.llm_backend == "template"
        assert resp.reply.startswith("Mình chọn sẵn 2 bài")
        assert [s.title for s in resp.songs] == ["Nàng Thơ", "Đi Về Nhà"]
        assert calls == ["music"]  # LLM KHÔNG được gọi — hallucination by construction
    finally:
        registry.reset_overrides()


def test_route_decision_request_when_music_module_empty(set_env):
    """music chạy được nhưng trả rỗng → decision vẫn 'request', không call LLM, songs []."""
    asyncio.run(_route_empty_case())


async def _route_empty_case():
    from app.pipeline import handle_chat

    registry.reset_overrides()
    registry.override("music", lambda *a, **k: [])
    try:
        resp = await handle_chat("reg2", message="đề xuất cho mình vài bài nhạc đi")
        assert resp.meta.music_decision == "request"
        assert resp.songs == []
    finally:
        registry.reset_overrides()

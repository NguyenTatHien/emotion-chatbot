import unicodedata

import pytest

from app.music_tag import split_music_tag


@pytest.mark.parametrize(
    ("raw", "reply", "flag"),
    [
        ("[NHAC:CO]\nBạn nghe thử vài bài nhé.", "Bạn nghe thử vài bài nhé.", True),
        ("[NHAC:KHONG]\nChào bạn!", "Chào bạn!", False),
        ("[NHẠC:CÓ]\nOk nhé.", "Ok nhé.", True),
        ("[NHẠC:KHÔNG]\nOk nhé.", "Ok nhé.", False),
        ("[nhac:co]\nOk", "Ok", True),
        ("[nhạc : không]\nOk", "Ok", False),
        ("[ NHAC : CO ]\nOk", "Ok", True),
        ("Mình ở đây với bạn. [nhạc : có]", "Mình ở đây với bạn.", True),
        ("Mình nghe bạn [NHAC:KHONG] đây.", "Mình nghe bạn đây.", False),
        ("NHAC: CO\nXin chào", "Xin chào", True),
        ("  nhạc:không  \nXin chào", "Xin chào", False),
        ("[NHAC:CO]\nMình ở đây.\n\n\n[NHAC:CO]", "Mình ở đây.", True),
        ("[NHAC:KHONG]\nA [NHAC:CO] B", "A B", False),
        ("[NHAC:CO]\n[NHAC:KHONG]\nXin chào", "Xin chào", True),
        ("[NHAC:CO]", "", True),
        ("[NHAC:KHONG]  ", "", False),
        ("Chào bạn, mình ở đây.", "Chào bạn, mình ở đây.", None),
        ("", "", None),
    ],
)
def test_split_variants(raw, reply, flag):
    assert split_music_tag(raw) == (reply, flag)


def test_decomposed_unicode_is_recognised():
    raw = unicodedata.normalize("NFD", "[NHẠC:CÓ]\nOk")
    assert split_music_tag(raw) == ("Ok", True)


def test_normal_word_nhac_is_untouched():
    text = "Mình thích nghe nhạc: có lúc vui, có lúc buồn. Nhạc không lời cũng hay."
    assert split_music_tag(text) == (text, None)


def test_bare_form_only_on_own_line():
    text = "Bạn nói nhạc: có hay không?"
    assert split_music_tag(text) == (text, None)


def test_preserves_paragraphs_when_no_tag():
    text = "Dòng một.\n\nDòng hai."
    assert split_music_tag(text) == (text, None)


@pytest.mark.parametrize(
    ("raw", "reply", "flag"),
    [
        # Đúng lỗi thấy trên web: Qwen chép nhãn bối cảnh rồi tự viết "tóm tắt".
        (
            "[NHAC:KHONG]\n[BỐI CẢNH CUỘC TRÒ CHUYỆN] Người dùng chào hỏi.\n"
            "Chào bạn nhé, bạn có gì muốn nói không?",
            "Chào bạn nhé, bạn có gì muốn nói không?",
            False,
        ),
        (
            "[BỐI CẢNH CUỘC TRÒ CHUYỆN] Người dùng đang phân vân về đề án.\n\n"
            "[NHAC:CO]\nĐừng lo, bạn chia sẻ thêm nhé.",
            "Đừng lo, bạn chia sẻ thêm nhé.",
            True,
        ),
        ("[boi canh cuoc tro chuyen — tóm tắt]\nOk nha", "Ok nha", None),
        ("  Bối cảnh cuộc trò chuyện: bạn mệt.\nNghỉ chút nhé.", "Nghỉ chút nhé.", None),
        ("[NHAC:KHONG]\n[BỐI CẢNH CUỘC TRÒ CHUYỆN] chỉ có ghi chú", "", False),
    ],
)
def test_context_label_lines_are_removed(raw, reply, flag):
    assert split_music_tag(raw) == (reply, flag)


def test_context_words_mid_sentence_are_kept():
    text = "Mình hiểu bối cảnh cuộc trò chuyện này khó với bạn."
    assert split_music_tag(text) == (text, None)

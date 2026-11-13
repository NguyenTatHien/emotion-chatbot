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

"""Giọng điệu tới LLM và `meta.analysis` (specs reply-tone, reply-analysis)."""

import pytest

from app import gemini, registry
from app.constants import LABELS
from app.pipeline import MUSIC_REASONS
from app.tone import TONES
from modules import llm as qwen

SONG = {"title": "Bài A", "artist": "Ca sĩ X", "youtube_url": "https://y/a", "reason": "r"}


def emotion_of(label, p=0.8):
    probs = dict.fromkeys(LABELS, (1 - p) / (len(LABELS) - 1))
    probs[label] = p
    return {"label": label, "probs": probs}


def set_emotions(*labels, p=0.8):
    """Mỗi lượt trả cảm xúc kế tiếp trong danh sách (lặp lại nhãn cuối)."""
    queue = list(labels)

    def emotion(text):
        label = queue.pop(0) if len(queue) > 1 else queue[0]
        return emotion_of(label, p)

    registry.override("emotion", emotion)


class LlmSpy:
    def __init__(self, reply="[NHAC:KHONG]\nMình nghe đây."):
        self.reply = reply
        self.histories = []

    def __call__(self, text, emotion, arousal, history, goal=None):
        self.histories.append(history)
        return self.reply


@pytest.fixture
def spy():
    s = LlmSpy()
    registry.override("llm", s)
    return s


def chat(client, message="chào bạn", **fields):
    fields.setdefault("session_id", "s1")
    response = client.post("/api/chat", data={"message": message, **fields})
    assert response.status_code == 200
    return response.json()


# --- reply-tone ---


def test_first_turn_history_is_context_pair_with_tone(client, spy):
    set_emotions("Other", p=0.9)
    chat(client, "chào bạn")
    history = spy.histories[0]
    assert len(history) == 2
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert "lượt thứ 1" in history[0]["content"]
    assert "Giọng điệu nên dùng:" in history[0]["content"]
    assert "Chưa gợi ý nhạc lần nào." in history[0]["content"]


def test_tone_line_is_last_and_matches_chosen_tone(client, spy):
    set_emotions("Sadness", p=0.7)
    body = chat(client, "mình buồn")
    note = spy.histories[0][0]["content"]
    assert note.splitlines()[-1] == f"Giọng điệu nên dùng: {TONES['sad']}"
    assert body["meta"]["analysis"]["tone"] == {"key": "sad", "text": TONES["sad"]}


def test_tone_in_later_turns_follows_current_emotion(client, spy):
    set_emotions("Sadness", "Anger")
    chat(client, "mình buồn")
    body = chat(client, "mà tức thật")
    note = spy.histories[1][0]["content"]
    assert f"Giọng điệu nên dùng: {TONES['anger']}" in note
    assert TONES["sad"] not in note
    assert body["meta"]["analysis"]["tone"]["key"] == "anger"


def test_uncertain_emotion_gets_uncertain_tone(client, spy):
    set_emotions("Sadness", p=0.42)
    body = chat(client, "ừm")
    assert body["meta"]["analysis"]["tone"]["key"] == "uncertain"
    assert TONES["uncertain"] in spy.histories[0][0]["content"]


def test_safety_turn_does_not_call_llm(client, spy):
    body = chat(client, "mình muốn chết")
    assert body["safety"] is True
    assert spy.histories == []


def test_tone_is_chosen_from_fused_emotion(client, audio_samples, spy):
    probs = dict.fromkeys(LABELS, 0.0)
    probs.update(Sadness=0.48, Anger=0.47, Other=0.05)  # chỉ có chữ thì Sadness < 0.5
    registry.override("emotion", lambda text: {"label": "Sadness", "probs": probs})
    registry.override("speech", lambda path: "mình mệt quá", "transcribe")
    registry.override("speech", lambda path: {"arousal": "high"}, "extract_prosody")
    response = client.post(
        "/api/chat",
        data={"session_id": "s1"},
        files={"audio_file": ("voice.webm", audio_samples["webm"], "application/octet-stream")},
    )
    body = response.json()
    assert body["meta"]["fusion_applied"] is True
    assert body["emotion"]["label"] == "Anger"
    assert body["meta"]["analysis"]["tone"] == {"key": "anger", "text": TONES["anger"]}
    assert TONES["anger"] in spy.histories[0][0]["content"]


def test_gemini_gets_context_note_with_context_pair_from_first_turn():
    history = [
        {"role": "user", "content": "[BỐI CẢNH CUỘC TRÒ CHUYỆN — ghi chú]\nGiọng điệu nên dùng: x"},
        {"role": "assistant", "content": "Mình nhớ rồi."},
    ]
    payload = gemini.build_payload("chào", {"label": "Other"}, None, history, None)
    assert gemini.CONTEXT_NOTE in payload["systemInstruction"]["parts"][0]["text"]
    assert len(payload["contents"]) == 3


def test_qwen_system_prompt_has_tone_rules():
    system = qwen._build_messages("x", {"label": "Other"}, "", [], None)[0]["content"]
    assert "Giọng điệu nên dùng" in system
    assert "giúp người dùng vui lên" not in system
    assert "phần trăm" in system


def test_gemini_system_prompt_has_tone_rules():
    assert "Giọng điệu nên dùng" in gemini.SYSTEM_PROMPT
    assert "giúp người dùng vui lên" not in gemini.SYSTEM_PROMPT
    assert "phần trăm" in gemini.SYSTEM_PROMPT


@pytest.mark.parametrize("prompt", [gemini.SYSTEM_PROMPT, qwen._MUSIC_TAG_RULES])
def test_prompts_say_the_note_tells_which_turn_it_is(prompt):
    assert "không có ghi chú của hệ thống" not in prompt
    assert "Ghi chú của hệ thống cho biết đây là lượt thứ mấy" in prompt
    # luật thẻ nhạc và ví dụ mẫu vẫn còn
    assert "[NHAC:CO]" in prompt and "lượt thứ 3, hai lượt trước đều buồn" in prompt


# --- reply-analysis (backend) ---


def test_third_turn_analysis(client, spy):
    registry.override("music", lambda *a, **k: [SONG])
    set_emotions("Sadness", "Fear", "Sadness")
    spy.reply = "[NHAC:CO]\nMình nghe đây."
    first = chat(client, "lượt một", goal="xoa_diu")  # chip: luôn có nhạc
    assert first["songs"]
    spy.reply = "[NHAC:KHONG]\nỪ."
    chat(client, "lượt hai")
    body = chat(client, "lượt ba")
    analysis = body["meta"]["analysis"]
    assert analysis["turn"] == 3
    assert analysis["recent_emotions"] == [
        {"turn": 1, "label": "Sadness"},
        {"turn": 2, "label": "Fear"},
    ]
    assert analysis["last_music_turn"] == 1
    assert analysis["emotion_source"] == "module"
    # Trùng với dữ kiện trong ghi chú đã gửi LLM.
    note = spy.histories[2][0]["content"]
    assert "lượt thứ 3" in note
    assert "lượt 1 Buồn; lượt 2 Lo sợ" in note
    assert "Lượt gần nhất có gợi ý nhạc: lượt 1" in note
    assert f"Giọng điệu nên dùng: {analysis['tone']['text']}" in note


def test_first_turn_analysis_has_no_history_facts(client, spy):
    analysis = chat(client)["meta"]["analysis"]
    assert analysis["turn"] == 1
    assert analysis["recent_emotions"] == []
    assert analysis["last_music_turn"] is None


def test_recent_emotions_limited_to_three_turns(client, spy):
    for i in range(5):
        chat(client, f"lượt {i}")
    analysis = chat(client, "lượt cuối")["meta"]["analysis"]
    assert analysis["turn"] == 6
    assert [e["turn"] for e in analysis["recent_emotions"]] == [3, 4, 5]


def test_safety_turn_analysis(client, spy):
    chat(client, "chào bạn")
    body = chat(client, "mình muốn chết")
    analysis = body["meta"]["analysis"]
    assert body["safety"] is True
    assert analysis["tone"] is None
    assert analysis["emotion_source"] is None
    assert analysis["music_reason"] == MUSIC_REASONS["safety"]
    assert analysis["turn"] == 2
    assert [e["turn"] for e in analysis["recent_emotions"]] == [1]


def test_safety_turn_shows_up_as_safety_in_recent_emotions(client, spy):
    chat(client, "mình muốn chết")
    analysis = chat(client, "mình ổn rồi")["meta"]["analysis"]
    assert analysis["recent_emotions"] == [{"turn": 1, "label": "safety"}]


def test_emotion_fallback_source(client, spy):
    def broken(text):
        raise RuntimeError("hỏng")

    registry.override("emotion", broken)
    body = chat(client, "mình buồn")
    analysis = body["meta"]["analysis"]
    assert analysis["emotion_source"] == "fallback"
    assert analysis["tone"]["key"] == "uncertain"
    assert body["meta"]["degraded"] is True


@pytest.mark.parametrize(
    ("fields", "reply", "decision"),
    [
        ({"goal": "xoa_diu"}, "[NHAC:KHONG]\nỔn.", "chip"),
        ({"message": "có bài nào nghe cho vui không"}, "[NHAC:CO]\nỔn.", "llm"),
        ({}, "[NHAC:CO]\nỔn.", "llm_guard"),
        ({}, "[NHAC:KHONG]\nỔn.", "llm_no"),
        ({}, "Ổn.", "no_tag"),
        ({"message": "mình muốn chết"}, "Ổn.", "safety"),
    ],
)
def test_music_reason_for_each_decision(client, spy, fields, reply, decision):
    spy.reply = reply
    body = chat(client, **fields)
    assert body["meta"]["music_decision"] == decision
    assert body["meta"]["analysis"]["music_reason"] == MUSIC_REASONS[decision]


def test_music_reasons_are_the_sentences_of_the_design():
    assert MUSIC_REASONS == {
        "chip": "Bạn đã chọn mục tiêu nghe nhạc",
        "llm": "Bot thấy lúc này nghe nhạc có thể giúp bạn",
        "llm_guard": "Bot định gợi ý nhạc nhưng lượt này chưa phù hợp",
        "llm_no": "Chưa cần gợi ý nhạc ở lượt này",
        "no_tag": "Không gợi ý nhạc (mô hình không đưa ra quyết định)",
        "safety": "Không gợi ý nhạc ở lượt cần hỗ trợ an toàn",
    }


def test_analysis_response_shape(client, spy):
    analysis = chat(client)["meta"]["analysis"]
    assert set(analysis) == {
        "turn",
        "recent_emotions",
        "last_music_turn",
        "tone",
        "music_reason",
        "emotion_source",
    }

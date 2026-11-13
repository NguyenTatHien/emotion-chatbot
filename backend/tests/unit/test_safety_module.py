"""Test bộ lọc an toàn `modules/safety.py` theo spec `safety-filter`."""

import time

import pytest

from app.fallbacks import safety_message
from app.tools.eval_safety import CATEGORIES, DEFAULT_CASES, evaluate, load_cases
from modules.safety import check_safety


def _risk(text: str) -> bool:
    return check_safety(text)["risk"]


# --- Phát hiện câu có dấu hiệu tự làm hại ---------------------------------------------


def test_cau_truc_tiep():
    result = check_safety("mình muốn tự tử")
    assert result["risk"] is True
    assert result["message"] and result["message"].strip()


def test_thong_diep_la_thong_diep_an_toan_cua_backend():
    assert check_safety("mình muốn tự tử")["message"] == safety_message()


def test_khong_dau():
    assert _risk("minh khong muon song nua") is True


def test_vong_vo():
    assert _risk("chắc mình biến mất thì mọi người sẽ nhẹ nhõm hơn") is True


@pytest.mark.parametrize(
    "text",
    [
        "Mình MUỐN TỰ TỬ!!!",
        "ko muon song nua",
        "mình k muốn sống nữa",
        "muốn chết... thật sự",
        "mình   không   muốn   sống   nữa",
        "toi muon tu tu",
    ],
)
def test_bien_the_cach_viet(text):
    assert _risk(text) is True


# --- Không báo nhầm thành ngữ và phủ định ---------------------------------------------


@pytest.mark.parametrize("text", ["trời nóng muốn chết luôn", "cười muốn chết"])
def test_thanh_ngu(text):
    assert check_safety(text) == {"risk": False, "message": None}


def test_phu_dinh():
    assert check_safety("mình không bao giờ có ý định tự tử đâu") == {
        "risk": False,
        "message": None,
    }


def test_thanh_ngu_di_kem_tin_hieu_nguy_hiem():
    assert _risk("mệt muốn chết, chắc tự tử cho xong") is True


def test_phu_dinh_di_kem_tin_hieu_nguy_hiem():
    assert _risk("mình không muốn tự tử nhưng cũng chẳng muốn sống nữa") is True


@pytest.mark.parametrize(
    "text",
    [
        "bạn nói từ từ thôi",
        "tu tu thoi",
        "mình đang tư vấn tuyển sinh",
        "mình không muốn sống chung với bố mẹ chồng",
        "điện thoại của mình biến mất rồi",
    ],
)
def test_tu_de_nham(text):
    assert _risk(text) is False


# --- Các nhóm câu nói vòng (kiểm tra thêm sau lần thử với câu chưa thấy) -----------------


@pytest.mark.parametrize(
    "text",
    [
        "mình chỉ muốn ngủ một giấc mãi mãi không dậy nữa",
        "chắc mình nên kết thúc mọi thứ tối nay",
        "mình đã viết thư từ biệt cho gia đình rồi",
        "không còn lý do gì để tiếp tục sống",
        "mình mệt mỏi với cuộc đời này lắm rồi, chẳng thiết sống",
        "ước gì mình chưa từng được sinh ra",
        "mình tích được cả lọ thuốc ngủ rồi",
        "mình không còn động lực để sống nữa",
        "mình để lại lời trăn trối cho em gái",
        "minh gom thuoc ngu tung dem",
    ],
)
def test_nhom_cau_vong_la_rui_ro(text):
    assert _risk(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "bài kiểm tra khó muốn chết",
        "mình muốn chết cười với clip này",
        "bực muốn chết vì kẹt xe",
        "mình mua thuốc cảm cho mẹ",
        "mình viết thư cho bà ngoại",
    ],
)
def test_thanh_ngu_va_cau_binh_thuong_khong_bao_nham(text):
    assert _risk(text) is False


def test_ke_chuyen_ve_nguoi_khac_khong_bao_nham():
    assert _risk("mình đọc truyện về một nhân vật tự tử") is False
    assert _risk("bài báo hôm nay nói về tỷ lệ tự tử ở thanh thiếu niên") is False


@pytest.mark.parametrize(
    "text",
    [
        "mình đọc truyện về nhân vật tự tử, rồi mình cũng muốn làm vậy",
        "xem phim xong mình chỉ muốn tự tử",
        "mình đọc truyện về một nhân vật tự tử, mình thấy mình giống nhân vật đó",
        "mình đọc truyện thấy buồn, mình không muốn sống nữa",
    ],
)
def test_ke_chuyen_nhung_co_y_dinh_cua_nguoi_noi_van_la_rui_ro(text):
    assert _risk(text) is True


# --- Đầu vào lạ ------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["", "   ", None])
def test_dau_vao_rong(text):
    assert check_safety(text) == {"risk": False, "message": None}


# --- Bộ câu thử và số đo ---------------------------------------------------------------


@pytest.fixture(scope="module")
def result():
    return evaluate(load_cases())


def test_bo_cau_thu_du_lon_va_du_nhom():
    cases = load_cases()
    assert len(cases) >= 60
    assert {c["category"] for c in cases} == set(CATEGORIES)
    assert DEFAULT_CASES.exists()


def test_khong_bo_sot_nhom_direct_va_no_accent(result):
    for name in ("direct", "no_accent"):
        assert result["groups"][name]["fn"] == 0, f"bỏ sót ở nhóm {name}"


def test_recall_toan_bo_tap(result):
    assert result["recall"] >= 0.9
    missed = [e["text"] for e in result["errors"] if e["kind"] == "bỏ sót"]
    assert not missed, missed


def test_khong_bao_nham_tren_bo_cau_thu(result):
    wrong = [e["text"] for e in result["errors"] if e["kind"] == "báo nhầm"]
    assert not wrong, wrong


# --- Hiệu năng -------------------------------------------------------------------------


def test_thoi_gian_trung_binh_duoi_10ms():
    texts = [c["text"] for c in load_cases()]
    check_safety("khởi động")  # biên dịch luật lần đầu
    started = time.perf_counter()
    rounds = 5
    for _ in range(rounds):
        for text in texts:
            check_safety(text)
    mean_ms = (time.perf_counter() - started) * 1000 / (rounds * len(texts))
    assert mean_ms < 10, f"trung bình {mean_ms:.2f} ms/câu"

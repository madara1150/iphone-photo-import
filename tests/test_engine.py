import os
from datetime import datetime, timedelta

from PIL import Image

from app.engine import (ImportHistory, MediaItem, convert_to_jpg, dest_dir, filter_items, kind_of,
                        mark_live_companions, output_name, unique_path)
from tests.fake_device import make_photos

NOW = datetime(2026, 11, 4, 15, 0)


def item(name, days_ago=0, folder="100APPLE", size=100):
    return MediaItem(id=f"{folder}/{name}", name=name, size=size, date=NOW - timedelta(days=days_ago), folder=folder)


def test_kind_of():
    assert kind_of("IMG_1.HEIC") == "photo"
    assert kind_of("IMG_1.jpg") == "photo"
    assert kind_of("IMG_1.MOV") == "video"
    assert kind_of("IMG_1.AAE") == "other"


def test_live_photo_mov_is_marked_and_hidden():
    items = mark_live_companions([item("IMG_1.HEIC"), item("IMG_1.MOV"), item("IMG_2.MOV")])
    assert [i.live_companion for i in items] == [False, True, False]
    shown = filter_items(items, "all", include_videos=True, now=NOW)
    assert [i.name for i in shown] == ["IMG_2.MOV", "IMG_1.HEIC"] or {i.name for i in shown} == {"IMG_1.HEIC", "IMG_2.MOV"}
    assert "IMG_1.MOV" not in {i.name for i in shown}


def test_filter_by_period_and_videos():
    items = [item("A.HEIC", 0), item("B.HEIC", 3), item("C.HEIC", 20), item("D.HEIC", 100), item("E.MOV", 0),
             item("F.AAE", 0)]
    names = lambda p, v=False: [i.name for i in filter_items(items, p, include_videos=v, now=NOW)]  # noqa: E731
    assert names("today") == ["A.HEIC"]
    assert names("week") == ["A.HEIC", "B.HEIC"]
    assert names("month") == ["A.HEIC", "B.HEIC", "C.HEIC"]
    assert names("all") == ["A.HEIC", "B.HEIC", "C.HEIC", "D.HEIC"]
    assert "E.MOV" in names("today", True)
    assert "F.AAE" not in names("all", True)


def test_items_without_date_only_in_all():
    no_date = MediaItem(id="x", name="X.JPG", size=1, date=None)
    assert filter_items([no_date], "today", now=NOW) == []
    assert filter_items([no_date], "all", now=NOW) == [no_date]


def test_history_roundtrip_and_hide_imported(tmp_path):
    path = str(tmp_path / "h" / "history.json")
    h = ImportHistory(path)
    h.use_device("PHONE1")
    a, b = item("A.HEIC"), item("B.HEIC")
    h.add(a, "/x/A.JPG")
    h.save()
    h2 = ImportHistory(path)
    h2.use_device("PHONE1")
    assert h2.contains(a) and not h2.contains(b)
    assert [i.name for i in filter_items([a, b], hide_imported=True, history=h2, now=NOW)] == ["B.HEIC"]
    h2.use_device("PHONE2")  # a different phone has its own history
    assert not h2.contains(a)


def test_history_survives_corrupt_file(tmp_path):
    p = tmp_path / "history.json"
    p.write_text("{not json")
    h = ImportHistory(str(p))
    h.use_device("x")
    assert h.count() == 0


def test_unique_path_never_overwrites(tmp_path):
    p = tmp_path / "IMG_1.JPG"
    assert unique_path(str(p)) == str(p)
    p.write_text("x")
    second = unique_path(str(p))
    assert second.endswith("IMG_1 (2).JPG")
    open(second, "w").close()
    assert unique_path(str(p)).endswith("IMG_1 (3).JPG")


def test_dest_dir_and_output_name(tmp_path):
    it = item("IMG_9.HEIC")
    assert dest_dir(it, "/r", True) == os.path.join("/r", "2026-11-04")
    assert dest_dir(it, "/r", False) == "/r"
    assert output_name(it, True) == "IMG_9.JPG"
    assert output_name(it, False) == "IMG_9.HEIC"


def test_convert_heic_to_jpg_keeps_exif_and_rotates(tmp_path):
    [src] = make_photos(str(tmp_path), [("IMG_1.HEIC", NOW)])
    dst = str(tmp_path / "IMG_1.JPG")
    convert_to_jpg(src, dst)
    with Image.open(dst) as im:
        assert im.format == "JPEG"
        assert im.size == (48, 64)  # portrait: pixels rotated upright
        assert im.getexif().get(0x0112) == 1
    assert not os.path.exists(dst + ".part")

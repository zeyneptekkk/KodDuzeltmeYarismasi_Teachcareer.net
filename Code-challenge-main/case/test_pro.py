# test_pro.py
import os
import json
import tempfile
import logging
import pytest
from datetime import datetime

from library_pro import (
    add_book_pro, search_books_adv,
    borrow_book_safe, return_book_with_delay_fee,
    list_overdue_stats, save_to_file_meta, load_from_file_safe,
    _in_days_str, setup_logging, titlecase_tr
)

# ------------ Yardımcı ------------
def make_seed_books():
    """
    Demo ile aynı tohum: Dune, Kürk Mantolu Madonna, 1984 (gecikmiş).
    """
    books = []
    add_book_pro(books, "Dune", "Frank Herbert", disallow_duplicates=True)
    add_book_pro(books, "Kürk Mantolu Madonna", "Sabahattin Ali", disallow_duplicates=True)
    add_book_pro(books, "1984", "George Orwell", disallow_duplicates=True)

    # 1984 → ödünçte ve 2 gün gecikmiş
    for b in books:
        if b["title"] == "1984":
            b["available"] = False
            b["borrower"] = "ayse"
            b["due_date"] = _in_days_str(-2)
            break
    return books


# ------------ Testler ------------
def test_add_book_pro_titlecase_and_duplicate():
    setup_logging(level=logging.INFO)
    books = make_seed_books()
    start = len(books)

    # Küçük harf gir → Title Case kaydedilmeli
    nb = add_book_pro(books, "bekle beni", "livaneli", disallow_duplicates=True)
    assert nb["title"] == "Bekle Beni"
    assert nb["author"] == "Livaneli"
    assert nb["id"] > 0 and nb["available"] is True
    assert len(books) == start + 1

    # Aynı başlık+yazar tekrar eklenemez (duplicate)
    with pytest.raises(ValueError):
        add_book_pro(books, "bekle beni", "livaneli", disallow_duplicates=True)

    # titlecase_tr yardımcı kontrol
    assert titlecase_tr("ayşe kulin") == "Ayşe Kulin"


def test_search_books_adv_turkish_normalize_and_modes():
    books = make_seed_books()
    add_book_pro(books, "Kırmızı Başlıklı Kız", "anonim", disallow_duplicates=True)

    # Türkçe normalize: "kurk" → "Kürk Mantolu Madonna" eşleşmeli
    res1 = search_books_adv(books, "kurk mantolu", mode="all", normalize=True)
    assert any(b["title"] == "Kürk Mantolu Madonna" for b in res1)

    # prefix modu: "du" → Dune
    res2 = search_books_adv(books, "du", mode="prefix", normalize=True)
    assert any(b["title"] == "Dune" for b in res2)

    # regex: başı "1984" ile başlayan
    res3 = search_books_adv(books, r"^1984\b", regex=True)
    assert any(b["title"] == "1984" for b in res3)

    # boş query → boş liste
    assert search_books_adv(books, "   ") == []


def test_borrow_return_fee_flow_and_validations():
    books = make_seed_books()

    # Müsait bir kitabı bul (Dune)
    dune = next(b for b in books if b["title"] == "Dune")

    # Ödünç ver
    ok1 = borrow_book_safe(books, dune["id"], "zey", days=1)
    assert ok1 is True and dune["available"] is False

    # Aynı kitabı ikinci kez veremez
    assert borrow_book_safe(books, dune["id"], "ali", days=7) is False

    # Gecikme simülasyonu: teslim tarihini 2 gün geriye al
    dune["due_date"] = _in_days_str(-2)
    ok2, delay, fee = return_book_with_delay_fee(books, dune["id"], fee_per_day=1.5)
    assert ok2 is True and delay >= 2 and fee == round(delay * 1.5, 2)
    assert dune["available"] is True and dune["borrower"] is None and dune["due_date"] is None

    # Doğrulama hataları
    with pytest.raises(TypeError):
        borrow_book_safe(books, "1", "x")           # book_id int değil
    with pytest.raises(ValueError):
        borrow_book_safe(books, dune["id"], "", 14) # boş kullanıcı
    with pytest.raises(ValueError):
        borrow_book_safe(books, dune["id"], "x", 0) # gün <= 0


def test_list_overdue_stats_count_and_total_fee():
    books = make_seed_books()
    today = datetime.now().strftime("%Y-%m-%d")
    lst, count, total = list_overdue_stats(books, today=today, fee_per_day=2.0)

    # 1984 gecikmiş olarak listede olmalı
    assert any(b["title"] == "1984" for b in lst)
    assert count >= 1
    # toplam ücret pozitif olmalı (en az 2 gün gecikme vardı)
    assert total >= 4.0


def test_save_to_file_meta_and_load_from_file_safe():
    books = make_seed_books()

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "books_meta.json")

        # meta'lı kaydet
        save_to_file_meta(books, path, with_meta=True)
        # ham dosyayı kontrol et (meta alanları)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        assert isinstance(raw, dict) and "books" in raw and "version" in raw
        assert raw["total_books"] == len(books)

        # güvenli yükle → liste dönmeli
        loaded = load_from_file_safe(path)
        assert isinstance(loaded, list) and len(loaded) == len(books)

        # Eksik dosya → []
        missing = os.path.join(tmp, "yok.json")
        assert load_from_file_safe(missing) == []

        # Bozuk JSON → []
        broken = os.path.join(tmp, "broken.json")
        with open(broken, "w", encoding="utf-8") as f:
            f.write("{ not-json ")
        assert load_from_file_safe(broken) == []

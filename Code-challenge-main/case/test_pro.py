# test_pro.py
import os
import io
import csv
import json
import tempfile
from datetime import datetime, timedelta

import pytest

from library_pro import (
    # çekirdek
    add_book_pro, search_books_adv, borrow_book_safe,
    return_book_with_delay_fee, renew_book, list_overdue_stats,
    # kalıcılık / CSV
    save_to_file_meta, load_from_file_safe, export_to_csv, import_from_csv,
    # yardımcılar / seed / log
    seed_books_initial, setup_logging,
    # hatalar
    DuplicateBookError, ValidationError, NotFoundError
)

# ---------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------

def make_seed_books():
    """Her test için taze seed oluşturur (in-memory)."""
    return seed_books_initial()

@pytest.fixture(autouse=True)
def _setup_logging():
    setup_logging(level=20)  # INFO
    yield

# ---------------------------------------------------------------------
# TESTLER
# ---------------------------------------------------------------------

def test_add_book_pro_titlecase_and_duplicate():
    books = make_seed_books()
    start_len = len(books)

    # TitleCase + Türkçe 'i' → 'İ' kontrolü
    nb = add_book_pro(books, "zeynep ve i̇nci", "zeynep inan", disallow_duplicates=True)
    assert nb["id"] > 0 and nb["available"] is True
    assert len(books) == start_len + 1
    # Başlık ilk harfler büyük, yazar içinde 'İ' (noktalı büyük I) beklenir
    assert nb["title"].startswith("Zeynep Ve")
    assert "İ" in nb["author"]  # 'inan' -> 'İnan'

    # Aynı başlık+yazar ile tekrar eklenmemeli
    with pytest.raises(DuplicateBookError):
        add_book_pro(books, "Zeynep ve İnci", "Zeynep İnAN", disallow_duplicates=True)


def test_search_books_adv_turkish_normalize_and_modes():
    books = make_seed_books()

    # aksan/harf büyük-küçük duyarsız: "dUnE" -> "Dune"
    res = search_books_adv(books, "dUnE", mode="any", normalize=True)
    assert any(b["title"] == "Dune" for b in res)

    # prefix modu: "kürk man" -> "Kürk Mantolu Madonna"
    res2 = search_books_adv(books, "kürk man", mode="prefix", normalize=True)
    assert any("Kürk Mantolu" in b["title"] for b in res2)

    # all modu: hem yazar hem başlık parçaları aynı anda
    res3 = search_books_adv(books, "george 1984", mode="all", normalize=True)
    assert any(b["title"] == "1984" for b in res3)


def test_borrow_return_fee_flow_and_validations():
    books = make_seed_books()

    # Geçersiz parametreler
    with pytest.raises(ValidationError):
        borrow_book_safe(books, "1", "ali", days=14)  # id int değil
    with pytest.raises(ValidationError):
        borrow_book_safe(books, 1, "   ", days=14)    # username boş
    with pytest.raises(ValidationError):
        borrow_book_safe(books, 1, "ali", days=0)     # days <= 0

    # Geçerli ödünç
    ok = borrow_book_safe(books, 1, "ali", days=7)
    assert ok is True
    b1 = next(b for b in books if b["id"] == 1)
    assert b1["available"] is False and b1["borrower"] == "ali"
    assert isinstance(b1["borrowed_at"], str) and isinstance(b1["due_date"], str)

    # Aynı kitabı tekrar veremez
    ok2 = borrow_book_safe(books, 1, "ayşe", days=7)
    assert ok2 is False

    # İade (gecikme & ücret hesaplanır). Seed’te ID=3 zaten gecikmiş.
    ok_ret, delay, fee = return_book_with_delay_fee(books, 3, fee_per_day=1.0)
    assert ok_ret is True
    assert delay >= 0
    assert fee >= 0.0


def test_list_overdue_stats_count_and_total_fee():
    books = make_seed_books()
    today = datetime.now().strftime("%Y-%m-%d")
    overdue, count, total_fee = list_overdue_stats(books, today=today, fee_per_day=1.0)

    # Seed’de "1984" gecikmiş durumda (ID=3)
    assert any(b["title"] == "1984" for b in overdue)
    assert count >= 1
    assert total_fee >= 0.0


def test_renew_book_rules_ok_and_blocked():
    books = make_seed_books()

    # Müsait bir kitap ödünç verilip due ileri alınır, sonra yenileme denenir
    assert borrow_book_safe(books, 1, "ali", days=7) is True
    b1 = next(b for b in books if b["id"] == 1)
    old_due = datetime.strptime(b1["due_date"], "%Y-%m-%d")

    # limit dahilinde yenileme başarılı
    assert renew_book(books, 1, extra_days=7, max_total_days=28) is True
    new_due = datetime.strptime(b1["due_date"], "%Y-%m-%d")
    assert (new_due - old_due).days == 7

    # gecikmiş kitap yenilenemez (seed’te 3 gecikmiş)
    assert renew_book(books, 3, extra_days=7, max_total_days=28) is False


def test_save_to_file_meta_and_load_from_file_safe(tmp_path):
    books = make_seed_books()
    p = tmp_path / "books_meta.json"

    # Kaydet & yükle
    save_to_file_meta(books, str(p), with_meta=True)
    loaded = load_from_file_safe(str(p))
    assert isinstance(loaded, list) and len(loaded) == len(books)

    # Eksik dosya → []
    missing = tmp_path / "yok.json"
    empty = load_from_file_safe(str(missing))
    assert empty == []

    # Bozuk JSON → []
    broken = tmp_path / "broken.json"
    with open(broken, "w", encoding="utf-8") as f:
        f.write("{ not-json }")
    empty2 = load_from_file_safe(str(broken))
    assert empty2 == []


def test_export_import_csv_roundtrip(tmp_path):
    books = make_seed_books()

    # CSV export
    csv_path = tmp_path / "export.csv"
    export_to_csv(books, str(csv_path))
    assert os.path.exists(csv_path)

    # İçeriği değiştirerek bir yeni satır ekle (duplicate olmayan)
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows.extend(r)
    # yeni kitap satırı (title/author alanları yeterli)
    rows.append({"id": "", "title": "Sefiller", "author": "Victor Hugo",
                 "available": "", "borrower": "", "borrowed_at": "", "due_date": ""})
    # tekrar yaz
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","title","author","available","borrower","borrowed_at","due_date"])
        w.writeheader()
        for row in rows:
            w.writerow(row)

    # Yeni boş listeye import
    new_books = []
    added = import_from_csv(new_books, str(csv_path))
    # en az 1 kitap (Sefiller) eklenmiş olmalı
    assert added >= 1
    assert any(b["title"] == "Sefiller" for b in new_books)


def test_search_filter_available_only_logic():
    """UI'ya bağlı kalmadan sadece available filtresini doğrula."""
    books = make_seed_books()

    # mevcut tüm kitaplar içinde 'available=True' olanları listele
    res = search_books_adv(books, " ", mode="any", normalize=True)  # boş gibi görünen ama eksiksiz arama olmasın diye
    # Boş/space query sonucu [] dönmesin diye küçük bir hile: spesifik bir harf ara
    res = search_books_adv(books, "e", mode="any", normalize=True)

    # available=True filtresi çalışsın
    only_av = search_books_adv(books, "e", mode="any", normalize=True, available=True)
    assert all(b.get("available") is True for b in only_av)
    # available=False filtresi çalışsın
    only_borrowed = search_books_adv(books, "e", mode="any", normalize=True, available=False)
    assert all(b.get("available") is False for b in only_borrowed)

# library_pro.py
"""
Geliştirilmiş Kütüphane (Pro Demo, sadeleşmiş)
- Türkçe/aksan duyarlı arama, duplicate kontrolü, gecikme ücreti, sağlam I/O.
- Demo/CLI açıldığında otomatik seed + envanter gösterimi.
- 🔒 Otomatik kalıcılık: ekleme/ödünç/iade/çıkışta books_pro.json'a kaydeder.
- 💄 Zengin görünüm: 'rich' varsa istatistik kartları + genişleyen/zebra tablo + vurgulu arama.
- ❌ ISBN alanı ve sıralama menüsü kaldırıldı (liste içten başlığa göre sıralanır).
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Tuple
import json
import logging
import sys
import unicodedata
import re
import os

# ========= Opsiyonel Zengin CLI (rich) =========
HAS_RICH = False
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.box import ROUNDED
    from rich.columns import Columns
    from rich.theme import Theme
    from rich.progress import Progress, SpinnerColumn, TextColumn

    THEME = Theme({
        "title": "bold cyan",
        "accent": "bold magenta",
        "muted": "grey66",
        "ok": "bold green",
        "warn": "bold yellow",
        "err": "bold red",
        "hdr": "bold white",
        "status_av": "bold green",
        "status_na": "bold red",
        "pill_av": "black on green",
        "pill_na": "white on red",
    })
    # genişlik ver → sütun başlıkları kırpılmasın
    console = Console(theme=THEME, width=120)
    HAS_RICH = True
except Exception:
    console = None
    HAS_RICH = False

# --- Fallback ANSI renkler (rich yoksa) ---
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RESET = "\033[0m"
try:
    import colorama
    colorama.just_fix_windows_console()
except Exception:
    pass

# =========================
# Genel Yardımcılar
# =========================
def _today_str() -> str:
    """Bugünün tarihini YYYY-MM-DD formatında döndürür."""
    return datetime.now().strftime("%Y-%m-%d")

def _in_days_str(days: int) -> str:
    """Bugünden itibaren 'days' gün sonrası (YYYY-MM-DD). Negatif gün geçmişi verir."""
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

def _now_iso() -> str:
    """ISO zaman damgası (YYYY-MM-DDTHH:MM:SS)."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def setup_logging(path: str = "library_log.txt", level: int = logging.INFO) -> None:
    """Basit log altyapısını kurar (dosya + konsol)."""
    logging.basicConfig(
        filename=path,
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(logging.StreamHandler(sys.stdout))


_TR_MAP = str.maketrans({"I": "ı", "İ": "i"})  # Türkçe I/İ düzeltmesi

def tr_lower(s: str) -> str:
    """Türkçe küçük harfe çevir (I→ı, İ→i) + normal lower()."""
    return s.translate(_TR_MAP).lower()

def strip_accents(s: str) -> str:
    """Aksan/diakritikleri temizler (genel dayanıklılık için)."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def norm_key(s: Optional[str]) -> str:
    """Arama/karşılaştırma için ortak anahtar: trim → aksan sil → tr_lower."""
    if not s:
        return ""
    return tr_lower(strip_accents(str(s).strip()))

def titlecase_tr(s: str) -> str:
    """
    Türkçe uyumlu basit Title Case:
    - her kelimenin ilk harfini büyüt, kalanını Türkçe lower yap
    - 'i'→'İ', 'ı'→'I' baş harfi özel
    """
    if not isinstance(s, str):
        return ""
    words = s.strip().split()
    out = []
    for w in words:
        if not w:
            continue
        first = w[0]
        rest = w[1:]
        if first == "i":
            head = "İ"
        elif first == "ı":
            head = "I"
        else:
            head = first.upper()
        out.append(head + tr_lower(rest))
    return " ".join(out)

# =========================
# Pro İşlevler (ISBN YOK)
# =========================
def add_book_pro(
    books: List[Dict],
    title: str,
    author: str,
    *,
    disallow_duplicates: bool = False,
) -> Dict:
    """
    Kitap ekler (pro, ISBN YOK).
    - Boş başlık/yazar ValueError.
    - disallow_duplicates=True ise aynı başlık+yazar eklenemez.
    - Kaydetmeden önce başlık ve yazarı Türkçe Title Case'e geçirir.
    """
    if not isinstance(title, str) or not isinstance(author, str):
        raise TypeError("title/author metin (str) olmalıdır.")
    t = title.strip()
    a = author.strip()
    if not t or not a:
        raise ValueError("title/author boş olamaz")

    # kullanıcı girdisini Title Case'e çevir
    t = titlecase_tr(t)
    a = titlecase_tr(a)

    if disallow_duplicates:
        t_norm, a_norm = norm_key(t), norm_key(a)
        for b in books:
            if norm_key(b.get("title")) == t_norm and norm_key(b.get("author")) == a_norm:
                raise ValueError("Bu kitap (başlık+yazar) zaten mevcut.")

    max_id = 0
    for b in books:
        try:
            bid = int(b.get("id"))
            if bid > max_id:
                max_id = bid
        except Exception:
            continue
    nid = max_id + 1 if books else 1

    new_book = {
        "id": nid,
        "title": t,
        "author": a,
        "available": True,
        "borrower": None,
        "due_date": None,
        "created_at": _now_iso(),  # 🆕 rozeti için
    }
    books.append(new_book)
    logging.info("Kitap eklendi: %s (%s) [id=%s]", t, a, nid)
    return new_book

def search_books_adv(
    books: List[Dict],
    query: str,
    *,
    mode: str = "any",      # "any" | "all" | "prefix"
    regex: bool = False,
    normalize: bool = True
) -> List[Dict]:
    """
    Gelişmiş arama:
    - any: kelimelerden biri geçsin / all: tümü geçsin / prefix: baştan eşleşsin
    - regex=True → düzenli ifade
    - normalize=True → Türkçe/aksan normalize ederek arama
    """
    if not query or not str(query).strip():
        return []
    q_raw = str(query).strip()

    def haystack_for(b: Dict) -> str:
        title = (b.get("title") or "")
        author = (b.get("author") or "")
        hay = f"{title} {author}".strip()
        return norm_key(hay) if normalize else hay.lower()

    if regex:
        pattern = re.compile(norm_key(q_raw) if normalize else q_raw, re.IGNORECASE)
        out = [b for b in books if pattern.search(haystack_for(b))]
        logging.info("Arama (regex) '%s' → %d sonuç", q_raw, len(out))
        return out

    tokens = (norm_key(q_raw) if normalize else q_raw.lower()).split()
    out = []
    for b in books:
        hay = haystack_for(b)
        if mode == "all":
            match = all(tok in hay for tok in tokens)
        elif mode == "prefix":
            match = any(
                hay.startswith(tok)
                or (b.get("title") or "").lower().startswith(tok)
                for tok in tokens
            )
        else:  # "any"
            match = any(tok in hay for tok in tokens)
        if match:
            out.append(b)

    logging.info("Arama '%s' (mode=%s, normalize=%s) → %d sonuç", q_raw, mode, normalize, len(out))
    return out

def borrow_book_safe(
    books: List[Dict],
    book_id: int,
    username: str,
    days: int = 14,
) -> bool:
    """
    Ödünç verme (gelişmiş doğrulamalar):
    - book_id int değilse TypeError, days<=0 ise ValueError, username boş olamaz
    """
    if not isinstance(book_id, int):
        raise TypeError("book_id bir tamsayı olmalıdır.")
    if not isinstance(days, int) or days <= 0:
        raise ValueError("days pozitif bir tamsayı olmalıdır.")
    if not isinstance(username, str) or not username.strip():
        raise ValueError("username boş olamaz")

    for b in books:
        if b.get("id") == book_id:
            if b.get("available"):
                b["available"] = False
                b["borrower"] = username.strip()
                b["due_date"] = _in_days_str(days)
                logging.info("Ödünç verildi: id=%s → %s (due=%s)", book_id, username, b["due_date"])
                return True
            logging.warning("Kitap zaten ödünçte: id=%s (borrower=%s)", book_id, b.get("borrower"))
            return False
    logging.error("Kitap bulunamadı: id=%s", book_id)
    return False

def return_book_with_delay(
    books: List[Dict],
    book_id: int
) -> Tuple[bool, int]:
    """İade eder ve gecikme gününü hesaplar. (ok, delay_days) döndürür."""
    for b in books:
        if b.get("id") == book_id:
            delay = 0
            if isinstance(b.get("due_date"), str) and b["due_date"]:
                try:
                    due_dt = datetime.strptime(b["due_date"], "%Y-%m-%d")
                    delay = max(0, (datetime.now() - due_dt).days)
                except ValueError:
                    delay = 0
            b.update({"available": True, "borrower": None, "due_date": None})
            if delay > 0:
                logging.warning("Gecikmeli iade: id=%s, delay=%s gün", book_id, delay)
            else:
                logging.info("Zamanında iade: id=%s", book_id)
            return True, delay
    logging.error("İade: kitap bulunamadı (id=%s)", book_id)
    return False, 0

def return_book_with_delay_fee(
    books: List[Dict],
    book_id: int,
    fee_per_day: float = 1.0
) -> Tuple[bool, int, float]:
    """İade eder ve (gecikme günü, ücret) hesaplar. (ok, delay_days, fee) döndürür."""
    ok, delay = return_book_with_delay(books, book_id)
    fee = round(max(0, delay) * float(fee_per_day), 2) if ok else 0.0
    if ok:
        logging.info("İade ücreti: id=%s, delay=%s gün, fee=%.2f", book_id, delay, fee)
    return ok, delay, fee

def list_overdue_stats(
    books: List[Dict],
    today: Optional[str] = None,
    *,
    fee_per_day: float = 1.0
) -> Tuple[List[Dict], int, float]:
    """Gecikenleri, sayısını ve tahmini toplam ücreti döndürür."""
    if today is None:
        today = _today_str()
    fmt = "%Y-%m-%d"
    try:
        today_dt = datetime.strptime(today, fmt)
    except ValueError:
        today_dt = datetime.now()

    out: List[Dict] = []
    total_fee = 0.0
    for book in books:
        if book.get("available") is True:
            continue
        due = book.get("due_date")
        if not isinstance(due, str) or not due:
            continue
        try:
            due_dt = datetime.strptime(due, fmt)
        except ValueError:
            continue
        if due_dt < today_dt:
            out.append(book)
            delay = (today_dt - due_dt).days
            total_fee += max(0, delay) * float(fee_per_day)

    total_fee = round(total_fee, 2)
    logging.info("Geciken: %d kitap, tahmini ücret=%.2f", len(out), total_fee)
    return out, len(out), total_fee

def save_to_file_meta(books: List[Dict], path: str, *, with_meta: bool = True) -> None:
    """
    JSON kaydı (isteğe bağlı metadata ile).
    with_meta=True ise:
        {"version":"pro-1","saved_at":"...","total_books":N,"books":[...]}
    """
    with open(path, "w", encoding="utf-8") as f:
        if with_meta:
            data = {
                "version": "pro-1",
                "saved_at": _now_iso(),
                "total_books": len(books),
                "books": books
            }
            json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            json.dump(books, f, ensure_ascii=False, indent=2)
    logging.info("Dosyaya kaydedildi: %s (meta=%s)", path, with_meta)

def load_from_file_safe(
    path: str,
    *,
    on_missing: Optional[Callable[[str], None]] = None
) -> List[Dict]:
    """
    JSON okuma (hata toleranslı).
    - Dosya yoksa: [] döndürür (uyarıyı stderr'e basar).
    - 'books' alanı varsa onu döndürür (meta'lı kayda uyum).
    - JSON bozuksa [] döndürür.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        msg = f"Uyarı: '{path}' bulunamadı, boş liste döndürülüyor."
        if on_missing:
            on_missing(msg)
        else:
            print(msg, file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print(f"Uyarı: '{path}' bozuk JSON, boş liste döndürülüyor.", file=sys.stderr)
        return []

    if isinstance(data, dict) and "books" in data and isinstance(data["books"], list):
        return data["books"]
    if isinstance(data, list):
        return data
    return []


def _format_status(b: Dict, *, compact: bool = True) -> str:
    """Durum metni: compact=True iken 'Müsait' / 'Müsait değil'."""
    if b.get("available"):
        return "Müsait"
    if compact:
        return "Müsait değil"
    borrower = b.get("borrower") or "bilinmiyor"
    due = b.get("due_date") or "-"
    return f"Müsait değil — {borrower} (teslim: {due})"

def _due_is_over(b: Dict, today: Optional[str] = None) -> bool:
    if b.get("available") is True:
        return False
    due = b.get("due_date")
    if not isinstance(due, str) or not due:
        return False
    fmt = "%Y-%m-%d"
    try:
        d = datetime.strptime(due, fmt)
    except ValueError:
        return False
    t = datetime.strptime(today, fmt) if today else datetime.now()
    return d < t

def _is_new(b: Dict) -> bool:
    """Son 24 saat içinde eklenmiş mi? (🆕 rozet için)"""
    ca = b.get("created_at")
    if not isinstance(ca, str):
        return False
    try:
        dt = datetime.strptime(ca[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return False
    return (datetime.now() - dt).total_seconds() <= 24*3600

def _counts(books: List[Dict]) -> Tuple[int, int, int, int]:
    total = len(books)
    available = sum(1 for b in books if b.get("available") is True)
    borrowed = total - available
    overdue = sum(1 for b in books if _due_is_over(b))
    return total, available, borrowed, overdue

def _search_highlight(text: str, tokens: List[str]) -> str:
    """rich yoksa sade highlight için ANSI renkle vurgula."""
    low = text.lower()
    out = text
    for tok in tokens:
        if not tok:
            continue
        idx = low.find(tok)
        if idx >= 0:
            part = out[idx:idx+len(tok)]
            out = out[:idx] + ANSI_YELLOW + part + ANSI_RESET + out[idx+len(tok):]
            low = out.lower().replace(ANSI_YELLOW, "").replace(ANSI_RESET, "")
    return out

def print_inventory(books: List[Dict]) -> None:
    """
    Tüm kitapları tablo halinde yazdırır.
    - rich varsa: özet kartları + GENİŞLEYEN zebra tablo + renkli/ikonlu rozetler
    - fallback: ANSI renkli sade çıktı
    """
    if not books:
        print("\n📚 Envanter boş.")
        return

    # Basit: başlığa göre sıralı gösterelim (menü yok)
    ordered = sorted(books, key=lambda b: (str(b.get("title") or "").lower(),))

    if HAS_RICH:
        total, available, borrowed, overdue = _counts(ordered)

        # Başlık
        header = Panel.fit(
            Text("📚 Pro Kütüphane — Envanter", style="title"),
            border_style="accent", box=ROUNDED
        )
        console.print(header)

        # İstatistik kartları
        cards = []
        cards.append(Panel(Text(f"Toplam\n[b]{total}[/b]", justify="center"), title="📦", border_style="muted", box=ROUNDED))
        cards.append(Panel(Text(f"Müsait\n[b]{available}[/b]", justify="center"), title="✅", border_style="status_av", box=ROUNDED))
        cards.append(Panel(Text(f"Ödünçte\n[b]{borrowed}[/b]", justify="center"), title="⛔", border_style="status_na", box=ROUNDED))
        cards.append(Panel(Text(f"Geciken\n[b]{overdue}[/b]", justify="center"), title="⏰", border_style="warn", box=ROUNDED))
        console.print(Columns(cards, expand=True))

        # GENİŞLEYEN Tablo (son sütun kırpılmayacak) — "Alan" sütunu geniş
        table = Table(
            box=ROUNDED,
            show_lines=False,
            header_style="hdr",
            row_styles=["", "dim"],
            expand=True,              # konsol genişliğini tam kullan
            padding=(0, 1)            # hücre içi yatay boşluk
        )
        table.add_column("ID", justify="right", width=4, no_wrap=True)
        table.add_column("Başlık", justify="left", min_width=28, overflow="fold")
        table.add_column("Yazar", justify="left", min_width=18, overflow="fold")
        table.add_column("Durum", justify="center", min_width=14, no_wrap=True)
        table.add_column("Alan", justify="left", min_width=16, overflow="fold")  # ← burada genişlettik
        table.add_column("Teslim", justify="left", min_width=14, no_wrap=True)

        for b in ordered:
            bid = str(b.get("id") or "")
            title = b.get("title") or ""
            author = b.get("author") or ""
            status_txt = _format_status(b, compact=True)
            status_pill = f"[pill_av] {status_txt} [/pill_av]" if b.get("available") else f"[pill_na] {status_txt} [/pill_na]"
            borrower = (b.get("borrower") or "-")
            due = (b.get("due_date") or "-")
            if not b.get("available") and _due_is_over(b):
                due = f"[warn]{due}[/warn]"
            new_badge = " 🆕" if _is_new(b) else ""
            table.add_row(bid, title + new_badge, author, status_pill, borrower, due)

        console.print(table)
        return

    # --- Fallback (sade metin, ANSI renkli) ---
    print("\n📚 Mevcut Kitaplar")
    print("─" * 100)
    for b in ordered:
        bid = b.get("id")
        title = b.get("title") or ""
        author = b.get("author") or ""
        status_plain = _format_status(b, compact=True)
        status_col = f"{ANSI_GREEN}{status_plain}{ANSI_RESET}" if b.get("available") else f"{ANSI_RED}{status_plain}{ANSI_RESET}"
        borrower = b.get("borrower") or "-"
        due = b.get("due_date") or "-"
        if not b.get("available") and _due_is_over(b):
            due = f"{ANSI_YELLOW}{due}{ANSI_RESET}"
        new_badge = " 🆕" if _is_new(b) else ""
        print(f"[{bid:>3}] {title}{new_badge} — {author} | {status_col} | Alan: {borrower} | Teslim: {due}")
    print("─" * 100)
    print(f"Toplam: {len(books)} kitap")

# =========================
# Seed (Başlangıç Verisi) — ISBN YOK
# =========================
def seed_books_initial() -> List[Dict]:
    """Demo için başlangıç kitapları. 1984 gecikmiş örnek olarak ayarlanır."""
    books: List[Dict] = []
    add_book_pro(books, "Dune", "Frank Herbert", disallow_duplicates=True)
    add_book_pro(books, "Kürk Mantolu Madonna", "Sabahattin Ali", disallow_duplicates=True)
    add_book_pro(books, "1984", "George Orwell", disallow_duplicates=True)
    for b in books:
        if b["title"] == "1984":
            b["available"] = False
            b["borrower"] = "Zey"
            b["due_date"] = _in_days_str(-2)  # 2 gün gecikmiş
            break
    return books

def load_or_seed_demo(
    path: str = "books_pro.json",
    *,
    force_seed: bool = False,
    save_if_seed: bool = True
) -> List[Dict]:
    """
    1) Dosya varsa ve doluysa → yükler.
    2) Yoksa (veya force_seed=True ise) → seed üretir, isterse diske kaydeder.
    """
    books: List[Dict] = []
    if not force_seed and os.path.exists(path):
        books = load_from_file_safe(path)
        if books:
            return books
    books = seed_books_initial()
    if save_if_seed:
        save_to_file_meta(books, path, with_meta=True)
    return books

# =========================
# 🔒 Otomatik Kaydetme Yardımcısı
# =========================
def _autosave(books: List[Dict], persist_path: Optional[str]) -> None:
    """Kalıcı dosya yolu verilmişse anında kaydeder (Rich varsa spinner ile)."""
    if not persist_path:
        return
    if HAS_RICH:
        with Progress(
            SpinnerColumn(style="accent"),
            TextColumn("[accent]Kaydediliyor...[/accent]"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task("save", total=None)
            save_to_file_meta(books, persist_path, with_meta=True)
        console.print("[ok]✓ Kaydedildi.[/ok]")
    else:
        save_to_file_meta(books, persist_path, with_meta=True)
        print("✓ Kaydedildi.")

# =========================
# Mini CLI (Jüri/Demo)
# =========================
def _print_banner():
    if HAS_RICH:
        header = Panel.fit(
            Text("📚 Pro Kütüphane — Zeynep Tek", style="title"),
            border_style="accent", box=ROUNDED
        )
        console.print(header)
    else:
        print("\n📚 Pro Kütüphane — Zeynep Tek")

def _print_menu():
    items = [
        ("t", "tüm liste"),
        ("a", "ara"),
        ("e", "ekle"),
        ("b", "ödünç ver"),
        ("o", "overdue"),
        ("i", "iade (ücretli)"),
        ("k", "kaydet"),
        ("y", "yükle"),
        ("u", "ücret"),
        ("q", "çıkış"),
    ]
    if HAS_RICH:
        txt = "  ".join(f"[accent]{k}[/accent]={v}" for k, v in items)
        console.print(Panel(txt, border_style="muted", box=ROUNDED))
    else:
        print(" | ".join(f"{k}={v}" for k, v in items))

def main(seed: bool = True, persist_path: Optional[str] = "books_pro.json"):
    """
    Küçük bir interaktif demo (pro).
    Komutlar: t/a/e/b/o/i/k/y/u/q
    """
    setup_logging(level=logging.INFO)

    # Veri
    if seed and persist_path:
        books: List[Dict] = load_or_seed_demo(persist_path, force_seed=False, save_if_seed=True)
    else:
        books: List[Dict] = []

    # Görsel açılış
    _print_banner()
    print_inventory(books)

    fee_per_day = 1.5
    while True:
        _print_menu()
        cmd = input("> ").strip().lower()

        if cmd == "t":
            print_inventory(books)

        elif cmd == "a":
            q = input("Arama: ").strip()
            mode = input("Mod (any/all/prefix): ").strip().lower() or "any"
            res = search_books_adv(books, q, mode=mode, normalize=True)
            tokens = (norm_key(q) or "").split()
            if HAS_RICH:
                table = Table(
                    box=ROUNDED, show_lines=False, header_style="hdr",
                    row_styles=["", "dim"], expand=True, padding=(0, 1)
                )
                table.add_column("ID", justify="right", width=4, no_wrap=True)
                table.add_column("Başlık", justify="left", min_width=28, overflow="fold")
                table.add_column("Yazar", justify="left", min_width=18, overflow="fold")
                table.add_column("Durum", justify="center", min_width=14, no_wrap=True)
                for b in res:
                    bid = str(b.get("id") or "")
                    title = b.get("title") or ""
                    author = b.get("author") or ""
                    t = Text(title); a = Text(author)
                    for tok in tokens:
                        if not tok: continue
                        t.highlight_regex(tok, style="warn", case_sensitive=False)
                        a.highlight_regex(tok, style="warn", case_sensitive=False)
                    status_txt = _format_status(b, compact=True)
                    status_pill = f"[pill_av] {status_txt} [/pill_av]" if b.get("available") else f"[pill_na] {status_txt} [/pill_na]"
                    table.add_row(bid, t, a, status_pill)
                console.print(table)
                console.print(Text(f"{len(res)} sonuç", style="muted"))
            else:
                print(f"{len(res)} sonuç:")
                for b in res:
                    title = b.get("title") or ""
                    author = b.get("author") or ""
                    print(" -", _search_highlight(title, tokens), "—", _search_highlight(author, tokens))

        elif cmd == "e":
            t = input("Başlık: ").strip()
            a = input("Yazar: ").strip()
            try:
                add_book_pro(books, t, a, disallow_duplicates=True)
                console.print("[ok]✓ Eklendi.[/ok]") if HAS_RICH else print("✓ Eklendi.")
                _autosave(books, persist_path)
                print_inventory(books)
            except Exception as e:
                msg = f"Hata: {e}"
                console.print(f"[err]{msg}[/err]") if HAS_RICH else print(msg)

        elif cmd == "b":
            try:
                bid = int(input("Ödünç verilecek ID: ").strip())
                user = input("Kullanıcı adı: ").strip()
                days = int(input("Gün sayısı (örn 14): ").strip() or "14")
            except ValueError:
                msg = "ID ve gün sayısı sayısal olmalı."
                console.print(f"[err]{msg}[/err]") if HAS_RICH else print(msg)
                continue
            ok = borrow_book_safe(books, bid, user, days=days)
            if ok:
                console.print("[ok]✓ Ödünç verildi.[/ok]") if HAS_RICH else print("✓ Ödünç verildi.")
                _autosave(books, persist_path)
                print_inventory(books)
            else:
                msg = "Verilemedi (kitap yok ya da zaten ödünçte)."
                console.print(f"[err]{msg}[/err]") if HAS_RICH else print(msg)

        elif cmd == "o":
            lst, n, fee = list_overdue_stats(books, today=_today_str(), fee_per_day=fee_per_day)
            titles = [b.get("title") for b in lst]
            txt = f"Geciken {n} kitap (tahmini ücret={fee:.2f}): {titles}"
            console.print(f"[warn]{txt}[/warn]") if HAS_RICH else print(txt)

        elif cmd == "i":
            try:
                bid = int(input("İade edilecek ID: ").strip())
            except ValueError:
                msg = "ID sayısal olmalı."
                console.print(f"[err]{msg}[/err]") if HAS_RICH else print(msg)
                continue
            ok, delay, fee = return_book_with_delay_fee(books, bid, fee_per_day=fee_per_day)
            if ok:
                console.print(f"[ok]✓ İade edildi.[/ok] Gecikme={delay} gün, Ücret={fee:.2f}") if HAS_RICH else print(f"✓ İade edildi. Gecikme={delay} gün, Ücret={fee:.2f}")
                _autosave(books, persist_path)
                print_inventory(books)
            else:
                msg = "Bulunamadı."
                console.print(f"[err]{msg}[/err]") if HAS_RICH else print(msg)

        elif cmd == "k":
            _autosave(books, persist_path)

        elif cmd == "y":
            books[:] = load_from_file_safe(persist_path or "books_pro.json", on_missing=print)
            console.print(f"[ok]✓ Yüklendi. Toplam: {len(books)}[/ok]") if HAS_RICH else print(f"✓ Yüklendi. Toplam: {len(books)}")
            print_inventory(books)

        elif cmd == "u":
            try:
                fee_per_day = float(input("Günlük ücret (örn 1.5): ").strip())
                console.print(f"[ok]✓ Güncellendi: {fee_per_day:.2f}[/ok]") if HAS_RICH else print(f"✓ Güncellendi: {fee_per_day:.2f}")
            except ValueError:
                msg = "Geçersiz değer."
                console.print(f"[err]{msg}[/err]") if HAS_RICH else print(msg)

        elif cmd == "q":
            _autosave(books, persist_path)
            if HAS_RICH:
                console.print("[muted]Görüşürüz! 👋[/muted]")
            else:
                print("Görüşürüz! 👋")
            break

        else:
            msg = "Komut: t/a/e/b/o/i/k/y/u/q"
            console.print(f"[muted]{msg}[/muted]") if HAS_RICH else print(msg)

if __name__ == "__main__":

    main(seed=True)

# library_pro.py
"""
Kütüphane (Pro, JSON) — JSON tabanlı CLI
- Türkçe/aksan duyarlı arama, Title Case normalizasyon
- Ödünç/iade, gecikme & ücret, 'yakında teslim' uyarısı
- Waitlist (bekleme sırası) + iade sonrası auto-assign
- Yenileme (renew) kurallı uzatma
- CSV import/export
- Atomic JSON kayıt + şema migration
- Zengin terminal (Rich varsa), yoksa ANSI
- ✅ 'Aldığı' (borrowed_at) ve 'Teslim' (due_date) ayrı sütunlar
- ✅ Kolon genişlikleri konsol genişliğine göre dinamik ayarlanır
- ✅ Sadece MÜSAİT kitapları gösteren özel görünüm (komut: s)
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Tuple, Literal
import json, logging, sys, unicodedata, re, os, csv, tempfile

# ====== (opsiyonel) Rich ======
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
    console = Console(theme=THEME, width=120)  # genişlik 120; Rich otomatik daraltır
    HAS_RICH = True
except Exception:
    console = None
    HAS_RICH = False

# ANSI fallback
ANSI_RED = "\033[31m"; ANSI_GREEN = "\033[32m"; ANSI_YELLOW = "\033[33m"; ANSI_RESET = "\033[0m"
try:
    import colorama; colorama.just_fix_windows_console()
except Exception:
    pass

# ====== Hatalar ======
class LibraryError(Exception): ...
class DuplicateBookError(LibraryError): ...
class ValidationError(LibraryError): ...
class NotFoundError(LibraryError): ...

# ====== Yardımcılar ======
def _today_str() -> str: return datetime.now().strftime("%Y-%m-%d")
def _in_days_str(days: int) -> str: return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
def _now_iso() -> str: return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def setup_logging(path: str = "library_log.txt", level: int = logging.INFO) -> None:
    logging.basicConfig(filename=path, level=level, format="%(asctime)s [%(levelname)s] %(message)s")
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(logging.StreamHandler(sys.stdout))

# ====== Türkçe & aksan normalize ======
_TR_MAP = str.maketrans({"I": "ı", "İ": "i"})
def tr_lower(s: str) -> str: return s.translate(_TR_MAP).lower()
def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))
def norm_key(s: Optional[str]) -> str:
    if not s: return ""
    return tr_lower(strip_accents(str(s).strip()))
def titlecase_tr(s: str) -> str:
    if not isinstance(s, str): return ""
    words = s.strip().split(); out = []
    for w in words:
        if not w: continue
        first, rest = w[0], w[1:]
        head = "İ" if first == "i" else ("I" if first == "ı" else first.upper())
        out.append(head + tr_lower(rest))
    return " ".join(out)

# ====== Atomic JSON + Migration ======
def _atomic_write_json(data, path: str, *, with_meta: bool = True):
    payload = {
        "version": "pro-3",
        "saved_at": _now_iso(),
        "total_books": len(data),
        "books": data,
    } if with_meta else data
    dir_name = os.path.dirname(os.path.abspath(path)) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)  # atomic replace

def _migrate_if_needed(books: List[Dict]) -> List[Dict]:
    changed = False
    for b in books:
        if "created_at" not in b:
            b["created_at"] = _now_iso(); changed = True
        if "available" not in b:
            b["available"] = True; changed = True
        if "waitlist" not in b:
            b["waitlist"] = []; changed = True
        if "borrowed_at" not in b:
            b["borrowed_at"] = None; changed = True
    if changed:
        logging.info("Kayıtlar yeni şemaya yükseltildi.")
    return books

# ====== Kalıcılık ======
def save_to_file_meta(books: List[Dict], path: str, *, with_meta: bool = True) -> None:
    _atomic_write_json(books, path, with_meta=with_meta)
    logging.info("Dosyaya kaydedildi: %s (meta=%s)", path, with_meta)

def load_from_file_safe(path: str, *, on_missing: Optional[Callable[[str], None]] = None) -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        msg = f"Uyarı: '{path}' bulunamadı, boş liste döndürülüyor."
        if on_missing: on_missing(msg)
        else: print(msg, file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print(f"Uyarı: '{path}' bozuk JSON, boş liste döndürülüyor.", file=sys.stderr)
        return []
    if isinstance(data, dict) and "books" in data and isinstance(data["books"], list):
        return _migrate_if_needed(list(data["books"]))
    if isinstance(data, list):
        return _migrate_if_needed(list(data))
    return []

# ====== Çekirdek işlevler ======
def add_book_pro(books: List[Dict], title: str, author: str, *, disallow_duplicates: bool = False) -> Dict:
    if not isinstance(title, str) or not isinstance(author, str):
        raise ValidationError("title/author metin olmalı")
    t, a = title.strip(), author.strip()
    if not t or not a:
        raise ValidationError("title/author boş olamaz")
    t, a = titlecase_tr(t), titlecase_tr(a)
    if disallow_duplicates:
        t_norm, a_norm = norm_key(t), norm_key(a)
        for b in books:
            if norm_key(b.get("title")) == t_norm and norm_key(b.get("author")) == a_norm:
                raise DuplicateBookError("Bu kitap (başlık+yazar) zaten mevcut.")
    max_id = 0
    for b in books:
        try:
            bid = int(b.get("id")); max_id = max(max_id, bid)
        except Exception:
            continue
    nid = max_id + 1 if books else 1
    new_book = {
        "id": nid, "title": t, "author": a,
        "available": True, "borrower": None, "due_date": None,
        "borrowed_at": None,
        "created_at": _now_iso(),
        "waitlist": [],
    }
    books.append(new_book)
    logging.info("Kitap eklendi: %s (%s) [id=%s]", t, a, nid)
    return new_book

def search_books_adv(
    books: List[Dict], query: str, *,
    mode: Literal["any","all","prefix"]="any",
    regex: bool=False, normalize: bool=True,
    available: Optional[bool]=None, borrower: Optional[str]=None,
    due_before: Optional[str]=None,
    order_by: Literal["title","author","due","created"]="title"
) -> List[Dict]:
    if not query or not str(query).strip(): return []
    q_raw = str(query).strip()
    def hay(b: Dict) -> str:
        s = f"{b.get('title','')} {b.get('author','')}".strip()
        return norm_key(s) if normalize else s.lower()
    if regex:
        pat = re.compile(norm_key(q_raw) if normalize else q_raw, re.IGNORECASE)
        res = [b for b in books if pat.search(hay(b))]
    else:
        toks = (norm_key(q_raw) if normalize else q_raw.lower()).split()
        res = []
        for b in books:
            H = hay(b)
            if mode == "all":
                ok = all(tok in H for tok in toks)
            elif mode == "prefix":
                ok = any(H.startswith(tok) or (b.get("title") or "").lower().startswith(tok) for tok in toks)
            else:
                ok = any(tok in H for tok in toks)
            if ok: res.append(b)
    if available is not None:
        res = [b for b in res if bool(b.get("available")) is available]
    if borrower:
        key = norm_key(borrower)
        res = [b for b in res if norm_key(b.get("borrower")) == key]
    if due_before:
        try:
            lim = datetime.strptime(due_before, "%Y-%m-%d")
            res = [b for b in res if isinstance(b.get("due_date"), str) and b["due_date"]
                   and datetime.strptime(b["due_date"], "%Y-%m-%d") < lim]
        except ValueError:
            pass
    if order_by == "author":
        res.sort(key=lambda x: (str(x.get("author") or "").lower(), str(x.get("title") or "")))
    elif order_by == "due":
        res.sort(key=lambda x: (x.get("due_date") or "9999-12-31"))
    elif order_by == "created":
        res.sort(key=lambda x: (x.get("created_at") or "0000-01-01"), reverse=True)
    else:
        res.sort(key=lambda x: (str(x.get("title") or "").lower(),))
    logging.info("Arama '%s' (mode=%s) → %d sonuç", q_raw, mode, len(res))
    return res

def borrow_book_safe(books: List[Dict], book_id: int, username: str, days: int = 14) -> bool:
    if not isinstance(book_id, int): raise ValidationError("book_id int olmalı")
    if not isinstance(days, int) or days <= 0: raise ValidationError("days>0 olmalı")
    if not isinstance(username, str) or not username.strip(): raise ValidationError("username boş olamaz")
    for b in books:
        if b.get("id") == book_id:
            if b.get("available"):
                b["available"] = False
                b["borrower"] = username.strip()
                b["borrowed_at"] = _today_str()           # Aldığı
                b["due_date"]   = _in_days_str(days)      # Teslim
                logging.info("Ödünç: id=%s → %s (borrowed_at=%s, due=%s)", book_id, username, b["borrowed_at"], b["due_date"])
                return True
            logging.warning("Meşgul: id=%s (borrower=%s)", book_id, b.get("borrower"))
            return False
    raise NotFoundError(f"Kitap yok: id={book_id}")

def join_waitlist(books: List[Dict], book_id: int, username: str) -> bool:
    for b in books:
        if b.get("id") == book_id:
            if b.get("available"): return False
            wl = b.setdefault("waitlist", [])
            key = norm_key(username)
            if any(norm_key(x) == key for x in wl): return False
            wl.append(username.strip()); logging.info("Waitlist: id=%s ← %s", book_id, username)
            return True
    raise NotFoundError(f"Kitap yok: id={book_id}")

def _assign_next_waiter(b: Dict) -> Optional[str]:
    wl = b.get("waitlist") or []
    if not wl: return None
    user = wl.pop(0)
    b["available"] = False
    b["borrower"] = user
    b["borrowed_at"] = _today_str()
    b["due_date"] = _in_days_str(14)
    logging.info("Auto-assign: %s → id=%s (borrowed_at=%s, due=%s)", user, b.get("id"), b["borrowed_at"], b["due_date"])
    return user

def return_book_with_delay(books: List[Dict], book_id: int) -> Tuple[bool, int]:
    for b in books:
        if b.get("id") == book_id:
            delay = 0
            if isinstance(b.get("due_date"), str) and b["due_date"]:
                try:
                    due_dt = datetime.strptime(b["due_date"], "%Y-%m-%d")
                    delay = max(0, (datetime.now() - due_dt).days)
                except ValueError:
                    delay = 0
            b.update({"available": True, "borrower": None, "due_date": None, "borrowed_at": None})
            if delay > 0: logging.warning("Gecikmeli iade: id=%s, delay=%s gün", book_id, delay)
            else: logging.info("Zamanında iade: id=%s", book_id)
            _assign_next_waiter(b)
            return True, delay
    raise NotFoundError(f"Kitap yok: id={book_id}")

def calc_fee(delay_days: int, *, base: float=1.0, weekend_free: bool=True) -> float:
    if delay_days <= 0: return 0.0
    if not weekend_free: return round(delay_days * base, 2)
    fee_days = 0; today = datetime.now().date()
    for i in range(delay_days):
        d = (today - timedelta(days=i+1))
        if d.weekday() < 5: fee_days += 1
    return round(fee_days * base, 2)

def return_book_with_delay_fee(books: List[Dict], book_id: int, fee_per_day: float = 1.0) -> Tuple[bool, int, float]:
    ok, delay = return_book_with_delay(books, book_id)
    fee = calc_fee(delay, base=float(fee_per_day), weekend_free=True) if ok else 0.0
    if ok: logging.info("İade ücreti: id=%s, delay=%s, fee=%.2f", book_id, delay, fee)
    return ok, delay, fee

def renew_book(books: List[Dict], book_id: int, extra_days: int = 7, *, max_total_days: int = 28) -> bool:
    if extra_days <= 0: raise ValidationError("extra_days>0 olmalı")
    for b in books:
        if b.get("id") == book_id:
            if b.get("available"): return False
            if not b.get("due_date"): return False
            due = datetime.strptime(b["due_date"], "%Y-%m-%d")
            if due < datetime.now():  # gecikmişken yenileme yok
                return False
            base_total = 14 + extra_days
            if base_total > max_total_days:
                return False
            b["due_date"] = (due + timedelta(days=extra_days)).strftime("%Y-%m-%d")
            logging.info("Yenileme: id=%s, +%s gün → %s", book_id, extra_days, b["due_date"])
            return True
    raise NotFoundError(f"Kitap yok: id={book_id}")

def list_overdue_stats(books: List[Dict], today: Optional[str] = None, *, fee_per_day: float = 1.0) -> Tuple[List[Dict], int, float]:
    if today is None: today = _today_str()
    fmt = "%Y-%m-%d"
    try: today_dt = datetime.strptime(today, fmt)
    except ValueError: today_dt = datetime.now()
    out: List[Dict] = []; total_fee = 0.0
    for book in books:
        if book.get("available") is True: continue
        due = book.get("due_date")
        if not isinstance(due, str) or not due: continue
        try: due_dt = datetime.strptime(due, fmt)
        except ValueError: continue
        if due_dt < today_dt:
            out.append(book)
            delay = (today_dt - due_dt).days
            total_fee += calc_fee(delay, base=float(fee_per_day), weekend_free=True)
    total_fee = round(total_fee, 2)
    logging.info("Overdue: %d kitap, toplam ücret=%.2f", len(out), total_fee)
    return out, len(out), total_fee

# ====== CSV import/export ======
def export_to_csv(books: List[Dict], path: str) -> None:
    fields = ["id", "title", "author", "available", "borrower", "borrowed_at", "due_date"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for b in books:
            w.writerow({k: b.get(k) for k in fields})
    logging.info("CSV export: %s", path)

def import_from_csv(books: List[Dict], path: str, *, title_col="title", author_col="author") -> int:
    if not os.path.exists(path): raise FileNotFoundError(path)
    added = 0
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            t = row.get(title_col) or ""
            a = row.get(author_col) or ""
            t, a = t.strip(), a.strip()
            if not t or not a: continue
            try:
                add_book_pro(books, t, a, disallow_duplicates=True)
                added += 1
            except DuplicateBookError:
                continue
    logging.info("CSV import: %s (eklenen=%s)", path, added)
    return added

# ====== Görsel yardımcılar ======
def _format_status(b: Dict, *, compact: bool = True) -> str:
    if b.get("available"): return "Müsait"
    if compact: return "Müsait değil"
    borrower = b.get("borrower") or "bilinmiyor"; due = b.get("due_date") or "-"
    return f"Müsait değil — {borrower} (teslim: {due})"

def _due_is_over(b: Dict, today: Optional[str] = None) -> bool:
    if b.get("available") is True: return False
    d = b.get("due_date"); fmt = "%Y-%m-%d"
    if not isinstance(d, str) or not d: return False
    try: dd = datetime.strptime(d, fmt)
    except ValueError: return False
    T = datetime.strptime(today, fmt) if today else datetime.now()
    return dd < T

def _due_is_soon(b: Dict, days: int = 2) -> bool:
    if b.get("available") is True: return False
    d = b.get("due_date")
    if not isinstance(d, str) or not d: return False
    try:
        dd = datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return False
    return 0 <= (dd - datetime.now()).days <= days

def _is_new(b: Dict) -> bool:
    ca = b.get("created_at")
    if not isinstance(ca, str): return False
    try: dt = datetime.strptime(ca[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError: return False
    return (datetime.now() - dt).total_seconds() <= 24*3600

def _counts(books: List[Dict]) -> Tuple[int, int, int, int]:
    total = len(books); available = sum(1 for b in books if b.get("available") is True)
    borrowed = total - available; overdue = sum(1 for b in books if _due_is_over(b))
    return total, available, borrowed, overdue

def _compute_widths():
    """Konsol genişliğine göre dinamik kolon genişlikleri."""
    if not HAS_RICH or not console:  # fallback varsayılanlar
        return dict(W_ID=4, W_DURUM=14, W_ALAN=14, W_ALDIGI=12, W_TESLIM=12, W_BEK=10, W_TITLE=32, W_AUTHOR=20)
    C = max(80, console.width)  # güvenli alt sınır
    W_ID, W_DURUM, W_ALAN, W_ALDIGI, W_TESLIM, W_BEK = 4, 14, 14, 12, 12, 10
    fixed = W_ID + W_DURUM + W_ALAN + W_ALDIGI + W_TESLIM + W_BEK
    overhead = 10  # kenarlık/padding tahmini
    rem = max(24, C - fixed - overhead)
    W_TITLE = max(18, int(rem * 0.6))
    W_AUTHOR = max(12, rem - W_TITLE)
    return dict(W_ID=W_ID, W_DURUM=W_DURUM, W_ALAN=W_ALAN, W_ALDIGI=W_ALDIGI,
                W_TESLIM=W_TESLIM, W_BEK=W_BEK, W_TITLE=W_TITLE, W_AUTHOR=W_AUTHOR)

def print_inventory(books: List[Dict]) -> None:
    if not books:
        print("\n📚 Envanter boş."); return
    ordered = sorted(books, key=lambda b: (str(b.get("title") or "").lower(),))
    if HAS_RICH:
        w = _compute_widths()
        total, available, borrowed, overdue = _counts(ordered)
        console.print(Panel.fit(Text("📚 Pro Kütüphane — Envanter", style="title"), border_style="accent", box=ROUNDED))
        cards = [
            Panel(Text.from_markup(f"Toplam\n[b]{total}[/b]", justify="center"), title="📦", border_style="muted", box=ROUNDED),
            Panel(Text.from_markup(f"Müsait\n[b]{available}[/b]", justify="center"), title="✅", border_style="status_av", box=ROUNDED),
            Panel(Text.from_markup(f"Ödünçte\n[b]{borrowed}[/b]", justify="center"), title="⛔", border_style="status_na", box=ROUNDED),
            Panel(Text.from_markup(f"Geciken\n[b]{overdue}[/b]", justify="center"), title="⏰", border_style="warn", box=ROUNDED),
        ]
        console.print(Columns(cards, expand=True))
        table = Table(box=ROUNDED, show_lines=False, header_style="hdr", row_styles=["", "dim"], expand=True, padding=(0,1))
        table.add_column("ID", justify="right", width=w["W_ID"], no_wrap=True)
        table.add_column("Başlık", justify="left", min_width=w["W_TITLE"], max_width=w["W_TITLE"], overflow="fold")
        table.add_column("Yazar", justify="left", min_width=w["W_AUTHOR"], max_width=w["W_AUTHOR"], overflow="fold")
        table.add_column("Durum", justify="center", width=w["W_DURUM"], no_wrap=True)
        table.add_column("Alan", justify="left", width=w["W_ALAN"], no_wrap=True)
        table.add_column("Aldığı", justify="left", width=w["W_ALDIGI"], no_wrap=True)
        table.add_column("Teslim", justify="left", width=w["W_TESLIM"], no_wrap=True)
        table.add_column("Bekleyen", justify="right", width=w["W_BEK"], no_wrap=True)
        for b in ordered:
            bid = str(b.get("id") or "")
            title = b.get("title") or ""
            author = b.get("author") or ""
            status_txt = _format_status(b, compact=True)
            status_pill = f"[pill_av] {status_txt} [/pill_av]" if b.get("available") else f"[pill_na] {status_txt} [/pill_na]"
            borrower = (b.get("borrower") or "-")
            borrowed_at = (b.get("borrowed_at") or "-")
            due = (b.get("due_date") or "-")
            if not b.get("available"):
                if _due_is_over(b): due = f"[warn]{due}[/warn]"
                elif _due_is_soon(b): due = f"[warn]{due}[/warn]"
            new_badge = " 🆕" if _is_new(b) else ""
            wl_count = len(b.get("waitlist") or [])
            table.add_row(bid, title + new_badge, author, status_pill, borrower, borrowed_at, due, str(wl_count))
        console.print(table); return
    # Fallback (Rich yoksa)
    print("\n📚 Mevcut Kitaplar"); print("─"*120)
    for b in ordered:
        bid = b.get("id"); title = b.get("title") or ""; author = b.get("author") or ""
        status_plain = _format_status(b, compact=True)
        status_col = f"{ANSI_GREEN}{status_plain}{ANSI_RESET}" if b.get("available") else f"{ANSI_RED}{status_plain}{ANSI_RESET}"
        borrower = b.get("borrower") or "-"
        borrowed_at = b.get("borrowed_at") or "-"
        due = b.get("due_date") or "-"
        if not b.get("available") and (_due_is_over(b) or _due_is_soon(b)):
            due = f"{ANSI_YELLOW}{due}{ANSI_RESET}"
        new_badge = " 🆕" if _is_new(b) else ""
        wl_count = len(b.get("waitlist") or [])
        print(f"[{bid:>3}] {title}{new_badge} — {author} | {status_col} | Alan:{borrower} | Aldığı:{borrowed_at} | Teslim:{due} | Bekleyen:{wl_count}")
    print("─"*120); print(f"Toplam: {len(books)} kitap")

def print_available_only(books: List[Dict]) -> None:
    """Sadece şu anda MÜSAİT olan kitapları kompakt listeler."""
    avail = [b for b in books if b.get("available") is True]
    if not avail:
        print("\n✅ Şu anda müsait kitap yok."); return
    avail.sort(key=lambda b: (str(b.get("title") or "").lower(),))
    if HAS_RICH:
        w = _compute_widths()
        # Bu görünümde yalnızca ID, Başlık, Yazar ve Durum kolonlarını gösteriyoruz.
        table = Table(box=ROUNDED, show_lines=False, header_style="hdr", row_styles=["", "dim"], expand=True, padding=(0,1))
        # Başlık/Yazar genişliği, ana tablodaki oranı koruyacak şekilde dağıtılır.
        W_TITLE = w["W_TITLE"]; W_AUTHOR = w["W_AUTHOR"]; W_ID = w["W_ID"]; W_DURUM = w["W_DURUM"]
        table.add_column("ID", justify="right", width=W_ID, no_wrap=True)
        table.add_column("Başlık", justify="left", min_width=W_TITLE, max_width=W_TITLE, overflow="fold")
        table.add_column("Yazar", justify="left", min_width=W_AUTHOR, max_width=W_AUTHOR, overflow="fold")
        table.add_column("Durum", justify="center", width=W_DURUM, no_wrap=True)
        for b in avail:
            table.add_row(str(b.get("id") or ""), b.get("title") or "", b.get("author") or "", "[pill_av] Müsait [/pill_av]")
        console.print(Panel.fit(Text("✅ Müsait Kitaplar", style="title"), border_style="status_av", box=ROUNDED))
        console.print(table)
    else:
        print("\n✅ Müsait Kitaplar"); print("─"*100)
        for b in avail:
            print(f"[{b.get('id'):>3}] {b.get('title')} — {b.get('author')} | Müsait")
        print("─"*100); print(f"Toplam: {len(avail)} kitap")

# ====== Seed + yükleme ======
def seed_books_initial() -> List[Dict]:
    books: List[Dict] = []
    add_book_pro(books, "Dune", "Frank Herbert", disallow_duplicates=True)
    add_book_pro(books, "Kürk Mantolu Madonna", "Sabahattin Ali", disallow_duplicates=True)
    add_book_pro(books, "1984", "George Orwell", disallow_duplicates=True)
    # 1984 ödünçte + gecikmiş örnek: due= -2 gün, borrowed_at ~14 gün önce
    for b in books:
        if b["title"] == "1984":
            due = datetime.strptime(_in_days_str(-2), "%Y-%m-%d")
            borrowed_at = (due - timedelta(days=14)).strftime("%Y-%m-%d")
            b.update({
                "available": False,
                "borrower": "Zey",
                "borrowed_at": borrowed_at,
                "due_date": due.strftime("%Y-%m-%d"),
                "waitlist": ["Ayşe"],
            })
            break
    return books

def load_or_seed_demo(path: str = "books_pro.json", *, force_seed: bool = False, save_if_seed: bool = True) -> List[Dict]:
    books: List[Dict] = []
    if not force_seed and os.path.exists(path):
        books = load_from_file_safe(path)
        if books: return books
    books = seed_books_initial()
    if save_if_seed: save_to_file_meta(books, path, with_meta=True)
    return books

def _autosave(books: List[Dict], persist_path: Optional[str]) -> None:
    if not persist_path: return
    if HAS_RICH:
        with Progress(SpinnerColumn(style="accent"), TextColumn("[accent]Kaydediliyor...[/accent]"),
                      transient=True, console=console) as progress:
            progress.add_task("save", total=None)
            save_to_file_meta(books, persist_path, with_meta=True)
        console.print("[ok]✓ Kaydedildi.[/ok]")
    else:
        save_to_file_meta(books, persist_path, with_meta=True)
        print("✓ Kaydedildi.")

# ====== CLI ======
def _print_banner():
    if HAS_RICH:
        console.print(Panel.fit(Text("📚 Pro Kütüphane — JSON", style="title"), border_style="accent", box=ROUNDED))
    else:
        print("\n📚 Pro Kütüphane — JSON")

def _print_menu():
    items = [
        ("t", "tüm liste"), ("s", "sadece müsaitler"),  # ✅ yeni
        ("a", "ara"), ("e", "ekle"),
        ("b", "ödünç ver"), ("w", "waitlist'e ekle"),
        ("r", "yenile (renew)"), ("o", "overdue"),
        ("i", "iade (ücretli)"),
        ("x", "CSV dışa aktar"), ("m", "CSV içe aktar"),
        ("k", "kaydet"), ("y", "yükle"), ("u", "günlük ücret"), ("q", "çıkış"),
    ]
    if HAS_RICH:
        txt = "  ".join(f"[accent]{k}[/accent]={v}" for k, v in items)
        console.print(Panel(txt, border_style="muted", box=ROUNDED))
    else:
        print(" | ".join(f"{k}={v}" for k, v in items))

def main(seed: bool = True, persist_path: Optional[str] = "books_pro.json"):
    setup_logging(level=logging.INFO)
    books: List[Dict] = load_or_seed_demo(persist_path, force_seed=False, save_if_seed=True) if seed and persist_path else []
    _print_banner(); print_inventory(books)

    fee_per_day = 1.5
    while True:
        _print_menu()
        cmd = input("> ").strip().lower()
        try:
            if cmd == "t":
                print_inventory(books)

            elif cmd == "s":  # ✅ sadece müsaitler
                print_available_only(books)

            elif cmd == "a":
                q = input("Arama: ").strip()
                mode = (input("Mod (any/all/prefix): ").strip().lower() or "any")
                if mode not in {"any", "all", "prefix"}: mode = "any"
                res = search_books_adv(books, q, mode=mode, normalize=True)
                if HAS_RICH:
                    table = Table(box=ROUNDED, show_lines=False, header_style="hdr",
                                  row_styles=["","dim"], expand=True, padding=(0,1))
                    widths = _compute_widths()
                    table.add_column("ID", justify="right", width=widths["W_ID"], no_wrap=True)
                    table.add_column("Başlık", justify="left", min_width=widths["W_TITLE"], max_width=widths["W_TITLE"], overflow="fold")
                    table.add_column("Yazar", justify="left", min_width=widths["W_AUTHOR"], max_width=widths["W_AUTHOR"], overflow="fold")
                    table.add_column("Durum", justify="center", width=widths["W_DURUM"], no_wrap=True)
                    for b in res:
                        bid = str(b.get("id") or "")
                        t = Text(b.get("title") or "")
                        a_txt = Text(b.get("author") or "")
                        toks = (norm_key(q) or "").split()
                        if toks:
                            t.highlight_words(toks, style="warn", case_sensitive=False)
                            a_txt.highlight_words(toks, style="warn", case_sensitive=False)
                        status_txt = _format_status(b, compact=True)
                        pill = f"[pill_av] {status_txt} [/pill_av]" if b.get("available") else f"[pill_na] {status_txt} [/pill_na]"
                        table.add_row(bid, t, a_txt, pill)
                    console.print(table)
                    console.print(Text(f"{len(res)} sonuç", style="muted"))
                else:
                    print(f"{len(res)} sonuç:")
                    toks = (norm_key(q) or "").split()
                    def hi(text: str) -> str:
                        low = text.lower(); out = text
                        for tok in toks:
                            i = low.find(tok)
                            if i >= 0:
                                out = out[:i]+ANSI_YELLOW+out[i:i+len(tok)]+ANSI_RESET+out[i+len(tok):]
                                low = out.lower().replace(ANSI_YELLOW,"").replace(ANSI_RESET,"")
                        return out
                    for b in res:
                        print(" -", hi(b.get("title") or ""), "—", hi(b.get("author") or ""))

            elif cmd == "e":
                t = input("Başlık: ").strip(); a = input("Yazar: ").strip()
                add_book_pro(books, t, a, disallow_duplicates=True)
                if HAS_RICH: console.print("[ok]✓ Eklendi.[/ok]")
                else: print("✓ Eklendi.")
                _autosave(books, persist_path); print_inventory(books)

            elif cmd == "b":
                bid = int(input("Ödünç verilecek ID: ").strip()); user = input("Kullanıcı adı: ").strip()
                days = int((input("Gün sayısı (örn 14): ").strip() or "14"))
                ok = borrow_book_safe(books, bid, user, days=days)
                if ok:
                    if HAS_RICH: console.print("[ok]✓ Ödünç verildi.[/ok]")
                    else: print("✓ Ödünç verildi.")
                    _autosave(books, persist_path); print_inventory(books)
                else:
                    msg = "Verilemedi (kitap yok ya da zaten ödünçte). Waitlist'e eklemeyi deneyin (w)."
                    if HAS_RICH: console.print(f"[err]{msg}[/err]")
                    else: print(msg)

            elif cmd == "w":
                bid = int(input("Waitlist ID: ").strip()); user = input("Kullanıcı adı: ").strip()
                ok = join_waitlist(books, bid, user)
                if ok:
                    if HAS_RICH: console.print("[ok]✓ Waitlist'e eklendi.[/ok]")
                    else: print("✓ Waitlist'e eklendi.")
                else:
                    if HAS_RICH: console.print("[err]Eklenemedi.[/err]")
                    else: print("Eklenemedi.")
                _autosave(books, persist_path); print_inventory(books)

            elif cmd == "r":
                bid = int(input("Yenilenecek ID: ").strip()); extra = int(input("Ek gün (örn 7): ").strip() or "7")
                ok = renew_book(books, bid, extra_days=extra, max_total_days=28)
                if ok:
                    if HAS_RICH: console.print("[ok]✓ Yenilendi.[/ok]")
                    else: print("✓ Yenilendi.")
                else:
                    if HAS_RICH: console.print("[err]Yenilenemedi.[/err]")
                    else: print("Yenilenemedi.")
                _autosave(books, persist_path); print_inventory(books)

            elif cmd == "o":
                lst, n, fee = list_overdue_stats(books, today=_today_str(), fee_per_day=fee_per_day)
                msg = f"Geciken {n} kitap (tahmini ücret={fee:.2f}): {[b.get('title') for b in lst]}"
                if HAS_RICH: console.print(f"[warn]{msg}[/warn]")
                else: print(msg)

            elif cmd == "i":
                bid = int(input("İade edilecek ID: ").strip())
                ok, delay, fee = return_book_with_delay_fee(books, bid, fee_per_day=fee_per_day)
                if ok:
                    if HAS_RICH: console.print(f"[ok]✓ İade.[/ok] Gecikme={delay} gün, Ücret={fee:.2f}")
                    else: print(f"✓ İade. Gecikme={delay} gün, Ücret={fee:.2f}")
                    _autosave(books, persist_path); print_inventory(books)
                else:
                    if HAS_RICH: console.print("[err]Bulunamadı.[/err]")
                    else: print("Bulunamadı.")

            elif cmd == "x":
                path = input("CSV yol (örn export.csv): ").strip() or "export.csv"
                export_to_csv(books, path)
                if HAS_RICH: console.print("[ok]✓ Dışa aktarıldı.[/ok]")
                else: print("✓ Dışa aktarıldı.")

            elif cmd == "m":
                path = input("CSV yol (örn import.csv): ").strip() or "import.csv"
                n = import_from_csv(books, path)
                if HAS_RICH: console.print(f"[ok]✓ İçe aktarıldı (eklenen={n}).[/ok]")
                else: print(f"✓ İçe aktarıldı (eklenen={n}).")
                _autosave(books, persist_path); print_inventory(books)

            elif cmd == "k":
                _autosave(books, persist_path)

            elif cmd == "y":
                books[:] = load_from_file_safe(persist_path or "books_pro.json", on_missing=print)
                if HAS_RICH: console.print(f"[ok]✓ Yüklendi. Toplam: {len(books)}[/ok]")
                else: print(f"✓ Yüklendi. Toplam: {len(books)}")
                print_inventory(books)

            elif cmd == "u":
                fee_per_day = float(input("Günlük ücret (örn 1.5): ").strip())
                if HAS_RICH: console.print(f"[ok]✓ Güncellendi: {fee_per_day:.2f}[/ok]")
                else: print(f"✓ Güncellendi: {fee_per_day:.2f}")

            elif cmd == "q":
                _autosave(books, persist_path)
                if HAS_RICH: console.print("[muted]Görüşürüz! 👋[/muted]")
                else: print("Görüşürüz! 👋")
                break

            else:
                if HAS_RICH: console.print("[muted]Komut: t/s/a/e/b/w/r/o/i/x/m/k/y/u/q[/muted]")
                else: print("Komut: t/s/a/e/b/w/r/o/i/x/m/k/y/u/q")

        except (ValidationError, DuplicateBookError, NotFoundError, ValueError) as e:
            msg = f"Hata: {e}"
            if HAS_RICH: console.print(f"[err]{msg}[/err]")
            else: print(msg)
        except KeyboardInterrupt:
            print("\n(iptal)")

if __name__ == "__main__":
    main(seed=True)

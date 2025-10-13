

from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional



def _today_str() -> str:
    """
      Bugünün tarihini YYYY-MM-DD formatında döndürür.
      Dönüş:
          str: ISO biçiminde tarih (örnek: '2025-10-13')
      """
    return datetime.now().strftime("%Y-%m-%d")


def _in_days_str(days: int) -> str:
    """
    Bugünden itibaren verilen gün sayısı kadar ileri (veya geri) tarih döndürür.
    Parametreler:
        days (int): Kaç gün ekleneceği (negatifse geçmiş tarih)
    Dönüş:
        str: ISO formatında tarih (YYYY-MM-DD)
    """
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


BOOKS: List[Dict] = [
    {"id": 1, "title": "Dune", "author": "Frank Herbert", "available": True,  "borrower": None, "due_date": None},
    {"id": 2, "title": "Kürk Mantolu Madonna", "author": "Sabahattin Ali", "available": True,  "borrower": None, "due_date": None},
    {"id": 3, "title": "1984", "author": "George Orwell", "available": False, "borrower": "ayse", "due_date": _in_days_str(-2)},  # gecikmiş örnek
]

def _next_book_id(books: List[Dict]) -> int:
    """
    Yeni kitap için benzersiz ID üretir.
    - Liste boşsa 1 döndürür.
    - Aksi halde listedeki en büyük ID’nin bir fazlasını verir.
    Parametreler:
        books (List[Dict]): Mevcut kitap listesi.
    Dönüş:
        int: Yeni verilecek benzersiz kitap ID’si.
    """
    if not books:
        return 1

    max_id = 0
    for b in books:
        try:
            bid = int(b.get("id"))
            if bid > max_id:
                max_id = bid
        except Exception:

            continue

    return max_id + 1


def add_book(books: List[Dict], title: str, author: str) -> Dict:
    """
        Yeni bir kitap ekler ve eklenen kitabı döndürür.
        Kurallar:
        - Başlık (title) veya yazar (author) boş olamaz, aksi halde ValueError fırlatılır.
        - Yeni kitap varsayılan olarak müsaittir (available=True).
        Parametreler:
            books (List[Dict]): Kitap listesi.
            title (str): Kitap başlığı.
            author (str): Kitap yazarı.
        Dönüş:
            Dict: Eklenen kitabın sözlük yapısı.
        """
    if title is None or author is None:
        raise ValueError("title/author boş olamaz")
    t = str(title).strip()
    a = str(author).strip()
    if not t or not a:
        raise ValueError("title/author boş olamaz")

    nid = _next_book_id(books)

    new_book = {
        "id": nid,
        "title": t,
        "author": a,
        "available": True,
        "borrower": None,
        "due_date": None,
    }


    books.append(new_book)
    return new_book


def search_books(books: List[Dict], query: str) -> List[Dict]:
    """
     Başlık veya yazar alanında, büyük/küçük harf duyarsız arama yapar.
     Kurallar:
     - Sorgu (query) boş veya None ise boş liste döndürülür.
     - None değerli alanlarda hata alınmaz.
     Parametreler:
         books (List[Dict]): Kitap listesi.
         query (str): Aranacak kelime veya ifade.
     Dönüş:
         List[Dict]: Eşleşen kitapların listesi.
     """
    if query is None:
        return []
    q = str(query).strip().lower()
    if not q:
        return []

    results = []
    for b in books:
        title = (b.get("title") or "").lower()
        author = (b.get("author") or "").lower()
        if q in title or q in author:
            results.append(b)
    return results

def borrow_book(books: List[Dict], book_id: int, username: str, days: int = 14) -> bool:
    """
     Kitabı ödünç verir.
     Args:
         books (list[dict]): Kitap listesi
         book_id (int): Kitap ID'si
         username (str): Kullanıcı adı
         days (int): Kaç günlüğüne verilecek
     Returns:
         bool: Başarılıysa True, aksi halde False
     """
    for b in books:
        if b.get("id") == book_id:
            if b.get("available"):
                b["available"] = False
                b["borrower"] = username
                b["due_date"] = _in_days_str(days)
                return True
            return False
    return False

def return_book(books: List[Dict], book_id: int) -> bool:
    """
    Kitabı iade eder; bulunursa alanları sıfırlar.
    Parametreler:
        books (List[Dict]): Kitap listesi.
        book_id (int): İade edilen kitabın ID’si.
    Dönüş:
        bool: Kitap bulunduysa True, bulunamadıysa False.
    """
    for b in books:
        if b.get("id") == book_id:
            b["available"] = True
            b["borrower"]  = None
            b["due_date"]  = None
            return True
    return False


def list_overdue(books: List[Dict], today: Optional[str] = None) -> List[Dict]:
    """
        Belirtilen tarihe göre gecikmiş kitapları döndürür.
        Kurallar:
        - available=True olanlar gecikmiş sayılmaz.
        - due_date < today olanlar gecikmiştir.
        - today verilmezse bugünün tarihi (_today_str) kullanılır.
        Parametreler:
            books (List[Dict]): Kitap listesi.
            today (Optional[str]): Karşılaştırma tarihi (YYYY-MM-DD).
        Dönüş:
            List[Dict]: Gecikmiş kitapların listesi.
        """
    if today is None:
        today = _today_str()
    fmt = "%Y-%m-%d"
    today_dt = datetime.strptime(today, fmt)

    out = []
    for book in books:
        if book.get("available") is True:
            continue
        due = book.get("due_date")
        if not isinstance(due, str) or due == "":
            continue
        try:
            due_dt = datetime.strptime(due, fmt)
        except ValueError:
            continue
        if due_dt < today_dt:
            out.append(book)
    return out

def save_to_file(books: List[Dict], path: str) -> None:
    """
       Kitap listesini belirtilen dosyaya JSON formatında kaydeder.
       Parametreler:
           books (List[Dict]): Kaydedilecek kitap listesi.
           path (str): Dosya yolu.
       Notlar:
           - UTF-8 formatında kaydeder.
           - ensure_ascii=False → Türkçe karakterleri korur.
           - indent=2 → okunabilir biçim.
       """

    with open(path, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)

def load_from_file(path: str) -> List[Dict]:
    """
       JSON dosyasını okuyup kitap listesi döndürür.
       Kurallar:
       - Dosya yoksa FileNotFoundError yakalanır ve boş liste döndürülür.
       - Hata durumunda kullanıcıya uyarı mesajı gösterilir.
       Parametreler:
           path (str): Dosya yolu.
       Dönüş:
           List[Dict]: Okunan kitap listesi veya boş liste.
       """
    import json, sys
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Uyarı: '{path}' bulunamadı, boş liste döndürülüyor.", file=sys.stderr)
        return []


def _demo():
    print("Demo: kitap ara 'an'")
    print(search_books(BOOKS, "an"))

if __name__ == "__main__":
    _demo()


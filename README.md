<!-- Banner / Kapak -->
<p align="center">

</p>

<h1 align="center">📚 Pro Kütüphane (CLI) — Türkçe Akıllı Arama, Zengin Terminal</h1>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="#"><img src="https://img.shields.io/badge/Tests-PASS-28a745?logo=pytest&logoColor=white" alt="Tests PASS"></a>
  <a href="#"><img src="https://img.shields.io/badge/CLI-Rich-6f42c1?logo=readme&logoColor=white" alt="Rich CLI"></a>
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-informational" alt="OS"></a>
</p>

<p align="center">
  <i>Türkçe/aksan duyarlı arama, Title Case normalizasyon, ödünç/iade (gecikme & ücret), kalıcı JSON, <b>Rich</b> ile renkli & zebra tablo, otomatik kaydetme.</i>
</p>

---
# Kütüphane Uygulaması (CLI) — Türkçe Akıllı Arama, Kalıcı Kayıt, Testli Tasarım

Bu repo; verilen “kitap yönetimi” gereksinimlerini sadece düzeltmekle kalmayıp, **kullanıcı deneyimi** ve **mühendislik kalitesi** ile genişleten bir örnek projedir.  
Öne çıkanlar: **Türkçe/aksan duyarlı arama**, **Title Case normalizasyonu**, **ödünç/iade + gecikme ücreti**, **kalıcı JSON formatı**, **zengin terminal arayüzü (Rich)** ve **pytest testleri**.

---

## 🔥 Proje?

Yarışmada verilen kitap yönetimi görevini sadece “düzeltmekle” kalmayıp, **kullanıcı deneyimi** ve **mühendislik kalitesi** ekledim:

- ✅ **Türkçe & aksan akıllı arama** (İ/ı, ş/Ş vb. dert yok)
- ✅ **Başlık/Yazar Title Case** — girdi otomatik güzelleşir
- ✅ **Ödünç verme & iade** — gecikme ve ücret hesabı
- ✅ **Zengin terminal arayüzü** — Rich: renkli rozetler, zebra tablo, sütun katlama
- ✅ **Kalıcı kayıt** — `books_pro.json` (meta’lı)
- ✅ **Güvenli I/O** — dosya yoksa/bozuksa hata yerine anlamlı geri dönüş
- ✅ **Testler (pytest)** — 5/5 PASS


## 1) Problem Tanımı & Beklentiler

- Kitap listesini yönet: **ekle**, **ara**, **ödünç ver**, **iade et**, **gecikenleri listele**.
- ID atama: liste boşsa `1`, doluysa **max(id)+1** (sıra bağımsız).
- Arama: başlık/yazar alanında **büyük–küçük harf ve aksan bağımsız** arama. Boş sorgu → boş liste.
- Ödünç verme: yalnız **müsait** kitaplar verilebilir; iade tarihini gün bazında hesapla.
- İade: kitabı sıfırla; **gecikme gününü ve ücreti** hesapla.
- Kalıcılaştırma: **JSON** formatında güvenli kaydet/okut (dosya yok/bozuk → anlamlı dönüş).
- CLI/demoda anlaşılır ve temiz çıktı.

---

## 2) Çözüm Özeti

- **library_pro.py**: Uygulama mantığı + CLI (interaktif demo).
- **test_pro.py**: İşlevsel testler (pytest) – 5/5 PASS.
- **Zengin CLI**: `rich` varsa renkli kartlar ve genişleyen tablo; yoksa ANSI fallback.
- **Türkçe normalize**: `İ/ı` için özel map + `unicodedata` ile aksan temizleme.
- **Kalıcı JSON**: meta’lı format (`version`, `saved_at`, `total_books`, `books`).
- **Hata toleranslı I/O**: `FileNotFoundError` ve `JSONDecodeError` güvenli yönetim.

---

## 3) Teknoloji Yığını

- **Python 3.10+**
- **Standart kütüphane**: `datetime`, `json`, `logging`, `typing`, `unicodedata`, `re`, `os`
- **3. parti (opsiyonel/prod)**:  
  - `rich` — zengin terminal, tablo ve paneller (opsiyonel)
  - `colorama` — Windows ANSI renk düzeltmesi (opsiyonel)
- **3. parti (dev/test)**:  
  - `pytest` — birim testleri

`requirements.txt`:


---


<img width="1761" height="800" alt="Ekran görüntüsü 2025-10-13 214226" src="https://github.com/user-attachments/assets/ae35ba60-f5cf-41f4-8c6b-4b85d4103406" />

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


## 1) Problem Tanımı & Beklentiler

- Kitap listesini yönet: **ekle**, **ara**, **ödünç ver**, **iade et**, **gecikenleri listele**.
- ID atama: liste boşsa `1`, doluysa **max(id)+1** (sıra bağımsız).
- Arama: başlık/yazar alanında **büyük–küçük harf ve aksan bağımsız** arama. Boş sorgu → boş liste.
- Ödünç verme: yalnız **müsait** kitaplar verilebilir; iade tarihini gün bazında hesapla.
- İade: kitabı sıfırla; **gecikme gününü ve ücreti** hesapla.
- Kalıcılaştırma: **JSON** formatında güvenli kaydet/okut (dosya yok/bozuk → anlamlı dönüş).
- CLI/demoda anlaşılır ve temiz çıktı.

---


# 🧭 Menü & Komut Haritası

| Kısayol | İşlem                | Ne Yapar?                                                              |
| :-----: | -------------------- | ---------------------------------------------------------------------- |
|   `t`   | **tüm liste**        | Bütün envanteri tabloda gösterir.                                      |
|   `s`   | **sadece müsaitler** | Anlık olarak **müsait** olanları listeler (ödünçte olmayanlar).        |
|   `a`   | **ara**              | Türkçe-aksan duyarlı arama (`any / all / prefix` modları desteklenir). |
|   `e`   | **ekle**             | Yeni kitap ekler (Title Case, duplicate kontrolüyle).                  |
|   `b`   | **ödünç ver**        | Kitabı kullanıcıya verir; **Aldığı/Teslim** tarihlerini ayarlar.       |
|   `w`   | **waitlist'e ekle**  | Meşgul kitaba sıraya girer; iade olunca otomatik atanır.               |
|   `r`   | **yenile (renew)**   | Gecikmemiş kitabın teslim tarihini kurallı şekilde uzatır.             |
|   `o`   | **overdue**          | Geciken kitapları ve tahmini toplam ücreti gösterir.                   |
|   `i`   | **iade (ücretli)**   | İade eder; gecikme gününden **ücret** hesaplar ve waitlist varsa atar. |
|   `x`   | **CSV dışa aktar**   | Listeyi CSV’ye yazar (örn. `export.csv`).                              |
|   `m`   | **CSV içe aktar**    | CSV’den `title/author` alanlarıyla kitap ekler (duplicate’ları atlar). |
|   `k`   | **kaydet**           | JSON’a kaydeder (atomic write + meta bilgisi).                         |
|   `y`   | **yükle**            | JSON’dan yeniden yükler.                                               |
|   `u`   | **günlük ücret**     | Gecikme ücretini değiştirir (varsayılan: `1.5`).                       |
|   `q`   | **çıkış**            | Kaydedip güvenle çıkar.                                                |





> t
📚 Pro Kütüphane — Envanter
[ID] [Başlık]                 [Yazar]             [Durum]        [Alan]  [Aldığı]     [Teslim]     [Bekleyen]
  1  Dune                     Frank Herbert       Müsait          -       -            -            0
  2  Kürk Mantolu Madonna     Sabahattin Ali      Müsait          -       -            -            0
  3  1984                     George Orwell       Müsait değil    Zey     2025-10-01   2025-10-12   1


-------------------------------------------------------------------

> s
✅ Müsait Kitaplar
[ID] [Başlık]                 [Yazar]             [Durum]
  1  Dune                     Frank Herbert       Müsait
  2  Kürk Mantolu Madonna     Sabahattin Ali      Müsait

-------------------------------------------------------------------

> a
Arama: dUnE
Mod (any/all/prefix): any
1 sonuç:
 - Dune — Frank Herbert
--------------------------------------------------------------------

> e
Başlık: sefiller
Yazar: victor hugo
✓ Eklendi.
--------------------------------------------------------------------

> b
Ödünç verilecek ID: 1
Kullanıcı adı: ali
Gün sayısı (örn 14): 7
✓ Ödünç verildi.
--------------------------------------------------------------------

> w
Waitlist ID: 1
Kullanıcı adı: ayşe
✓ Waitlist'e eklendi.
-------------------------------------------------------------------

> r
Yenilenecek ID: 1
Ek gün (örn 7): 7
✓ Yenilendi.
-------------------------------------------------------------------

> o
Geciken 1 kitap (tahmini ücret=3.00): ['1984']
-------------------------------------------------------------------

> i
İade edilecek ID: 3
✓ İade. Gecikme=2 gün, Ücret=2.00
-------------------------------------------------------------------

> x
CSV yol (örn export.csv): kitaplar.csv
✓ Dışa aktarıldı.
-------------------------------------------------------------------

> m
CSV yol (örn import.csv): import.csv
✓ İçe aktarıldı (eklenen=5).
------------------------------------------------------------------

> k
✓ Kaydedildi.
-----------------------------------------------------------------

> y
✓ Yüklendi. Toplam: 12






> s
✅ Müsait Kitaplar
[ID] [Başlık]                 [Yazar]            [Durum]
  1   Dune                    Frank Herbert      Müsait
  2   Kürk Mantolu Madonna    Sabahattin Ali     Müsait



<img width="1699" height="615" alt="Ekran görüntüsü 2025-10-14 172050" src="https://github.com/user-attachments/assets/232e3ee4-09de-499d-bec1-a918a851928d" />

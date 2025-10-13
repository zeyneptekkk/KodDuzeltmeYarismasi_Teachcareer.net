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

## 🔥 Neden Bu Proje?

Yarışmada verilen kitap yönetimi görevini sadece “düzeltmekle” kalmayıp, **kullanıcı deneyimi** ve **mühendislik kalitesi** ekledim:

- ✅ **Türkçe & aksan akıllı arama** (İ/ı, ş/Ş vb. dert yok)
- ✅ **Başlık/Yazar Title Case** — girdi otomatik güzelleşir
- ✅ **Ödünç verme & iade** — gecikme ve ücret hesabı
- ✅ **Zengin terminal arayüzü** — Rich: renkli rozetler, zebra tablo, sütun katlama
- ✅ **Kalıcı kayıt** — `books_pro.json` (meta’lı)
- ✅ **Güvenli I/O** — dosya yoksa/bozuksa hata yerine anlamlı geri dönüş
- ✅ **Testler (pytest)** — 5/5 PASS

---

## 🧭 İçindekiler

- [Kurulum](#-kurulum)
- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Özellikler](#-özellikler)
- [Ekran Görüntüleri](#-ekran-görüntüleri)
- [Kullanım (Demo CLI)](#-kullanım-demo-cli)
- [Testler](#-testler)
- [Proje Yapısı](#-proje-yapısı)
- [Mimari & Akış](#-mimari--akış)
- [Teknik Notlar](#-teknik-notlar)
- [SSS](#-sss)
- [Yol Haritası](#-yol-haritası)
- [Lisans & İletişim](#-lisans--iletişim)

---

t = tüm liste
a = ara
e = ekle
b = ödünç ver
o = overdue (gecikenler)
i = iade (gecikme + ücret)
k = kaydet
y = yükle
u = günlük ücret
q = çıkış


> t


> a
Arama: kurk mantolu
Mod (any/all/prefix): all


> e
Başlık: ayşe kulin
Yazar: veda
✓ Eklendi.
# Listeye "Ayşe Kulin — Veda" olarak eklenir.

 > b
Ödünç verilecek ID: 2
Kullanıcı adı: Zey
Gün sayısı (örn 14): 7
✓ Ödünç verildi.
# Listede "Müsait değil", Alan: Zey, Teslim: YYYY-MM-DD


> o
Geciken 1 kitap (tahmini ücret=3.00): ['1984']


> i
İade edilecek ID: 2

✓ İade edildi. Gecikme=2 gün, Ücret=3.00



<img width="1761" height="800" alt="Ekran görüntüsü 2025-10-13 214226" src="https://github.com/user-attachments/assets/ae35ba60-f5cf-41f4-8c6b-4b85d4103406" />

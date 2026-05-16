# TulparAI · 11-Slide Pitch Deck Content (TR)

> Hackathon brief mandates this exact slide order. Theme codes appear on cover + final slide.
> Visual identity: Turkish flag red `#A91101` + dark obsidian background + Fraunces display +
> Geist sans body. Tulpar (winged horse) silhouette as recurring motif.

---

## Slide 1 — Kapak

**Başlık (display):**
> # TulparAI 🐎
> _Türk sporcusunun **doğrulanmış** AI antrenörü._

**Alt başlık:**
> Çoklu ajan · Tool kullanan · Sıfır halüsinasyon · NVIDIA Nemotron × Türksat altyapısı

**Tema kodları (alt köşe, ufak):**
> A3 · B2 · C1 · C2 · C3 · C5 · C7 · D7

**Logo şeridi:** NVIDIA · Türksat · YTÜ

**Tasarım notu:** Tam ekran kanatlı at silueti (vektor), kırmızı vurgular. Tipografi: Fraunces italic.

---

## Slide 2 — Ekip

**Başlık:** Ekip

**Tek kişi format:**
> ## Abdulhamid Batayhi
> Full-stack AI mühendisi · Backend & AI mimar · Frontend tasarımcı · Veri & pitch
>
> 38 saatte ✕ tek kişi ✕ 5,500+ satır kod ✕ üretim seviye demo

**Yanında küçük:**
> Build partner: **Claude (Anthropic)** — yan ajanlar, kod review, dokümantasyon.

**Tasarım notu:** Üst alanda Github avatarı / fotoğraf, altta "yetenekler" listesi rozet stilinde.

---

## Slide 3 — Problem

**Başlık:** Türkiye'nin sporcuları eşitsiz.

**Ana metin:**
> - **800+ milli sporcu** — bir kısmı diyetisyenle, çoğu Google ile çalışıyor.
> - **350.000+ federe sporcu (TFF · TWF · THF · TVF)** — kişisel rehberlik bütçesi yok.
> - **5 milyon+ rekreasyonel sporcu** — gelişigüzel YouTube tavsiyesi.

**Mevcut çözümlerin sınırı:**
> | Seçenek | Sorun |
> |---|---|
> | İnsan diyetisyen | ~₺1.500 / seans, sadece elit sporcunun erişimi |
> | ChatGPT / Gemini | Halüsinasyon var → bakanlık yasal olarak deploy edemez |
> | MyFitnessPal | AI yok, kişisel antrenörlük yok |

**Vurgu:** *Halüsinasyon, kamuda AI'ın önündeki en büyük yasal engel.*

---

## Slide 4 — Çözüm

**Başlık:** Tool çağıran AI'a kaynak gösterme zorunluluğu ekledik.

**Mimari diyagram (kutu çerçeve):**
```
[Sporcu sorusu]
      ↓
   ANALYZER          → JSON niyet
      ↓
   REASONER          → 7 tool · function calling · [T1] [T2] etiketleri
      ↓
   VERIFIER          → her [Tx] iddiası tool çıktısıyla eşleşir; eşleşmeyen silinir
      ↓
   FORMATTER         → güvenlik notu + kaynak paneli
      ↓
[Doğrulanmış cevap]
```

**Üç farklılaşma:**
> 1. **`[Tx]` kanıt işaretleri tool *çıktılarına* bağlı** — statik kaynaklara değil. Verifier garantisi daha güçlü.
> 2. **Sport-filtered RAG** — futbol sorusu sadece futbol KB'sini görür. Çapraz kirlilik imkânsız.
> 3. **Authority-weighted reranker** — IOC × 1.0, federasyon × 0.9, makale × 0.85.

**Pitch line:** _"Diğer ajanlar tool çağırır ve modele güvenir. TulparAI tool çağırır, modeli kaynak göstermeye zorlar, sonra ayrı bir Verifier modeli kaynaksız iddiaları siler."_

---

## Slide 5 — Ürün

**Başlık:** Tek bir hero ekran.

**İçerik:** `/chat` ekranının screenshot'u (orta) — şu unsurlar görünür:
> - Sol üst: 4 ajan rozeti, sırayla yanıp sönen (Analyzer → Reasoner → Verifier → Formatter)
> - Mesaj balonu içinde: tool çağrı chip'leri (search_sport_kb · 247ms, web_search_trusted · 1.7s)
> - Cevap metni: cümle sonlarında `[T1] [T2]` işaretleri
> - Cevabın altında: ✅ Doğrulandı 95% · "Nasıl cevapladım?" linki
> - Genişletilmiş kaynak paneli: 2 satır snippet + URL'ye git butonu

**Yan sütun (özellik listesi):**
> - 🎙️ Sesli giriş (TR + EN)
> - 📸 Yemek/sakatlık fotoğrafı (NVIDIA VLM)
> - 📄 Kişisel doküman yükleme (per-athlete RAG)
> - 💬 Telegram bot (her kullanıcı kendi profili)
> - 🌗 Açık / koyu tema

---

## Slide 6 — Demo

**Başlık:** 60 saniyede TulparAI.

**Demo akış kart:**
> ```
> 0:00 — 4 sporcu profili: Ahmet (futbol) · Ayşe (voleybol) · Mehmet (güreş) · Naim (halter)
> 0:08 — Aynı soru hepsine: "Bugün antrenmandan önce ne yemeliyim?"
> 0:25 — 4 farklı doğru cevap akıyor — her biri kendi sporundan, kendi profilinden
> 0:50 — Ahmet'in cevabında "Nasıl cevapladım?" — Verifier'ın sildiği iddialar görünür
> 0:58 — github.com/abdulhamidbatayhi123/TulparAI · canlı URL
> 1:00 — "Aynı motor. 4 spor. Sıfır halüsinasyon."
> ```

**Embed:** 60 sn YouTube unlisted video, tam alan.

---

## Slide 7 — İş Modeli

**Başlık:** B2G + B2B2C + Premium.

**3 sütun (her biri kart):**

> **B2G — Bakanlık**
> Gençlik ve Spor Bakanlığı: 800 milli sporcu × ₺500/yıl = **₺400.000 v1 sözleşmesi**.
> Genişleme: 60 federasyon başkanına lisans.

> **B2B2C — Federasyonlar**
> TFF · TWF · THF · TVF ortaklığı. Her federasyon kendi üyelerine ücretsiz veya ucuz erişim sağlar.
> 60 federasyon × ort. 5.000 sporcu × ₺50/yıl = **~₺15M / yıl**.

> **Premium — Kulüpler & bireysel**
> Süper Lig kulüpleri, özel halter / güreş kampları: **₺200 / ay**.
> Çoklu sporcu, gelişmiş analitik, koç paneli (slide 7 mock).

**Alt çıkarım:** Yıllık potansiyel ₺20M+ Türkiye iç pazarda.

---

## Slide 8 — Hedef Kitle

**Başlık:** Üç katmanlı pazar.

**T1 — Elit (800 kişi):**
> Milli takım sporcuları. GSB sözleşmesi. Yüksek dokunma, yüksek bütçe.

**T2 — Federe (350K+):**
> TFF aktif lisansı + diğer federasyonlar. Kişiselleştirme + çoklu ses (TR).

**T3 — Rekreasyonel (5M+):**
> Spor salonu üyeleri, koşucular, amatör futbolcular. Freemium katman + Telegram bot dağıtımı.

**Demo sporcular:**
> Ahmet · Süper Lig forveti · İstanbul
> Ayşe · Milli voleybolcu (orta) · Ankara
> Mehmet · 74 kg serbest güreş · Konya
> Naim · 89 kg halter · İzmir

---

## Slide 9 — Pazar

**Başlık:** Pazar potansiyeli.

**Üç sayı, tek satır:**
> | Pazar | Boyut | Kaynak |
> |---|---|---|
> | TR spor-tech | **₺2 milyar+** | Türksat dijitalleşme planı 2026 |
> | Global AI nutrition / coaching | **\$4 milyar by 2028** | Statista, sport-tech raporu |
> | TR kamu AI Türksat | **\$1 milyar+** | Türksat 5-yıl plan |

**Vurgu:** Türksat altyapısı, ses tonu, federasyon ortaklığı → defansif moat.

---

## Slide 10 — Rekabet

**Başlık:** Rakipler vs TulparAI.

**Matrix (5 satır × 5 sütun):**

> | | ChatGPT | MyFitnessPal | İnsan diyetisyen | **TulparAI** |
> |---|---|---|---|---|
> | Halüsinasyon koruması | ❌ | n/a | ✅ | ✅ Verifier |
> | Spor-özel KB | ❌ | ❌ | ✅ | ✅ Sport-filtered |
> | Personalizasyon | Yüzeysel | Manuel | ✅ | ✅ Profile + logs |
> | Ölçek | ✅ | ✅ | ❌ | ✅ Cloud |
> | Türkçe + TR federasyon | Genel | ❌ | ✅ | ✅ Yerel |
> | Maliyet / kullanıcı | Belirsiz | Aylık | ₺1.500 / seans | **< ₺50 / yıl** |

**Moat'lar:**
> 1. Verifier guardrail (yasal defansif)
> 2. TFF/TWF/THF/TVF ortaklık potansiyeli
> 3. NVIDIA + Türksat altyapı uyumu
> 4. Bilinen olmayan açık-kaynak çekirdek (OpenAgent türevi)

---

## Slide 11 — Teşekkür

**Başlık:** Teşekkürler.

**Ana metin:**
> ## TulparAI 🐎
> Doğrulanmış. Kişisel. Türksat'ta hazır.

**İletişim + linkler:**
> - 🔗 github.com/abdulhamidbatayhi123/TulparAI
> - 🌐 tulparai.vercel.app
> - 📨 abdulhamidbataihi@gmail.com

**Tema kodları (tekrar):**
> A3 · B2 · C1 · C2 · C3 · C5 · C7 · D7

**Logo şeridi:** NVIDIA · Türksat · YTÜ · 100 StartUP Bootcamp

**Pitch closing line (yüksek sesle):**
> _"Aynı motor. Dört spor. Sıfır halüsinasyon. Türksat altyapısında, Türk sporcusunun cebinde."_

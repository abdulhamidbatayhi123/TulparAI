# TulparAI — 5 Dakikalık Türkçe Pitch Script

> Hedef: Tam 5 dakika · Türkçe · 11 slide · sonunda 2 dakikalık Q&A.
> Konuşma temposu: ~150 kelime / dakika. ~750 kelime toplam.

---

## 0:00 – 0:30 · Açılış (Slide 1 — Kapak)

> "Selamlar. Ben Abdulhamid Batayhi. Karşınızda **TulparAI** — Türk sporcusunun
> doğrulanmış AI antrenörü.
>
> *Tulpar* Türk mitolojisindeki kanatlı attır. Hızlı, akıllı, sadık. AI'mız da öyle —
> ama daha önemlisi, **halüsinasyon yapmıyor.** Çünkü matematiksel olarak yapamayacak
> şekilde tasarladık.
>
> Size 5 dakikada neden bunun GSB için bir devrim olduğunu göstereceğim."

---

## 0:30 – 0:50 · Ekip (Slide 2 — Ekip)

> "Ben tek başıma — 38 saatte, sıfırdan, üretim seviye bir mimari kurdum:
> backend, frontend, multimodal pipeline, çoklu ajan orkestrasyon, doğrulama mekaniği,
> kişiselleştirme. Build partner olarak Claude'u kullandım — kod review, doküman ve
> yan ajanlar için. Tek başıma çoğu takımdan daha hızlıydım çünkü doğru yapılandırdım."

---

## 0:50 – 1:30 · Problem (Slide 3 — Problem)

> "Türkiye'de 800 milli sporcu var. 350 binden fazla federe sporcu. 5 milyondan fazla
> rekreasyonel sporcu. Bu insanların büyük çoğunluğu, spor-spesifik beslenme veya
> antrenman tavsiyesini şu üç yerden alıyor:
>
> Bir — pahalı insan diyetisyenden, ₺1500 seansta. Ulaşılmaz.
> İki — Google'dan. Düşük kalite.
> Üç — ChatGPT'den. **Halüsinasyon var.** Yani bakanlık yasal olarak deploy edemez.
>
> **İşte bu yüzden kamuda AI dönüşümü tıkanıyor: kaynaksız iddia hayatla oynar.**"

---

## 1:30 – 2:30 · Çözüm (Slide 4 — Çözüm)

> "Çözümümüz şu. Çoğu agent tool çağırır ve modele güvenir. TulparAI tool çağırır,
> sonra modeli her olgusal cümlenin sonuna `[T1] [T2]` etiketi koymaya zorlar. **Bu
> etiket, hangi tool çıktısına dayanıyor o cümle, onu söyler.**
>
> Ardından — ki esas yenilik bu — *ayrı bir Verifier modeli* çalışır. Her `[Tx]`
> iddiasını gerçekten ilgili tool çıktısının desteklediğini kontrol eder.
> Kaynaksız iddiayı **siler.**
>
> Bizim mimarimiz dört ajan: Analyzer niyet okur, Reasoner tool çağırır ve cevap
> üretir, Verifier siler, Formatter sonu temizler. Yedi tool var: spor-filtreli
> bilgi tabanı, gıda makro arama, kalori hesabı, hava durumu, log kaydı, güvenli
> web araması, görüntü analizi.
>
> Bilgi tabanı **1.236 chunk** — IOC, UEFA, UWW, IWF, FIVB, NSCA. Hepsi açık
> erişim, otorite ağırlıklı reranker'la skorlanıyor."

---

## 2:30 – 3:15 · Demo (Slide 5 + 6 — Ürün + Demo)

> "Şimdi ekrana dikkat. **[Demo videosu başlar — 60 saniye.]**
>
> [Anlatım, video sırasında:]
> Dört sporcu var, dört farklı spor. Aynı soruyu soruyorum: 'Bugün antrenmandan
> önce ne yemeliyim?'
>
> Bakın — her birinde sol üstte ajan rozetleri yanıp sönüyor. Tool chip'leri
> akıyor — search_sport_kb 247 milisaniye, web_search_trusted 1.7 saniye. Cevaplar
> aynı anda farklılaşıyor. Ahmet için pasta + tavuk, Ayşe için RED-S dikkati,
> Mehmet için kilo kesimi-hassas, Naim için yüksek karb.
>
> Şimdi 'Nasıl cevapladım?' butonuna basıyorum. Drawer açılıyor — Verifier'ın
> sildiği iki iddia burada gözüküyor. Şeffaflık. Yasal defansiflik.
>
> [Video biter.]
>
> Aynı motor. Dört spor. Sıfır halüsinasyon."

---

## 3:15 – 3:50 · İş Modeli (Slide 7 — İş Modeli)

> "Üç gelir kanalı:
>
> Bir — **B2G**. Gençlik ve Spor Bakanlığı'nın 800 milli sporcusu için yıllık
> ₺500 üzerinden ₺400 bin liralık V1 sözleşmesi. Genişlerken 60 federasyon başkanı.
>
> İki — **B2B2C**. Federasyonlarla ortaklık. TFF, TWF, THF, TVF. Her federasyon
> kendi üyelerine erişim verir. 60 federasyon × ortalama 5 bin sporcu × ₺50 →
> yaklaşık ₺15 milyon yıllık.
>
> Üç — **Premium**. Kulüpler ve bireysel kullanıcılar için aylık ₺200. Süper Lig
> kulüpleri, halter kampları, güreş takımları için koç paneli.
>
> Toplam Türkiye iç pazar potansiyeli: yıllık ₺20 milyon üzeri."

---

## 3:50 – 4:15 · Pazar + Rekabet (Slide 8, 9, 10)

> "Pazar büyük. TR spor-tech ₺2 milyar üzeri. Global AI nutrition 2028'e kadar
> $4 milyar. Türksat'ın kamu AI altyapısı ekstra $1 milyar.
>
> Rakiplerimize karşı moat'ımız net: ChatGPT halüsinasyon yapar, MyFitnessPal'da
> AI yok, insan diyetisyen ulaşılmaz pahalı. Bizde **dört defansif kale** var:
> Verifier guardrail, federasyon ortaklığı, NVIDIA + Türksat altyapı uyumu, ve
> Türkçe-yerli bir UX. Hepsini bir araya getiren başka bir ürün yok."

---

## 4:15 – 4:45 · Kapanış (Slide 11 — Teşekkür)

> "TulparAI bugün canlı çalışıyor. GitHub'da public, MIT lisansla. Vercel'de canlı
> URL. Brev tunnel'da NVIDIA backend.
>
> Yarın isterseniz GSB'ye on güne deploy edebiliriz — çünkü zaten Türksat-uyumlu
> NVIDIA altyapısında.
>
> **Verilen söz tek bir cümle**: aynı motor, dört spor, sıfır halüsinasyon.
> Türk sporcusunun cebinde, Türksat altyapısında."

---

## 4:45 – 5:00 · Çağrı

> "Sorularınıza geçebiliriz. Demo için QR kod ekranda."

---

## Sahne notları

| Saniye | Beden / Ses |
|---|---|
| 0:30 | "halüsinasyon yapmıyor" — durakla. Eş-zamanlı düşük tonla. |
| 1:30 | "kamuda AI dönüşümü tıkanıyor" — sahnenin yarısı, ciddi ton. |
| 2:30 | Demo başlamadan önce ekrana dön — telefonu kullan veya pointer. |
| 3:45 | Para rakamları — yavaş ve net. |
| 4:30 | "yarın deploy edebiliriz" — kendinden emin, takım gözüne bak. |
| 5:00 | Q&A için açık duruş, mikrofonu sahnenin önüne. |

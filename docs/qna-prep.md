# TulparAI · Q&A Hazırlığı

> Jüri'nin en olası 10 sorusu + üç-cümlelik öz cevaplar.
> Tonlama: kendinden emin, defansif değil, somut sayılarla.

---

## 1. "Verifier hata yaparsa? False negative riski?"

**Cevap:**
> Verifier şüpheli iddiayı silmek üzerine yapılandırıldı — bilerek "false positive
> < false negative" yönünde eğdik. Skor 0.5 altına düşerse kullanıcı görür: kısmen
> doğrulandı uyarısı. Tamamen güvenemediğimizde ürün açık şekilde *"bu konuda
> doğrulanmış kaynak bulamadım"* der. Bu davranışsal seçim, GSB için yasal
> defansif zırhın özüdür.

---

## 2. "ChatGPT yarın halüsinasyon problemini çözse ne yaparsınız?"

**Cevap:**
> Üç moat'ımız hâlâ durur: bir, sport-filtered RAG ile çapraz-spor kirliliği
> imkânsız — ChatGPT bunu mimari olarak yapamaz. İki, federasyon partnerlikleri
> (TFF, TWF, THF, TVF) ve Türksat altyapı uyumu — bunlar erişim moat'ı.
> Üç, kişiselleştirme — profil + son 48 saat log'ları her sorgunun içine
> enjekte ediliyor. Halüsinasyon problemini çözmek bu üç katmanı çözmez.

---

## 3. "Neden 4 spor? Neden tüm sporları kapsamadınız?"

**Cevap:**
> 38 saatlik hackathon penceresinde 4 sporda iyi olmak, 60 sporda yüzeysel
> olmaktan iyi. Seçtiğimiz dörtlü — futbol (kitle), güreş (Türk milli mirası,
> ağırlık-kesim hassasiyeti), halter (Naim Süleymanoğlu izleği), voleybol
> (kadın sporcu, Olympic gold, kapsayıcılık) — Türkiye'nin spor portföyünün
> derinliğini kanıtlıyor. Üretime geçince her ay 2-3 spor ekleyebiliriz —
> mimari değişmiyor, sadece KB ingest.

---

## 4. "Brev tunnel ölünce demo bozulur. Plan B?"

**Cevap:**
> Üç katmanlı redundancy var. Bir, OpenRouter Nemotron fallback otomatik aktif —
> NVIDIA hosted düşse de cevap akar. İki, 60 saniyelik demo videosu yerel olarak
> hazır — venue wifi'si bile çökse oynatırız. Üç, telefon hotspot. Demo'nun gece
> 11'de ev internetinde, bugün öğlen 3G'de ve şimdi venue'da olmak üzere üç
> farklı network'te test edildi.

---

## 5. "Türksat ile gerçek bir sözleşme var mı?"

**Cevap:**
> Henüz hayır — ama mimari uyum var. NVIDIA build.nvidia.com'da çalışıyoruz,
> aynı altyapıyı Türksat kullanıyor. Brev tunnel da NVIDIA'nın. Yani teknik
> olarak Türksat'ın iç AI cloud'una taşımak bir "infra migration" değil,
> doğrudan deploy. Bu hackathon sonrası ilk hedefimiz Türksat / GSB ile
> görüşme.

---

## 6. "Modeli kendiniz mi eğittiniz?"

**Cevap:**
> Hayır — NVIDIA'nın Nemotron'unu kullanıyoruz, hosted. Bu bilinçli bir tercih:
> bir öğrenci ekibi 38 saatte 120B parametre modeli eğitemez. **Yenilik mimaride.**
> Çoklu ajan orkestrasyon, tool-output-bağlı evidence marker'ları, sport-filtered
> RAG, authority-weighted reranker — bunların tümü bizim. Model katmanı NVIDIA'nın.
> Tıpkı bir car-maker'ın motoru Mercedes'ten alıp şasiyi kendisi inşa etmesi gibi.

---

## 7. "Veri gizliliği? Sporcunun profilini ne yaparsınız?"

**Cevap:**
> Profil sadece SQLite'ta, on-prem ya da Brev tunnel üstünde. NVIDIA'ya sadece
> mevcut sorgu için anonim profil enjeksiyonu gider — kayıt yok, model fine-tune'a
> dahil değil. Türksat deploy'da bu, KVKK seviye-1 güvencesidir. Ek olarak,
> kullanıcı isterse /delete-me ile tüm verileri silinir (henüz UI'da yok ama
> backend hazır).

---

## 8. "1.236 chunk az değil mi?"

**Cevap:**
> Quality > quantity. 1.236 chunk, otorite skoru 0.85-1.0 arasında olan,
> federasyon ya da IOC tarafından yayımlanmış metinler. Bizim eval setimizde
> bu chunk'larla %92 grounding rate elde ediyoruz. Üretime geçince haftada 100
> kaynak eklemek bir cron job — yine de mimari aynı kalır. Daha önemlisi: KB
> dolmasa bile `web_search_trusted` tool'u domain-whitelist'le anlık fallback
> yapıyor — sistem boş veritabanında da çalışıyor.

---

## 9. "Telegram bot neden? Web app yeterli değil mi?"

**Cevap:**
> Türkiye'de 60 milyon Telegram kullanıcısı var. Bir genç sporcu için web app'e
> giriş yapmak friction. Telegram'da sorabilirsen, soruyu **soracaksın**.
> Multi-tenant'lık ücretsiz bonusu: her Telegram user_id otomatik bir TulparAI
> athlete_id oluyor, profil komutla set ediliyor. GSB için ölçek: 800 sporcuya
> bot eklenmesi, web onboarding'inden 10× hızlı.

---

## 10. "Bir judge sorusunu cevaplayamazsanız?"

**Cevap:**
> "Bu, hackathon'da test etmediğimiz bir senaryo — ama mimari açısından şöyle
> ele alırdık: [makul tahmin]. Doğru cevabı sizinle paylaşmak için 24 saat
> verirseniz, daha sağlam bir analizle döneriz." Yalan söylemek değil, *somut
> dürüstlük* — TulparAI'ın kendisinin yaptığı gibi.

---

## Ek sorular (yedek)

- **"Ne kadar para harcıyorsunuz?"** → NVIDIA build ücretsiz, Brev için $5 kullandık (350'lik kredinin).
- **"Açık kaynak mı?"** → MIT lisansla evet, github.com/abdulhamidbatayhi123/TulparAI.
- **"Ölçek?"** → SSE streaming + FastAPI: 100 eşzamanlı kullanıcı tek L4 GPU instance.
- **"Mobile?"** → Responsive tasarım var, native app sonraki sprint.
- **"İngilizce destek?"** → Var, runtime toggle. Pitch için TR seçtik.

import React from "react";
import QuestionImage from "../common/QuestionImage.jsx";

// Draft-only fixture. This screen makes no API calls and cannot publish content.
const localSources = import.meta.glob("../../assets/quiz/*.svg", {
  eager: true,
  query: "?url",
  import: "default",
});
const artwork = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/500px-1665_Girl_with_a_Pearl_Earring.jpg";
const draftAssets = [
  { set: "Genel Kültür", number: 11, name: "İstanbul Boğazı", filename: "bosphorus-schematic.svg", alt: "İki kara bölgesi arasında uzanan boğazı gösteren ölçekli olmayan harita." },
  { set: "Genel Kültür", number: 12, name: "İnci Küpeli Kız", external: artwork, alt: "Koyu arka planda, mavi ve sarı başlık takmış, inci küpeli kişinin portresi." },
  { set: "Genel Kültür", number: 15, name: "Sıfır koordinatları", filename: "zero-coordinates.svg", alt: "Ekvator ve başlangıç meridyeninin işaretlendiği şematik dünya haritası." },
  { set: "Bilim ve Teknoloji", number: 11, name: "Seri dirençler", filename: "series-resistors.svg", alt: "Bir pil ile aynı kapalı devrede seri bağlanmış iki direnç." },
  { set: "Bilim ve Teknoloji", number: 12, name: "Gezegen çapları", filename: "planet-orbits.svg", alt: "Güneş Sistemi'ndeki sekiz gezegenin çaplarını yaklaşık oranlarla gösteren isimsiz karşılaştırma." },
  { set: "Bilim ve Teknoloji", number: 13, name: "Hücre organeli", filename: "mitochondrion.svg", alt: "Çift zarlı ve iç zarı kıvrımlı oval bir hücre organeli şeması." },
  { set: "Bilim ve Teknoloji", number: 15, name: "İkili sayı basamakları", filename: "binary-place-values.svg", alt: "Dört ikili basamağın 8, 4, 2 ve 1 yer değerlerini gösteren tablo." },
];

export default function DraftVisualPreview() {
  return (
    <main style={{ maxWidth: 1160, margin: "0 auto", padding: "24px", fontFamily: "system-ui", color: "#17324d" }}>
      <h1>QuizBlast — görsel taslak önizleme</h1>
      <p role="status" style={{ background: "#fff1ca", borderRadius: 8, padding: 12 }}>
        Geliştirme ortamına özeldir. 7/7 görsel onay bekliyor. Bu sayfa oyun başlatmaz, veri değiştirmez veya içerik yayımlamaz.
      </p>
      <p>Fiziksel kabulde okunabilirlik, doğruluk, kırpma, cevap ipuçları, alt metin ve bozuk görsel davranışını ayrı ayrı kontrol edin.</p>
      <section aria-label="Yedi onaysız görsel taslağı" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 310px), 1fr))", gap: 18 }}>
        {draftAssets.map((item) => {
          const src = item.external || localSources[`../../assets/quiz/${item.filename}`];
          return (
            <article key={`${item.set}-${item.number}`} style={{ border: "1px solid #cad9ea", borderRadius: 12, padding: 16, background: "white" }}>
              <h2 style={{ fontSize: 18, margin: "0 0 8px" }}>{item.set} · Soru {item.number}</h2>
              <p style={{ margin: "0 0 12px" }}>{item.name} — <strong>ONAYSIZ TASLAK</strong></p>
              <QuestionImage src={src} alt={item.alt} style={{ display: "block", width: "100%", maxHeight: 270, objectFit: "contain" }} />
              {!src && <p role="alert">Kaynak dosya bulunamadı.</p>}
              {item.external && <p style={{ fontSize: 12 }}>Harici aday. Lisans kaydı bulunuyor; tarayıcı erişimi ve yayın uygunluğu henüz onaylanmadı.</p>}
            </article>
          );
        })}
      </section>
    </main>
  );
}

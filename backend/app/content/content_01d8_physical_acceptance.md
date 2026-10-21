# CONTENT-01D.8 — Toplu fiziksel kabul hazırlığı (yayın dışı)

## Verify-First kanıtları
- 01D.7 gezegen çap karşılaştırma düzeltmesi: GitHub CI #331 SUCCESS (commit `5b9d312df03df0cfaa3e55541c245a86abcd2634`).
- Genel Kültür ve Bilim-Teknoloji V3: her biri 15 soru, toplam 30 soru; 01D.5 CI #326 SUCCESS.
- 7 görsel `pending_review`, 0 görsel `approved`. Beş SVG özgün taslak; iki dış görsel (tablo ve seri direnç) aday kaynak.
- `backend/app/services/content_deploy.py` sadece ilk V1 koleksiyonu için `publish-v1` işaretini destekliyor. V3 yayın akışı **uygulanmış ve doğrulanmış değil**.

## Fiziksel kabul kontrol listesi — kullanıcı akşam test oturumuna erteledi

- [ ] Önce 7 görselin her birine hak sahibini/kaynağını, lisansını, atfını ve alt metnini tanımla; gerçek erişim, çizim doğruluğu ve düzenleme şartlarını doğrula
- [ ] V3 taslaklarına onaylı görsel bağlantıları kontrollü şekilde ilişkilendir, yayın kapısının gerçekten V3 yayın akışında çağrıldığını doğrula
- [ ] Host Chrome: 30 soruluk iki setin soru sırası, görsel yerleşimi, seçenekleri, sayaç ve sonuç/açıklama davranışı
- [ ] Player Edge: görsel yükleme, alternatif metin, mobil okunabilirlik, cevap seçimi, görsel hata durumunda yanıtlayabilme
- [ ] Display Opera: kırpma, görsel oranı, font ve okunabilirlik, geçiş/sayaç uyumu
- [ ] Her görselde cevabı ele veren yazı, ok, işaret ve aşırı belirgin ipucu bulunmadığını değerlendir
- [ ] Bilim Soru 12: gerçek çap oranları, tüm sekiz gezegenin görünmesi, gezegen isimlerinin gizliliği
- [ ] Genel Kültür Soru 15: 0°/0° kesişiminin doğru coğrafi konumu; yaklaşık kıyı çizgisi sebebiyle yanlış yönlendirme olmaması
- [ ] Bilim Soru 11 ve Genel Kültür Soru 12: harici SVG/JPG lisans/atıf ve güvenilir URL
- [ ] Bozuk görsel URL'sinde oyunun ilerlemeye devam etmesi ve açıklayıcı hata mesajının görünmesi
- [ ] F5/reconnect/QR ve Host/Admin sınırının mevcut regresyonlarda korunması
- [ ] CI PASS, ayrı editoryal onay ve açık kullanıcı izni olmadan Render deploy, veritabanı yazımı veya katalog yayımlaması yapma

## Kabul kararı
**Teknik taslak PASS; görsel ve fiziksel kabul AÇIK.**
Bu kontrol listesi testin yapıldığını veya tüm adayların kullanıma uygun olduğunu göstermez. Yayın aşaması CONTENT-01E olarak ayrıca planlanmalıdır.

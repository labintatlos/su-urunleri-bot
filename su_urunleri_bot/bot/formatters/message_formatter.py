"""
Message templates and formatters for bot responses.
"""

from typing import Dict, List, Optional

from bot.formatters.text_formatter import TextFormatter


class MessageFormatter:
    """Format messages and responses."""

    # Emoji constants
    EMOJI = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'search': '🔍',
        'list': '📋',
        'fish': '🐟',
        'boat': '🚤',
        'alert': '🚨',
        'home': '🏠',
        'back': '🔙',
        'time': '🕐',
        'money': '💰',
        'user': '👤',
        'rule': '📖',
        'penalty': '⚖️',
        'gear': '🎣',
    }

    @staticmethod
    def success(message: str) -> str:
        """Format success message."""
        return f"{MessageFormatter.EMOJI['success']} <b>{TextFormatter.escape_html(message)}</b>"

    @staticmethod
    def error(message: str) -> str:
        """Format error message."""
        return f"{MessageFormatter.EMOJI['error']} <b>Hata:</b> {TextFormatter.escape_html(message)}"

    @staticmethod
    def warning(message: str) -> str:
        """Format warning message."""
        return f"{MessageFormatter.EMOJI['warning']} <b>Uyarı:</b> {TextFormatter.escape_html(message)}"

    @staticmethod
    def info(message: str) -> str:
        """Format info message."""
        return f"{MessageFormatter.EMOJI['info']} {TextFormatter.escape_html(message)}"

    @staticmethod
    def welcome_message(name: str) -> str:
        """Format welcome message."""
        return f"""<b>⚓ SU ÜRÜNLERİ KOLLUK ASİSTANI</b>

Merhaba {TextFormatter.escape_html(name)}! 👋

🌊 <b>Deniz görev alanı</b>

Bu bot, su ürünleri denetimlerinde mevzuat hükümlerinin değerlendirilmesi, ihlallerin tespiti ve uygulanacak işlemlerin belirlenmesine yardımcı olur.

📋 <b>Kullanılabilir Araçlar:</b>
• <b>Tekne Türü Kılavuzları</b> - Kontrol föyü ve raporlama
• <b>Denetime Başla</b> - Adım adım denetim rehberi
• <b>Ceza Rehberi</b> - Mevzuat cezaları ve yaptırımlar
• <b>Tür Çizelgesi</b> - Balık türleri ve avcılık kuralları
• <b>Hesaplayıcılar</b> - Ceza hesaplama araçları

Yardım için <code>/help</code> yazabilirsiniz."""

    @staticmethod
    def article_message(article: Dict) -> str:
        """Format article/regulation message."""
        lines = [
            f"📚 <b>{TextFormatter.escape_html(article.get('title', f'Madde {article.get(\"article\")}'))}</b>",
            f"Kaynak: {TextFormatter.escape_html(article.get('source', '?'))}",
            f"Sayfa: {article.get('page_start', '?')}-{article.get('page_end', '?')}",
            "",
            TextFormatter.escape_html(article.get('body', 'İçerik yok.')[:1000]),
        ]
        return TextFormatter.join_lines(lines)

    @staticmethod
    def species_message(species: Dict) -> str:
        """Format species information."""
        lines = [
            f"🐟 <b>{TextFormatter.escape_html(species.get('name', 'Bilinmeyen'))}</b>",
        ]

        if species.get('min_cm'):
            lines.append(f"📏 Asgari Boy: {species.get('min_cm')} cm")

        if species.get('min_kg'):
            lines.append(f"⚖️ Asgari Ağırlık: {species.get('min_kg')} kg")

        if species.get('time_bans'):
            bans = species.get('time_bans', [])
            human = ', '.join(b.replace('/', ' – ') for b in bans)
            lines.append(f"📅 Zaman Yasağı: {human}")

        return TextFormatter.join_lines(lines)

    @staticmethod
    def penalty_message(penalty: Dict) -> str:
        """Format penalty card."""
        lines = [
            f"⚖️ <b>{TextFormatter.escape_html(penalty.get('violation', 'İhlal'))}</b>",
            f"Seçenek: {TextFormatter.escape_html(penalty.get('option_text', '?'))}",
        ]

        if penalty.get('base_ipc'):
            lines.append(f"💰 Taban Ceza: {TextFormatter.format_money(penalty.get('base_ipc'))}")

        if penalty.get('product_seizure'):
            lines.append(f"✓ Ürün El Konuşu: {penalty.get('product_seizure')}")

        if penalty.get('means_seizure'):
            lines.append(f"✓ Av Aracı El Konuşu: {penalty.get('means_seizure')}")

        if penalty.get('license_action'):
            lines.append(f"📜 Ruhsat İşlemi: {TextFormatter.escape_html(penalty.get('license_action'))}")

        return TextFormatter.join_lines(lines)

    @staticmethod
    def search_results_header(query: str, count: int) -> str:
        """Format search results header."""
        if count == 0:
            return f"{MessageFormatter.EMOJI['search']} <b>\"{TextFormatter.escape_html(query)}\" için sonuç bulunamadı.</b>"
        return f"{MessageFormatter.EMOJI['search']} <b>{count} sonuç bulundu:</b>"

    @staticmethod
    def no_results(query: str) -> str:
        """Format no results message."""
        return f"{MessageFormatter.EMOJI['warning']} <b>\"{TextFormatter.escape_html(query)}\" için sonuç bulunamadı.</b>"

    @staticmethod
    def unauthorized_message(user_id: int) -> str:
        """Format unauthorized access message."""
        return f"""❌ <b>Bu botu kullanmaya yetkiniz bulunmamaktadır.</b>

Yetki talep etmek için sistem yöneticisine aşağıdaki kimlik numaranızı iletin:
🆔 <b>Telegram ID:</b> <code>{user_id}</code>"""

    @staticmethod
    def rate_limit_message(retry_seconds: int) -> str:
        """Format rate limit message."""
        return f"""⏳ <b>Çok sık talep gönderdiniz.</b>

Lütfen {retry_seconds} saniye bekleyip tekrar deneyin."""

    @staticmethod
    def audit_summary(audit) -> str:
        """Format audit summary."""
        return audit.to_summary() if hasattr(audit, 'to_summary') else "Denetim özeti kullanılamıyor."

    @staticmethod
    def error_with_context(error_type: str, message: str, context: Optional[str] = None) -> str:
        """Format error with context."""
        lines = [
            f"{MessageFormatter.EMOJI['error']} <b>Hata Oluştu</b>",
            f"Tür: {TextFormatter.escape_html(error_type)}",
            f"Mesaj: {TextFormatter.escape_html(message)}",
        ]

        if context:
            lines.append(f"Detay: {TextFormatter.escape_html(context)}")

        return TextFormatter.join_lines(lines)

    @staticmethod
    def help_message() -> str:
        """Format help message."""
        return """<b>📖 YARDIM</b>

<b>Komutlar:</b>
/start - Botu başlat
/menu - Ana menüyü göster
/help - Bu yardım mesajını göster
/id - Senin Telegram ID'ni göster

<b>Özellikler:</b>
🔍 <b>Mevzuat Arama</b> - Kanun ve yönetmeliklerde ara
🐟 <b>Tür Arama</b> - Balık türlerini ve kurallarını öğren
⚖️ <b>Ceza Ara</b> - İhlaller ve cezaları sorgula
🚨 <b>Denetim Rehberi</b> - Adım adım denetim yapı

<b>Sorular?</b>
Sistem yöneticisine ulaşın."""

    @staticmethod
    def processing_message() -> str:
        """Format processing message."""
        return "⏳ <b>İşleniyor...</b>"

    @staticmethod
    def confirmation_needed(action: str) -> str:
        """Format confirmation needed message."""
        return f"❓ <b>{TextFormatter.escape_html(action)}</b> işlemini onaylıyor musunuz?"

"""
Kbeauty_diluz Bot v2
- Manual product database (always available, instant)
- Live search across YesStyle, StyleKorean, Jolse, Stylevana, Soko Glam
- Auto price calculation in UZS with shipping + 30% margin
- Bilingual: Uzbek / Russian
- Order collection → Admin notification via Telegram
"""

import os
import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode

from scraper import search_all_sites

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")   # run /adminsetup to find yours
CHANNEL_LINK  = "https://t.me/Kbeauty_diluz"
HUMO_CARD     = "5614 6814 0884 9804"

KRW_TO_UZS  = 8        # 1 KRW  = 8 UZS
USD_TO_UZS  = 12700    # 1 USD  = 12700 UZS  (update when needed)
SHIPPING_USD = 11       # flat shipping cost
MARGIN       = 0.30     # 30% your profit

# ══════════════════════════════════════════════════════════════════════════════
# CONVERSATION STATES
# ══════════════════════════════════════════════════════════════════════════════
(
    LANG, SKIN_TYPE, SKIN_CONCERN, AGE, BUDGET, ROUTINE,
    SHOW_PRODUCTS, PICK_PRODUCT, ORDER_CONFIRM,
    NAME, PHONE, ADDRESS, BIRTHDATE, PAYMENT
) = range(14)

# ══════════════════════════════════════════════════════════════════════════════
# MANUAL PRODUCT DATABASE  ← You add products here anytime
# ══════════════════════════════════════════════════════════════════════════════
# MANUAL PRODUCTS  ← Add your own products here anytime
# Each product has full info: what it is, what it's for, how to use
# ══════════════════════════════════════════════════════════════════════════════
MANUAL_PRODUCTS = [
    {
        "name": "COSRX Acne Pimple Master Patch",
        "brand": "COSRX", "price_usd": 6.50,
        "concern": ["acne"], "skin": ["oily", "combo"],
        "info_uz": (
            "🔬 *Nima bu?* Akne va toshmalarga qarshi maxsus yamoqlar (24 dona).\n"
            "🎯 *Nima uchun?* Yiring chiqaradi, yallig'lanishni kamaytiradi, dog' qoldirmaydi.\n"
            "📋 *Qanday ishlatiladi?* Kechqurun toza quruq teriga yamoqni yopishtirib qo'ying. "
            "Ertalab oling — toshma kichraygan bo'ladi."
        ),
        "info_ru": (
            "🔬 *Что это?* Специальные патчи от прыщей и акне (24 штуки).\n"
            "🎯 *Для чего?* Вытягивает гной, уменьшает воспаление, не оставляет пятен.\n"
            "📋 *Как использовать?* Вечером наклейте на чистую сухую кожу. "
            "Утром снимите — прыщ уменьшится."
        ),
    },
    {
        "name": "Some By Mi AHA BHA PHA 30 Days Miracle Toner",
        "brand": "Some By Mi", "price_usd": 14.00,
        "concern": ["acne", "dark_spots"], "skin": ["oily", "combo"],
        "info_uz": (
            "🔬 *Nima bu?* 3 kislotali (AHA+BHA+PHA) teri yangilovchi toner.\n"
            "🎯 *Nima uchun?* Teshikchalarni tozalaydi, akne va qora dog'larni kamaytiradi, "
            "30 kunda teri yangilanadi.\n"
            "📋 *Qanday ishlatiladi?* Yuz yuvgandan so'ng paxtaga to'kib, "
            "yuzga artib chiqing. Kuniga 1-2 marta."
        ),
        "info_ru": (
            "🔬 *Что это?* Тонер с 3 кислотами (AHA+BHA+PHA) для обновления кожи.\n"
            "🎯 *Для чего?* Очищает поры, уменьшает акне и тёмные пятна, "
            "за 30 дней обновляет кожу.\n"
            "📋 *Как использовать?* После умывания нанесите на ватный диск "
            "и протрите лицо. 1-2 раза в день."
        ),
    },
    {
        "name": "Laneige Water Sleeping Mask",
        "brand": "Laneige", "price_usd": 25.00,
        "concern": ["hydration"], "skin": ["dry", "combo", "sensitive"],
        "info_uz": (
            "🔬 *Nima bu?* Tungi uyqu maskasi — krem ko'rinishida.\n"
            "🎯 *Nima uchun?* Uxlayotganda teri chuqur namlaydi, "
            "ertalab teri yumshoq va porloq bo'ladi.\n"
            "📋 *Qanday ishlatiladi?* Kechqurun barcha parvarish oxirida "
            "yupqa qatlam surib qo'ying. Yuvmasdan uxlang."
        ),
        "info_ru": (
            "🔬 *Что это?* Ночная маска для сна — в виде крема.\n"
            "🎯 *Для чего?* Пока спите — кожа глубоко увлажняется, "
            "утром кожа мягкая и сияющая.\n"
            "📋 *Как использовать?* Вечером, последним шагом ухода, "
            "нанесите тонким слоем. Не смывайте, ложитесь спать."
        ),
    },
    {
        "name": "Beauty of Joseon Glow Serum",
        "brand": "Beauty of Joseon", "price_usd": 19.50,
        "concern": ["brightening", "dark_spots"], "skin": ["all"],
        "info_uz": (
            "🔬 *Nima bu?* Propolis va niasinamid asosidagi yorqinlik serumi.\n"
            "🎯 *Nima uchun?* Teri rangini tekislaydi, qora dog'larni oqlaydi, "
            "yuz porloq va sog'lom ko'rinadi.\n"
            "📋 *Qanday ishlatiladi?* Tonerdan keyin 2-3 tomchi kaftga olib "
            "yuzga patlab surib chiqing. Ertalab va kechqurun."
        ),
        "info_ru": (
            "🔬 *Что это?* Сыворотка сияния на основе прополиса и ниацинамида.\n"
            "🎯 *Для чего?* Выравнивает тон кожи, осветляет тёмные пятна, "
            "лицо выглядит сияющим и здоровым.\n"
            "📋 *Как использовать?* После тонера 2-3 капли на ладонь, "
            "вбейте в кожу. Утром и вечером."
        ),
    },
    {
        "name": "Dr.Jart+ Cicapair Tiger Grass Cream",
        "brand": "Dr.Jart+", "price_usd": 35.00,
        "concern": ["hydration", "sensitive"], "skin": ["dry", "sensitive"],
        "info_uz": (
            "🔬 *Nima bu?* Tiger o'ti (Centella) asosidagi tinchlantiruvchi krem.\n"
            "🎯 *Nima uchun?* Qizarish va yallig'lanishni kamaytiradi, "
            "sezgir va quruq terini tinchlantiradi, uzoq namlaydi.\n"
            "📋 *Qanday ishlatiladi?* Serumdan keyin yuzga va bo'yinga "
            "teng surib chiqing. Ertalab va kechqurun ishlatsa bo'ladi."
        ),
        "info_ru": (
            "🔬 *Что это?* Успокаивающий крем с экстрактом центеллы азиатской.\n"
            "🎯 *Для чего?* Снимает покраснения и воспаления, "
            "успокаивает чувствительную и сухую кожу, надолго увлажняет.\n"
            "📋 *Как использовать?* После сыворотки равномерно нанесите "
            "на лицо и шею. Можно утром и вечером."
        ),
    },
    {
        "name": "Anua Niacinamide 10% Serum",
        "brand": "Anua", "price_usd": 22.00,
        "concern": ["dark_spots", "brightening", "acne"], "skin": ["all"],
        "info_uz": (
            "🔬 *Nima bu?* 10% niasinamid (B3 vitamini) serumi.\n"
            "🎯 *Nima uchun?* Qora dog'larni oqlaydi, akne izlarini yo'q qiladi, "
            "teri rangini tekislaydi va teshikchalarni kichraytiradi.\n"
            "📋 *Qanday ishlatiladi?* Tonerdan keyin 3-4 tomchi yuzga "
            "patlab surib chiqing. Kuniga 1-2 marta, muntazam ishlating."
        ),
        "info_ru": (
            "🔬 *Что это?* Сыворотка с 10% ниацинамидом (витамин B3).\n"
            "🎯 *Для чего?* Осветляет тёмные пятна, убирает следы акне, "
            "выравнивает тон и сужает поры.\n"
            "📋 *Как использовать?* После тонера вбейте 3-4 капли в кожу. "
            "1-2 раза в день, применяйте регулярно."
        ),
    },
    {
        "name": "Sulwhasoo Concentrated Ginseng Cream",
        "brand": "Sulwhasoo", "price_usd": 95.00,
        "concern": ["aging"], "skin": ["dry", "combo"],
        "info_uz": (
            "🔬 *Nima bu?* Premium Koreya ginseng ekstraktli yaşartuvchi krem.\n"
            "🎯 *Nima uchun?* Ajinlarni kamaytiradi, teri elastikligini oshiradi, "
            "chuqur namlaydi. 40+ yoshga ideal.\n"
            "📋 *Qanday ishlatiladi?* Kechqurun mo'tabar miqdorda yuzga "
            "yuqoridan pastga qarab surib chiqing."
        ),
        "info_ru": (
            "🔬 *Что это?* Премиум омолаживающий крем с экстрактом корейского женьшеня.\n"
            "🎯 *Для чего?* Уменьшает морщины, повышает эластичность кожи, "
            "глубоко увлажняет. Идеально для 40+.\n"
            "📋 *Как использовать?* Вечером нанесите небольшое количество "
            "на лицо движениями снизу вверх."
        ),
    },
    {
        "name": "Missha Time Revolution Night Repair Ampoule",
        "brand": "Missha", "price_usd": 33.00,
        "concern": ["aging", "hydration"], "skin": ["dry", "combo"],
        "info_uz": (
            "🔬 *Nima bu?* Tungi ta'sirli anti-aging ampoule (konsentrat serum).\n"
            "🎯 *Nima uchun?* Uyqu paytida ajinlarni kamaytiradi, "
            "teri qayta tiklanadi, ertalab teri yoshroq ko'rinadi.\n"
            "📋 *Qanday ishlatiladi?* Faqat kechqurun — tonerdan keyin "
            "2-3 tomchi kaftga olib yuzga patlab surib chiqing."
        ),
        "info_ru": (
            "🔬 *Что это?* Ночная ампула (концентрат) против старения.\n"
            "🎯 *Для чего?* Пока вы спите — уменьшает морщины, "
            "кожа восстанавливается, утром выглядит моложе.\n"
            "📋 *Как использовать?* Только вечером — после тонера "
            "вбейте 2-3 капли в кожу."
        ),
    },
    {
        "name": "Innisfree Super Volcanic Pore Clay Mask",
        "brand": "Innisfree", "price_usd": 12.00,
        "concern": ["acne"], "skin": ["oily"],
        "info_uz": (
            "🔬 *Nima bu?* Vulkanik tuproq asosidagi chuqur tozalovchi maska.\n"
            "🎯 *Nima uchun?* Teshikchalarni chuqur tozalaydi, yog'lilikni kamaytiradi, "
            "akne oldini oladi.\n"
            "📋 *Qanday ishlatiladi?* Haftada 1-2 marta — yuzga surib "
            "10-15 daqiqa qoldirib yuvib tashlang."
        ),
        "info_ru": (
            "🔬 *Что это?* Маска для глубокого очищения с вулканической глиной.\n"
            "🎯 *Для чего?* Глубоко очищает поры, убирает жирность, "
            "предотвращает акне.\n"
            "📋 *Как использовать?* 1-2 раза в неделю — нанесите на лицо, "
            "оставьте на 10-15 минут, смойте."
        ),
    },
    {
        "name": "Klairs Supple Preparation Toner",
        "brand": "Klairs", "price_usd": 17.00,
        "concern": ["hydration"], "skin": ["dry", "sensitive", "combo"],
        "info_uz": (
            "🔬 *Nima bu?* Yumshoq, spirtsiz namlash toneri.\n"
            "🎯 *Nima uchun?* Terini keyingi parvarish mahsulotlarini "
            "qabul qilishga tayyorlaydi, chuqur namlaydi, qizarishni kamaytiradi.\n"
            "📋 *Qanday ishlatiladi?* Yuz yuvgandan keyin kaftga quyib "
            "yuzga patlab surib chiqing. Birinchi qadam sifatida."
        ),
        "info_ru": (
            "🔬 *Что это?* Мягкий безалкогольный увлажняющий тонер.\n"
            "🎯 *Для чего?* Подготавливает кожу к последующему уходу, "
            "глубоко увлажняет, снимает покраснения.\n"
            "📋 *Как использовать?* После умывания вбейте в кожу ладонями. "
            "Первый шаг ухода."
        ),
    },
]

CONCERN_MAP = {
    "🔴 Akne / Toshma":"acne",   "🌑 Qora dog'lar":"dark_spots",
    "⏳ Qarish belgilari":"aging","💦 Namlash":"hydration","✨ Yorqinlik":"brightening",
    "🔴 Акне / Прыщи":"acne",    "🌑 Тёмные пятна":"dark_spots",
    "⏳ Признаки старения":"aging","💦 Увлажнение":"hydration","✨ Сияние":"brightening",
}
SKIN_MAP = {
    "🫧 Yog'li":"oily","🌵 Quruq":"dry","☯️ Aralash":"combo","🌸 Sezgir":"sensitive",
    "🫧 Жирная":"oily","🌵 Сухая":"dry","☯️ Комбинированная":"combo","🌸 Чувствительная":"sensitive",
}
BUDGET_MAP = {
    "💵 100K–300K so'm":"low","💳 300K–700K so'm":"mid","💎 700K+ so'm":"high",
    "💵 100K–300K сум":"low","💳 300K–700K сум":"mid","💎 700K+ сум":"high",
}

# ══════════════════════════════════════════════════════════════════════════════
# PRICE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def calc_price_from_usd(price_usd: float) -> dict:
    product_uzs  = price_usd * USD_TO_UZS
    shipping_uzs = SHIPPING_USD * USD_TO_UZS
    subtotal     = product_uzs + shipping_uzs
    total        = subtotal * (1 + MARGIN)
    return {"product_uzs": int(product_uzs), "shipping_uzs": int(shipping_uzs), "total": int(total)}


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def budget_ok(total: int, budget: str) -> bool:
    return (budget == "low" and total <= 300_000) or \
           (budget == "mid" and total <= 700_000) or \
           (budget == "high")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT MATCHING
# ══════════════════════════════════════════════════════════════════════════════

def match_manual(skin: str, concern: str, budget: str) -> list[dict]:
    out = []
    for p in MANUAL_PRODUCTS:
        skin_ok    = skin in p["skin"] or "all" in p["skin"]
        concern_ok = concern in p["concern"]
        if not (skin_ok and concern_ok):
            continue
        pi = calc_price_from_usd(p["price_usd"])
        if budget_ok(pi["total"], budget):
            out.append({**p, "pi": pi, "source": "📦 Mening do'konim"})
    out.sort(key=lambda x: x["pi"]["total"])
    return out[:3]


def match_web(skin: str, concern: str, budget: str) -> list[dict]:
    raw = search_all_sites(skin, concern, max_per_site=2)
    out = []
    for r in raw:
        if not r.get("price_usd"):
            continue
        pi = calc_price_from_usd(r["price_usd"])
        if budget_ok(pi["total"], budget):
            out.append({
                "name":    r["name"],
                "brand":   r["source"],
                "price_usd": r["price_usd"],
                "link":    r["link"],
                "pi":      pi,
                "source":  f"🌐 {r['source']}",
                "desc_uz": f"{r['source']} saytidan topildi",
                "desc_ru": f"Найдено на {r['source']}",
            })
    out.sort(key=lambda x: x["pi"]["total"])
    return out[:5]

# ══════════════════════════════════════════════════════════════════════════════
# UI TEXTS
# ══════════════════════════════════════════════════════════════════════════════
T = {
    "welcome": {
        "uz": "🌸 *Kbeauty\\_diluz botiga xush kelibsiz!*\n\nKoreya go'zallik mahsulotlarini Uzbekistonga yetkazib beramiz 💄✨\n\nTilni tanlang:",
        "ru": "🌸 *Добро пожаловать в Kbeauty\\_diluz!*\n\nДоставляем корейскую косметику по Узбекистану 💄✨\n\nВыберите язык:",
    },
    "skin_type":   {"uz":"💧 *Teri turingiz?*",                  "ru":"💧 *Ваш тип кожи?*"},
    "skin_concern":{"uz":"🔍 *Asosiy muammongiz?*",              "ru":"🔍 *Главная проблема кожи?*"},
    "age":         {"uz":"🎂 *Yosh guruhingiz?*",                "ru":"🎂 *Ваш возраст?*"},
    "budget":      {"uz":"💰 *Byudjetingiz (yetkazish bilan)?*", "ru":"💰 *Ваш бюджет (с доставкой)?*"},
    "routine":     {"uz":"🧴 *Parvarish usuli?*",                "ru":"🧴 *Предпочтение ухода?*"},
    "searching":   {"uz":"⏳ Barcha saytlarda qidirilmoqda...",   "ru":"⏳ Ищем по всем сайтам..."},
    "no_results":  {"uz":"😔 Mos mahsulot topilmadi. /start bilan qaytadan urinib ko'ring.",
                    "ru":"😔 Подходящих товаров не найдено. Попробуйте /start заново."},
    "ask_name":    {"uz":"👤 *Ism va familiyangiz:*",            "ru":"👤 *Ваше имя и фамилия:*"},
    "ask_phone":   {"uz":"📱 *Telefon raqamingiz:*",             "ru":"📱 *Ваш номер телефона:*"},
    "ask_address": {"uz":"📍 *Yetkazish manzilingiz:*\n_(Shahar, ko'cha, uy)_",
                    "ru":"📍 *Адрес доставки:*\n_(Город, улица, дом)_"},
    "ask_birthdate":{"uz":"🎂 *Tug'ilgan sana:* _(15.03.1995)_", "ru":"🎂 *Дата рождения:* _(15.03.1995)_"},
    "thanks":      {
        "uz": f"✅ *Buyurtmangiz qabul qilindi!*\n\n📢 Kanalimizga obuna bo'ling: {CHANNEL_LINK}",
        "ru": f"✅ *Ваш заказ принят!*\n\n📢 Подпишитесь на наш канал: {CHANNEL_LINK}",
    },
}

SKIN_OPTS    = {"uz":["🫧 Yog'li","🌵 Quruq","☯️ Aralash","🌸 Sezgir"],
                "ru":["🫧 Жирная","🌵 Сухая","☯️ Комбинированная","🌸 Чувствительная"]}
CONCERN_OPTS = {"uz":["🔴 Akne / Toshma","🌑 Qora dog'lar","⏳ Qarish belgilari","💦 Namlash","✨ Yorqinlik"],
                "ru":["🔴 Акне / Прыщи","🌑 Тёмные пятна","⏳ Признаки старения","💦 Увлажнение","✨ Сияние"]}
AGE_OPTS     = {"uz":["👧 15-19","💃 20-29","👩 30-39","🌹 40+"],
                "ru":["👧 15-19","💃 20-29","👩 30-39","🌹 40+"]}
BUDGET_OPTS  = {"uz":["💵 100K–300K so'm","💳 300K–700K so'm","💎 700K+ so'm"],
                "ru":["💵 100K–300K сум","💳 300K–700K сум","💎 700K+ сум"]}
ROUTINE_OPTS = {"uz":["⚡ Oddiy (3 qadam)","🌟 To'liq (10 qadam)"],
                "ru":["⚡ Простой (3 шага)","🌟 Полный (10 шагов)"]}

# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARD HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def ikb(options: list, cols: int = 2) -> InlineKeyboardMarkup:
    rows = [options[i:i+cols] for i in range(0, len(options), cols)]
    return InlineKeyboardMarkup([[InlineKeyboardButton(o, callback_data=o) for o in r] for r in rows])


def product_card(p: dict, idx: int, lang: str) -> str:
    pi   = p["pi"]
    info = p.get(f"info_{lang}", p.get(f"desc_{lang}", ""))
    if lang == "uz":
        return (
            f"━━━━━━━━━━━━━━━\n"
            f"*{idx}. {p['name']}*\n\n"
            f"{info}\n\n"
            f"💵 *Narxi: {fmt(pi['total'])} so'm*\n"
            f"📢 [Kanalda ko'rish]({CHANNEL_LINK})\n"
        )
    else:
        return (
            f"━━━━━━━━━━━━━━━\n"
            f"*{idx}. {p['name']}*\n\n"
            f"{info}\n\n"
            f"💵 *Цена: {fmt(pi['total'])} сум*\n"
            f"📢 [Смотреть в канале]({CHANNEL_LINK})\n"
        )

# ══════════════════════════════════════════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(T["welcome"]["uz"], parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=ikb(["🇺🇿 O'zbekcha","🇷🇺 Русский"]))
    return LANG


async def set_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    lang = "uz" if "O'zbekcha" in q.data else "ru"
    ctx.user_data["lang"] = lang
    await q.edit_message_text(T["skin_type"][lang], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=ikb(SKIN_OPTS[lang]))
    return SKIN_TYPE


async def set_skin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    lang = ctx.user_data["lang"]
    ctx.user_data["skin"] = SKIN_MAP.get(q.data, "combo")
    await q.edit_message_text(T["skin_concern"][lang], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=ikb(CONCERN_OPTS[lang], cols=1))
    return SKIN_CONCERN


async def set_concern(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    lang = ctx.user_data["lang"]
    ctx.user_data["concern"] = CONCERN_MAP.get(q.data, "hydration")
    await q.edit_message_text(T["age"][lang], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=ikb(AGE_OPTS[lang]))
    return AGE


async def set_age(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    lang = ctx.user_data["lang"]
    ctx.user_data["age"] = q.data
    await q.edit_message_text(T["budget"][lang], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=ikb(BUDGET_OPTS[lang], cols=1))
    return BUDGET


async def set_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    lang = ctx.user_data["lang"]
    ctx.user_data["budget"] = BUDGET_MAP.get(q.data, "mid")
    await q.edit_message_text(T["routine"][lang], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=ikb(ROUTINE_OPTS[lang], cols=1))
    return ROUTINE


async def set_routine(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    lang   = ctx.user_data["lang"]
    skin   = ctx.user_data["skin"]
    concern= ctx.user_data["concern"]
    budget = ctx.user_data["budget"]

    status = await q.edit_message_text(T["searching"][lang])

    # Run manual + web search in parallel
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        web_future = loop.run_in_executor(pool, match_web, skin, concern, budget)
        manual     = match_manual(skin, concern, budget)
        web        = await web_future

    # Combine: manual first, then web results
    all_products = manual + [p for p in web if p["name"] not in {m["name"] for m in manual}]
    ctx.user_data["products"] = all_products[:8]

    if not all_products:
        await status.edit_text(T["no_results"][lang])
        return ConversationHandler.END

    # Build product list message
    header = "🌸 *Siz uchun topilgan mahsulotlar:*\n" if lang == "uz" else "🌸 *Найденные товары для вас:*\n"
    # Show sources summary
    sources = list(dict.fromkeys([p["source"] for p in all_products]))
    src_line = ("📍 Manbalar: " if lang == "uz" else "📍 Источники: ") + " · ".join(sources) + "\n"

    cards = "\n".join([product_card(p, i+1, lang) for i, p in enumerate(all_products[:8])])

    order_btn  = "✅ Buyurtma berish" if lang == "uz" else "✅ Оформить заказ"
    restart_btn= "🔄 Qaytadan" if lang == "uz" else "🔄 Начать заново"

    await status.edit_text(
        header + src_line + "\n" + cards,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ikb([order_btn, restart_btn], cols=1),
        disable_web_page_preview=True,
    )
    return ORDER_CONFIRM


async def order_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    lang = ctx.user_data["lang"]
    if "Qaytadan" in q.data or "заново" in q.data:
        await q.edit_message_text("/start bosing" if lang == "uz" else "Нажмите /start")
        return ConversationHandler.END
    await q.edit_message_text(T["ask_name"][lang], parse_mode=ParseMode.MARKDOWN)
    return NAME


async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = ctx.user_data["lang"]
    ctx.user_data["customer_name"] = update.message.text
    btn_label = "📱 Raqamni yuborish" if lang == "uz" else "📱 Отправить номер"
    await update.message.reply_text(T["ask_phone"][lang], parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(btn_label, request_contact=True)]],
                                         resize_keyboard=True, one_time_keyboard=True))
    return PHONE


async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = ctx.user_data["lang"]
    ctx.user_data["phone"] = update.message.contact.phone_number if update.message.contact else update.message.text
    await update.message.reply_text(T["ask_address"][lang], parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=ReplyKeyboardRemove())
    return ADDRESS


async def get_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = ctx.user_data["lang"]
    ctx.user_data["address"] = update.message.text
    await update.message.reply_text(T["ask_birthdate"][lang], parse_mode=ParseMode.MARKDOWN)
    return BIRTHDATE


async def get_birthdate(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = ctx.user_data["lang"]
    ctx.user_data["birthdate"] = update.message.text
    payment_text = (
        f"💳 *To'lov:*\n\n🏦 Humo: `{HUMO_CARD}`\n\n"
        f"To'lovdan so'ng *chek rasmini* yuboring 📸"
        if lang == "uz" else
        f"💳 *Оплата:*\n\n🏦 Humo: `{HUMO_CARD}`\n\n"
        f"После оплаты отправьте *скриншот чека* 📸"
    )
    await update.message.reply_text(payment_text, parse_mode=ParseMode.MARKDOWN)
    return PAYMENT


async def get_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = ctx.user_data["lang"]
    ud   = ctx.user_data
    products = ud.get("products", [])

    # Build order for admin
    lines = "\n".join([f"• {p['name']} ({p.get('source','')}) — {fmt(p['pi']['total'])} so'm"
                       for p in products])
    total_all = sum(p["pi"]["total"] for p in products)

    admin_msg = (
        f"🛒 *YANGI BUYURTMA*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {ud.get('customer_name')}\n"
        f"📱 {ud.get('phone')}\n"
        f"📍 {ud.get('address')}\n"
        f"🎂 {ud.get('birthdate')}\n"
        f"🌍 {'O\'zbekcha' if lang=='uz' else 'Русский'}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🧴 Teri: {ud.get('skin')} | Muammo: {ud.get('concern')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 Mahsulotlar:\n{lines}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 *Jami: {fmt(total_all)} so'm*\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    if ADMIN_CHAT_ID:
        try:
            if update.message.photo:
                await ctx.bot.send_photo(ADMIN_CHAT_ID, update.message.photo[-1].file_id,
                                         caption=admin_msg, parse_mode=ParseMode.MARKDOWN)
            else:
                await ctx.bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error("Admin notify failed: %s", e)

    confirm = "✅ To'lov qabul qilindi! Tez orada bog'lanamiz 🌸" if lang == "uz" \
              else "✅ Оплата получена! Свяжемся скоро 🌸"
    await update.message.reply_text(confirm)
    await asyncio.sleep(1)
    await update.message.reply_text(T["thanks"][lang], parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = ctx.user_data.get("lang", "uz")
    msg  = "Bekor qilindi. /start" if lang == "uz" else "Отменено. /start"
    await update.message.reply_text(msg)
    return ConversationHandler.END


async def admin_setup(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"✅ Sizning admin Chat ID: `{update.message.chat_id}`\n\n"
        f"Buni ADMIN\\_CHAT\\_ID ga qo'ying.",
        parse_mode=ParseMode.MARKDOWN)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:         [CallbackQueryHandler(set_lang)],
            SKIN_TYPE:    [CallbackQueryHandler(set_skin)],
            SKIN_CONCERN: [CallbackQueryHandler(set_concern)],
            AGE:          [CallbackQueryHandler(set_age)],
            BUDGET:       [CallbackQueryHandler(set_budget)],
            ROUTINE:      [CallbackQueryHandler(set_routine)],
            ORDER_CONFIRM:[CallbackQueryHandler(order_confirm)],
            NAME:         [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE:        [MessageHandler(filters.CONTACT | filters.TEXT, get_phone)],
            ADDRESS:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            BIRTHDATE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthdate)],
            PAYMENT:      [MessageHandler(filters.PHOTO | filters.TEXT, get_payment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("adminsetup", admin_setup))

    logger.info("🌸 Kbeauty_diluz bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

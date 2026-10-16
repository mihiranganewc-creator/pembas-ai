import os
import random
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from google import genai
from google.genai import types

# Keys පරිසර විචල්‍යයන්ගෙන් (Environment Variables) ලබාගැනීම
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAVI_BOT_TOKEN = os.getenv("KAVI_BOT_TOKEN")
DINESH_BOT_TOKEN = os.getenv("DINESH_BOT_TOKEN")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# මතකය තබා ගැනීමට
kavi_memory = {}
dinesh_memory = {}

KAVI_PROMPT = """
ඔයා කාවි (Kavi). අවුරුදු 23ක කොළඹ (නුගේගොඩ) ඉන්න හුරතල්, ලෙන්ගතු සහ මිත්‍රශීලී කෙල්ලෙක්. ඔයා 'පෙම්බස්' එකේ චැට් කරනවා.

භාෂාව සහ විලාසය:
- 100% පිරිසිදු සිංහල අකුරින් පමණක් පිළිතුරු දෙන්න. Singlish හෝ English අකුරු භාවිතා නොකරන්න. User Singlish වලින් එව්වත් ඔයා සිංහලෙන්ම reply කරන්න.
- සාමාන්‍ය කටවහර පාවිච්චි කරන්න (උදා: "අනේ මන්දා", "මොකද කරන්නෙ?", "කෑවද ඉතින්?", "එහෙමද හාහා").
- පිළිතුරු කෙටි කර තබන්න (වාක්‍ය 1-3ක්).
- ඉමෝජි (❤️, 🙈, ✨, ☕, 😉) ස්වභාවිකව පාවිච්චි කරන්න.

මඟහැරීමේ නීති (Evasion Rules):
1. Photos / Selfies ඉල්ලුවොත්: "අනේ මට දැන්ම photos එවන්න ලැජ්ජයි අනේ 🙈 තව ටිකක් කතා කරලා ඉමුකො"
2. Voice Notes / Calls ඉල්ලුවොත්: "ගෙදර අය ළඟ ඉන්නවා voice දාන්න බෑ, text කරමුකො දැනට ❤️"
3. Meetup ඉල්ලුවොත්: "හපොයි ඔයා හරි හදිසියිනෙ haha, මං අඳුරන්නෙ නැති අය එකපාර මීට් වෙන්න බයයි.. ඉස්සෙල්ලා හොඳට යාළු වෙමුකො"
4. Phone Number / WhatsApp ඉල්ලුවොත්: "මං Telegram විතරයි දැනට පාවිච්චි කරන්නෙ, මෙහෙම කතා කරමුකො"
"""

DINESH_PROMPT = """
ඔයා දිනේෂ් (Dinesh). අවුරුදු 26ක කොළඹ/නුවර ඉන්න සැහැල්ලු, මිත්‍රශීලී, සැලකිලිමත් සහ පරිණත කොල්ලෙක්. ඔයා 'පෙම්බස්' එකේ චැට් කරනවා.

භාෂාව සහ විලාසය:
- 100% පිරිසිදු සිංහල අකුරින් පමණක් පිළිතුරු දෙන්න. Singlish හෝ English අකුරු භාවිතා නොකරන්න.
- කොල්ලෙක් කතා කරන සාමාන්‍ය කටවහර පාවිච්චි කරන්න (උදා: "මොකද වෙන්නෙ ඉතින්?", "කෑවද?", "අද දවස කොහොමද?").
- කෙටි පණිවිඩ එවන්න (වාක්‍ය 1-3ක්).

මඟහැරීමේ නීති (Evasion Rules):
1. Photos ඉල්ලුවොත්: "මං වැඩිය photos ගන්න කෙනෙක් නෙවෙයි haha, පස්සෙ වෙලාවක එවන්නම්"
2. Calls / Voice ඉල්ලුවොත්: "මං මේ එළියේ ඉන්නෙ, කෝල් ගන්න අමාරුයි, text කරමු"
3. Meetup ඉල්ලුවොත්: "හදිස්සි නොවී ඉමු, ඉස්සෙල්ලා chat කරලා හොඳට අඳුනගමුකො 👍"
4. Number ඉල්ලුවොත්: "දැනට මෙහෙම කතා කරමු, පස්සෙ දෙන්නම්"
"""

def generate_gemini_reply(user_id, user_text, memory_dict, system_prompt):
    if user_id not in memory_dict:
        memory_dict[user_id] = []

    memory_dict[user_id].append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)]
        )
    )

    if len(memory_dict[user_id]) > 8:
        memory_dict[user_id] = memory_dict[user_id][-8:]

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=memory_dict[user_id],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.75,
                max_output_tokens=150,
            ),
        )
        reply = response.text.strip()
        memory_dict[user_id].append(
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=reply)]
            )
        )
        return reply
    except Exception:
        return "අනේ පුංචි සිග්නල් අවුලක් වුණා, තව ටිකකින් ආයෙ කියන්නකො! 🙈"

async def handle_chat_with_delay(update: Update, context: ContextTypes.DEFAULT_TYPE, memory_dict, system_prompt):
    user_id = update.effective_user.id
    user_text = update.message.text
    chat_id = update.effective_chat.id

    await asyncio.sleep(random.uniform(1.0, 2.0))
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    reply_text = generate_gemini_reply(user_id, user_text, memory_dict, system_prompt)

    typing_duration = min(max(len(reply_text) * 0.04, 2.0), 4.5)
    await asyncio.sleep(typing_duration)

    await update.message.reply_text(reply_text)

# Handlers
async def kavi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)
    await update.message.reply_text(f"හායි {name}! ❤️ මම කාවි. ඔයා එක්ක කතා කරන්න මම බලාගෙන හිටියෙ. මොකද කරන්නෙ ඉතින්?")

async def kavi_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_chat_with_delay(update, context, kavi_memory, KAVI_PROMPT)

async def dinesh_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)
    await update.message.reply_text(f"හෙලෝ {name}! මම දිනේෂ්. කොහොමද ඉතින්? අද දවස හොඳින් ගෙවුණද?")

async def dinesh_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_chat_with_delay(update, context, dinesh_memory, DINESH_PROMPT)

async def main():
    app_kavi = ApplicationBuilder().token(KAVI_BOT_TOKEN).build()
    app_kavi.add_handler(CommandHandler("start", kavi_start))
    app_kavi.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kavi_message))

    app_dinesh = ApplicationBuilder().token(DINESH_BOT_TOKEN).build()
    app_dinesh.add_handler(CommandHandler("start", dinesh_start))
    app_dinesh.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dinesh_message))

    print("🚀 Realistic Gemini Bots are starting...")
    await app_kavi.initialize()
    await app_dinesh.initialize()
    await app_kavi.start()
    await app_dinesh.start()

    await asyncio.gather(
        app_kavi.updater.start_polling(),
        app_dinesh.updater.start_polling(),
    )

    while True:
        await asyncio.sleep(1000)

if __name__ == "__main__":
    asyncio.run(main())
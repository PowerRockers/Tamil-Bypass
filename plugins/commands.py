import contextlib
import datetime
import logging

from validators import domain
from config import (
    ADMINS,
    LOG_CHANNEL,
    SOURCE_CODE,
    WELCOME_IMAGE,
)
from database import db
from database.users import get_user, is_user_exist, total_users_count, update_user_info
from helpers import temp
from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.filters import private_use
from translation import *
from utils import extract_link, get_me_button, get_size

logger = logging.getLogger(__name__)

user_commands = [
    "mdisk_api",
    "shortener_api",
    "header",
    "footer",
    "username",
    "banner_image",
    "base_site",
    "me",
]

@Client.on_message(filters.command("start") & filters.private & filters.incoming)
@private_use
async def start(c: Client, m: Message):
    NEW_USER_REPLY_MARKUP = [
        [
            InlineKeyboardButton("Ban", callback_data=f"ban#{m.from_user.id}"),
            InlineKeyboardButton("Close", callback_data="delete"),
        ]
    ]
    is_user = await is_user_exist(m.from_user.id)

    reply_markup = InlineKeyboardMarkup(NEW_USER_REPLY_MARKUP)

    if not is_user and LOG_CHANNEL:
        await c.send_message(
            LOG_CHANNEL,
            f"#NewUser\n\nUser ID: `{m.from_user.id}`\nName: {m.from_user.mention}",
            reply_markup=reply_markup,
        )
    new_user = await get_user(m.from_user.id)
    t = START_MESSAGE.format(
        m.from_user.mention, new_user["method"], new_user["base_site"]
    )

    if WELCOME_IMAGE:
        return await m.reply_photo(
            photo=WELCOME_IMAGE, caption=t, reply_markup=START_MESSAGE_REPLY_MARKUP
        )
    await m.reply_text(
        t, reply_markup=START_MESSAGE_REPLY_MARKUP, disable_web_page_preview=True
    )


@Client.on_message(filters.command("help") & filters.private)
@private_use
async def help_command(c, m: Message):
    s = HELP_MESSAGE.format(
        firstname=temp.FIRST_NAME,
        username=temp.BOT_USERNAME,
        repo=SOURCE_CODE,
        owner="@ask_admin001",
    )

    if WELCOME_IMAGE:
        return await m.reply_photo(
            photo=WELCOME_IMAGE, caption=s, reply_markup=HELP_REPLY_MARKUP
        )
    await m.reply_text(s, reply_markup=HELP_REPLY_MARKUP, disable_web_page_preview=True)


@Client.on_message(filters.command("about"))
@private_use
async def about_command(c, m: Message):
    reply_markup = ABOUT_REPLY_MARKUP

    bot = await c.get_me()
    if WELCOME_IMAGE:
        return await m.reply_photo(
            photo=WELCOME_IMAGE,
            caption=ABOUT_TEXT.format(bot.mention(style="md")),
            reply_markup=reply_markup,
        )
    await m.reply_text(
        ABOUT_TEXT.format(bot.mention(style="md")),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )

@Client.on_message(filters.command("restart") & filters.user(ADMINS) & filters.private)
@private_use
async def restart_handler(c: Client, m: Message):
    RESTARTE_MARKUP = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Sure", callback_data="restart"),
                InlineKeyboardButton("Disable", callback_data="delete"),
            ]
        ]
    )
    await m.reply(
        "Are you sure you want to restart / re-deploy the server?",
        reply_markup=RESTARTE_MARKUP,
    )


@Client.on_message(filters.command("stats") & filters.private)
@private_use
async def stats_handler(c: Client, m: Message):
    try:
        txt = await m.reply("`Fetching stats...`")
        size = await db.get_db_size()
        free = 536870912 - size
        size = await get_size(size)
        free = await get_size(free)
        link_stats = await db.get_bot_stats()
        runtime = datetime.datetime.now()

        t = runtime - temp.START_TIME
        runtime = str(datetime.timedelta(seconds=t.seconds))
        total_users = await total_users_count()

        msg = f"""
**- Total Users:** `{total_users}`
**- Total Posts Sent:** `{link_stats['posts']}`
**- Total Links Shortened:** `{link_stats['links']}`
**- Total Mdisk Links Shortened:** `{link_stats['mdisk_links']}`
**- Total Shortener Links Shortened:** `{link_stats['shortener_links']}`
**- Used Storage:** `{size}`
**- Total Free Storage:** `{free}`

**- Runtime:** `{runtime}`
    """


        return await txt.edit(msg)
    except Exception as e:
        logging.error(e, exc_info=True)


@Client.on_message(filters.command("logs") & filters.user(ADMINS) & filters.private)
@private_use
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document("TelegramBot.log")
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command("me") & filters.private)
@private_use
async def me_handler(bot, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)

    user_id = m.from_user.id
    user = await get_user(user_id)
    res = USER_ABOUT_MESSAGE.format(
        base_site=user["base_site"],
        method=user["method"],
        shortener_api=user["shortener_api"],
        mdisk_api=user["mdisk_api"],
        username=user["username"],
        header_text=user["header_text"].replace(r"\n", "\n")
        if user["header_text"]
        else None,
        footer_text=user["footer_text"].replace(r"\n", "\n")
        if user["footer_text"]
        else None,
        banner_image=user["banner_image"],
    )

    buttons = await get_me_button(user)
    reply_markup = InlineKeyboardMarkup(buttons)
    return await m.reply_text(
        res, reply_markup=reply_markup, disable_web_page_preview=True
    )

@Client.on_message(filters.command("ban") & filters.private & filters.user(ADMINS))
@private_use
async def banned_user_handler(c: Client, m: Message):
    try:
        if len(m.command) == 1:
            x = "".join(f"- `{user}`\n" for user in temp.BANNED_USERS)
            txt = BANNED_USER_TXT.format(users=x or "None")
            await m.reply(txt)
        elif len(m.command) == 2:
            user_id = m.command[1]
            user = await get_user(int(user_id))
            if user:
                if not user["banned"]:
                    await update_user_info(user_id, {"banned": True})
                    with contextlib.suppress(Exception):
                        temp.BANNED_USERS.append(int(user_id))
                        await c.send_message(
                            user_id, "You are now banned from the bot by Admin"
                        )
                    await m.reply(
                        f"User [`{user_id}`] has been banned from the bot. To Unban. `/unban {user_id}`"
                    )

                else:
                    await m.reply("User is already banned")
            else:
                await m.reply("User doesn't exist")
    except Exception as e:
        logging.exception(e, exc_info=True)


@Client.on_message(filters.command("unban") & filters.private & filters.user(ADMINS))
@private_use
async def unban_user_handler(c: Client, m: Message):
    try:
        if len(m.command) == 1:
            x = "".join(f"- `{user}`\n" for user in temp.BANNED_USERS)
            txt = BANNED_USER_TXT.format(users=x or "None")
            await m.reply(txt)
        elif len(m.command) == 2:
            user_id = m.command[1]
            user = await get_user(int(user_id))
            if user:
                if user["banned"]:
                    await update_user_info(user_id, {"banned": False})
                    with contextlib.suppress(Exception):
                        temp.BANNED_USERS.remove(int(user_id))
                        await c.send_message(
                            user_id,
                            "You are now free to use the bot. You have been unbanned by the Admin",
                        )

                    await m.reply(
                        f"User [`{user_id}`] has been unbanned from the bot. To ban. `/ban {user_id}`"
                    )

                else:
                    await m.reply("User is not banned yet")
            else:
                await m.reply("User doesn't exist")
    except Exception as e:
        logging.exception(e, exc_info=True)


@Client.on_message(filters.command("info") & filters.private & filters.user(ADMINS))
@private_use
async def get_user_info_handler(c: Client, m: Message):
    try:
        if len(m.command) != 2:
            return await m.reply_text("Wrong Input!!\n`/info user_id`")
        user = await get_user(int(m.command[1]))
        if not user:
            return await m.reply_text("User doesn't exist")
        res = USER_ABOUT_MESSAGE.format(
            base_site=user["base_site"],
            method=user["method"],
            shortener_api="This is something secret",
            mdisk_api="This is something secret",
            username=user["username"],
            header_text=user["header_text"].replace("\n", "\n")
            if user["header_text"]
            else None,
            footer_text=user["footer_text"].replace("\n", "\n")
            if user["footer_text"]
            else None,
            banner_image=user["banner_image"],
        )

        res = f'User: `{user["user_id"]}`\n{res}'
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Ban", callback_data=f'ban#{user["user_id"]}'),
                    InlineKeyboardButton("Close", callback_data="delete"),
                ]
            ]
        )

        return await m.reply_text(res, reply_markup=reply_markup, quote=True)
    except Exception as e:
        await m.reply_text(e)
        logging.error(e)

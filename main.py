import os
import re
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv


load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = int(
    os.getenv(
        "GUILD_ID",
        "1423304327107182704",
    )
)

OPERATIONS_ROLE_ID = int(
    os.getenv(
        "OPERATIONS_ROLE_ID",
        "1531252911483519126",
    )
)

TIMEZONE_NAME = os.getenv(
    "TIMEZONE",
    "Asia/Kolkata",
)


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")

if not GUILD_ID:
    raise RuntimeError("GUILD_ID is missing.")


try:
    LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)
except Exception:
    LOCAL_TZ = timezone.utc


BRAND_COLOR = 0x003B7A


MODMAIL_STAFF_ROLE_ID = 1531252969654321343
TICKET_CATEGORY_ID = 1530230686273896620
CLOSED_TICKET_LOG_CHANNEL_ID = 1531253717980938301
DEPARTURE_CHANNEL_ID = 1531253179054821396


LOGO = "<:tail:1526303107708092567>"
FLAG = "<:flag:1530228152649908344>"
ANNOUNCE = "<:announce:1531243911211647018>"
SCHEDULE = "<:schedule:1531243944908947617>"
NETWORK = "<:network:1531243969739227208>"
HELPDESK = "<:personnel:1531244023673651200>"
MAIL = "<:information_ITA:1531244145002152027>"
ROBLOX = "<:roblox:1531244097170440262>"
INFORMATION = "<:information_ITA:1531244145002152027>"
VR_CROSS = "<:Cross:1531244067965370369>"
VR_TICK = "<:tick:1531244120490770432>"
POINTER = "<:notification:1531244167500664882>"
FLIGHT = "<:tail:1526303107708092567>"

DEVELOPMENT = "<:development:1531244047010889910>"
PERSONNEL = "<:personnel:1531244023673651200>"
FOLDER = "<:folder:1531244001758548139>"
LOCK_EMOJI = "<:Lock:1530207501117685860>"
UNLOCK_EMOJI = "<:Unlock:1530206619617464351>"


ITALIAN_NAMES = [
    "Alessandro",
    "Andrea",
    "Antonio",
    "Chiara",
    "Elena",
    "Francesca",
    "Giulia",
    "Lorenzo",
    "Marco",
    "Matteo",
    "Sofia",
    "Vittoria",
]


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.reactions = True


bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(".", ";"),
    intents=intents,
    help_command=None,
    case_insensitive=True,
)


db = sqlite3.connect("ita_customer_core.db")
db.row_factory = sqlite3.Row
cursor = db.cursor()


cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        channel_id INTEGER,
        category TEXT NOT NULL,
        opened_at INTEGER NOT NULL,
        opened_by_id INTEGER NOT NULL,
        closed_at INTEGER,
        closed_by_id INTEGER,
        status TEXT NOT NULL DEFAULT 'open'
    )
    """
)


cursor.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS one_open_ticket_per_user
    ON tickets(user_id)
    WHERE status = 'open'
    """
)


cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS banned_users (
        user_id INTEGER PRIMARY KEY,
        banned_by_id INTEGER NOT NULL,
        banned_at INTEGER NOT NULL
    )
    """
)


cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS flights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER UNIQUE NOT NULL,
        event_url TEXT NOT NULL,
        flight_number TEXT NOT NULL,
        start_timestamp INTEGER NOT NULL,
        game_link TEXT NOT NULL,
        route TEXT NOT NULL,
        aircraft TEXT NOT NULL,
        scheduled_by_id INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'scheduled'
    )
    """
)


cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS bot_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """
)


db.commit()


def utc_now_ts() -> int:
    return int(
        datetime.now(
            timezone.utc,
        ).timestamp()
    )


def make_embed(
    title: str,
    description: str = "",
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=BRAND_COLOR,
        timestamp=discord.utils.utcnow(),
    )

    embed.set_footer(
        text="ITA Airways Customer Core",
    )

    return embed


def clean_channel_name(name: str) -> str:
    name = re.sub(
        r"[^a-z0-9-]",
        "-",
        name.lower().strip(),
    )

    return (
        re.sub(
            r"-+",
            "-",
            name,
        ).strip("-")[:70]
        or "passenger"
    )


def has_role(
    member: discord.Member,
    role_id: int,
) -> bool:
    return any(
        role.id == role_id
        for role in member.roles
    )


def is_modmail_staff(
    member: discord.Member,
) -> bool:
    return has_role(
        member,
        MODMAIL_STAFF_ROLE_ID,
    )


def is_operations_staff(
    member: discord.Member,
) -> bool:
    if (
        OPERATIONS_ROLE_ID
        and has_role(
            member,
            OPERATIONS_ROLE_ID,
        )
    ):
        return True

    return (
        member.guild_permissions.manage_events
        or member.guild_permissions.manage_guild
    )


def staff_rank(
    member: discord.Member,
) -> str:
    roles = [
        role
        for role in member.roles
        if role != member.guild.default_role
        and not role.managed
    ]

    return (
        roles[-1].name
        if roles
        else "Helpline Agent"
    )


def get_open_ticket_for_user(
    user_id: int,
):
    cursor.execute(
        """
        SELECT *
        FROM tickets
        WHERE user_id = ?
          AND status = 'open'
        """,
        (user_id,),
    )

    return cursor.fetchone()


def get_open_ticket_for_channel(
    channel_id: int,
):
    cursor.execute(
        """
        SELECT *
        FROM tickets
        WHERE channel_id = ?
          AND status = 'open'
        """,
        (channel_id,),
    )

    return cursor.fetchone()


def is_banned(
    user_id: int,
) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM banned_users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    return cursor.fetchone() is not None


async def add_reaction_safe(
    message: discord.Message,
    emoji_text: str,
):
    try:
        await message.add_reaction(
            discord.PartialEmoji.from_str(
                emoji_text,
            )
        )
    except Exception:
        pass


async def send_passenger_message_to_ticket(
    message: discord.Message,
    ticket_row,
):
    guild = bot.get_guild(GUILD_ID)

    if not guild:
        return False

    channel = guild.get_channel(
        ticket_row["channel_id"]
    )

    if not channel:
        return False

    description = (
        message.content.strip()
        or "*No text was included.*"
    )

    if message.attachments:
        description += "\n\n" + "\n".join(
            f"[Attachment {index}]({attachment.url})"
            for index, attachment in enumerate(
                message.attachments,
                start=1,
            )
        )

    embed = make_embed(
        f"{MAIL} Passenger Message",
        description,
    )

    embed.set_author(
        name=(
            f"{message.author} • "
            f"{message.author.id}"
        ),
        icon_url=message.author.display_avatar.url,
    )

    await channel.send(
        embed=embed,
    )

    return True


pending_first_messages: dict[
    int,
    discord.Message,
] = {}


async def create_ticket(
    user,
    category_name: str,
    opened_by_id: int,
):
    guild = bot.get_guild(GUILD_ID)

    if not guild:
        raise RuntimeError(
            "Configured ITA Airways server not found."
        )

    if is_banned(user.id):
        raise RuntimeError(
            "This user is banned."
        )

    existing = get_open_ticket_for_user(
        user.id
    )

    if existing:
        channel = guild.get_channel(
            existing["channel_id"]
        )

        if channel:
            return channel

    category = guild.get_channel(
        TICKET_CATEGORY_ID
    )

    staff_role = guild.get_role(
        MODMAIL_STAFF_ROLE_ID
    )

    if not isinstance(
        category,
        discord.CategoryChannel,
    ):
        raise RuntimeError(
            "Ticket category not found."
        )

    if not staff_role:
        raise RuntimeError(
            "ModMail staff role not found."
        )

    overwrites = {
        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False,
            ),

        staff_role:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
    }

    if guild.me:
        overwrites[guild.me] = (
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            )
        )

    channel = await guild.create_text_channel(
        name=(
            f"ticket-"
            f"{clean_channel_name(user.name)}-"
            f"{str(user.id)[-4:]}"
        ),
        category=category,
        overwrites=overwrites,
        topic=(
            f"ITA Airways ModMail | "
            f"User ID: {user.id} | "
            f"Category: {category_name}"
        ),
        reason=(
            f"ModMail ticket opened for {user}"
        ),
    )

    opened_at = utc_now_ts()

    cursor.execute(
        """
        INSERT INTO tickets (
            user_id,
            channel_id,
            category,
            opened_at,
            opened_by_id,
            status
        )
        VALUES (?, ?, ?, ?, ?, 'open')
        """,
        (
            user.id,
            channel.id,
            category_name,
            opened_at,
            opened_by_id,
        ),
    )

    db.commit()

    embed = make_embed(
        f"{HELPDESK} New Helpline Ticket",
        (
            f"{POINTER} A new passenger has connected."
            "\n\n"
            f"**Passenger:** {user.mention} "
            f"(`{user.id}`)\n"
            f"**Category:** {category_name}\n"
            f"**Opened:** <t:{opened_at}:F>\n"
            f"**Opened By:** <@{opened_by_id}>"
        ),
    )

    embed.set_thumbnail(
        url=user.display_avatar.url,
    )

    await channel.send(
        content=staff_role.mention,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            roles=True,
        ),
    )

    return channel


class TicketCategorySelect(
    discord.ui.Select,
):
    def __init__(
        self,
        user_id: int,
    ):
        self.user_id = user_id

        options = [
            discord.SelectOption(
                label="Recruiting Department",
                value="Recruiting Department",
            ),
            discord.SelectOption(
                label="Operating Department",
                value="Operating Department",
            ),
            discord.SelectOption(
                label="Customer Service Department",
                value="Customer Service Department",
            ),
        ]

        super().__init__(
            placeholder=(
                "Choose a helpline department"
            ),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        if (
            interaction.user.id
            != self.user_id
        ):
            await interaction.response.send_message(
                embed=make_embed(
                    f"{VR_CROSS} Not Available",
                    (
                        "This request belongs to "
                        "another passenger."
                    ),
                ),
                ephemeral=True,
            )

            return

        await interaction.response.defer()

        category = self.values[0]

        first_message = (
            pending_first_messages.pop(
                self.user_id,
                None,
            )
        )

        if is_banned(self.user_id):
            await interaction.edit_original_response(
                embed=make_embed(
                    f"{VR_CROSS} Connection Refused",
                    (
                        f"{POINTER} You are currently "
                        "unable to open a ticket."
                    ),
                ),
                view=None,
            )

            return

        if get_open_ticket_for_user(
            self.user_id
        ):
            await interaction.edit_original_response(
                embed=make_embed(
                    f"{NETWORK} Already Connected",
                    (
                        f"{POINTER} You already have "
                        "an active ticket."
                    ),
                ),
                view=None,
            )

            return

        try:
            await create_ticket(
                interaction.user,
                category,
                interaction.user.id,
            )

        except Exception as exc:
            await interaction.edit_original_response(
                embed=make_embed(
                    f"{VR_CROSS} Connection Failed",
                    f"`{exc}`",
                ),
                view=None,
            )

            return

        await interaction.edit_original_response(
            embed=make_embed(
                f"{NETWORK} Connected",
                (
                    f"{POINTER} You are now connected "
                    "to the ITA Airways system. One of "
                    "our helpline agents will be "
                    "assisting you momentarily."
                ),
            ),
            view=None,
        )

        if first_message:
            ticket = get_open_ticket_for_user(
                self.user_id
            )

            if ticket:
                await send_passenger_message_to_ticket(
                    first_message,
                    ticket,
                )

                await add_reaction_safe(
                    first_message,
                    VR_TICK,
                )


class TicketCategoryView(
    discord.ui.View,
):
    def __init__(
        self,
        user_id: int,
    ):
        super().__init__(
            timeout=300,
        )

        self.add_item(
            TicketCategorySelect(
                user_id,
            )
        )


class TicketConfirmView(
    discord.ui.View,
):
    def __init__(
        self,
        user_id: int,
    ):
        super().__init__(
            timeout=300,
        )

        self.user_id = user_id

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.success,
        emoji=discord.PartialEmoji.from_str(
            VR_TICK
        ),
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if (
            interaction.user.id
            != self.user_id
        ):
            await interaction.response.send_message(
                embed=make_embed(
                    f"{VR_CROSS} Not Available",
                    (
                        "This request belongs to "
                        "another passenger."
                    ),
                ),
                ephemeral=True,
            )

            return

        await interaction.response.edit_message(
            embed=make_embed(
                f"{HELPDESK} Helpline Department",
                (
                    f"{POINTER} Amazing, now please "
                    "choose the helpline department "
                    "you would like to connect with "
                    "to resolve your query."
                ),
            ),
            view=TicketCategoryView(
                self.user_id
            ),
        )

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji=discord.PartialEmoji.from_str(
            VR_CROSS
        ),
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if (
            interaction.user.id
            != self.user_id
        ):
            await interaction.response.send_message(
                embed=make_embed(
                    f"{VR_CROSS} Not Available",
                    (
                        "This request belongs to "
                        "another passenger."
                    ),
                ),
                ephemeral=True,
            )

            return

        pending_first_messages.pop(
            self.user_id,
            None,
        )

        await interaction.response.edit_message(
            embed=make_embed(
                f"{VR_CROSS} Connection Cancelled",
                (
                    f"{POINTER} Your ticket was "
                    "not created."
                ),
            ),
            view=None,
        )
        async def require_modmail_staff(
    ctx: commands.Context,
) -> bool:
    if (
        not isinstance(
            ctx.author,
            discord.Member,
        )
        or not is_modmail_staff(
            ctx.author
        )
    ):
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Permission Denied",
                (
                    "Only authorised ITA Airways "
                    "helpline staff may use this "
                    "command."
                ),
            )
        )

        return False

    return True


async def require_ticket_channel(
    ctx: commands.Context,
):
    ticket = get_open_ticket_for_channel(
        ctx.channel.id
    )

    if not ticket:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Ticket Required",
                (
                    "This command can only be used "
                    "inside an active ticket channel."
                ),
            )
        )

        return None

    return ticket


@bot.command(
    name="reply",
)
async def reply_command(
    ctx: commands.Context,
    *,
    message: str,
):
    if not await require_modmail_staff(ctx):
        return

    ticket = await require_ticket_channel(ctx)

    if not ticket:
        return

    try:
        user = await bot.fetch_user(
            ticket["user_id"]
        )

    except Exception:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Passenger Not Found",
                (
                    "The passenger could not "
                    "be found."
                ),
            )
        )

        return

    embed = make_embed(
        "",
        message,
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=(
            ctx.author.display_avatar.url
        ),
    )

    embed.set_footer(
        text=(
            f"{staff_rank(ctx.author)} • "
            f"{datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}"
        )
    )

    try:
        await user.send(
            embed=embed,
        )

    except discord.Forbidden:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Delivery Failed",
                (
                    "The passenger has disabled "
                    "direct messages or blocked "
                    "the bot."
                ),
            )
        )

        return

    await add_reaction_safe(
        ctx.message,
        VR_TICK,
    )


@bot.command(
    name="areply",
)
async def anonymous_reply_command(
    ctx: commands.Context,
    *,
    message: str,
):
    if not await require_modmail_staff(ctx):
        return

    ticket = await require_ticket_channel(ctx)

    if not ticket:
        return

    try:
        user = await bot.fetch_user(
            ticket["user_id"]
        )

    except Exception:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Passenger Not Found",
                (
                    "The passenger could not "
                    "be found."
                ),
            )
        )

        return

    alias = random.choice(
        ITALIAN_NAMES
    )

    embed = make_embed(
        "",
        message,
    )

    embed.set_author(
        name=alias,
        icon_url=bot.user.display_avatar.url,
    )

    embed.set_footer(
        text=(
            "ITA Airways Helpline • "
            f"{datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}"
        )
    )

    try:
        await user.send(
            embed=embed,
        )

    except discord.Forbidden:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Delivery Failed",
                (
                    "The passenger has disabled "
                    "direct messages or blocked "
                    "the bot."
                ),
            )
        )

        return

    await add_reaction_safe(
        ctx.message,
        VR_TICK,
    )


@bot.command(
    name="openfor",
)
async def open_for_command(
    ctx: commands.Context,
    user_id: int,
):
    if not await require_modmail_staff(ctx):
        return

    if is_banned(user_id):
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} User Banned",
                (
                    "A ticket cannot be opened "
                    "because this user is banned."
                ),
            )
        )

        return

    try:
        user = await bot.fetch_user(
            user_id
        )

    except Exception:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Invalid User",
                (
                    "A Discord user could not be "
                    "found with that ID."
                ),
            )
        )

        return

    existing = get_open_ticket_for_user(
        user_id
    )

    if existing:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Ticket Already Open",
                (
                    "This user already has an "
                    "active ticket: "
                    f"<#{existing['channel_id']}>"
                ),
            )
        )

        return

    channel = await create_ticket(
        user,
        "Customer Service Department",
        ctx.author.id,
    )

    try:
        await user.send(
            embed=make_embed(
                f"{NETWORK} Connected",
                (
                    f"{POINTER} An ITA Airways "
                    "helpline agent has opened a "
                    "ticket for you. You may reply "
                    "directly to this message."
                ),
            )
        )

    except Exception:
        pass

    await ctx.send(
        embed=make_embed(
            f"{VR_TICK} Ticket Opened",
            (
                "The ticket has been created "
                f"successfully: {channel.mention}"
            ),
        )
    )


@bot.command(
    name="ban",
)
async def ban_command(
    ctx: commands.Context,
    user_id: int,
):
    if not await require_modmail_staff(ctx):
        return

    cursor.execute(
        """
        INSERT INTO banned_users (
            user_id,
            banned_by_id,
            banned_at
        )
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            banned_by_id = excluded.banned_by_id,
            banned_at = excluded.banned_at
        """,
        (
            user_id,
            ctx.author.id,
            utc_now_ts(),
        ),
    )

    db.commit()

    ticket = get_open_ticket_for_user(
        user_id
    )

    if ticket:
        channel = ctx.guild.get_channel(
            ticket["channel_id"]
        )

        cursor.execute(
            """
            UPDATE tickets
            SET
                status = 'closed',
                closed_at = ?,
                closed_by_id = ?
            WHERE ticket_id = ?
            """,
            (
                utc_now_ts(),
                ctx.author.id,
                ticket["ticket_id"],
            ),
        )

        db.commit()

        if channel:
            try:
                await channel.delete(
                    reason=(
                        f"User banned by "
                        f"{ctx.author}"
                    )
                )

            except Exception:
                pass

    await ctx.send(
        embed=make_embed(
            f"{VR_TICK} User Banned",
            (
                f"User ID `{user_id}` has been "
                "banned from using the ITA Airways "
                "helpline."
            ),
        )
    )


@bot.command(
    name="unban",
)
async def unban_command(
    ctx: commands.Context,
    user_id: int,
):
    if not await require_modmail_staff(ctx):
        return

    cursor.execute(
        """
        DELETE FROM banned_users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    db.commit()

    await ctx.send(
        embed=make_embed(
            f"{VR_TICK} User Unbanned",
            (
                f"User ID `{user_id}` may now use "
                "the ITA Airways helpline again."
            ),
        )
    )


async def close_ticket(
    ticket_row,
    closed_by: discord.Member,
    source_channel: discord.TextChannel,
):
    closed_at = utc_now_ts()

    cursor.execute(
        """
        UPDATE tickets
        SET
            status = 'closed',
            closed_at = ?,
            closed_by_id = ?
        WHERE ticket_id = ?
        """,
        (
            closed_at,
            closed_by.id,
            ticket_row["ticket_id"],
        ),
    )

    db.commit()

    try:
        user = await bot.fetch_user(
            ticket_row["user_id"]
        )

        await user.send(
            embed=make_embed(
                f"{VR_CROSS} Ticket Closed",
                (
                    f"{POINTER} Your ITA Airways "
                    "helpline ticket has been closed "
                    "by a staff member."
                ),
            )
        )

    except Exception:
        pass

    log_channel = (
        source_channel.guild.get_channel(
            CLOSED_TICKET_LOG_CHANNEL_ID
        )
    )

    if log_channel:
        duration = str(
            timedelta(
                seconds=max(
                    0,
                    closed_at
                    - ticket_row["opened_at"],
                )
            )
        ).split(".")[0]

        embed = make_embed(
            (
                f"{ticket_row['ticket_id']} "
                f"({str(ticket_row['user_id'])[-2:]})"
            ),
            (
                "**Ticket closed by a staff member**"
                "\n\n"
                "🟢 **Opened by:** "
                f"<@{ticket_row['user_id']}> "
                f"(`{ticket_row['user_id']}`) "
                f"at <t:{ticket_row['opened_at']}:F>"
                "\n\n"
                "🔴 **Closed by:** "
                f"{closed_by.mention} "
                f"(`{closed_by.id}`) "
                f"at <t:{closed_at}:F>"
                "\n\n"
                "📁 **Panel:** "
                f"{ticket_row['category']}\n"
                "⏱️ **Duration:** "
                f"{duration}"
            ),
        )

        await log_channel.send(
            embed=embed,
        )

    await source_channel.send(
        embed=make_embed(
            f"{VR_TICK} Ticket Closed",
            (
                "This ticket will be deleted "
                "in five seconds."
            ),
        )
    )

    await asyncio.sleep(5)

    await source_channel.delete(
        reason=(
            f"Ticket closed by {closed_by}"
        )
    )


@bot.command(
    name="close",
)
async def close_command(
    ctx: commands.Context,
):
    if not await require_modmail_staff(ctx):
        return

    ticket = await require_ticket_channel(ctx)

    if not ticket:
        return

    await close_ticket(
        ticket,
        ctx.author,
        ctx.channel,
    )


async def ask_dm_question(
    ctx: commands.Context,
    title: str,
    prompt: str,
    timeout: int = 300,
):
    try:
        dm = (
            ctx.author.dm_channel
            or await ctx.author.create_dm()
        )

        await dm.send(
            embed=make_embed(
                title,
                prompt,
            )
        )

    except discord.Forbidden:
        await ctx.send(
            embed=make_embed(
                f"{VR_CROSS} Direct Messages Required",
                (
                    "Please enable direct messages "
                    "to complete the scheduling form."
                ),
            )
        )

        return None

    def check(
        message: discord.Message,
    ):
        return (
            message.author.id
            == ctx.author.id
            and isinstance(
                message.channel,
                discord.DMChannel,
            )
        )

    try:
        response = await bot.wait_for(
            "message",
            check=check,
            timeout=timeout,
        )

        return response.content.strip()

    except asyncio.TimeoutError:
        await dm.send(
            embed=make_embed(
                f"{VR_CROSS} Form Expired",
                (
                    "The scheduling form has "
                    "expired."
                ),
            )
        )

        return None


def parse_unix_timestamp(
    value: str,
):
    match = re.search(
        r"(\d{10})",
        value.strip(),
    )

    return (
        int(match.group(1))
        if match
        else None
    )
    async def update_departure_schedule_message():
    guild = bot.get_guild(GUILD_ID)

    if not guild:
        return

    channel = guild.get_channel(
        DEPARTURE_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel,
    ):
        return

    cursor.execute(
        """
        SELECT *
        FROM flights
        WHERE status = 'scheduled'
          AND start_timestamp >= ?
        ORDER BY start_timestamp ASC
        """,
        (utc_now_ts(),),
    )

    flights = cursor.fetchall()

    today = datetime.now(
        LOCAL_TZ
    ).date()

    today_flights = []
    future_flights = []

    for row in flights:
        flight_date = datetime.fromtimestamp(
            row["start_timestamp"],
            tz=timezone.utc,
        ).astimezone(
            LOCAL_TZ
        ).date()

        if flight_date == today:
            today_flights.append(row)

        elif flight_date > today:
            future_flights.append(row)

    def lines(rows):
        if not rows:
            return (
                f"{FLIGHT} No flights currently listed."
            )

        return "\n".join(
            (
                f"{FLIGHT} "
                f"[{row['flight_number']}]"
                f"({row['event_url']})"
            )
            for row in rows
        )

    now_ts = utc_now_ts()

    embed = make_embed(
        f"{SCHEDULE} Flight Schedule",
        (
            f"-# `LAST UPDATED:` <t:{now_ts}:R>"
            "\n\n"
            "We are excited to share that "
            f"**{len(today_flights)}** flight(s) "
            "are scheduled for today. For your "
            "convenience, all details may be found "
            "in the event cards below."
            "\n\n"
            f"**{INFORMATION} Scheduled Today**\n"
            f"{lines(today_flights)}"
            "\n\n"
            f"**{INFORMATION} Scheduled Flights**\n"
            f"{lines(future_flights)}"
        ),
    )

    cursor.execute(
        """
        SELECT value
        FROM bot_config
        WHERE key = 'schedule_message_id'
        """
    )

    row = cursor.fetchone()

    message_id = (
        int(row["value"])
        if row and row["value"]
        else None
    )

    if message_id:
        try:
            message = await channel.fetch_message(
                message_id
            )

            await message.edit(
                embed=embed
            )

            return

        except Exception:
            pass

    message = await channel.send(
        embed=embed
    )

    cursor.execute(
        """
        INSERT INTO bot_config (
            key,
            value
        )
        VALUES (
            'schedule_message_id',
            ?
        )
        ON CONFLICT(key)
        DO UPDATE SET
            value = excluded.value
        """,
        (str(message.id),),
    )

    db.commit()


@bot.command(name="schedule")
async def schedule_command(
    ctx: commands.Context,
):
    if (
        not isinstance(
            ctx.author,
            discord.Member,
        )
        or not is_operations_staff(
            ctx.author
        )
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Permission Denied",
                (
                    "You do not have permission to "
                    "schedule ITA Airways flights."
                ),
            )
        )

        return

    await ctx.send(
        embed=make_embed(
            f"{MAIL} Scheduling Form Sent",
            (
                "Please check your direct messages "
                "and complete the flight scheduling "
                "form."
            ),
        )
    )

    flight_number = await ask_dm_question(
        ctx,
        f"{SCHEDULE} Flight Number",
        "Please enter the flight number.",
    )

    if not flight_number:
        return

    timestamp_input = await ask_dm_question(
        ctx,
        f"{SCHEDULE} Flight Timestamp",
        (
            "Please enter the ten-digit Unix "
            "timestamp for the flight."
        ),
    )

    if not timestamp_input:
        return

    start_timestamp = parse_unix_timestamp(
        timestamp_input
    )

    if not start_timestamp:
        await ctx.author.send(
            embed=make_embed(
                f"{ITA_CROSS} Invalid Timestamp",
                (
                    "Please provide a valid ten-digit "
                    "Unix timestamp."
                ),
            )
        )

        return

    if start_timestamp <= utc_now_ts():
        await ctx.author.send(
            embed=make_embed(
                f"{ITA_CROSS} Invalid Timestamp",
                (
                    "The scheduled flight time must "
                    "be in the future."
                ),
            )
        )

        return

    game_link = await ask_dm_question(
        ctx,
        f"{ROBLOX} Game Link",
        (
            "Please enter the Roblox game or "
            "private-server link."
        ),
    )

    if not game_link:
        return

    if not game_link.startswith(
        (
            "http://",
            "https://",
        )
    ):
        game_link = (
            "https://"
            + game_link
        )

    route = await ask_dm_question(
        ctx,
        f"{INFORMATION} Flight Route",
        (
            "Please enter the route, for example "
            "`FCO → LHR`."
        ),
    )

    if not route:
        return

    aircraft = await ask_dm_question(
        ctx,
        f"{FLIGHT} Aircraft",
        (
            "Please enter the aircraft for "
            "this flight."
        ),
    )

    if not aircraft:
        return

    try:
        banner_dm = (
            ctx.author.dm_channel
            or await ctx.author.create_dm()
        )

        await banner_dm.send(
            embed=make_embed(
                f"{ANNOUNCE} Event Banner",
                (
                    "Please upload the image you want "
                    "to use as the Discord event banner. "
                    "Send one PNG, JPG, JPEG, or WEBP "
                    "image."
                ),
            )
        )

    except discord.Forbidden:
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Direct Messages Required",
                (
                    "Please enable direct messages so "
                    "the event banner can be uploaded."
                ),
            )
        )

        return

    def banner_check(
        message: discord.Message,
    ):
        return (
            message.author.id
            == ctx.author.id
            and isinstance(
                message.channel,
                discord.DMChannel,
            )
            and len(
                message.attachments
            ) > 0
        )

    try:
        banner_message = await bot.wait_for(
            "message",
            check=banner_check,
            timeout=300,
        )

    except asyncio.TimeoutError:
        await banner_dm.send(
            embed=make_embed(
                f"{ITA_CROSS} Form Expired",
                (
                    "The scheduling form expired "
                    "because no event banner was "
                    "uploaded."
                ),
            )
        )

        return

    banner_attachment = (
        banner_message.attachments[0]
    )

    allowed_extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    )

    content_type = (
        banner_attachment.content_type
        or ""
    ).lower()

    filename = (
        banner_attachment.filename.lower()
    )

    if (
        not content_type.startswith(
            "image/"
        )
        and not filename.endswith(
            allowed_extensions
        )
    ):
        await banner_dm.send(
            embed=make_embed(
                f"{ITA_CROSS} Invalid Banner",
                (
                    "Please upload a PNG, JPG, JPEG, "
                    "or WEBP image."
                ),
            )
        )

        return

    try:
        banner_bytes = (
            await banner_attachment.read()
        )

    except Exception as exc:
        await banner_dm.send(
            embed=make_embed(
                f"{ITA_CROSS} Banner Download Failed",
                (
                    "The banner could not be "
                    f"downloaded.\n\n`{exc}`"
                ),
            )
        )

        return

    if len(banner_bytes) > (
        10 * 1024 * 1024
    ):
        await banner_dm.send(
            embed=make_embed(
                f"{ITA_CROSS} Banner Too Large",
                (
                    "Please upload an event banner "
                    "smaller than 10 MB."
                ),
            )
        )

        return

    guild = bot.get_guild(
        GUILD_ID
    )

    if not guild:
        await ctx.author.send(
            embed=make_embed(
                f"{ITA_CROSS} Scheduling Failed",
                (
                    "The configured ITA Airways "
                    "server could not be found."
                ),
            )
        )

        return

    start_time = datetime.fromtimestamp(
        start_timestamp,
        tz=timezone.utc,
    )

    end_time = (
        start_time
        + timedelta(hours=1)
    )

    event_description = (
        f"**{LOGO} Flight Scheduled**"
        "\n\n"
        f"{POINTER} Greetings! A new flight "
        "has been scheduled "
        f"**{SCHEDULE} {flight_number}** "
        "and the route is "
        f"**{INFORMATION} {route}** "
        f"onboard our **{aircraft}** "
        f"from **{ROBLOX} "
        f"[Game Link]({game_link})**."
        "\n\n"
        "If interested, please click "
        "**Interested**."
    )

    try:
        event = await guild.create_scheduled_event(
            name=(
                f"{flight_number} | {route}"
            ),
            description=event_description,
            start_time=start_time,
            end_time=end_time,
            entity_type=(
                discord.EntityType.external
            ),
            privacy_level=(
                discord.PrivacyLevel.guild_only
            ),
            location=game_link[:100],
            image=banner_bytes,
            reason=(
                f"Flight scheduled by "
                f"{ctx.author}"
            ),
        )

    except Exception as exc:
        await ctx.author.send(
            embed=make_embed(
                f"{ITA_CROSS} Event Creation Failed",
                (
                    "The event could not be "
                    f"created.\n\n`{exc}`"
                ),
            )
        )

        return

    event_url = (
        "https://discord.com/events/"
        f"{guild.id}/{event.id}"
    )

    cursor.execute(
        """
        INSERT INTO flights (
            event_id,
            event_url,
            flight_number,
            start_timestamp,
            game_link,
            route,
            aircraft,
            scheduled_by_id,
            created_at,
            status
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled'
        )
        """,
        (
            event.id,
            event_url,
            flight_number,
            start_timestamp,
            game_link,
            route,
            aircraft,
            ctx.author.id,
            utc_now_ts(),
        ),
    )

    db.commit()

    await update_departure_schedule_message()

    await ctx.author.send(
        embed=make_embed(
            f"{ITA_TICK} Flight Scheduled",
            (
                f"**Flight:** {flight_number}\n"
                f"**Route:** {route}\n"
                f"**Aircraft:** {aircraft}\n"
                f"**Departure:** "
                f"<t:{start_timestamp}:F>\n"
                f"**Event:** "
                f"[Open Event Card]({event_url})"
            ),
        )
    )
    @bot.command(name="list-events")
async def list_events_command(
    ctx: commands.Context,
):
    if (
        not isinstance(ctx.author, discord.Member)
        or not is_operations_staff(ctx.author)
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Permission Denied",
                (
                    "You do not have permission to "
                    "list ITA Airways flight events."
                ),
            )
        )
        return

    departure_channel = ctx.guild.get_channel(
        DEPARTURE_CHANNEL_ID
    )

    if not isinstance(
        departure_channel,
        discord.TextChannel,
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Channel Not Found",
                (
                    "The configured departure channel "
                    "could not be found."
                ),
            )
        )
        return

    cursor.execute(
        """
        DELETE FROM bot_config
        WHERE key = 'schedule_message_id'
        """
    )
    db.commit()

    await update_departure_schedule_message()

    await ctx.send(
        embed=make_embed(
            f"{ITA_TICK} Events Listed",
            (
                "The flight schedule has been posted "
                f"again in {departure_channel.mention}."
            ),
        )
    )


@bot.command(name="unlock")
async def unlock_command(
    ctx: commands.Context,
    *,
    flight_number: str,
):
    if (
        not isinstance(ctx.author, discord.Member)
        or not is_operations_staff(ctx.author)
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Permission Denied",
                (
                    "You do not have permission to "
                    "unlock ITA Airways flight servers."
                ),
            )
        )
        return

    cursor.execute(
        """
        SELECT *
        FROM flights
        WHERE LOWER(flight_number) = LOWER(?)
          AND status = 'scheduled'
        ORDER BY id DESC
        LIMIT 1
        """,
        (flight_number.strip(),),
    )

    flight_row = cursor.fetchone()

    if not flight_row:
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Flight Not Found",
                (
                    "No scheduled flight was found "
                    f"with flight number `{flight_number}`."
                ),
            )
        )
        return

    departure_channel = ctx.guild.get_channel(
        DEPARTURE_CHANNEL_ID
    )

    if not isinstance(
        departure_channel,
        discord.TextChannel,
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Channel Not Found",
                (
                    "The configured departure channel "
                    "could not be found."
                ),
            )
        )
        return

    ghost_ping = await departure_channel.send(
        content="@everyone",
        allowed_mentions=discord.AllowedMentions(
            everyone=True,
        ),
    )

    try:
        await ghost_ping.delete()
    except Exception:
        pass

    await departure_channel.send(
        embed=make_embed(
            f"{ROBLOX} Server Unlocked",
            (
                f"{POINTER} Greetings! It is with "
                "pleasure that I announce that the "
                "server has been unlocked for passengers "
                "to join flight "
                f"**{FLIGHT} {flight_row['flight_number']}**. "
                "Please join through "
                f"**[this link]({flight_row['game_link']})**."
            ),
        )
    )

    await ctx.send(
        embed=make_embed(
            f"{ITA_TICK} Server Unlock Announced",
            (
                "The unlock announcement for "
                f"**{flight_row['flight_number']}** "
                "was posted."
            ),
        )
    )


@bot.command(name="lock")
async def lock_command(
    ctx: commands.Context,
    *,
    flight_number: str,
):
    if (
        not isinstance(ctx.author, discord.Member)
        or not is_operations_staff(ctx.author)
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Permission Denied",
                (
                    "You do not have permission to "
                    "lock ITA Airways flight servers."
                ),
            )
        )
        return

    cursor.execute(
        """
        SELECT *
        FROM flights
        WHERE LOWER(flight_number) = LOWER(?)
          AND status = 'scheduled'
        ORDER BY id DESC
        LIMIT 1
        """,
        (flight_number.strip(),),
    )

    flight_row = cursor.fetchone()

    if not flight_row:
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Flight Not Found",
                (
                    "No scheduled flight was found "
                    f"with flight number `{flight_number}`."
                ),
            )
        )
        return

    departure_channel = ctx.guild.get_channel(
        DEPARTURE_CHANNEL_ID
    )

    if not isinstance(
        departure_channel,
        discord.TextChannel,
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Channel Not Found",
                (
                    "The configured departure channel "
                    "could not be found."
                ),
            )
        )
        return

    await departure_channel.send(
        content="@here",
        embed=make_embed(
            f"{INFORMATION} Server Locked",
            (
                f"{POINTER} It is with great pleasure "
                "that I announce boarding has begun for "
                f"flight **{FLIGHT} "
                f"{flight_row['flight_number']}**. "
                "Therefore, the server has been locked "
                "for smooth operations."
            ),
        ),
        allowed_mentions=discord.AllowedMentions(
            everyone=True,
        ),
    )

    await ctx.send(
        embed=make_embed(
            f"{ITA_TICK} Server Lock Announced",
            (
                "The lock announcement for "
                f"**{flight_row['flight_number']}** "
                "was posted."
            ),
        )
    )


@bot.command(name="complete")
async def complete_command(
    ctx: commands.Context,
    *,
    flight_number: str,
):
    if (
        not isinstance(ctx.author, discord.Member)
        or not is_operations_staff(ctx.author)
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Permission Denied",
                (
                    "You do not have permission to "
                    "complete ITA Airways flights."
                ),
            )
        )
        return

    cursor.execute(
        """
        SELECT *
        FROM flights
        WHERE LOWER(flight_number) = LOWER(?)
          AND status = 'scheduled'
        ORDER BY id DESC
        LIMIT 1
        """,
        (flight_number.strip(),),
    )

    flight = cursor.fetchone()

    if not flight:
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Flight Not Found",
                (
                    "No active scheduled flight was "
                    "found with flight number "
                    f"`{flight_number}`."
                ),
            )
        )
        return

    cursor.execute(
        """
        UPDATE flights
        SET status = 'completed'
        WHERE id = ?
        """,
        (flight["id"],),
    )
    db.commit()

    try:
        event = await ctx.guild.fetch_scheduled_event(
            int(flight["event_id"])
        )

        if event.status == discord.EventStatus.active:
            await event.end(
                reason=(
                    f"Flight completed by "
                    f"{ctx.author}"
                )
            )

        elif event.status == discord.EventStatus.scheduled:
            await event.edit(
                status=discord.EventStatus.completed,
                reason=(
                    f"Flight completed by "
                    f"{ctx.author}"
                ),
            )

    except Exception:
        pass

    await update_departure_schedule_message()

    await ctx.send(
        embed=make_embed(
            f"{ITA_TICK} Flight Completed",
            (
                f"Flight **{flight['flight_number']}** "
                "has been marked as completed and "
                "removed from the departure schedule."
            ),
        )
    )


@bot.command(name="cancel")
async def cancel_command(
    ctx: commands.Context,
    *,
    flight_number: str,
):
    if (
        not isinstance(ctx.author, discord.Member)
        or not is_operations_staff(ctx.author)
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Permission Denied",
                (
                    "You do not have permission to "
                    "cancel ITA Airways flights."
                ),
            )
        )
        return

    cursor.execute(
        """
        SELECT *
        FROM flights
        WHERE LOWER(flight_number) = LOWER(?)
          AND status = 'scheduled'
        ORDER BY id DESC
        LIMIT 1
        """,
        (flight_number.strip(),),
    )

    flight = cursor.fetchone()

    if not flight:
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Flight Not Found",
                (
                    "No active scheduled flight was "
                    "found with flight number "
                    f"`{flight_number}`."
                ),
            )
        )
        return

    cursor.execute(
        """
        UPDATE flights
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (flight["id"],),
    )
    db.commit()

    try:
        event = await ctx.guild.fetch_scheduled_event(
            int(flight["event_id"])
        )

        await event.delete(
            reason=(
                f"Flight cancelled by "
                f"{ctx.author}"
            )
        )

    except Exception:
        pass

    await update_departure_schedule_message()

    await ctx.send(
        embed=make_embed(
            f"{ITA_TICK} Flight Cancelled",
            (
                f"Flight **{flight['flight_number']}** "
                "has been cancelled and removed from "
                "the departure schedule."
            ),
        )
    )


@bot.event
async def on_scheduled_event_delete(
    event: discord.ScheduledEvent,
):
    cursor.execute(
        """
        UPDATE flights
        SET status = 'cancelled'
        WHERE event_id = ?
        """,
        (event.id,),
    )
    db.commit()

    cursor.execute(
        """
        SELECT value
        FROM bot_config
        WHERE key = 'schedule_message_id'
        """
    )

    saved_message = cursor.fetchone()

    if saved_message:
        await update_departure_schedule_message()


@bot.event
async def on_ready():
    print(
        f"Logged in as {bot.user} | "
        "ITA Airways Customer Core online"
    )


@bot.event
async def on_message(
    message: discord.Message,
):
    if message.author.bot:
        return

    if message.guild is not None:
        await bot.process_commands(message)
        return

    if is_banned(message.author.id):
        await add_reaction_safe(
            message,
            ITA_CROSS,
        )

        try:
            await message.author.send(
                embed=make_embed(
                    f"{ITA_CROSS} Connection Refused",
                    (
                        f"{POINTER} You are currently "
                        "unable to open an ITA Airways "
                        "helpline ticket."
                    ),
                )
            )

        except Exception:
            pass

        return

    open_ticket = get_open_ticket_for_user(
        message.author.id
    )

    if open_ticket:
        sent = await send_passenger_message_to_ticket(
            message,
            open_ticket,
        )

        await add_reaction_safe(
            message,
            ITA_TICK if sent else ITA_CROSS,
        )
        return

    pending_first_messages[
        message.author.id
    ] = message

    await message.author.send(
        embed=make_embed(
            f"{MAIL} Connecting",
            (
                f"{FLAG} Benvenuto, thank you for "
                "contacting the ITA Airways Helpline."
                "\n\n"
                f"{POINTER} We appreciate your interest "
                "in consulting with us today, but are "
                "you sure you want to create a ticket? "
                "Please use the buttons below."
            ),
        ),
        view=TicketConfirmView(
            message.author.id
        ),
    )


@bot.event
async def on_command_error(
    ctx: commands.Context,
    error: commands.CommandError,
):
    if isinstance(
        error,
        commands.CommandNotFound,
    ):
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument,
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Missing Information",
                (
                    "Required information is missing: "
                    f"`{error.param.name}`."
                ),
            )
        )
        return

    if isinstance(
        error,
        commands.BadArgument,
    ):
        await ctx.send(
            embed=make_embed(
                f"{ITA_CROSS} Invalid Information",
                (
                    "One of the provided values "
                    "was invalid."
                ),
            )
        )
        return

    await ctx.send(
        embed=make_embed(
            f"{ITA_CROSS} Command Error",
            (
                "An unexpected error occurred."
                "\n\n"
                f"`{type(error).__name__}: {error}`"
            ),
        )
    )

    raise error


bot.run(TOKEN)

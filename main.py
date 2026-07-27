from __future__ import annotations

import os
import sys
from pathlib import Path


SOURCE_FILE = Path(__file__).with_name("vertex_core.py")

if not SOURCE_FILE.exists():
    raise FileNotFoundError(
        "vertex_core.py was not found. Upload the original Vertex Customer "
        "Core code and name it vertex_core.py."
    )


def replace_required(source: str, old: str, new: str) -> str:
    """
    Replace a source-code value.

    A warning is printed when the old value was not found, but the bot is
    still allowed to continue because different Vertex versions may contain
    slightly different formatting.
    """
    if old not in source:
        print(f"[ITA conversion warning] Could not find: {old!r}")
        return source

    return source.replace(old, new)


source = SOURCE_FILE.read_text(encoding="utf-8")


# ============================================================
# ITA AIRWAYS SERVER CONFIGURATION
# ============================================================

source = replace_required(
    source,
    'MODMAIL_STAFF_ROLE_ID = 1523239968561172511',
    'MODMAIL_STAFF_ROLE_ID = int(os.getenv("MODMAIL_STAFF_ROLE_ID", "1531252969654321343"))',
)

source = replace_required(
    source,
    'TICKET_CATEGORY_ID = 1523240280168599552',
    'TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "1530230686273896620"))',
)

source = replace_required(
    source,
    'CLOSED_TICKET_LOG_CHANNEL_ID = 1523240300909301790',
    'CLOSED_TICKET_LOG_CHANNEL_ID = int(os.getenv("CLOSED_TICKET_LOG_CHANNEL_ID", "1531253717980938301"))',
)

source = replace_required(
    source,
    'DEPARTURE_CHANNEL_ID = 1523011676365000885',
    'DEPARTURE_CHANNEL_ID = int(os.getenv("DEPARTURE_CHANNEL_ID", "1531253179054821396"))',
)


# ============================================================
# ITA AIRWAYS BRAND COLOUR
# ============================================================

source = replace_required(
    source,
    'BRAND_COLOR = 0x1B2A6B',
    'BRAND_COLOR = int(os.getenv("BRAND_COLOR", "003B7A"), 16)',
)


# ============================================================
# ITA CUSTOM EMOJIS
# ============================================================

emoji_replacements = {
    '<:logo:1523025299879493873>':
        '<:tail:1526303107708092567>',

    '<:flag:1523024705999864051>':
        '<:flag:1530228152649908344>',

    '<:announce:1523019706674708490>':
        '<:announce:1531243911211647018>',

    '<:schedule:1523018152668303512>':
        '<:schedule:1531243944908947617>',

    '<:network:1523018073114677558>':
        '<:network:1531243969739227208>',

    '<:helpdesk:1523013663441686621>':
        '<:personnel:1531244023673651200>',

    '<:mail:1523013626976276610>':
        '<:information_ITA:1531244145002152027>',

    '<:roblox:1523013155494826045>':
        '<:roblox:1531244097170440262>',

    '<:information:1523012977308209182>':
        '<:information_ITA:1531244145002152027>',

    '<:VR_cross:1523179629605687458>':
        '<:Cross:1531244067965370369>',

    '<:VR_tick:1523179608269258854>':
        '<:tick:1531244120490770432>',

    '<:Pointer:1523241611171987506>':
        '<:notification:1531244167500664882>',

    '<:flight:1523246237954871367>':
        '<:tail:1526303107708092567>',
}

for old_emoji, new_emoji in emoji_replacements.items():
    source = source.replace(old_emoji, new_emoji)


# Add all ITA emojis as constants so they are available throughout the bot.

extra_emoji_constants = '''
# ITA Airways custom emojis
NOTIFICATION = "<:notification:1531244167500664882>"
INFORMATION_ITA = "<:information_ITA:1531244145002152027>"
ITA_TICK = "<:tick:1531244120490770432>"
ITA_ROBLOX = "<:roblox:1531244097170440262>"
ITA_CROSS = "<:Cross:1531244067965370369>"
DEVELOPMENT = "<:development:1531244047010889910>"
PERSONNEL = "<:personnel:1531244023673651200>"
FOLDER = "<:folder:1531244001758548139>"
ITA_NETWORK = "<:network:1531243969739227208>"
ITA_SCHEDULE = "<:schedule:1531243944908947617>"
ITA_ANNOUNCE = "<:announce:1531243911211647018>"
ITA_FLAG = "<:flag:1530228152649908344>"
LOCK_EMOJI = "<:Lock:1530207501117685860>"
UNLOCK_EMOJI = "<:Unlock:1530206619617464351>"
ITA_TAIL = "<:tail:1526303107708092567>"
'''

insertion_marker = 'FLIGHT = "<:tail:1526303107708092567>"'

if insertion_marker in source:
    source = source.replace(
        insertion_marker,
        insertion_marker + "\n" + extra_emoji_constants,
        1,
    )
else:
    print("[ITA conversion warning] Emoji insertion marker was not found.")


# ============================================================
# ITA AIRWAYS BRANDING
# ============================================================

branding_replacements = {
    "Vertex Air Customer Core": "ITA Airways Customer Core",
    "Vertex Air Helpline": "ITA Airways Helpline",
    "Vertex Air helpline": "ITA Airways helpline",
    "Vertex Air Modmail": "ITA Airways ModMail",
    "Vertex Air ModMail": "ITA Airways ModMail",
    "Vertex Air Operations": "ITA Airways Operations",
    "Vertex Air Departure": "ITA Airways Departure",
    "Vertex Air flight": "ITA Airways flight",
    "Vertex Air Flight": "ITA Airways Flight",
    "Vertex Air server": "ITA Airways server",
    "Vertex Air": "ITA Airways",
    "vertex_customer_core.db": "ita_customer_core.db",
}

for old_branding, new_branding in branding_replacements.items():
    source = source.replace(old_branding, new_branding)


# ============================================================
# ITALIAN ANONYMOUS SUPPORT NAMES
# ============================================================

old_names = '''GREEK_NAMES = [
    "Alexandros", "Andreas", "Dimitrios", "Eleni", "Katerina",
    "Konstantinos", "Leonidas", "Nikos", "Sofia", "Stavros",
    "Theodoros", "Yannis",
]'''

new_names = '''GREEK_NAMES = [
    "Alessandro",
    "Andrea",
    "Antonio",
    "Beatrice",
    "Chiara",
    "Francesca",
    "Giulia",
    "Lorenzo",
    "Marco",
    "Matteo",
    "Sofia",
    "Valentina",
]'''

source = source.replace(old_names, new_names)


# ============================================================
# FINAL SAFETY CHECK
# ============================================================

remaining_vertex_references = source.count("Vertex Air")

if remaining_vertex_references:
    print(
        f"[ITA conversion warning] "
        f"{remaining_vertex_references} Vertex Air reference(s) remain."
    )
else:
    print("[ITA conversion] All Vertex Air branding was replaced.")


# Make the converted program behave as the main Python file.
runtime_globals = {
    "__name__": "__main__",
    "__file__": str(SOURCE_FILE),
    "__package__": None,
    "__cached__": None,
}

compiled_source = compile(
    source,
    str(SOURCE_FILE),
    "exec",
)

exec(compiled_source, runtime_globals)

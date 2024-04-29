import os
import aiofiles
import interactions
from interactions import (
    Button,
    ButtonStyle,
    AutocompleteContext,
    slash_option,
    OptionType,
    Member,
    Role,
)

from pydantic import BaseModel


from rich.console import Console


console = Console()


class GuildConfig(BaseModel):
    divider_contains: str = "[]"

    def is_divider(self, role: Role) -> bool:
        return all([(c in role.name) for c in self.divider_contains])

    async def fix_member_roles(self, member: Member):

        current_divider: Role = None
        for role in member.guild.roles:
            console.log(role)
            if self.is_divider(role):
                current_divider = role
            


async def load_config(guild_id: int) -> GuildConfig:
    try:
        async with aiofiles.open(generate_path(guild_id), "r") as f:
            config = GuildConfig.model_validate_json(await f.read())
    except Exception as e:
        console.log(f"[red] Error occur: {e} when load_config")
        config = GuildConfig()

    return config


async def save_config(guild_id: int, config: GuildConfig):
    async with aiofiles.open(generate_path(guild_id), "w") as f:
        await f.write(config.model_dump_json(indent=4))


async def is_admin(ctx: interactions.SlashContext) -> bool:
    return ctx.author.has_permission(interactions.Permissions.ADMINISTRATOR)


def generate_path(guild_id: int):
    return f"{os.path.dirname(__file__)}/{guild_id}_config.json"


class GuildRoleDivider:
    def __init__(self, guild_id: int) -> None:
        self.guilld_id = guild_id


class RoleDivider(interactions.Extension):
    module_base: interactions.SlashCommand = interactions.SlashCommand(
        name="role_divider",
        description="自動添加分隔用身份組給每一位成員，注意分隔用身份組本身的權限",
        checks=[is_admin],
    )

    @module_base.subcommand("help", sub_cmd_description="顯示關於分隔用身份組的介紹")
    async def help(self, ctx: interactions.SlashContext):
        config = await load_config(ctx.guild_id)
        await ctx.respond(
            embed=interactions.Embed(
                title="分隔用身份組",
                description=f"""
分隔用身份組模組，會自動化添加分隔用身份組給需要的人，請注意分隔身份組本身自帶的權限，以避免安全隱患。

## 介紹
0. 只有管理員可以使用本模組的指令。
1. 任一非分隔身份組的分隔用身份組，為前一個最近的分隔用身份組
2. 按照目前的設定，同時包含{'、'.join(['「'+c+'」' for c in config.divider_contains.split()])}的身份組將會被視為分隔用身份組。

""",
                color=0xFF5252,
            )
        )

    @module_base.subcommand(
        "config",
        sub_cmd_description="設定分隔身份組的相關設定，若不進行任何設定，則可以看見目前設定",
    )
    @slash_option(
        name="divider_contains",
        description="同時包含所有字元的身份組，將會被視為分隔身份組",
        required=False,
        opt_type=OptionType.STRING,
    )
    async def config(
        self,
        ctx: interactions.SlashContext,
        divider_contains: str = None,
    ):

        config = await load_config(ctx.guild_id)
        if divider_contains:
            assert isinstance(divider_contains, str)
            config.divider_contains = divider_contains.strip()

        await save_config(ctx.guild_id, config)
        await ctx.respond(f"已設定，新的設定如下\n```py\n{config}\n```", ephemeral=True)

    @module_base.subcommand(
        "manual_fix", sub_cmd_description="手動修復任一，或是所有成員的分隔身份組狀態"
    )
    @slash_option(
        name="member",
        description="要修復的成員，若不指定，則會修復全部成員的狀態",
        required=False,
        opt_type=OptionType.USER,
    )
    async def manual_fix(self, ctx: interactions.SlashContext, member: Member = None):
        config = await load_config(ctx.guild_id)
        await config.fix_member_roles(member)
        # effect_list = await fix_gossiper_role(ctx.guild)
        # await ctx.respond(
        #     f"修復了{len(effect_list)}位成員的吃瓜觀光團身份組狀態。", ephemeral=True
        # )

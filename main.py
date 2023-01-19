import re
import os

from dotenv import load_dotenv
import discord
from discord.ext.commands import Bot

load_dotenv()
bot = Bot(command_prefix="", intents=discord.Intents.all())

"""
``conquest ⚐`` **|** Attacks on *blackstone* since 1970/01/01 00:00:00 UTC:

`T2R4lpha` *(scaffolding)* has attacked 6 times, stealing **4** tiles, **2x Mine**, **1x Material Storage**
"""


building_emojis = {
    "Mine": "<:mine:1065288475412271104>",
    "Training Camp": "<:camp:1065289097112989787>",
    "Material Storage": "<:mat_storage:1065289895565869087>",
    "House": "<:pow_storage:1065290439395127357>",
    "Laboratory": "<:lab:1065290676461375528>",
    "Anti-Missile Wall": "",
    "Fortifier": "",
    "Rift": "<:rift:1065286350934376519>",
    "Tiles": "<:tile:1065289534419505193>"
}


class Attack:
    def __init__(self, attacked, attacker, attack_times, tiles_stolen, stolen):
        self.attacked = attacked
        self.attacker = attacker
        self.attack_times = attack_times
        self.tiles_stolen = tiles_stolen
        self.stolen = stolen


def parse(data: str) -> dict[str, Attack]:
    attacked = ""
    attacks = {}

    for line in data.split("\n"):
        if line == "":
            continue
        if re.match("``conquest ⚐`` \*\*|\*\* Attacks on \*[a-z_]+\* since [/:0-9 ]+ UTC:", line):
            attacked = re.search("Attacks on \*[a-z_]+\*", line).group()[11:]
        elif re.match("`[A-z_0-9]+` \*\([a-z_]+\)\* has attacked [0-9]+ times, stealing \*\*[0-9]+\*\* tiles(, [A-z0-9, *])*", line):
            stolen = []
            attacker = re.search("^`[A-z_0-9]+` \*\([a-z_]+\)\*", line).group().replace("`", "").replace("*", "")
            attack_times = re.search(" has attacked [0-9]+ times,", line).group()[14:-7]
            tiles_stolen = re.search(" stealing \*\*[0-9]+\*\* tiles", line).group()[12:-8]
            if not re.search("tiles, [A-z0-9, *]+", line) is None:
                stolen_data = re.search("tiles, [A-z0-9, *]+", line).group()[7:]
                for part in re.findall("\*\*[0-9]+x [A-z ]+\*\*", stolen_data):
                    part = part[2:-2]
                    amount = part.split("x ")[0]
                    other = part.split("x ")[1:]
                    building = " ".join(other)
                    stolen.append((amount, building))
            attacks[attacker] = Attack(attacked, attacker, attack_times, tiles_stolen, stolen)
    return attacks


async def edit_embed(interaction, selected_building, remove_amount=1, add_s=True):
    embed = interaction.message.embeds[0]
    total_lost = 0
    index = -1
    for i, field in enumerate(embed.fields):
        nums = re.search("s: \*\*[0-9]+\*\* \[[0-9]+\]", field.value).group()[5:]
        if "Attacks" not in field.value:
            total_lost += int(nums.split(" ")[0][:-2])
        if selected_building in field.value:
            index = i
            amount, total = nums.split(" ")
            amount = int(amount[:-2])
            total_lost -= remove_amount
        print(total_lost, field.value)
    await interaction.response.defer()
    if total_lost == 0:
        embed.color = discord.Color.green()
    if index != -1 and amount > 0:
        embed.remove_field(index)
        emoji = building_emojis.get(selected_building, "")
        if add_s:
            selected_building += "s"
        embed.add_field(name="", value=f"{emoji} Stolen {selected_building}: **{max(amount-remove_amount, 0)}** {total}", inline=False)
        await interaction.message.edit(embed=embed)


@bot.event
async def on_ready():
    await bot.tree.sync()


@bot.event
async def on_message(msg: discord.Message):
    if re.match("``conquest ⚐`` \*\*|\*\* Attacks on \*[a-z_]+\* since [/:0-9 ]+ UTC:", msg.content.split("\n")[0]):
        attacks = parse(msg.content)
        for attacker, attack in attacks.items():
            embed = discord.Embed(title=f"{attacker} attacked!",
                                  description=f":crossed_swords: Attacks: **{attack.attack_times}**", color=discord.Color.from_rgb(255, 0, 0))
            embed.add_field(
                value=f"{building_emojis['Tiles']} Stolen Tiles: **{attack.tiles_stolen}** [{attack.tiles_stolen}]",
                name=""
            )
            for amount, building in attack.stolen:
                emoji = building_emojis.get(building, "")
                embed.add_field(
                    value=f"{emoji} Stolen {building}s: **{amount}** [{amount}]",
                    name="",
                    inline=False
                )

            async def select_callback(interaction: discord.Interaction):
                await edit_embed(interaction, select.values[0])

            async def button_callback(interaction: discord.Interaction):
                class Tiles(discord.ui.Modal, title="Reclaimed Tiles"):
                    def __init__(self):
                        super().__init__()
                        self.add_item(discord.ui.TextInput(label="Amount"))

                    async def on_submit(self, interaction: discord.Interaction) -> None:
                        await edit_embed(interaction, "Tiles", int(str(self.children[0])), False)
                await interaction.response.send_modal(Tiles())

            select_building = discord.ui.View()
            select = discord.ui.Select(
                options=[
                    discord.SelectOption(label="Mine", value="Mine", emoji=building_emojis["Mine"]),
                    discord.SelectOption(label="Training Camp", value="Training Camp", emoji=building_emojis["Training Camp"]),
                    discord.SelectOption(label="Material Storage", value="Material Storage", emoji=building_emojis["Material Storage"]),
                    discord.SelectOption(label="House", value="House", emoji=building_emojis["House"]),
                    discord.SelectOption(label="Laboratory", value="Laboratory", emoji=building_emojis["Laboratory"]),
                    discord.SelectOption(label="Rift", value="Rift", emoji=building_emojis["Rift"]),
                ], min_values=1, max_values=1
            )
            select.callback = select_callback
            button = discord.ui.Button(label="Add Tiles", emoji=building_emojis["Tiles"], style=discord.ButtonStyle.green)
            button.callback = button_callback
            select_building.add_item(button)
            select_building.add_item(select)
            await msg.channel.send(embed=embed, view=select_building)
        await msg.delete()


bot.run(token=os.getenv("TOKEN"))

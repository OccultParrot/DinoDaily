import discord
import dotenv
import requests
import os
from discord.ui import Modal, View

GITHUB_URL = "https://api.github.com/repos/OccultParrot/DinoDaily/issues"

dotenv.load_dotenv()

class DinoPostView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Suggest a Change", style=discord.ButtonStyle.blurple)
    async def suggest_callback(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(SuggestModal())


class SuggestModal(Modal):
    def __init__(self):
        super().__init__(title="Suggest a Change")
        self.suggestion_name = discord.ui.TextInput(label="Name of Suggestion", style=discord.TextStyle.short)
        self.suggestion = discord.ui.TextInput(label="Suggestion", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.suggestion_name)
        self.add_item(self.suggestion)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        headers = {
            "Authorization": f"Bearer {os.getenv("GITHUB_TOKEN")}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        issue_data = {
            "title": f"{self.suggestion_name} by {interaction.user.name} ({interaction.user.id})",
            "body": f"Suggestion: {self.suggestion}",
            "labels": ["suggestion"]
        }

        response = requests.post(GITHUB_URL, headers=headers, json=issue_data)

        if response.status_code == 201:
            issue = response.json()
            await interaction.edit_original_response(
                content=f"Issue #{issue['number']} successfully created!\n\n[Check it out here]({issue['html_url']})"
            )
        else:
            await interaction.edit_original_response(
                content=f"Suggestion failed to be created."
            )

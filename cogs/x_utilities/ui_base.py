# utils/ui_base.py 

import discord

class BaseCogView(discord.ui.View):
    def __init__(self, *, cog, timeout=None):
        super().__init__(timeout=timeout)
        self.cog = cog

class BaseCogButton(discord.ui.Button):
    def __init__(self, *, user_id, cog, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.cog = cog


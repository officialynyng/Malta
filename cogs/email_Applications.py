import discord
import imaplib
import email
import re
from discord.ext import tasks, commands
from email_config import (
    IMAP_SERVER,
    EMAIL_ACCOUNT,
    EMAIL_PASSWORD,
    DISCORD_APPLICATION_CHANNEL_ID
)

class EmailListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("📧 EmailListener initialized.")
        self.check_email.start()

    @tasks.loop(minutes=120)  # check every 2 hours
    async def check_email(self):
        print("🔁 Checking email...")
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            print(f"✅ Connected to IMAP server: {IMAP_SERVER}")
            mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            print(f"🔓 Logged in as: {EMAIL_ACCOUNT}")

            mail.select("inbox")
            status, messages = mail.search(None, 'UNSEEN')
            message_numbers = messages[0].split()
            print(f"📥 Unseen messages: {len(message_numbers)}")

            for num in message_numbers:
                print(f"📦 Fetching email ID: {num}")
                _, msg_data = mail.fetch(num, '(RFC822)')
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = msg.get("Subject", "[No Subject]")
                sender = msg.get("From", "[Unknown Sender]")
                body = self._extract_plaintext(msg)

                # Clean and strip trailing filler
                body = body.split("Powered by Elementor")[0]

                # Extract fields
                username = re.search(r"Username:\s*(.*)", body)
                steam = re.search(r"Steam Profile Link::\s*(.*)", body)
                discord_id = re.search(r"Discord ID #::\s*(.*)", body)
                reason = re.search(r"Why you want to join::\s*(.*?)\n\n", body, re.DOTALL)

                username = username.group(1).strip() if username else "N/A"
                steam = steam.group(1).strip() if steam else "N/A"
                discord_id = discord_id.group(1).strip() if discord_id else "N/A"
                reason = reason.group(1).strip() if reason else "N/A"

                app_channel = self.bot.get_channel(DISCORD_APPLICATION_CHANNEL_ID)
                if app_channel:
                    await app_channel.send(
                        f"🛡️ **New Malta Application**\n"
                        f"**Username:** {username}\n"
                        f"**Steam Profile:** {steam}\n"
                        f"**Discord ID:** <@{discord_id}> (`{discord_id}`)\n"
                        f"**Reason for Joining:**\n```{reason}```"
                    )
                    print("✅ Posted to application channel.")
                else:
                    print("❌ Application channel not found.")

            mail.logout()
            print("🔒 Logged out from mail server.")

        except Exception as e:
            print(f"❌ Email check failed: {e}")

    def _extract_plaintext(self, msg):
        print("🔍 Extracting plaintext...")
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    print("✅ Found text/plain part.")
                    return part.get_payload(decode=True).decode(errors="ignore")
        else:
            print("📄 Email is not multipart.")
            return msg.get_payload(decode=True).decode(errors="ignore")
        print("⚠️ No readable body.")
        return "(No readable body)"

async def setup(bot):
    await bot.add_cog(EmailListener(bot))
    print("🧩 EmailListener cog loaded.")

import asyncio
import discord
import os.path
import os
import logging
import random

from robobrowser import RoboBrowser

from urllib.parse import urljoin
from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO


class Genote:
    """Periodically check a site for changes"""

    DATA_FOLDER = "data/genote"
    CONFIG_FILE_PATH = DATA_FOLDER + "/config.json"

    CONFIG_DEFAULT = {"url": "https://www.usherbrooke.ca/genote/application/etudiant/cours.php",
                      "form_id": "authentification", "login": "", "password": "", "last_save": {},
                      "loop_time": 180, "announcement_channel": "355384548671881220", "notifs": []}

    CHANNEL_SET = ":white_check_mark: Le channel d'annonce des nouvelles notes est maintenant: <#{}>."
    ANNOUNCEMENT = "Une nouvelle note est disponible sur Genote pour **{}**."
    LOOP_SET = ":white_check_mark: Le temps entre chaque vérification est maintenant: **{}** secondes."
    WILL_NOTIFY = "🔔"
    WONT_NOTIFY = "🔕"

    def __init__(self, bot):
        self.bot = bot
        self.check_configs()
        self.load_data()
        self.LOGGER = logging.Logger("genote")
        self.LOGGER.setLevel(logging.INFO)
        self.LOGGER.addHandler(logging.StreamHandler())
        asyncio.ensure_future(self.periodic_check())

    # Commands
    @commands.group(name="genote", pass_context=True, invoke_without_command=True)
    async def genote(self, ctx):
        """Commandes de gestion du module Genote"""
        await self.bot.send_cmd_help(ctx)

    @genote.command(name="notify", pass_context=True)
    async def _genote_notify(self, ctx, should_notify: str="no"):
        """Définis si oui ou non tu veux recevoir des notifications

        Si `should_notify` vaut `yes`, `y`, `1`, `true` ou `t`, alors tu recevras les notifications 🔔
        Tout autre chaîne de caractères sera considérée comme ne pas vouloir de notifications 🔕"""
        message = ctx.message
        will_notify = should_notify.lower() in self.YES_STRINGS
        self.config["notifs"] = list(set(self.config["notifs"]) | {message.author.id})
        self.save_data()
        await self.bot.add_reaction(message, self.WILL_NOTIFY if will_notify else self.WONT_NOTIFY)

    @genote.command(name="channel", pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def genote_channel(self, ctx, new_channel: discord.Channel):
        """Change le channel d'annonce des nouvelles notes disponibles"""
        message = ctx.message
        channel = message.channel
        self.config["announcement_channel"] = new_channel.id
        self.save_data()
        await self.bot.send_message(channel, self.CHANNEL_SET.format(new_channel.id))

    @genote.command(name="loop_time", pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def genote_loop_time(self, ctx, loop_time: int):
        """Change le nombre de temps (en secondes) entre chaque vérification des changements de note"""
        message = ctx.message
        channel = message.channel
        self.config["loop_time"] = loop_time
        self.save_data()
        await self.bot.send_message(channel, self.LOOP_SET.format(loop_time))

    # Utilities
    async def periodic_check(self):
        await self.bot.wait_until_ready()
        self.announcement_channel = self.bot.get_channel(self.config["announcement_channel"])
        while self == self.bot.get_cog(self.__class__.__name__):
            await self.run()
            random_offset = (random.random() * 10) - 5
            await asyncio.sleep(config["loop_time"] + random_offset)

    async def run(self):
        """
        Fetches the content from Genote, parses it, then compare it with an old version of the same
        page. If differences are found, logs it.
        """
        self.LOGGER.info("Booting... ")
        try:
            browser = RoboBrowser(session=None,
                                  history=False,
                                  timeout=1000,
                                  allow_redirects=True,
                                  cache=False,
                                  parser="html.parser")
            self.__connect_to_genote(browser)
        except Exception as e:
            self.LOGGER.critical("Something bad happened during the browsing: {}".format(e))
        else:
            classes_urls = self.get_classes_urls(browser.select("#contenu_principal table tbody tr"))
            classes_dictionary = self.get_classes(browser, classes_urls)
            await self.check_differences(classes_dictionary)

    async def check_differences(self, classes_dictionary):
        """
        Compares the old classes dictionary with the new one. If there are differences, log them.
        :param classes_dictionary: The new classes_dictionary to be compared with the old one
        """
        self.LOGGER.info("Check for differences")
        differences = self.calculate_differences(self.config["last_save"], classes_dictionary)
        if len(differences) > 0:
            self.LOGGER.warning("DIFFERENCE FOUND BETWEEN OLD AND NEW: old: {}, new: {}"
                                .format(self.config["last_save"], classes_dictionary))
            self.config["last_save"] = classes_dictionary
            self.save_data()
            announcement = self.ANNOUNCEMENT.format(", ".join(differences))
            await self.bot.send_message(self.announcement_channel, announcement)
            for m_id in self.config["notifs"]:
                m = self.announcement_channel.server.get_member(m_id)
                if m is not None:
                    await self.bot.send_message(m, announcement)
        else:
            self.LOGGER.info("Did verification, no difference was found between old and new data.")

    def get_classes(self, browser, classes_urls):
        result = {}
        for class_name, class_url in classes_urls.items():
            full_url = urljoin(self.config["url"], class_url)
            browser.open(full_url)
            tp_rows = browser.select("#contenu_principal table tbody tr")
            tps = []
            for tp_row in tp_rows:
                if "footer" not in tp_row.get("class", []):
                    title = ""
                    for title_part in tp_row.td.stripped_strings:
                        title += title_part
                    tps.append(title)
            result[class_name] = tps
        return result

    def calculate_differences(self, a, b):
        updates = set()
        for k, v in b.items():
            if k in a and len(v) > len(a[k]) and len(v) > 0:
                new_titles = set(v) - set(a[k])
                updates.update({k + " - " + title for title in new_titles})
        return updates

    def get_classes_urls(self, table_rows):
        classes = {}
        for row in table_rows:
            title = row.td.string
            consulter_td = row.find_all("td")[-1]
            if consulter_td.a is not None:
                classes[title] = consulter_td.a.get("href")
        return classes

    def __connect_to_genote(self, browser):
        """
        Using the provided browser, connects to Genote and redirects to the page with
        the desired data.
        :param browser: The browser object to navigate
        """
        self.LOGGER.info("Opening url: {}".format(self.config["url"]))
        browser.open(self.config["url"])
        self.LOGGER.info("Looking for form: {}".format(self.config["form_id"]))
        form = browser.get_form(self.config["form_id"])
        self.LOGGER.debug("Found form: {}".format(form))
        self.LOGGER.info("Filling login and password for user: {}".format(self.config["login"]))
        form["username"].value = self.config["login"]
        form["password"].value = self.config["password"]
        browser.submit_form(form)
        self.LOGGER.info("Going to: {}".format(self.config["url"]))
        browser.open(self.config["url"])

    # Config
    def check_configs(self):
        self.check_folders()
        self.check_files()

    def check_folders(self):
        if not os.path.exists(self.DATA_FOLDER):
            print("Creating data folder...")
            os.makedirs(self.DATA_FOLDER, exist_ok=True)

    def check_files(self):
        self.check_file(self.CONFIG_FILE_PATH, self.CONFIG_DEFAULT)

    def check_file(self, f, default):
        if not dataIO.is_valid_json(f):
            print("Creating empty " + f + "...")
            dataIO.save_json(f, default)

    def load_data(self):
        self.config = dataIO.load_json(self.CONFIG_FILE_PATH)

    def save_data(self):
        dataIO.save_json(self.CONFIG_FILE_PATH, self.config)


def setup(bot):
    # Creating the cog
    c = Genote(bot)
    # Finally, add the cog to the bot.
    bot.add_cog(c)

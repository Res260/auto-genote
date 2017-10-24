import asyncio
import discord
import os.path
import os
import logging

from robobrowser import RoboBrowser

from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO


class Genote:
    """Periodically check a site for changes"""

    DATA_FOLDER = "data/genote"
    CONFIG_FILE_PATH = DATA_FOLDER + "/config.json"

    CONFIG_DEFAULT = {"url": "https://www.usherbrooke.ca/genote/application/etudiant/cours.php",
                      "form_id": "authentification", "login": "", "password": "", "last_save": {},
                      "loop_time": 180, "announcement_channel": "355384548671881220"}

    CHANNEL_SET = ":white_check_mark: Le channel d'annonce des nouvelles notes est maintenant: <#{}>."
    ANNOUNCEMENT = "Une nouvelle note est disponible sur Genote!"
    LOOP_SET = ":white_check_mark: Le temps entre chaque vérification est maintenant: **{}** secondes."

    def __init__(self, bot):
        self.bot = bot
        self.check_configs()
        self.load_data()
        self.LOGGER = logging.Logger("mainnn")
        self.LOGGER.setLevel(logging.INFO)
        self.LOGGER.addHandler(logging.StreamHandler())
        asyncio.ensure_future(self.periodic_check())

    # Events
    def __unload(self):
        pass

    # Commands
    @commands.group(name="genote", pass_context=True, invoke_without_command=True)
    async def genote(self, ctx):
        """Commandes de gestion du module Genote"""
        await self.bot.send_cmd_help(ctx)

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
            await asyncio.sleep(self.config["loop_time"])

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
            classes_dictionary = self.__get_classes_dictionary(browser.select("tbody")[0].findAll("tr"))
            await self.check_differences(classes_dictionary)

    async def check_differences(self, classes_dictionary):
        """
        Compares the old classes dictionary with the new one. If there are differences, log them.
        :param classes_dictionary: The new classes_dictionary to be compared with the old one
        """
        self.LOGGER.info("Check for differences")
        if classes_dictionary != self.config["last_save"]:
            self.LOGGER.warning("DIFFERENCE FOUND BETWEEN OLD AND NEW: old: {}, new: {}"
                                .format(self.config["last_save"], classes_dictionary))
            self.config["last_save"] = classes_dictionary
            self.save_data()
            await self.bot.send_message(self.announcement_channel, self.ANNOUNCEMENT)
        else:
            self.LOGGER.info("Did verification, no difference was found between old and new data.")

    def __get_classes_dictionary(self, table_rows):
        """
        :param table_rows: The list of html tags of the rows of the classes
        :return: A dictionary with the class name as key and a the grade count as value
        """
        self.LOGGER.info("Parsing HTML to find data.")
        classes = {}
        for row in table_rows:
            row_data = row.findAll("td")
            row_data_pretty = []
            for data in row_data:
                row_data_pretty.append(data.decode_contents())
            classes[row_data_pretty[0]] = row_data_pretty[4]
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

import configparser as cp
import json
import logging

from robobrowser import RoboBrowser


class AutoGenote:
    def __init__(self):
        self.LOGGER = logging.Logger("main")
        self.LOGGER.addHandler(logging.StreamHandler())

    def run(self):
        self.LOGGER.info("Booting... ")
        config = self.__get_config_file_data()
        try:
            browser = RoboBrowser(session=None,
                                  history=False,
                                  timeout=1000,
                                  allow_redirects=True,
                                  cache=False,
                                  parser="html.parser")
            self.__connect_to_genote(browser, config)
        except Exception as e:
            self.LOGGER.critical("Something bad happened during the browsing: {}".format(e))
            exit(1)

        classes_dictionary = self.__get_classes_dictionary(browser.select("tbody")[0].findAll("tr"))
        self.__compare_warn_and_save(classes_dictionary, config["GENERAL"]["save_file"])

    def __compare_warn_and_save(self, classes_dictionary, save_file):
        """
        Compares the old classes dictionary with the new one. If there are differences, log them.
        :param classes_dictionary: The new classes_dictionary to be compared with the old one
        :param save_file: the name of the save file to save and fetch the classes_dictionary.
        """
        try:
            self.LOGGER.info("Open old save file")
            with open(save_file, 'rb') as save_file_stream:
                old_classes_dictionary = json.loads(save_file_stream.read(), encoding="UTF-8")

                self.LOGGER.info("Check for differences")
                if self.dict_has_differences(classes_dictionary, old_classes_dictionary):
                    self.LOGGER.warning("DIFFERENCE FOUND BETWEEN OLD AND NEW: old: {}, new: {}"
                                        .format(old_classes_dictionary, classes_dictionary))
                    self.save_classes_dict(classes_dictionary, save_file)
                else:
                    self.LOGGER.info("Did verification, no difference was "
                                     "found between old and new data.")
        except FileNotFoundError:
            self.LOGGER.info("Old save file did not exist, create one with data.")
            self.save_classes_dict(classes_dictionary, save_file)

    def save_classes_dict(self, classes_dictionary, file_name):
        """
        Serializes classes_dicionary in UTF-8 and saves it to file_name.
        :param classes_dictionary: The dict to be saved to a file
        :param file_name: The file name
        """
        self.LOGGER.info("Saving classes_dictionary to file: {} --> {}"
                         .format(file_name, classes_dictionary))
        with open(file_name, 'wb') as save_file:
            save_file.write(json.dumps(classes_dictionary, ensure_ascii=False).encode("UTF-8"))

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

    def __connect_to_genote(self, browser, config):
        self.LOGGER.info("Opening url: {}".format(config["GENERAL"]["url"]))
        browser.open(config["GENERAL"]["url"])
        self.LOGGER.info("Looking for form: {}".format(config["GENERAL"]["form_id"]))
        form = browser.get_form(config["GENERAL"]["form_id"])
        self.LOGGER.debug("Found form: {}".format(form))
        self.LOGGER.info(
            "Filling login and password for user: {}".format(config["CREDIDENTIALS"]["login"]))
        form["username"].value = config["CREDIDENTIALS"]["login"]
        form["password"].value = config["CREDIDENTIALS"]["password"]
        browser.submit_form(form)
        self.LOGGER.info("Going to: {}".format(config["GENERAL"]["url"]))
        browser.open(config["GENERAL"]["url"])

    def __get_config_file_data(self):
        """
        :return: The configuration file reader. To access data, use config["SECTIONNAME"]["keyname"]
        """
        file = "config.file"
        self.LOGGER.info("Fetching config file: {}".format(file))
        config = cp.ConfigParser()
        config.read(file)
        return config

    @staticmethod
    def dict_has_differences(dict1, dict2):
        """
        :param dict1: First dictionary to compare
        :param dict2: Second dictionary to compare
        :return: True if dict1 and dict2 are not equivalent
        """
        has_differences = False
        if len(dict1) != len(dict2):
            has_differences = True
        else:
            for key, value in dict1.items():
                if key not in dict2:
                    has_differences = True
                else:
                    if not value == dict2[key]:
                        has_differences = True
        return has_differences


if __name__ == '__main__':
    AutoGenote().run()

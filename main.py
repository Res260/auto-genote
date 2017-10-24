import configparser as cp
import json
import logging

from robobrowser import RoboBrowser

LOGGER = logging.Logger("main")
LOGGER.addHandler(logging.StreamHandler())


def main():
    LOGGER.info("Booting... ")
    config = get_config_file_data()
    try:
        browser = RoboBrowser(session=None,
                              history=False,
                              timeout=1000,
                              allow_redirects=True,
                              cache=False,
                              parser="html.parser")
        connect_to_genote(browser, config)
    except Exception as e:
        LOGGER.error("Something bad happened during the browsing: {}".format(e))

    classes_dictionary = get_classes_dictionary(browser.select("tbody")[0].findAll("tr"))
    compare_warn_and_save(classes_dictionary, config["GENERAL"]["save_file"])


def compare_warn_and_save(classes_dictionary, save_file):
    """
    Compares the old classes dictionary with the new one. If there are differences, log them.
    :param classes_dictionary: The new classes_dictionary to be compared with the old one
    :param save_file: the name of the save file to save and fetch the classes_dictionary.
    """
    try:
        LOGGER.info("Open old save file")
        with open(save_file, 'rb') as save_file:
            old_classes_dictionary = json.loads(save_file.read(), encoding="UTF-8")

            LOGGER.info("Check for differences")
            if dict_has_differences(classes_dictionary, old_classes_dictionary):
                LOGGER.warning("DIFFERENCE FOUND BETWEEN OLD AND NEW: old: {}, new: {}"
                               .format(old_classes_dictionary, classes_dictionary))
                save_classes_dict(classes_dictionary, save_file)
            else:
                LOGGER.info("Did verification, no difference was found between old and new data.")
    except FileNotFoundError:
        LOGGER.info("Old save file did not exist, create one with data.")
        save_classes_dict(classes_dictionary, save_file)


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
            if not key in dict2:
                has_differences = True
            else:
                if not value == dict2[key]:
                    has_differences = True
    return has_differences


def save_classes_dict(classes_dictionary, file_name):
    """
    Serializes classes_dicionary in UTF-8 and saves it to file_name.
    :param classes_dictionary: The dict to be saved to a file
    :param file_name: The file name
    """
    LOGGER.info(
        "Saving classes_dictionary to file: {} --> {}".format(file_name, classes_dictionary))
    with open(file_name, 'wb') as save_file:
        save_file.write(json.dumps(classes_dictionary, ensure_ascii=False).encode("UTF-8"))


def get_classes_dictionary(table_rows):
    """

    :param table_rows: The list of html tags of the rows of the classes
    :return: A dictionary with the class name as key and a dictionary of the class' informations
             as value: {class: string, grades_count: int}
    """
    LOGGER.info("Parsing HTML to find data.")
    classes = {}
    for row in table_rows:
        row_data = row.findAll("td")
        row_data_pretty = []
        for data in row_data:
            row_data_pretty.append(data.decode_contents())
        data_dictionary = {
            "class": row_data_pretty[0],
            "grades_count": row_data_pretty[4]
        }
        classes[data_dictionary["class"]] = data_dictionary
    return classes


def connect_to_genote(browser, config):
    LOGGER.info("Opening url: {}".format(config["GENERAL"]["url"]))
    browser.open(config["GENERAL"]["url"])
    LOGGER.info("Looking for form: {}".format(config["GENERAL"]["form_id"]))
    form = browser.get_form(config["GENERAL"]["form_id"])
    LOGGER.debug("Found form: {}".format(form))
    LOGGER.info("Filling login and password for user: {}".format(config["CREDIDENTIALS"]["login"]))
    form["username"].value = config["CREDIDENTIALS"]["login"]
    form["password"].value = config["CREDIDENTIALS"]["password"]
    browser.submit_form(form)
    LOGGER.info("Going to: {}".format(config["GENERAL"]["url"]))
    browser.open(config["GENERAL"]["url"])


def get_config_file_data():
    """
    :return: The configuration file reader. To access data, use config["SECTIONNAME"]["keyname"]
    """
    file = "config.file"
    LOGGER.info("Fetching config file: {}".format(file))
    config = cp.ConfigParser()
    config.read(file)
    return config


if __name__ == '__main__':
    main()

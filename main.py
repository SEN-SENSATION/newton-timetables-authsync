from datetime import datetime
import json
import logging
import os
from pprint import pprint
from time import sleep
from typing import TypedDict

import inquirer
import certifi
import coloredlogs
import gspread
import pymongo
from oauth2client.service_account import ServiceAccountCredentials
from tqdm import tqdm

from utils.filter import filter_unwanted

ConfigDict = TypedDict("ConfigDict", {"DB_URI": str, "SPREADSHEET_ID": str})

logger = logging.getLogger(__name__)
coloredlogs.install(level="LOG", logger=logger)


class Main:
    config: ConfigDict
    dbClient: pymongo.MongoClient
    sheet: gspread.Spreadsheet

    selected_year: list[str]

    read_records: list[dict]
    operator_name: str

    reset_auth_db: bool = False

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(self):

        logger.info("Initializing the program")
        self.operator_name = inquirer.text("What is your name?")

        self.load_config()
        self.connect_db()
        self.ask_year()
        logger.info(self.selected_year)
        self.open_spreadsheet()
        self.read_worksheet()

        reset_db = inquirer.confirm(
            "Do you want to reset the auth database? (for student only)"
        )
        confrim_reset_db = (
            inquirer.confirm(
                "Are you sure you want to reset the auth database? (for student only)"
            )
            if reset_db
            else None
        )

        self.reset_auth_db = True if confrim_reset_db else False
        final_confrim = inquirer.confirm("Are you sure you want to continue?")
        if not final_confrim:
            logger.critical("Aborting - User has cancelled the program")
            quit()

        self.write_db()

        logger.info("Successfully finished the task. Exiting")
        exit()

    def ask_year(self):

        questions = [
            inquirer.Checkbox(
                "year",
                message="What year are you instrested in syncing? (Spacebar to select, Enter to continue)",
                choices=[
                    "Year 5      (Junior)",
                    "Year 6      (Junior)",
                    "Year 7      (Junior)",
                    "Year 8      (Senior)",
                    "Year 9      (Senior)",
                    "Year 10     (Senior)",
                    "Year 11     (Senior)",
                    "Year 12 Med (Senior)",
                    "Year 12 Com (Senior)",
                    "Year 12 Hum (Senior)",
                    "Year 12 NBS (Senior)",
                    "Year 13 Med (Senior)",
                    "Year 13 Com (Senior)",
                    "Year 13 Hum (Senior)",
                    "Year 13 NBS (Senior)",
                ],
            )
        ]
        answers = inquirer.prompt(questions)
        if len(answers["year"]) <= 0:
            raise ValueError("No year selected")
        self.selected_year = [
            x.split()[1] + " Room"
            if int(x.split()[1]) < 12
            else x.split()[1] + " " + x.split()[2]
            for x in answers["year"]
        ]
        print(self.selected_year)

    def connect_db(self):
        logger.info("trying to connect to the database")
        self.dbClient = pymongo.MongoClient(
            self.config["DB_URI"], tlsCAFile=certifi.where()
        )

    def load_config(self):
        logger.info("trying to read the config file")
        if os.path.exists("config.json"):
            with open("config.json") as f:
                config = json.load(f)
                if not all(c in config for c in ("DB_URI", "SPREADSHEET_ID")):
                    raise ValueError("Value missing from the config file")
                print(config)
                self.config = config
        else:
            raise ValueError("config.json not found")

    def open_spreadsheet(self):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", self.scope
        )
        client = gspread.authorize(creds)

        logger.info("Trying to open the spreadsheet.")
        self.sheet = client.open_by_key(self.config["SPREADSHEET_ID"])
        logger.info("Successfully opened the spreadsheet")

    def read_worksheet(self):

        all_raw_records = []
        logger.info("Reading the worksheet")
        for i in tqdm(range(len(self.selected_year))):
            year_records = self.sheet.worksheet(
                f"Year {self.selected_year[i]}"
            ).get_all_records()
            all_raw_records.extend(year_records)

        filtered_records = filter_unwanted(records=all_raw_records)

        self.read_records = filtered_records

    def write_db(self):
        if self.reset_auth_db:
            for year in self.selected_year:
                result = self.dbClient["auth"]["users"].delete_many(
                    {"year": int(year.split()[0]), "type": "student"}
                )
            logger.info(f"deleted {result.deleted_count} users")

        for i in tqdm(range(self.read_records["counts"])):
            this_record = self.read_records["data"][i]

            prepared_data = {
                "firstName": this_record["Name"].split()[0],
                "lastName": this_record["Name"].split()[1],
                "nickName": this_record["Nickname"],
                "email": this_record["Email"],
                "year": this_record["Year"],
                "room": this_record["Room"],
                "track": this_record.get("Track", None),
                "type": "student",
                "issuedId": "N00000",
                "elective": {
                    "english": this_record.get("English", None),
                    "activity": "Creative Drama",
                },
                "lastSync": datetime.now(),
                "syncedBy": self.operator_name,
            }

            if self.dbClient["auth"]["users"].find_one({"email": this_record["Email"]}):
                self.dbClient["auth"]["users"].update_one(
                    {"email": this_record["Email"]}, {"$set": prepared_data}
                )
            else:
                self.dbClient["auth"]["users"].insert_one(
                    {
                        **prepared_data,
                        "password": "$2b$12$Br3v95wIpDGgaFyttKheyuorkTuH8OE6IaBflcoAIHAmBs/hSem/S",
                    }
                )


if __name__ == "__main__":
    Main()

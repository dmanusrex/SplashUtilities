"""Update functions for Splash Utilities"""

from config import appConfig
from threading import Thread
import requests
import pyodbc  # type: ignore
import csv
import logging


def get_active_roster() -> list:
    """Get the active roster from the API"""

    URL = "https://rankings.edey.org/api/ActiveRoster"
    headers = {
        "User-Agent": "Chrome/126.0.0.0",
        "Accept": "*/*",
    }

    # Get the response and handle common errors

    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as ex:
        logging.error("Error retrieving Active Roster: %s", ex)
        return []

    # Be sure to convert SNC ID to a string to match the database field
    roster = response.json()
    for athlete in roster:
        athlete["SNC_ID"] = str(int(athlete["SNC_ID"]))

    # dump the first 5 records to the log
    logging.info("Active Roster Retrieved - Total Athletes = %s", len(roster))
    #for i in range(5):
    #    logging.info("  %s %s ID: %s", roster[i]["Family_Name"], roster[i]["Given_Name"] , roster[i]["SNC_ID"])
    return roster


class Update_Clubs(Thread):
    def __init__(self, config: appConfig):
        super().__init__()
        self._config: appConfig = config

    def run(self):
        logging.info("Updating Region (Province) Code on all Clubs...")

        _splash_db_file = self._config.get_str("splash_db")
        _splash_db_driver = "{Microsoft Access Driver (*.mdb, *.accdb)}"
        _csv_file = self._config.get_str("csv_file")
        _update_db = self._config.get_bool("update_database")

        try:
            logging.info("Reading CSV File...")
            data = self.csv_to_dict(_csv_file)
            logging.info("  CSV File Read - Total Clubs = %s", len(data))
        except FileNotFoundError:
            logging.error("CSV File not found")
            return

        logging.info("Reading Splash Database...")

        connection_string = "DRIVER={};DBQ={};".format(_splash_db_driver, _splash_db_file)
        try:
            con = pyodbc.connect(connection_string)
        except pyodbc.Error as ex:
            logging.error("Error connecting to database")
            logging.error(ex)
            return

        SQL = "SELECT CLUBID, CODE, NAME, NATION, REGION " "FROM CLUB "

        # iterate over the returned rows and set the region code to the province field from the CSV file

        cursor = con.cursor()
        try:
            cursor.execute(SQL)
            rows = cursor.fetchall()
        except:
            logging.error("Error reading database")
            return

        logging.info("  Splash Database Read - Total Clubs = %s", len(rows))

        _count_clubs = 0
        _count_club_names = 0

        for row in rows:
            club_id = row[0]
            club_code = row[1]
            club_name = row[2]
            club_nation = row[3]
            club_region = row[4]

            # if the club is not Canadian, skip it
            if club_nation != "CAN":
                continue

            mylist = list(filter(lambda person: person["Club Code"] == club_code, data))

            if len(mylist) != 1:
                logging.error("Club Code %s not found in CSV file", club_code)
                continue

            province = mylist[0]["Province"]
            clubname = mylist[0]["Club Name"]
            preferred_club_name = mylist[0]["Preferred Club Name"]

            # update the region code in the database only if it is different from the province field in the CSV file

            if club_region != province:
                SQL = "UPDATE CLUB SET REGION = ? WHERE CLUBID = ? "
                _count_clubs += 1
                if _update_db:
                    cursor.execute(SQL, (province, club_id))
                    con.commit()
                    logging.info("Club Code %s updated to Province %s", club_code, province)
                else:
                    logging.info("Would have updated Club Code %s to Province %s", club_code, province)

            # Set the preferred club long name if one is set.
            if preferred_club_name is not None:
                if (preferred_club_name != club_name) and (len(preferred_club_name) > 1):
                    SQL = "UPDATE CLUB SET NAME = ? WHERE CLUBID = ? "
                    _count_club_names += 1
                    if _update_db:
                        cursor.execute(SQL, (preferred_club_name, club_id))
                        con.commit()
                    logging.info(
                        "Club Code %s not preferred name. <%s> updated to <%s>",
                        club_code,
                        club_name,
                        preferred_club_name,
                    )

        con.close()
        logging.info("Update Complete - %s Clubs updated, %s Club Names updated", _count_clubs, _count_club_names)

    def csv_to_dict(self, file_path):
        data_dict = []
        with open(file_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                data_dict.append(row)
        return data_dict


class Update_Para(Thread):
    def __init__(self, config: appConfig):
        super().__init__()
        self._config: appConfig = config

    def run(self):
        logging.info("Updating Para and exception codes on all Athletes...")

        _splash_db_file = self._config.get_str("splash_db")
        _splash_db_driver = self._config.get_str("splash_db_driver")
        _update_db = self._config.get_bool("update_database")
        _update_sdms = self._config.get_bool("update_sdms")
        _para_level = self._config.get_str("para_level")
        _para_level_list = ["1","2","3","Int"]
        _para_levels = _para_level_list[_para_level_list.index(_para_level):]

        logging.info("Database updates: %s", _update_db)
        logging.info("SDMS updates: %s", _update_sdms)

        logging.info("Opening Splash Database")

        connection_string = "DRIVER={};DBQ={};".format(_splash_db_driver, _splash_db_file)
        try:
            con = pyodbc.connect(connection_string)
        except pyodbc.Error as ex:
            logging.error("Error connecting to database")
            logging.error(ex)

        # Get the active roster
        roster = get_active_roster()
        if len(roster) == 0:
            con.close()
            logging.error("No Active Roster")
            return

        # Get all the Athlete Data

        SQL = "SELECT ATHLETEID, FIRSTNAME, LASTNAME, LICENSE, HANDICAPEX, HANDICAPS, HANDICAPSB, HANDICAPSM, SDMSID, NATION FROM ATHLETE"

        # iterate over the returned rows and set the region code to the province field from the CSV file

        cursor = con.cursor()
        try:
            cursor.execute(SQL)
            rows = cursor.fetchall()
        except pyodbc.Error as ex:
            logging.error("Error reading database")
            # log the error reason and return
            logging.error(ex)
            con.close()
            return

        for row in rows:
            athlete_id = row[0]
            firstname = row[1]
            lastname = row[2]
            license = row[3]
            handicapex = row[4]
            handicaps = row[5]
            handicapsb = row[6]
            handicapsm = row[7]
            sdmsid = row[8]
            nation = row[9]

            # find the athlete in the roster

            if nation != "CAN":
                continue

            mylist = list(filter(lambda person: str(person["SNC_ID"]) == license, roster))

            if len(mylist) != 1:
                #logging.error("Athlete %s %s (%s) not found in Active Roster", firstname, lastname, license)
                continue
            # print("Found Para for ", firstname, lastname, " in Active Roster")
            athlete = mylist[0]

            # Check if the fields match the roster individually.  IF not, log it and update it

            if athlete["S"] in ("NE", "PSPI", "PSVI", "PSII", "PI","II","VI", "") or athlete["S"] is None:
                athlete["S"] = "0"
            if athlete["SB"] in ("NE", "PSPI", "PSVI", "PSII", "PI","II","VI","") or athlete["SB"] is None:
                athlete["SB"] = "0"
            if athlete["SM"] in ("NE", "PSPI", "PSVI", "PSII", "PI","II","VI", "") or athlete["SM"] is None:
                athlete["SM"] = "0"

            if athlete["SDMS_ID"] is None:
                athlete["SDMS_ID"] = "0"
            else:
                athlete["SDMS_ID"] = str(int(athlete["SDMS_ID"]))

            if str(athlete["Exceptions"]) != str(handicapex):
                logging.error(
                    "Athlete %s %s exceptions mismatch. Splash: %s Roster: %s",
                    firstname,
                    lastname,
                    handicapex,
                    athlete["Exceptions"],
                )
                if _update_db:
                    SQL = "UPDATE ATHLETE SET HANDICAPEX = ? WHERE ATHLETEID = ? "
                    con.execute(SQL, (str(athlete["Exceptions"]), athlete_id))
                    con.commit()

            if str(athlete["S"]) != str(handicaps):
                logging.error(
                    "Athlete %s %s S sport class mismatch. Splash: %s Roster: %s",
                    firstname,
                    lastname,
                    handicaps,
                    athlete["S"],
                )
                if _update_db:
                    SQL = "UPDATE ATHLETE SET HANDICAPS = ? WHERE ATHLETEID = ? "
                    con.execute(SQL, (athlete["S"], athlete_id))
                    con.commit()

            if str(athlete["SB"]) != str(handicapsb):
                logging.error(
                    "Athlete %s %s SB sport class mismatch. Splash: %s Roster: %s",
                    firstname,
                    lastname,
                    handicapsb,
                    athlete["SB"],
                )
                if _update_db:
                    SQL = "UPDATE ATHLETE SET HANDICAPSB = ? WHERE ATHLETEID = ? "
                    con.execute(SQL, (athlete["SB"], athlete_id))
                    con.commit()

            if str(athlete["SM"]) != str(handicapsm):
                logging.error(
                    "Athlete %s %s SM sport class mismatch. Splash: %s Roster: %s",
                    firstname,
                    lastname,
                    handicapsm,
                    athlete["SM"],
                )
                if _update_db:
                    SQL = "UPDATE ATHLETE SET HANDICAPSM = ? WHERE ATHLETEID = ? "
                    con.execute(SQL, (athlete["SM"], athlete_id))
                    con.commit()

            if (athlete["SDMS_ID"] != str(sdmsid))  and (athlete["Level"] == "Int"):
                logging.error(
                    "Athlete %s %s SDMSID mismatch. Splash: %s Roster: %s",
                    firstname,
                    lastname,
                    sdmsid,
                    athlete["SDMS_ID"],
                )
                if _update_db & _update_sdms:
                    SQL = "UPDATE ATHLETE SET SDMSID = ? WHERE ATHLETEID = ? "
                    con.execute(SQL, (athlete["SDMS_ID"], athlete_id))
                    con.commit()

            if str(athlete["Level"]) not in _para_levels:
                logging.warning("Athlete %s %s not at minimum meet level %s has level %s", firstname, lastname, _para_level, athlete["Level"])

        con.close()
        logging.info("Report Complete")


class Update_Para_Names(Thread):
    # Update the para names from the active roster and create a rollback file
    def __init__(self, config: appConfig):
        super().__init__()
        self._config: appConfig = config

    def run(self):
        logging.info("Updating Para Athlete Names...")

        _splash_db_file = self._config.get_str("splash_db")
        _splash_db_driver = "{Microsoft Access Driver (*.mdb, *.accdb)}"
        _update_db = self._config.get_bool("update_database")
        _rollback_file = self._config.get_str("rollback_file")

        logging.info("Reading Splash Database...")

        connection_string = "DRIVER={};DBQ={};".format(_splash_db_driver, _splash_db_file)
        try:
            con = pyodbc.connect(connection_string)
        except pyodbc.Error as ex:
            logging.error("Error connecting to database")
            logging.error(ex)
            return

        # Get the active roster

        roster = get_active_roster()
        if len(roster) == 0:
            con.close()
            return

        # Get all the Athlete Data

        SQL = "SELECT ATHLETEID, FIRSTNAME, LASTNAME, LICENSE, NATION FROM ATHLETE"

        # iterate over the returned rows and update the firname and lastname fields. Create a rollback file with the old names

        try:
            cursor = con.cursor()
            cursor.execute(SQL)
        except pyodbc.Error as ex:
            logging.error("Error reading database")
            # log the error reason and return
            logging.error(ex)
            con.close()
            return

        rows = cursor.fetchall()

        for row in rows:
            athlete_id = row[0]
            firstname = row[1]
            lastname = row[2]
            license = row[3]
            nation = row[4]

            # find the athlete in the roster

            if nation != "CAN":
                continue

            mylist = list(filter(lambda person: str(person["SNC_ID"]) == license, roster))

            if len(mylist) != 1:  # We only update Para Athletes so skip anyone not on the roster
                continue

            athlete = mylist[0]

            if (firstname != athlete["Given_Name"]) or (lastname != athlete["Family_Name"]):
#                SQL = "UPDATE ATHLETE SET FIRSTNAMEEN = ?, LASTNAMEEN = ? WHERE ATHLETEID = ? "
                SQL = "UPDATE ATHLETE SET FIRSTNAME = ?, LASTNAME = ? WHERE ATHLETEID = ? "

                if _update_db:
                    con.execute(SQL, (athlete["Given_Name"], athlete["Family_Name"], athlete_id))
                    con.commit()
                logging.info(
                    "Athlete %s %s updated to %s %s",
                    firstname,
                    lastname,
                    athlete["Given_Name"],
                    athlete["Family_Name"],
                )

        con.close()
        logging.info("Update Complete")


class Rollback_Names(Thread):
    # Restore the names from a rollback file

    def __init__(self, config: appConfig):
        super().__init__()
        self._config: appConfig = config

    def run(self):
        logging.info("Restoring Athlete Names...")

        _splash_db_file = self._config.get_str("splash_db")
        _splash_db_driver = "{Microsoft Access Driver (*.mdb, *.accdb)}"
        _rollback_file = self._config.get_str("rollback_file")
        _update_db = self._config.get_bool("update_database")

        logging.info("Updating Splash Database...")

        connection_string = "DRIVER={};DBQ={};".format(_splash_db_driver, _splash_db_file)
        con = pyodbc.connect(connection_string)

        with open(_rollback_file, "r") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                athlete_id = row[0]
                firstname = row[1]
                lastname = row[2]

                SQL = "UPDATE ATHLETE SET FIRSTNAME = ?, LASTNAME = ? WHERE ATHLETEID = ? "
                if _update_db:
                    try:
                        con.execute(SQL, (firstname, lastname, athlete_id))
                        con.commit()
                        logging.info("Athlete %s restored to %s %s", athlete_id, firstname, lastname)
                    except pyodbc.Error as ex:
                        logging.error("Error updating database for %s %s", lastname, firstname)
                        logging.error(ex)

        con.close()
        logging.info("Restore Complete")


class Clear_Exceptions(Thread):
    def __init__(self, config: appConfig):
        super().__init__()
        self._config: appConfig = config

    def run(self):
        logging.info("Clearing exceptions on non-para Athletes...")

        _splash_db_file = self._config.get_str("splash_db")
        #        _splash_db_driver = self._config.get_str("splash_db_driver")
        _splash_db_driver = "{Microsoft Access Driver (*.mdb, *.accdb)}"
        _update_db = self._config.get_bool("update_database")

        logging.info("Reading Splash Database...")

        connection_string = "DRIVER={};DBQ={};".format(_splash_db_driver, _splash_db_file)
        
        try:
            con = pyodbc.connect(connection_string)
        except pyodbc.Error as ex:
            logging.error("Error connecting to database")
            logging.error(ex)

        # Get the active roster

        roster = get_active_roster()
        if len(roster) == 0:
            con.close()
            return

        # Get all the Athlete Data

        SQL = "SELECT ATHLETEID, FIRSTNAME, LASTNAME,  LICENSE, HANDICAPEX, NATION FROM ATHLETE"

        # iterate over the returned rows and set the region code to the province field from the CSV file

        cursor = con.cursor()
        try:
            cursor.execute(SQL)
            rows = cursor.fetchall()
        except pyodbc.Error as ex:
            logging.error("Error reading database")
            # log the error reason and return
            logging.error(ex)
            con.close()
            return
        _count_exceptions = 0
        
        for row in rows:
            athlete_id = row[0]
            firstname = row[1]
            lastname = row[2]
            license = row[3]
            handicapex = row[4]
            nation = row[5]

            # find the athlete in the roster

            if nation != "CAN":
                continue

            mylist = list(filter(lambda person: str(person["SNC_ID"]) == license, roster))



            if len(mylist) != 1:
                if handicapex is not None:
                    # Clear the exceptions
                    logging.info("Athlete %s %s exceptions cleared, was set to: %s", firstname, lastname, handicapex)
                    handicapex = None
                    SQL = "UPDATE ATHLETE SET HANDICAPEX = ? WHERE ATHLETEID = ? "
                    _count_exceptions += 1
                    if _update_db:
                        con.execute(SQL, (handicapex, athlete_id))
                        con.commit()

        con.close()
        logging.info("Updatng Exceptions Complete - %s exceptions cleared", _count_exceptions)


class Remove_Initial(Thread):
    def __init__(self, config: appConfig):
        super().__init__()
        self._config: appConfig = config

    def run(self):
        logging.info("Removing the trailing initial from first names...")

        _splash_db_file = self._config.get_str("splash_db")
        _splash_db_driver = "{Microsoft Access Driver (*.mdb, *.accdb)}"
        _update_db = self._config.get_bool("update_database")

        logging.info("Reading Splash Database...")

        connection_string = "DRIVER={};DBQ={};".format(_splash_db_driver, _splash_db_file)
        try: 
            con = pyodbc.connect(connection_string)
        except pyodbc.Error as ex:
            logging.error("Error connecting to database")
            logging.error(ex)
            return

        SQL = "SELECT ATHLETEID, FIRSTNAME, LASTNAME FROM ATHLETE ORDER BY LASTNAME, FIRSTNAME"

        cursor = con.cursor()
        try:
            cursor.execute(SQL)
            rows = cursor.fetchall()
        except pyodbc.Error as ex:
            logging.error("Error reading database")
            # log the error reason and return
            logging.error(ex)
            con.close()
            return

        number_changed = 0

        for row in rows:
            athlete_id = row[0]
            firstname = row[1]
            lastname = row[2]

            # remove the trailing initial from the name

            y = firstname.split(" ")

            if len(y[-1]) == 1:
                y.pop()
                number_changed += 1

                new_firstname = " ".join(y)

#                SQL = "UPDATE ATHLETE SET FIRSTNAMEEN = ? WHERE ATHLETEID = ? "
                SQL = "UPDATE ATHLETE SET FIRSTNAME = ? WHERE ATHLETEID = ? "

                if _update_db:
                    try:
                        cursor.execute(SQL, (new_firstname, athlete_id))
                        con.commit()
                    except pyodbc.Error as ex:
                        logging.error("Error updating database for %s %s", lastname, firstname)
                        logging.error(ex)
                        con.close()
                        return

                logging.info("Athlete %s, %s updated to %s, %s", lastname, firstname, lastname, new_firstname)

        con.close()
        logging.info("Finished Name Updates - %s names changed", number_changed)


if __name__ == "__main__":
    print(get_active_roster())

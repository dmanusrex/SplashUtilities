""" TimeValidate Main Screen """

import os
import pandas as pd
import logging
import customtkinter as ctk  # type: ignore
import webbrowser

import tkinter as tk
from tkinter import filedialog, BooleanVar, StringVar, HORIZONTAL
from typing import Any
from platformdirs import user_config_dir
import pathlib

# Appliction Specific Imports
from config import appConfig
from version import APP_VERSION
from splashutilities_core import Update_Clubs, Update_Para, Remove_Initial, Update_Para_Names, Rollback_Names

tkContainer = Any


class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
    # Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06

    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text.configure(state="normal")
            self.text.insert(tk.END, msg + "\n")
            self.text.configure(state="disabled")
            # Autoscroll to the bottom
            self.text.yview(tk.END)

        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)


class _Splash_Fixes_Tab(ctk.CTkFrame):  # pylint: disable=too-many-ancestors
    """Main Ui Window to apply the various changes"""

    def __init__(self, container: tkContainer, config: appConfig):
        super().__init__(container)
        self._config = config

        self._splash_db = StringVar(value=self._config.get_str("splash_db"))
        self._csv_file = StringVar(value=self._config.get_str("csv_file"))
        self._rollback_file = StringVar(value=self._config.get_str("rollback_file"))

        # self is a vertical container that will contain 3 frames
        self.columnconfigure(0, weight=1)
        # Options Frame - Left and Right Panels

        optionsframe = ctk.CTkFrame(self)
        optionsframe.grid(column=0, row=2, sticky="news")

        filesframe = ctk.CTkFrame(optionsframe)
        filesframe.grid(column=0, row=0, sticky="new", padx=10, pady=10)
        filesframe.rowconfigure(0, weight=1)
        filesframe.rowconfigure(1, weight=1)
        filesframe.rowconfigure(2, weight=1)

        buttonsframe = ctk.CTkFrame(self)
        buttonsframe.grid(column=0, row=4, sticky="news")
        buttonsframe.rowconfigure(0, weight=0)

        # Files Section
        ctk.CTkLabel(filesframe, text="Files").grid(column=0, row=0, sticky="w", padx=10)

        btn1 = ctk.CTkButton(filesframe, text="Database", command=self._handle_splash_db_browse)
        btn1.grid(column=0, row=1, padx=20, pady=10)
        ctk.CTkLabel(filesframe, textvariable=self._splash_db).grid(column=1, row=1, sticky="w", padx=(0, 10))

        btn2 = ctk.CTkButton(filesframe, text="Club CSV File", command=self._handle_csv_file_browse)
        btn2.grid(column=0, row=2, padx=20, pady=10)
        ctk.CTkLabel(filesframe, textvariable=self._csv_file).grid(column=1, row=2, sticky="w", padx=(0, 10))

        btn3 = ctk.CTkButton(filesframe, text="Name Rollback File", command=self._handle_rollback_file_browse)
        btn3.grid(column=0, row=5, padx=20, pady=10)
        ctk.CTkLabel(filesframe, textvariable=self._rollback_file).grid(column=1, row=5, sticky="w", padx=(0, 10))

        # Right options frame for status options

        ctk.CTkLabel(buttonsframe, text="Apply Fixes").grid(column=0, row=0, sticky="w", padx=10, pady=10)

        self.qb_report_btn = ctk.CTkButton(buttonsframe, text="Fix Clubs", command=self._handle_reports_btn)
        self.qb_report_btn.grid(column=0, row=1, sticky="news", padx=20, pady=10)

        self.para_btn = ctk.CTkButton(buttonsframe, text="Fix Para", command=self._handle_fix_para_btn)
        self.para_btn.grid(column=1, row=1, sticky="news", padx=20, pady=10)

        self.remove_initial_btn = ctk.CTkButton(
            buttonsframe, text="Remove Initials", command=self._handle_remove_initial_btn
        )
        self.remove_initial_btn.grid(column=3, row=1, sticky="news", padx=20, pady=10)

        self.update_para_names = ctk.CTkButton(
            buttonsframe, text="Update Para Names", command=self._handle_update_para_names
        )
        self.update_para_names.grid(column=4, row=1, sticky="news", padx=20, pady=10)

        self.rollback_names = ctk.CTkButton(buttonsframe, text="Rollback Names", command=self._handle_rollback_names)
        self.rollback_names.grid(column=5, row=1, sticky="news", padx=20, pady=10)

    def _handle_splash_db_browse(self) -> None:
        splash_db = filedialog.askopenfilename(
            filetypes=[("Splash Database", "*.mdb")],
            defaultextension=".mdb",
            title="Splash Database",
            initialfile=os.path.basename(self._splash_db.get()),
            initialdir=os.path.dirname(self._splash_db.get()),
        )
        if len(splash_db) == 0:
            return
        self._config.set_str("splash_db", splash_db)
        self._splash_db.set(splash_db)

    def _handle_csv_file_browse(self) -> None:
        csv_file = filedialog.askopenfilename(
            filetypes=[("CSV File", "*.csv")],
            defaultextension=".csv",
            title="CSV File",
            initialfile=os.path.basename(self._csv_file.get()),
            initialdir=os.path.dirname(self._csv_file.get()),
        )
        if len(csv_file) == 0:
            return
        self._config.set_str("csv_file", csv_file)
        self._csv_file.set(csv_file)

    def _handle_rollback_file_browse(self) -> None:
        rollback_file = filedialog.askopenfilename(
            filetypes=[("CSV File", "*.csv")],
            defaultextension=".csv",
            title="Rollback File",
            initialfile=os.path.basename(self._rollback_file.get()),
            initialdir=os.path.dirname(self._rollback_file.get()),
        )
        if len(rollback_file) == 0:
            return
        self._config.set_str("rollback_file", rollback_file)
        self._rollback_file.set(rollback_file)

    def buttons(self, newstate) -> None:
        """Enable/disable all buttons"""
        self.qb_report_btn.configure(state=newstate)
        self.para_btn.configure(state=newstate)

    def _handle_reports_btn(self) -> None:
        self.buttons("disabled")

        reports_thread = Update_Clubs(self._config)
        reports_thread.start()
        self.monitor_reports_thread(reports_thread)

    def monitor_reports_thread(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor_reports_thread(thread))
        else:
            self.buttons("enabled")
            thread.join()

    def _handle_fix_para_btn(self) -> None:
        self.buttons("disabled")

        para_thread = Update_Para(self._config)
        para_thread.start()
        self.monitor_reports_thread(para_thread)

    def monitor_para_thread(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor_para_thread(thread))
        else:
            self.buttons("enabled")
            thread.join()

    def _handle_remove_initial_btn(self) -> None:
        self.buttons("disabled")

        remove_initial_thread = Remove_Initial(self._config)
        remove_initial_thread.start()
        self.monitor_remove_initial_thread(remove_initial_thread)

    def monitor_remove_initial_thread(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor_remove_initial_thread(thread))
        else:
            self.buttons("enabled")
            thread.join()

    def _handle_update_para_names(self) -> None:
        self.buttons("disabled")

        para_thread = Update_Para_Names(self._config)
        para_thread.start()
        self.monitor_reports_thread(para_thread)

    def monitor_update_para_names_thread(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor_update_para_names_thread(thread))
        else:
            self.buttons("enabled")
            thread.join()

    def _handle_rollback_names(self) -> None:
        self.buttons("disabled")

        rollback_thread = Rollback_Names(self._config)
        rollback_thread.start()
        self.monitor_rollback_thread(rollback_thread)

    def monitor_rollback_thread(self, thread):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor_rollback_thread(thread))
        else:
            self.buttons("enabled")
            thread.join()


class _Configuration_Tab(ctk.CTkFrame):  # pylint: disable=too-many-ancestors
    """Configuration Tab"""

    def __init__(self, container: tkContainer, config: appConfig):
        super().__init__(container)
        self._config = config

        self._ctk_theme = StringVar(value=self._config.get_str("Theme"))
        self._ctk_size = StringVar(value=self._config.get_str("Scaling"))
        self._ctk_colour = StringVar(value=self._config.get_str("Colour"))

        # self is a vertical container that will contain 3 frames
        self.columnconfigure(0, weight=1)

        optionsframe = ctk.CTkFrame(self)
        optionsframe.grid(column=0, row=2, sticky="news")

        # Options Frame - Left and Right Panels

        left_optionsframe = ctk.CTkFrame(optionsframe)
        left_optionsframe.grid(column=0, row=0, sticky="news", padx=10, pady=10)
        left_optionsframe.rowconfigure(0, weight=1)
        right_optionsframe = ctk.CTkFrame(optionsframe)
        right_optionsframe.grid(column=1, row=0, sticky="new", padx=10, pady=10)
        right_optionsframe.rowconfigure(0, weight=1)
        right_optionsframe.rowconfigure(1, weight=1)
        right_optionsframe.rowconfigure(2, weight=1)
        right_optionsframe.rowconfigure(3, weight=1)

        # Program Options on the left frame

        ctk.CTkLabel(left_optionsframe, text="UI Appearance").grid(column=0, row=0, sticky="w", padx=10)

        ctk.CTkLabel(left_optionsframe, text="Appearance Mode", anchor="w").grid(row=1, column=1, sticky="w")
        ctk.CTkOptionMenu(
            left_optionsframe,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
            variable=self._ctk_theme,
        ).grid(row=1, column=0, padx=20, pady=10)

        ctk.CTkLabel(left_optionsframe, text="UI Scaling", anchor="w").grid(row=2, column=1, sticky="w")
        ctk.CTkOptionMenu(
            left_optionsframe,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event,
            variable=self._ctk_size,
        ).grid(row=2, column=0, padx=20, pady=10)

        ctk.CTkLabel(left_optionsframe, text="Colour (Restart Required)", anchor="w").grid(row=3, column=1, sticky="w")
        ctk.CTkOptionMenu(
            left_optionsframe,
            values=["blue", "green", "dark-blue"],
            command=self.change_colour_event,
            variable=self._ctk_colour,
        ).grid(row=3, column=0, padx=20, pady=10)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        self._config.set_str("Theme", new_appearance_mode)

    def change_scaling_event(self, new_scaling: str) -> None:
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)
        self._config.set_str("Scaling", new_scaling)

    def change_colour_event(self, new_colour: str) -> None:
        logging.info("Changing colour to : " + new_colour)
        ctk.set_default_color_theme(new_colour)
        self._config.set_str("Colour", new_colour)


class _Logging(ctk.CTkFrame):  # pylint: disable=too-many-ancestors,too-many-instance-attributes
    """Logging Window"""

    def __init__(self, container: ctk.CTk, config: appConfig):
        super().__init__(container)
        self._config = config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)

        ctk.CTkLabel(self, text="Messages").grid(column=0, row=0, sticky="ws", padx=(10, 0), pady=10)

        self.logwin = ctk.CTkTextbox(self, state="disabled")
        self.logwin.grid(column=0, row=2, sticky="new", padx=(10, 10), pady=(0, 10))
        self.logwin.configure(height=100, wrap="word")
        # Logging configuration
        userconfdir = user_config_dir("TimeValidate", "Swimming Canada")
        pathlib.Path(userconfdir).mkdir(parents=True, exist_ok=True)
        logfile = os.path.join(userconfdir, "timevalidate.log")

        logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        # Create textLogger
        text_handler = TextHandler(self.logwin)
        text_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        # Add the handler to logger
        logger = logging.getLogger()
        logger.addHandler(text_handler)


class mainApp(ctk.CTkFrame):  # pylint: disable=too-many-ancestors
    """Main Appliction"""

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(self, container: ctk.CTk, config: appConfig):
        super().__init__(container)
        self._config = config

        self.grid(column=0, row=0, sticky="news")
        self.columnconfigure(0, weight=1)
        # Odd rows are empty filler to distribute vertical whitespace
        for i in [1, 3]:
            self.rowconfigure(i, weight=1)

        self.tabview = ctk.CTkTabview(self, width=container.winfo_width())
        self.tabview.grid(row=0, column=0, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.tabview.add("Splash Fixes")
        self.tabview.add("Configuration")

        # Generate Documents Tab
        self.tabview.tab("Splash Fixes").grid_columnconfigure(0, weight=1)
        self.SplashFixesTab = _Splash_Fixes_Tab(self.tabview.tab("Splash Fixes"), self._config)
        self.SplashFixesTab.grid(column=0, row=0, sticky="news")

        self.tabview.tab("Configuration").grid_columnconfigure(0, weight=1)
        self.configinfo = _Configuration_Tab(self.tabview.tab("Configuration"), self._config)
        self.configinfo.grid(column=0, row=0, sticky="news")

        # Logging Window
        loggingwin = _Logging(self, self._config)
        loggingwin.grid(column=0, row=2, padx=(20, 20), pady=(20, 0), sticky="new")

        # Info panel
        fr8 = ctk.CTkFrame(self)
        fr8.grid(column=0, row=4, sticky="news", pady=(10, 0))
        fr8.rowconfigure(0, weight=1)
        fr8.columnconfigure(0, weight=1)
        link_label = ctk.CTkLabel(fr8, text="Documentation: Coming Soon...")
        link_label.grid(column=0, row=0, sticky="w", padx=10)
        # Custom Tkinter clickable label example https://github.com/TomSchimansky/CustomTkinter/issues/1208
        link_label.bind(
            "<Button-1>", lambda event: webbrowser.open("https://www.swimming.ca")
        )  # link the command function
        link_label.bind("<Enter>", lambda event: link_label.configure(font=("", 13, "underline"), cursor="hand2"))
        link_label.bind("<Leave>", lambda event: link_label.configure(font=("", 13), cursor="arrow"))
        version_label = ctk.CTkLabel(fr8, text="Version " + APP_VERSION)
        version_label.grid(column=1, row=0, sticky="nes", padx=(0, 10))


def main():
    """testing"""
    root = ctk.CTk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    root.resizable(True, True)
    options = appConfig()
    settings = mainApp(root, options)
    settings.grid(column=0, row=0, sticky="news")
    logging.info("Hello World")
    root.mainloop()


if __name__ == "__main__":
    main()

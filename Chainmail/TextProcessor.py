import difflib
import json
import logging
import os
import re
from typing import Dict, Pattern, List, Match

from .Events import Events, ConsoleOutputEvent, VersionDiscoveredEvent
from . import Wrapper

RegexMatches = List[Match[str]]


class TextProcessor(object):

    def __init__(self, wrapper: "Wrapper.Wrapper"):
        self._wrapper = wrapper
        self.regexes = []  # type: List[Dict[str, Pattern[str]]]
        self._logger = logging.getLogger("TextProcessor")
        self.server_log = logging.getLogger("MinecraftServer")

        self._regex_path = os.path.join(__file__, os.pardir, "regex")

        self.load_version("generic")

    @staticmethod
    def get_json_files(path: str):
        for file in os.listdir(path):
            if file.endswith(".json"):
                yield os.path.join(path, file)

    def load_version(self, version: str):
        self._logger.debug(f"Loading regexes for version {version}...")
        directory = os.path.join(self._regex_path, version)
        if os.path.isdir(directory):
            for file in self.get_json_files(directory):
                with open(file) as f:
                    data = json.load(f)

                    for item in data:
                        self.regexes.append({
                            "type": item["type"],
                            "regex": re.compile(item["regex"])
                        })
                        self._logger.debug(f"Loaded new regex for {item['type']}")
        else:
            self._logger.warning(f"Version {version} not found.")
            close = difflib.get_close_matches(version, os.listdir(self._regex_path))
            if len(close) != 0:
                self._logger.warning(f"Using closest variation: {close[0]}. This may cause compatibility issues.")
                self.load_version(close[0])
            else:
                self._logger.error("No close variation found. Not attempting to load.")
                return
        self._logger.debug("Regexes loaded.")

    def unspecified_handler(self, event_type: str, matches: RegexMatches):
        self._logger.warning(f"No handler specified for {event_type} (Matches: {', '.join(matches)}")

    def console_output(self, event_type: str, matches: RegexMatches):
        self.server_log.log(getattr(logging, matches[0][0]), matches[0][1])
        self._wrapper.EventManager.throw_event(Events.CONSOLE_OUTPUT, ConsoleOutputEvent(matches[0][0],
                                                                                         matches[0][1]))

    def version_discovered(self, event_type: str, matches: RegexMatches):
        self._logger.debug(f"Version detected: {matches[0]}")
        self._wrapper.version = matches[0]
        self.load_version(matches[0])
        self._wrapper.EventManager.throw_event(Events.VERSION_DISCOVERED, VersionDiscoveredEvent(matches[0]))

    def process_line(self, line: str):
        line = line.replace("\r\n", "\n").rstrip("\n")
        print(line)
        for regex in self.regexes:
            if regex["regex"].match(line):
                getattr(self, regex["type"], self.unspecified_handler)(regex["type"], regex["regex"].findall(line))
import logging
import datetime
import requests
import dateutil.parser

from pajbot.models.command import Command
from pajbot.managers.db import DBManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.models.user import User

from pajbot import utils

log = logging.getLogger(__name__)

class Taxation(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Taxation"
    DESCRIPTION = "Forces users to pay tax"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="timeout_duration",
            label="Timeout duration, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=86400,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="default_process_time_days",
            label="Default number of days to process",
            type="number",
            required=True,
            placeholder="",
            default=7,
            constraints={"min_value": 1, "max_value": 30},
        ),
        ModuleSetting(
            key="minimum_taxes",
            label="Minimum number of taxes to avoid a ban if the user is not a sub, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="minimum_taxes_subs",
            label="Minimum number of taxes to avoid a ban if the user is subbed, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="number_taxes_award_points",
            label="Minimum number of taxes to award points, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=7,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="number_points_tax",
            label="Points to give when they hit the threshold, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=15000,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="number_points_top",
            label="Points to the user with the most taxes paid, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=15000,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="redeemed_id",
            label="ID of redemeed prize",
            type="text",
            required=True,
            default="",
            constraints={"min_str_len": 36, "max_str_len": 36},
        ),
    ]

    def process_tax(self, bot, source, message, **rest):
        message_split = message.split()
        if message_split:
            try:
                process_time = int(message_split[0])
            except ValueError:
                process_time = 0

        process_time = process_time if process_time > 0 and process_time < 30 else self.settings["default_process_time_days"]

        after_date = utils.now() - datetime.timedelta(days=process_time)
        with DBManager.create_session_scope() as db_session:
            users_active = db_session.query(User).filter(User.last_active > after_date).filter_by(moderator=False).filter_by(ignored=False).filter_by(banned=False).all() # ignore the mods or users who are ignored/banned by the bot
            user_taxes_dict = {}
            users_dict = {}
            for user in users_active:
                user_taxes_dict[user.id] = 0
                users_dict[user.id] = user

            data = {
                "request": "channel",
                "category": "rewards",
                "room_id": f"{self.bot.streamer_user_id}",
                "reward_id": self.settings["reward_id"],
                "after_date": str(after_date)
            }

            request = requests.post('https://chatlogs.troybot.live/query', json=data)
            if request.status_code != 200:
                self.bot.say("Api is currently down 4Head")
                return False

            resp = request.json()["data"]
            for item in resp:
                if item["user_id"] in user_taxes_dict:
                    user_taxes_dict[item["user_id"]] += 1

            users_to_timeout = []
            users_to_award = []
            action_messages = []

            for item in user_taxes_dict:
                user = users_dict[item]
                min_tax = self.settings[f"minimum_taxes{'_subs' if user.subscriber else ''}"]
                if user_taxes_dict[item] < min_tax and min_tax:
                    users_to_timeout.append(user)
                elif user_taxes_dict[item] >= self.settings["number_taxes_award_points"] and self.settings["number_taxes_award_points"]:
                    users_to_award.append(user)

            if self.settings["timeout_duration"]:
                check_user_timeouts = self.bot.twitch_helix_api.bulk_fetch_user_bans("user_id", [x.id for x in users_to_timeout], self.bot.streamer_user_id, self.bot.streamer_access_token_manager.token)
                number_of_timeouts = 0
                for user in users_to_timeout:
                    timeout = check_user_timeouts[user.id]
                    if timeout is not None:
                        if not timeout["expires_at"]:
                            continue
                        new_timeout = (dateutil.parser.parse(timeout["expires_at"]) - utils.now()).total_seconds() + self.settings["timeout_duration"]
                    else:
                        new_timeout = self.settings["timeout_duration"]
                    new_timeout = int(60*60*24*14 if new_timeout > 60*60*24*14 else new_timeout)
                    if new_timeout > 0:
                        self.bot.timeout(user, new_timeout, "Failed to pay taxes")
                        number_of_timeouts += 1
                action_messages.append(f"Timedout {number_of_timeouts} users for not paying tax.")

            if self.settings["number_points_tax"]:
                for user in users_to_award:
                    user.points += self.settings["number_points_tax"]
                action_messages.append(f"Awarded {len(users_to_award)} users {self.settings['number_points_tax']} points for paying tax.")

            if self.settings["number_points_top"]:
                top_user = max(user_taxes_dict, key=user_taxes_dict.get)
                top_user.points += self.settings["number_points_top"]
                action_messages.append(f"Awarded {top_user}, {self.settings['number_points_tax']} points for paying the most tax.")

            self.bot.me(" ".join(action_messages))

    def load_commands(self, **options):
        self.commands["processtax"] = Command.raw_command(
            self.process_tax, level=1000, description="Processes the tax for the last 7 days"
        )

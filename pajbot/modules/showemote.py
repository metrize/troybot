import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.managers.schedule import ScheduleManager

log = logging.getLogger(__name__)

WIDGET_ID = 1


class ShowEmoteModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Show Emote"
    DESCRIPTION = "Show a single emote on screen for a few seconds using !#showemote"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="point_cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=100,
            constraints={"min_value": 0, "max_value": 999999},
        ),
        ModuleSetting(
            key="cooldown_per_user",
            label="Cooldown per user",
            type="number",
            required=True,
            placeholder="Cooldown per user",
            default=0,
            constraints={"min_value": 0, "max_value": 999999},
        ),
        ModuleSetting(
            key="cooldown_global",
            label="Cooldown global",
            type="number",
            required=True,
            placeholder="Cooldown global",
            default=0,
            constraints={"min_value": 0, "max_value": 999999},
        ),
        ModuleSetting(
            key="disable_cost",
            label="Point disable cost",
            type="number",
            required=True,
            placeholder="Point disable cost",
            default=5000,
            constraints={"min_value": 0, "max_value": 999999},
        ),
        ModuleSetting(
            key="disable_duration",
            label="Point disable duration",
            type="number",
            required=True,
            placeholder="Point disable cost",
            default=300,
            constraints={"min_value": 0, "max_value": 999999},
        ),
        ModuleSetting(
            key="disable_cooldown",
            label="Point disable cooldown",
            type="number",
            required=True,
            placeholder="Point disable cooldown",
            default=600,
            constraints={"min_value": 0, "max_value": 999999},
        ),
        ModuleSetting(key="sub_only", label="Subscribers only", type="boolean", required=True, default=False),
        ModuleSetting(
            key="can_whisper", label="Command can be whispered", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="emote_whitelist",
            label="Whitelisted emotes (separate by spaces). Leave empty to use the blacklist.",
            type="text",
            required=True,
            placeholder="i.e. Kappa Keepo PogChamp KKona",
            default="",
        ),
        ModuleSetting(
            key="emote_blacklist",
            label="Blacklisted emotes (separate by spaces). Leave empty to allow all emotes.",
            type="text",
            required=True,
            placeholder="i.e. Kappa Keepo PogChamp KKona",
            default="",
        ),
        ModuleSetting(
            key="emote_opacity",
            label="Emote opacity (in percent)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="emote_persistence_time",
            label="Time in milliseconds until emotes disappear on screen",
            type="number",
            required=True,
            placeholder="",
            default=5000,
            constraints={"min_value": 500, "max_value": 60000},
        ),
        ModuleSetting(
            key="emote_onscreen_scale",
            label="Scale emotes onscreen by this factor (100 = normal size)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 0, "max_value": 100000},
        ),
        ModuleSetting(
            key="success_whisper",
            label="Send a whisper when emote was successfully sent",
            type="boolean",
            required=True,
            default=True,
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.showemote_disabled = False

    def is_emote_allowed(self, emote_code):
        if len(self.settings["emote_whitelist"].strip()) > 0:
            return emote_code in self.settings["emote_whitelist"]

        return emote_code not in self.settings["emote_blacklist"]

    def show_emote(self, bot, source, args, **rest):
        if self.showemote_disabled:
            bot.whisper(source, "Someone has paid to turn this off")
            return False

        emote_instances = args["emote_instances"]

        if len(emote_instances) <= 0:
            # No emotes in the given message
            bot.whisper(source, "No valid emotes were found in your message.")
            return False

        first_emote = emote_instances[0].emote

        # request to show emote is ignored but return False ensures user is refunded points
        if not self.is_emote_allowed(first_emote.code):
            return False

        self.bot.websocket_manager.emit(
            "new_emotes",
            WIDGET_ID,
            {
                "emotes": [first_emote.jsonify()],
                "opacity": self.settings["emote_opacity"],
                "persistence_time": self.settings["emote_persistence_time"],
                "scale": self.settings["emote_onscreen_scale"],
            },
        )
        if self.settings["success_whisper"]:
            bot.whisper(source, f"Successfully sent the emote {first_emote.code} to the stream!")

    def disable_showemote(self, bot, source, args, **rest):
        if not self.showemote_disabled:
            self.showemote_disabled = True
            bot.whisper(source, f"Successfully disabled the show emote feature")
            ScheduleManager.execute_delayed(self.settings["disable_duration"], self.enable_showemote)
            return True

        bot.whisper(source, f"Show emote is already disabled!")
        return False

    def enable_showemote(self):
        self.showemote_disabled = False

    def load_commands(self, **options):
        self.commands["showemote"] = Command.raw_command(
            self.show_emote,
            notify_on_error=True,
            cost=self.settings["point_cost"],
            description="Show an emote on stream!",
            sub_only=self.settings["sub_only"],
            can_execute_with_whisper=self.settings["can_whisper"],
            delay_all=self.settings["cooldown_global"],
            delay_user=self.settings["cooldown_per_user"],
            examples=[
                CommandExample(
                    None,
                    "Show an emote on stream.",
                    chat="user:!showemote Keepo\n" "bot>user: Successfully sent the emote Keepo to the stream!",
                    description="",
                ).parse()
            ],
        )
        self.commands["disableshowemote"] = Command.raw_command(
            self.disable_showemote,
            cost=self.settings["point_disable_cost"],
            description="Show an emote on stream!",
            delay_all=self.settings["point_disable_cooldown"],
            examples=[
                CommandExample(
                    None,
                    "Show an emote on stream.",
                    chat="user:!#showemote Keepo\n" "bot>user: Successfully sent the emote Keepo to the stream!",
                    description="",
                ).parse()
            ],
        )

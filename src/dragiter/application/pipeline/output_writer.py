import json
from pathlib import Path

from dragiter.domain.models.chat_sessions import ChatSessions, ChatMessage
from dragiter.domain.models.settings import OutputDirectoryPathSetting, OutputFilePathSetting, OutputModeStringSetting, \
    ActivityFilePathSetting
from dragiter.application.core.xdi import *
from dragiter.domain.models.application_result import ApplicationResult
from dragiter.domain.models.loop import Loop
from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.infrastructure.io.io_services import write_or_append_lines_to_unique_file

logger = logging.getLogger(__name__)

class OutputWriter:
    def __init__(self) -> None:
        pass



    def run(self,
            chat_sessions: ChatSessions,
            activity_file_path_setting: ActivityFilePathSetting,
            output_file_path_setting: OutputFilePathSetting,
            output_directory_path_setting: OutputDirectoryPathSetting,
            output_mode_string_setting: OutputModeStringSetting,
            prompt: PromptTemplate,
            loop: Loop) -> ApplicationResult:

        try:
            printable_value: str = ""
            open_mode: str = output_mode_string_setting.value or "x"
            application_result = ApplicationResult(0)

            # create simple list
            content_list = [chat_session.output_chat_message.content for chat_session in chat_sessions.session_list]

            # if nothin to report - bail out ...
            out_data = " ".join(content_list)
            if out_data == "": return application_result   # --> out 0

            # printable_value = "\n\n\n\n".join(content_list)
            printable_value = prompt.output_delimiter.join(content_list)
            # write result to one file
            if output_file_path_setting.is_set:
                write_or_append_lines_to_unique_file(output_file_path_setting.value, open_mode, [printable_value] )



            # write to many files (all loops, use numbered prompt file name as output filename
            if output_directory_path_setting.is_set:
                #calc filename
                name_of_file_path: Path = None

                if loop.lines:
                    name_of_file_path = Path(prompt.output_filename_schema)
                    counter: int = 0
                    for line in content_list:
                        counter += 1
                        numbered_file_name: Path = Path(f"{name_of_file_path.stem}_{counter:03d}{name_of_file_path.suffix}")
                        write_or_append_lines_to_unique_file(output_directory_path_setting.value / numbered_file_name, open_mode, [line] )

                else:
                    name_of_file_path = Path(prompt.output_filename_schema)
                    write_or_append_lines_to_unique_file(
                        output_directory_path_setting.value / Path(name_of_file_path), open_mode, content_list)

            # last but not least the activity, jsonl
            if activity_file_path_setting.is_set:
                activity_dicts: list[dict[str, str]] = []
                activity_lines: list[str] = []

                chat_message_list: list[ChatMessage] = []
                for chat_session in chat_sessions.session_list:
                    for chat_message in chat_session.input_chat_message_list:
                        activity_dicts.append(
                            json.dumps({
                                "TS": chat_session.chat_result.ended_at.isoformat() if chat_session.chat_result.ended_at else "",
                                "RL": chat_message.role,
                                "CT": chat_message.content}))

                    activity_dicts.append(
                        json.dumps({
                            "TS": chat_session.chat_result.ended_at.isoformat() if chat_session.chat_result.ended_at else "",
                            "RL": chat_session.output_chat_message.role,
                            "CT": chat_session.output_chat_message.content}))

                write_or_append_lines_to_unique_file(activity_file_path_setting.value, open_mode, activity_dicts)
            # end of activity block


            # finally put data to std_out
            print(printable_value)  # to std_out


            return ApplicationResult(0)
        except Exception as e:
            raise OutputWriterError(f"Output dispatcher failure.") from e


class OutputWriterError(Exception):
    pass
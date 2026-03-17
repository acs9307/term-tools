from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from importlib.machinery import SourceFileLoader


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "bin" / "smart-kill"
LOADER = SourceFileLoader("smart_kill", str(MODULE_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {MODULE_PATH}")

smart_kill = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = smart_kill
SPEC.loader.exec_module(smart_kill)


class FindMatchingProcessesTest(unittest.TestCase):
    def test_exact_match_still_works(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=100,
                comm="/usr/local/bin/node",
                args="/usr/local/bin/node server.js",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["node"],
            ignore_case=False,
        )

        self.assertEqual([process.pid for process in matches], [100])

    def test_partial_match_on_executable_name_is_included(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=101,
                comm="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                args='"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --type=renderer',
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["Chrome"],
            ignore_case=False,
        )

        self.assertEqual([process.pid for process in matches], [101])

    def test_partial_match_on_arg0_name_is_included(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=102,
                comm="/usr/bin/python3",
                args="/tmp/my-service-worker --reload",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["service"],
            ignore_case=False,
        )

        self.assertEqual([process.pid for process in matches], [102])

    def test_exact_match_on_raw_relative_arg0_is_included(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=108,
                comm="core-service",
                args="./core-service --watch",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["./core-service"],
            ignore_case=False,
        )

        self.assertEqual([process.pid for process in matches], [108])

    def test_ignore_case_applies_to_partial_matches(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=103,
                comm="/opt/tools/MyToolDaemon",
                args="/opt/tools/MyToolDaemon --watch",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["mytool"],
            ignore_case=True,
        )

        self.assertEqual([process.pid for process in matches], [103])

    def test_argument_search_is_included_by_default(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=104,
                comm="/usr/bin/python3",
                args="/usr/bin/python3 app.py --port 3000 --watch",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["3000"],
            ignore_case=False,
        )

        self.assertEqual([process.pid for process in matches], [104])

    def test_match_scope_executables_ignores_argument_only_matches(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=105,
                comm="/usr/bin/python3",
                args="/usr/bin/python3 app.py --port 3000 --watch",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["3000"],
            ignore_case=False,
            match_scope=smart_kill.MATCH_SCOPE_EXECUTABLES,
        )

        self.assertEqual(matches, [])

    def test_match_scope_arguments_ignores_executable_matches(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=106,
                comm="/usr/local/bin/node",
                args="/usr/local/bin/node server.js",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["node"],
            ignore_case=False,
            match_scope=smart_kill.MATCH_SCOPE_ARGUMENTS,
        )

        self.assertEqual(matches, [])

    def test_match_scope_arguments_still_supports_partial_matching(self) -> None:
        processes = [
            smart_kill.ProcessEntry(
                pid=107,
                comm="/usr/bin/python3",
                args="/usr/bin/python3 app.py --reload --host devbox.local",
            )
        ]

        matches = smart_kill.find_matching_processes(
            processes=processes,
            names=["devbox"],
            ignore_case=False,
            match_scope=smart_kill.MATCH_SCOPE_ARGUMENTS,
        )

        self.assertEqual([process.pid for process in matches], [107])


if __name__ == "__main__":
    unittest.main()

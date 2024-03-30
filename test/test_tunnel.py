import logging
import re

import pytest
from pytest_mock import MockerFixture

from src.tunnel import Tunnel


@pytest.fixture
def mock_get_logger(mocker: MockerFixture):
    return mocker.patch("src.tunnel.logging.getLogger")


@pytest.fixture
def mock_stream_handler(mocker: MockerFixture):
    return mocker.patch("src.tunnel.logging.StreamHandler")


@pytest.fixture
def mock_socket(mocker):
    return mocker.patch("src.tunnel.socket.socket")


@pytest.fixture
def mock_thread(mocker: MockerFixture):
    return mocker.patch("src.tunnel.Thread")


@pytest.fixture
def mock_event(mocker: MockerFixture):
    return mocker.patch("src.tunnel.Event")


@pytest.fixture
def mock_file_handler(mocker: MockerFixture):
    return mocker.patch("src.tunnel.logging.FileHandler")


@pytest.fixture
def mock_popen(mocker: MockerFixture):
    return mocker.patch("src.tunnel.subprocess.Popen")


@pytest.mark.parametrize(
    "debug, handlers",
    [
        (True, []),
        (False, ["handler"]),
    ],
)
def test_initialize_tunnel_class(
    mock_get_logger, mock_stream_handler, debug, handlers, mocker: MockerFixture
):
    # Mock getLogger method to return MagicMock object
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger
    mock_handlers = mock_logger.handlers
    mock_handlers.return_value = handlers

    # Mock the StreamHandler class
    mock_handler_instance = mocker.MagicMock()
    mock_stream_handler.return_value = mock_handler_instance

    # Create a Tunnel instance
    tunnel = Tunnel(3000, debug=debug)

    # Assertions
    mock_get_logger.assert_called_with("Tunnel")
    assert tunnel.logger == mock_logger
    if not mock_handlers:
        mock_logger.addHandler.assert_called_once_with(mock_handler_instance)
        mock_handler_instance.setLevel.assert_called_once_with(
            logging.DEBUG if debug else logging.INFO
        )


def test_with_tunnel_list():
    tunnel = Tunnel.with_tunnel_list(
        3000, [{"command": "cmd", "pattern": "pat", "name": "n", "note": "nt"}]
    )
    assert tunnel.port == 3000
    assert len(tunnel.tunnel_list) == 1


def test_with_tunnel_list_empty_list():
    with pytest.raises(ValueError):
        Tunnel.with_tunnel_list(3000, [])


def test_with_tunnel_list_invalid_list():
    with pytest.raises(ValueError):
        Tunnel.with_tunnel_list(3000, [{"command": "cmd", "pattern": 1}])


def test_add_tunnel():
    tunnel = Tunnel(3000)
    for tunnel_data in [
        {"command": "cmd1", "pattern": "pat1", "name": "n1", "note": "nt1"},
        {"command": "cmd2", "pattern": "pat2", "name": "n2", "note": "nt2"},
    ]:
        tunnel.add_tunnel(**tunnel_data)
    assert len(tunnel.tunnel_list) == 2


def test_add_tunnel_invalid_value():
    tunnel = Tunnel(3000)
    with pytest.raises((ValueError, TypeError)):
        tunnel.add_tunnel(**{"command": "cmd", "pattern": re.compile("pat")})


def test_reset():
    tunnel = Tunnel(3000)
    tunnel.reset()
    assert len(tunnel.urls) == 0
    assert len(tunnel.jobs) == 0
    assert len(tunnel.processes) == 0
    assert not tunnel.stop_event.is_set()
    assert not tunnel.printed.is_set()
    assert not tunnel._is_running


def test_is_port_available(mock_socket):
    mock_sock_instance = mock_socket.return_value.__enter__.return_value
    mock_sock_instance.connect_ex.return_value = 1
    assert Tunnel.is_port_available(3000)

    mock_sock_instance.connect_ex.return_value = 0
    assert not Tunnel.is_port_available(3000)

    mock_sock_instance.connect_ex.bind.side_effect = OSError
    assert not Tunnel.is_port_available(3000)


@pytest.mark.parametrize("result", [True, False])
def test_wait_for_condition(result):
    def condition():
        return result

    assert Tunnel.wait_for_condition(condition, timeout=1) == result


def test__process_line():
    tunnel = Tunnel(3000)
    tunnel.add_tunnel(**{"command": "cmd", "pattern": "pat", "name": "n", "note": "nt"})
    line = "http://pat nt"
    assert tunnel._process_line(line)
    assert line in tunnel.urls


@pytest.mark.parametrize(
    "wait_condition, check_local_port, expected_info_calls, expected_warning_calls",
    [
        (
            True,
            True,
            [
                "Getting URLs",
                "Wait until port: 3000 online before print URLs",
                "* Running on: http://example.com",
            ],
            [],
        ),
        (
            False,
            True,
            [
                "Getting URLs",
                "Wait until port: 3000 online before print URLs",
                "* Running on: http://example.com",
            ],
            ["Timeout while getting tunnel URLs, print available URLs"],
        ),
        (
            True,
            False,
            [
                "Getting URLs",
                "* Running on: http://example.com",
            ],
            [],
        ),
        (
            False,
            False,
            [
                "Getting URLs",
                "* Running on: http://example.com",
            ],
            ["Timeout while getting tunnel URLs, print available URLs"],
        ),
    ],
)
def test__print(
    mock_get_logger,
    wait_condition,
    check_local_port,
    expected_info_calls,
    expected_warning_calls,
    mocker: MockerFixture,
):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    mocker.patch.object(Tunnel, "wait_for_condition", return_value=wait_condition)
    tunnel = Tunnel(3000)
    tunnel.urls = ["http://example.com"]
    tunnel.check_local_port = check_local_port

    tunnel._print()

    mock_logger.info.assert_has_calls([mocker.call(c) for c in expected_info_calls])
    if wait_condition is False:
        mock_logger.warning.assert_has_calls([mocker.call(c) for c in expected_warning_calls])


@pytest.mark.parametrize(
    "wait_condition, check_local_port, expected_debug_calls",
    [
        (True, True, ["Wait until port: 3000 online before running the command for test_tunnel"]),
        (False, True, ["Wait until port: 3000 online before running the command for test_tunnel"]),
        (True, False, []),
        (False, False, []),
    ],
)
def test__run(
    mock_get_logger,
    mock_popen,
    wait_condition,
    check_local_port,
    expected_debug_calls,
    mocker: MockerFixture,
):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    mocker.patch.object(Tunnel, "wait_for_condition", return_value=wait_condition)

    tunnel = Tunnel(3000)

    mock_popen_instance = mocker.MagicMock()
    mock_popen.return_value = mock_popen_instance

    tunnel.check_local_port = check_local_port

    mock_child_logger = mocker.MagicMock()
    mock_get_logger.return_value.getChild.return_value = mock_child_logger

    tunnel._run("test_command", "test_tunnel")

    if check_local_port:
        mock_child_logger.debug.assert_has_calls([mocker.call(c) for c in expected_debug_calls])


def test_start(
    mock_get_logger, mock_popen, mock_thread, mock_event, mock_file_handler, mocker: MockerFixture
):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)
    tunnel.add_tunnel(**{"command": "cmd", "pattern": "pat", "name": "n", "note": "nt"})

    mock_popen_instance = mocker.MagicMock()
    mock_popen.return_value = mock_popen_instance

    mock_thread_instance = mocker.MagicMock()
    mock_thread.return_value = mock_thread_instance

    mock_event_instance = mocker.MagicMock()
    mock_event.return_value = mock_event_instance

    mock_file_handler_instance = mocker.MagicMock()
    mock_file_handler.return_value = mock_file_handler_instance

    tunnel.start()

    assert tunnel.printed.is_set()
    assert tunnel._is_running


def test_start_empty_tunnel_list(mock_get_logger, mocker: MockerFixture):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)

    with pytest.raises(ValueError):
        tunnel.start()


def test_start_already_run(mock_get_logger, mocker: MockerFixture):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)
    tunnel._is_running = True

    with pytest.raises(RuntimeError):
        tunnel.start()


def test_stop(
    mock_get_logger, mock_popen, mock_thread, mock_event, mock_file_handler, mocker: MockerFixture
):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)
    tunnel.add_tunnel(**{"command": "cmd", "pattern": "pat", "name": "n", "note": "nt"})

    mock_popen_instance = mocker.MagicMock()
    mock_popen.return_value = mock_popen_instance

    mock_thread_instance = mocker.MagicMock()
    mock_thread.return_value = mock_thread_instance

    mock_event_instance = mocker.MagicMock()
    mock_event.return_value = mock_event_instance

    mock_file_handler_instance = mocker.MagicMock()
    mock_file_handler.return_value = mock_file_handler_instance

    tunnel.start()
    tunnel.stop()

    assert tunnel._is_running is False


def test_stop_not_running(mock_get_logger, mocker: MockerFixture):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)

    with pytest.raises(RuntimeError):
        tunnel.stop()


def test_enter_exit(
    mock_get_logger,
    mock_popen,
    mock_thread,
    mock_event,
    mock_file_handler,
    mocker: MockerFixture,
):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)
    tunnel.add_tunnel(**{"command": "cmd", "pattern": "pat", "name": "n", "note": "nt"})

    mock_popen_instance = mocker.MagicMock()
    mock_popen.return_value = mock_popen_instance

    mock_thread_instance = mocker.MagicMock()
    mock_thread.return_value = mock_thread_instance

    mock_event_instance = mocker.MagicMock()
    mock_event.return_value = mock_event_instance

    mock_file_handler_instance = mocker.MagicMock()
    mock_file_handler.return_value = mock_file_handler_instance

    with tunnel:
        assert tunnel._is_running

    assert not tunnel._is_running


def test_enter_exit_empty_tunnel_list(mock_get_logger, mocker: MockerFixture):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)

    with pytest.raises(ValueError):
        with tunnel:
            pass


def test_enter_exit_already_run(mock_get_logger, mocker: MockerFixture):
    mock_logger = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger

    tunnel = Tunnel(3000)
    tunnel._is_running = True

    with pytest.raises(RuntimeError):
        with tunnel:
            pass
